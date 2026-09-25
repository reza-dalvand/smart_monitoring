from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse


def province_admin_required(view_func):
    """فقط مسئول استانی با استان اختصاص‌یافته مجاز است."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role != 'province_admin':
            messages.error(request, 'دسترسی غیرمجاز. این بخش فقط برای مسئول استانی است.')
            return redirect('dashboard:home')
        if not request.user.province:
            messages.error(request, 'هیچ استانی به حساب شما اختصاص داده نشده است.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def province_admin_api_required(view_func):
    """نسخه API: پاسخ JSON با کد وضعیت مناسب."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {'success': False, 'code': 'UNAUTHORIZED', 'message': 'احراز هویت لازم است.'},
                status=401,
            )
        if request.user.role != 'province_admin':
            return JsonResponse(
                {'success': False, 'code': 'FORBIDDEN', 'message': 'دسترسی غیرمجاز.'},
                status=403,
            )
        if not request.user.province:
            return JsonResponse(
                {'success': False, 'code': 'NO_PROVINCE', 'message': 'استانی اختصاص داده نشده.'},
                status=403,
            )
        return view_func(request, *args, **kwargs)
    return wrapper