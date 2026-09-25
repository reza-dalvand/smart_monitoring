"""
ثابت‌ها و وضعیت‌های مربوط به تشخیص چهره و احراز هویت حضور
"""


class FaceStatus:
    VERIFIED = 'VERIFIED'
    SUSPICIOUS = 'SUSPICIOUS'
    FAILED = 'FAILED'
    NOT_CHECKED = 'NOT_CHECKED'

    CHOICES = (
        (VERIFIED, 'تایید شده'),
        (SUSPICIOUS, 'مشکوک'),
        (FAILED, 'ناموفق'),
        (NOT_CHECKED, 'بررسی نشده'),
    )


class MatchDecision:
    MATCH = 'MATCH'
    SUSPICIOUS = 'SUSPICIOUS'
    NO_FACE = 'NO_FACE'
    MULTIPLE_FACES = 'MULTIPLE_FACES'
    LOW_QUALITY = 'LOW_QUALITY'
    LIVENESS_FAILED = 'LIVENESS_FAILED'
    PROCESSING_ERROR = 'PROCESSING_ERROR'

    CHOICES = (
        (MATCH, 'تطبیق موفق'),
        (SUSPICIOUS, 'مشکوک'),
        (NO_FACE, 'چهره یافت نشد'),
        (MULTIPLE_FACES, 'چند چهره یافت شد'),
        (LOW_QUALITY, 'کیفیت پایین'),
        (LIVENESS_FAILED, 'لایونس تایید نشد'),
        (PROCESSING_ERROR, 'خطای پردازش'),
    )


class EnrollmentStatus:
    PENDING = 'pending'
    ENROLLED = 'enrolled'
    FAILED = 'failed'

    CHOICES = (
        (PENDING, 'در انتظار'),
        (ENROLLED, 'ثبت شده'),
        (FAILED, 'ناموفق'),
    )


class ImageValidationStatus:
    VALID = 'VALID'
    NO_FACE = 'NO_FACE'
    MULTIPLE_FACES = 'MULTIPLE_FACES'
    LOW_QUALITY = 'LOW_QUALITY'
    BLURRY = 'BLURRY'
    INVALID_IMAGE = 'INVALID_IMAGE'


class LivenessStatus:
    PASSED = 'passed'
    FAILED = 'failed'
    NOT_CHECKED = 'not_checked'

    CHOICES = (
        (PASSED, 'تایید شده'),
        (FAILED, 'ناموفق'),
        (NOT_CHECKED, 'بررسی نشده'),
    )


class VerificationErrorCode:
    CAMERA_PERMISSION_DENIED = 'CAMERA_PERMISSION_DENIED'
    CAMERA_NOT_FOUND = 'CAMERA_NOT_FOUND'
    CAMERA_NOT_READABLE = 'CAMERA_NOT_READABLE'

    NO_FACE = 'NO_FACE'
    MULTIPLE_FACES = 'MULTIPLE_FACES'
    FACE_TOO_SMALL = 'FACE_TOO_SMALL'
    LOW_QUALITY_FACE = 'LOW_QUALITY_FACE'

    LIVENESS_FAILED = 'LIVENESS_FAILED'
    ENROLLMENT_REQUIRED = 'ENROLLMENT_REQUIRED'
    NO_REFERENCE_EMBEDDING = 'NO_REFERENCE_EMBEDDING'
    MATCH_FAILED = 'MATCH_FAILED'
    SUSPICIOUS = 'SUSPICIOUS'

    ATTENDANCE_NOT_FOUND = 'ATTENDANCE_NOT_FOUND'
    ATTENDANCE_NOT_ACTIVE = 'ATTENDANCE_NOT_ACTIVE'
    UNAUTHORIZED = 'UNAUTHORIZED'
    TOO_MANY_ATTEMPTS = 'TOO_MANY_ATTEMPTS'
    MODEL_UNAVAILABLE = 'MODEL_UNAVAILABLE'
    INVALID_IMAGE = 'INVALID_IMAGE'
    PROCESSING_ERROR = 'PROCESSING_ERROR'
    FACE_DEADLINE_EXPIRED = 'FACE_DEADLINE_EXPIRED'


class VerificationSessionStatus:
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    PASSED = 'passed'
    FAILED = 'failed'
    EXPIRED = 'expired'

    CHOICES = (
        (PENDING, 'در انتظار'),
        (IN_PROGRESS, 'در حال انجام'),
        (PASSED, 'موفق'),
        (FAILED, 'ناموفق'),
        (EXPIRED, 'منقضی شده'),
    )


class ChallengeStep:
    TURN_LEFT = 'TURN_LEFT'
    TURN_RIGHT = 'TURN_RIGHT'
    BLINK = 'BLINK'


class FacePositionState:
    NO_FACE = 'NO_FACE'
    MULTIPLE_FACES = 'MULTIPLE_FACES'
    FACE_OUT_OF_FRAME = 'FACE_OUT_OF_FRAME'
    FACE_TOO_SMALL = 'FACE_TOO_SMALL'
    FACE_TOO_LARGE = 'FACE_TOO_LARGE'
    FACE_READY = 'FACE_READY'


# گسترش کدهای خطا بدون شکستن ساختار قبلی
VerificationErrorCode.FACE_OUT_OF_FRAME = 'FACE_OUT_OF_FRAME'
VerificationErrorCode.FACE_NOT_CENTERED = 'FACE_NOT_CENTERED'
VerificationErrorCode.FACE_TOO_FAR = 'FACE_TOO_FAR'
VerificationErrorCode.FACE_TOO_CLOSE = 'FACE_TOO_CLOSE'

VerificationErrorCode.HEAD_TURN_LEFT_REQUIRED = 'HEAD_TURN_LEFT_REQUIRED'
VerificationErrorCode.HEAD_TURN_RIGHT_REQUIRED = 'HEAD_TURN_RIGHT_REQUIRED'
VerificationErrorCode.BLINK_REQUIRED = 'BLINK_REQUIRED'
VerificationErrorCode.CHALLENGE_TIMEOUT = 'CHALLENGE_TIMEOUT'

VerificationErrorCode.VERIFICATION_SESSION_INVALID = 'VERIFICATION_SESSION_INVALID'
VerificationErrorCode.VERIFICATION_SESSION_EXPIRED = 'VERIFICATION_SESSION_EXPIRED'
VerificationErrorCode.VERIFICATION_ALREADY_COMPLETED = 'VERIFICATION_ALREADY_COMPLETED'