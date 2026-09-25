"""بررسی کیفیت تصویر و چهره"""
import cv2
import numpy as np

from .interfaces import FaceQualityResult, DetectedFace


class FaceQualityChecker:
    def __init__(self, min_face_size=80, max_blur_threshold=100.0,
                 min_brightness=40.0, max_brightness=220.0):
        self.min_face_size = min_face_size
        self.max_blur_threshold = max_blur_threshold
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness

    def check_quality(self, image, face):
        if face.is_small:
            return FaceQualityResult(
                is_valid=False,
                error_code='SMALL_FACE',
                error_message=f'چهره بسیار کوچک است. حداقل: {self.min_face_size} پیکسل',
            )

        face_crop = self._crop_face(image, face)
        if face_crop is None or face_crop.size == 0:
            return FaceQualityResult(
                is_valid=False,
                error_code='CROP_FAILED',
                error_message='خطا در بریدن تصویر چهره',
            )

        blur_score = self._calculate_blur(face_crop)
        if blur_score < self.max_blur_threshold:
            return FaceQualityResult(
                is_valid=False,
                error_code='BLURRY',
                error_message='تصویر تار است.',
                blur_score=blur_score,
            )

        brightness = self._calculate_brightness(face_crop)
        if brightness < self.min_brightness:
            return FaceQualityResult(
                is_valid=False,
                error_code='TOO_DARK',
                error_message='تصویر بسیار تاریک است.',
                brightness_score=brightness,
            )

        if brightness > self.max_brightness:
            return FaceQualityResult(
                is_valid=False,
                error_code='TOO_BRIGHT',
                error_message='تصویر بسیار روشن است.',
                brightness_score=brightness,
            )

        return FaceQualityResult(
            is_valid=True,
            blur_score=blur_score,
            brightness_score=brightness,
        )

    def _crop_face(self, image, face, margin=0.2):
        h, w = image.shape[:2]
        x1, y1, x2, y2 = face.bbox
        face_w = x2 - x1
        face_h = y2 - y1
        margin_x = face_w * margin
        margin_y = face_h * margin
        x1 = max(0, int(x1 - margin_x))
        y1 = max(0, int(y1 - margin_y))
        x2 = min(w, int(x2 + margin_x))
        y2 = min(h, int(y2 + margin_y))
        return image[y1:y2, x1:x2].copy()

    def _calculate_blur(self, image):
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        gray = cv2.resize(gray, (160, 160), interpolation=cv2.INTER_AREA)
        return cv2.Laplacian(gray, cv2.CV_64F).var()

    def _calculate_brightness(self, image):
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        return float(np.mean(gray))