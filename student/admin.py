from django.contrib import admin
from .models import (
    StudentRequest, StudentFaceChangeRequest,
    SessionMaterial, VirtualSessionInfo,
)


@admin.register(StudentRequest)
class StudentRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'student', 'request_type', 'status', 'created_at')
    list_filter = ('request_type', 'status', 'priority')
    search_fields = ('title', 'student__username')
    readonly_fields = ('request_number', 'created_at', 'updated_at')


@admin.register(StudentFaceChangeRequest)
class StudentFaceChangeRequestAdmin(admin.ModelAdmin):
    list_display = ('student', 'status', 'created_at', 'reviewed_at')
    list_filter = ('status',)
    search_fields = ('student__username',)


@admin.register(SessionMaterial)
class SessionMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'session', 'material_type', 'visible_to_students')
    list_filter = ('material_type', 'visible_to_students')


@admin.register(VirtualSessionInfo)
class VirtualSessionInfoAdmin(admin.ModelAdmin):
    list_display = ('session', 'meeting_provider', 'meeting_start_time')