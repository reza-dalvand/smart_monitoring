"""
اینترفیس‌های انتزاعی برای سرویس‌های تشخیص چهره

هدف: جداسازی کامل منطق تجاری از پیاده‌سازی هوش مصنوعی
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class DetectedFace:
    """ساختار داده برای یک چهره شناسایی شده"""
    bbox: Tuple[float, float, float, float]
    confidence: float
    landmarks: Optional[np.ndarray] = None
    embedding: Optional[np.ndarray] = None
    image_crop: Optional[np.ndarray] = None

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    @property
    def is_small(self) -> bool:
        from django.conf import settings
        min_size = getattr(settings, 'FACE_MIN_FACE_SIZE', 80)
        return self.width < min_size or self.height < min_size


@dataclass
class FaceQualityResult:
    is_valid: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    blur_score: float = 0.0
    brightness_score: float = 0.0
    details: dict = field(default_factory=dict)


@dataclass
class LivenessResult:
    is_live: bool
    confidence: float = 0.0
    method: str = 'rgb_basic'
    details: dict = field(default_factory=dict)


@dataclass
class MatchResult:
    decision: str
    similarity_score: float = 0.0
    best_match_index: int = -1
    all_similarities: List[float] = field(default_factory=list)
    details: dict = field(default_factory=dict)


class BaseFaceDetector(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def model_version(self) -> str: ...

    @abstractmethod
    def detect(self, image: np.ndarray) -> List[DetectedFace]: ...

    @abstractmethod
    def is_available(self) -> bool: ...


class BaseFaceRecognizer(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def model_version(self) -> str: ...

    @property
    @abstractmethod
    def embedding_dimension(self) -> int: ...

    @abstractmethod
    def extract_embedding(self, image: np.ndarray, face: DetectedFace) -> np.ndarray: ...

    @abstractmethod
    def is_available(self) -> bool: ...


class BaseLivenessDetector(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @abstractmethod
    def check_liveness(self, frames: List[np.ndarray]) -> LivenessResult: ...

    @abstractmethod
    def is_available(self) -> bool: ...


class BaseFaceMatcher(ABC):
    @abstractmethod
    def match(self, query_embedding, reference_embeddings, threshold) -> MatchResult: ...

    @abstractmethod
    def calculate_similarity(self, embedding_a, embedding_b) -> float: ...