"""دکوراتورهای دسترسی برای پنل مسئول کشوری"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse


def national_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role != 'country_admin':
            messages.error(request, 'دسترسی غیرمجاز. این بخش فقط برای مسئول کشوری است.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def national_admin_api_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False, 'code': 'UNAUTHORIZED',
                'message': 'احراز هویت لازم است.'
            }, status=401)
        if request.user.role != 'country_admin':
            return JsonResponse({
                'success': False, 'code': 'FORBIDDEN',
                'message': 'دسترسی غیرمجاز.'
            }, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper