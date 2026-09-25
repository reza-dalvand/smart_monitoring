"""
مدل‌های سازمانی برای پنل مسئول کشوری
ساختار: کشور → استان → منطقه → مدرسه → کلاس
"""
from django.db import models
from django.conf import settings


class Province(models.Model):
    """استان"""
    name = models.CharField(max_length=100, unique=True, verbose_name="نام استان")
    code = models.CharField(max_length=10, unique=True, blank=True, verbose_name="کد استان")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "استان"
        verbose_name_plural = "استان‌ها"
        ordering = ['name']

    def __str__(self):
        return self.name


class District(models.Model):
    """منطقه آموزشی"""
    province = models.ForeignKey(
        Province, on_delete=models.CASCADE,
        related_name='districts', verbose_name="استان"
    )
    name = models.CharField(max_length=100, verbose_name="نام منطقه")
    code = models.CharField(max_length=20, blank=True, verbose_name="کد منطقه")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "منطقه آموزشی"
        verbose_name_plural = "مناطق آموزشی"
        ordering = ['province', 'name']
        unique_together = ('province', 'name')

    def __str__(self):
        return f"{self.province.name} - {self.name}"


class School(models.Model):
    """مدرسه"""
    SCHOOL_TYPE_CHOICES = (
        ('public', 'دولتی'),
        ('private', 'غیرانتفاعی'),
        ('technical', 'فنی و حرفه‌ای'),
        ('special', 'استثنایی'),
    )
    name = models.CharField(max_length=200, verbose_name="نام مدرسه")
    district = models.ForeignKey(
        District, on_delete=models.CASCADE,
        related_name='schools', verbose_name="منطقه آموزشی"
    )
    school_type = models.CharField(
        max_length=20, choices=SCHOOL_TYPE_CHOICES,
        default='public', verbose_name="نوع مدرسه"
    )
    address = models.TextField(blank=True, verbose_name="آدرس")
    phone = models.CharField(max_length=20, blank=True, verbose_name="تلفن")
    principal = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_schools',
        limit_choices_to={'role': 'principal'}, verbose_name="مدیر مدرسه"
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مدرسه"
        verbose_name_plural = "مدارس"
        ordering = ['district__province', 'district', 'name']

    def __str__(self):
        return self.name

    @property
    def province(self):
        return self.district.province

    @property
    def students_count(self):
        from accounts.models import User
        return User.objects.filter(
            role='student', enrolled_classes__school=self
        ).distinct().count()

    @property
    def teachers_count(self):
        from accounts.models import User
        return User.objects.filter(
            role='teacher', taught_classes__school=self
        ).distinct().count()

    @property
    def classrooms_count(self):
        return self.classrooms.count()


class NationalAuditLog(models.Model):
    """لاگ عملیات مسئول کشوری"""
    ACTION_CHOICES = (
        ('view_dashboard', 'مشاهده داشبورد'),
        ('view_province', 'مشاهده استان'),
        ('view_district', 'مشاهده منطقه'),
        ('view_school', 'مشاهده مدرسه'),
        ('view_reports', 'مشاهده گزارش‌ها'),
        ('export_data', 'خروجی داده'),
        ('update_policy', 'به‌روزرسانی سیاست'),
        ('view_api', 'استفاده از API'),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='national_audit_logs', verbose_name="کاربر"
    )
    action = models.CharField(
        max_length=50, choices=ACTION_CHOICES, verbose_name="عملیات"
    )
    scope = models.CharField(
        max_length=20, default='national', verbose_name="محدوده"
    )
    scope_id = models.IntegerField(null=True, blank=True, verbose_name="شناسه محدوده")
    scope_name = models.CharField(
        max_length=200, blank=True, default='', verbose_name="نام محدوده"
    )
    details = models.JSONField(
        default=dict, blank=True, verbose_name="جزئیات"
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name="آدرس IP"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان")

    class Meta:
        verbose_name = "لاگ عملیات کشوری"
        verbose_name_plural = "لاگ‌های عملیات کشوری"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()}"


class NationalPolicy(models.Model):
    """سیاست‌های عمومی سامانه در سطح کشوری"""
    key = models.CharField(
        max_length=100, unique=True, verbose_name="کلید"
    )
    value = models.TextField(verbose_name="مقدار")
    description = models.TextField(blank=True, verbose_name="توضیح")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='updated_policies',
        verbose_name="به‌روزرسانی توسط"
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "سیست عمومی"
        verbose_name_plural = "سیاست‌های عمومی"
        ordering = ['key']

    def __str__(self):
        return f"{self.key} = {self.value[:50]}"