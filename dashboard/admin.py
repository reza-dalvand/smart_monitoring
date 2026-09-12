from django.contrib import admin

from .models import (
    Classroom,
    ClassSession,
    AttendanceCheck,
    AttendanceRecord,
    Question,
    StudentAnswer,
    WeeklySchedule,
    AIGenerationJob,
    StudentReferencePhoto,
    AttendanceRequest,
    AttendanceRequestQuestion,
    AttendanceResponse,
)


class AttendanceRequestQuestionInline(admin.TabularInline):
    model = AttendanceRequestQuestion
    extra = 1
    autocomplete_fields = ('question',)
    fields = ('question', 'order', 'timer_seconds')


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'grade', 'field', 'teacher_name', 'created_at')
    list_filter = ('grade', 'field', 'subject')
    search_fields = ('name', 'subject', 'teacher_name')
    filter_horizontal = ('students',)


@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'classroom', 'topic', 'session_date')
    list_filter = ('classroom',)
    search_fields = ('topic', 'classroom__name')


@admin.register(AIGenerationJob)
class AIGenerationJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'teacher', 'classroom', 'requested_count', 'status', 'created_at')
    list_filter = ('status', 'classroom')
    search_fields = ('teacher__username', 'teacher__first_name', 'teacher__last_name', 'classroom__name', 'topic')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AttendanceCheck)
class AttendanceCheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'check_time')


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'attendance_check', 'status')
    list_filter = ('status',)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'classroom',
        'session',
        'topic',
        'source',
        'review_status',
        'is_approved',
        'timer_seconds',
        'correct_answer',
        'created_at',
    )
    list_filter = ('source', 'review_status', 'is_approved', 'classroom', 'session')
    search_fields = ('text', 'topic', 'classroom__name')
    readonly_fields = ('created_at',)
    actions = ('approve_questions', 'reject_questions')

    @admin.action(description='تایید سوال‌های انتخاب‌شده')
    def approve_questions(self, request, queryset):
        updated = queryset.update(is_approved=True, review_status='approved')
        self.message_user(request, f'{updated} سوال تایید شد.')

    @admin.action(description='رد سوال‌های انتخاب‌شده')
    def reject_questions(self, request, queryset):
        updated = queryset.update(is_approved=False, review_status='rejected')
        self.message_user(request, f'{updated} سوال رد شد.')

        
@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ('student', 'question', 'attendance_request', 'selected_choice', 'is_correct', 'answered_at')
    list_filter = ('is_correct',)
    search_fields = ('student__username', 'question__text')
    readonly_fields = ('answered_at',)


@admin.register(WeeklySchedule)
class WeeklyScheduleAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'day_of_week', 'start_time', 'end_time', 'room')
    list_filter = ('day_of_week', 'classroom', 'classroom__grade', 'classroom__field')
    search_fields = ('classroom__name', 'classroom__subject')


@admin.register(StudentReferencePhoto)
class StudentReferencePhotoAdmin(admin.ModelAdmin):
    list_display = ('student', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('student__username', 'student__first_name', 'student__last_name')
    readonly_fields = ('created_at',)


@admin.register(AttendanceRequest)
class AttendanceRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'classroom',
        'teacher',
        'request_type',
        'status',
        'face_time_seconds',
        'face_deadline_at',
        'created_at',
    )
    list_filter = ('request_type', 'status', 'classroom')
    search_fields = ('classroom__name', 'teacher__username')
    readonly_fields = ('face_deadline_at', 'created_at', 'updated_at')
    inlines = [AttendanceRequestQuestionInline]


@admin.register(AttendanceResponse)
class AttendanceResponseAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'attendance_request',
        'auto_status',
        'final_status',
        'confidence',
        'face_submitted_at',
        'reviewed_at',
    )
    list_filter = ('auto_status', 'final_status', 'attendance_request__classroom')
    search_fields = ('student__username', 'student__first_name', 'student__last_name')
    readonly_fields = ('created_at', 'updated_at')