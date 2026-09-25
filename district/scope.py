"""
هسته اجبار محدوده (Scope Enforcement) برای مسئول منطقه.
هیچ ویو یا سرویسی نباید بدون عبور از این لایه به داده دسترسی پیدا کند.
هر کوئری باید از متدهای این کلاس استفاده کند.
"""
from django.http import Http404
from django.shortcuts import get_object_or_404

from national.models import District, School
from dashboard.models import Classroom
from accounts.models import User


class ScopeViolationError(Exception):
    """دسترسی خارج از محدوده منطقه"""
    pass


class DistrictScope:
    """
    محدوده ثابت مسئول منطقه.
    یک‌بار ساخته می‌شود و تمام کوئری‌ها از آن عبور می‌کنند.
    """

    def __init__(self, user):
        if user.role != 'district_admin':
            raise ScopeViolationError('کاربر نقش مسئول منطقه ندارد.')
        if not user.district:
            raise ScopeViolationError('هیچ منطقه‌ای به این کاربر اختصاص داده نشده.')
        self.user = user
        self.district = user.district
        self.district_id = user.district.id
        self.province = user.district.province

    # ──────────────────────────────────────────────
    #  QuerySet Filters (اجباری)
    # ──────────────────────────────────────────────

    def filter_schools(self, qs=None):
        if qs is None:
            qs = School.objects.all()
        return qs.filter(district=self.district)

    def filter_classrooms(self, qs=None):
        if qs is None:
            qs = Classroom.objects.all()
        return qs.filter(school__district=self.district)

    def filter_students(self, qs=None):
        if qs is None:
            qs = User.objects.filter(role='student')
        return qs.filter(
            enrolled_classes__school__district=self.district
        ).distinct()

    def filter_teachers(self, qs=None):
        if qs is None:
            qs = User.objects.filter(role='teacher')
        return qs.filter(
            taught_classes__school__district=self.district
        ).distinct()

    # ──────────────────────────────────────────────
    #  Safe Object Retrieval (جلوگیری از ID جعلی)
    # ──────────────────────────────────────────────

    def get_school_or_404(self, school_id):
        """هرگز از School.objects.get(id=...) به‌تنهایی استفاده نکنید."""
        return get_object_or_404(
            School,
            id=school_id,
            district=self.district,  # ← اجبار محدوده
        )

    def get_classroom_or_404(self, classroom_id):
        return get_object_or_404(
            Classroom,
            id=classroom_id,
            school__district=self.district,
        )

    def validate_school_id(self, school_id):
        """
        اگر school_id خارج از منطقه باشد → 404.
        برای استفاده در پارامترهای اختیاری فیلتر.
        """
        if not school_id:
            return None
        try:
            return self.get_school_or_404(school_id)
        except Http404:
            raise Http404('مدرسه مورد نظر در محدوده منطقه شما نیست.')