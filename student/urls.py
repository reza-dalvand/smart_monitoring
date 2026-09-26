from django.urls import path
from . import views

app_name = 'student'

urlpatterns = [
    # Dashboard
    path('', views.student_dashboard, name='dashboard'),

    # Profile
    path('profile/', views.student_profile, name='profile'),

    # Schedule
    path('schedule/', views.student_schedule, name='schedule'),

    # Classes
    path('classes/', views.student_classes, name='classes'),
    path('classes/<int:classroom_id>/', views.student_class_detail, name='class_detail'),

    # Sessions
    path('sessions/', views.student_sessions, name='sessions'),
    path('sessions/<int:session_id>/', views.student_session_detail, name='session_detail'),

    # Attendance
    path('attendance/', views.student_attendance, name='attendance'),

    # Questions
    path('questions/', views.student_questions, name='questions'),

    # Assessments
    path('assessments/', views.student_assessments, name='assessments'),
    path('assessments/<int:assessment_id>/', views.student_assessment_detail, name='assessment_detail'),
    path('assessments/<int:assessment_id>/take/', views.student_assessment_take, name='assessment_take'),
    path('assessments/<int:assessment_id>/result/', views.student_assessment_result, name='assessment_result'),

    # Homework
    path('homeworks/', views.student_homeworks, name='homeworks'),
    path('homeworks/<int:homework_id>/', views.student_homework_detail, name='homework_detail'),
    path('homeworks/<int:homework_id>/submit/', views.student_homework_submit, name='homework_submit'),

    # Feedback
    path('feedback/', views.student_feedback, name='feedback'),

    # Educational Status
    path('status/', views.student_status, name='status'),

    # Requests
    path('requests/', views.student_requests, name='requests'),
    path('requests/create/', views.student_request_create, name='request_create'),
    path('requests/<int:request_id>/', views.student_request_detail, name='request_detail'),
    path('requests/<int:request_id>/cancel/', views.student_request_cancel, name='request_cancel'),

    # Face
    path('face/', views.student_face, name='face'),
    path('face/change-request/', views.student_face_change_request, name='face_change_request'),

    # Virtual Classes
    path('virtual/', views.student_virtual_classes, name='virtual_classes'),
]