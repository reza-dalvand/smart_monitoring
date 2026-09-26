"""
سرویس احراز هویت چهره برای پنل دانش‌آموز.
وظیفه: پیدا کردن درخواست‌های فعال احراز هویت و آماده‌سازی داده برای مودال.
"""
from typing import Dict, List, Any
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from dashboard.models import AttendanceRequest, AttendanceResponse
from face.models import FaceProfile, FaceEmbedding


class StudentFaceService:
    """
    سرویس مدیریت احراز هویت چهره دانش‌آموز.
    """

    def __init__(self, scope):
        self.scope = scope
        self.student = scope.student

    def get_active_face_requests(self) -> List[Dict[str, Any]]:
        """درخواست‌های فعال احراز هویت + وضعیت فعلی دانش‌آموز."""
        active_requests = self.scope.filter_attendance_requests().filter(
            status='active',
            request_type__in=['face_only', 'face_and_question'],
        ).filter(
            Q(face_deadline_at__isnull=True) |
            Q(face_deadline_at__gt=timezone.now())
        ).select_related(
            'classroom', 'session', 'teacher'
        ).order_by('-created_at')

        items = []
        for req in active_requests:
            response = AttendanceResponse.objects.filter(
                attendance_request=req,
                student=self.student,
            ).first()

            already_verified = bool(
                response
                and response.face_verified
                and response.final_status == 'present'
            )

            max_attempts = getattr(settings, 'FACE_MAX_ATTEMPTS', 3)
            attempts_exhausted = bool(
                response and response.attempts >= max_attempts
            )

            expired = bool(req.is_face_expired)

            items.append({
                'request': req,
                'response': response,
                'already_verified': already_verified,
                'attempts_exhausted': attempts_exhausted,
                'expired': expired,
                'can_scan': not already_verified and not attempts_exhausted and not expired,
                'max_attempts': max_attempts,
                'attempts_used': response.attempts if response else 0,
            })

        return items

    def get_face_enrollment_status(self) -> Dict[str, Any]:
        """وضعیت ثبت چهره دانش‌آموز"""
        face_profile = None
        try:
            face_profile = self.student.face_profile
        except Exception:
            pass

        embeddings_count = FaceEmbedding.objects.filter(
            student=self.student,
            is_active=True,
        ).count()

        min_ref = getattr(settings, 'FACE_MIN_REFERENCE_IMAGES', 3)

        return {
            'face_profile': face_profile,
            'embeddings_count': embeddings_count,
            'min_reference': min_ref,
            'is_enrolled': embeddings_count >= min_ref,
        }

    def get_active_face_count(self) -> int:
        """تعداد درخواست‌های فعال که نیاز به اسکن دارند"""
        items = self.get_active_face_requests()
        return sum(1 for item in items if item['can_scan'])