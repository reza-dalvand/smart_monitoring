"""ویوهای پنل مسئول منطقه"""
import logging
from datetime import datetime

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Count

from .decorators import district_admin_required, district_admin_api_required
from .scope import DistrictScope, ScopeViolationError
from .services import DistrictAnalyticsService
from .exports import DistrictExportService
from .audit import DistrictAuditService

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
        scope = DistrictScope(request.user)
    except ScopeViolationError as e:
        raise Http404(str(e))
    service = DistrictAnalyticsService(scope)
    return scope, service


# ════════════════════════════════════════════════
#  داشبورد اصلی
# ════════════════════════════════════════════════

@district_admin_required
def district_dashboard(request):
    scope, service = _build_context(request)
    period = request.GET.get('period', 'month')
    school_id = request.GET.get('school')
    grade = request.GET.get('grade')
    field = request.GET.get('field')
    date_from, date_to, df_str, dt_str = _parse_dates(request)

    selected_school = None
    if school_id:
        selected_school = scope.validate_school_id(school_id)

    overview = service.get_overview(
        period=period, date_from=date_from, date_to=date_to,
        school_id=school_id, grade=grade, field=field)

    attendance_trend = service.get_attendance_trend(30, school_id)
    participation_trend = service.get_participation_trend(30, school_id)
    performance_subjects = service.get_performance_by_subject(school_id)
    face_stats = service.get_face_stats()
    ai_stats = service.get_ai_stats()
    usage_stats = service.get_system_usage()
    alerts = service.get_alerts()
    recent_activity = service.get_recent_activity()
    school_activity = service.get_school_activity_stats()
    school_comparison = service.get_school_comparison()
    schools = scope.filter_schools().filter(is_active=True).order_by('name')

    DistrictAuditService.log(request, 'view_dashboard',
                             details={'school': selected_school.name if selected_school else 'کل منطقه'})

    context = {
        'title': f'داشبورد منطقه {scope.district.name}',
        'district': scope.district,
        'province': scope.province,
        'scope': scope,
        'schools': schools,
        'selected_school': selected_school,
        'period': period,
        'grade_filter': grade,
        'field_filter': field,
        'date_from': df_str,
        'date_to': dt_str,
        'overview': overview,
        'attendance_trend': attendance_trend,
        'participation_trend': participation_trend,
        'performance_subjects': performance_subjects,
        'face_stats': face_stats,
        'ai_stats': ai_stats,
        'usage_stats': usage_stats,
        'alerts': alerts,
        'recent_activity': recent_activity,
        'school_comparison': school_comparison,
        'school_activity': school_activity,
        'has_data': bool(overview.get('students')),
        'grades': [('10', 'دهم'), ('11', 'یازدهم'), ('12', 'دوازدهم')],
        'fields': [
            ('computer', 'کامپیوتر'), ('electrical', 'برق'),
            ('mechanical', 'مکانیک'), ('accounting', 'حسابداری'),
            ('math', 'ریاضی'), ('experimental', 'تجربی'),
            ('humanities', 'انسانی'),
        ],
    }
    return render(request, 'district/dashboard.html', context)


# ════════════════════════════════════════════════
#  لیست مدارس
# ════════════════════════════════════════════════

@district_admin_required
def schools_list(request):
    scope, service = _build_context(request)
    comparison = service.get_school_comparison()

    search = request.GET.get('q', '')
    if search:
        comparison = [s for s in comparison if search in s['name']]

    paginator = Paginator(comparison, 20)
    page = request.GET.get('page')
    schools_page = paginator.get_page(page)

    DistrictAuditService.log(request, 'view_schools')

    context = {
        'title': f'مدارس منطقه {scope.district.name}',
        'district': scope.district,
        'province': scope.province,
        'schools': schools_page,
        'search': search,
    }
    return render(request, 'district/schools_list.html', context)


# ════════════════════════════════════════════════
#  جزئیات مدرسه
# ════════════════════════════════════════════════

@district_admin_required
def school_detail(request, school_id):
    scope, service = _build_context(request)
    school = scope.get_school_or_404(school_id)

    class_analytics = service.get_class_analytics(school.id)
    overview = service.get_overview(school_id=school.id)

    DistrictAuditService.log(request, 'view_school',
                             details={'school': school.name})

    context = {
        'title': f'{scope.district.name} / {school.name}',
        'district': scope.district,
        'province': scope.province,
        'school': school,
        'class_analytics': class_analytics,
        'overview': overview,
    }
    return render(request, 'district/school_detail.html', context)


# ════════════════════════════════════════════════
#  گزارش‌ها
# ════════════════════════════════════════════════

