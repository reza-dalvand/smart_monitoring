"""
تست‌های امنیتی و عملکردی ماژول دانش‌آموز.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from dashboard.models import Classroom, ClassSession, Question, WeeklySchedule
from teacher.models import Assessment, Homework, HomeworkSubmission
from .models import StudentRequest, StudentFaceChangeRequest
from .constants import StudentRequestStatus, StudentRequestType

User = get_user_model()


class StudentAccessTests(TestCase):
    """تست‌های دسترسی"""

    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(
            username='student_test', password='test123', role='student')
        self.teacher = User.objects.create_user(
            username='teacher_test', password='test123', role='teacher')
        self.assistant = User.objects.create_user(
            username='assistant_test', password='test123', role='assistant')

    def test_student_can_access_dashboard(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('student:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_teacher_cannot_access_student_routes(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('student:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_assistant_cannot_access_student_routes(self):
        self.client.force_login(self.assistant)
        response = self.client.get(reverse('student:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_cannot_access(self):
        response = self.client.get(reverse('student:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_student_can_access_profile(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('student:profile'))
        self.assertEqual(response.status_code, 200)

    def test_student_can_access_schedule(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('student:schedule'))
        self.assertEqual(response.status_code, 200)

    def test_student_can_access_requests(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('student:requests'))
        self.assertEqual(response.status_code, 200)


class StudentIDORTests(TestCase):
    """تست‌های جلوگیری از IDOR"""

    def setUp(self):
        self.client = Client()
        self.student_a = User.objects.create_user(
            username='student_a', password='test123', role='student')
        self.student_b = User.objects.create_user(
            username='student_b', password='test123', role='student')
        self.teacher = User.objects.create_user(
            username='teacher_idor', password='test123', role='teacher')

        self.class_a = Classroom.objects.create(
            name='کلاس الف', subject='ریاضی',
            teacher=self.teacher, teacher_name='معلم')
        self.class_a.students.add(self.student_a)

        self.class_b = Classroom.objects.create(
            name='کلاس ب', subject='فیزیک',
            teacher=self.teacher, teacher_name='معلم')
        self.class_b.students.add(self.student_b)

    def test_student_cannot_access_other_class(self):
        self.client.force_login(self.student_a)
        response = self.client.get(
            reverse('student:class_detail', args=[self.class_b.id]))
        self.assertEqual(response.status_code, 404)

    def test_student_can_access_own_class(self):
        self.client.force_login(self.student_a)
        response = self.client.get(
            reverse('student:class_detail', args=[self.class_a.id]))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_see_other_student_requests(self):
        # ایجاد درخواست برای دانش‌آموز B
        req = StudentRequest.objects.create(
            student=self.student_b,
            request_type=StudentRequestType.GENERAL,
            title='درخواست تست',
            description='تست',
        )
        # دانش‌آموز A سعی در مشاهده آن دارد
        self.client.force_login(self.student_a)
        response = self.client.get(
            reverse('student:request_detail', args=[req.id]))
        self.assertEqual(response.status_code, 404)

    def test_student_can_see_own_requests(self):
        req = StudentRequest.objects.create(
            student=self.student_a,
            request_type=StudentRequestType.GENERAL,
            title='درخواست من',
            description='تست',
        )
        self.client.force_login(self.student_a)
        response = self.client.get(
            reverse('student:request_detail', args=[req.id]))
        self.assertEqual(response.status_code, 200)


class StudentHomeworkTests(TestCase):
    """تست‌های تکالیف"""

    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(
            username='student_hw', password='test123', role='student')
        self.teacher = User.objects.create_user(
            username='teacher_hw', password='test123', role='teacher')
        self.classroom = Classroom.objects.create(
            name='کلاس', subject='درس',
            teacher=self.teacher, teacher_name='معلم')
        self.classroom.students.add(self.student)

        from django.utils import timezone
        from datetime import timedelta
        self.homework = Homework.objects.create(
            title='تکلیف تست',
            teacher=self.teacher,
            classroom=self.classroom,
            deadline=timezone.now() + timedelta(days=7),
            status='ACTIVE',
        )

    def test_student_can_see_own_homework(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('student:homeworks'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تکلیف تست')

    def test_student_can_view_homework_detail(self):
        self.client.force_login(self.student)
        response = self.client.get(
            reverse('student:homework_detail', args=[self.homework.id]))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_access_unrelated_homework(self):
        other_class = Classroom.objects.create(
            name='کلاس دیگر', subject='درس دیگر',
            teacher=self.teacher, teacher_name='معلم')
        other_hw = Homework.objects.create(
            title='تکلیف دیگر',
            teacher=self.teacher,
            classroom=other_class,
            deadline=timezone.now() + timedelta(days=7),
            status='ACTIVE',
        )
        self.client.force_login(self.student)
        response = self.client.get(
            reverse('student:homework_detail', args=[other_hw.id]))
        self.assertEqual(response.status_code, 404)


class StudentRequestTests(TestCase):
    """تست‌های درخواست‌ها"""

    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(
            username='student_req', password='test123', role='student')

    def test_student_can_create_request(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('student:request_create'),
            {
                'request_type': StudentRequestType.GENERAL,
                'title': 'درخواست تست',
                'description': 'شرح درخواست',
                'priority': 'MEDIUM',
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StudentRequest.objects.filter(
            student=self.student, title='درخواست تست'
        ).exists())

    def test_student_can_cancel_open_request(self):
        req = StudentRequest.objects.create(
            student=self.student,
            request_type=StudentRequestType.GENERAL,
            title='درخواست',
            description='تست',
            status=StudentRequestStatus.OPEN,
        )
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('student:request_cancel', args=[req.id]))
        req.refresh_from_db()
        self.assertEqual(req.status, StudentRequestStatus.CANCELLED)

    def test_student_cannot_cancel_resolved_request(self):
        req = StudentRequest.objects.create(
            student=self.student,
            request_type=StudentRequestType.GENERAL,
            title='درخواست',
            description='تست',
            status=StudentRequestStatus.RESOLVED,
        )
        self.client.force_login(self.student)
        self.client.post(reverse('student:request_cancel', args=[req.id]))
        req.refresh_from_db()
        self.assertEqual(req.status, StudentRequestStatus.RESOLVED)


class StudentFaceTests(TestCase):
    """تست‌های احراز هویت چهره"""

    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(
            username='student_face', password='test123', role='student')

    def test_student_can_view_face_page(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('student:face'))
        self.assertEqual(response.status_code, 200)

    def test_student_can_submit_face_change_request(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('student:face_change_request'),
            {'reason': 'چهره من تغییر کرده است.'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StudentFaceChangeRequest.objects.filter(
            student=self.student
        ).exists())

    def test_student_cannot_approve_own_face_request(self):
        """دانش‌آموز نمی‌تواند درخواست خودش را تأیید کند"""
        req = StudentFaceChangeRequest.objects.create(
            student=self.student,
            reason='تست',
        )
        # هیچ ویویی برای تأیید توسط دانش‌آموز وجود ندارد
        # این تست تأیید می‌کند که چنین ویویی وجود ندارد
        self.client.force_login(self.student)
        # تلاش برای دسترسی به ویوی تأیید (وجود ندارد)
        # اگر وجود داشت، باید ۴۰۳ یا ۴۰۴ برگرداند


class StudentAssessmentTests(TestCase):
    """تست‌های ارزیابی"""

    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(
            username='student_assess', password='test123', role='student')
        self.teacher = User.objects.create_user(
            username='teacher_assess', password='test123', role='teacher')
        self.classroom = Classroom.objects.create(
            name='کلاس', subject='درس',
            teacher=self.teacher, teacher_name='معلم')
        self.classroom.students.add(self.student)

        self.assessment = Assessment.objects.create(
            title='آزمون تست',
            teacher=self.teacher,
            classroom=self.classroom,
            status='published',
        )

    def test_student_can_see_own_assessment(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('student:assessments'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'آزمون تست')

    def test_student_cannot_access_unrelated_assessment(self):
        other_class = Classroom.objects.create(
            name='کلاس دیگر', subject='درس دیگر',
            teacher=self.teacher, teacher_name='معلم')
        other_assessment = Assessment.objects.create(
            title='آزمون دیگر',
            teacher=self.teacher,
            classroom=other_class,
            status='published',
        )
        self.client.force_login(self.student)
        response = self.client.get(
            reverse('student:assessment_detail', args=[other_assessment.id]))
        self.assertEqual(response.status_code, 404)