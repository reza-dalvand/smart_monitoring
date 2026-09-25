"""تست‌های امنیتی و عملکردی پنل مسئول استانی"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from national.models import Province, District, School
from dashboard.models import Classroom

User = get_user_model()


class ProvinceScopeSecurityTests(TestCase):
    """تست‌های امنیتی: جلوگیری از دسترسی بین‌استانی"""

    def setUp(self):
        self.client = Client()

        # دو استان مجزا
        self.tehran = Province.objects.create(name='تهران', code='01')
        self.isfahan = Province.objects.create(name='اصفهان', code='02')

        # مناطق هر استان
        self.tehran_d1 = District.objects.create(province=self.tehran, name='منطقه ۱ تهران')
        self.isfahan_d1 = District.objects.create(province=self.isfahan, name='منطقه ۱ اصفهان')

        # مدارس هر استان
        self.tehran_school = School.objects.create(
            district=self.tehran_d1, name='مدرسه تهران')
        self.isfahan_school = School.objects.create(
            district=self.isfahan_d1, name='مدرسه اصفهان')

        # کاربران
        self.tehran_admin = User.objects.create_user(
            username='tehran_admin', password='test123',
            role='province_admin', province=self.tehran)
        self.isfahan_admin = User.objects.create_user(
            username='isfahan_admin', password='test123',
            role='province_admin', province=self.isfahan)
        self.teacher = User.objects.create_user(
            username='teacher_test', password='test123', role='teacher')
        self.student = User.objects.create_user(
            username='student_test', password='test123', role='student')
        self.national_admin = User.objects.create_user(
            username='national_admin', password='test123', role='country_admin')

    # ── دسترسی مجاز ──

    def test_tehran_admin_can_access_own_dashboard(self):
        self.client.force_login(self.tehran_admin)
        response = self.client.get(reverse('province:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تهران')

    def test_tehran_admin_can_view_own_district(self):
        self.client.force_login(self.tehran_admin)
        response = self.client.get(
            reverse('province:district_detail', args=[self.tehran_d1.id]))
        self.assertEqual(response.status_code, 200)

    def test_tehran_admin_can_view_own_school(self):
        self.client.force_login(self.tehran_admin)
        response = self.client.get(
            reverse('province:school_detail', args=[self.tehran_school.id]))
        self.assertEqual(response.status_code, 200)

    # ── دسترسی غیرمجاز بین‌استانی ──

    def test_tehran_admin_cannot_access_isfahan_district(self):
        """مهم‌ترین تست امنیتی: دسترسی بین‌استانی"""
        self.client.force_login(self.tehran_admin)
        response = self.client.get(
            reverse('province:district_detail', args=[self.isfahan_d1.id]))
        self.assertEqual(response.status_code, 404)

    def test_tehran_admin_cannot_access_isfahan_school(self):
        self.client.force_login(self.tehran_admin)
        response = self.client.get(
            reverse('province:school_detail', args=[self.isfahan_school.id]))
        self.assertEqual(response.status_code, 404)

    def test_tehran_admin_cannot_filter_by_isfahan_district(self):
        """تست Query Parameter جعلی"""
        self.client.force_login(self.tehran_admin)
        response = self.client.get(
            reverse('province:dashboard'),
            {'district': self.isfahan_d1.id})
        self.assertEqual(response.status_code, 404)

    # ── نقش‌های غیرمجاز ──

    def test_teacher_cannot_access_province_dashboard(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('province:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_student_cannot_access_province_dashboard(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('province:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_national_admin_cannot_access_province_dashboard(self):
        """National Admin باید از پنل ملی استفاده کند نه استانی"""
        self.client.force_login(self.national_admin)
        response = self.client.get(reverse('province:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_cannot_access(self):
        response = self.client.get(reverse('province:dashboard'))
        self.assertEqual(response.status_code, 302)

    # ── API Security ──

    def test_api_requires_province_admin(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('province:api_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_api_returns_scoped_data(self):
        self.client.force_login(self.tehran_admin)
        response = self.client.get(reverse('province:api_dashboard'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['province']['name'], 'تهران')

    def test_api_districts_only_own_province(self):
        self.client.force_login(self.tehran_admin)
        response = self.client.get(reverse('province:api_districts'))
        data = response.json()
        district_names = [d['name'] for d in data['districts']]
        self.assertIn('منطقه ۱ تهران', district_names)
        self.assertNotIn('منطقه ۱ اصفهان', district_names)

    # ── بدون استان ──

    def test_province_admin_without_province(self):
        user = User.objects.create_user(
            username='no_province', password='test123',
            role='province_admin', province=None)
        self.client.force_login(user)
        response = self.client.get(reverse('province:dashboard'))
        self.assertEqual(response.status_code, 302)


class ProvinceAnalyticsTests(TestCase):
    """تست صحت داده‌های تحلیلی"""

    def setUp(self):
        self.client = Client()
        self.province = Province.objects.create(name='تهران', code='01')
        self.district = District.objects.create(
            province=self.province, name='منطقه ۱')
        self.admin = User.objects.create_user(
            username='admin', password='test123',
            role='province_admin', province=self.province)
        self.client.force_login(self.admin)

    def test_dashboard_with_no_data(self):
        """حالت بدون داده: باید پیام مناسب نمایش داده شود نه 0%"""
        response = self.client.get(reverse('province:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'داده‌ای')

    def test_export_districts_csv(self):
        response = self.client.get(reverse('province:export_districts_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])

    def test_audit_log_recorded(self):
        from national.models import NationalAuditLog
        self.client.get(reverse('province:dashboard'))
        self.assertTrue(NationalAuditLog.objects.filter(
            user=self.admin, action='view_dashboard').exists())