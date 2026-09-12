from django.db import models
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from .validators import validate_pdf_file, validate_image_file


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


class AIGenerationJob(models.Model):
    """
    درخواست تولید سوال با هوش مصنوعی
    فعلاً سرویس هوش مصنوعی به صورت ماک در فاز بعد استفاده می‌شود.
    """

    STATUS_CHOICES = (
        ('pending', 'در انتظار'),
        ('processing', 'در حال پردازش'),
        ('completed', 'تکمیل شده'),
        ('failed', 'ناموفق'),
    )

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_generation_jobs',
        limit_choices_to={'role': 'teacher'},
        verbose_name="معلم"
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='ai_generation_jobs',
        verbose_name="کلاس"
    )
    pdf_file = models.FileField(
        upload_to='ai_pdfs/',
        validators=[validate_pdf_file],
        verbose_name="فایل PDF"
    )
    prompt = models.TextField(blank=True, verbose_name="پرامپت معلم")
    topic = models.CharField(max_length=200, blank=True, verbose_name="مبحث")
    requested_count = models.PositiveSmallIntegerField(
        default=5,
        verbose_name="تعداد سوال"
    )
    default_timer_seconds = models.PositiveIntegerField(
        default=300,
        verbose_name="زمان پیش‌فرض هر سوال (ثانیه)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="وضعیت"
    )
    raw_response = models.TextField(blank=True, verbose_name="پاسخ خام هوش مصنوعی")
    error_message = models.TextField(blank=True, verbose_name="پیام خطا")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")

    def __str__(self):
        return f"درخواست هوش مصنوعی {self.id} - {self.classroom.name}"

    class Meta:
        verbose_name = "درخواست تولید سوال با هوش مصنوعی"
        verbose_name_plural = "درخواست‌های تولید سوال با هوش مصنوعی"
        ordering = ['-created_at']


