"""
ثابت‌ها و وضعیت‌های ماژول معلم
الگوی مشابه: school/constants.py
"""


class SessionStatus:
    """وضعیت جلسه آموزشی"""
    SCHEDULED = 'scheduled'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

    CHOICES = (
        (SCHEDULED, 'زمان‌بندی شده'),
        (ACTIVE, 'فعال'),
        (COMPLETED, 'تکمیل شده'),
        (CANCELLED, 'لغو شده'),
    )


class ParticipationLevel:
    """سطح مشارکت"""
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'

    CHOICES = (
        (HIGH, 'بالا'),
        (MEDIUM, 'متوسط'),
        (LOW, 'کم'),
    )

    SCORE_MAP = {
        HIGH: 90,
        MEDIUM: 60,
        LOW: 25,
    }


class ParticipationSource:
    """منبع ثبت مشارکت"""
    MANUAL = 'manual'
    QUESTION_RESPONSE = 'question_response'
    ASSESSMENT = 'assessment'
    HOMEWORK = 'homework'
    CLASS_ACTIVITY = 'class_activity'

    CHOICES = (
        (MANUAL, 'ثبت دستی معلم'),
        (QUESTION_RESPONSE, 'پاسخ به سوال'),
        (ASSESSMENT, 'ارزیابی'),
        (HOMEWORK, 'تکلیف'),
        (CLASS_ACTIVITY, 'فعالیت کلاسی'),
    )


class AssessmentStatus:
    """وضعیت ارزیابی"""
    DRAFT = 'draft'
    PUBLISHED = 'published'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    ARCHIVED = 'archived'

    CHOICES = (
        (DRAFT, 'پیش‌نویس'),
        (PUBLISHED, 'منتشر شده'),
        (IN_PROGRESS, 'در حال برگزاری'),
        (COMPLETED, 'تکمیل شده'),
        (ARCHIVED, 'بایگانی شده'),
    )


class AssessmentQuestionStatus:
    """وضعیت سوال در ارزیابی"""
    PENDING = 'pending'
    ANSWERED = 'answered'
    GRADED = 'graded'

    CHOICES = (
        (PENDING, 'در انتظار'),
        (ANSWERED, 'پاسخ داده شده'),
        (GRADED, 'نمره داده شده'),
    )


class HomeworkStatus:
    """وضعیت تکلیف"""
    DRAFT = 'draft'
    ACTIVE = 'active'
    CLOSED = 'closed'
    ARCHIVED = 'archived'

    CHOICES = (
        (DRAFT, 'پیش‌نویس'),
        (ACTIVE, 'فعال'),
        (CLOSED, 'بسته شده'),
        (ARCHIVED, 'بایگانی شده'),
    )


class SubmissionStatus:
    """وضعیت ارسال تکلیف"""
    NOT_SUBMITTED = 'not_submitted'
    SUBMITTED = 'submitted'
    LATE = 'late'
    REVIEWED = 'reviewed'
    RETURNED = 'returned'

    CHOICES = (
        (NOT_SUBMITTED, 'ارسال نشده'),
        (SUBMITTED, 'ارسال شده'),
        (LATE, 'ارسال با تأخیر'),
        (REVIEWED, 'بررسی شده'),
        (RETURNED, 'بازگردانده شده'),
    )


class FeedbackType:
    """نوع بازخورد"""
    ASSESSMENT = 'assessment'
    HOMEWORK = 'homework'
    PARTICIPATION = 'participation'
    GENERAL = 'general'

    CHOICES = (
        (ASSESSMENT, 'ارزیابی'),
        (HOMEWORK, 'تکلیف'),
        (PARTICIPATION, 'مشارکت'),
        (GENERAL, 'عمومی'),
    )


class FollowUpSuggestionStatus:
    """وضعیت پیشنهاد پیگیری معلم"""
    SUBMITTED = 'submitted'
    REVIEWED = 'reviewed'
    CONVERTED = 'converted'  # تبدیل به FollowUpCase شده
    REJECTED = 'rejected'

    CHOICES = (
        (SUBMITTED, 'ارسال شده'),
        (REVIEWED, 'بررسی شده'),
        (CONVERTED, 'تبدیل به پرونده'),
        (REJECTED, 'رد شده'),
    )


class QuestionDifficulty:
    """سطح دشواری سوال"""
    EASY = 'easy'
    MEDIUM = 'medium'
    HARD = 'hard'

    CHOICES = (
        (EASY, 'آسان'),
        (MEDIUM, 'متوسط'),
        (HARD, 'سخت'),
    )


