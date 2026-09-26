"""
هسته اجبار محدوده (Scope Enforcement) برای دانش‌آموز.
الگوی مشابه: teacher/scope.py, school/scope.py, district/scope.py

هر ویو یا سرویسی باید از این لایه عبور کند.
دانش‌آموز فقط به داده‌های خودش دسترسی دارد.
"""
from django.http import Http404
from django.shortcuts import get_object_or_404

from accounts.models import User
from dashboard.models import (
    Classroom, ClassSession, Question, StudentAnswer,
    AttendanceRequest, AttendanceResponse, WeeklySchedule,
)


class StudentScopeViolationError(Exception):
    """دسترسی خارج از محدوده دانش‌آموز"""
    pass


class StudentScope:
    """
    محدوده دسترسی دانش‌آموز.
    یک‌بار ساخته می‌شود و تمام کوئری‌ها از آن عبور می‌کنند.

    استفاده:
        scope = StudentScope(request.user)
        classroom = scope.get_class_or_404(classroom_id)
    """

    def __init__(self, user):
        if user.role != 'student':
            raise StudentScopeViolationError('کاربر نقش دانش‌آموز ندارد.')
        self.user = user
        self.student = user

    # ──────────────────────────────────────────────
    #  QuerySet Filters (اجباری)
    # ──────────────────────────────────────────────

    def filter_classes(self, qs=None):
        """فقط کلاس‌هایی که دانش‌آموز عضو آن‌هاست"""
        if qs is None:
            qs = Classroom.objects.all()
        return qs.filter(students=self.student)

    def filter_sessions(self, qs=None):
        """فقط جلسات کلاس‌های دانش‌آموز"""
        if qs is None:
            qs = ClassSession.objects.all()
        return qs.filter(classroom__students=self.student)

    def filter_questions(self, qs=None):
        """فقط سوالات کلاس‌های دانش‌آموز"""
        if qs is None:
            qs = Question.objects.all()
        return qs.filter(classroom__students=self.student)

    def filter_schedules(self, qs=None):
        """فقط برنامه هفتگی کلاس‌های دانش‌آموز"""
        if qs is None:
            qs = WeeklySchedule.objects.all()
        return qs.filter(classroom__students=self.student)

    def filter_attendance_requests(self, qs=None):
        """فقط درخواست‌های حضور کلاس‌های دانش‌آموز"""
        if qs is None:
            qs = AttendanceRequest.objects.all()
        return qs.filter(classroom__students=self.student)

    def filter_attendance_responses(self, qs=None):
        """فقط پاسخ‌های حضور خود دانش‌آموز"""
        if qs is None:
            qs = AttendanceResponse.objects.all()
        return qs.filter(student=self.student)

    def filter_student_answers(self, qs=None):
        """فقط پاسخ‌های خود دانش‌آموز"""
        if qs is None:
            qs = StudentAnswer.objects.all()
        return qs.filter(student=self.student)

    def filter_assessments(self, qs=None):
        """فقط ارزیابی‌های کلاس‌های دانش‌آموز"""
        from teacher.models import Assessment
        if qs is None:
            qs = Assessment.objects.all()
        return qs.filter(classroom__students=self.student)

    def filter_homeworks(self, qs=None):
        """فقط تکالیف کلاس‌های دانش‌آموز"""
        from teacher.models import Homework
        if qs is None:
            qs = Homework.objects.all()
        return qs.filter(classroom__students=self.student)

    def filter_homework_submissions(self, qs=None):
        """فقط ارسال‌های خود دانش‌آموز"""
        from teacher.models import HomeworkSubmission
        if qs is None:
            qs = HomeworkSubmission.objects.all()
        return qs.filter(student=self.student)

    def filter_feedbacks(self, qs=None):
        """فقط بازخوردهای خود دانش‌آموز"""
        from teacher.models import TeacherFeedback
        if qs is None:
            qs = TeacherFeedback.objects.all()
        return qs.filter(student=self.student)

    def filter_participation_records(self, qs=None):
        """فقط رکوردهای مشارکت خود دانش‌آموز"""
        from teacher.models import ParticipationRecord
        if qs is None:
            qs = ParticipationRecord.objects.all()
        return qs.filter(student=self.student)

    def filter_student_requests(self, qs=None):
        """فقط درخواست‌های خود دانش‌آموز"""
        from .models import StudentRequest
        if qs is None:
            qs = StudentRequest.objects.all()
        return qs.filter(student=self.student)

    # ──────────────────────────────────────────────
    #  Safe Object Retrieval (جلوگیری از IDOR)
    # ──────────────────────────────────────────────

    def get_class_or_404(self, classroom_id):
        return get_object_or_404(
            Classroom,
            id=classroom_id,
            students=self.student,
        )

    def get_session_or_404(self, session_id):
        return get_object_or_404(
            ClassSession,
            id=session_id,
            classroom__students=self.student,
        )

    def get_question_or_404(self, question_id):
        return get_object_or_404(
            Question,
            id=question_id,
            classroom__students=self.student,
        )

    def get_attendance_request_or_404(self, request_id):
        return get_object_or_404(
            AttendanceRequest,
            id=request_id,
            classroom__students=self.student,
        )

    def get_attendance_response_or_404(self, response_id):
        """فقط پاسخ حضور خود دانش‌آموز"""
        return get_object_or_404(
            AttendanceResponse,
            id=response_id,
            student=self.student,
        )

    def get_assessment_or_404(self, assessment_id):
        from teacher.models import Assessment
        return get_object_or_404(
            Assessment,
            id=assessment_id,
            classroom__students=self.student,
        )

    def get_homework_or_404(self, homework_id):
        from teacher.models import Homework
        return get_object_or_404(
            Homework,
            id=homework_id,
            classroom__students=self.student,
        )

    def get_homework_submission_or_404(self, submission_id):
        """فقط ارسال خود دانش‌آموز"""
        from teacher.models import HomeworkSubmission
        return get_object_or_404(
            HomeworkSubmission,
            id=submission_id,
            student=self.student,
        )

    def get_student_request_or_404(self, request_pk):
        from .models import StudentRequest
        return get_object_or_404(
            StudentRequest,
            id=request_pk,
            student=self.student,
        )

    def get_face_change_request_or_404(self, request_pk):
        from .models import StudentFaceChangeRequest
        return get_object_or_404(
            StudentFaceChangeRequest,
            id=request_pk,
            student=self.student,
        )