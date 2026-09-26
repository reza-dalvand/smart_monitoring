"""سرویس ثبت لاگ عملیات مدرسه"""
import logging

logger = logging.getLogger(__name__)


class SchoolAuditService:
    @staticmethod
    def log(request, school, action, object_type='', object_id='',
            old_values=None, new_values=None, reason='',
            classroom=None, obj=None, details=None):
        """
        ✅ اصلاح شد: پارامترهای obj و details اضافه شدند
        """
        try:
            from .models import SchoolAuditLog
            SchoolAuditLog.objects.create(
                actor=request.user,
                school=school,
                action=action,
                object_type=object_type or (type(obj).__name__ if obj else ''),
                object_id=str(object_id or (obj.pk if obj else '')),
                old_values=old_values or {},
                new_values=new_values or {},
                reason=reason or (details if details else ''),
                ip_address=SchoolAuditService._get_ip(request),
            )
        except Exception as e:
            logger.error('School audit log failed: %s', e)

    @staticmethod
    def _get_ip(request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')