class AttendanceCheck(models.Model):
    """هر بار حضور و غیاب در یک جلسه - مدل قدیمی"""

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
    """وضعیت حضور هر دانش‌آموز در هر حضور و غیاب - مدل قدیمی"""

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

    SOURCE_CHOICES = (
        ('ai', 'هوش مصنوعی'),
        ('manual', 'دستی'),
    )

    REVIEW_STATUS_CHOICES = (
        ('pending', 'در انتظار بررسی'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده'),
    )

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
        null=True,
        blank=True,
        verbose_name="جلسه"
    )
    review_status = models.CharField(
        max_length=10,
        choices=REVIEW_STATUS_CHOICES,
        default='approved',
        verbose_name="وضعیت بررسی"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_questions',
        verbose_name="ایجادکننده"
    )
    ai_job = models.ForeignKey(
        AIGenerationJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_questions',
        verbose_name="درخواست هوش مصنوعی"
    )
    source = models.CharField(
        max_length=10,
        choices=SOURCE_CHOICES,
        default='manual',
        verbose_name="منبع سوال"
    )
    is_approved = models.BooleanField(
        default=True,
        verbose_name="تایید شده"
    )
    topic = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="مبحث"
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
    timer_seconds = models.PositiveIntegerField(
        default=300,
        verbose_name="زمان پاسخ (ثانیه)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"سوال {self.id} - {self.classroom.name}"

    class Meta:
        verbose_name = "سوال"
        verbose_name_plural = "سوالات"
        ordering = ['-created_at']


class AttendanceRequest(models.Model):
    """
    درخواست حضور و غیاب / سوال معلم

    انواع:
    - فقط حضور و غیاب
    - فقط سوال
    - حضور و غیاب + سوال
    """

    REQUEST_TYPE_CHOICES = (
        ('face_only', 'فقط حضور و غیاب'),
        ('question_only', 'فقط سوال'),
        ('face_and_question', 'حضور و غیاب + سوال'),
    )

    STATUS_CHOICES = (
        ('active', 'فعال'),
        ('finished', 'پایان یافته'),
        ('canceled', 'لغو شده'),
    )

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='attendance_requests',
        limit_choices_to={'role': 'teacher'},
        verbose_name="معلم"
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='attendance_requests',
        verbose_name="کلاس"
    )
    session = models.ForeignKey(
        ClassSession,
        on_delete=models.CASCADE,
        related_name='attendance_requests',
        verbose_name="جلسه"
    )
    request_type = models.CharField(
        max_length=30,
        choices=REQUEST_TYPE_CHOICES,
        default='face_only',
        verbose_name="نوع درخواست"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="وضعیت"
    )
    face_time_seconds = models.PositiveIntegerField(
        default=120,
        verbose_name="زمان اسکن چهره (ثانیه)"
    )
    face_deadline_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="مهلت اسکن چهره"
    )
    questions = models.ManyToManyField(
        Question,
        through='AttendanceRequestQuestion',
        related_name='attendance_requests',
        blank=True,
        verbose_name="سوالات"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")

    def save(self, *args, **kwargs):
        creating = self._state.adding

        if creating:
            self.face_deadline_at = timezone.now() + timedelta(seconds=self.face_time_seconds)
        else:
            try:
                old = AttendanceRequest.objects.get(pk=self.pk)
                if old.face_time_seconds != self.face_time_seconds and self.status == 'active':
                    self.face_deadline_at = timezone.now() + timedelta(seconds=self.face_time_seconds)
            except AttendanceRequest.DoesNotExist:
                pass

        if not self.face_deadline_at:
            self.face_deadline_at = timezone.now() + timedelta(seconds=self.face_time_seconds)

        super().save(*args, **kwargs)

        # اگر درخواست شامل حضور و غیاب باشد، برای همه دانش‌آموزان کلاس رکورد اولیه می‌سازیم.
        if creating and self.requires_face:
            for student in self.classroom.students.all():
                AttendanceResponse.objects.get_or_create(
                    attendance_request=self,
                    student=student,
                    defaults={
                        'auto_status': 'pending',
                        'final_status': 'pending',
                    }
                )

    @property
    def requires_face(self):
        return self.request_type in ('face_only', 'face_and_question')

    @property
    def requires_question(self):
        return self.request_type in ('question_only', 'face_and_question')

    @property
    def is_face_expired(self):
        if self.requires_face and self.face_deadline_at:
            return timezone.now() > self.face_deadline_at
        return False

    @property
    def pending_review_count(self):
        return self.responses.filter(
            auto_status='suspicious',
            final_status='pending'
        ).count()

    def __str__(self):
        return f"درخواست {self.id} - {self.classroom.name} ({self.get_request_type_display()})"

    class Meta:
        verbose_name = "درخواست حضور و غیاب / سوال"
        verbose_name_plural = "درخواست‌های حضور و غیاب / سوال"
        ordering = ['-created_at']


class AttendanceRequestQuestion(models.Model):
    """
    رابطه بین درخواست و سوال

    چون ممکن است برای هر سوال زمان جداگانه مشخص شود،
    از مدل میانی استفاده می‌کنیم.
    """

    attendance_request = models.ForeignKey(
        AttendanceRequest,
        on_delete=models.CASCADE,
        related_name='request_questions',
        verbose_name="درخواست"
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='request_links',
        verbose_name="سوال"
    )
    order = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="ترتیب"
    )
    timer_seconds = models.PositiveIntegerField(
        default=300,
        verbose_name="زمان پاسخ (ثانیه)"
    )

    def __str__(self):
        return f"سوال {self.question.id} برای درخواست {self.attendance_request.id}"

    class Meta:
        verbose_name = "سوال درخواست"
        verbose_name_plural = "سوالات درخواست‌ها"
        unique_together = ('attendance_request', 'question')
        ordering = ['order', 'id']


