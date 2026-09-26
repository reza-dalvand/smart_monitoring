"""سرویس داشبورد دانش‌آموز"""
import logging
from typing import Dict, Any
from django.db.models import Avg
from django.utils import timezone

from ..scope import StudentScope
from ..constants import EducationalStatusLevel, DEFAULT_THRESHOLDS

logger = logging.getLogger(__name__)


class StudentDashboardService:
    """محاسبه داده‌های داشبورد دانش‌آموز"""

    def __init__(self, scope: StudentScope):
        self.scope = scope
        self.student = scope.student

    def _safe_rate(self, numerator, denominator, digits=1):
        if not denominator:
            return None
        return round((numerator / denominator) * 100, digits)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """دریافت تمام داده‌های داشبورد در یک فراخوانی بهینه"""
        result = {
            'attendance_rate': None,
            'participation_rate': None,
            'performance_rate': None,
            'homework_completion_rate': None,
            'active_assessments_count': 0,
            'active_homeworks_count': 0,
            'active_requests_count': 0,
            'next_session': None,
            'educational_status': EducationalStatusLevel.NORMAL,
            'status_reasons': [],
            'classes_count': 0,
        }

        # ── Attendance ──
        att_responses = self.scope.filter_attendance_responses()
        total_att = att_responses.count()
        if total_att > 0:
            present = att_responses.filter(final_status='present').count()
            result['attendance_rate'] = self._safe_rate(present, total_att)

        # ── Participation ──
        from teacher.models import ParticipationRecord
        part_records = self.scope.filter_participation_records()
        total_part = part_records.count()
        if total_part > 0:
            avg_score = part_records.aggregate(avg=Avg('score'))['avg']
            result['participation_rate'] = round(avg_score, 1) if avg_score else None

        # ── Performance (Questions) ──
        answers = self.scope.filter_student_answers()
        total_answers = answers.count()
        if total_answers > 0:
            correct = answers.filter(is_correct=True).count()
            result['performance_rate'] = self._safe_rate(correct, total_answers)

        # ── Homework ──
        from teacher.models import Homework
        active_hw = self.scope.filter_homeworks().filter(status='active')
        result['active_homeworks_count'] = active_hw.count()
        total_hw = self.scope.filter_homeworks().count()
        if total_hw > 0:
            submitted = self.scope.filter_homework_submissions().exclude(
                status='not_submitted'
            ).count()
            result['homework_completion_rate'] = self._safe_rate(submitted, total_hw)

        # ── Assessments ──
        from teacher.models import Assessment
        active_assessments = self.scope.filter_assessments().filter(
            status__in=['published', 'in_progress']
        )
        result['active_assessments_count'] = active_assessments.count()

        # ── Classes ──
        result['classes_count'] = self.scope.filter_classes().count()

        # ── Requests ──
        result['active_requests_count'] = self.scope.filter_student_requests().filter(
            status__in=['OPEN', 'IN_REVIEW', 'NEEDS_INFO']
        ).count()

        # ── Next Session ──
        now = timezone.now()
        next_session = self.scope.filter_sessions().filter(
            session_date__gte=now
        ).order_by('session_date').select_related('classroom').first()
        result['next_session'] = next_session

        # ── Educational Status ──
        status, reasons = self._calculate_educational_status(result)
        result['educational_status'] = status
        result['status_reasons'] = reasons

        return result

    def _calculate_educational_status(self, data: Dict) -> tuple:
        """محاسبه وضعیت آموزشی بر اساس Ruleهای سیستم"""
        thresholds = self._get_thresholds()
        reasons = []

        if data['attendance_rate'] is not None:
            if data['attendance_rate'] < thresholds['attendance_min']:
                reasons.append(
                    f"حضور {data['attendance_rate']}٪ "
                    f"(کمتر از {thresholds['attendance_min']:.0f}٪)"
                )

        if data['participation_rate'] is not None:
            if data['participation_rate'] < thresholds['participation_min']:
                reasons.append(
                    f"مشارکت {data['participation_rate']} "
                    f"(کمتر از {thresholds['participation_min']:.0f})"
                )

        if data['performance_rate'] is not None:
            score_20 = data['performance_rate'] / 5
            if score_20 < thresholds['assessment_min']:
                reasons.append(
                    f"عملکرد تقریبی {score_20:.1f} از ۲۰ "
                    f"(کمتر از {thresholds['assessment_min']:.0f})"
                )

        if data['homework_completion_rate'] is not None:
            if data['homework_completion_rate'] < thresholds['homework_min']:
                reasons.append(
                    f"انجام تکالیف {data['homework_completion_rate']}٪ "
                    f"(کمتر از {thresholds['homework_min']:.0f}٪)"
                )

        if len(reasons) >= 2:
            return EducationalStatusLevel.NEEDS_ATTENTION, reasons
        elif len(reasons) == 1:
            return EducationalStatusLevel.UNDER_OBSERVATION, reasons
        return EducationalStatusLevel.NORMAL, []

    def _get_thresholds(self) -> Dict:
        """دریافت آستانه‌ها از تنظیمات مدرسه"""
        try:
            classrooms = self.scope.filter_classes().filter(school__isnull=False)
            if classrooms.exists():
                school = classrooms.first().school
                settings_obj = school.settings
                return {
                    'attendance_min': settings_obj.absence_warning_threshold,
                    'participation_min': settings_obj.participation_warning_threshold,
                    'assessment_min': settings_obj.performance_warning_threshold / 5,
                    'homework_min': 60.0,
                }
        except Exception:
            pass
        return DEFAULT_THRESHOLDS.copy()


class StudentStatusService:
    """سرویس وضعیت آموزشی دانش‌آموز"""

    def __init__(self, scope: StudentScope):
        self.scope = scope
        self.dashboard_service = StudentDashboardService(scope)

    def get_full_status(self) -> Dict:
        """دریافت وضعیت کامل آموزشی"""
        data = self.dashboard_service.get_dashboard_data()
        return {
            'attendance_rate': data['attendance_rate'],
            'participation_rate': data['participation_rate'],
            'performance_rate': data['performance_rate'],
            'homework_completion_rate': data['homework_completion_rate'],
            'educational_status': data['educational_status'],
            'status_reasons': data['status_reasons'],
            'classes_count': data['classes_count'],
        }