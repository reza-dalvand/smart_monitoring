"""
سرویس‌های تحلیلی و مدیریتی مدرسه
الگوی مشابه: district/services.py و national/services.py
"""
import logging
from datetime import timedelta
from typing import Optional, Dict, Any, List

from django.db.models import Count, Q, Avg, F
from django.db.models.functions import TruncDate
from django.utils import timezone

from accounts.models import User
from dashboard.models import (
    Classroom, ClassSession, AttendanceRecord,
    AttendanceRequest, AttendanceResponse,
    Question, StudentAnswer, WeeklySchedule,
)
from face.models import FaceVerificationLog
from national.models import School
from national.services import NationalAnalyticsService

from .scope import SchoolScope
from .models import (
    SchoolStaffAssignment, FollowUpCase, SchoolAlert,
    SchoolTask, SchoolSettings, StudentSchoolStatus,
    AbsenceReview,
)
from .constants import (
    StaffRole, AssistantType, CaseStatus, CasePriority,
    AlertType, AlertSeverity, StudentStatus, TaskStatus,
    AbsenceReviewStatus,
)

logger = logging.getLogger(__name__)


class SchoolAnalyticsService:
    """محاسبه KPIها و آمار مدرسه"""

    def __init__(self, scope: SchoolScope):
        self.scope = scope
        self.school = scope.active_school
        self.school_id = self.school.id if self.school else None

    def _safe_rate(self, numerator, denominator, digits=1):
        if not denominator:
            return None
        return round((numerator / denominator) * 100, digits)

    # ──────────────────────────────────────────────
    #  Overview KPIs
    # ──────────────────────────────────────────────
    def get_overview(self) -> Dict[str, Any]:
        today = timezone.now().date()
        result = {
            'total_students': 0,
            'total_teachers': 0,
            'total_classes': 0,
            'present_today': 0,
            'absent_today': 0,
            'pending_attendance': 0,
            'suspicious_attendance': 0,
            'active_classes': 0,
            'completed_sessions': 0,
            'active_teachers': 0,
            'students_needing_followup': 0,
            'low_participation_classes': 0,
            'open_cases': 0,
            'pending_tasks': 0,
        }

        if not self.school_id:
            return result

        # Students
        result['total_students'] = self.scope.filter_students().count()

        # Teachers
        result['total_teachers'] = self.scope.filter_teachers().count()

        # Classes
        classrooms = self.scope.filter_classrooms()
        result['total_classes'] = classrooms.count()
        result['active_classes'] = classrooms.filter(sessions__isnull=False).distinct().count()


        # Today's Attendance
        today_responses = AttendanceResponse.objects.filter(
            attendance_request__classroom__school_id=self.school_id,
            attendance_request__created_at__date=today,
        )
        result['present_today'] = today_responses.filter(
            final_status='present').count()
        result['absent_today'] = today_responses.filter(
            final_status='absent').count()
        result['pending_attendance'] = today_responses.filter(
            final_status='pending').count()
        result['suspicious_attendance'] = today_responses.filter(
            auto_status='suspicious').count()

        # Sessions
        sessions = self.scope.filter_sessions()
        result['completed_sessions'] = sessions.count()

        # Follow-ups
        result['open_cases'] = FollowUpCase.objects.filter(
            school_id=self.school_id,
            status__in=['OPEN', 'IN_REVIEW', 'ASSIGNED'],
        ).count()

        # Tasks
        result['pending_tasks'] = SchoolTask.objects.filter(
            school_id=self.school_id,
            status__in=['TODO', 'IN_PROGRESS'],
        ).count()

        return result

    # ──────────────────────────────────────────────
    #  Attendance Analytics
    # ──────────────────────────────────────────────
    def get_attendance_stats(self, period='month') -> Dict:
        records = AttendanceRecord.objects.filter(
            attendance_check__session__classroom__school_id=self.school_id
        )
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

        total = records.count()
        if total == 0:
            return {'present_rate': None, 'absent_rate': None,
                    'total': 0, 'present': 0, 'absent': 0}

        present = records.filter(status='present').count()
        absent = records.filter(status='absent').count()
        return {
            'present_rate': self._safe_rate(present, total),
            'absent_rate': self._safe_rate(absent, total),
            'total': total, 'present': present, 'absent': absent,
        }

    def get_attendance_trend(self, days=30) -> List[Dict]:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        records = AttendanceRecord.objects.filter(
            attendance_check__session__classroom__school_id=self.school_id,
            attendance_check__session__session_date__date__gte=start_date,
            attendance_check__session__session_date__date__lte=end_date,
        )
        daily = (
            records
            .annotate(date=TruncDate('attendance_check__session__session_date'))
            .values('date')
            .annotate(total=Count('id'),
                      present=Count('id', filter=Q(status='present')))
            .order_by('date')
        )
        return [
            {
                'date': str(d['date']),
                'rate': self._safe_rate(d['present'], d['total']),
                'total': d['total'],
                'present': d['present'],
            }
            for d in daily
        ]

    # ──────────────────────────────────────────────
    #  Participation Analytics
    # ──────────────────────────────────────────────
    def get_participation_stats(self) -> Dict:
        answers = StudentAnswer.objects.filter(
            question__classroom__school_id=self.school_id)
        questions = Question.objects.filter(
            classroom__school_id=self.school_id)
        total_answers = answers.count()
        total_qs = questions.count()
        correct = answers.filter(is_correct=True).count()
        return {
            'response_rate': self._safe_rate(total_answers, total_qs),
            'correct_rate': self._safe_rate(correct, total_answers),
            'total_answers': total_answers,
            'total_questions': total_qs,
            'correct': correct,
        }

    # ──────────────────────────────────────────────
    #  Student Risk Detection (Rule-based)
    # ──────────────────────────────────────────────
    def get_students_needing_attention(self) -> List[Dict]:
        """تشخیص دانش‌آموزان نیازمند توجه با قوانین ساده"""
        settings = self._get_school_settings()
        absence_threshold = settings.absence_warning_threshold
        participation_threshold = settings.participation_warning_threshold

        students = self.scope.filter_students()
        result = []

        for student in students[:200]:  # محدود کردن برای عملکرد
            reasons = []

            # بررسی غیبت
            att_records = AttendanceRecord.objects.filter(
                student=student,
                attendance_check__session__classroom__school_id=self.school_id,
            )
            total_att = att_records.count()
            if total_att > 0:
                absent_count = att_records.filter(status='absent').count()
                absence_rate = (absent_count / total_att) * 100
                if absence_rate > absence_threshold:
                    reasons.append(f'نرخ غیبت {absence_rate:.0f}٪')

            # بررسی مشارکت
            answers = StudentAnswer.objects.filter(
                student=student,
                question__classroom__school_id=self.school_id,
            )
            total_questions = Question.objects.filter(
                classroom__school_id=self.school_id,
                classroom__students=student,
            ).count()
            if total_questions > 0:
                participation_rate = (answers.count() / total_questions) * 100
                if participation_rate < participation_threshold:
                    reasons.append(f'مشارکت {participation_rate:.0f}٪')

            # بررسی احراز هویت
            face_failures = FaceVerificationLog.objects.filter(
                student=student,
                status__in=['failed', 'error'],
            ).count()
            if face_failures >= 3:
                reasons.append(f'{face_failures} خطای احراز هویت')

            if reasons:
                result.append({
                    'student': student,
                    'reasons': reasons,
                    'risk_level': 'HIGH' if len(reasons) >= 2 else 'MEDIUM',
                })

        return result

    # ──────────────────────────────────────────────
    #  Alert Generation
    # ──────────────────────────────────────────────
    def generate_alerts(self) -> List[Dict]:
        """تولید هشدارها از داده‌های واقعی"""
        alerts = []
        today = timezone.now().date()
        month_ago = today - timedelta(days=30)

        # 1) کلاس بدون ثبت حضور امروز
        classrooms = self.scope.filter_classrooms()
        for classroom in classrooms:
            has_today = AttendanceRequest.objects.filter(
                classroom=classroom,
                created_at__date=today,
            ).exists()
            if not has_today and classroom.sessions.exists():
                alerts.append({
                    'type': AlertType.NO_ATTENDANCE_RECORDED,
                    'severity': AlertSeverity.WARNING,
                    'title': f'کلاس {classroom.name} امروز حضور و غیاب ندارد',
                    'classroom': classroom,
                })

        # 2) حضور مشکوک
        suspicious = AttendanceResponse.objects.filter(
            attendance_request__classroom__school_id=self.school_id,
            auto_status='suspicious',
            final_status='pending',
        ).select_related('student', 'attendance_request__classroom')
        for resp in suspicious[:10]:
            alerts.append({
                'type': AlertType.SUSPICIOUS_ATTENDANCE,
                'severity': AlertSeverity.CRITICAL,
                'title': f'حضور مشکوک: {resp.student.get_full_name()}',
                'student': resp.student,
                'classroom': resp.attendance_request.classroom,
            })

        # 3) پرونده‌های باز
        open_cases = FollowUpCase.objects.filter(
            school_id=self.school_id,
            status__in=['OPEN', 'IN_REVIEW'],
        ).count()
        if open_cases > 5:
            alerts.append({
                'type': AlertType.UNRESOLVED_FOLLOWUP,
                'severity': AlertSeverity.WARNING,
                'title': f'{open_cases} پرونده پیگیری باز وجود دارد',
            })

        return alerts

    # ──────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────
    def _get_school_settings(self) -> SchoolSettings:
        settings_obj, _ = SchoolSettings.objects.get_or_create(
            school=self.school
        )
        return settings_obj


