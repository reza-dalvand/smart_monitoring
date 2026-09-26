"""
هسته اجبار محدوده (Scope Enforcement) برای مدرسه.
مشابه الگوی district/scope.py و province/scope.py.
هیچ ویو یا سرویسی نباید بدون عبور از این لایه به داده دسترسی پیدا کند.
"""
from django.http import Http404
from django.shortcuts import get_object_or_404

from national.models import School
from dashboard.models import Classroom, ClassSession
from accounts.models import User
from .models import SchoolStaffAssignment
from .constants import StaffRole, Permission


class SchoolScopeViolationError(Exception):
    """دسترسی خارج از محدوده مدرسه"""
    pass


class SchoolScope:
    """
    محدوده دسترسی کاربر به مدرسه.
    یک‌بار ساخته می‌شود و تمام کوئری‌ها از آن عبور می‌کنند.
    """

    def __init__(self, user):
        self.user = user
        self._assignments = None
        self._permissions = None
        self._active_school_id = None

    # ──────────────────────────────────────────────
    #  Assignments
    # ──────────────────────────────────────────────
    @property
    def assignments(self):
        if self._assignments is None:
            self._assignments = list(
                SchoolStaffAssignment.objects.filter(
                    user=self.user,
                    is_active=True,
                ).select_related('school')
            )
        return self._assignments

    @property
    def active_assignments(self):
        return [a for a in self.assignments if a.is_currently_active]

    @property
    def schools(self):
        """لیست مدارس مجاز"""
        return [a.school for a in self.active_assignments]

    @property
    def school_ids(self):
        return [a.school_id for a in self.active_assignments]

    @property
    def is_principal(self):
        return any(
            a.staff_role == StaffRole.PRINCIPAL
            for a in self.active_assignments
        )

    @property
    def is_assistant(self):
        return any(
            a.staff_role == StaffRole.ASSISTANT
            for a in self.active_assignments
        )

    @property
    def assistant_types(self):
        """انواع معاونت کاربر"""
        return set(
            a.assistant_type
            for a in self.active_assignments
            if a.staff_role == StaffRole.ASSISTANT and a.assistant_type
        )

    # ──────────────────────────────────────────────
    #  Single School Context
    # ──────────────────────────────────────────────
    def set_active_school(self, school_id):
        """تنظیم مدرسه فعال (برای کاربران با چند مدرسه)"""
        if school_id not in self.school_ids:
            raise SchoolScopeViolationError('مدرسه مورد نظر در محدوده دسترسی شما نیست.')
        self._active_school_id = school_id

    @property
    def active_school(self):
        """مدرسه فعال فعلی"""
        if self._active_school_id:
            return self.get_school_or_404(self._active_school_id)
        # اگر فقط یک مدرسه دارد، همان را برگردان
        if len(self.school_ids) == 1:
            return self.get_school_or_404(self.school_ids[0])
        return None

    @property
    def active_school_id(self):
        school = self.active_school
        return school.id if school else None

    # ──────────────────────────────────────────────
    #  Permissions
    # ──────────────────────────────────────────────
    def get_permissions_for_school(self, school_id=None):
        """دسترسی‌های کاربر برای یک مدرسه مشخص"""
        target_id = school_id or self.active_school_id
        perms = set()
        for a in self.active_assignments:
            if a.school_id == target_id:
                perms |= a.get_permissions()
        return perms

    def has_permission(self, permission, school_id=None):
        """بررسی یک دسترسی خاص"""
        return permission in self.get_permissions_for_school(school_id)

    # ──────────────────────────────────────────────
    #  QuerySet Filters (اجباری)
    # ──────────────────────────────────────────────
    def filter_schools(self, qs=None):
        if qs is None:
            qs = School.objects.all()
        return qs.filter(id__in=self.school_ids)

    def filter_classrooms(self, qs=None, school_id=None):
        if qs is None:
            qs = Classroom.objects.all()
        sid = school_id or self.active_school_id
        if sid:
            return qs.filter(school_id=sid)
        return qs.filter(school_id__in=self.school_ids)

    def filter_students(self, qs=None, school_id=None):
        if qs is None:
            qs = User.objects.filter(role='student')
        sid = school_id or self.active_school_id
        if sid:
            return qs.filter(
                enrolled_classes__school_id=sid
            ).distinct()
        return qs.filter(
            enrolled_classes__school_id__in=self.school_ids
        ).distinct()

    def filter_teachers(self, qs=None, school_id=None):
        if qs is None:
            qs = User.objects.filter(role='teacher')
        sid = school_id or self.active_school_id
        if sid:
            return qs.filter(
                taught_classes__school_id=sid
            ).distinct()
        return qs.filter(
            taught_classes__school_id__in=self.school_ids
        ).distinct()

    def filter_sessions(self, qs=None, school_id=None):
        if qs is None:
            qs = ClassSession.objects.all()
        sid = school_id or self.active_school_id
        if sid:
            return qs.filter(classroom__school_id=sid)
        return qs.filter(classroom__school_id__in=self.school_ids)

    # ──────────────────────────────────────────────
    #  Safe Object Retrieval (جلوگیری از IDOR)
    # ──────────────────────────────────────────────
    def get_school_or_404(self, school_id):
        """هرگز از School.objects.get(id=...) به‌تنهایی استفاده نکنید."""
        return get_object_or_404(
            School,
            id=school_id,
            id__in=self.school_ids,  # ← اجبار محدوده
        )

    def get_classroom_or_404(self, classroom_id):
        return get_object_or_404(
            Classroom,
            id=classroom_id,
            school_id__in=self.school_ids,
        )

    def get_student_or_404(self, student_id):
        """هرگز از User.objects.get(id=...) به‌تنهایی استفاده نکنید."""
        qs = User.objects.filter(
            id=student_id,
            role='student',
            enrolled_classes__school_id__in=self.school_ids,
        ).distinct()  # ← جلوگیری از رکوردهای تکراری ناشی از JOIN
        return get_object_or_404(qs)

    def get_teacher_or_404(self, teacher_id):
        qs = User.objects.filter(
            id=teacher_id,
            role='teacher',
            taught_classes__school_id__in=self.school_ids,
        ).distinct()  # ← جلوگیری از رکوردهای تکراری ناشی از JOIN
        return get_object_or_404(qs)

    def validate_school_id(self, school_id):
        """اعتبارسنجی پارامتر اختیاری فیلتر"""
        if not school_id:
            return None
        try:
            return self.get_school_or_404(school_id)
        except Http404:
            raise Http404('مدرسه مورد نظر در محدوده دسترسی شما نیست.')