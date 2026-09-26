"""
دکوراتورهای دسترسی دانش‌آموز.
الگوی مشابه: teacher/decorators.py
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

from .scope import StudentScope, StudentScopeViolationError


def student_required(view_func):
    """فقط دانش‌آموز با ساخت اسکوپ موفق"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role != 'student':
            messages.error(request, 'دسترسی غیرمجاز. این بخش فقط برای دانش‌آموز است.')
            return redirect('dashboard:home')
        try:
            scope = StudentScope(request.user)
        except StudentScopeViolationError:
            messages.error(request, 'خطا در تعیین محدوده دسترسی.')
            return redirect('dashboard:home')
        request.student_scope = scope
        return view_func(request, *args, **kwargs)
    return wrapper