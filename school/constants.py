"""
ثابت‌های مرکزی سیستم مدیریت مدرسه
"""


class StaffRole:
    """نقش‌های کارکنان مدرسه"""
    PRINCIPAL = 'principal'
    ASSISTANT = 'assistant'

    CHOICES = (
        (PRINCIPAL, 'مدیر مدرسه'),
        (ASSISTANT, 'معاون'),
    )


class AssistantType:
    """نوع مسئولیت معاون"""
    EXECUTIVE = 'EXECUTIVE'
    EDUCATIONAL = 'EDUCATIONAL'
    CULTURAL = 'CULTURAL'
    TECHNICAL = 'TECHNICAL'
    GENERAL = 'GENERAL'
    CUSTOM = 'CUSTOM'

    CHOICES = (
        (EXECUTIVE, 'اجرایی'),
        (EDUCATIONAL, 'آموزشی'),
        (CULTURAL, 'پرورشی'),
        (TECHNICAL, 'فنی'),
        (GENERAL, 'عمومی'),
        (CUSTOM, 'سفارشی'),
    )

    # حداقل انواع برای نسخه اول
    V1_TYPES = [EXECUTIVE, EDUCATIONAL, GENERAL]


class StudentStatus:
    """وضعیت دانش‌آموز"""
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'
    TRANSFERRED = 'TRANSFERRED'
    GRADUATED = 'GRADUATED'

    CHOICES = (
        (ACTIVE, 'فعال'),
        (INACTIVE, 'غیرفعال'),
        (TRANSFERRED, 'منتقل شده'),
        (GRADUATED, 'فارغ‌التحصیل'),
    )


class ClassroomStatus:
    """وضعیت کلاس"""
    ACTIVE = 'ACTIVE'
    ARCHIVED = 'ARCHIVED'

    CHOICES = (
        (ACTIVE, 'فعال'),
        (ARCHIVED, 'بایگانی شده'),
    )


class ScheduleStatus:
    """وضعیت برنامه هفتگی"""
    DRAFT = 'DRAFT'
    PENDING_APPROVAL = 'PENDING_APPROVAL'
    APPROVED = 'APPROVED'
    PUBLISHED = 'PUBLISHED'
    ARCHIVED = 'ARCHIVED'

    CHOICES = (
        (DRAFT, 'پیش‌نویس'),
        (PENDING_APPROVAL, 'در انتظار تأیید'),
        (APPROVED, 'تأیید شده'),
        (PUBLISHED, 'منتشر شده'),
        (ARCHIVED, 'بایگانی شده'),
    )


class CaseStatus:
    """وضعیت پرونده پیگیری"""
    OPEN = 'OPEN'
    IN_REVIEW = 'IN_REVIEW'
    ASSIGNED = 'ASSIGNED'
    RESOLVED = 'RESOLVED'
    DISMISSED = 'DISMISSED'

    CHOICES = (
        (OPEN, 'باز'),
        (IN_REVIEW, 'در حال بررسی'),
        (ASSIGNED, 'ارجاع داده شده'),
        (RESOLVED, 'حل شده'),
        (DISMISSED, 'رد شده'),
    )


class CasePriority:
    """اولویت پرونده"""
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


class CaseCategory:
    """دسته‌بندی پرونده"""
    ABSENCE = 'ABSENCE'
    PARTICIPATION = 'PARTICIPATION'
    PERFORMANCE = 'PERFORMANCE'
    BEHAVIOR = 'BEHAVIOR'
    VERIFICATION = 'VERIFICATION'
    SCHEDULE = 'SCHEDULE'
    OTHER = 'OTHER'

    CHOICES = (
        (ABSENCE, 'غیبت'),
        (PARTICIPATION, 'مشارکت'),
        (PERFORMANCE, 'عملکرد تحصیلی'),
        (BEHAVIOR, 'رفتاری'),
        (VERIFICATION, 'احراز هویت'),
        (SCHEDULE, 'برنامه'),
        (OTHER, 'سایر'),
    )


class AlertSeverity:
    """شدت هشدار"""
    CRITICAL = 'CRITICAL'
    WARNING = 'WARNING'
    INFO = 'INFO'

    CHOICES = (
        (CRITICAL, 'بحرانی'),
        (WARNING, 'هشدار'),
        (INFO, 'اطلاع'),
    )


