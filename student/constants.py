"""
ثابت‌ها و وضعیت‌های ماژول دانش‌آموز.
الگوی مشابه: teacher/constants.py, school/constants.py
"""


class StudentRequestType:
    """انواع درخواست دانش‌آموز"""
    ATTENDANCE_CORRECTION = 'ATTENDANCE_CORRECTION'
    ATTENDANCE_PROBLEM = 'ATTENDANCE_PROBLEM'
    GRADE_APPEAL = 'GRADE_APPEAL'
    ANSWER_REVIEW = 'ANSWER_REVIEW'
    STATUS_REVIEW = 'STATUS_REVIEW'
    FACE_VERIFICATION_REVIEW = 'FACE_VERIFICATION_REVIEW'
    FACE_CHANGE_REQUEST = 'FACE_CHANGE_REQUEST'
    GENERAL = 'GENERAL'

    CHOICES = (
        (ATTENDANCE_CORRECTION, 'اصلاح حضور و غیاب'),
        (ATTENDANCE_PROBLEM, 'مشکل در حضور و غیاب'),
        (GRADE_APPEAL, 'اعتراض به نمره'),
        (ANSWER_REVIEW, 'بررسی پاسخ'),
        (STATUS_REVIEW, 'بازبینی وضعیت آموزشی'),
        (FACE_VERIFICATION_REVIEW, 'بررسی مشکل احراز هویت'),
        (FACE_CHANGE_REQUEST, 'درخواست تغییر چهره'),
        (GENERAL, 'سایر'),
    )


class StudentRequestStatus:
    """وضعیت درخواست دانش‌آموز"""
    OPEN = 'OPEN'
    IN_REVIEW = 'IN_REVIEW'
    NEEDS_INFO = 'NEEDS_INFO'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    RESOLVED = 'RESOLVED'
    CANCELLED = 'CANCELLED'

    CHOICES = (
        (OPEN, 'ثبت شده'),
        (IN_REVIEW, 'در حال بررسی'),
        (NEEDS_INFO, 'نیازمند اطلاعات'),
        (APPROVED, 'تأیید شده'),
        (REJECTED, 'رد شده'),
        (RESOLVED, 'حل شده'),
        (CANCELLED, 'لغو شده'),
    )

    # وضعیت‌هایی که دانش‌آموز می‌تواند لغو کند
    CANCELLABLE = {OPEN}

    # وضعیت‌های نهایی
    FINAL = {APPROVED, REJECTED, RESOLVED, CANCELLED}


class StudentRequestPriority:
    """اولویت درخواست"""
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    URGENT = 'URGENT'

    CHOICES = (
        (LOW, 'کم'),
        (MEDIUM, 'متوسط'),
        (HIGH, 'زیاد'),
        (URGENT, 'فوری'),
    )


class FaceChangeRequestStatus:
    """وضعیت درخواست تغییر چهره"""
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'

    CHOICES = (
        (PENDING, 'در انتظار بررسی'),
        (APPROVED, 'تأیید شده'),
        (REJECTED, 'رد شده'),
    )


class MaterialType:
    """نوع محتوای آموزشی"""
    FILE = 'FILE'
    LINK = 'LINK'
    VIDEO = 'VIDEO'
    DOCUMENT = 'DOCUMENT'

    CHOICES = (
        (FILE, 'فایل'),
        (LINK, 'لینک'),
        (VIDEO, 'ویدیو'),
        (DOCUMENT, 'سند'),
    )


class EducationalStatusLevel:
    """سطح وضعیت آموزشی"""
    NORMAL = 'NORMAL'
    UNDER_OBSERVATION = 'UNDER_OBSERVATION'
    NEEDS_ATTENTION = 'NEEDS_ATTENTION'

    CHOICES = (
        (NORMAL, 'عادی'),
        (UNDER_OBSERVATION, 'زیر نظر'),
        (NEEDS_ATTENTION, 'نیازمند توجه'),
    )


# آستانه‌های پیش‌فرض (از SchoolSettings خوانده می‌شود)
DEFAULT_THRESHOLDS = {
    'attendance_min': 75.0,
    'participation_min': 50.0,
    'assessment_min': 10.0,  # از ۲۰
    'homework_min': 60.0,
}