class StudentReferencePhoto(models.Model):
    """
    عکس‌های مرجع دانش‌آموز برای مقایسه در اسکن چهره.
    ممکن است برای هر دانش‌آموز چند عکس مرجع ثبت شود.
    """

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reference_photos',
        limit_choices_to={'role': 'student'},
        verbose_name="دانش‌آموز"
    )
    image = models.ImageField(
        upload_to='students/reference/',
        validators=[validate_image_file],
        verbose_name="تصویر مرجع"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    def __str__(self):
        return f"عکس مرجع {self.student.username}"

    class Meta:
        verbose_name = "عکس مرجع دانش‌آموز"
        verbose_name_plural = "عکس‌های مرجع دانش‌آموزان"
        ordering = ['-created_at']


class AttendanceResponse(models.Model):
    """
    پاسخ هر دانش‌آموز به یک درخواست حضور و غیاب
    """

    AUTO_STATUS_CHOICES = (
        ('pending', 'در انتظار'),
        ('present', 'حاضر'),
        ('suspicious', 'مشکوک'),
        ('absent_mismatch', 'عدم تطابق'),
        ('no_response', 'عدم پاسخ'),
        ('not_applicable', 'نامرتبط'),
    )

    FINAL_STATUS_CHOICES = (
        ('pending', 'در انتظار'),
        ('present', 'حاضر'),
        ('absent', 'غایب'),
        ('not_applicable', 'نامرتبط'),
    )

    attendance_request = models.ForeignKey(
        AttendanceRequest,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name="درخواست"
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='attendance_responses',
        limit_choices_to={'role': 'student'},
        verbose_name="دانش‌آموز"
    )
    face_image = models.FileField(
        upload_to='attendance/captured/',
        validators=[validate_image_file],
        null=True,
        blank=True,
        verbose_name="تصویر گرفته‌شده"
    )
    confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name="درصد تطابق"
    )
    auto_status = models.CharField(
        max_length=20,
        choices=AUTO_STATUS_CHOICES,
        default='pending',
        verbose_name="وضعیت خودکار"
    )
    final_status = models.CharField(
        max_length=20,
        choices=FINAL_STATUS_CHOICES,
        default='pending',
        verbose_name="وضعیت نهایی"
    )
    face_submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان ارسال اسکن"
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_attendance_responses',
        verbose_name="بررسی‌کننده"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان بررسی"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")

    def apply_face_result(self, confidence, face_image=None):
        """
        اعمال نتیجه ارسالی از اپ دانش‌آموز

        قرارداد:
        - اگر درصد 90 یا بیشتر باشد: حاضر
        - اگر بین 70 تا 89 باشد: مشکوک
        - اگر کمتر از 70 باشد: عدم تطابق / غایب
        """

        confidence = float(confidence or 0)

        # اگر اپ به اشتباه عدد بین 0 و 1 فرستاد، آن را به درصد تبدیل می‌کنیم.
        if confidence <= 1:
            confidence = confidence * 100

        confidence = max(0.0, min(100.0, confidence))

        self.confidence = confidence

        if face_image:
            self.face_image = face_image

        self.face_submitted_at = timezone.now()

        if confidence >= 90:
            self.auto_status = 'present'
            self.final_status = 'present'
        elif confidence >= 70:
            self.auto_status = 'suspicious'
            self.final_status = 'pending'
        else:
            self.auto_status = 'absent_mismatch'
            self.final_status = 'absent'

        self.save()
        return self

    def mark_no_response(self):
        """
        وقتی دانش‌آموز در مهلت تعیین‌شده هیچ پاسخی ارسال نکند.
        """

        if self.auto_status == 'pending':
            self.auto_status = 'no_response'
            self.final_status = 'absent'
            self.save()

        return self

    def mark_no_response_if_expired(self):
        """
        اگر مهلت اسکن تمام شده باشد و هنوز پاسخی ثبت نشده باشد،
        وضعیت عدم پاسخ ثبت می‌شود.
        """

        if (
            self.attendance_request.requires_face and
            self.auto_status == 'pending' and
            self.attendance_request.is_face_expired
        ):
            return self.mark_no_response()

        return self

    def teacher_review(self, approved, reviewer):
        """
        تایید یا رد دستی دانش‌آموز مشکوک توسط معلم
        """

        if self.auto_status != 'suspicious':
            return self

        self.final_status = 'present' if approved else 'absent'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()

        # بعد از تایید یا رد، تصویر گرفته‌شده حذف می‌شود.
        if self.face_image:
            self.face_image.delete(save=False)
            self.face_image = None
            self.save(update_fields=['face_image'])

        return self

    def __str__(self):
        return f"پاسخ {self.student.username} به درخواست {self.attendance_request.id}"

    class Meta:
        verbose_name = "پاسخ حضور و غیاب"
        verbose_name_plural = "پاسخ‌های حضور و غیاب"
        unique_together = ('attendance_request', 'student')
        ordering = ['-created_at']


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
    attendance_request = models.ForeignKey(
        AttendanceRequest,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='student_answers',
        verbose_name="درخواست حضور / سوال"
    )
    attendance_response = models.ForeignKey(
        AttendanceResponse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_answers',
        verbose_name="پاسخ حضور مرتبط"
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
        ordering = ['-answered_at']


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