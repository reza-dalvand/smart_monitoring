"""سرویس ماک برای تست و توسعه"""
import logging

from django.conf import settings

from face.constants import MatchDecision, FaceStatus, ImageValidationStatus
from .exceptions import (
    EnrollmentError,
    VerificationError,
    LivenessFailedError,
    InvalidFramesError,
)

logger = logging.getLogger(__name__)


class MockFaceRecognitionService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        self._match_threshold = getattr(settings, 'FACE_MATCH_THRESHOLD', 0.45)
        self._min_reference_images = getattr(settings, 'FACE_MIN_REFERENCE_IMAGES', 3)
        self._max_reference_images = getattr(settings, 'FACE_MAX_REFERENCE_IMAGES', 5)

        logger.info('MockFaceRecognitionService initialized')

    @classmethod
    def get_instance(cls):
        return cls()

    def enroll_student(self, student_id, images, replace_existing=False):
        if len(images) < self._min_reference_images:
            raise EnrollmentError(f'حداقل {self._min_reference_images} تصویر لازم است.')

        if len(images) > self._max_reference_images:
            raise EnrollmentError(f'حداکثر {self._max_reference_images} تصویر مجاز است.')

        return {
            'success': True,
            'message': f'چهره با موفقیت ثبت شد (حالت ماک). {len(images)} تصویر پردازش شد.',
            'processed': len(images),
            'failed': 0,
            'errors': []
        }

    def validate_enrollment_image(self, image_file):
        return {
            'valid': True,
            'status': ImageValidationStatus.VALID,
            'message': 'تصویر معتبر است (حالت ماک).',
            'mock': True
        }

    def verify_student(self, student_id, frames, check_liveness=True):
        result = self.verify_frames(
            student_id=student_id,
            frames=frames,
            check_liveness=check_liveness
        )
        return result

    def verify_frames(self, student_id, frames, check_liveness=True):
        """
        خروجی ماک اما deterministic برای توسعه و تست.
        """
        if not frames:
            raise VerificationError('هیچ فریمی ارسال نشده است.')

        min_frames = getattr(settings, 'FACE_MIN_FRAMES', 5)
        max_frames = getattr(settings, 'FACE_MAX_FRAMES', 15)

        if len(frames) < min_frames:
            raise InvalidFramesError(f'حداقل {min_frames} فریم لازم است.')

        if len(frames) > max_frames:
            raise InvalidFramesError(f'حداکثر {max_frames} فریم مجاز است.')

        if check_liveness and not getattr(settings, 'FACE_AI_MOCK_LIVENESS_PASS', True):
            raise LivenessFailedError()

        similarity_score = float(getattr(settings, 'FACE_AI_MOCK_SIMILARITY', 0.93))

        if similarity_score >= self._match_threshold:
            decision = MatchDecision.MATCH
            face_status = FaceStatus.VERIFIED
        else:
            decision = MatchDecision.SUSPICIOUS
            face_status = FaceStatus.SUSPICIOUS

        return {
            'decision': decision,
            'face_status': face_status,
            'similarity_score': similarity_score,
            'valid_frames': len(frames),
            'total_frames': len(frames),
            'liveness_result': {
                'is_live': True,
                'confidence': 1.0,
                'method': 'mock',
            } if check_liveness else None,
            'all_similarities': [similarity_score],
            'reference_count': self._min_reference_images,
            'threshold': self._match_threshold,
        }

    def get_service_status(self):
        return {
            'mock_mode': True,
            'threshold': self._match_threshold,
            'min_reference_images': self._min_reference_images,
            'max_reference_images': self._max_reference_images,
            'liveness_enabled': True,
            'detector_available': True,
            'recognizer_available': True,
        }