class FollowUpService:
    """سرویس مدیریت پرونده‌های پیگیری"""

    def __init__(self, scope: SchoolScope):
        self.scope = scope
        self.school = scope.active_school

    def create_case(self, request, title, description='',
                    student=None, classroom=None,
                    category='OTHER', priority='MEDIUM') -> FollowUpCase:
        from django.db import transaction
        with transaction.atomic():
            case = FollowUpCase.objects.create(
                school=self.school,
                student=student,
                classroom=classroom,
                created_by=request.user,
                title=title,
                description=description,
                category=category,
                priority=priority,
                status='OPEN',
            )
            from .audit import SchoolAuditService
            SchoolAuditService.log(
                request, self.school, 'followup_creation',
                object_type='FollowUpCase',
                object_id=case.case_number,
                new_values={'title': title, 'priority': priority},
            )
        return case

    def assign_case(self, request, case, assigned_to) -> FollowUpCase:
        from django.db import transaction
        with transaction.atomic():
            case.assigned_to = assigned_to
            case.status = 'ASSIGNED'
            case.save(update_fields=['assigned_to', 'status', 'updated_at'])
            from .audit import SchoolAuditService
            SchoolAuditService.log(
                request, self.school, 'followup_assignment',
                object_type='FollowUpCase',
                object_id=case.case_number,
                new_values={'assigned_to': assigned_to.username},
            )
        return case

    def resolve_case(self, request, case, resolution_note='') -> FollowUpCase:
        from django.db import transaction
        with transaction.atomic():
            case.status = 'RESOLVED'
            case.resolved_at = timezone.now()
            case.resolution_note = resolution_note
            case.save(update_fields=[
                'status', 'resolved_at', 'resolution_note', 'updated_at'
            ])
            from .audit import SchoolAuditService
            SchoolAuditService.log(
                request, self.school, 'followup_resolution',
                object_type='FollowUpCase',
                object_id=case.case_number,
                new_values={'status': 'RESOLVED'},
                reason=resolution_note,
            )
        return case

    def escalate_case(self, request, case) -> FollowUpCase:
        case.escalated = True
        case.status = 'IN_REVIEW'
        case.save(update_fields=['escalated', 'status', 'updated_at'])
        return case


class AttendanceOverrideService:
    """سرویس تغییر وضعیت حضور توسط مدیر"""

    def __init__(self, scope: SchoolScope):
        self.scope = scope
        self.school = scope.active_school

    def override_attendance_response(self, request, response, new_status, reason):
        from django.db import transaction
        from .models import AttendanceOverrideLog
        from .audit import SchoolAuditService

        with transaction.atomic():
            old_status = response.final_status

            # ثبت Override Log
            AttendanceOverrideLog.objects.create(
                school=self.school,
                attendance_response=response,
                student=response.student,
                old_status=old_status,
                new_status=new_status,
                reason=reason,
                overridden_by=request.user,
            )

            # تغییر وضعیت
            response.final_status = new_status
            response.reviewed_by = request.user
            response.reviewed_at = timezone.now()
            response.save(update_fields=[
                'final_status', 'reviewed_by', 'reviewed_at', 'updated_at'
            ])

            # Audit
            SchoolAuditService.log(
                request, self.school, 'attendance_override',
                object_type='AttendanceResponse',
                object_id=response.id,
                old_values={'final_status': old_status},
                new_values={'final_status': new_status},
                reason=reason,
            )
        return response