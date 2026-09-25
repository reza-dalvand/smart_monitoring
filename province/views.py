"""ویوهای پنل مسئول استانی"""
import logging
from datetime import datetime

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Count

from .decorators import province_admin_required, province_admin_api_required
from .scope import ProvinceScope, ScopeViolationError
from .services import ProvinceAnalyticsService
from .exports import ProvinceExportService
from .audit import ProvinceAuditService

from national.models import District, School
from dashboard.models import Classroom

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


def _build_context(request):
    """ساخت اسکوپ و سرویس مشترک تمام ویوها"""
    try:
        scope = ProvinceScope(request.user)
    except ScopeViolationError as e:
        raise Http404(str(e))
    service = ProvinceAnalyticsService(scope)
    return scope, service


# ════════════════════════════════════════════════
#  داشبورد اصلی
# ════════════════════════════════════════════════

@province_admin_required
def province_dashboard(request):
    scope, service = _build_context(request)
    period = request.GET.get('period', 'month')
    district_id = request.GET.get('district')
    date_from, date_to, df_str, dt_str = _parse_dates(request)

    # اعتبارسنجی منطقه در محدوده استان
    selected_district = None
    if district_id:
        selected_district = scope.validate_district_id(district_id)

    overview = service.get_overview(
        district_id=district_id, period=period,
        date_from=date_from, date_to=date_to)

    attendance_trend = service.get_attendance_trend(30)
    participation_trend = service.get_participation_trend(30)
    attendance_status = service.get_attendance_status()
    performance_subjects = service.get_performance_by_subject()
    face_stats = service.get_face_stats()
    ai_stats = service.get_ai_stats()
    usage_stats = service.get_system_usage()
    alerts = service.get_alerts()
    recent_activity = service.get_recent_activity()
    school_activity = service.get_school_activity_stats()

    districts = scope.filter_districts().filter(is_active=True).order_by('name')
    district_comparison = service.get_district_comparison()

    ProvinceAuditService.log(request, 'view_dashboard',
                             details={'district': selected_district.name if selected_district else 'کل استان'})

    context = {
        'title': f'داشبورد مسئول استان {scope.province.name}',
        'province': scope.province,
        'scope': scope,
        'districts': districts,
        'selected_district': selected_district,
        'period': period,
        'date_from': df_str,
        'date_to': dt_str,
        'overview': overview,
        'attendance_trend': attendance_trend,
        'participation_trend': participation_trend,
        'attendance_status': attendance_status,
        'performance_subjects': performance_subjects,
        'face_stats': face_stats,
        'ai_stats': ai_stats,
        'usage_stats': usage_stats,
        'alerts': alerts,
        'recent_activity': recent_activity,
        'district_comparison': district_comparison,
        'school_activity': school_activity,
        'has_data': bool(overview.get('students')),
    }
    return render(request, 'province/dashboard.html', context)


# ════════════════════════════════════════════════
#  جزئیات منطقه
# ════════════════════════════════════════════════

@province_admin_required
def district_detail(request, district_id):
    scope, service = _build_context(request)
    district = scope.get_district_or_404(district_id)

    schools = service.get_schools_list(district_id=district.id)
    overview = service.get_overview()

    ProvinceAuditService.log(request, 'view_district',
                             details={'district': district.name})

    context = {
        'title': f'{scope.province.name} / {district.name}',
        'province': scope.province,
        'district': district,
        'schools': schools,
        'overview': overview,
    }
    return render(request, 'province/district_detail.html', context)


# ════════════════════════════════════════════════
#  جزئیات مدرسه
# ════════════════════════════════════════════════

@province_admin_required
def school_detail(request, school_id):
    scope, service = _build_context(request)
    school = scope.get_school_or_404(school_id)

    classrooms = scope.filter_classrooms().filter(school=school).select_related(
        'teacher').annotate(
        students_count=Count('students', distinct=True),
        sessions_count=Count('sessions', distinct=True),
    )

    ProvinceAuditService.log(request, 'view_school',
                             details={'school': school.name})

    context = {
        'title': f'{scope.province.name} / {school.district.name} / {school.name}',
        'province': scope.province,
        'school': school,
        'classrooms': classrooms,
    }
    return render(request, 'province/school_detail.html', context)


