"""
سرویس تحلیلی مسئول منطقه.
از NationalAnalyticsService موجود استفاده می‌کند
و لایه اجبار محدوده (Scope) را اضافه می‌نماید.
"""
import logging
from datetime import timedelta
from typing import Optional, Dict, Any, List

from django.db.models import Count, Q, Avg, F
from django.db.models.functions import TruncDate
from django.utils import timezone

from national.services import NationalAnalyticsService
from national.models import School
from dashboard.models import (
    Classroom, ClassSession, AttendanceRecord,
    Question, StudentAnswer, AttendanceRequest,
    AttendanceResponse, AIGenerationJob,
)
from face.models import FaceVerificationLog
from accounts.models import User
from .scope import DistrictScope

logger = logging.getLogger(__name__)


class DistrictAnalyticsService:
    """
    تمام متدها اجباراً با DistrictScope کار می‌کنند.
    View نمی‌تواند district را جعل کند.
    """

    def __init__(self, scope: DistrictScope):
        self.scope = scope
        self.district_id = scope.district_id

    # ──────────────────────────────────────────────
    #  Helper: فیلتر بر اساس منطقه
    # ──────────────────────────────────────────────

    def _school_filter(self):
        return Q(school__district_id=self.district_id)

    def _classroom_filter(self):
        return Q(classroom__school__district_id=self.district_id)

    def _date_filter(self, period='month', date_from=None, date_to=None):
        return NationalAnalyticsService._date_filter(period, date_from, date_to)

    # ──────────────────────────────────────────────
    #  Overview KPIs
    # ──────────────────────────────────────────────

    def get_overview(self, period='month', date_from=None, date_to=None,
                     school_id=None, grade=None, field=None) -> Dict[str, Any]:
        result = {
            'students': 0, 'teachers': 0, 'schools': 0,
            'classrooms': 0, 'sessions': 0,
            'attendance_rate': None, 'absence_rate': None,
            'participation_rate': None, 'performance_rate': None,
            'face_verifications': 0, 'questions_used': 0,
        }

        sf = self._school_filter()
        if school_id:
            sf &= Q(school_id=school_id)

        # Schools
        result['schools'] = self.scope.filter_schools().filter(is_active=True).count()

        # Classrooms
        cq = Classroom.objects.filter(sf)
        if grade:
            cq = cq.filter(grade=grade)
        if field:
            cq = cq.filter(field=field)
        result['classrooms'] = cq.count()

        # Students
        sq = User.objects.filter(role='student', enrolled_classes__school__district_id=self.district_id)
        if school_id:
            sq = sq.filter(enrolled_classes__school_id=school_id)
        result['students'] = sq.distinct().count()

        # Teachers
        tq = User.objects.filter(role='teacher', taught_classes__school__district_id=self.district_id)
        if school_id:
            tq = tq.filter(taught_classes__school_id=school_id)
        result['teachers'] = tq.distinct().count()

        # Sessions
        df = self._date_filter(period, date_from, date_to)
        sesq = ClassSession.objects.filter(self._classroom_filter() & df)
        if school_id:
            sesq = sesq.filter(classroom__school_id=school_id)
        result['sessions'] = sesq.count()

        # Attendance
        att = self._get_attendance_stats(period, date_from, date_to, school_id)
        result['attendance_rate'] = att.get('present_rate')
        result['absence_rate'] = att.get('absent_rate')

        # Participation
        part = self._get_participation_stats(school_id)
        result['participation_rate'] = part.get('response_rate')
        result['performance_rate'] = part.get('correct_rate')

        # Face verifications
        fq = FaceVerificationLog.objects.filter(
            student__enrolled_classes__school__district_id=self.district_id
        ).distinct()
        result['face_verifications'] = fq.count()

        # Questions used
        qq = StudentAnswer.objects.filter(
            question__classroom__school__district_id=self.district_id
        )
        result['questions_used'] = qq.count()

        return result

    # ──────────────────────────────────────────────
    #  Attendance
    # ──────────────────────────────────────────────

    def _get_attendance_stats(self, period='month', date_from=None,
                              date_to=None, school_id=None) -> Dict:
        records = AttendanceRecord.objects.filter(
            attendance_check__session__classroom__school__district_id=self.district_id
        )
        if school_id:
            records = records.filter(
                attendance_check__session__classroom__school_id=school_id)

        today = timezone.now().date()
        if period == 'today':
            records = records.filter(
                attendance_check__session__session_date__date=today)
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

    def get_attendance_trend(self, days=30, school_id=None) -> List[Dict]:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        records = AttendanceRecord.objects.filter(
            attendance_check__session__classroom__school__district_id=self.district_id,
            attendance_check__session__session_date__date__gte=start_date,
            attendance_check__session__session_date__date__lte=end_date,
        )
        if school_id:
            records = records.filter(
                attendance_check__session__classroom__school_id=school_id)

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

    # ──────────────────────────────────────────────
    #  Participation
    # ──────────────────────────────────────────────

    def _get_participation_stats(self, school_id=None) -> Dict:
        answers = StudentAnswer.objects.filter(
            question__classroom__school__district_id=self.district_id)
        questions = Question.objects.filter(
            classroom__school__district_id=self.district_id)
        if school_id:
            answers = answers.filter(question__classroom__school_id=school_id)
            questions = questions.filter(classroom__school_id=school_id)

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

    def get_participation_trend(self, days=30, school_id=None) -> List[Dict]:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        answers = StudentAnswer.objects.filter(
            question__classroom__school__district_id=self.district_id,
            answered_at__date__gte=start_date,
            answered_at__date__lte=end_date,
        )
        if school_id:
            answers = answers.filter(question__classroom__school_id=school_id)

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

    def get_performance_by_subject(self, school_id=None) -> List[Dict]:
        answers = StudentAnswer.objects.filter(
            question__classroom__school__district_id=self.district_id
        ).select_related('question__classroom')
        if school_id:
            answers = answers.filter(question__classroom__school_id=school_id)

        subjects = (
            answers
            .values(subject=F('question__classroom__subject'))
            .annotate(total=Count('id'), correct=Count('id', filter=Q(is_correct=True)))
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
    #  School Comparison
    # ──────────────────────────────────────────────

    def get_school_comparison(self) -> List[Dict]:
        schools = self.scope.filter_schools().filter(is_active=True)
        result = []
        for school in schools:
            att = AttendanceRecord.objects.filter(
                attendance_check__session__classroom__school=school)
            total_a = att.count()
            present_a = att.filter(status='present').count()

            ans = StudentAnswer.objects.filter(
                question__classroom__school=school)
            total_ans = ans.count()
            correct_ans = ans.filter(is_correct=True).count()

            sessions_count = ClassSession.objects.filter(
                classroom__school=school).count()

            result.append({
                'id': school.id,
                'name': school.name,
                'school_type': school.get_school_type_display(),
                'students': school.students_count,
                'teachers': school.teachers_count,
                'classrooms': school.classrooms_count,
                'attendance_rate': NationalAnalyticsService._safe_rate(present_a, total_a),
                'participation_rate': NationalAnalyticsService._safe_rate(total_ans, Question.objects.filter(classroom__school=school).count()),
                'performance_rate': NationalAnalyticsService._safe_rate(correct_ans, total_ans),
                'sessions': sessions_count,
            })
        return result

    # ──────────────────────────────────────────────
    #  Face Verification
    # ──────────────────────────────────────────────

    def get_face_stats(self) -> Dict:
        logs = FaceVerificationLog.objects.filter(
            student__enrolled_classes__school__district_id=self.district_id
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

    def get_ai_stats(self) -> Dict:
        jobs = AIGenerationJob.objects.filter(
            classroom__school__district_id=self.district_id)
        questions = Question.objects.filter(
            source='ai', classroom__school__district_id=self.district_id)
        return {
            'total_jobs': jobs.count(),
            'completed_jobs': jobs.filter(status='completed').count(),
            'failed_jobs': jobs.filter(status='failed').count(),
            'total_ai_questions': questions.count(),
            'approved': questions.filter(review_status='approved').count(),
            'rejected': questions.filter(review_status='rejected').count(),
            'pending': questions.filter(review_status='pending').count(),
        }

    # ──────────────────────────────────────────────
    #  System Usage
    # ──────────────────────────────────────────────

    def get_system_usage(self) -> Dict:
        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        sessions = ClassSession.objects.filter(
            classroom__school__district_id=self.district_id)
        requests = AttendanceRequest.objects.filter(
            classroom__school__district_id=self.district_id)

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

    def get_alerts(self) -> List[Dict]:
        alerts = []
        today = timezone.now().date()
        month_ago = today - timedelta(days=30)

        schools = self.scope.filter_schools().filter(is_active=True)
        for school in schools[:50]:
            has_session = ClassSession.objects.filter(
                classroom__school=school,
                session_date__date__gte=month_ago
            ).exists()
            if not has_session:
                alerts.append({
                    'type': 'inactive_school', 'severity': 'warning',
                    'scope': school.name,
                    'message': f'مدرسه «{school.name}» در ۳۰ روز گذشته فعالیتی نداشته است.',
                    'date': today,
                })

        fq = FaceVerificationLog.objects.filter(
            student__enrolled_classes__school__district_id=self.district_id,
            created_at__date__gte=month_ago,
        ).distinct()
        total_f = fq.count()
        failed_f = fq.filter(status__in=['failed', 'error']).count()
        if total_f > 10 and (failed_f / total_f) > 0.3:
            alerts.append({
                'type': 'face_errors', 'severity': 'danger',
                'scope': 'سیستم احراز هویت',
                'message': f'نرخ خطای احراز هویت چهره به {round((failed_f/total_f)*100)}% رسیده است.',
                'date': today,
            })

        return alerts

    # ──────────────────────────────────────────────
    #  School Activity
    # ──────────────────────────────────────────────

    def get_school_activity_stats(self) -> Dict:
        now = timezone.now()
        month_ago = now - timedelta(days=30)
        schools = self.scope.filter_schools().filter(is_active=True)
        total = schools.count()
        active_schools = 0
        inactive_names = []

        for school in schools:
            has_session = ClassSession.objects.filter(
                classroom__school=school,
                session_date__date__gte=month_ago.date(),
            ).exists()
            if has_session:
                active_schools += 1
            else:
                inactive_names.append(school.name)

        return {
            'total': total,
            'active': active_schools,
            'inactive': total - active_schools,
            'inactive_names': inactive_names[:20],
        }

    # ──────────────────────────────────────────────
    #  Recent Activity
    # ──────────────────────────────────────────────

    def get_recent_activity(self, limit=10) -> List[Dict]:
        activities = []

        sessions_qs = ClassSession.objects.filter(
            classroom__school__district_id=self.district_id
        ).select_related('classroom', 'classroom__school').order_by('-session_date')[:limit]
        for session in sessions_qs:
            activities.append({
                'type': 'session',
                'icon': 'bi-calendar-event-fill',
                'title': f'جلسه جدید در {session.classroom.name}',
                'description': session.topic or 'بدون موضوع',
                'date': session.session_date,
            })

        requests_qs = AttendanceRequest.objects.filter(
            classroom__school__district_id=self.district_id
        ).select_related('classroom', 'teacher').order_by('-created_at')[:limit]
        for req in requests_qs:
            activities.append({
                'type': 'attendance_request',
                'icon': 'bi-person-check-fill',
                'title': f'درخواست {req.get_request_type_display()}',
                'description': f'{req.classroom.name} - {req.teacher.get_full_name()}',
                'date': req.created_at,
            })

        activities.sort(key=lambda x: x['date'], reverse=True)
        return activities[:limit]

    # ──────────────────────────────────────────────
    #  Schools List (with pagination support)
    # ──────────────────────────────────────────────

    def get_schools_list(self, school_id=None) -> List[Dict]:
        schools = self.scope.filter_schools().filter(is_active=True).select_related(
            'district', 'district__province'
        ).annotate(classrooms_count=Count('classrooms', distinct=True))
        if school_id:
            schools = schools.filter(id=school_id)

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
    #  Class Analytics for a School
    # ──────────────────────────────────────────────

    def get_class_analytics(self, school_id) -> List[Dict]:
        classrooms = Classroom.objects.filter(
            school_id=school_id,
            school__district_id=self.district_id,
        ).select_related('teacher').annotate(
            students_count=Count('students', distinct=True),
            sessions_count=Count('sessions', distinct=True),
        )

        result = []
        for c in classrooms:
            att = AttendanceRecord.objects.filter(
                attendance_check__session__classroom=c)
            total_a = att.count()
            present_a = att.filter(status='present').count()

            ans = StudentAnswer.objects.filter(question__classroom=c)
            total_ans = ans.count()
            correct_ans = ans.filter(is_correct=True).count()

            result.append({
                'id': c.id,
                'name': c.name,
                'subject': c.subject,
                'grade': c.get_grade_display(),
                'field': c.get_field_display(),
                'teacher_name': c.teacher_name,
                'students_count': c.students_count,
                'sessions_count': c.sessions_count,
                'attendance_rate': NationalAnalyticsService._safe_rate(present_a, total_a),
                'participation_rate': NationalAnalyticsService._safe_rate(
                    total_ans, Question.objects.filter(classroom=c).count()),
                'performance_rate': NationalAnalyticsService._safe_rate(correct_ans, total_ans),
            })
        return result