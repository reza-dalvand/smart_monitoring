"""
مدل‌های سیستم مدیریت مدرسه
این مدل‌ها مکمل مدل‌های موجود هستند و هیچ تکراری ایجاد نمی‌کنند.
"""
import logging
from django.conf import settings
from django.db import models
from django.utils import timezone

from .constants import (
    StaffRole, AssistantType, StudentStatus, ClassroomStatus,
    ScheduleStatus, CaseStatus, CasePriority, CaseCategory,
    AlertSeverity, AlertType, TaskStatus, AbsenceReviewStatus,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
#  1. SchoolStaffAssignment
#     انتصاب کارکنان به مدرسه
#     هر مدرسه می‌تواند ۰ تا N معاون داشته باشد
# ══════════════════════════════════════════════════════════
class SchoolStaffAssignment(models.Model):
    """
    انتصاب یک کاربر به یک مدرسه با نقش مشخص.
    - مدیر: یک رکورد با staff_role='principal'
    - معاون: یک یا چند رکورد با staff_role='assistant'
    - یک کاربر می‌تواند چند مسئولیت داشته باشد (چند رکورد)
    - یک کاربر می‌تواند در چند مدرسه assignment داشته باشد
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='school_assignments',
        verbose_name='کاربر',
    )
    school = models.ForeignKey(
        'national.School',
        on_delete=models.CASCADE,
        related_name='staff_assignments',
        verbose_name='مدرسه',
    )
    staff_role = models.CharField(
        max_length=20,
        choices=StaffRole.CHOICES,
        verbose_name='نقش',
    )
    assistant_type = models.CharField(
        max_length=20,
        choices=AssistantType.CHOICES,
        blank=True,
        default='',
        verbose_name='نوع معاونت',
        help_text='فقط برای نقش معاون',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='فعال',
    )
    start_date = models.DateField(
        null=True, blank=True,
        verbose_name='تاریخ شروع',
    )
    end_date = models.DateField(
        null=True, blank=True,
        verbose_name='تاریخ پایان',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'انتصاب کارکنان مدرسه'
        verbose_name_plural = 'انتصاب‌های کارکنان مدرسه'
        unique_together = ('user', 'school', 'staff_role', 'assistant_type')
        ordering = ['-is_active', 'staff_role', 'assistant_type']

    def __str__(self):
        role_display = self.get_staff_role_display()
        if self.assistant_type:
            return f'{self.user.username} - {role_display} ({self.get_assistant_type_display()})'
        return f'{self.user.username} - {role_display}'

    @property
    def is_currently_active(self):
        """بررسی فعال بودن با توجه به تاریخ"""
        if not self.is_active:
            return False
        today = timezone.now().date()
        if self.start_date and today < self.start_date:
            return False
        if self.end_date and today > self.end_date:
            return False
        return True

    def get_permissions(self):
        from .constants import get_permissions_for_assignment
        return get_permissions_for_assignment(
            self.staff_role, self.assistant_type
        )


# ══════════════════════════════════════════════════════════
#  2. StudentSchoolStatus
#     وضعیت تحصیلی دانش‌آموز در مدرسه
#     (حذف فیزیکی ممنوع — فقط تغییر وضعیت)
# ══════════════════════════════════════════════════════════
class StudentSchoolStatus(models.Model):
    """
    وضعیت دانش‌آموز در یک مدرسه.
    به‌جای حذف فیزیکی، وضعیت تغییر می‌کند.
    """
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='school_statuses',
        limit_choices_to={'role': 'student'},
        verbose_name='دانش‌آموز',
    )
    school = models.ForeignKey(
        'national.School',
        on_delete=models.CASCADE,
        related_name='student_statuses',
        verbose_name='مدرسه',
    )
    status = models.CharField(
        max_length=20,
        choices=StudentStatus.CHOICES,
        default=StudentStatus.ACTIVE,
        verbose_name='وضعیت',
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_status_changes',
        verbose_name='تغییر توسط',
    )
    reason = models.TextField(
        blank=True, default='',
        verbose_name='دلیل تغییر',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'وضعیت دانش‌آموز در مدرسه'
        verbose_name_plural = 'وضعیت‌های دانش‌آموزان در مدارس'
        unique_together = ('student', 'school')

    def __str__(self):
        return f'{self.student.username} - {self.get_status_display()}'


# ══════════════════════════════════════════════════════════
#  3. FollowUpCase
#     پرونده پیگیری
# ══════════════════════════════════════════════════════════
class FollowUpCase(models.Model):
    """
    پرونده پیگیری برای دانش‌آموز، کلاس یا موارد مدیریتی.
    """
    case_number = models.AutoField(
        primary_key=True,
        verbose_name='شماره پرونده',
    )
    school = models.ForeignKey(
        'national.School',
        on_delete=models.CASCADE,
        related_name='followup_cases',
        verbose_name='مدرسه',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='followup_cases',
        limit_choices_to={'role': 'student'},
        verbose_name='دانش‌آموز',
    )
    classroom = models.ForeignKey(
        'dashboard.Classroom',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='followup_cases',
        verbose_name='کلاس',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_followup_cases',
        verbose_name='ایجادکننده',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_followup_cases',
        verbose_name='ارجاع به',
    )
    title = models.CharField(
        max_length=200,
        verbose_name='عنوان',
    )
    description = models.TextField(
        blank=True, default='',
        verbose_name='توضیحات',
    )
    category = models.CharField(
        max_length=30,
        choices=CaseCategory.CHOICES,
        default=CaseCategory.OTHER,
        verbose_name='دسته‌بندی',
    )
    priority = models.CharField(
        max_length=10,
        choices=CasePriority.CHOICES,
        default=CasePriority.MEDIUM,
        verbose_name='اولویت',
    )
    status = models.CharField(
        max_length=20,
        choices=CaseStatus.CHOICES,
        default=CaseStatus.OPEN,
        verbose_name='وضعیت',
    )
    due_date = models.DateField(
        null=True, blank=True,
        verbose_name='مهلت پیگیری',
    )
    resolved_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='زمان حل',
    )
    resolution_note = models.TextField(
        blank=True, default='',
        verbose_name='یادداشت حل',
    )
    escalated = models.BooleanField(
        default=False,
        verbose_name='ارجاع به مدیر',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'پرونده پیگیری'
        verbose_name_plural = 'پرونده‌های پیگیری'
        ordering = ['-created_at']

    def __str__(self):
        return f'پرونده #{self.case_number} - {self.title}'


class FollowUpCaseNote(models.Model):
    """یادداشت‌های پرونده پیگیری"""
    case = models.ForeignKey(
        FollowUpCase,
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name='پرونده',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='followup_notes',
        verbose_name='نویسنده',
    )
    content = models.TextField(verbose_name='متن یادداشت')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'یادداشت پرونده'
        verbose_name_plural = 'یادداشت‌های پرونده‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return f'یادداشت #{self.id} برای پرونده #{self.case_id}'


# ══════════════════════════════════════════════════════════
#  4. SchoolAlert
#     هشدارها و موارد استثنایی
# ══════════════════════════════════════════════════════════
class SchoolAlert(models.Model):
    """
    هشدارهای سیستم برای مدیر.
    از داده‌های واقعی استخراج می‌شود.
    """
    school = models.ForeignKey(
        'national.School',
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name='مدرسه',
    )
    alert_type = models.CharField(
        max_length=40,
        choices=AlertType.CHOICES,
        verbose_name='نوع هشدار',
    )
    severity = models.CharField(
        max_length=10,
        choices=AlertSeverity.CHOICES,
        default=AlertSeverity.WARNING,
        verbose_name='شدت',
    )
    title = models.CharField(
        max_length=200,
        verbose_name='عنوان',
    )
    message = models.TextField(
        blank=True, default='',
        verbose_name='پیام',
    )
    # ارجاع به موجودیت مرتبط
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='school_alerts',
        verbose_name='دانش‌آموز مرتبط',
    )
    classroom = models.ForeignKey(
        'dashboard.Classroom',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='school_alerts',
        verbose_name='کلاس مرتبط',
    )
    is_read = models.BooleanField(default=False, verbose_name='خوانده شده')
    is_resolved = models.BooleanField(default=False, verbose_name='حل شده')
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='resolved_alerts',
        verbose_name='حل توسط',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(
        default=dict, blank=True,
        verbose_name='داده‌های اضافی',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'هشدار مدرسه'
        verbose_name_plural = 'هشدارهای مدرسه'
        ordering = ['-is_resolved', '-created_at']

    def __str__(self):
        return f'{self.get_severity_display()} - {self.title}'


# ══════════════════════════════════════════════════════════
#  5. SchoolTask
#     وظایف داخلی (Task Center ساده)
# ══════════════════════════════════════════════════════════
class SchoolTask(models.Model):
    """وظیفه داخلی برای مدیر یا معاون"""
    school = models.ForeignKey(
        'national.School',
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='مدرسه',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='school_tasks',
        verbose_name='مسئول',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_school_tasks',
        verbose_name='ایجادکننده',
    )
    title = models.CharField(max_length=200, verbose_name='عنوان')
    description = models.TextField(blank=True, default='', verbose_name='توضیحات')
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.CHOICES,
        default=TaskStatus.TODO,
        verbose_name='وضعیت',
    )
    # ارجاع اختیاری به پرونده پیگیری
    related_case = models.ForeignKey(
        FollowUpCase,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tasks',
        verbose_name='پرونده مرتبط',
    )
    due_date = models.DateField(null=True, blank=True, verbose_name='مهلت')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'وظیفه'
        verbose_name_plural = 'وظایف'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


# ══════════════════════════════════════════════════════════
#  6. SchoolAuditLog
#     لاگ عملیات حساس در سطح مدرسه
# ══════════════════════════════════════════════════════════
class SchoolAuditLog(models.Model):
    """لاگ عملیات حساس مدیریتی"""
    ACTION_CHOICES = (
        ('attendance_override', 'تغییر حضور و غیاب'),
        ('student_status_change', 'تغییر وضعیت دانش‌آموز'),
        ('class_change', 'تغییر کلاس'),
        ('teacher_assignment', 'انتصاب معلم'),
        ('assistant_assignment', 'انتصاب معاون'),
        ('schedule_approval', 'تأیید برنامه'),
        ('school_setting_change', 'تغییر تنظیمات مدرسه'),
        ('followup_resolution', 'حل پرونده پیگیری'),
        ('followup_creation', 'ایجاد پرونده پیگیری'),
        ('followup_assignment', 'ارجاع پرونده'),
        ('student_class_assign', 'انتصاب دانش‌آموز به کلاس'),
        ('view_dashboard', 'مشاهده داشبورد'),
        ('view_reports', 'مشاهده گزارش‌ها'),
        ('export_data', 'خروجی داده'),
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='school_audit_logs',
        verbose_name='انجام‌دهنده',
    )
    school = models.ForeignKey(
        'national.School',
        on_delete=models.CASCADE,
        related_name='audit_logs',
        verbose_name='مدرسه',
    )
    action = models.CharField(
        max_length=40,
        choices=ACTION_CHOICES,
        verbose_name='عملیات',
    )
    object_type = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name='نوع شیء',
    )
    object_id = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name='شناسه شیء',
    )
    old_values = models.JSONField(
        default=dict, blank=True,
        verbose_name='مقادیر قبلی',
    )
    new_values = models.JSONField(
        default=dict, blank=True,
        verbose_name='مقادیر جدید',
    )
    reason = models.TextField(
        blank=True, default='',
        verbose_name='دلیل',
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name='آدرس IP',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'لاگ عملیات مدرسه'
        verbose_name_plural = 'لاگ‌های عملیات مدرسه'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.actor.username} - {self.get_action_display()}'


# ══════════════════════════════════════════════════════════
#  7. SchoolSettings
#     تنظیمات سطح مدرسه
# ══════════════════════════════════════════════════════════
class SchoolSettings(models.Model):
    """تنظیمات قابل پیکربندی هر مدرسه"""
    school = models.OneToOneField(
        'national.School',
        on_delete=models.CASCADE,
        related_name='settings',
        verbose_name='مدرسه',
    )
    academic_year = models.CharField(
        max_length=20, blank=True, default='1404-1405',
        verbose_name='سال تحصیلی',
    )
    # Thresholds
    absence_warning_threshold = models.FloatField(
        default=20.0,
        verbose_name='آستانه هشدار غیبت (٪)',
    )
    participation_warning_threshold = models.FloatField(
        default=40.0,
        verbose_name='آستانه هشدار مشارکت (٪)',
    )
    performance_warning_threshold = models.FloatField(
        default=50.0,
        verbose_name='آستانه هشدار عملکرد (٪)',
    )
    late_threshold_minutes = models.PositiveIntegerField(
        default=15,
        verbose_name='آستانه تأخیر (دقیقه)',
    )
    face_verification_required = models.BooleanField(
        default=True,
        verbose_name='الزام احراز هویت چهره',
    )
    # Attendance policy
    auto_mark_absent_on_deadline = models.BooleanField(
        default=True,
        verbose_name='ثبت خودکار غیبت پس از مهلت',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='به‌روزرسانی توسط',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'تنظیمات مدرسه'
        verbose_name_plural = 'تنظیمات مدارس'

    def __str__(self):
        return f'تنظیمات {self.school.name}'


# ══════════════════════════════════════════════════════════
#  8. AttendanceOverrideLog
#     لاگ تغییر وضعیت حضور (Override)
# ══════════════════════════════════════════════════════════
class AttendanceOverrideLog(models.Model):
    """ثبت تغییر وضعیت حضور توسط مدیر"""
    school = models.ForeignKey(
        'national.School',
        on_delete=models.CASCADE,
        related_name='attendance_overrides',
        verbose_name='مدرسه',
    )
    attendance_response = models.ForeignKey(
        'dashboard.AttendanceResponse',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='override_logs',
        verbose_name='پاسخ حضور',
    )
    attendance_record = models.ForeignKey(
        'dashboard.AttendanceRecord',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='override_logs',
        verbose_name='رکورد حضور',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_overrides',
        verbose_name='دانش‌آموز',
    )
    old_status = models.CharField(
        max_length=30,
        verbose_name='وضعیت قبلی',
    )
    new_status = models.CharField(
        max_length=30,
        verbose_name='وضعیت جدید',
    )
    reason = models.TextField(
        verbose_name='دلیل تغییر',
    )
    overridden_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='performed_overrides',
        verbose_name='تغییر توسط',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'لاگ تغییر حضور'
        verbose_name_plural = 'لاگ‌های تغییر حضور'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student.username}: {self.old_status} → {self.new_status}'


# ══════════════════════════════════════════════════════════
#  9. AbsenceReview
#     وضعیت بررسی غیبت (عملیات معاون)
# ══════════════════════════════════════════════════════════
class AbsenceReview(models.Model):
    """بررسی و پیگیری غیبت توسط معاون"""
    school = models.ForeignKey(
        'national.School',
        on_delete=models.CASCADE,
        related_name='absence_reviews',
        verbose_name='مدرسه',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='absence_reviews',
        verbose_name='دانش‌آموز',
    )
    attendance_record = models.ForeignKey(
        'dashboard.AttendanceRecord',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='absence_reviews',
        verbose_name='رکورد حضور',
    )
    attendance_response = models.ForeignKey(
        'dashboard.AttendanceResponse',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='absence_reviews',
        verbose_name='پاسخ حضور',
    )
    review_status = models.CharField(
        max_length=20,
        choices=AbsenceReviewStatus.CHOICES,
        default=AbsenceReviewStatus.DETECTED,
        verbose_name='وضعیت بررسی',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_absences',
        verbose_name='بررسی توسط',
    )
    contact_note = models.TextField(
        blank=True, default='',
        verbose_name='یادداشت تماس',
    )
    related_case = models.ForeignKey(
        FollowUpCase,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='absence_reviews',
        verbose_name='پرونده مرتبط',
    )
    review_date = models.DateField(
        verbose_name='تاریخ غیبت',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'بررسی غیبت'
        verbose_name_plural = 'بررسی‌های غیبت'
        ordering = ['-created_at']

    def __str__(self):
        return f'بررسی غیبت {self.student.username} - {self.review_date}'