class RiskLevel:
    """سطح نیاز به توجه"""
    NONE = 'none'
    WATCH = 'watch'
    NEEDS_ATTENTION = 'needs_attention'

    CHOICES = (
        (NONE, 'عادی'),
        (WATCH, 'زیر نظر'),
        (NEEDS_ATTENTION, 'نیازمند توجه آموزشی'),
    )


# ──────────────────────────────────────────────────────────
#  Participation Weights (Configurable)
# ──────────────────────────────────────────────────────────
PARTICIPATION_WEIGHTS = {
    'manual': 0.40,
    'question_response': 0.25,
    'assessment': 0.20,
    'homework': 0.15,
}

# ──────────────────────────────────────────────────────────
#  Risk Detection Thresholds
# ──────────────────────────────────────────────────────────
RISK_THRESHOLDS = {
    'attendance_min': 75.0,       # درصد حداقل حضور
    'participation_min': 50.0,    # درصد حداقل مشارکت
    'assessment_min': 10.0,       # حداقل نمره از ۲۰
    'homework_min': 60.0,         # درصد حداقل انجام تکلیف
    'recent_sessions': 4,         # تعداد جلسات اخیر برای بررسی
    'decline_threshold': 15.0,    # درصد افت برای شناسایی
}


# ──────────────────────────────────────────────────────────
#  Teacher Permission Matrix
# ──────────────────────────────────────────────────────────
class TeacherPermission:
    """دسترسی‌های نقش معلم"""
    # Classes
    CLASS_VIEW = 'teacher.class.view'

    # Sessions
    SESSION_CREATE = 'teacher.session.create'
    SESSION_START = 'teacher.session.start'
    SESSION_END = 'teacher.session.end'
    SESSION_VIEW = 'teacher.session.view'

    # Students
    STUDENT_VIEW = 'teacher.student.view'
    STUDENT_ANALYTICS_VIEW = 'teacher.student.analytics.view'

    # Attendance
    ATTENDANCE_VIEW = 'teacher.attendance.view'
    ATTENDANCE_CORRECT = 'teacher.attendance.correct'

    # Participation
    PARTICIPATION_VIEW = 'teacher.participation.view'
    PARTICIPATION_EDIT = 'teacher.participation.edit'

    # Questions
    QUESTION_CREATE = 'teacher.question.create'
    QUESTION_APPROVE = 'teacher.question.approve'
    QUESTION_REJECT = 'teacher.question.reject'
    QUESTION_DELETE = 'teacher.question.delete'

    # Assessments
    ASSESSMENT_CREATE = 'teacher.assessment.create'
    ASSESSMENT_PUBLISH = 'teacher.assessment.publish'
    ASSESSMENT_GRADE = 'teacher.assessment.grade'

    # Homework
    HOMEWORK_CREATE = 'teacher.homework.create'
    HOMEWORK_GRADE = 'teacher.homework.grade'

    # Feedback & Notes
    FEEDBACK_CREATE = 'teacher.feedback.create'
    NOTE_CREATE = 'teacher.note.create'

    # Analytics
    ANALYTICS_VIEW = 'teacher.analytics.view'
    REPORTS_VIEW = 'teacher.reports.view'

    # Follow-up
    FOLLOWUP_SUGGEST = 'teacher.followup.suggest'

    # AI
    AI_GENERATE = 'teacher.ai.generate'


# تمام دسترسی‌های معلم
TEACHER_ALL_PERMISSIONS = {
    TeacherPermission.CLASS_VIEW,
    TeacherPermission.SESSION_CREATE,
    TeacherPermission.SESSION_START,
    TeacherPermission.SESSION_END,
    TeacherPermission.SESSION_VIEW,
    TeacherPermission.STUDENT_VIEW,
    TeacherPermission.STUDENT_ANALYTICS_VIEW,
    TeacherPermission.ATTENDANCE_VIEW,
    TeacherPermission.ATTENDANCE_CORRECT,
    TeacherPermission.PARTICIPATION_VIEW,
    TeacherPermission.PARTICIPATION_EDIT,
    TeacherPermission.QUESTION_CREATE,
    TeacherPermission.QUESTION_APPROVE,
    TeacherPermission.QUESTION_REJECT,
    TeacherPermission.QUESTION_DELETE,
    TeacherPermission.ASSESSMENT_CREATE,
    TeacherPermission.ASSESSMENT_PUBLISH,
    TeacherPermission.ASSESSMENT_GRADE,
    TeacherPermission.HOMEWORK_CREATE,
    TeacherPermission.HOMEWORK_GRADE,
    TeacherPermission.FEEDBACK_CREATE,
    TeacherPermission.NOTE_CREATE,
    TeacherPermission.ANALYTICS_VIEW,
    TeacherPermission.REPORTS_VIEW,
    TeacherPermission.FOLLOWUP_SUGGEST,
    TeacherPermission.AI_GENERATE,
}