class AlertType:
    """نوع هشدار"""
    ABSENCE_SPIKE = 'ABSENCE_SPIKE'
    PARTICIPATION_DROP = 'PARTICIPATION_DROP'
    PERFORMANCE_DROP = 'PERFORMANCE_DROP'
    SUSPICIOUS_ATTENDANCE = 'SUSPICIOUS_ATTENDANCE'
    NO_ATTENDANCE_RECORDED = 'NO_ATTENDANCE_RECORDED'
    INCOMPLETE_SESSION = 'INCOMPLETE_SESSION'
    FACE_VERIFICATION_FAILURE = 'FACE_VERIFICATION_FAILURE'
    SCHEDULE_CONFLICT = 'SCHEDULE_CONFLICT'
    PENDING_REVIEW = 'PENDING_REVIEW'
    UNRESOLVED_FOLLOWUP = 'UNRESOLVED_FOLLOWUP'

    CHOICES = (
        (ABSENCE_SPIKE, 'افزایش غیبت'),
        (PARTICIPATION_DROP, 'افت مشارکت'),
        (PERFORMANCE_DROP, 'افت عملکرد'),
        (SUSPICIOUS_ATTENDANCE, 'حضور مشکوک'),
        (NO_ATTENDANCE_RECORDED, 'کلاس بدون حضور و غیاب'),
        (INCOMPLETE_SESSION, 'جلسه ناقص'),
        (FACE_VERIFICATION_FAILURE, 'خطای احراز هویت'),
        (SCHEDULE_CONFLICT, 'تداخل برنامه'),
        (PENDING_REVIEW, 'در انتظار بررسی'),
        (UNRESOLVED_FOLLOWUP, 'پیگیری حل نشده'),
    )


class TaskStatus:
    """وضعیت وظیفه"""
    TODO = 'TODO'
    IN_PROGRESS = 'IN_PROGRESS'
    DONE = 'DONE'

    CHOICES = (
        (TODO, 'در انتظار'),
        (IN_PROGRESS, 'در حال انجام'),
        (DONE, 'انجام شده'),
    )


class AbsenceReviewStatus:
    """وضعیت بررسی غیبت"""
    DETECTED = 'DETECTED'
    REVIEWED = 'REVIEWED'
    CONTACTED = 'CONTACTED'
    CONFIRMED = 'CONFIRMED'
    ESCALATED = 'ESCALATED'
    RESOLVED = 'RESOLVED'

    CHOICES = (
        (DETECTED, 'شناسایی شده'),
        (REVIEWED, 'بررسی شده'),
        (CONTACTED, 'تماس گرفته شده'),
        (CONFIRMED, 'تأیید شده'),
        (ESCALATED, 'ارجاع به مدیر'),
        (RESOLVED, 'حل شده'),
    )


# ──────────────────────────────────────────────────────────
#  Permission Matrix
# ──────────────────────────────────────────────────────────
class Permission:
    """تمام دسترسی‌های سیستم"""
    # School
    SCHOOL_VIEW = 'school.view'
    SCHOOL_MANAGE = 'school.manage'

    # Students
    STUDENTS_VIEW = 'students.view'
    STUDENTS_MANAGE = 'students.manage'
    STUDENTS_ASSIGN_CLASS = 'students.assign_class'
    STUDENTS_CHANGE_STATUS = 'students.change_status'

    # Classes
    CLASSES_VIEW = 'classes.view'
    CLASSES_MANAGE = 'classes.manage'
    CLASSES_ARCHIVE = 'classes.archive'

    # Teachers
    TEACHERS_VIEW = 'teachers.view'
    TEACHERS_MANAGE_ASSIGNMENT = 'teachers.manage_assignment'

    # Attendance
    ATTENDANCE_VIEW = 'attendance.view'
    ATTENDANCE_REVIEW = 'attendance.review'
    ATTENDANCE_OVERRIDE = 'attendance.override'

    # Schedule
    SCHEDULE_VIEW = 'schedule.view'
    SCHEDULE_MANAGE = 'schedule.manage'
    SCHEDULE_APPROVE = 'schedule.approve'

    # Reports
    REPORTS_VIEW = 'reports.view'
    REPORTS_EXPORT = 'reports.export'

    # Follow-ups
    FOLLOWUPS_VIEW = 'followups.view'
    FOLLOWUPS_CREATE = 'followups.create'
    FOLLOWUPS_ASSIGN = 'followups.assign'
    FOLLOWUPS_RESOLVE = 'followups.resolve'

    # Assistants
    ASSISTANTS_VIEW = 'assistants.view'
    ASSISTANTS_MANAGE = 'assistants.manage'

    # Settings
    SETTINGS_VIEW = 'settings.view'
    SETTINGS_MANAGE = 'settings.manage'

    # Audit
    AUDIT_VIEW = 'audit.view'

    # Analytics (Educational)
    PARTICIPATION_VIEW = 'participation.view'
    PERFORMANCE_VIEW = 'performance.view'
    CLASS_ANALYTICS_VIEW = 'class.analytics.view'
    STUDENT_ANALYTICS_VIEW = 'student.analytics.view'
    TEACHER_ACTIVITY_VIEW = 'teacher.activity.view'
    QUESTION_ANALYTICS_VIEW = 'question.analytics.view'


