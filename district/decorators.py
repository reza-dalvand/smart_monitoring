from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse


def district_admin_required(view_func):
    """فقط مسئول منطقه با منطقه اختصاص‌یافته مجاز است."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role != 'district_admin':
            messages.error(request, 'دسترسی غیرمجاز. این بخش فقط برای مسئول منطقه است.')
            return redirect('dashboard:home')
        if not request.user.district:
            messages.error(request, 'هیچ منطقه‌ای به حساب شما اختصاص داده نشده است.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def district_admin_api_required(view_func):
    """نسخه API: پاسخ JSON با کد وضعیت مناسب."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {'success': False, 'code': 'UNAUTHORIZED',
                 'message': 'احراز هویت لازم است.'},
                status=401,
            )
        if request.user.role != 'district_admin':
            return JsonResponse(
                {'success': False, 'code': 'FORBIDDEN',
                 'message': 'دسترسی غیرمجاز.'},
                status=403,
            )
        if not request.user.district:
            return JsonResponse(
                {'success': False, 'code': 'NO_DISTRICT',
                 'message': 'منطقه‌ای اختصاص داده نشده.'},
                status=403,
            )
        return view_func(request, *args, **kwargs)
    return wrapper