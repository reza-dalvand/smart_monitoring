from django.db import models
from accounts.models import User

class Classroom(models.Model):
    """کلاس درس"""
    GRADE_CHOICES = (
        ('10', 'دهم'),
        ('11', 'یازدهم'),
        ('12', 'دوازدهم'),
    )
    
    FIELD_CHOICES = (
        ('computer', 'کامپیوتر'),
        ('electrical', 'برق'),
        ('mechanical', 'مکانیک'),
        ('accounting', 'حسابداری'),
        ('math', 'ریاضی'),
        ('experimental', 'تجربی'),
        ('humanities', 'انسانی'),
    )
    
    name = models.CharField(max_length=100, verbose_name="نام کلاس")
    subject = models.CharField(max_length=100, verbose_name="درس")
    grade = models.CharField(
        max_length=2,
        choices=GRADE_CHOICES,
        default='10',
        verbose_name="پایه تحصیلی"
    )
    field = models.CharField(
        max_length=20,
        choices=FIELD_CHOICES,
        default='math',
        verbose_name="رشته تحصیلی"
    )
    teacher_name = models.CharField(
        max_length=100,
        verbose_name="نام معلم"
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='taught_classes',
        verbose_name="کاربر معلم (اختیاری)"
    )
    students = models.ManyToManyField(
        User,
        related_name='enrolled_classes',
        blank=True,
        verbose_name="دانش‌آموزان"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.subject} ({self.get_grade_display()} {self.get_field_display()})"
    
    class Meta:
        verbose_name = "کلاس"
        verbose_name_plural = "کلاس‌ها"


class ClassSession(models.Model):
    """جلسه کلاس"""
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name="کلاس"
    )
    session_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ جلسه")
    topic = models.CharField(max_length=200, blank=True, null=True, verbose_name="موضوع جلسه")
    
    def __str__(self):
        return f"جلسه {self.id} - {self.classroom.name}"
    
    class Meta:
        verbose_name = "جلسه کلاس"
        verbose_name_plural = "جلسات کلاس"


class AttendanceCheck(models.Model):
    """هر بار حضور و غیاب در یک جلسه"""
    session = models.ForeignKey(
        ClassSession,
        on_delete=models.CASCADE,
        related_name='attendance_checks',
        verbose_name="جلسه"
    )
    check_time = models.DateTimeField(auto_now_add=True, verbose_name="زمان حضور و غیاب")
    
    def __str__(self):
        return f"حضور و غیاب {self.id} - جلسه {self.session.id}"
    
    class Meta:
        verbose_name = "حضور و غیاب"
        verbose_name_plural = "حضور و غیاب‌ها"


class AttendanceRecord(models.Model):
    """وضعیت حضور هر دانش‌آموز در هر حضور و غیاب"""
    STATUS_CHOICES = (
        ('present', 'حاضر'),
        ('absent', 'غایب'),
    )
    attendance_check = models.ForeignKey(
        AttendanceCheck,
        on_delete=models.CASCADE,
        related_name='records',
        verbose_name="حضور و غیاب"
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        verbose_name="دانش‌آموز"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='present',
        verbose_name="وضعیت"
    )
    
    def __str__(self):
        return f"{self.student.username} - {self.get_status_display()}"
    
    class Meta:
        verbose_name = "رکورد حضور"
        verbose_name_plural = "رکوردهای حضور"


class Question(models.Model):
    """سوال چهار گزینه‌ای"""
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name="کلاس"
    )
    session = models.ForeignKey(
        ClassSession,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name="جلسه"
    )
    text = models.TextField(verbose_name="متن سوال")
    choice_a = models.CharField(max_length=200, verbose_name="گزینه الف")
    choice_b = models.CharField(max_length=200, verbose_name="گزینه ب")
    choice_c = models.CharField(max_length=200, verbose_name="گزینه ج")
    choice_d = models.CharField(max_length=200, verbose_name="گزینه د")
    correct_answer = models.CharField(
        max_length=1,
        choices=[('a', 'الف'), ('b', 'ب'), ('c', 'ج'), ('d', 'د')],
        verbose_name="پاسخ صحیح"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"سوال {self.id} - {self.classroom.name}"
    
    class Meta:
        verbose_name = "سوال"
        verbose_name_plural = "سوالات"


class StudentAnswer(models.Model):
    """پاسخ دانش‌آموز به سوال"""
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name="سوال"
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='student_answers',
        verbose_name="دانش‌آموز"
    )
    selected_choice = models.CharField(
        max_length=1,
        choices=[('a', 'الف'), ('b', 'ب'), ('c', 'ج'), ('d', 'د')],
        verbose_name="گزینه انتخابی"
    )
    is_correct = models.BooleanField(default=False, verbose_name="پاسخ صحیح")
    answered_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.student.username} - سوال {self.question.id}"
    
    class Meta:
        verbose_name = "پاسخ دانش‌آموز"
        verbose_name_plural = "پاسخ‌های دانش‌آموزان"


class WeeklySchedule(models.Model):
    """برنامه هفتگی کلاس‌ها"""
    WEEKDAY_CHOICES = (
        ('saturday', 'شنبه'),
        ('sunday', 'یکشنبه'),
        ('monday', 'دوشنبه'),
        ('tuesday', 'سه‌شنبه'),
        ('wednesday', 'چهارشنبه'),
    )
    
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name="کلاس"
    )
    day_of_week = models.CharField(
        max_length=10,
        choices=WEEKDAY_CHOICES,
        verbose_name="روز هفته"
    )
    start_time = models.TimeField(verbose_name="ساعت شروع")
    end_time = models.TimeField(verbose_name="ساعت پایان")
    room = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="شماره اتاق/کلاس"
    )
    
    def __str__(self):
        return f"{self.classroom.subject} - {self.get_day_of_week_display()} {self.start_time.strftime('%H:%M')}"
    
    class Meta:
        verbose_name = "برنامه هفتگی"
        verbose_name_plural = "برنامه‌های هفتگی"
        ordering = ['day_of_week', 'start_time']