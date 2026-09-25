"""تشخیص هویت چهره با استفاده از بینش چهره"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from django.conf import settings

from .interfaces import BaseFaceRecognizer, DetectedFace
from .exceptions import ModelNotAvailableError, FaceServiceError

logger = logging.getLogger(__name__)


class InsightFaceRecognizer(BaseFaceRecognizer):
    _model_name = 'arcface'
    _model_version = 'unknown'
    _embedding_dim = 512

    def __init__(self, model_dir=None, rec_model_name=None):
        self._model_dir = Path(model_dir or getattr(settings, 'FACE_MODEL_DIR', 'models'))
        self._rec_model_name = rec_model_name or getattr(settings, 'FACE_RECOGNITION_MODEL', 'buffalo_l')
        self._recognizer = None
        self._is_loaded = False

    @property
    def model_name(self):
        return self._model_name

    @property
    def model_version(self):
        return self._model_version

    @property
    def embedding_dimension(self):
        return self._embedding_dim

    def _ensure_loaded(self):
        if self._is_loaded:
            return
        try:
            from insightface.app import FaceAnalysis
            self._model_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f'Loading face recognition model: {self._rec_model_name}')
            self._recognizer = FaceAnalysis(
                name=self._rec_model_name,
                root=str(self._model_dir),
                providers=['CPUExecutionProvider']
            )
            self._recognizer.prepare(ctx_id=0, det_size=(640, 640))
            self._model_version = 'buffalo_l'
            self._is_loaded = True
            logger.info('Face recognition model loaded successfully')
        except ImportError as e:
            logger.error(f'InsightFace not installed: {e}')
            raise ModelNotAvailableError('کتابخانه بینش چهره نصب نشده است.')
        except Exception as e:
            logger.error(f'Failed to load face recognition model: {e}')
            raise ModelNotAvailableError(f'خطا در بارگذاری مدل: {str(e)}')

    def extract_embedding(self, image, face):
        self._ensure_loaded()
        try:
            if face.image_crop is not None:
                face_image = face.image_crop
            else:
                h, w = image.shape[:2]
                x1, y1, x2, y2 = [int(v) for v in face.bbox]
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(w, x2)
                y2 = min(h, y2)
                face_image = image[y1:y2, x1:x2].copy()

            if face_image is None or face_image.size == 0:
                raise FaceServiceError('تصویر چهره خالی است.')

            faces = self._recognizer.get(face_image)
            if not faces:
                raise FaceServiceError('چهره‌ای برای استخراج امبدینگ یافت نشد.')

            face_obj = faces[0]
            if not hasattr(face_obj, 'embedding') or face_obj.embedding is None:
                raise FaceServiceError('امبدینگ چهره قابل استخراج نیست.')

            embedding = face_obj.embedding.astype(np.float32)
            embedding = self._normalize_embedding(embedding)
            return embedding

        except FaceServiceError:
            raise
        except Exception as e:
            logger.error(f'Embedding extraction error: {e}')
            raise FaceServiceError(f'خطا در استخراج امبدینگ: {str(e)}')

    def _normalize_embedding(self, embedding):
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return embedding
        return embedding / norm

    def is_available(self):
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False