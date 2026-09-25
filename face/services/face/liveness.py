"""تشخیص زنده بودن چهره"""
import logging
from typing import List

import cv2
import numpy as np

from .interfaces import BaseLivenessDetector, LivenessResult

logger = logging.getLogger(__name__)


class RGBLivenessDetector(BaseLivenessDetector):
    _model_name = 'rgb_basic'

    def __init__(self, min_motion_threshold=1.0, max_identical_frames=2,
                 min_brightness_variance=5.0):
        self.min_motion_threshold = min_motion_threshold
        self.max_identical_frames = max_identical_frames
        self.min_brightness_variance = min_brightness_variance

    @property
    def model_name(self):
        return self._model_name

    def check_liveness(self, frames):
        if len(frames) < 3:
            return LivenessResult(
                is_live=False,
                confidence=0.0,
                method=self.model_name,
                details={'error': 'حداقل ۳ فریم لازم است.', 'frame_count': len(frames)}
            )

        motion_score = self._calculate_motion(frames)
        brightness_variance = self._calculate_brightness_variance(frames)
        texture_variance = self._calculate_texture_variance(frames)
        identical_count = self._count_identical_frames(frames)

        is_live = True
        confidence = 1.0
        reasons = []

        if motion_score < self.min_motion_threshold:
            is_live = False
            confidence -= 0.3
            reasons.append('حرکت بین فریم‌ها بسیار کم است.')

        if identical_count > self.max_identical_frames:
            is_live = False
            confidence -= 0.3
            reasons.append('فریم‌های کاملاً یکسان زیاد هستند.')

        if brightness_variance < self.min_brightness_variance:
            confidence -= 0.1
            reasons.append('تنوع روشنایی کم است.')

        confidence = max(0.0, min(1.0, confidence))

        logger.info(f'Liveness check: Live={is_live}, Confidence={confidence:.2f}')

        return LivenessResult(
            is_live=is_live,
            confidence=confidence,
            method=self.model_name,
            details={
                'motion_score': motion_score,
                'brightness_variance': brightness_variance,
                'texture_variance': texture_variance,
                'identical_frames': identical_count,
                'frame_count': len(frames),
                'reasons': reasons
            }
        )

    def _calculate_motion(self, frames):
        if len(frames) < 2:
            return 0.0
        motions = []
        for i in range(1, len(frames)):
            prev_gray = cv2.cvtColor(frames[i-1], cv2.COLOR_BGR2GRAY)
            curr_gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            prev_gray = cv2.resize(prev_gray, (160, 120))
            curr_gray = cv2.resize(curr_gray, (160, 120))
            diff = cv2.absdiff(prev_gray, curr_gray)
            motion = float(np.mean(diff))
            motions.append(motion)
        return sum(motions) / len(motions) if motions else 0.0

    def _calculate_brightness_variance(self, frames):
        brightness_values = []
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = float(np.mean(gray))
            brightness_values.append(brightness)
        if len(brightness_values) < 2:
            return 0.0
        return float(np.var(brightness_values))

    def _calculate_texture_variance(self, frames):
        texture_scores = []
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (160, 120))
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            texture_scores.append(laplacian_var)
        if len(texture_scores) < 2:
            return 0.0
        return float(np.var(texture_scores))

    def _count_identical_frames(self, frames):
        if len(frames) < 2:
            return 0
        identical_count = 0
        for i in range(1, len(frames)):
            diff = cv2.absdiff(frames[i-1], frames[i])
            if float(np.mean(diff)) < 0.5:
                identical_count += 1
        return identical_count

    def is_available(self):
        return True


class MockLivenessDetector(BaseLivenessDetector):
    _model_name = 'mock'

    @property
    def model_name(self):
        return self._model_name

    def check_liveness(self, frames):
        return LivenessResult(
            is_live=True,
            confidence=1.0,
            method=self.model_name,
            details={'mock': True, 'frame_count': len(frames)}
        )

    def is_available(self):
        return True