import logging

logger = logging.getLogger(__name__)


class DistrictAuditService:
    """ثبت لاگ فعالیت‌های مسئول منطقه (بدون ایجاد مدل تکراری)"""

    @staticmethod
    def log(request, action, scope_name='', details=None):
        try:
            from national.models import NationalAuditLog
            NationalAuditLog.objects.create(
                user=request.user,
                action=action,
                scope='district',
                scope_id=request.user.district.id,
                scope_name=scope_name or request.user.district.name,
                details=details or {},
                ip_address=DistrictAuditService._get_ip(request),
            )
        except Exception as e:
            logger.error('District audit log failed: %s', e)

    @staticmethod
    def _get_ip(request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')