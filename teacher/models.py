"""
مدل‌های جدید ماژول معلم.
این مدل‌ها مکمل مدل‌های موجود هستند.
از مدل‌های موجود (Classroom, ClassSession, Question, ...) استفاده می‌شود.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from .constants import (
    SessionStatus,
    ParticipationLevel,
    ParticipationSource,
    AssessmentStatus,
    AssessmentQuestionStatus,
    HomeworkStatus,
    SubmissionStatus,
    FeedbackType,
    FollowUpSuggestionStatus,
    QuestionDifficulty,
)


# ══════════════════════════════════════════════════════════
#  1. Session Enhancement (فیلدهای جدید برای ClassSession)
#     بدون حذف مدل موجود، فیلدهای جدید اضافه می‌شوند
# ══════════════════════════════════════════════════════════
class SessionExtension(models.Model):
    """
    فیلدهای تکمیلی برای جلسه آموزشی.
    به‌جای تغییر مستقیم ClassSession (که وابستگی‌های زیادی دارد)،
    از یک مدل الحاقی استفاده می‌کنیم.
    """
    session = models.OneToOneField(
        'dashboard.ClassSession',
        on_delete=models.CASCADE,
        related_name='extension',
        verbose_name='جلسه',
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='session_extensions',
        limit_choices_to={'role': 'teacher'},
        verbose_name='معلم',
    )
    status = models.CharField(
        max_length=20,
        choices=SessionStatus.CHOICES,
        default=SessionStatus.SCHEDULED,
        verbose_name='وضعیت جلسه',
    )
    subject = models.CharField(
        max_length=200, blank=True, default='',
        verbose_name='درس',
    )
    learning_objectives = models.TextField(
        blank=True, default='',
        verbose_name='اهداف یادگیری',
    )
    description = models.TextField(
        blank=True, default='',
        verbose_name='توضیحات',
    )
    started_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='زمان شروع',
    )
    ended_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='زمان پایان',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'اطلاعات تکمیلی جلسه'
        verbose_name_plural = 'اطلاعات تکمیلی جلسات'

    def __str__(self):
        return f'جلسه {self.session_id} - {self.get_status_display()}'


# ══════════════════════════════════════════════════════════
#  2. ParticipationRecord
#     مشارکت ≠ حضور
# ══════════════════════════════════════════════════════════
class ParticipationRecord(models.Model):
    """
    رکورد مشارکت دانش‌آموز در یک جلسه.
    مشارکت می‌تواند دستی (توسط معلم) یا خودکار باشد.
    """
    session = models.ForeignKey(
        'dashboard.ClassSession',
        on_delete=models.CASCADE,
        related_name='participation_records',
        verbose_name='جلسه',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='participation_records',
        limit_choices_to={'role': 'student'},
        verbose_name='دانش‌آموز',
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recorded_participations',
        verbose_name='معلم',
    )
    level = models.CharField(
        max_length=10,
        choices=ParticipationLevel.CHOICES,
        verbose_name='سطح مشارکت',
    )
    score = models.FloatField(
        null=True, blank=True,
        verbose_name='امتیاز مشارکت (0-100)',
    )
    source = models.CharField(
        max_length=30,
        choices=ParticipationSource.CHOICES,
        default=ParticipationSource.MANUAL,
        verbose_name='منبع ثبت',
    )
    note = models.TextField(
        blank=True, default='',
        verbose_name='یادداشت',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'رکورد مشارکت'
        verbose_name_plural = 'رکوردهای مشارکت'
        unique_together = ('session', 'student', 'source')
        ordering = ['-created_at']

    def __str__(self):
        return (
            f'{self.student.username} - '
            f'{self.get_level_display()} '
            f'({self.session_id})'
        )

    def save(self, *args, **kwargs):
        if self.level and self.score is None:
            self.score = ParticipationLevel.SCORE_MAP.get(
                self.level, 0
            )
        super().save(*args, **kwargs)


# ══════════════════════════════════════════════════════════
#  3. Assessment System
# ══════════════════════════════════════════════════════════
class Assessment(models.Model):
    """ارزیابی / آزمون"""
    title = models.CharField(
        max_length=200, verbose_name='عنوان',
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_assessments',
        verbose_name='معلم',
    )
    classroom = models.ForeignKey(
        'dashboard.Classroom',
        on_delete=models.CASCADE,
        related_name='assessments',
        verbose_name='کلاس',
    )
    session = models.ForeignKey(
        'dashboard.ClassSession',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assessments',
        verbose_name='جلسه مرتبط',
    )
    topic = models.CharField(
        max_length=200, blank=True, default='',
        verbose_name='موضوع',
    )
    status = models.CharField(
        max_length=20,
        choices=AssessmentStatus.CHOICES,
        default=AssessmentStatus.DRAFT,
        verbose_name='وضعیت',
    )
    duration_minutes = models.PositiveIntegerField(
        default=30, verbose_name='مدت (دقیقه)',
    )
    total_score = models.FloatField(
        default=20.0, verbose_name='نمره کل',
    )
    start_time = models.DateTimeField(
        null=True, blank=True, verbose_name='زمان شروع',
    )
    end_time = models.DateTimeField(
        null=True, blank=True, verbose_name='زمان پایان',
    )
    # تنظیمات
    randomize_questions = models.BooleanField(
        default=False, verbose_name='ترتیب تصادفی سوالات',
    )
    show_result = models.BooleanField(
        default=True, verbose_name='نمایش نتیجه به دانش‌آموز',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ارزیابی'
        verbose_name_plural = 'ارزیابی‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.classroom.name})'


class AssessmentQuestion(models.Model):
    """رابطه ارزیابی و سوال"""
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name='ارزیابی',
    )
    question = models.ForeignKey(
        'dashboard.Question',
        on_delete=models.CASCADE,
        related_name='assessment_links',
        verbose_name='سوال',
    )
    order = models.PositiveSmallIntegerField(
        default=1, verbose_name='ترتیب',
    )
    score = models.FloatField(
        default=1.0, verbose_name='نمره سوال',
    )
    difficulty = models.CharField(
        max_length=10,
        choices=QuestionDifficulty.CHOICES,
        default=QuestionDifficulty.MEDIUM,
        verbose_name='سطح دشواری',
    )

    class Meta:
        verbose_name = 'سوال ارزیابی'
        verbose_name_plural = 'سوالات ارزیابی‌ها'
        unique_together = ('assessment', 'question')
        ordering = ['order']

    def __str__(self):
        return f'سوال {self.order} - {self.assessment.title}'


class StudentAssessmentResponse(models.Model):
    """پاسخ دانش‌آموز به ارزیابی"""
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='student_responses',
        verbose_name='ارزیابی',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assessment_responses',
        verbose_name='دانش‌آموز',
    )
    question = models.ForeignKey(
        'dashboard.Question',
        on_delete=models.CASCADE,
        related_name='assessment_student_responses',
        verbose_name='سوال',
    )
    selected_choice = models.CharField(
        max_length=1,
        choices=[('a', 'الف'), ('b', 'ب'), ('c', 'ج'), ('d', 'د')],
        verbose_name='گزینه انتخابی',
    )
    is_correct = models.BooleanField(
        default=False, verbose_name='پاسخ صحیح',
    )
    score = models.FloatField(
        null=True, blank=True, verbose_name='نمره',
    )
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'پاسخ دانش‌آموز به ارزیابی'
        verbose_name_plural = 'پاسخ‌های دانش‌آموزان به ارزیابی‌ها'
        unique_together = ('assessment', 'student', 'question')

    def __str__(self):
        return f'{self.student.username} - {self.assessment.title}'


# ══════════════════════════════════════════════════════════
#  4. Homework System
# ══════════════════════════════════════════════════════════
class Homework(models.Model):
    """تکلیف"""
    title = models.CharField(
        max_length=200, verbose_name='عنوان',
    )
    description = models.TextField(
        blank=True, default='', verbose_name='شرح تکلیف',
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_homeworks',
        verbose_name='معلم',
    )
    classroom = models.ForeignKey(
        'dashboard.Classroom',
        on_delete=models.CASCADE,
        related_name='homeworks',
        verbose_name='کلاس',
    )
    session = models.ForeignKey(
        'dashboard.ClassSession',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='homeworks',
        verbose_name='جلسه مرتبط',
    )
    topic = models.CharField(
        max_length=200, blank=True, default='',
        verbose_name='موضوع',
    )
    status = models.CharField(
        max_length=20,
        choices=HomeworkStatus.CHOICES,
        default=HomeworkStatus.ACTIVE,
        verbose_name='وضعیت',
    )
    deadline = models.DateTimeField(
        verbose_name='مهلت ارسال',
    )
    max_score = models.FloatField(
        default=20.0, verbose_name='حداکثر نمره',
    )
    attachment = models.FileField(
        upload_to='homework/attachments/',
        null=True, blank=True,
        verbose_name='پیوست',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'تکلیف'
        verbose_name_plural = 'تکالیف'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.classroom.name})'


class HomeworkSubmission(models.Model):
    """ارسال تکلیف توسط دانش‌آموز"""
    homework = models.ForeignKey(
        Homework,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name='تکلیف',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='homework_submissions',
        verbose_name='دانش‌آموز',
    )
    status = models.CharField(
        max_length=20,
        choices=SubmissionStatus.CHOICES,
        default=SubmissionStatus.NOT_SUBMITTED,
        verbose_name='وضعیت',
    )
    content = models.TextField(
        blank=True, default='',
        verbose_name='متن پاسخ',
    )
    attachment = models.FileField(
        upload_to='homework/submissions/',
        null=True, blank=True,
        verbose_name='فایل ارسالی',
    )
    score = models.FloatField(
        null=True, blank=True,
        verbose_name='نمره',
    )
    feedback = models.TextField(
        blank=True, default='',
        verbose_name='بازخورد معلم',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_submissions',
        verbose_name='بررسی‌کننده',
    )
    reviewed_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='زمان بررسی',
    )
    submitted_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='زمان ارسال',
    )

    class Meta:
        verbose_name = 'ارسال تکلیف'
        verbose_name_plural = 'ارسال‌های تکلیف'
        unique_together = ('homework', 'student')

    def __str__(self):
        return f'{self.student.username} - {self.homework.title}'


# ══════════════════════════════════════════════════════════
#  5. TeacherNote
# ══════════════════════════════════════════════════════════
class TeacherNote(models.Model):
    """یادداشت آموزشی خصوصی معلم برای دانش‌آموز"""
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_notes',
        verbose_name='معلم',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_notes',
        verbose_name='دانش‌آموز',
    )
    classroom = models.ForeignKey(
        'dashboard.Classroom',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='teacher_notes',
        verbose_name='کلاس مرتبط',
    )
    content = models.TextField(verbose_name='متن یادداشت')
    is_sensitive = models.BooleanField(
        default=False,
        verbose_name='حساس (فقط با مجوز قابل مشاهده)',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'یادداشت معلم'
        verbose_name_plural = 'یادداشت‌های معلمان'
        ordering = ['-created_at']

    def __str__(self):
        return f'یادداشت {self.teacher.username} برای {self.student.username}'


# ══════════════════════════════════════════════════════════
#  6. TeacherFeedback
# ══════════════════════════════════════════════════════════
class TeacherFeedback(models.Model):
    """بازخورد معلم به دانش‌آموز"""
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='given_feedbacks',
        verbose_name='معلم',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_feedbacks',
        verbose_name='دانش‌آموز',
    )
    feedback_type = models.CharField(
        max_length=20,
        choices=FeedbackType.CHOICES,
        default=FeedbackType.GENERAL,
        verbose_name='نوع بازخورد',
    )
    score = models.FloatField(
        null=True, blank=True,
        verbose_name='نمره',
    )
    content = models.TextField(
        verbose_name='متن بازخورد',
    )
    # ارجاع به شیء مرتبط (اختیاری)
    related_assessment = models.ForeignKey(
        Assessment,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='feedbacks',
        verbose_name='ارزیابی مرتبط',
    )
    related_homework = models.ForeignKey(
        Homework,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='feedbacks',
        verbose_name='تکلیف مرتبط',
    )
    is_ai_draft = models.BooleanField(
        default=False,
        verbose_name='پیش‌نویس هوش مصنوعی',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'بازخورد معلم'
        verbose_name_plural = 'بازخوردهای معلمان'
        ordering = ['-created_at']

    def __str__(self):
        return f'بازخورد برای {self.student.username}'


# ══════════════════════════════════════════════════════════
#  7. FollowUpSuggestion
#     معلم فقط پیشنهاد می‌دهد، مدیریت با معاون/مدیر است
# ══════════════════════════════════════════════════════════
class FollowUpSuggestion(models.Model):
    """
    پیشنهاد پیگیری معلم.
    این مدل با FollowUpCase متفاوت است.
    معلم پیشنهاد می‌دهد → معاون/مدیر تصمیم می‌گیرد.
    """
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='followup_suggestions',
        verbose_name='معلم',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_suggestions',
        verbose_name='دانش‌آموز',
    )
    classroom = models.ForeignKey(
        'dashboard.Classroom',
        on_delete=models.CASCADE,
        related_name='followup_suggestions',
        verbose_name='کلاس',
    )
    reason = models.CharField(
        max_length=200,
        verbose_name='دلیل پیشنهاد',
    )
    details = models.TextField(
        blank=True, default='',
        verbose_name='توضیحات',
    )
    # داده‌های شواهد (Explainability)
    evidence = models.JSONField(
        default=dict, blank=True,
        verbose_name='شواهد (داده‌های پشتیبان)',
    )
    status = models.CharField(
        max_length=20,
        choices=FollowUpSuggestionStatus.CHOICES,
        default=FollowUpSuggestionStatus.SUBMITTED,
        verbose_name='وضعیت',
    )
    # ارجاع به FollowUpCase در صورت تبدیل
    converted_case = models.ForeignKey(
        'school.FollowUpCase',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='teacher_suggestions',
        verbose_name='پرونده مرتبط',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'پیشنهاد پیگیری معلم'
        verbose_name_plural = 'پیشنهادهای پیگیری معلمان'
        ordering = ['-created_at']

    def __str__(self):
        return (
            f'پیشنهاد {self.teacher.username} '
            f'برای {self.student.username}'
        )