@district_admin_required
def district_reports(request):
    scope, service = _build_context(request)
    DistrictAuditService.log(request, 'view_reports')
    context = {
        'title': f'گزارشات منطقه {scope.district.name}',
        'district': scope.district,
        'province': scope.province,
    }
    return render(request, 'district/reports.html', context)


# ════════════════════════════════════════════════
#  هشدارها
# ════════════════════════════════════════════════

@district_admin_required
def district_alerts(request):
    scope, service = _build_context(request)
    alerts = service.get_alerts()

    paginator = Paginator(alerts, 20)
    page = request.GET.get('page')
    alerts_page = paginator.get_page(page)

    context = {
        'title': f'هشدارهای منطقه {scope.district.name}',
        'district': scope.district,
        'alerts': alerts_page,
    }
    return render(request, 'district/alerts.html', context)


# ════════════════════════════════════════════════
#  Export
# ════════════════════════════════════════════════

@district_admin_required
def export_schools_csv(request):
    scope, service = _build_context(request)
    data = service.get_school_comparison()
    DistrictAuditService.log(request, 'export_data',
                             details={'type': 'schools_csv'})
    return DistrictExportService.school_comparison_to_csv(data)


@district_admin_required
def export_classes_csv(request):
    scope, service = _build_context(request)
    school_id = request.GET.get('school')
    if school_id:
        scope.validate_school_id(school_id)
        data = service.get_class_analytics(school_id)
    else:
        data = []
        for school in scope.filter_schools().filter(is_active=True):
            data.extend(service.get_class_analytics(school.id))
    DistrictAuditService.log(request, 'export_data',
                             details={'type': 'classes_csv'})
    return DistrictExportService.class_analytics_to_csv(data)


# ════════════════════════════════════════════════
#  مدیران مدارس
# ════════════════════════════════════════════════

@district_admin_required
def school_admins(request):
    scope, service = _build_context(request)
    from accounts.models import User
    admins = User.objects.filter(
        role='principal',
        managed_schools__district=scope.district,
    ).select_related().distinct()

    paginator = Paginator(admins, 20)
    page = request.GET.get('page')
    admins_page = paginator.get_page(page)

    DistrictAuditService.log(request, 'view_district_admins')

    context = {
        'title': 'مدیران مدارس',
        'district': scope.district,
        'province': scope.province,
        'admins': admins_page,
        'schools': scope.filter_schools().filter(is_active=True),
    }
    return render(request, 'district/school_admins.html', context)


# ════════════════════════════════════════════════
#  تنظیمات منطقه
# ════════════════════════════════════════════════

@district_admin_required
def district_settings(request):
    scope, service = _build_context(request)
    from national.models import NationalPolicy
    policies = NationalPolicy.objects.filter(
        is_active=True,
        key__startswith=f'district_{scope.district_id}_',
    )
    context = {
        'title': 'تنظیمات منطقه',
        'district': scope.district,
        'province': scope.province,
        'policies': policies,
    }
    return render(request, 'district/settings.html', context)


# ════════════════════════════════════════════════
#  Audit Log
# ════════════════════════════════════════════════

@district_admin_required
def district_audit_log(request):
    scope, service = _build_context(request)
    from national.models import NationalAuditLog
    logs = NationalAuditLog.objects.filter(
        scope='district',
        scope_id=scope.district_id,
    ).order_by('-created_at')

    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)

    context = {
        'title': 'گزارش فعالیت‌ها',
        'district': scope.district,
        'logs': logs_page,
    }
    return render(request, 'district/audit_log.html', context)


# ════════════════════════════════════════════════
#  API Endpoints
# ════════════════════════════════════════════════

@district_admin_api_required
def api_dashboard_data(request):
    scope, service = _build_context(request)
    overview = service.get_overview()
    DistrictAuditService.log(request, 'view_api',
                             details={'endpoint': 'dashboard'})
    return JsonResponse({
        'success': True,
        'scope': 'district',
        'district': {
            'id': scope.district.id,
            'name': scope.district.name,
            'province': scope.province.name,
        },
        'overview': overview,
    })


@district_admin_api_required
def api_schools(request):
    scope, service = _build_context(request)
    schools = scope.filter_schools().filter(
        is_active=True).values('id', 'name', 'school_type')
    return JsonResponse({
        'success': True,
        'schools': list(schools),
    })


@district_admin_api_required
def api_attendance_data(request):
    scope, service = _build_context(request)
    trend = service.get_attendance_trend(30)
    return JsonResponse({'success': True, 'trend': trend})