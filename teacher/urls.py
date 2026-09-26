from django.urls import path
from . import views

app_name = 'teacher'

urlpatterns = [
    # Dashboard
    path('', views.teacher_dashboard, name='dashboard'),

    # Classes
    path('classes/', views.teacher_classes, name='classes'),
    path('classes/<int:classroom_id>/', views.teacher_class_detail, name='class_detail'),
    path('classes/<int:classroom_id>/students/', views.teacher_class_students, name='class_students'),

    # Sessions
    path('sessions/', views.teacher_sessions, name='sessions'),
    path('sessions/create/', views.teacher_session_create, name='session_create'),
    path('sessions/<int:session_id>/', views.teacher_session_detail, name='session_detail'),
    path('sessions/<int:session_id>/start/', views.teacher_session_start, name='session_start'),
    path('sessions/<int:session_id>/end/', views.teacher_session_end, name='session_end'),
    path('sessions/<int:session_id>/panel/', views.teacher_session_panel, name='session_panel'),

    # Attendance Requests (از dashboard منتقل شد)
    path('classes/<int:classroom_id>/session/<int:session_id>/new-request/',
         views.teacher_create_attendance_request, name='teacher_create_attendance_request'),
    path('requests/<int:request_id>/results/', views.teacher_request_results, name='teacher_request_results'),
    path('requests/<int:request_id>/finish/', views.teacher_finish_request, name='teacher_finish_request'),
    path('attendance/', views.teacher_attendance, name='attendance'),
    path('attendance/<int:request_id>/', views.teacher_attendance_detail, name='attendance_detail'),
    path('attendance/<int:response_id>/correct/', views.teacher_attendance_correct, name='attendance_correct'),

    # Participation
    path('participation/', views.teacher_participation, name='participation'),
    path('participation/<int:session_id>/record/', views.teacher_participation_record, name='participation_record'),
    path('participation/stats/', views.teacher_participation_stats, name='teacher_participation_stats'),
    path('session/<int:session_id>/stats/', views.teacher_session_detail_stats, name='teacher_session_detail_stats'),
    path('classroom/<int:classroom_id>/period-stats/', views.teacher_period_stats, name='teacher_period_stats'),

    # Questions
    path('questions/', views.teacher_questions, name='questions'),
    path('questions/create/', views.teacher_question_create, name='question_create'),
    path('questions/<int:pk>/edit/', views.teacher_question_edit, name='question_edit'),
    path('questions/<int:pk>/delete/', views.teacher_question_delete, name='question_delete'),

    # AI Question Generation (از dashboard منتقل شد)
    path('ai/', views.teacher_ai, name='ai'),
    path('ai/new/', views.teacher_ai_new, name='teacher_ai_new'),
    path('ai/<int:job_id>/review/', views.teacher_ai_review, name='teacher_ai_review'),
    path('ai/<int:job_id>/regenerate/', views.teacher_ai_regenerate_rejected, name='teacher_ai_regenerate_rejected'),
    path('ai/question/<int:pk>/approve/', views.teacher_ai_question_approve, name='teacher_ai_question_approve'),
    path('ai/question/<int:pk>/reject/', views.teacher_ai_question_reject, name='teacher_ai_question_reject'),
    path('ai/question/<int:pk>/reject-regenerate/',
         views.teacher_ai_question_reject_and_regenerate, name='teacher_ai_question_reject_regenerate'),

    # Weekly Schedule
    path('schedule/', views.teacher_weekly_schedule, name='teacher_weekly_schedule'),

    # Assessments
    path('assessments/', views.teacher_assessments, name='assessments'),
    path('assessments/create/', views.teacher_assessment_create, name='assessment_create'),
    path('assessments/<int:assessment_id>/', views.teacher_assessment_detail, name='assessment_detail'),
    path('assessments/<int:assessment_id>/publish/', views.teacher_assessment_publish, name='assessment_publish'),

    # Homework
    path('homework/', views.teacher_homework, name='homework'),
    path('homework/create/', views.teacher_homework_create, name='homework_create'),
    path('homework/<int:homework_id>/', views.teacher_homework_detail, name='homework_detail'),
    path('homework/<int:homework_id>/grade/', views.teacher_homework_grade, name='homework_grade'),

    # Students
    path('students/', views.teacher_students, name='students'),
    path('students/<int:student_id>/', views.teacher_student_detail, name='student_detail'),
    path('students/<int:student_id>/notes/', views.teacher_student_notes, name='student_notes'),
    path('students/<int:student_id>/notes/add/', views.teacher_note_add, name='note_add'),

    # Follow-up Suggestion
    path('followup/suggest/', views.teacher_followup_suggest, name='followup_suggest'),

    # Analytics
    path('analytics/', views.teacher_analytics, name='analytics'),
    path('analytics/class/<int:classroom_id>/', views.teacher_class_analytics, name='class_analytics'),
    path('analytics/topics/<int:classroom_id>/', views.teacher_topic_analytics, name='topic_analytics'),

    # Reports
    path('reports/', views.teacher_reports, name='reports'),
]