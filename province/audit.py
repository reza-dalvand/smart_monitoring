import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class ProvinceAuditService:
    """ثبت لاگ فعالیت‌های مسئول استانی (بدون ایجاد مدل تکراری)"""

    @staticmethod
    def log(request, action, scope_name='', details=None):
        try:
            from national.models import NationalAuditLog
            NationalAuditLog.objects.create(
                user=request.user,
                action=action,
                scope='province',
                scope_id=request.user.province.id,
                scope_name=scope_name or request.user.province.name,
                details=details or {},
                ip_address=ProvinceAuditService._get_ip(request),
            )
        except Exception as e:
            logger.error('Province audit log failed: %s', e)

    @staticmethod
    def _get_ip(request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')