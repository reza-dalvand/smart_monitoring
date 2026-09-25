"""تست‌های امنیتی و عملکردی پنل مسئول منطقه"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from national.models import Province, District, School
from dashboard.models import Classroom

User = get_user_model()


class DistrictScopeSecurityTests(TestCase):
    """تست‌های امنیتی: جلوگیری از دسترسی بین‌منطقه‌ای"""

    def setUp(self):
        self.client = Client()
        self.tehran = Province.objects.create(name='تهران', code='01')
        self.district_1 = District.objects.create(
            province=self.tehran, name='منطقه ۱')
        self.district_2 = District.objects.create(
            province=self.tehran, name='منطقه ۲')

        self.school_d1 = School.objects.create(
            district=self.district_1, name='مدرسه منطقه ۱')
        self.school_d2 = School.objects.create(
            district=self.district_2, name='مدرسه منطقه ۲')

        self.admin_d1 = User.objects.create_user(
            username='admin_d1', password='test123',
            role='district_admin', district=self.district_1)
        self.admin_d2 = User.objects.create_user(
            username='admin_d2', password='test123',
            role='district_admin', district=self.district_2)
        self.teacher = User.objects.create_user(
            username='teacher_test', password='test123', role='teacher')
        self.student = User.objects.create_user(
            username='student_test', password='test123', role='student')

    # ── دسترسی مجاز ──
    def test_admin_can_access_own_dashboard(self):
        self.client.force_login(self.admin_d1)
        response = self.client.get(reverse('district:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'منطقه ۱')

    def test_admin_can_view_own_school(self):
        self.client.force_login(self.admin_d1)
        response = self.client.get(
            reverse('district:school_detail', args=[self.school_d1.id]))
        self.assertEqual(response.status_code, 200)

    # ── دسترسی غیرمجاز بین‌منطقه‌ای ──
    def test_admin_cannot_access_other_district_school(self):
        """مهم‌ترین تست امنیتی"""
        self.client.force_login(self.admin_d1)
        response = self.client.get(
            reverse('district:school_detail', args=[self.school_d2.id]))
        self.assertEqual(response.status_code, 404)

    # ── نقش‌های غیرمجاز ──
    def test_teacher_cannot_access(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('district:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_student_cannot_access(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('district:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_cannot_access(self):
        response = self.client.get(reverse('district:dashboard'))
        self.assertEqual(response.status_code, 302)

    # ── API Security ──
    def test_api_requires_district_admin(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('district:api_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_api_returns_scoped_data(self):
        self.client.force_login(self.admin_d1)
        response = self.client.get(reverse('district:api_dashboard'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['district']['name'], 'منطقه ۱')

    def test_api_schools_only_own_district(self):
        self.client.force_login(self.admin_d1)
        response = self.client.get(reverse('district:api_schools'))
        data = response.json()
        school_names = [s['name'] for s in data['schools']]
        self.assertIn('مدرسه منطقه ۱', school_names)
        self.assertNotIn('مدرسه منطقه ۲', school_names)

    # ── بدون منطقه ──
    def test_admin_without_district(self):
        user = User.objects.create_user(
            username='no_district', password='test123',
            role='district_admin', district=None)
        self.client.force_login(user)
        response = self.client.get(reverse('district:dashboard'))
        self.assertEqual(response.status_code, 302)

    # ── Export Scope ──
    def test_export_scoped(self):
        self.client.force_login(self.admin_d1)
        response = self.client.get(reverse('district:export_schools_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        content = response.content.decode('utf-8-sig')
        self.assertIn('مدرسه منطقه ۱', content)
        self.assertNotIn('مدرسه منطقه ۲', content)


class DistrictAnalyticsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.province = Province.objects.create(name='تهران', code='01')
        self.district = District.objects.create(
            province=self.province, name='منطقه ۱')
        self.admin = User.objects.create_user(
            username='admin', password='test123',
            role='district_admin', district=self.district)
        self.client.force_login(self.admin)

    def test_dashboard_with_no_data(self):
        response = self.client.get(reverse('district:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_audit_log_recorded(self):
        from national.models import NationalAuditLog
        self.client.get(reverse('district:dashboard'))
        self.assertTrue(NationalAuditLog.objects.filter(
            user=self.admin, action='view_dashboard').exists())