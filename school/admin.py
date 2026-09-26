from django.contrib import admin
from .models import (
    SchoolStaffAssignment, StudentSchoolStatus,
    FollowUpCase, FollowUpCaseNote,
    SchoolAlert, SchoolTask, SchoolAuditLog,
    SchoolSettings, AttendanceOverrideLog, AbsenceReview,
)


@admin.register(SchoolStaffAssignment)
class SchoolStaffAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'staff_role', 'assistant_type',
                    'is_active', 'start_date', 'end_date')
    list_filter = ('staff_role', 'assistant_type', 'is_active', 'school')
    search_fields = ('user__username', 'user__first_name', 'school__name')


@admin.register(StudentSchoolStatus)
class StudentSchoolStatusAdmin(admin.ModelAdmin):
    list_display = ('student', 'school', 'status', 'updated_at')
    list_filter = ('status', 'school')
    search_fields = ('student__username',)


@admin.register(FollowUpCase)
class FollowUpCaseAdmin(admin.ModelAdmin):
    list_display = ('case_number', 'title', 'school', 'status',
                    'priority', 'created_at')
    list_filter = ('status', 'priority', 'category', 'school')
    search_fields = ('title', 'student__username')


@admin.register(SchoolAlert)
class SchoolAlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'school', 'alert_type', 'severity',
                    'is_resolved', 'created_at')
    list_filter = ('alert_type', 'severity', 'is_resolved')


@admin.register(SchoolTask)
class SchoolTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'school', 'assigned_to', 'status', 'due_date')
    list_filter = ('status',)


@admin.register(SchoolAuditLog)
class SchoolAuditLogAdmin(admin.ModelAdmin):
    list_display = ('actor', 'school', 'action', 'created_at')
    list_filter = ('action', 'school')
    readonly_fields = ('actor', 'school', 'action', 'object_type',
                       'object_id', 'old_values', 'new_values',
                       'reason', 'ip_address', 'created_at')


@admin.register(SchoolSettings)
class SchoolSettingsAdmin(admin.ModelAdmin):
    list_display = ('school', 'academic_year')


@admin.register(AttendanceOverrideLog)
class AttendanceOverrideLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'old_status', 'new_status',
                    'overridden_by', 'created_at')
    list_filter = ('school',)


@admin.register(AbsenceReview)
class AbsenceReviewAdmin(admin.ModelAdmin):
    list_display = ('student', 'review_status', 'review_date')
    list_filter = ('review_status',)