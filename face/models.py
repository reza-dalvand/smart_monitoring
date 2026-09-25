"""
مدل‌های دیتابیس برای سیستم تشخیص چهره
"""
import logging

from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid


logger = logging.getLogger(__name__)


class FaceProfile(models.Model):
    """پروفایل چهره یک دانش‌آموز"""

    ENROLLMENT_STATUS_CHOICES = (
        ('pending', 'در انتظار'),
        ('enrolled', 'ثبت شده'),
        ('failed', 'ناموفق'),
    )

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='face_profile',
        limit_choices_to={'role': 'student'},
        verbose_name='دانش‌آموز'
    )

    enrollment_status = models.CharField(
        max_length=20,
        choices=ENROLLMENT_STATUS_CHOICES,
        default='pending',
        verbose_name='وضعیت ثبت چهره'
    )

    reference_images_count = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='تعداد تصاویر مرجع'
    )

    last_enrollment_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='آخرین زمان ثبت چهره'
    )

    last_verification_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='آخرین زمان احراز هویت'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='فعال'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'پروفایل چهره {self.student.username}'

    class Meta:
        verbose_name = 'پروفایل چهره'
        verbose_name_plural = 'پروفایل‌های چهره'

    def update_enrollment_status(self):
        """به‌روزرسانی وضعیت ثبت چهره بر اساس تعداد امبدینگ‌ها"""
        embeddings = FaceEmbedding.objects.filter(
            student_id=self.student_id,
            is_active=True
        ).count()

        self.reference_images_count = embeddings

        if embeddings > 0:
            self.enrollment_status = 'enrolled'
        else:
            self.enrollment_status = 'pending'

        self.last_enrollment_at = timezone.now()
        self.save()

        logger.info(
            f'Face profile updated for student {self.student_id}. '
            f'Embeddings: {embeddings}, Status: {self.enrollment_status}'
        )


