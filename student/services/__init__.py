"""
سرویس‌های ماژول دانش‌آموز.
فقط ایمپورت‌ها — کد اصلی در فایل‌های جداگانه است.
"""
from .dashboard_service import StudentDashboardService, StudentStatusService
from .assessment_service import StudentAssessmentService
from .homework_service import StudentHomeworkService
from .request_service import StudentRequestService

__all__ = [
    'StudentDashboardService',
    'StudentStatusService',
    'StudentAssessmentService',
    'StudentHomeworkService',
    'StudentRequestService',
]