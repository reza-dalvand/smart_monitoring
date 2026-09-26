"""سرویس درخواست‌های دانش‌آموز"""
from ..scope import StudentScope
from ..constants import StudentRequestStatus


class StudentRequestService:
    """سرویس درخواست‌های دانش‌آموز"""

    def __init__(self, scope: StudentScope):
        self.scope = scope

    def create_request(self, request_type, title, description,
                       priority='MEDIUM', **related_objects):
        """ایجاد درخواست جدید"""
        from ..models import StudentRequest

        return StudentRequest.objects.create(
            student=self.scope.student,
            request_type=request_type,
            title=title,
            description=description,
            priority=priority,
            **related_objects,
        )

    def cancel_request(self, request_obj) -> bool:
        """لغو درخواست (فقط در وضعیت OPEN)"""
        if not request_obj.is_cancellable:
            return False
        request_obj.status = StudentRequestStatus.CANCELLED
        request_obj.save(update_fields=['status', 'updated_at'])
        return True