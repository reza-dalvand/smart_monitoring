"""
سرویس مرکزی احراز هویت چهره برای حضور و غیاب

این سرویس مسئول هماهنگ‌سازی کامل فرآیند است:
1. اعتبارسنجی درخواست حضور
2. بررسی مجوز دانش‌آموز
3. بررسی ثبت چهره
4. اعتبارسنجی فریم‌ها
5. فراخوانی سرویس چهره
6. ذخیره نتیجه در AttendanceResponse
7. ثبت لاگ
"""
import logging
import time
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from face.constants import FaceStatus, LivenessStatus, MatchDecision
from face.models import FaceEmbedding, FaceVerificationLog
from dashboard.models import AttendanceResponse

from .service import FaceRecognitionService
from .exceptions import (
    FaceServiceError,
    LivenessFailedError,
    FaceNotFoundError,
    MultipleFacesDetectedError,
    LowQualityFaceError,
    InvalidFramesError,
    AttendanceNotActiveError,
    AttendanceNotForStudentError,
    EnrollmentRequiredError,
    TooManyAttemptsError,
    FaceDeadlineExpiredError,
    ModelNotAvailableError,
)

logger = logging.getLogger(__name__)


class AttendanceFaceVerificationService:
    """
    این کلاس تنها نقطه‌ای است که باید برای احراز هویت حضور استفاده شود.
    View فقط باید این سرویس را صدا بزند.
    """

    def __init__(self, face_service=None):
        self.face_service = face_service or FaceRecognitionService.get_instance()

    @transaction.atomic
    def verify_attendance(
        self,
        student,
        attendance_request,
        frames,
        session=None,
        challenge_result=None,
    ):
        if not getattr(settings, 'FACE_AI_ENABLED', True):
            raise ModelNotAvailableError('سرویس هوش مصنوعی فعال نیست.')

        started = time.monotonic()

        def processing_ms():
            return int((time.monotonic() - started) * 1000)

        logger.info(
            'verification_started student_id=%s attendance_request_id=%s session_id=%s',
            student.id,
            attendance_request.id,
            session.session_id if session else None,
        )

        self._validate_request(student, attendance_request)

        response, _ = AttendanceResponse.objects.get_or_create(
            attendance_request=attendance_request,
            student=student,
            defaults={
                'auto_status': 'pending',
                'final_status': 'pending',
            }
        )

        if response.face_verified and response.final_status == 'present':
            logger.info(
                'already_verified student_id=%s attendance_request_id=%s',
                student.id,
                attendance_request.id,
            )
            return {
                'success': True,
                'status': FaceStatus.VERIFIED,
                'message': 'حضور شما قبلاً تایید شده است.',
                'similarity_score': response.similarity_score,
                'already_verified': True,
                'remaining_attempts': 0,
            }

        max_attempts = getattr(settings, 'FACE_MAX_ATTEMPTS', 3)
        if response.attempts >= max_attempts:
            logger.info(
                'too_many_attempts student_id=%s attendance_request_id=%s attempts=%s',
                student.id,
                attendance_request.id,
                response.attempts,
            )
            raise TooManyAttemptsError()

        self._validate_frames(frames)
        self._check_enrollment(student)

        try:
            result = self.face_service.verify_frames(
                student_id=student.id,
                frames=frames,
                check_liveness=True,
            )
        except LivenessFailedError as e:
            self._register_failure(
                student=student,
                attendance_request=attendance_request,
                response=response,
                code=e.code,
                message=e.message,
                liveness_status=LivenessStatus.FAILED,
                session=session,
                challenge_result=challenge_result,
                processing_time_ms=processing_ms(),
            )
            raise
        except InvalidFramesError:
            # برای حفظ سازگاری با رفتار قبلی، فریم نامعتبر attempt مصرف نمی‌کند.
            raise
        except FaceServiceError as e:
            self._register_failure(
                student=student,
                attendance_request=attendance_request,
                response=response,
                code=e.code,
                message=e.message,
                liveness_status=LivenessStatus.NOT_CHECKED,
                session=session,
                challenge_result=challenge_result,
                processing_time_ms=processing_ms(),
            )
            raise

        liveness_result = result.get('liveness_result') or {}
        liveness_status = (
            LivenessStatus.PASSED
            if liveness_result.get('is_live')
            else LivenessStatus.NOT_CHECKED
        )
        similarity_score = result.get('similarity_score')
        elapsed = processing_ms()

        if result.get('decision') == MatchDecision.MATCH:
            response.register_face_verification(
                face_status=FaceStatus.VERIFIED,
                similarity_score=similarity_score,
                liveness_status=liveness_status,
                failure_reason='',
                increment_attempt=True,
            )
            self._log_verification(
                student=student,
                attendance_request=attendance_request,
                status='verified',
                similarity_score=similarity_score,
                liveness_passed=True,
                liveness_confidence=liveness_result.get('confidence'),
                total_frames=result.get('total_frames', 0),
                valid_frames=result.get('valid_frames', 0),
                failure_reason='',
                session=session,
                challenge_result=challenge_result,
                processing_time_ms=elapsed,
            )
            logger.info(
                'verification_completed status=VERIFIED student_id=%s attendance_request_id=%s similarity=%.4f',
                student.id,
                attendance_request.id,
                similarity_score or 0,
            )
            return {
                'success': True,
                'status': FaceStatus.VERIFIED,
                'message': 'احراز هویت چهره با موفقیت انجام شد.',
                'similarity_score': similarity_score,
                'remaining_attempts': max(0, max_attempts - response.attempts),
            }

        response.register_face_verification(
            face_status=FaceStatus.SUSPICIOUS,
            similarity_score=similarity_score,
            liveness_status=liveness_status,
            failure_reason='MATCH_BELOW_THRESHOLD',
            increment_attempt=True,
        )
        self._log_verification(
            student=student,
            attendance_request=attendance_request,
            status='suspicious',
            similarity_score=similarity_score,
            liveness_passed=True,
            liveness_confidence=liveness_result.get('confidence'),
            total_frames=result.get('total_frames', 0),
            valid_frames=result.get('valid_frames', 0),
            failure_reason='MATCH_BELOW_THRESHOLD',
            session=session,
            challenge_result=challenge_result,
            processing_time_ms=elapsed,
        )
        logger.info(
            'verification_completed status=SUSPICIOUS student_id=%s attendance_request_id=%s similarity=%.4f',
            student.id,
            attendance_request.id,
            similarity_score or 0,
        )
        return {
            'success': True,
            'status': FaceStatus.SUSPICIOUS,
            'message': 'تطبیق چهره با اطمینان کافی انجام نشد.',
            'similarity_score': similarity_score,
            'remaining_attempts': max(0, max_attempts - response.attempts),
        }
    # ------------------------------------------------------------------
    # Validations
    # ------------------------------------------------------------------
    def _validate_request(self, student, attendance_request):
        if student.role != 'student':
            raise AttendanceNotForStudentError()

        if attendance_request.status != 'active':
            raise AttendanceNotActiveError()

        if not attendance_request.requires_face:
            raise AttendanceNotActiveError('این درخواست نیاز به اسکن چهره ندارد.')

        if attendance_request.is_face_expired:
            raise FaceDeadlineExpiredError()

        if not attendance_request.classroom.students.filter(pk=student.pk).exists():
            raise AttendanceNotForStudentError()

    def _validate_frames(self, frames):
        if not frames:
            raise InvalidFramesError('هیچ فریمی ارسال نشده است.')

        min_frames = getattr(settings, 'FACE_MIN_FRAMES', 5)
        max_frames = getattr(settings, 'FACE_MAX_FRAMES', 15)
        max_size_mb = getattr(settings, 'FACE_MAX_FRAME_SIZE_MB', 2)
        max_size_bytes = max_size_mb * 1024 * 1024

        if len(frames) < min_frames:
            raise InvalidFramesError(f'حداقل {min_frames} فریم لازم است.')

        if len(frames) > max_frames:
            raise InvalidFramesError(f'حداکثر {max_frames} فریم مجاز است.')

        allowed_extensions = ('.jpg', '.jpeg', '.png', '.webp')

        for frame in frames:
            size = getattr(frame, 'size', 0)
            name = getattr(frame, 'name', '') or ''
            content_type = getattr(frame, 'content_type', '') or ''

            if size > max_size_bytes:
                raise InvalidFramesError('حجم یکی از فریم‌ها بیش از حد مجاز است.')

            valid_name = name.lower().endswith(allowed_extensions)
            valid_type = content_type.startswith('image/')

            if not (valid_name or valid_type):
                raise InvalidFramesError('فرمت یکی از فریم‌ها معتبر نیست.')

    def _check_enrollment(self, student):
        min_reference_images = getattr(settings, 'FACE_MIN_REFERENCE_IMAGES', 3)
        active_embeddings = FaceEmbedding.objects.filter(
            student_id=student.id,
            is_active=True
        ).count()

        if active_embeddings < min_reference_images:
            raise EnrollmentRequiredError()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _register_failure(
        self,
        student,
        attendance_request,
        response,
        code,
        message,
        liveness_status,
        session=None,
        challenge_result=None,
        processing_time_ms=None,
    ):
        response.register_face_verification(
        face_status=FaceStatus.FAILED,
        similarity_score=None,
        liveness_status=liveness_status,
        failure_reason=code,
        increment_attempt=True,
        )
        self._log_verification(
            student=student,
            attendance_request=attendance_request,
            status='failed',
            similarity_score=None,
            liveness_passed=(liveness_status == LivenessStatus.PASSED),
            liveness_confidence=None,
            total_frames=0,
            valid_frames=0,
            failure_reason=code,
            session=session,
            challenge_result=challenge_result,
            processing_time_ms=processing_time_ms,
        )
        logger.info(
            'verification_failed student_id=%s attendance_request_id=%s code=%s message=%s',
            student.id,
            attendance_request.id,
            code,
            message,
        )


    def _log_verification(
        self,
        student,
        attendance_request,
        status,
        similarity_score,
        liveness_passed,
        liveness_confidence,
        total_frames,
        valid_frames,
        failure_reason,
        session=None,
        challenge_result=None,
        processing_time_ms=None,
    ):
            FaceVerificationLog.objects.create(
            student=student,
            attendance_request=attendance_request,
            session=session,
            status=status,
            similarity_score=similarity_score,
            liveness_passed=liveness_passed,
            liveness_confidence=liveness_confidence,
            total_frames=total_frames or 0,
            valid_frames=valid_frames or 0,
            failure_reason=failure_reason or '',
            challenge_result=challenge_result,
            processing_time_ms=processing_time_ms,
        )