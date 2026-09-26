"""
دکوراتورهای دسترسی معلم.
الگوی مشابه: district/decorators.py, school/decorators.py
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

from .scope import TeacherScope, TeacherScopeViolationError


def teacher_scope_required(view_func):
    """
    دکوراتور اصلی: فقط معلم با ساخت اسکوپ موفق.
    اسکوپ در request.teacher_scope قرار می‌گیرد.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role != 'teacher':
            messages.error(
                request,
                'دسترسی غیرمجاز. این بخش فقط برای معلم است.'
            )
            return redirect('dashboard:home')
        try:
            scope = TeacherScope(request.user)
        except TeacherScopeViolationError:
            messages.error(request, 'خطا در تعیین محدوده دسترسی.')
            return redirect('dashboard:home')
        request.teacher_scope = scope
        return view_func(request, *args, **kwargs)
    return wrapper


def teacher_permission_required(permission):
    """
    دکوراتور پارامتری برای بررسی دسترسی خاص.

    استفاده:
        @teacher_permission_required(TeacherPermission.SESSION_CREATE)
        def my_view(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.role != 'teacher':
                messages.error(request, 'دسترسی غیرمجاز.')
                return redirect('dashboard:home')
            try:
                scope = TeacherScope(request.user)
            except TeacherScopeViolationError:
                messages.error(request, 'خطا در تعیین محدوده.')
                return redirect('dashboard:home')
            if not scope.has_permission(permission):
                messages.error(
                    request,
                    'شما دسترسی لازم برای این عملیات را ندارید.'
                )
                return redirect('teacher:dashboard')
            request.teacher_scope = scope
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator