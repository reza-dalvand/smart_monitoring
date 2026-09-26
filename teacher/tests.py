"""
تست‌های امنیتی و عملکردی ماژول معلم.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from national.models import Province, District, School
from dashboard.models import Classroom, ClassSession
from .models import (
    SessionExtension, ParticipationRecord,
    Assessment, Homework, TeacherNote,
)
from .scope import TeacherScope
from .constants import SessionStatus

User = get_user_model()


class TeacherScopeSecurityTests(TestCase):
    """تست‌های امنیتی: جلوگیری از دسترسی بین‌معلمی"""

    def setUp(self):
        self.client = Client()
        self.province = Province.objects.create(name='تهران', code='01')
        self.district = District.objects.create(
            province=self.province, name='منطقه ۱')
        self.school = School.objects.create(
            district=self.district, name='مدرسه تست')

        self.teacher_a = User.objects.create_user(
            username='teacher_a', password='test123', role='teacher')
        self.teacher_b = User.objects.create_user(
            username='teacher_b', password='test123', role='teacher')
        self.student_a = User.objects.create_user(
            username='student_a', password='test123', role='student')
        self.student_b = User.objects.create_user(
            username='student_b', password='test123', role='student')

        self.class_a = Classroom.objects.create(
            name='کلاس الف', subject='ریاضی',
            teacher=self.teacher_a, teacher_name='معلم الف',
            school=self.school)
        self.class_b = Classroom.objects.create(
            name='کلاس ب', subject='فیزیک',
            teacher=self.teacher_b, teacher_name='معلم ب',
            school=self.school)

        self.class_a.students.add(self.student_a)
        self.class_b.students.add(self.student_b)

        self.session_a = ClassSession.objects.create(
            classroom=self.class_a, topic='جلسه تست الف')
        self.session_b = ClassSession.objects.create(
            classroom=self.class_b, topic='جلسه تست ب')

    # ── دسترسی مجاز ──
    def test_teacher_a_can_view_own_dashboard(self):
        self.client.force_login(self.teacher_a)
        response = self.client.get(reverse('teacher:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_teacher_a_can_view_own_classes(self):
        self.client.force_login(self.teacher_a)
        response = self.client.get(reverse('teacher:classes'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'کلاس الف')
        self.assertNotContains(response, 'کلاس ب')

    def test_teacher_a_can_view_own_session(self):
        self.client.force_login(self.teacher_a)
        response = self.client.get(
            reverse('teacher:session_detail', args=[self.session_a.id]))
        self.assertEqual(response.status_code, 200)

    # ── دسترسی غیرمجاز بین‌معلمی ──
    def test_teacher_a_cannot_access_teacher_b_class(self):
        self.client.force_login(self.teacher_a)
        response = self.client.get(
            reverse('teacher:class_detail', args=[self.class_b.id]))
        self.assertEqual(response.status_code, 404)

    def test_teacher_a_cannot_access_teacher_b_student(self):
        self.client.force_login(self.teacher_a)
        response = self.client.get(
            reverse('teacher:student_detail', args=[self.student_b.id]))
        self.assertEqual(response.status_code, 404)

    def test_teacher_a_cannot_access_teacher_b_session(self):
        self.client.force_login(self.teacher_a)
        response = self.client.get(
            reverse('teacher:session_detail', args=[self.session_b.id]))
        self.assertEqual(response.status_code, 404)

    # ── نقش‌های غیرمجاز ──
    def test_student_cannot_access_teacher_panel(self):
        self.client.force_login(self.student_a)
        response = self.client.get(reverse('teacher:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_cannot_access(self):
        response = self.client.get(reverse('teacher:dashboard'))
        self.assertEqual(response.status_code, 302)


class TeacherScopeUnitTests(TestCase):
    """تست‌های واحد TeacherScope"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher_unit', password='test', role='teacher')
        self.student = User.objects.create_user(
            username='student_unit', password='test', role='student')
        self.classroom = Classroom.objects.create(
            name='کلاس', subject='درس',
            teacher=self.teacher, teacher_name='معلم')
        self.classroom.students.add(self.student)

    def test_scope_creation_for_teacher(self):
        scope = TeacherScope(self.teacher)
        self.assertEqual(scope.user, self.teacher)

    def test_scope_filter_classes(self):
        scope = TeacherScope(self.teacher)
        classes = scope.filter_classes()
        self.assertEqual(classes.count(), 1)
        self.assertEqual(classes.first(), self.classroom)

    def test_scope_get_class_or_404(self):
        scope = TeacherScope(self.teacher)
        classroom = scope.get_class_or_404(self.classroom.id)
        self.assertEqual(classroom, self.classroom)

    def test_scope_get_class_or_404_unauthorized(self):
        other_teacher = User.objects.create_user(
            username='other_teacher', password='test', role='teacher')
        scope = TeacherScope(other_teacher)
        from django.http import Http404
        with self.assertRaises(Http404):
            scope.get_class_or_404(self.classroom.id)

    def test_scope_get_student_or_404(self):
        scope = TeacherScope(self.teacher)
        student = scope.get_student_or_404(self.student.id)
        self.assertEqual(student, self.student)

    def test_scope_get_student_or_404_unauthorized(self):
        other_teacher = User.objects.create_user(
            username='other_teacher2', password='test', role='teacher')
        scope = TeacherScope(other_teacher)
        from django.http import Http404
        with self.assertRaises(Http404):
            scope.get_student_or_404(self.student.id)


