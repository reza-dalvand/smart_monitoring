from django.contrib import admin
from .models import FaceProfile, FaceEmbedding, FaceVerificationLog
from .models import FaceVerificationSession


@admin.register(FaceVerificationSession)
class FaceVerificationSessionAdmin(admin.ModelAdmin):
    list_display = (
        'session_id',
        'student',
        'attendance_request',
        'status',
        'started_at',
        'deadline_at',
        'completed_at',
    )
    list_filter = ('status',)
    search_fields = (
        'student__username',
        'student__first_name',
        'student__last_name',
        'session_id',
    )
    readonly_fields = ('created_at', 'updated_at')

@admin.register(FaceProfile)
class FaceProfileAdmin(admin.ModelAdmin):
    list_display = ('student', 'enrollment_status', 'reference_images_count',
                    'last_enrollment_at', 'last_verification_at', 'is_active')
    list_filter = ('enrollment_status', 'is_active')
    search_fields = ('student__username', 'student__first_name', 'student__last_name')


@admin.register(FaceEmbedding)
class FaceEmbeddingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'student',
        'model_name',
        'model_version',
        'embedding_dimension',
        'is_active',
        'created_at'
    )
    list_filter = ('model_name', 'is_active')
    search_fields = ('student__username',)

    fields = (
        'student',
        'model_name',
        'model_version',
        'embedding_dimension',
        'source_image',
        'is_active',
        'created_at',
        'updated_at'
    )

    readonly_fields = ('created_at', 'updated_at')

@admin.register(FaceVerificationLog)
class FaceVerificationLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'status', 'similarity_score', 'liveness_passed',
                    'total_frames', 'valid_frames', 'attendance_request', 'created_at')
    list_filter = ('status', 'liveness_passed')
    search_fields = ('student__username',)