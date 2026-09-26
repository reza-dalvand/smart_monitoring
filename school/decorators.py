"""دکوراتورهای دسترسی برای پنل مدرسه"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse

from .scope import SchoolScope, SchoolScopeViolationError
from .constants import StaffRole


def _build_scope(request):
    try:
        return SchoolScope(request.user)
    except SchoolScopeViolationError:
        return None


def principal_required(view_func):
    """فقط مدیر مدرسه با انتصاب فعال"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        scope = _build_scope(request)
        if not scope or not scope.is_principal:
            messages.error(request, 'دسترسی غیرمجاز. این بخش فقط برای مدیر مدرسه است.')
            return redirect('dashboard:home')
        if not scope.active_school:
            messages.error(request, 'هیچ مدرسه‌ای به حساب شما اختصاص داده نشده.')
            return redirect('dashboard:home')
        request.school_scope = scope
        return view_func(request, *args, **kwargs)
    return wrapper


def assistant_required(view_func):
    """فقط معاون مدرسه با انتصاب فعال"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        scope = _build_scope(request)
        if not scope or not scope.is_assistant:
            messages.error(request, 'دسترسی غیرمجاز. این بخش فقط برای معاون مدرسه است.')
            return redirect('dashboard:home')
        if not scope.active_school:
            messages.error(request, 'هیچ مدرسه‌ای به حساب شما اختصاص داده نشده.')
            return redirect('dashboard:home')
        request.school_scope = scope
        return view_func(request, *args, **kwargs)
    return wrapper


def school_staff_required(view_func):
    """مدیر یا معاون مدرسه"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        scope = _build_scope(request)
        if not scope or (not scope.is_principal and not scope.is_assistant):
            messages.error(request, 'دسترسی غیرمجاز.')
            return redirect('dashboard:home')
        if not scope.active_school:
            messages.error(request, 'هیچ مدرسه‌ای به حساب شما اختصاص داده نشده.')
            return redirect('dashboard:home')
        request.school_scope = scope
        return view_func(request, *args, **kwargs)
    return wrapper


def school_permission_required(permission):
    """دکوراتور پارامتری برای بررسی دسترسی خاص"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            scope = _build_scope(request)
            if not scope:
                messages.error(request, 'دسترسی غیرمجاز.')
                return redirect('dashboard:home')
            if not scope.has_permission(permission):
                messages.error(request, 'شما دسترسی لازم برای این عملیات را ندارید.')
                return redirect('dashboard:home')
            request.school_scope = scope
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def school_staff_api_required(view_func):
    """نسخه API"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {'success': False, 'code': 'UNAUTHORIZED',
                 'message': 'احراز هویت لازم است.'},
                status=401,
            )
        scope = _build_scope(request)
        if not scope or (not scope.is_principal and not scope.is_assistant):
            return JsonResponse(
                {'success': False, 'code': 'FORBIDDEN',
                 'message': 'دسترسی غیرمجاز.'},
                status=403,
            )
        request.school_scope = scope
        return view_func(request, *args, **kwargs)
    return wrapper