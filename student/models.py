"""
مدل‌های ماژول دانش‌آموز.
این مدل‌ها مکمل مدل‌های موجود هستند.
از مدل‌های موجود (Assessment, Homework, ...) استفاده می‌شود.
"""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

from .constants import (
    StudentRequestType,
    StudentRequestStatus,
    StudentRequestPriority,
    FaceChangeRequestStatus,
    MaterialType,
)


class StudentRequest(models.Model):
    """
    درخواست دانش‌آموز.
    انواع: اصلاح حضور، اعتراض نمره، بررسی پاسخ، بازبینی وضعیت،
    بررسی مشکل احراز هویت، درخواست تغییر چهره، عمومی.
    """
    request_number = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name='شماره درخواست',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_requests',
        limit_choices_to={'role': 'student'},
        verbose_name='دانش‌آموز',
    )
    request_type = models.CharField(
        max_length=30,
        choices=StudentRequestType.CHOICES,
        verbose_name='نوع درخواست',
    )
    title = models.CharField(
        max_length=200,
        verbose_name='عنوان',
    )
    description = models.TextField(
        verbose_name='شرح درخواست',
    )
    priority = models.CharField(
        max_length=10,
        choices=StudentRequestPriority.CHOICES,
        default=StudentRequestPriority.MEDIUM,
        verbose_name='اولویت',
    )
    status = models.CharField(
        max_length=20,
        choices=StudentRequestStatus.CHOICES,
        default=StudentRequestStatus.OPEN,
        verbose_name='وضعیت',
    )

    # ارجاع به اشیاء مرتبط (اختیاری)
    related_classroom = models.ForeignKey(
        'dashboard.Classroom',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_requests',
        verbose_name='کلاس مرتبط',
    )
    related_session = models.ForeignKey(
        'dashboard.ClassSession',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_requests',
        verbose_name='جلسه مرتبط',
    )
    related_attendance = models.ForeignKey(
        'dashboard.AttendanceResponse',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_requests',
        verbose_name='حضور مرتبط',
    )
    related_question = models.ForeignKey(
        'dashboard.Question',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_requests',
        verbose_name='سوال مرتبط',
    )
    related_assessment = models.ForeignKey(
        'teacher.Assessment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_requests',
        verbose_name='ارزیابی مرتبط',
    )
    related_submission = models.ForeignKey(
        'teacher.HomeworkSubmission',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_requests',
        verbose_name='ارسال مرتبط',
    )

    # اطلاعات بررسی
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_student_requests',
        verbose_name='ارجاع به',
    )
    resolved_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='زمان حل',
    )
    resolution_note = models.TextField(
        blank=True, default='',
        verbose_name='یادداشت حل',
    )

    # متادیتا
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'درخواست دانش‌آموز'
        verbose_name_plural = 'درخواست‌های دانش‌آموزان'
        ordering = ['-created_at']

    def __str__(self):
        return f'درخواست {self.request_number} - {self.title}'

    @property
    def is_cancellable(self):
        return self.status in StudentRequestStatus.CANCELLABLE

    @property
    def is_final(self):
        return self.status in StudentRequestStatus.FINAL


class StudentFaceChangeRequest(models.Model):
    """
    درخواست تغییر چهره دانش‌آموز.
    چرخه: دانش‌آموز درخواست → تصاویر → بررسی مدرسه → تأیید/رد
    """
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='face_change_requests',
        limit_choices_to={'role': 'student'},
        verbose_name='دانش‌آموز',
    )
    reason = models.TextField(
        verbose_name='دلیل درخواست',
    )
    status = models.CharField(
        max_length=20,
        choices=FaceChangeRequestStatus.CHOICES,
        default=FaceChangeRequestStatus.PENDING,
        verbose_name='وضعیت',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_face_changes',
        verbose_name='بررسی‌کننده',
    )
    reviewed_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='زمان بررسی',
    )
    review_note = models.TextField(
        blank=True, default='',
        verbose_name='یادداشت بررسی',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'درخواست تغییر چهره'
        verbose_name_plural = 'درخواست‌های تغییر چهره'
        ordering = ['-created_at']

    def __str__(self):
        return f'درخواست تغییر چهره {self.student.username}'


class SessionMaterial(models.Model):
    """محتوای آموزشی جلسه"""
    session = models.ForeignKey(
        'dashboard.ClassSession',
        on_delete=models.CASCADE,
        related_name='materials',
        verbose_name='جلسه',
    )
    title = models.CharField(
        max_length=200,
        verbose_name='عنوان',
    )
    description = models.TextField(
        blank=True, default='',
        verbose_name='توضیحات',
    )
    material_type = models.CharField(
        max_length=20,
        choices=MaterialType.CHOICES,
        default=MaterialType.FILE,
        verbose_name='نوع محتوا',
    )
    file = models.FileField(
        upload_to='session_materials/',
        null=True, blank=True,
        verbose_name='فایل',
    )
    external_url = models.URLField(
        blank=True, default='',
        verbose_name='لینک خارجی',
    )
    visible_to_students = models.BooleanField(
        default=True,
        verbose_name='قابل مشاهده برای دانش‌آموز',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_materials',
        verbose_name='ایجادکننده',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'محتوای آموزشی جلسه'
        verbose_name_plural = 'محتوای آموزشی جلسات'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} - جلسه {self.session_id}'


class VirtualSessionInfo(models.Model):
    """اطلاعات کلاس مجازی برای یک جلسه"""
    session = models.OneToOneField(
        'dashboard.ClassSession',
        on_delete=models.CASCADE,
        related_name='virtual_info',
        verbose_name='جلسه',
    )
    meeting_url = models.URLField(
        blank=True, default='',
        verbose_name='لینک کلاس مجازی',
    )
    meeting_provider = models.CharField(
        max_length=100,
        blank=True, default='',
        verbose_name='سرویس‌دهنده',
    )
    meeting_start_time = models.DateTimeField(
        null=True, blank=True,
        verbose_name='زمان شروع کلاس مجازی',
    )
    meeting_end_time = models.DateTimeField(
        null=True, blank=True,
        verbose_name='زمان پایان کلاس مجازی',
    )
    meeting_id = models.CharField(
        max_length=200,
        blank=True, default='',
        verbose_name='شناسه جلسه',
    )
    meeting_password = models.CharField(
        max_length=100,
        blank=True, default='',
        verbose_name='رمز جلسه',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'اطلاعات کلاس مجازی'
        verbose_name_plural = 'اطلاعات کلاس‌های مجازی'

    def __str__(self):
        return f'کلاس مجازی - جلسه {self.session_id}'

    @property
    def is_active(self):
        now = timezone.now()
        if self.meeting_start_time and self.meeting_end_time:
            return self.meeting_start_time <= now <= self.meeting_end_time
        return bool(self.meeting_url)