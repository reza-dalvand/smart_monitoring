from django.contrib.auth.models import AbstractUser
from django.db import models

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
    national_id = models.CharField(max_length=10, unique=True, null=True, blank=True, verbose_name="کد ملی")
    
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