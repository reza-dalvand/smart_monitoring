"""
هسته اجبار محدوده (Scope Enforcement)

هیچ ویو یا سرویسی نباید بدون عبور از این لایه به داده دسترسی پیدا کند.
هر کوئری باید از متدهای این کلاس استفاده کند.
"""
from django.http import Http404
from django.shortcuts import get_object_or_404

from national.models import Province, District, School
from dashboard.models import Classroom


class ScopeViolationError(Exception):
    """دسترسی خارج از محدوده استان"""
    pass


class ProvinceScope:
    """
    محدوده ثابت مسئول استانی.
    یک‌بار ساخته می‌شود و تمام کوئری‌ها از آن عبور می‌کنند.
    """

    def __init__(self, user):
        if user.role != 'province_admin':
            raise ScopeViolationError('کاربر نقش مسئول استانی ندارد.')
        if not user.province:
            raise ScopeViolationError('هیچ استانی به این کاربر اختصاص داده نشده.')
        self.user = user
        self.province = user.province
        self.province_id = user.province.id

    # ──────────────────────────────────────────────
    #  QuerySet Filters (اجباری)
    # ──────────────────────────────────────────────

    def filter_districts(self, qs=None):
        if qs is None:
            qs = District.objects.all()
        return qs.filter(province=self.province)

    def filter_schools(self, qs=None):
        if qs is None:
            qs = School.objects.all()
        return qs.filter(district__province=self.province)

    def filter_classrooms(self, qs=None):
        if qs is None:
            qs = Classroom.objects.all()
        return qs.filter(school__district__province=self.province)

    # ──────────────────────────────────────────────
    #  Safe Object Retrieval (جلوگیری از ID جعلی)
    # ──────────────────────────────────────────────

    def get_district_or_404(self, district_id):
        """هرگز از District.objects.get(id=...) به‌تنهایی استفاده نکنید."""
        district = get_object_or_404(
            District,
            id=district_id,
            province=self.province,   # ← اجبار محدوده
        )
        return district

    def get_school_or_404(self, school_id):
        return get_object_or_404(
            School,
            id=school_id,
            district__province=self.province,
        )

    def get_classroom_or_404(self, classroom_id):
        return get_object_or_404(
            Classroom,
            id=classroom_id,
            school__district__province=self.province,
        )

    def validate_district_id(self, district_id):
        """
        اگر district_id خارج از استان باشد → 404.
        برای استفاده در پارامترهای اختیاری فیلتر.
        """
        if not district_id:
            return None
        try:
            return self.get_district_or_404(district_id)
        except Http404:
            raise Http404('منطقه مورد نظر در محدوده استان شما نیست.')