"""سرویس ثبت لاگ عملیات مسئول کشوری"""
import logging
from .models import NationalAuditLog

logger = logging.getLogger(__name__)


class AuditService:
    @staticmethod
    def log(request, action, scope='national', scope_id=None,
            scope_name='', details=None):
        try:
            NationalAuditLog.objects.create(
                user=request.user,
                action=action,
                scope=scope,
                scope_id=scope_id,
                scope_name=scope_name,
                details=details or {},
                ip_address=AuditService._get_ip(request),
            )
        except Exception as e:
            logger.error(f'Failed to write audit log: {e}')

    @staticmethod
    def _get_ip(request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')