# ════════════════════════════════════════════════
#  گزارش‌ها
# ════════════════════════════════════════════════

@province_admin_required
def province_reports(request):
    scope, service = _build_context(request)
    ProvinceAuditService.log(request, 'view_reports')
    context = {
        'title': f'گزارشات استان {scope.province.name}',
        'province': scope.province,
    }
    return render(request, 'province/reports.html', context)


# ════════════════════════════════════════════════
#  Export
# ════════════════════════════════════════════════

@province_admin_required
def export_districts_csv(request):
    scope, service = _build_context(request)
    data = service.get_district_comparison()
    ProvinceAuditService.log(request, 'export_data',
                             details={'type': 'districts_csv'})
    return ProvinceExportService.district_comparison_to_csv(data)


@province_admin_required
def export_schools_csv(request):
    scope, service = _build_context(request)
    district_id = request.GET.get('district')
    district = scope.validate_district_id(district_id) if district_id else None
    data = service.get_schools_list(
        district_id=district.id if district else None)
    ProvinceAuditService.log(request, 'export_data',
                             details={'type': 'schools_csv'})
    return ProvinceExportService.schools_to_csv(data)


# ════════════════════════════════════════════════
#  مسئولان مناطق
# ════════════════════════════════════════════════

@province_admin_required
def district_admins(request):
    scope, service = _build_context(request)
    from accounts.models import User

    admins = User.objects.filter(
        role='district_admin',
        province=scope.province,
    ).select_related('province')

    ProvinceAuditService.log(request, 'view_district_admins')

    context = {
        'title': 'مسئولان مناطق',
        'province': scope.province,
        'admins': admins,
        'districts': scope.filter_districts().filter(is_active=True),
    }
    return render(request, 'province/district_admins.html', context)


# ════════════════════════════════════════════════
#  تنظیمات استانی
# ════════════════════════════════════════════════

@province_admin_required
def province_settings(request):
    scope, service = _build_context(request)
    from national.models import NationalPolicy

    # فقط سیاست‌های استانی قابل ویرایش‌اند
    policies = NationalPolicy.objects.filter(
        is_active=True,
        key__startswith=f'province_{scope.province.id}_',
    )

    context = {
        'title': 'تنظیمات استانی',
        'province': scope.province,
        'policies': policies,
    }
    return render(request, 'province/settings.html', context)


# ════════════════════════════════════════════════
#  Audit Log
# ════════════════════════════════════════════════

@province_admin_required
def province_audit_log(request):
    scope, service = _build_context(request)
    from national.models import NationalAuditLog

    logs = NationalAuditLog.objects.filter(
        scope='province',
        scope_id=scope.province_id,
    ).order_by('-created_at')

    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)

    context = {
        'title': 'گزارش فعالیت‌ها',
        'province': scope.province,
        'logs': logs_page,
    }
    return render(request, 'province/audit_log.html', context)


# ════════════════════════════════════════════════
#  API Endpoints
# ════════════════════════════════════════════════

@province_admin_api_required
def api_dashboard_data(request):
    scope, service = _build_context(request)
    overview = service.get_overview()
    att = service.get_attendance_status()

    ProvinceAuditService.log(request, 'view_api',
                             details={'endpoint': 'dashboard'})

    return JsonResponse({
        'success': True,
        'scope': 'province',
        'province': {
            'id': scope.province.id,
            'name': scope.province.name,
        },
        'overview': overview,
        'attendance': {
            'present_rate': att.get('present_rate'),
            'absent_rate': att.get('absent_rate'),
        },
    })


@province_admin_api_required
def api_districts(request):
    scope, service = _build_context(request)
    districts = scope.filter_districts().filter(
        is_active=True).values('id', 'name', 'code')
    return JsonResponse({
        'success': True,
        'districts': list(districts),
    })


@province_admin_api_required
def api_attendance_data(request):
    scope, service = _build_context(request)
    trend = service.get_attendance_trend(30)
    return JsonResponse({'success': True, 'trend': trend})