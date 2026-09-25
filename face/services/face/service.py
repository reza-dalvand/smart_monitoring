"""سرویس اصلی تشخیص چهره"""
import logging
from typing import List

import cv2
import numpy as np
from django.conf import settings

from face.constants import MatchDecision, FaceStatus, ImageValidationStatus
from .detector import InsightFaceDetector
from .recognizer import InsightFaceRecognizer
from .matcher import CosineFaceMatcher
from .liveness import RGBLivenessDetector, MockLivenessDetector
from .quality import FaceQualityChecker
from .embedding import EmbeddingStorage
from .exceptions import (
    EnrollmentError,
    VerificationError,
    LivenessFailedError,
    FaceNotFoundError,
    MultipleFacesDetectedError,
    InvalidFaceImageError,
    InvalidFramesError,
    NoReferenceEmbeddingError,
    LowQualityFaceError,
)

logger = logging.getLogger(__name__)


class FaceRecognitionService:
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

        self._use_mock = getattr(settings, 'FACE_AI_MOCK', False)
        self._match_threshold = getattr(settings, 'FACE_MATCH_THRESHOLD', 0.45)
        self._min_reference_images = getattr(settings, 'FACE_MIN_REFERENCE_IMAGES', 3)
        self._max_reference_images = getattr(settings, 'FACE_MAX_REFERENCE_IMAGES', 5)
        self._liveness_enabled = getattr(settings, 'FACE_LIVENESS_ENABLED', True)
        self._min_frames_for_liveness = getattr(settings, 'FACE_MIN_FRAMES_FOR_LIVENESS', 3)

        if self._use_mock:
            self._detector = None
            self._recognizer = None
            self._liveness_detector = MockLivenessDetector()
        else:
            self._detector = InsightFaceDetector()
            self._recognizer = InsightFaceRecognizer()
            self._liveness_detector = RGBLivenessDetector()

        self._matcher = CosineFaceMatcher(
            aggregation_method=getattr(settings, 'FACE_MATCH_AGGREGATION_METHOD', 'MAX'),
            top_k=getattr(settings, 'FACE_MATCH_TOP_K', 2),
        )

        self._quality_checker = FaceQualityChecker(
            min_face_size=getattr(settings, 'FACE_MIN_FACE_SIZE', 80),
            max_blur_threshold=getattr(settings, 'FACE_MAX_BLUR_THRESHOLD', 100.0),
            min_brightness=getattr(settings, 'FACE_MIN_BRIGHTNESS', 40.0),
            max_brightness=getattr(settings, 'FACE_MAX_BRIGHTNESS', 220.0),
        )

        self._embedding_storage = EmbeddingStorage()

        logger.info('FaceRecognitionService initialized. Mock=%s', self._use_mock)

    @classmethod
    def get_instance(cls):
        if getattr(settings, 'FACE_AI_MOCK', False):
            from .mock_service import MockFaceRecognitionService
            return MockFaceRecognitionService.get_instance()
        return cls()

    # ------------------------------------------------------------------
    # Enrollment
    # ------------------------------------------------------------------
    def enroll_student(self, student_id, images, replace_existing=False):
        logger.info('Enrollment started for student %s', student_id)

        if len(images) < self._min_reference_images:
            raise EnrollmentError(
                message=f'حداقل {self._min_reference_images} تصویر لازم است.'
            )

        if len(images) > self._max_reference_images:
            raise EnrollmentError(
                message=f'حداکثر {self._max_reference_images} تصویر مجاز است.'
            )

        if replace_existing:
            self._embedding_storage.deactivate_all_for_student(student_id)

        results = []
        success_count = 0
        error_count = 0

        for index, image_file in enumerate(images, 1):
            try:
                result = self._process_enrollment_image(
                    student_id=student_id,
                    image_file=image_file,
                    image_index=index
                )
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                results.append(result)
            except Exception as e:
                logger.error('Error processing image %s: %s', index, e)
                error_count += 1
                results.append({
                    'index': index,
                    'success': False,
                    'error_code': 'PROCESSING_ERROR',
                    'error_message': str(e)
                })

        if success_count < self._min_reference_images:
            raise EnrollmentError(
                message=f'ثبت چهره ناموفق بود. حداقل {self._min_reference_images} تصویر معتبر لازم است.'
            )

        logger.info(
            'Enrollment completed. Success=%s, Failed=%s',
            success_count,
            error_count
        )

        return {
            'success': True,
            'message': f'چهره با موفقیت ثبت شد. {success_count} تصویر ذخیره شد.',
            'processed': success_count,
            'failed': error_count,
            'errors': [r for r in results if not r['success']]
        }

    def _process_enrollment_image(self, student_id, image_file, image_index):
        image = self._read_image(image_file)
        if image is None:
            return {
                'index': image_index,
                'success': False,
                'error_code': ImageValidationStatus.INVALID_IMAGE,
                'error_message': 'تصویر قابل خواندن نیست.'
            }

        try:
            faces = self._detector.detect(image)
        except FaceNotFoundError:
            return {
                'index': image_index,
                'success': False,
                'error_code': ImageValidationStatus.NO_FACE,
                'error_message': 'چهره‌ای یافت نشد.'
            }
        except MultipleFacesDetectedError as e:
            return {
                'index': image_index,
                'success': False,
                'error_code': ImageValidationStatus.MULTIPLE_FACES,
                'error_message': str(e)
            }

        if not faces:
            return {
                'index': image_index,
                'success': False,
                'error_code': ImageValidationStatus.NO_FACE,
                'error_message': 'چهره‌ای یافت نشد.'
            }

        face = faces[0]
        quality_result = self._quality_checker.check_quality(image, face)

        if not quality_result.is_valid:
            return {
                'index': image_index,
                'success': False,
                'error_code': quality_result.error_code,
                'error_message': quality_result.error_message
            }

        try:
            embedding = self._recognizer.extract_embedding(image, face)
        except Exception as e:
            return {
                'index': image_index,
                'success': False,
                'error_code': 'EMBEDDING_ERROR',
                'error_message': str(e)
            }

        try:
            self._embedding_storage.save_embedding(
                student_id=student_id,
                embedding=embedding,
                model_name=self._recognizer.model_name,
                model_version=self._recognizer.model_version,
                embedding_dimension=self._recognizer.embedding_dimension,
                source_image_path=image_file.name if hasattr(image_file, 'name') else None,
                is_active=True
            )
        except Exception as e:
            return {
                'index': image_index,
                'success': False,
                'error_code': 'SAVE_ERROR',
                'error_message': str(e)
            }

        return {
            'index': image_index,
            'success': True,
            'error_code': None,
            'error_message': None
        }

    def validate_enrollment_image(self, image_file):
        """
        اعتبارسنجی سریع یک تصویر برای ثبت چهره.
        این متد فقط برای کمک به UX است و تصمیم نهایی با سرور است.
        """
        if self._use_mock:
            return {
                'valid': True,
                'status': ImageValidationStatus.VALID,
                'message': 'تصویر معتبر است (حالت ماک).',
                'mock': True
            }

        image = self._read_image(image_file)
        if image is None:
            return {
                'valid': False,
                'status': ImageValidationStatus.INVALID_IMAGE,
                'message': 'تصویر قابل خواندن نیست.'
            }

        try:
            faces = self._detector.detect(image)
        except FaceNotFoundError:
            return {
                'valid': False,
                'status': ImageValidationStatus.NO_FACE,
                'message': 'چهره‌ای در تصویر یافت نشد.'
            }
        except MultipleFacesDetectedError:
            return {
                'valid': False,
                'status': ImageValidationStatus.MULTIPLE_FACES,
                'message': 'بیش از یک چهره در تصویر یافت شد.'
            }

        if not faces:
            return {
                'valid': False,
                'status': ImageValidationStatus.NO_FACE,
                'message': 'چهره‌ای در تصویر یافت نشد.'
            }

        face = faces[0]
        quality_result = self._quality_checker.check_quality(image, face)

        if not quality_result.is_valid:
            return {
                'valid': False,
                'status': quality_result.error_code or ImageValidationStatus.LOW_QUALITY,
                'message': quality_result.error_message or 'کیفیت تصویر کافی نیست.'
            }

        return {
            'valid': True,
            'status': ImageValidationStatus.VALID,
            'message': 'تصویر معتبر است.'
        }

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    def verify_frames(self, student_id, frames: List, check_liveness: bool = True):
        """
        ورودی: لیستی از فریم‌های ارسالی از مرورگر
        خروجی: ساختار استاندارد برای تطبیق چهره

        این متد مسئول:
        - اعتبارسنجی اولیه فریم‌ها
        - لایونس
        - تشخیص چهره
        - کنترل کیفیت
        - استخراج امبدینگ
        - تطبیق با مرجع‌ها
        """
        if self._use_mock:
            from .mock_service import MockFaceRecognitionService
            return MockFaceRecognitionService.get_instance().verify_frames(
                student_id=student_id,
                frames=frames,
                check_liveness=check_liveness
            )

        if not frames:
            raise InvalidFramesError('هیچ فریمی ارسال نشده است.')

        min_frames = getattr(settings, 'FACE_MIN_FRAMES', self._min_frames_for_liveness)
        max_frames = getattr(settings, 'FACE_MAX_FRAMES', 15)

        if len(frames) < min_frames:
            raise InvalidFramesError(f'حداقل {min_frames} فریم لازم است.')

        if len(frames) > max_frames:
            raise InvalidFramesError(f'حداکثر {max_frames} فریم مجاز است.')

        decoded_frames = []
        for uploaded_frame in frames:
            image = self._read_image(uploaded_frame)
            if image is None:
                raise InvalidFaceImageError('حداقل یکی از فریم‌ها قابل خواندن نیست.')
            decoded_frames.append(image)

        liveness_result = None
        if check_liveness and self._liveness_enabled:
            liveness_result = self._liveness_detector.check_liveness(decoded_frames)
            if not liveness_result.is_live:
                raise LivenessFailedError(
                    message='زنده بودن چهره تایید نشد.',
                    details=liveness_result.details
                )

        reference_data = self._embedding_storage.get_embeddings_for_student(student_id)
        if not reference_data:
            raise NoReferenceEmbeddingError()

        reference_embeddings = [emb for emb, _ in reference_data]

        valid_embeddings = []
        no_face_count = 0
        low_quality_count = 0

        for image in decoded_frames:
            try:
                faces = self._detector.detect(image)
            except MultipleFacesDetectedError:
                raise MultipleFacesDetectedError()
            except FaceNotFoundError:
                no_face_count += 1
                continue

            if not faces:
                no_face_count += 1
                continue

            face = faces[0]

            quality_result = self._quality_checker.check_quality(image, face)
            if not quality_result.is_valid:
                low_quality_count += 1
                continue

            try:
                embedding = self._recognizer.extract_embedding(image, face)
                valid_embeddings.append(embedding)
            except Exception as e:
                logger.warning('Embedding extraction failed: %s', e)
                low_quality_count += 1
                continue

        if not valid_embeddings:
            if no_face_count > 0 and low_quality_count == 0:
                raise FaceNotFoundError()
            if low_quality_count > 0:
                raise LowQualityFaceError()
            raise VerificationError()

        query_embedding = np.mean(valid_embeddings, axis=0).astype(np.float32)
        norm = np.linalg.norm(query_embedding)
        if norm > 0:
            query_embedding = query_embedding / norm

        match_result = self._matcher.match(
            query_embedding=query_embedding,
            reference_embeddings=reference_embeddings,
            threshold=self._match_threshold
        )

        decision = (
            MatchDecision.MATCH
            if match_result.similarity_score >= self._match_threshold
            else MatchDecision.SUSPICIOUS
        )

        face_status = (
            FaceStatus.VERIFIED
            if decision == MatchDecision.MATCH
            else FaceStatus.SUSPICIOUS
        )

        return {
            'decision': decision,
            'face_status': face_status,
            'similarity_score': float(match_result.similarity_score),
            'valid_frames': len(valid_embeddings),
            'total_frames': len(decoded_frames),
            'liveness_result': {
                'is_live': bool(liveness_result.is_live) if liveness_result else None,
                'confidence': float(liveness_result.confidence) if liveness_result else None,
                'method': liveness_result.method if liveness_result else None,
            } if liveness_result else None,
            'all_similarities': match_result.all_similarities,
            'reference_count': len(reference_embeddings),
            'threshold': self._match_threshold,
        }

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _read_image(self, image_file):
        try:
            if hasattr(image_file, 'read'):
                image_data = image_file.read()
                image_file.seek(0)
            else:
                image_data = image_file

            if not image_data:
                return None

            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return image
        except Exception as e:
            logger.error('Error reading image: %s', e)
            return None

    def get_service_status(self):
        status = {
            'mock_mode': self._use_mock,
            'threshold': self._match_threshold,
            'min_reference_images': self._min_reference_images,
            'max_reference_images': self._max_reference_images,
            'liveness_enabled': self._liveness_enabled,
        }

        if not self._use_mock:
            status['detector_available'] = self._detector.is_available() if self._detector else False
            status['recognizer_available'] = self._recognizer.is_available() if self._recognizer else False
        else:
            status['detector_available'] = True
            status['recognizer_available'] = True

        return status