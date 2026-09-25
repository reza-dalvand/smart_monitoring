from django.urls import path
from . import views

app_name = 'district'

urlpatterns = [
    # صفحات اصلی
    path('', views.district_dashboard, name='dashboard'),
    path('dashboard/', views.district_dashboard, name='district_dashboard'),
    path('schools/', views.schools_list, name='schools'),
    path('schools/<int:school_id>/', views.school_detail, name='school_detail'),

    # گزارش‌ها و خروجی
    path('reports/', views.district_reports, name='reports'),
    path('alerts/', views.district_alerts, name='alerts'),
    path('export/schools/csv/', views.export_schools_csv, name='export_schools_csv'),
    path('export/classes/csv/', views.export_classes_csv, name='export_classes_csv'),

    # مدیریت
    path('school-admins/', views.school_admins, name='school_admins'),
    path('settings/', views.district_settings, name='settings'),
    path('audit/', views.district_audit_log, name='audit_log'),

    # API
    path('api/dashboard/', views.api_dashboard_data, name='api_dashboard'),
    path('api/schools/', views.api_schools, name='api_schools'),
    path('api/attendance/', views.api_attendance_data, name='api_attendance'),
]