class SessionTests(TestCase):
    """تست‌های جلسه"""

    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user(
            username='teacher_session', password='test', role='teacher')
        self.classroom = Classroom.objects.create(
            name='کلاس', subject='درس',
            teacher=self.teacher, teacher_name='معلم')
        self.client.force_login(self.teacher)

    def test_create_session(self):
        response = self.client.post(
            reverse('teacher:session_create'),
            {'classroom': self.classroom.id, 'topic': 'جلسه تست'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ClassSession.objects.filter(
            topic='جلسه تست').exists())

    def test_start_session(self):
        session = ClassSession.objects.create(
            classroom=self.classroom, topic='تست')
        SessionExtension.objects.create(
            session=session, teacher=self.teacher,
            status=SessionStatus.SCHEDULED)

        response = self.client.post(
            reverse('teacher:session_start', args=[session.id]))
        self.assertEqual(response.status_code, 302)

        ext = SessionExtension.objects.get(session=session)
        self.assertEqual(ext.status, SessionStatus.ACTIVE)

    def test_end_session(self):
        session = ClassSession.objects.create(
            classroom=self.classroom, topic='تست')
        SessionExtension.objects.create(
            session=session, teacher=self.teacher,
            status=SessionStatus.ACTIVE,
            started_at=timezone.now())

        response = self.client.post(
            reverse('teacher:session_end', args=[session.id]))
        self.assertEqual(response.status_code, 302)

        ext = SessionExtension.objects.get(session=session)
        self.assertEqual(ext.status, SessionStatus.COMPLETED)


class ParticipationTests(TestCase):
    """تست‌های مشارکت"""

    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user(
            username='teacher_part', password='test', role='teacher')
        self.student = User.objects.create_user(
            username='student_part', password='test', role='student')
        self.classroom = Classroom.objects.create(
            name='کلاس', subject='درس',
            teacher=self.teacher, teacher_name='معلم')
        self.classroom.students.add(self.student)
        self.session = ClassSession.objects.create(
            classroom=self.classroom, topic='تست')
        self.client.force_login(self.teacher)

    def test_record_participation(self):
        response = self.client.post(
            reverse('teacher:participation_record', args=[self.session.id]),
            {f'level_{self.student.id}': 'high'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ParticipationRecord.objects.filter(
            student=self.student,
            session=self.session,
            level='high',
        ).exists())