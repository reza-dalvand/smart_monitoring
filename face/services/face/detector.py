"""تشخیص چهره با استفاده از بینش چهره"""
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
from django.conf import settings

from .interfaces import BaseFaceDetector, DetectedFace
from .exceptions import (
    FaceNotFoundError,
    MultipleFacesDetectedError,
    ModelNotAvailableError,
)

logger = logging.getLogger(__name__)


class InsightFaceDetector(BaseFaceDetector):
    _model_name = 'scrfd'
    _model_version = 'unknown'

    def __init__(self, model_dir=None, det_model_name=None, det_threshold=0.5):
        self._model_dir = Path(model_dir or getattr(settings, 'FACE_MODEL_DIR', 'models'))
        self._det_model_name = det_model_name or getattr(settings, 'FACE_DETECTION_MODEL', 'buffalo_l')
        self._det_threshold = det_threshold or getattr(settings, 'FACE_DETECTION_THRESHOLD', 0.5)
        self._detector = None
        self._is_loaded = False

    @property
    def model_name(self):
        return self._model_name

    @property
    def model_version(self):
        return self._model_version

    def _ensure_loaded(self):
        if self._is_loaded:
            return
        try:
            from insightface.app import FaceAnalysis
            self._model_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f'Loading face detection model: {self._det_model_name}')
            self._detector = FaceAnalysis(
                name=self._det_model_name,
                root=str(self._model_dir),
                providers=['CPUExecutionProvider']
            )
            self._detector.prepare(ctx_id=0, det_size=(640, 640))
            self._model_version = 'buffalo_l'
            self._is_loaded = True
            logger.info('Face detection model loaded successfully')
        except ImportError as e:
            logger.error(f'InsightFace not installed: {e}')
            raise ModelNotAvailableError('کتابخانه بینش چهره نصب نشده است.')
        except Exception as e:
            logger.error(f'Failed to load face detection model: {e}')
            raise ModelNotAvailableError(f'خطا در بارگذاری مدل: {str(e)}')

    def detect(self, image):
        self._ensure_loaded()
        try:
            faces = self._detector.get(image)
            if not faces:
                raise FaceNotFoundError()
            if len(faces) > 1:
                raise MultipleFacesDetectedError(
                    message=f'{len(faces)} چهره در تصویر یافت شد.'
                )
            detected_faces = []
            for face in faces:
                bbox = face.bbox.astype(float)
                confidence = float(face.det_score) if hasattr(face, 'det_score') else 0.0
                landmarks = face.kps.astype(float) if hasattr(face, 'kps') and face.kps is not None else None
                face_crop = self._crop_face(image, bbox)
                detected_face = DetectedFace(
                    bbox=tuple(bbox.tolist()),
                    confidence=confidence,
                    landmarks=landmarks,
                    image_crop=face_crop
                )
                detected_faces.append(detected_face)
            return detected_faces
        except (FaceNotFoundError, MultipleFacesDetectedError):
            raise
        except Exception as e:
            logger.error(f'Face detection error: {e}')
            raise FaceNotFoundError(message=f'خطا در تشخیص چهره: {str(e)}')

    def _crop_face(self, image, bbox, margin=0.2):
        h, w = image.shape[:2]
        x1, y1, x2, y2 = bbox.astype(int)
        face_w = x2 - x1
        face_h = y2 - y1
        margin_x = int(face_w * margin)
        margin_y = int(face_h * margin)
        x1 = max(0, x1 - margin_x)
        y1 = max(0, y1 - margin_y)
        x2 = min(w, x2 + margin_x)
        y2 = min(h, y2 + margin_y)
        return image[y1:y2, x1:x2].copy()

    def is_available(self):
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False