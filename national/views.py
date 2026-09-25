"""ویوهای پنل مسئول کشوری"""
import logging
from datetime import datetime

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone

from .decorators import national_admin_required, national_admin_api_required
from .services import NationalAnalyticsService, ReportService
from .exports import ExportService
from .audit import AuditService
from .models import Province, District, School

logger = logging.getLogger(__name__)


def _parse_dates(request):
    date_from = date_to = None
    df = request.GET.get('date_from')
    dt = request.GET.get('date_to')
    if df:
        try:
            date_from = datetime.strptime(df, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pass
    if dt:
        try:
            date_to = datetime.strptime(dt, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pass
    return date_from, date_to, df or '', dt or ''


def _get_scope_params(request):
    scope = request.GET.get('scope', 'national')
    province_id = request.GET.get('province')
    province = None
    if scope == 'province' and province_id:
        province = get_object_or_404(Province, id=province_id, is_active=True)
    return scope, province_id, province


@national_admin_required
def national_dashboard(request):
    scope, province_id, province = _get_scope_params(request)
    period = request.GET.get('period', 'month')
    date_from, date_to, df_str, dt_str = _parse_dates(request)
    pid = int(province_id) if province_id else None

    provinces = Province.objects.filter(is_active=True).order_by('name')
    overview = NationalAnalyticsService.get_overview(
        scope=scope, province_id=pid, period=period,
        date_from=date_from, date_to=date_to)
    attendance_trend = NationalAnalyticsService.get_attendance_trend(scope, pid, 30)
    participation_trend = NationalAnalyticsService.get_participation_trend(scope, pid, 30)
    attendance_status = NationalAnalyticsService.get_attendance_status_breakdown(scope, pid)
    performance_subjects = NationalAnalyticsService.get_performance_by_subject(scope, pid)
    face_stats = NationalAnalyticsService.get_face_verification_stats(scope, pid)
    ai_stats = NationalAnalyticsService.get_ai_stats(scope, pid)
    usage_stats = NationalAnalyticsService.get_system_usage(scope, pid)
    alerts = NationalAnalyticsService.get_alerts(scope, pid)
    recent_activity = NationalAnalyticsService.get_recent_activity(scope, pid)
    province_comparison = []
    if scope == 'national':
        province_comparison = NationalAnalyticsService.get_province_comparison()

    AuditService.log(request, 'view_dashboard', scope, pid,
                     province.name if province else 'کل کشور')

    context = {
        'title': 'داشبورد مسئول کشوری',
        'scope': scope, 'province': province,
        'provinces': provinces, 'period': period,
        'date_from': df_str, 'date_to': dt_str,
        'overview': overview,
        'province_comparison': province_comparison,
        'attendance_trend': attendance_trend,
        'participation_trend': participation_trend,
        'attendance_status': attendance_status,
        'performance_subjects': performance_subjects,
        'face_stats': face_stats, 'ai_stats': ai_stats,
        'usage_stats': usage_stats,
        'alerts': alerts, 'recent_activity': recent_activity,
        'has_data': overview['students'] > 0 or overview['schools'] > 0,
    }
    return render(request, 'national/dashboard.html', context)


@national_admin_required
def province_detail(request, province_id):
    province = get_object_or_404(Province, id=province_id, is_active=True)
    districts = District.objects.filter(
        province=province, is_active=True
    ).annotate(schools_count=Count('schools', distinct=True))
    overview = NationalAnalyticsService.get_overview(
        scope='province', province_id=province_id, period='month')
    schools = NationalAnalyticsService.get_schools_list('province', province_id)
    AuditService.log(request, 'view_province', 'province', province_id, province.name)
    context = {
        'title': f'استان {province.name}',
        'province': province, 'districts': districts,
        'overview': overview, 'schools': schools, 'scope': 'province',
    }
    return render(request, 'national/province_detail.html', context)


@national_admin_required
def district_detail(request, district_id):
    district = get_object_or_404(District, id=district_id, is_active=True)
    schools = School.objects.filter(
        district=district, is_active=True
    ).annotate(classrooms_count=Count('classrooms', distinct=True))
    AuditService.log(request, 'view_district', 'district', district_id,
                     f'{district.province.name} - {district.name}')
    context = {
        'title': f'{district.province.name} - {district.name}',
        'district': district, 'province': district.province,
        'schools': schools, 'scope': 'district',
    }
    return render(request, 'national/district_detail.html', context)


@national_admin_required
def school_detail(request, school_id):
    school = get_object_or_404(School, id=school_id)
    classrooms = school.classrooms.select_related('teacher').annotate(
        students_count=Count('students', distinct=True),
        sessions_count=Count('sessions', distinct=True),
    )
    AuditService.log(request, 'view_school', 'school', school_id, school.name)
    context = {
        'title': f'مدرسه {school.name}',
        'school': school, 'classrooms': classrooms, 'scope': 'school',
    }
    return render(request, 'national/school_detail.html', context)


@national_admin_required
def national_reports(request):
    scope, province_id, province = _get_scope_params(request)
    provinces = Province.objects.filter(is_active=True).order_by('name')
    AuditService.log(request, 'view_reports', scope,
                     int(province_id) if province_id else None,
                     province.name if province else 'کل کشور')
    context = {
        'title': 'گزارشات ملی', 'scope': scope,
        'province': province, 'provinces': provinces,
    }
    return render(request, 'national/reports.html', context)


@national_admin_required
def export_provinces_csv(request):
    data = NationalAnalyticsService.get_province_comparison()
    AuditService.log(request, 'export_data', 'national', details={'type': 'provinces_csv'})
    return ExportService.province_comparison_to_csv(data)


@national_admin_required
def export_schools_csv(request):
    scope, province_id, _ = _get_scope_params(request)
    pid = int(province_id) if province_id else None
    data = NationalAnalyticsService.get_schools_list(scope, pid)
    AuditService.log(request, 'export_data', scope, pid, details={'type': 'schools_csv'})
    return ExportService.schools_to_csv(data)


# ──────────────────────────────────────────────
#  APIs
# ──────────────────────────────────────────────
@national_admin_api_required
def api_dashboard_data(request):
    scope, province_id, province = _get_scope_params(request)
    pid = int(province_id) if province_id else None
    overview = NationalAnalyticsService.get_overview(scope=scope, province_id=pid)
    att = NationalAnalyticsService._get_attendance_stats(scope, pid)
    AuditService.log(request, 'view_api', scope, pid, details={'endpoint': 'dashboard'})
    return JsonResponse({
        'success': True,
        'scope': scope,
        'province': {'id': province.id, 'name': province.name} if province else None,
        'overview': overview,
        'attendance': {
            'present_rate': att.get('present_rate'),
            'absent_rate': att.get('absent_rate'),
        },
    })


@national_admin_api_required
def api_provinces(request):
    provinces = Province.objects.filter(is_active=True).values('id', 'name', 'code')
    return JsonResponse({
        'success': True,
        'provinces': list(provinces),
    })


@national_admin_api_required
def api_attendance_data(request):
    scope, province_id, _ = _get_scope_params(request)
    pid = int(province_id) if province_id else None
    trend = NationalAnalyticsService.get_attendance_trend(scope, pid, 30)
    return JsonResponse({'success': True, 'trend': trend})