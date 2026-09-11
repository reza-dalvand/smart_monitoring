from django.contrib import admin
from .models import (
    Classroom, ClassSession, AttendanceCheck,
    AttendanceRecord, Question, StudentAnswer,
    WeeklySchedule
)


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


@admin.register(AttendanceCheck)
class AttendanceCheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'check_time')


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'attendance_check', 'status')
    list_filter = ('status',)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'classroom', 'session', 'correct_answer', 'created_at')


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ('student', 'question', 'selected_choice', 'is_correct')
    list_filter = ('is_correct',)


@admin.register(WeeklySchedule)
class WeeklyScheduleAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'day_of_week', 'start_time', 'end_time', 'room')
    list_filter = ('day_of_week', 'classroom', 'classroom__grade', 'classroom__field')
    search_fields = ('classroom__name', 'classroom__subject')