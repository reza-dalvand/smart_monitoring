from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # داشبورد اصلی
    path('', views.dashboard_home, name='home'),

    # برنامه هفتگی دانش‌آموز
    path('weekly-schedule/', views.weekly_schedule_view, name='weekly_schedule'),

    # ========== پنل معلم - فاز ۲ ==========
    path('teacher/ai/new/', views.teacher_ai_new, name='teacher_ai_new'),
    path('teacher/ai/<int:job_id>/review/', views.teacher_ai_review, name='teacher_ai_review'),
    path('teacher/ai/<int:job_id>/regenerate/', views.teacher_ai_regenerate_rejected, name='teacher_ai_regenerate_rejected'),

    path('teacher/ai/question/<int:pk>/approve/', views.teacher_ai_question_approve, name='teacher_ai_question_approve'),
    path('teacher/ai/question/<int:pk>/reject/', views.teacher_ai_question_reject, name='teacher_ai_question_reject'),

    path('teacher/questions/', views.teacher_question_bank, name='teacher_question_bank'),
    path('teacher/questions/manual/create/', views.teacher_question_manual_create, name='teacher_question_manual_create'),
    path('teacher/questions/<int:pk>/edit/', views.teacher_question_edit, name='teacher_question_edit'),
    path('teacher/questions/<int:pk>/delete/', views.teacher_question_delete, name='teacher_question_delete'),

    # پنل معاون
    path('assistant/', views.assistant_dashboard, name='assistant_dashboard'),
    path('assistant/absences/', views.absences_today_view, name='assistant_absences'),
    path('assistant/students/', views.student_list_view, name='assistant_students'),

    # مدیریت کلاس‌ها
    path('assistant/classes/', views.class_list_view, name='assistant_class_list'),
    path('assistant/classes/create/', views.class_create_view, name='assistant_class_create'),
    path('assistant/classes/<int:pk>/edit/', views.class_edit_view, name='assistant_class_edit'),
    path('assistant/classes/<int:pk>/delete/', views.class_delete_view, name='assistant_class_delete'),

    # مدیریت برنامه هفتگی
    path('assistant/schedule/', views.schedule_builder_view, name='assistant_schedule'),
    path('assistant/schedule/copy/', views.schedule_copy_view, name='assistant_schedule_copy'),
    path('assistant/schedule/<int:pk>/delete/', views.schedule_delete_view, name='assistant_schedule_delete'),
    path('assistant/schedule/print/<int:classroom_id>/', views.schedule_print_view, name='assistant_schedule_print'),
]