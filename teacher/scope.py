"""
هسته اجبار محدوده (Scope Enforcement) برای معلم.
الگوی مشابه: district/scope.py, school/scope.py

هیچ ویو یا سرویسی نباید بدون عبور از این لایه
به داده‌های آموزشی دسترسی پیدا کند.
"""
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.db.models import Q

from accounts.models import User
from dashboard.models import Classroom, ClassSession, Question
from .constants import TeacherPermission, TEACHER_ALL_PERMISSIONS


class TeacherScopeViolationError(Exception):
    """دسترسی خارج از محدوده معلم"""
    pass


class TeacherScope:
    """
    محدوده دسترسی معلم.
    یک‌بار ساخته می‌شود و تمام کوئری‌ها از آن عبور می‌کنند.

    استفاده:
        scope = TeacherScope(request.user)
        classroom = scope.get_class_or_404(classroom_id)
        student = scope.get_student_or_404(student_id)
    """

    def __init__(self, user):
        if user.role != 'teacher':
            raise TeacherScopeViolationError(
                'کاربر نقش معلم ندارد.'
            )
        self.user = user
        self.teacher = user
        self._permissions = None

    # ──────────────────────────────────────────────
    #  Permissions
    # ──────────────────────────────────────────────
    @property
    def permissions(self):
        """معلم تمام دسترسی‌های آموزشی خودش را دارد"""
        if self._permissions is None:
            self._permissions = TEACHER_ALL_PERMISSIONS.copy()
        return self._permissions

    def has_permission(self, permission):
        return permission in self.permissions

    # ──────────────────────────────────────────────
    #  QuerySet Filters (اجباری)
    # ──────────────────────────────────────────────
    def filter_classes(self, qs=None):
        """فقط کلاس‌هایی که معلم فعلی آن‌هاست"""
        if qs is None:
            qs = Classroom.objects.all()
        return qs.filter(teacher=self.user)

    def filter_sessions(self, qs=None):
        """فقط جلسات کلاس‌های معلم"""
        if qs is None:
            qs = ClassSession.objects.all()
        return qs.filter(classroom__teacher=self.user)

    def filter_students(self, qs=None, classroom=None):
        """فقط دانش‌آموزان کلاس‌های معلم"""
        if qs is None:
            qs = User.objects.filter(role='student')
        base_filter = Q(enrolled_classes__teacher=self.user)
        if classroom:
            base_filter &= Q(enrolled_classes=classroom)
        return qs.filter(base_filter).distinct()

    def filter_questions(self, qs=None):
        """فقط سوالات کلاس‌های معلم"""
        if qs is None:
            qs = Question.objects.all()
        return qs.filter(classroom__teacher=self.user)

    def filter_attendance_requests(self, qs=None):
        """فقط درخواست‌های حضور معلم"""
        from dashboard.models import AttendanceRequest
        if qs is None:
            qs = AttendanceRequest.objects.all()
        return qs.filter(teacher=self.user)

    def filter_attendance_responses(self, qs=None):
        """فقط پاسخ‌های حضور کلاس‌های معلم"""
        from dashboard.models import AttendanceResponse
        if qs is None:
            qs = AttendanceResponse.objects.all()
        return qs.filter(
            attendance_request__teacher=self.user
        )

    def filter_student_answers(self, qs=None):
        """فقط پاسخ‌های سوالات کلاس‌های معلم"""
        from dashboard.models import StudentAnswer
        if qs is None:
            qs = StudentAnswer.objects.all()
        return qs.filter(
            question__classroom__teacher=self.user
        )

    # ──────────────────────────────────────────────
    #  Safe Object Retrieval (جلوگیری از IDOR)
    # ──────────────────────────────────────────────
    def get_class_or_404(self, classroom_id):
        """
        هرگز از Classroom.objects.get(id=...) استفاده نکنید.
        """
        return get_object_or_404(
            Classroom,
            id=classroom_id,
            teacher=self.user,  # ← اجبار محدوده
        )

    def get_session_or_404(self, session_id):
        """جلسه باید متعلق به کلاس معلم باشد"""
        return get_object_or_404(
            ClassSession,
            id=session_id,
            classroom__teacher=self.user,
        )

    def get_student_or_404(self, student_id):
        """
        دانش‌آموز باید در یکی از کلاس‌های معلم ثبت‌نام باشد.
        """
        qs = User.objects.filter(
            id=student_id,
            role='student',
            enrolled_classes__teacher=self.user,
        ).distinct()
        return get_object_or_404(qs)

    def get_question_or_404(self, question_id):
        """سوال باید متعلق به کلاس معلم باشد"""
        return get_object_or_404(
            Question,
            id=question_id,
            classroom__teacher=self.user,
        )

    def get_attendance_request_or_404(self, request_id):
        """درخواست حضور باید متعلق به معلم باشد"""
        from dashboard.models import AttendanceRequest
        return get_object_or_404(
            AttendanceRequest,
            id=request_id,
            teacher=self.user,
        )

    def get_attendance_response_or_404(self, response_id):
        """پاسخ حضور باید متعلق به کلاس معلم باشد"""
        from dashboard.models import AttendanceResponse
        return get_object_or_404(
            AttendanceResponse,
            id=response_id,
            attendance_request__teacher=self.user,
        )

    def get_assessment_or_404(self, assessment_id):
        """ارزیابی باید متعلق به معلم باشد"""
        from .models import Assessment
        return get_object_or_404(
            Assessment,
            id=assessment_id,
            teacher=self.user,
        )

    def get_homework_or_404(self, homework_id):
        """تکلیف باید متعلق به معلم باشد"""
        from .models import Homework
        return get_object_or_404(
            Homework,
            id=homework_id,
            teacher=self.user,
        )

    def get_participation_record_or_404(self, record_id):
        """رکورد مشارکت باید متعلق به جلسه کلاس معلم باشد"""
        from .models import ParticipationRecord
        return get_object_or_404(
            ParticipationRecord,
            id=record_id,
            session__classroom__teacher=self.user,
        )

    def get_teacher_note_or_404(self, note_id):
        """یادداشت باید متعلق به خود معلم باشد"""
        from .models import TeacherNote
        return get_object_or_404(
            TeacherNote,
            id=note_id,
            teacher=self.user,
        )

    def get_feedback_or_404(self, feedback_id):
        """بازخورد باید متعلق به معلم باشد"""
        from .models import TeacherFeedback
        return get_object_or_404(
            TeacherFeedback,
            id=feedback_id,
            teacher=self.user,
        )

    # ──────────────────────────────────────────────
    #  Validation Helpers
    # ──────────────────────────────────────────────
    def validate_classroom_id(self, classroom_id):
        """اعتبارسنجی پارامتر اختیاری فیلتر"""
        if not classroom_id:
            return None
        try:
            return self.get_class_or_404(classroom_id)
        except Http404:
            raise Http404('کلاس مورد نظر در محدوده شما نیست.')

    def is_student_in_class(self, student_id, classroom_id):
        """بررسی عضویت دانش‌آموز در کلاس"""
        return User.objects.filter(
            id=student_id,
            role='student',
            enrolled_classes__id=classroom_id,
            enrolled_classes__teacher=self.user,
        ).exists()