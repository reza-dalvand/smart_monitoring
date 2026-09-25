from django.urls import path
from . import views

app_name = 'face'

urlpatterns = [
    path('enrollment/', views.enrollment_page, name='enrollment'),
    path('verify/<int:request_id>/', views.verify_page, name='verify'),

    path('api/enrollment/', views.api_enrollment, name='api_enrollment'),
    path('api/enrollment/validate/', views.api_enrollment_validate, name='api_enrollment_validate'),

    # Endpoint قدیمی حفظ می‌شود.
    path('api/verify/<int:attendance_request_id>/', views.api_verify, name='api_verify'),

    # Endpointهای جدید session-based
    path(
        'api/verification/start/<int:attendance_request_id>/',
        views.api_start_verification,
        name='api_verification_start'
    ),
    path(
        'api/verification/complete/<uuid:session_id>/',
        views.api_complete_verification,
        name='api_verification_complete'
    ),

    path('api/profile/', views.api_profile, name='api_profile'),
    path('api/status/', views.api_status, name='api_status'),
    path('api/mark-absent/<int:attendance_request_id>/', views.api_mark_absent, name='api_mark_absent'),
]