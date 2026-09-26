"""
تست‌های امنیتی جامع — بخش ۵۱ و ۸۵ مستندات
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from national.models import Province, District, School
from dashboard.models import Classroom, ClassSession
from .models import SchoolStaffAssignment, SchoolSettings
from .constants import StaffRole, AssistantType

User = get_user_model()


class CrossSchoolAccessTests(TestCase):
    """Principal A cannot access School B"""

    def setUp(self):
        self.client = Client()
        self.province = Province.objects.create(name='تهران', code='01')
        self.district = District.objects.create(province=self.province, name='منطقه ۱')
        self.school_a = School.objects.create(district=self.district, name='مدرسه الف')
        self.school_b = School.objects.create(district=self.district, name='مدرسه ب')

        self.principal_a = User.objects.create_user(
            username='p_a', password='t', role='principal')
        self.principal_b = User.objects.create_user(
            username='p_b', password='t', role='principal')

        SchoolStaffAssignment.objects.create(
            user=self.principal_a, school=self.school_a,
            staff_role=StaffRole.PRINCIPAL)
        SchoolStaffAssignment.objects.create(
            user=self.principal_b, school=self.school_b,
            staff_role=StaffRole.PRINCIPAL)

        self.classroom_a = Classroom.objects.create(
            name='ک الف', subject='ریاضی', school=self.school_a,
            teacher_name='م')
        self.classroom_b = Classroom.objects.create(
            name='ک ب', subject='فیزیک', school=self.school_b,
            teacher_name='م')

        self.student_a = User.objects.create_user(
            username='s_a', password='t', role='student')
        self.student_b = User.objects.create_user(
            username='s_b', password='t', role='student')
        self.classroom_a.students.add(self.student_a)
        self.classroom_b.students.add(self.student_b)

    def test_principal_a_cannot_view_student_b(self):
        self.client.force_login(self.principal_a)
        r = self.client.get(reverse('school:principal_student_detail',
                                    args=[self.student_b.id]))
        self.assertEqual(r.status_code, 404)

    def test_principal_a_cannot_view_class_b(self):
        self.client.force_login(self.principal_a)
        r = self.client.get(reverse('school:principal_class_detail',
                                    args=[self.classroom_b.id]))
        self.assertEqual(r.status_code, 404)

    def test_principal_b_cannot_view_student_a(self):
        self.client.force_login(self.principal_b)
        r = self.client.get(reverse('school:principal_student_detail',
                                    args=[self.student_a.id]))
        self.assertEqual(r.status_code, 404)


class AssistantPermissionTests(TestCase):
    """Assistant cannot execute Principal-only actions"""

    def setUp(self):
        self.client = Client()
        self.province = Province.objects.create(name='تهران', code='01')
        self.district = District.objects.create(province=self.province, name='منطقه ۱')
        self.school = School.objects.create(district=self.district, name='مدرسه')

        self.principal = User.objects.create_user(
            username='p', password='t', role='principal')
        self.assistant = User.objects.create_user(
            username='a', password='t', role='assistant')
        self.teacher = User.objects.create_user(
            username='t', password='t', role='teacher')
        self.student = User.objects.create_user(
            username='s', password='t', role='student')

        SchoolStaffAssignment.objects.create(
            user=self.principal, school=self.school,
            staff_role=StaffRole.PRINCIPAL)
        SchoolStaffAssignment.objects.create(
            user=self.assistant, school=self.school,
            staff_role=StaffRole.ASSISTANT,
            assistant_type=AssistantType.GENERAL)

    def test_assistant_cannot_access_principal_dashboard(self):
        self.client.force_login(self.assistant)
        r = self.client.get(reverse('school:principal_dashboard'))
        self.assertEqual(r.status_code, 302)

    def test_assistant_cannot_access_principal_settings(self):
        self.client.force_login(self.assistant)
        r = self.client.get(reverse('school:principal_settings'))
        self.assertEqual(r.status_code, 302)

    def test_assistant_cannot_access_principal_audit(self):
        self.client.force_login(self.assistant)
        r = self.client.get(reverse('school:principal_audit_log'))
        self.assertEqual(r.status_code, 302)

    def test_assistant_cannot_manage_assistants(self):
        self.client.force_login(self.assistant)
        r = self.client.get(reverse('school:principal_assistants'))
        self.assertEqual(r.status_code, 302)

    def test_teacher_cannot_access_any_school_panel(self):
        self.client.force_login(self.teacher)
        for url_name in ['school:principal_dashboard', 'school:assistant_dashboard']:
            r = self.client.get(reverse(url_name))
            self.assertEqual(r.status_code, 302, f'Failed for {url_name}')

    def test_student_cannot_access_any_school_panel(self):
        self.client.force_login(self.student)
        for url_name in ['school:principal_dashboard', 'school:assistant_dashboard']:
            r = self.client.get(reverse(url_name))
            self.assertEqual(r.status_code, 302, f'Failed for {url_name}')


class MultiAssistantTests(TestCase):
    """هر مدرسه می‌تواند ۰..N معاون داشته باشد"""

    def setUp(self):
        self.province = Province.objects.create(name='تهران', code='01')
        self.district = District.objects.create(province=self.province, name='منطقه ۱')
        self.school = School.objects.create(district=self.district, name='مدرسه')

    def test_zero_assistants(self):
        count = SchoolStaffAssignment.objects.filter(
            school=self.school, staff_role=StaffRole.ASSISTANT).count()
        self.assertEqual(count, 0)

    def test_one_assistant(self):
        user = User.objects.create_user(username='a1', password='t', role='assistant')
        SchoolStaffAssignment.objects.create(
            user=user, school=self.school,
            staff_role=StaffRole.ASSISTANT,
            assistant_type=AssistantType.GENERAL)
        count = SchoolStaffAssignment.objects.filter(
            school=self.school, staff_role=StaffRole.ASSISTANT).count()
        self.assertEqual(count, 1)

    def test_multiple_assistants(self):
        for i in range(5):
            user = User.objects.create_user(
                username=f'a{i}', password='t', role='assistant')
            SchoolStaffAssignment.objects.create(
                user=user, school=self.school,
                staff_role=StaffRole.ASSISTANT,
                assistant_type=AssistantType.GENERAL)
        count = SchoolStaffAssignment.objects.filter(
            school=self.school, staff_role=StaffRole.ASSISTANT).count()
        self.assertEqual(count, 5)

    def test_user_with_multiple_responsibilities(self):
        user = User.objects.create_user(username='multi', password='t', role='assistant')
        SchoolStaffAssignment.objects.create(
            user=user, school=self.school,
            staff_role=StaffRole.ASSISTANT,
            assistant_type=AssistantType.EXECUTIVE)
        SchoolStaffAssignment.objects.create(
            user=user, school=self.school,
            staff_role=StaffRole.ASSISTANT,
            assistant_type=AssistantType.EDUCATIONAL)

        from .scope import SchoolScope
        scope = SchoolScope(user)
        types = scope.assistant_types
        self.assertIn(AssistantType.EXECUTIVE, types)
        self.assertIn(AssistantType.EDUCATIONAL, types)

    def test_deactivated_assignment_removes_access(self):
        user = User.objects.create_user(username='deact', password='t', role='assistant')
        assignment = SchoolStaffAssignment.objects.create(
            user=user, school=self.school,
            staff_role=StaffRole.ASSISTANT,
            assistant_type=AssistantType.GENERAL)

        assignment.is_active = False
        assignment.save()

        from .scope import SchoolScope
        scope = SchoolScope(user)
        self.assertEqual(len(scope.active_assignments), 0)
        self.assertEqual(len(scope.school_ids), 0)


class BackwardCompatibilityTests(TestCase):
    """قابلیت‌های قبلی نباید خراب شوند"""

    def test_student_dashboard_still_works(self):
        client = Client()
        student = User.objects.create_user(
            username='student_bc', password='t', role='student')
        client.force_login(student)
        r = client.get(reverse('dashboard:home'))
        self.assertEqual(r.status_code, 200)

    def test_teacher_dashboard_still_works(self):
        client = Client()
        teacher = User.objects.create_user(
            username='teacher_bc', password='t', role='teacher')
        client.force_login(teacher)
        r = client.get(reverse('dashboard:home'))
        self.assertEqual(r.status_code, 200)

    def test_existing_assistant_urls_still_work(self):
        """URLهای قدیمی معاون در dashboard نباید شکسته شوند"""
        client = Client()
        assistant = User.objects.create_user(
            username='assistant_bc', password='t', role='assistant')
        client.force_login(assistant)
        # URL قدیمی هنوز باید کار کند
        r = client.get(reverse('dashboard:assistant_dashboard'))
        self.assertIn(r.status_code, [200, 302])