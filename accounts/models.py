import secrets

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'دانش آموز'),
        ('teacher', 'معلم'),
        ('assistant', 'معاون'),
        ('principal', 'مدیر مدرسه'),
        ('district_admin', 'مسئول منطقه'),
        ('county_admin', 'مسئول شهرستان'),
        ('province_admin', 'مسئول استان'),
        ('country_admin', 'مسئول کشور'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    national_id = models.CharField(
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        verbose_name="کد ملی"
    )

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"


class StudentProfile(models.Model):
    """پروفایل کامل دانش‌آموز با اطلاعات والدین"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name="دانش‌آموز"
    )

    # اطلاعات والدین
    father_name = models.CharField(max_length=100, blank=True, verbose_name="نام پدر")
    mother_name = models.CharField(max_length=100, blank=True, verbose_name="نام مادر")
    parent_phone = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="شماره تماس والدین"
    )
    parent_phone_2 = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="شماره تماس اضطراری"
    )

    # اطلاعات تماس و آدرس
    phone = models.CharField(max_length=15, blank=True, verbose_name="شماره موبایل دانش‌آموز")
    address = models.TextField(blank=True, verbose_name="آدرس منزل")
    city = models.CharField(max_length=50, blank=True, verbose_name="شهر")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="کد پستی")

    # اطلاعات پزشکی
    blood_type = models.CharField(
        max_length=5,
        blank=True,
        verbose_name="گروه خونی"
    )
    medical_conditions = models.TextField(
        blank=True,
        verbose_name="بیماری‌های خاص/حساسیت‌ها"
    )

    # اطلاعات تحصیلی
    enrollment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاریخ ثبت‌نام"
    )
    previous_school = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="مدرسه قبلی"
    )

    # متادیتا
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"پروفایل {self.user.get_full_name() or self.user.username}"

    class Meta:
        verbose_name = "پروفایل دانش‌آموز"
        verbose_name_plural = "پروفایل‌های دانش‌آموزان"


class APIToken(models.Model):
    """
    توکن ساده برای احراز هویت اپ جداگانه دانش‌آموز

    در فازهای بعد برای اپ ری‌اکت استفاده می‌شود.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_token',
        verbose_name="کاربر"
    )
    key = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        verbose_name="کلید توکن"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاریخ انقضا"
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def __str__(self):
        return f"API Token - {self.user.username}"

    class Meta:
        verbose_name = "توکن API"
        verbose_name_plural = "توکن‌های API"