class FaceEmbedding(models.Model):
    """
    امبدینگ چهره یک دانش‌آموز

    امبدینگ به صورت باینری ذخیره می‌شود (فرمت: فرمت عددی).
    این روش با سازگاری کامل با محیط توسعه فعلی است
    و در آینده می‌توان به پایگاه داده برداری مهاجرت کرد.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='face_embeddings',
        limit_choices_to={'role': 'student'},
        verbose_name='دانش‌آموز'
    )

    embedding = models.BinaryField(
        verbose_name='امبدینگ چهره',
        help_text='امبدینگ چهره به صورت باینری'
    )

    model_name = models.CharField(
        max_length=100,
        default='arcface',
        verbose_name='نام مدل'
    )

    model_version = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='نسخه مدل'
    )

    embedding_dimension = models.PositiveIntegerField(
        default=512,
        verbose_name='بعد امبدینگ'
    )

    source_image = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='مسیر تصویر منبع'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='فعال'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'امبدینگ {self.id} برای {self.student.username}'

    class Meta:
        verbose_name = 'امبدینگ چهره'
        verbose_name_plural = 'امبدینگ‌های چهره'
        ordering = ['-created_at']

    def get_embedding_as_array(self):
        """دریافت امبدینگ به صورت آرایه"""
        import numpy as np
        if not self.embedding:
            return None
        try:
            return np.frombuffer(self.embedding, dtype=np.float32)
        except Exception:
            return None


class FaceVerificationSession(models.Model):
    """
    نشست جدید احراز هویت چهره

    این مدل فقط lifecycle verification را مدیریت می‌کند.
    Business rule اصلی حضور و غیاب همچنان روی AttendanceRequest/AttendanceResponse باقی می‌ماند.
    """
    session_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name='شناسه نشست'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='face_verification_sessions',
        limit_choices_to={'role': 'student'},
        verbose_name='دانش‌آموز'
    )
    attendance_request = models.ForeignKey(
        'dashboard.AttendanceRequest',
        on_delete=models.CASCADE,
        related_name='face_verification_sessions',
        verbose_name='درخواست حضور و غیاب'
    )
    status = models.CharField(
        max_length=20,
        choices=(
            ('pending', 'در انتظار'),
            ('in_progress', 'در حال انجام'),
            ('passed', 'موفق'),
            ('failed', 'ناموفق'),
            ('expired', 'منقضی شده'),
        ),
        default='pending',
        verbose_name='وضعیت نشست'
    )
    challenge_sequence = models.JSONField(
        default=list,
        blank=True,
        verbose_name='ترتیب چالش‌ها'
    )
    challenge_state = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='وضعیت داخلی چالش‌ها'
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='زمان شروع'
    )
    deadline_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='مهلت نشست'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='زمان تکمیل'
    )
    failure_code = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='کد ناموفق بودن'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'نشست احراز هویت چهره'
        verbose_name_plural = 'نشست‌های احراز هویت چهره'
        ordering = ['-created_at']

    def __str__(self):
        return f'نشست احراز هویت {self.student.username} - {self.get_status_display()}'

    @property
    def is_expired(self):
        if not self.deadline_at:
            return False
        return timezone.now() > self.deadline_at

    def mark_passed(self):
        if self.status == 'passed':
            return self
        self.status = 'passed'
        self.completed_at = timezone.now()
        self.failure_code = ''
        self.save(update_fields=['status', 'completed_at', 'failure_code', 'updated_at'])
        return self

    def mark_failed(self, failure_code=''):
        if self.status == 'passed':
            return self
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.failure_code = failure_code or ''
        self.save(update_fields=['status', 'completed_at', 'failure_code', 'updated_at'])
        return self

    def mark_expired(self, failure_code='EXPIRED'):
        if self.status == 'passed':
            return self
        self.status = 'expired'
        self.completed_at = timezone.now()
        self.failure_code = failure_code or 'EXPIRED'
        self.save(update_fields=['status', 'completed_at', 'failure_code', 'updated_at'])
        return self


class FaceVerificationLog(models.Model):
    """لاگ احراز هویت چهره"""

    VERIFICATION_STATUS_CHOICES = (
        ('verified', 'تایید شده'),
        ('suspicious', 'مشکوک'),
        ('failed', 'ناموفق'),
        ('error', 'خطا'),
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='face_verification_logs',
        limit_choices_to={'role': 'student'},
        verbose_name='دانش‌آموز'
    )

    status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        verbose_name='وضعیت'
    )

    similarity_score = models.FloatField(
        null=True, blank=True,
        verbose_name='امتیاز تطبیق'
    )

    liveness_passed = models.BooleanField(
        null=True, blank=True,
        verbose_name='لایونس تایید شده'
    )

    liveness_confidence = models.FloatField(
        null=True, blank=True,
        verbose_name='امتیاز لایونس'
    )

    total_frames = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='تعداد کل فریم‌ها'
    )

    valid_frames = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='تعداد فریم‌های معتبر'
    )

    failure_reason = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='دلیل عدم موفقیت'
    )

    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name='آدرس آی‌پی'
    )

    attendance_request = models.ForeignKey(
        'dashboard.AttendanceRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='face_verification_logs',
        verbose_name='درخواست حضور و غیاب'
    )

    session = models.ForeignKey(
        'face.FaceVerificationSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verification_logs',
        verbose_name='نشست احراز هویت'
    )
    challenge_result = models.JSONField(
        null=True,
        blank=True,
        verbose_name='نتیجه چالش کلاینت (فقط تله‌متری)'
    )
    processing_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='زمان پردازش (میلی‌ثانیه)'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'لاگ احراز هویت {self.student.username} - {self.get_status_display()}'

    class Meta:
        verbose_name = 'لاگ احراز هویت چهره'
        verbose_name_plural = 'لاگ‌های احراز هویت چهره'
        ordering = ['-created_at']