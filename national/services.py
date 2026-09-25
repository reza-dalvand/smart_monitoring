"""
سرویس مرکزی تحلیل داده برای پنل مسئول کشوری
تمام منطق آماری در این لایه پیاده‌سازی می‌شود.
"""
import logging
from datetime import timedelta
from typing import Optional, Dict, Any, List

from django.db.models import (
    Count, Avg, Sum, Q, F, Case, When,
    FloatField, IntegerField, Value, Prefetch,
)
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from accounts.models import User
from dashboard.models import (
    Classroom, ClassSession, AttendanceRecord,
    Question, StudentAnswer, AttendanceRequest,
    AttendanceResponse, AIGenerationJob,
)
from face.models import FaceVerificationLog, FaceProfile
from .models import Province, District, School

logger = logging.getLogger(__name__)


class NationalAnalyticsService:
    """سرویس اصلی تحلیل داده‌های ملی"""

    # ──────────────────────────────────────────────
    #  Scope & Date Helpers
    # ──────────────────────────────────────────────
    @staticmethod
    def _apply_scope(qs, scope, province_id, rel='school__district__province_id'):
        if scope == 'province' and province_id:
            return qs.filter(**{rel: province_id})
        return qs

    @staticmethod
    def _date_filter(period, date_from=None, date_to=None):
        now = timezone.now()
        today = now.date()
        if period == 'today':
            return Q(session_date__date=today)
        if period == 'week':
            days_since_sat = (today.weekday() + 2) % 7
            start = today - timedelta(days=days_since_sat)
            return Q(session_date__date__gte=start,
                     session_date__date__lte=start + timedelta(days=6))
        if period == 'month':
            start = today.replace(day=1)
            if today.month == 12:
                end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            return Q(session_date__date__gte=start, session_date__date__lte=end)
        if period == 'year':
            if today.month >= 9:
                start = today.replace(month=9, day=23)
            else:
                start = today.replace(year=today.year - 1, month=9, day=23)
            return Q(session_date__date__gte=start,
                     session_date__date__lte=start + timedelta(days=364))
        if period == 'custom' and date_from and date_to:
            return Q(session_date__date__gte=date_from,
                     session_date__date__lte=date_to)
        return Q()

    @staticmethod
    def _safe_rate(numerator, denominator, digits=1):
        if not denominator:
            return None
        return round((numerator / denominator) * 100, digits)

    # ──────────────────────────────────────────────
    #  Overview KPIs
    # ──────────────────────────────────────────────
    @staticmethod
    def get_overview(scope='national', province_id=None,
                     period='month', date_from=None, date_to=None) -> Dict[str, Any]:
        result = {
            'students': 0, 'teachers': 0, 'schools': 0,
            'classrooms': 0, 'sessions': 0,
            'attendance_rate': None, 'absence_rate': None,
            'participation_rate': None, 'performance_rate': None,
            'active_users': 0, 'questions_used': 0,
            'face_verifications': 0,
        }

        # Students
        sq = User.objects.filter(role='student')
        if scope == 'province' and province_id:
            sq = sq.filter(enrolled_classes__school__district__province_id=province_id).distinct()
        result['students'] = sq.count()

        # Teachers
        tq = User.objects.filter(role='teacher')
        if scope == 'province' and province_id:
            tq = tq.filter(taught_classes__school__district__province_id=province_id).distinct()
        result['teachers'] = tq.count()

        # Schools
        schq = School.objects.filter(is_active=True)
        if scope == 'province' and province_id:
            schq = schq.filter(district__province_id=province_id)
        result['schools'] = schq.count()

        # Classrooms
        cq = Classroom.objects.all()
        if scope == 'province' and province_id:
            cq = cq.filter(school__district__province_id=province_id)
        result['classrooms'] = cq.count()

        # Sessions
        sesq = ClassSession.objects.all()
        if scope == 'province' and province_id:
            sesq = sesq.filter(classroom__school__district__province_id=province_id)
        df = NationalAnalyticsService._date_filter(period, date_from, date_to)
        result['sessions'] = sesq.filter(df).count()

        # Attendance
        att = NationalAnalyticsService._get_attendance_stats(scope, province_id, period, date_from, date_to)
        result['attendance_rate'] = att.get('present_rate')
        result['absence_rate'] = att.get('absent_rate')

        # Participation
        part = NationalAnalyticsService._get_participation_stats(scope, province_id)
        result['participation_rate'] = part.get('response_rate')
        result['performance_rate'] = part.get('correct_rate')

        # Face verifications
        fq = FaceVerificationLog.objects.all()
        if scope == 'province' and province_id:
            fq = fq.filter(student__enrolled_classes__school__district__province_id=province_id).distinct()
        result['face_verifications'] = fq.count()

        # Questions used
        qq = StudentAnswer.objects.all()
        if scope == 'province' and province_id:
            qq = qq.filter(question__classroom__school__district__province_id=province_id)
        result['questions_used'] = qq.count()

        return result

    # ──────────────────────────────────────────────
    #  Attendance
    # ──────────────────────────────────────────────
    @staticmethod
    def _get_attendance_stats(scope, province_id, period='month',
                              date_from=None, date_to=None) -> Dict:
        records = AttendanceRecord.objects.all()
        if scope == 'province' and province_id:
            records = records.filter(
                attendance_check__session__classroom__school__district__province_id=province_id
            )
        # date filter on session_date
        today = timezone.now().date()
        if period == 'today':
            records = records.filter(attendance_check__session__session_date__date=today)
        elif period == 'week':
            days_since_sat = (today.weekday() + 2) % 7
            start = today - timedelta(days=days_since_sat)
            records = records.filter(
                attendance_check__session__session_date__date__gte=start,
                attendance_check__session__session_date__date__lte=start + timedelta(days=6))
        elif period == 'month':
            start = today.replace(day=1)
            if today.month == 12:
                end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            records = records.filter(
                attendance_check__session__session_date__date__gte=start,
                attendance_check__session__session_date__date__lte=end)
        elif period == 'custom' and date_from and date_to:
            records = records.filter(
                attendance_check__session__session_date__date__gte=date_from,
                attendance_check__session__session_date__date__lte=date_to)

        total = records.count()
        if total == 0:
            return {'present_rate': None, 'absent_rate': None, 'total': 0,
                    'present': 0, 'absent': 0}
        present = records.filter(status='present').count()
        absent = records.filter(status='absent').count()
        return {
            'present_rate': NationalAnalyticsService._safe_rate(present, total),
            'absent_rate': NationalAnalyticsService._safe_rate(absent, total),
            'total': total, 'present': present, 'absent': absent,
        }

    @staticmethod
    def get_attendance_trend(scope, province_id=None, days=30) -> List[Dict]:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        records = AttendanceRecord.objects.filter(
            attendance_check__session__session_date__date__gte=start_date,
            attendance_check__session__session_date__date__lte=end_date,
        )
        if scope == 'province' and province_id:
            records = records.filter(
                attendance_check__session__classroom__school__district__province_id=province_id)

        daily = (
            records
            .annotate(date=TruncDate('attendance_check__session__session_date'))
            .values('date')
            .annotate(total=Count('id'), present=Count('id', filter=Q(status='present')))
            .order_by('date')
        )
        return [
            {
                'date': str(d['date']),
                'rate': NationalAnalyticsService._safe_rate(d['present'], d['total']),
                'total': d['total'], 'present': d['present'],
            }
            for d in daily
        ]

    @staticmethod
    def get_attendance_status_breakdown(scope, province_id=None) -> Dict:
        records = AttendanceRecord.objects.all()
        if scope == 'province' and province_id:
            records = records.filter(
                attendance_check__session__classroom__school__district__province_id=province_id)
        total = records.count()
        present = records.filter(status='present').count()
        absent = records.filter(status='absent').count()
        return {
            'total': total, 'present': present, 'absent': absent,
            'has_data': total > 0,
        }

    # ──────────────────────────────────────────────
    #  Participation
    # ──────────────────────────────────────────────
    @staticmethod
    def _get_participation_stats(scope, province_id) -> Dict:
        answers = StudentAnswer.objects.all()
        questions = Question.objects.all()
        if scope == 'province' and province_id:
            rel = 'question__classroom__school__district__province_id'
            answers = answers.filter(**{rel: province_id})
            questions = questions.filter(
                classroom__school__district__province_id=province_id)

        total_answers = answers.count()
        total_qs = questions.count()
        correct = answers.filter(is_correct=True).count()
        return {
            'response_rate': NationalAnalyticsService._safe_rate(total_answers, total_qs),
            'correct_rate': NationalAnalyticsService._safe_rate(correct, total_answers),
            'total_answers': total_answers,
            'total_questions': total_qs,
            'correct': correct,
        }

    @staticmethod
    def get_participation_trend(scope, province_id=None, days=30) -> List[Dict]:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        answers = StudentAnswer.objects.filter(
            answered_at__date__gte=start_date,
            answered_at__date__lte=end_date,
        )
        if scope == 'province' and province_id:
            answers = answers.filter(
                question__classroom__school__district__province_id=province_id)
        daily = (
            answers
            .annotate(date=TruncDate('answered_at'))
            .values('date')
            .annotate(total=Count('id'), correct=Count('id', filter=Q(is_correct=True)))
            .order_by('date')
        )
        return [
            {
                'date': str(d['date']),
                'total': d['total'],
                'correct': d['correct'],
                'rate': NationalAnalyticsService._safe_rate(d['correct'], d['total']),
            }
            for d in daily
        ]

    # ──────────────────────────────────────────────
    #  Performance by Subject
    # ──────────────────────────────────────────────
    @staticmethod
    def get_performance_by_subject(scope, province_id=None) -> List[Dict]:
        answers = StudentAnswer.objects.select_related('question__classroom')
        if scope == 'province' and province_id:
            answers = answers.filter(
                question__classroom__school__district__province_id=province_id)
        subjects = (
            answers
            .values(subject=F('question__classroom__subject'))
            .annotate(
                total=Count('id'),
                correct=Count('id', filter=Q(is_correct=True)),
            )
            .order_by('-total')[:15]
        )
        return [
            {
                'subject': s['subject'],
                'total': s['total'],
                'correct': s['correct'],
                'rate': NationalAnalyticsService._safe_rate(s['correct'], s['total']),
            }
            for s in subjects
        ]

    # ──────────────────────────────────────────────
    #  Province Comparison
    # ──────────────────────────────────────────────
    @staticmethod
    def get_province_comparison() -> List[Dict]:
        provinces = Province.objects.filter(is_active=True).annotate(
            students_count=Count('districts__schools__classrooms__students', distinct=True),
            schools_count=Count('districts__schools', distinct=True),
            classrooms_count=Count('districts__schools__classrooms', distinct=True),
        ).values('id', 'name', 'students_count', 'schools_count', 'classrooms_count')

        result = []
        for p in provinces:
            att = NationalAnalyticsService._get_attendance_stats('province', p['id'], 'month')
            part = NationalAnalyticsService._get_participation_stats('province', p['id'])
            result.append({
                'id': p['id'], 'name': p['name'],
                'students': p['students_count'],
                'schools': p['schools_count'],
                'classrooms': p['classrooms_count'],
                'attendance_rate': att.get('present_rate'),
                'participation_rate': part.get('response_rate'),
                'performance_rate': part.get('correct_rate'),
            })
        return result

    # ──────────────────────────────────────────────
    #  Face Verification
    # ──────────────────────────────────────────────
    @staticmethod
    def get_face_verification_stats(scope, province_id=None) -> Dict:
        logs = FaceVerificationLog.objects.all()
        if scope == 'province' and province_id:
            logs = logs.filter(
                student__enrolled_classes__school__district__province_id=province_id
            ).distinct()
        total = logs.count()
        if total == 0:
            return {'total': 0, 'has_data': False}
        verified = logs.filter(status='verified').count()
        suspicious = logs.filter(status='suspicious').count()
        failed = logs.filter(status='failed').count()
        error = logs.filter(status='error').count()
        return {
            'total': total, 'has_data': True,
            'verified': verified, 'suspicious': suspicious,
            'failed': failed, 'error': error,
            'success_rate': NationalAnalyticsService._safe_rate(verified, total),
        }

    # ──────────────────────────────────────────────
    #  AI Statistics
    # ──────────────────────────────────────────────
    @staticmethod
    def get_ai_stats(scope, province_id=None) -> Dict:
        jobs = AIGenerationJob.objects.all()
        questions = Question.objects.filter(source='ai')
        if scope == 'province' and province_id:
            rel = 'classroom__school__district__province_id'
            jobs = jobs.filter(**{rel: province_id})
            questions = questions.filter(**{rel: province_id})
        total_jobs = jobs.count()
        completed = jobs.filter(status='completed').count()
        failed = jobs.filter(status='failed').count()
        total_q = questions.count()
        approved = questions.filter(review_status='approved').count()
        rejected = questions.filter(review_status='rejected').count()
        pending = questions.filter(review_status='pending').count()
        return {
            'total_jobs': total_jobs, 'completed_jobs': completed,
            'failed_jobs': failed, 'total_ai_questions': total_q,
            'approved': approved, 'rejected': rejected, 'pending': pending,
        }

    # ──────────────────────────────────────────────
    #  System Usage
    # ──────────────────────────────────────────────
    @staticmethod
    def get_system_usage(scope, province_id=None) -> Dict:
        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        sessions = ClassSession.objects.all()
        requests = AttendanceRequest.objects.all()
        if scope == 'province' and province_id:
            rel = 'classroom__school__district__province_id'
            sessions = sessions.filter(**{rel: province_id})
            requests = requests.filter(**{rel: province_id})

        return {
            'sessions_today': sessions.filter(session_date__date=today).count(),
            'sessions_week': sessions.filter(session_date__date__gte=week_ago).count(),
            'sessions_month': sessions.filter(session_date__date__gte=month_ago).count(),
            'active_requests': requests.filter(status='active').count(),
            'total_requests': requests.count(),
        }

    # ──────────────────────────────────────────────
    #  Alerts
    # ──────────────────────────────────────────────
    @staticmethod
    def get_alerts(scope, province_id=None) -> List[Dict]:
        alerts = []
        today = timezone.now().date()
        month_ago = today - timedelta(days=30)

        # 1) Inactive schools
        schq = School.objects.filter(is_active=True)
        if scope == 'province' and province_id:
            schq = schq.filter(district__province_id=province_id)
        for school in schq[:50]:
            has_session = ClassSession.objects.filter(
                classroom__school=school,
                session_date__date__gte=month_ago
            ).exists()
            if not has_session:
                alerts.append({
                    'type': 'inactive_school', 'severity': 'warning',
                    'scope': school.name,
                    'province': school.district.province.name,
                    'message': f'مدرسه «{school.name}» در ۳۰ روز گذشته فعالیتی نداشته است.',
                    'date': today,
                })

        # 2) Face verification error rate
        fq = FaceVerificationLog.objects.filter(created_at__date__gte=month_ago)
        if scope == 'province' and province_id:
            fq = fq.filter(
                student__enrolled_classes__school__district__province_id=province_id
            ).distinct()
        total_f = fq.count()
        failed_f = fq.filter(status__in=['failed', 'error']).count()
        if total_f > 10 and (failed_f / total_f) > 0.3:
            alerts.append({
                'type': 'face_errors', 'severity': 'danger',
                'scope': 'سیستم احراز هویت',
                'province': 'کل' if scope == 'national' else Province.objects.filter(id=province_id).values_list('name', flat=True).first(),
                'message': f'نرخ خطای احراز هویت چهره به {round((failed_f/total_f)*100)}% رسیده است.',
                'date': today,
            })

        # 3) AI failure rate
        aj = AIGenerationJob.objects.filter(created_at__date__gte=month_ago)
        if scope == 'province' and province_id:
            aj = aj.filter(classroom__school__district__province_id=province_id)
        total_j = aj.count()
        failed_j = aj.filter(status='failed').count()
        if total_j > 5 and (failed_j / total_j) > 0.4:
            alerts.append({
                'type': 'ai_failures', 'severity': 'warning',
                'scope': 'سیستم هوش مصنوعی',
                'province': 'کل' if scope == 'national' else '',
                'message': f'نرخ شکست تولید سوال با هوش مصنوعی به {round((failed_j/total_j)*100)}% رسیده است.',
                'date': today,
            })
        return alerts

    # ──────────────────────────────────────────────
    #  Schools List
    # ──────────────────────────────────────────────
    @staticmethod
    def get_schools_list(scope, province_id=None, district_id=None) -> List[Dict]:
        schools = School.objects.filter(is_active=True).select_related(
            'district', 'district__province'
        ).annotate(classrooms_count=Count('classrooms', distinct=True))
        if scope == 'province' and province_id:
            schools = schools.filter(district__province_id=province_id)
        if district_id:
            schools = schools.filter(district_id=district_id)

        result = []
        for school in schools:
            att = AttendanceRecord.objects.filter(
                attendance_check__session__classroom__school=school)
            total_a = att.count()
            present_a = att.filter(status='present').count()
            result.append({
                'id': school.id, 'name': school.name,
                'district': school.district.name,
                'province': school.district.province.name,
                'school_type': school.get_school_type_display(),
                'classrooms_count': school.classrooms_count,
                'attendance_rate': NationalAnalyticsService._safe_rate(present_a, total_a),
            })
        return result

    # ──────────────────────────────────────────────
    #  Recent Activity
    # ──────────────────────────────────────────────
    @staticmethod
    def get_recent_activity(scope: str, province_id: Optional[int] = None,
                            limit: int = 10) -> List[Dict]:
        """فعالیت‌های اخیر"""
        activities = []
        
        # ۱. آخرین جلسات (ابتدا فیلتر، سپس Slice)
        sessions_qs = ClassSession.objects.select_related(
            'classroom', 'classroom__school'
        )
        if scope == 'province' and province_id:
            sessions_qs = sessions_qs.filter(
                classroom__school__district__province_id=province_id
            )
        sessions = sessions_qs.order_by('-session_date')[:limit]
        
        for session in sessions:
            activities.append({
                'type': 'session',
                'icon': 'bi-calendar-event-fill',
                'title': f'جلسه جدید در {session.classroom.name}',
                'description': session.topic or 'بدون موضوع',
                'date': session.session_date,
            })
            
        # ۲. آخرین درخواست‌های حضور (ابتدا فیلتر، سپس Slice)
        requests_qs = AttendanceRequest.objects.select_related(
            'classroom', 'teacher'
        )
        if scope == 'province' and province_id:
            requests_qs = requests_qs.filter(
                classroom__school__district__province_id=province_id
            )
        requests = requests_qs.order_by('-created_at')[:limit]

        for req in requests:
            activities.append({
                'type': 'attendance_request',
                'icon': 'bi-person-check-fill',
                'title': f'درخواست {req.get_request_type_display()}',
                'description': f'{req.classroom.name} - {req.teacher.get_full_name()}',
                'date': req.created_at,
            })
            
        # مرتب‌سازی نهایی بر اساس تاریخ و محدود کردن خروجی ترکیبی
        activities.sort(key=lambda x: x['date'], reverse=True)
        return activities[:limit]

class ReportService:
    @staticmethod
    def get_attendance_report(scope, province_id, period, date_from, date_to):
        return NationalAnalyticsService._get_attendance_stats(
            scope, province_id, period, date_from, date_to)

    @staticmethod
    def get_participation_report(scope, province_id):
        return NationalAnalyticsService._get_participation_stats(scope, province_id)

    @staticmethod
    def get_schools_report(scope, province_id):
        return NationalAnalyticsService.get_schools_list(scope, province_id)