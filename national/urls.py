from django.urls import path
from . import views

app_name = 'national'

urlpatterns = [
    path('', views.national_dashboard, name='dashboard'),
    path('dashboard/', views.national_dashboard, name='national_dashboard'),
    path('provinces/<int:province_id>/', views.province_detail, name='province_detail'),
    path('districts/<int:district_id>/', views.district_detail, name='district_detail'),
    path('schools/<int:school_id>/', views.school_detail, name='school_detail'),
    path('reports/', views.national_reports, name='reports'),
    path('export/provinces/csv/', views.export_provinces_csv, name='export_provinces_csv'),
    path('export/schools/csv/', views.export_schools_csv, name='export_schools_csv'),
    path('api/dashboard/', views.api_dashboard_data, name='api_dashboard'),
    path('api/provinces/', views.api_provinces, name='api_provinces'),
    path('api/attendance/', views.api_attendance_data, name='api_attendance'),
]