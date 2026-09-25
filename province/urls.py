from django.urls import path
from . import views

app_name = 'province'

urlpatterns = [
    # صفحات اصلی
    path('', views.province_dashboard, name='dashboard'),
    path('districts/<int:district_id>/', views.district_detail, name='district_detail'),
    path('schools/<int:school_id>/', views.school_detail, name='school_detail'),

    # گزارش‌ها و خروجی
    path('reports/', views.province_reports, name='reports'),
    path('export/districts/csv/', views.export_districts_csv, name='export_districts_csv'),
    path('export/schools/csv/', views.export_schools_csv, name='export_schools_csv'),

    # مدیریت
    path('district-admins/', views.district_admins, name='district_admins'),
    path('settings/', views.province_settings, name='settings'),
    path('audit/', views.province_audit_log, name='audit_log'),

    # API
    path('api/dashboard/', views.api_dashboard_data, name='api_dashboard'),
    path('api/districts/', views.api_districts, name='api_districts'),
    path('api/attendance/', views.api_attendance_data, name='api_attendance'),
]