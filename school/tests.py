"""تست‌های امنیتی و عملکردی سیستم مدیریت مدرسه"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from national.models import Province, District, School
from dashboard.models import Classroom, ClassSession
from .models import SchoolStaffAssignment, FollowUpCase, SchoolSettings
from .constants import StaffRole, AssistantType, CaseStatus

User = get_user_model()


class SchoolScopeSecurityTests(TestCase):
    """تست‌های امنیتی: جلوگیری از دسترسی بین‌مدرسه‌ای"""

    def setUp(self):
        self.client = Client()

        # ساختار سازمانی
        self.province = Province.objects.create(name='تهران', code='01')
        self.district = District.objects.create(
            province=self.province, name='منطقه ۱')

        self.school_a = School.objects.create(
            district=self.district, name='مدرسه الف')
        self.school_b = School.objects.create(
            district=self.district, name='مدرسه ب')

        # کاربران
        self.principal_a = User.objects.create_user(
            username='principal_a', password='test123', role='principal')
        self.principal_b = User.objects.create_user(
            username='principal_b', password='test123', role='principal')

        self.assistant_a = User.objects.create_user(
            username='assistant_a', password='test123', role='assistant')
        self.assistant_b = User.objects.create_user(
            username='assistant_b', password='test123', role='assistant')

        self.teacher = User.objects.create_user(
            username='teacher_test', password='test123', role='teacher')
        self.student = User.objects.create_user(
            username='student_test', password='test123', role='student')

        # انتصابات
        SchoolStaffAssignment.objects.create(
            user=self.principal_a, school=self.school_a,
            staff_role=StaffRole.PRINCIPAL)
        SchoolStaffAssignment.objects.create(
            user=self.principal_b, school=self.school_b,
            staff_role=StaffRole.PRINCIPAL)
        SchoolStaffAssignment.objects.create(
            user=self.assistant_a, school=self.school_a,
            staff_role=StaffRole.ASSISTANT,
            assistant_type=AssistantType.GENERAL)
        SchoolStaffAssignment.objects.create(
            user=self.assistant_b, school=self.school_b,
            staff_role=StaffRole.ASSISTANT,
            assistant_type=AssistantType.EDUCATIONAL)

        # کلاس‌ها
        self.classroom_a = Classroom.objects.create(
            name='کلاس الف', subject='ریاضی',
            school=self.school_a, teacher_name='معلم الف')
        self.classroom_b = Classroom.objects.create(
            name='کلاس ب', subject='فیزیک',
            school=self.school_b, teacher_name='معلم ب')

        self.classroom_a.students.add(self.student)

    # ── دسترسی مجاز ──
    def test_principal_a_can_access_own_dashboard(self):
        self.client.force_login(self.principal_a)
        response = self.client.get(reverse('school:principal_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مدرسه الف')

    def test_principal_a_can_view_own_students(self):
        self.client.force_login(self.principal_a)
        response = self.client.get(reverse('school:principal_students'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'student_test')

    # ── دسترسی غیرمجاز بین‌مدرسه‌ای ──
    def test_principal_a_cannot_access_school_b_student(self):
        """مهم‌ترین تست امنیتی"""
        student_b = User.objects.create_user(
            username='student_b', password='test123', role='student')
        self.classroom_b.students.add(student_b)

        self.client.force_login(self.principal_a)
        response = self.client.get(
            reverse('school:principal_student_detail', args=[student_b.id]))
        self.assertEqual(response.status_code, 404)

    def test_assistant_a_cannot_access_school_b(self):
        self.client.force_login(self.assistant_a)
        response = self.client.get(reverse('school:assistant_dashboard'))
        self.assertEqual(response.status_code, 200)
        # نباید کلاس مدرسه ب را ببیند
        self.assertNotContains(response, 'کلاس ب')

    # ── نقش‌های غیرمجاز ──
    def test_teacher_cannot_access_principal(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('school:principal_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_student_cannot_access_assistant(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('school:assistant_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_assistant_cannot_access_principal_pages(self):
        self.client.force_login(self.assistant_a)
        response = self.client.get(reverse('school:principal_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_assistant_cannot_override_attendance(self):
        """معاون نباید بتواند حضور را تغییر دهد"""
        self.client.force_login(self.assistant_a)
        # URL override فقط برای مدیر است
        response = self.client.get(
            reverse('school:principal_attendance'))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_cannot_access(self):
        response = self.client.get(reverse('school:principal_dashboard'))
        self.assertEqual(response.status_code, 302)

    # ── بدون انتصاب ──
    def test_principal_without_assignment(self):
        user = User.objects.create_user(
            username='no_school', password='test123', role='principal')
        self.client.force_login(user)
        response = self.client.get(reverse('school:principal_dashboard'))
        self.assertEqual(response.status_code, 302)

    # ── چند معاون ──
    def test_multiple_assistants_per_school(self):
        """هر مدرسه می‌تواند چند معاون داشته باشد"""
        assistant_2 = User.objects.create_user(
            username='assistant_2', password='test123', role='assistant')
        SchoolStaffAssignment.objects.create(
            user=assistant_2, school=self.school_a,
            staff_role=StaffRole.ASSISTANT,
            assistant_type=AssistantType.EDUCATIONAL)

        assignments = SchoolStaffAssignment.objects.filter(
            school=self.school_a, staff_role=StaffRole.ASSISTANT)
        self.assertEqual(assignments.count(), 2)

    def test_assistant_with_multiple_responsibilities(self):
        """یک کاربر می‌تواند چند مسئولیت داشته باشد"""
        SchoolStaffAssignment.objects.create(
            user=self.assistant_a, school=self.school_a,
            staff_role=StaffRole.ASSISTANT,
            assistant_type=AssistantType.EDUCATIONAL)

        assignments = SchoolStaffAssignment.objects.filter(
            user=self.assistant_a, school=self.school_a,
            staff_role=StaffRole.ASSISTANT)
        self.assertEqual(assignments.count(), 2)


class FollowUpCaseTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.province = Province.objects.create(name='تهران', code='01')
        self.district = District.objects.create(
            province=self.province, name='منطقه ۱')
        self.school = School.objects.create(
            district=self.district, name='مدرسه تست')

        self.principal = User.objects.create_user(
            username='principal', password='test123', role='principal')
        SchoolStaffAssignment.objects.create(
            user=self.principal, school=self.school,
            staff_role=StaffRole.PRINCIPAL)

        self.client.force_login(self.principal)

    def test_create_followup_case(self):
        response = self.client.post(
            reverse('school:principal_followup_create'),
            {'title': 'تست پرونده', 'priority': 'HIGH',
             'category': 'ABSENCE'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(FollowUpCase.objects.filter(
            title='تست پرونده').exists())

    def test_resolve_followup_case(self):
        case = FollowUpCase.objects.create(
            school=self.school,
            created_by=self.principal,
            title='تست',
            status=CaseStatus.OPEN,
        )
        response = self.client.post(
            reverse('school:principal_followup_resolve',
                    args=[case.case_number]),
            {'resolution_note': 'حل شد'})
        case.refresh_from_db()
        self.assertEqual(case.status, CaseStatus.RESOLVED)