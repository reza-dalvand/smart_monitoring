"""اکسپشن‌های سفارشی برای سرویس تشخیص چهره"""


class FaceServiceError(Exception):
    code = 'FACE_SERVICE_ERROR'
    message = 'خطای سرویس چهره'

    def __init__(self, message=None, **kwargs):
        self.message = message or self.__class__.message
        self.details = kwargs
        super().__init__(self.message)


class FaceNotFoundError(FaceServiceError):
    code = 'NO_FACE'
    message = 'چهره‌ای در تصویر یافت نشد.'


class MultipleFacesDetectedError(FaceServiceError):
    code = 'MULTIPLE_FACES'
    message = 'بیش از یک چهره در تصویر یافت شد.'


class LowQualityFaceError(FaceServiceError):
    code = 'LOW_QUALITY_FACE'
    message = 'کیفیت چهره بسیار پایین است.'


class BlurryFaceError(FaceServiceError):
    code = 'BLURRY'
    message = 'تصویر تار است. لطفاً تصویر واضح‌تری ارسال کنید.'


class InvalidFaceImageError(FaceServiceError):
    code = 'INVALID_IMAGE'
    message = 'تصویر نامعتبر است.'


class LivenessFailedError(FaceServiceError):
    code = 'LIVENESS_FAILED'
    message = 'زنده بودن چهره تایید نشد.'


class FaceMatchFailedError(FaceServiceError):
    code = 'MATCH_FAILED'
    message = 'تطبیق چهره ناموفق بود.'


class ModelNotAvailableError(FaceServiceError):
    code = 'MODEL_UNAVAILABLE'
    message = 'مدل هوش مصنوعی در دسترس نیست.'


class EnrollmentError(FaceServiceError):
    code = 'ENROLLMENT_ERROR'
    message = 'خطا در ثبت چهره.'


class VerificationError(FaceServiceError):
    code = 'VERIFICATION_ERROR'
    message = 'خطا در احراز هویت.'


class InvalidFramesError(FaceServiceError):
    code = 'INVALID_IMAGE'
    message = 'فریم‌های ارسالی معتبر نیستند.'


class AttendanceNotActiveError(FaceServiceError):
    code = 'ATTENDANCE_NOT_ACTIVE'
    message = 'درخواست حضور و غیاب فعال نیست.'


class AttendanceNotForStudentError(FaceServiceError):
    code = 'UNAUTHORIZED'
    message = 'شما مجاز به احراز هویت برای این درخواست نیستید.'


class EnrollmentRequiredError(FaceServiceError):
    code = 'ENROLLMENT_REQUIRED'
    message = 'ثبت چهره دانش‌آموز کامل نشده است.'


class NoReferenceEmbeddingError(FaceServiceError):
    code = 'NO_REFERENCE_EMBEDDING'
    message = 'هیچ امبدینگ مرجعی برای این دانش‌آموز یافت نشد.'


class TooManyAttemptsError(FaceServiceError):
    code = 'TOO_MANY_ATTEMPTS'
    message = 'تعداد تلاش‌های مجاز به پایان رسیده است.'


class FaceDeadlineExpiredError(FaceServiceError):
    code = 'FACE_DEADLINE_EXPIRED'
    message = 'مهلت اسکن چهره به پایان رسیده است.'


class VerificationSessionInvalidError(FaceServiceError):
    code = 'VERIFICATION_SESSION_INVALID'
    message = 'نشست احراز هویت معتبر نیست.'


class VerificationSessionExpiredError(FaceServiceError):
    code = 'VERIFICATION_SESSION_EXPIRED'
    message = 'مهلت نشست احراز هویت به پایان رسیده است.'


class VerificationAlreadyCompletedError(FaceServiceError):
    code = 'VERIFICATION_ALREADY_COMPLETED'
    message = 'این نشست احراز هویت قبلاً تکمیل شده است.'


class ChallengeTimeoutError(FaceServiceError):
    code = 'CHALLENGE_TIMEOUT'
    message = 'مهلت انجام چالش‌ها به پایان رسید.'