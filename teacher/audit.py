"""
ثبت لاگ عملیات معلم.
از SchoolAuditLog موجود استفاده می‌شود.
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class TeacherAuditService:
    """
    ثبت لاگ عملیات حساس معلم.
    از مدل موجود SchoolAuditLog استفاده می‌کند.
    """

    @staticmethod
    def log(request, action, object_type='', object_id='',
            old_values=None, new_values=None, reason='',
            classroom=None):
        try:
            from school.models import SchoolAuditLog
            from teacher.scope import TeacherScope

            scope = getattr(request, 'teacher_scope', None)
            school = None
            if scope and classroom:
                school = classroom.school
            elif scope:
                classes = scope.filter_classes().filter(
                    school__isnull=False
                )
                if classes.exists():
                    school = classes.first().school

            SchoolAuditLog.objects.create(
                actor=request.user,
                school=school,
                action=action,
                object_type=object_type,
                object_id=str(object_id),
                old_values=old_values or {},
                new_values=new_values or {},
                reason=reason,
                ip_address=TeacherAuditService._get_ip(request),
            )
        except Exception as e:
            logger.error('Teacher audit log failed: %s', e)

    @staticmethod
    def _get_ip(request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')