# ──────────────────────────────────────────────────────────
#  Permission Sets per Role/Type
# ──────────────────────────────────────────────────────────
PRINCIPAL_PERMISSIONS = {
    Permission.SCHOOL_VIEW, Permission.SCHOOL_MANAGE,
    Permission.STUDENTS_VIEW, Permission.STUDENTS_MANAGE,
    Permission.STUDENTS_ASSIGN_CLASS, Permission.STUDENTS_CHANGE_STATUS,
    Permission.CLASSES_VIEW, Permission.CLASSES_MANAGE, Permission.CLASSES_ARCHIVE,
    Permission.TEACHERS_VIEW, Permission.TEACHERS_MANAGE_ASSIGNMENT,
    Permission.ATTENDANCE_VIEW, Permission.ATTENDANCE_REVIEW, Permission.ATTENDANCE_OVERRIDE,
    Permission.SCHEDULE_VIEW, Permission.SCHEDULE_MANAGE, Permission.SCHEDULE_APPROVE,
    Permission.REPORTS_VIEW, Permission.REPORTS_EXPORT,
    Permission.FOLLOWUPS_VIEW, Permission.FOLLOWUPS_CREATE,
    Permission.FOLLOWUPS_ASSIGN, Permission.FOLLOWUPS_RESOLVE,
    Permission.ASSISTANTS_VIEW, Permission.ASSISTANTS_MANAGE,
    Permission.SETTINGS_VIEW, Permission.SETTINGS_MANAGE,
    Permission.AUDIT_VIEW,
    Permission.PARTICIPATION_VIEW, Permission.PERFORMANCE_VIEW,
    Permission.CLASS_ANALYTICS_VIEW, Permission.STUDENT_ANALYTICS_VIEW,
    Permission.TEACHER_ACTIVITY_VIEW, Permission.QUESTION_ANALYTICS_VIEW,
}

ASSISTANT_GENERAL_PERMISSIONS = {
    Permission.SCHOOL_VIEW,
    Permission.STUDENTS_VIEW, Permission.STUDENTS_MANAGE,
    Permission.STUDENTS_ASSIGN_CLASS,
    Permission.CLASSES_VIEW, Permission.CLASSES_MANAGE,
    Permission.ATTENDANCE_VIEW, Permission.ATTENDANCE_REVIEW,
    Permission.SCHEDULE_VIEW, Permission.SCHEDULE_MANAGE,
    Permission.REPORTS_VIEW,
    Permission.FOLLOWUPS_VIEW, Permission.FOLLOWUPS_CREATE,
}

ASSISTANT_EDUCATIONAL_EXTRA = {
    Permission.PARTICIPATION_VIEW,
    Permission.PERFORMANCE_VIEW,
    Permission.CLASS_ANALYTICS_VIEW,
    Permission.STUDENT_ANALYTICS_VIEW,
    Permission.TEACHER_ACTIVITY_VIEW,
    Permission.QUESTION_ANALYTICS_VIEW,
    Permission.FOLLOWUPS_ASSIGN,
    Permission.FOLLOWUPS_RESOLVE,
}

ASSISTANT_EXECUTIVE_EXTRA = {
    Permission.STUDENTS_CHANGE_STATUS,
    Permission.CLASSES_ARCHIVE,
    Permission.TEACHERS_VIEW,
    Permission.ATTENDANCE_VIEW, Permission.ATTENDANCE_REVIEW,
    Permission.FOLLOWUPS_ASSIGN,
    Permission.FOLLOWUPS_RESOLVE,
}


def get_permissions_for_assignment(staff_role, assistant_type=None):
    """محاسبه دسترسی‌ها بر اساس نقش و نوع معاون"""
    if staff_role == StaffRole.PRINCIPAL:
        return PRINCIPAL_PERMISSIONS.copy()

    if staff_role == StaffRole.ASSISTANT:
        perms = ASSISTANT_GENERAL_PERMISSIONS.copy()
        if assistant_type == AssistantType.EDUCATIONAL:
            perms |= ASSISTANT_EDUCATIONAL_EXTRA
        elif assistant_type == AssistantType.EXECUTIVE:
            perms |= ASSISTANT_EXECUTIVE_EXTRA
        return perms

    return set()