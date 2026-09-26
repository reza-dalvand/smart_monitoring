"""سرویس تکالیف دانش‌آموز"""
from django.utils import timezone

from ..scope import StudentScope


class StudentHomeworkService:
    """سرویس تکالیف دانش‌آموز"""

    def __init__(self, scope: StudentScope):
        self.scope = scope

    def get_or_create_submission(self, homework):
        """دریافت یا ایجاد ارسال برای تکلیف"""
        from teacher.models import HomeworkSubmission

        submission, created = HomeworkSubmission.objects.get_or_create(
            homework=homework,
            student=self.scope.student,
            defaults={'status': 'not_submitted'},
        )
        return submission, created

    def can_submit(self, homework) -> bool:
        """بررسی امکان ارسال"""
        now = timezone.now()
        if homework.status != 'active':
            return False
        if homework.deadline < now:
            return False
        return True

    def is_late(self, homework) -> bool:
        """بررسی تأخیر"""
        return timezone.now() > homework.deadline