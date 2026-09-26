from django.urls import path
from . import views

app_name = 'school'

urlpatterns = [
    # ── Principal ──
    path('principal/', views.principal_dashboard, name='principal_dashboard'),
    path('principal/students/', views.principal_students, name='principal_students'),
    path('principal/students/<int:student_id>/', views.principal_student_detail, name='principal_student_detail'),
    path('principal/teachers/', views.principal_teachers, name='principal_teachers'),
    path('principal/teachers/<int:teacher_id>/', views.principal_teacher_detail, name='principal_teacher_detail'),
    path('principal/classes/', views.principal_classes, name='principal_classes'),
    path('principal/classes/<int:classroom_id>/', views.principal_class_detail, name='principal_class_detail'),
    path('principal/attendance/', views.principal_attendance, name='principal_attendance'),
    path('principal/attendance/override/<int:response_id>/', views.principal_attendance_override, name='principal_attendance_override'),
    path('principal/followups/', views.principal_followups, name='principal_followups'),
    path('principal/followups/create/', views.principal_followup_create, name='principal_followup_create'),
    path('principal/followups/<int:case_id>/', views.principal_followup_detail, name='principal_followup_detail'),
    path('principal/followups/<int:case_id>/assign/', views.principal_followup_assign, name='principal_followup_assign'),
    path('principal/followups/<int:case_id>/resolve/', views.principal_followup_resolve, name='principal_followup_resolve'),
    path('principal/assistants/', views.principal_assistants, name='principal_assistants'),
    path('principal/assistants/assign/', views.principal_assistant_assign, name='principal_assistant_assign'),
    path('principal/assistants/<int:assignment_id>/toggle/', views.principal_assistant_toggle, name='principal_assistant_toggle'),
    path('principal/reports/', views.principal_reports, name='principal_reports'),
    path('principal/settings/', views.principal_settings, name='principal_settings'),
    path('principal/audit/', views.principal_audit_log, name='principal_audit_log'),
    path('principal/alerts/', views.principal_alerts, name='principal_alerts'),
        # ── تغییر وضعیت دانش‌آموز ──
    path('principal/students/<int:student_id>/status/',
         views.principal_student_status,
         name='principal_student_status'),

    # ── تغییر وضعیت کلاس ──
    path('principal/classes/<int:classroom_id>/toggle-status/',
         views.principal_class_toggle_status,
         name='principal_class_toggle_status'),

        # ── مدیریت وظایف ──
    path('principal/tasks/', views.principal_tasks, name='principal_tasks'),
    path('principal/tasks/create/', views.principal_task_create, name='principal_task_create'),
    path('principal/tasks/<int:task_id>/', views.principal_task_detail, name='principal_task_detail'),
    path('principal/tasks/<int:task_id>/delete/', views.principal_task_delete, name='principal_task_delete'),

    # ── Assistant ──
    path('assistant/', views.assistant_operational_dashboard, name='assistant_dashboard'),
    path('assistant/students/', views.assistant_students, name='assistant_students'),
    path('assistant/students/<int:student_id>/', views.assistant_student_detail, name='assistant_student_detail'),
    path('assistant/classes/', views.assistant_classes, name='assistant_classes'),
    path('assistant/classes/create/', views.assistant_class_create, name='assistant_class_create'),
    path('assistant/classes/<int:classroom_id>/', views.assistant_class_detail, name='assistant_class_detail'),
    path('assistant/classes/<int:classroom_id>/edit/', views.assistant_class_edit, name='assistant_class_edit'),
    path('assistant/attendance/', views.assistant_attendance, name='assistant_attendance'),
    path('assistant/attendance/review/<int:review_id>/', views.assistant_attendance_review, name='assistant_attendance_review'),
    path('assistant/schedule/', views.assistant_schedule, name='assistant_schedule'),
    path('assistant/followups/', views.assistant_followups, name='assistant_followups'),
    path('assistant/followups/create/', views.assistant_followup_create, name='assistant_followup_create'),
    path('assistant/followups/<int:case_id>/', views.assistant_followup_detail, name='assistant_followup_detail'),
    path('assistant/followups/<int:case_id>/escalate/', views.assistant_followup_escalate, name='assistant_followup_escalate'),
    path('assistant/reports/', views.assistant_reports, name='assistant_reports'),
    path('assistant/students/<int:student_id>/status/', views.assistant_student_status, name='assistant_student_status'),
    path('assistant/classes/<int:classroom_id>/toggle/', views.assistant_class_toggle_status, name='assistant_class_toggle_status'),
    path('assistant/followups/<int:case_id>/resolve/', views.assistant_followup_resolve, name='assistant_followup_resolve'),
]