"""
سرویس تحلیلی مسئول استانی

این سرویس از NationalAnalyticsService موجود استفاده می‌کند
و لایه اجبار محدوده (Scope) را اضافه می‌نماید.
هیچ منطق تحلیلی تکراری نوشته نمی‌شود.
"""
import logging
from typing import Optional, Dict, Any, List

from django.db.models import Count, Q, Avg
from django.utils import timezone

from national.services import NationalAnalyticsService
from national.models import District, School
from dashboard.models import Classroom, ClassSession, StudentAnswer, AttendanceRequest
from face.models import FaceVerificationLog
from dashboard.models import AIGenerationJob, Question

from .scope import ProvinceScope

logger = logging.getLogger(__name__)


class ProvinceAnalyticsService:
    """
    تمام متدها اجباراً با ProvinceScope کار می‌کنند.
    View نمی‌تواند province را جعل کند.
    """

    def __init__(self, scope: ProvinceScope):
        self.scope = scope
        self.pid = scope.province_id

    # ──────────────────────────────────────────────
    #  Overview KPIs
    # ──────────────────────────────────────────────

    def get_overview(self, district_id=None, period='month',
                     date_from=None, date_to=None) -> Dict[str, Any]:
        """KPIهای اصلی استان/منطقه"""
        return NationalAnalyticsService.get_overview(
            scope='province',
            province_id=self.pid,
            period=period,
            date_from=date_from,
            date_to=date_to,
        )

    # ──────────────────────────────────────────────
    #  District Comparison
    # ──────────────────────────────────────────────

    def get_district_comparison(self) -> List[Dict]:
        """مقایسه مناطق استان (فقط مناطق خود استان)"""
        districts = self.scope.filter_districts().filter(is_active=True)
        result = []
        for district in districts:
            att = NationalAnalyticsService._get_attendance_stats(
                'province', self.pid, 'month')
            part = NationalAnalyticsService._get_participation_stats(
                'province', self.pid)

            schools_count = School.objects.filter(
                district=district, is_active=True).count()
            students_count = Classroom.objects.filter(
                school__district=district
            ).values('students').distinct().count()

            result.append({
                'id': district.id,
                'name': district.name,
                'schools': schools_count,
                'students': students_count,
                'attendance_rate': att.get('present_rate'),
                'participation_rate': part.get('response_rate'),
                'performance_rate': part.get('correct_rate'),
            })
        return result

    # ──────────────────────────────────────────────
    #  Attendance Analytics
    # ──────────────────────────────────────────────

    def get_attendance_trend(self, days=30) -> List[Dict]:
        return NationalAnalyticsService.get_attendance_trend(
            'province', self.pid, days)

    def get_attendance_status(self) -> Dict:
        return NationalAnalyticsService.get_attendance_status_breakdown(
            'province', self.pid)

    # ──────────────────────────────────────────────
    #  Participation Analytics
    # ──────────────────────────────────────────────

    def get_participation_trend(self, days=30) -> List[Dict]:
        return NationalAnalyticsService.get_participation_trend(
            'province', self.pid, days)

    def get_performance_by_subject(self) -> List[Dict]:
        return NationalAnalyticsService.get_performance_by_subject(
            'province', self.pid)

    # ──────────────────────────────────────────────
    #  Face Verification Analytics
    # ──────────────────────────────────────────────

    def get_face_stats(self) -> Dict:
        return NationalAnalyticsService.get_face_verification_stats(
            'province', self.pid)

    # ──────────────────────────────────────────────
    #  AI Analytics
    # ──────────────────────────────────────────────

    def get_ai_stats(self) -> Dict:
        return NationalAnalyticsService.get_ai_stats('province', self.pid)

    # ──────────────────────────────────────────────
    #  System Usage
    # ──────────────────────────────────────────────

    def get_system_usage(self) -> Dict:
        return NationalAnalyticsService.get_system_usage('province', self.pid)

    # ──────────────────────────────────────────────
    #  Alerts
    # ──────────────────────────────────────────────

    def get_alerts(self) -> List[Dict]:
        return NationalAnalyticsService.get_alerts('province', self.pid)

    # ──────────────────────────────────────────────
    #  Schools List (در محدوده استان)
    # ──────────────────────────────────────────────

    def get_schools_list(self, district_id=None) -> List[Dict]:
        return NationalAnalyticsService.get_schools_list(
            'province', self.pid, district_id)

    # ──────────────────────────────────────────────
    #  Recent Activity
    # ──────────────────────────────────────────────

    def get_recent_activity(self, limit=10) -> List[Dict]:
        return NationalAnalyticsService.get_recent_activity(
            'province', self.pid, limit)

    # ──────────────────────────────────────────────
    #  School Activity Analytics
    # ──────────────────────────────────────────────

    def get_school_activity_stats(self) -> Dict:
        """وضعیت فعالیت مدارس استان"""
        now = timezone.now()
        month_ago = now - timezone.timedelta(days=30)

        schools = self.scope.filter_schools().filter(is_active=True)
        total = schools.count()

        active_schools = 0
        inactive_schools = []
        for school in schools:
            has_session = ClassSession.objects.filter(
                classroom__school=school,
                session_date__date__gte=month_ago.date(),
            ).exists()
            if has_session:
                active_schools += 1
            else:
                inactive_schools.append(school.name)

        return {
            'total': total,
            'active': active_schools,
            'inactive': total - active_schools,
            'inactive_names': inactive_schools[:20],
        }