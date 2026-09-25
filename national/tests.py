"""تست‌های پنل مسئول کشوری"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Province, District, School
from dashboard.models import Classroom, ClassSession

User = get_user_model()


class NationalPermissionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.national_admin = User.objects.create_user(
            username='national_admin_test', password='test123', role='country_admin')
        self.teacher = User.objects.create_user(
            username='teacher_test', password='test123', role='teacher')
        self.student = User.objects.create_user(
            username='student_test', password='test123', role='student')
        self.assistant = User.objects.create_user(
            username='assistant_test', password='test123', role='assistant')
        self.principal = User.objects.create_user(
            username='principal_test', password='test123', role='principal')
        self.dashboard_url = reverse('national:dashboard')

    def test_national_admin_allowed(self):
        self.client.force_login(self.national_admin)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

    def test_teacher_denied(self):
        self.client.force_login(self.teacher)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)

    def test_student_denied(self):
        self.client.force_login(self.student)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)

    def test_assistant_denied(self):
        self.client.force_login(self.assistant)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)

    def test_principal_denied(self):
        self.client.force_login(self.principal)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_denied(self):
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)


class NationalScopeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin_scope', password='test123', role='country_admin')
        self.client.force_login(self.admin)
        self.tehran = Province.objects.create(name='تهران', code='01')
        self.isfahan = Province.objects.create(name='اصفهان', code='02')
        self.district_t1 = District.objects.create(province=self.tehran, name='منطقه ۱')
        self.district_i1 = District.objects.create(province=self.isfahan, name='منطقه ۱')
        self.school_t1 = School.objects.create(district=self.district_t1, name='مدرسه تهران ۱')
        self.school_i1 = School.objects.create(district=self.district_i1, name='مدرسه اصفهان ۱')

    def test_national_scope_shows_all(self):
        response = self.client.get(reverse('national:dashboard'), {'scope': 'national'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تهران')
        self.assertContains(response, 'اصفهان')

    def test_province_scope_filters_data(self):
        response = self.client.get(
            reverse('national:dashboard'),
            {'scope': 'province', 'province': self.tehran.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تهران')

    def test_province_detail(self):
        response = self.client.get(
            reverse('national:province_detail', args=[self.tehran.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'استان تهران')

    def test_district_detail(self):
        response = self.client.get(
            reverse('national:district_detail', args=[self.district_t1.id]))
        self.assertEqual(response.status_code, 200)

    def test_school_detail(self):
        response = self.client.get(
            reverse('national:school_detail', args=[self.school_t1.id]))
        self.assertEqual(response.status_code, 200)

    def test_invalid_province_id(self):
        response = self.client.get(
            reverse('national:dashboard'),
            {'scope': 'province', 'province': 99999})
        self.assertEqual(response.status_code, 404)


class NationalAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin_api', password='test123', role='country_admin')

    def test_api_requires_auth(self):
        response = self.client.get(reverse('national:api_dashboard'))
        self.assertEqual(response.status_code, 401)

    def test_api_requires_national_admin(self):
        teacher = User.objects.create_user(
            username='teacher_api', password='test123', role='teacher')
        self.client.force_login(teacher)
        response = self.client.get(reverse('national:api_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_api_returns_json(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('national:api_dashboard'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('overview', data)

    def test_api_provinces(self):
        Province.objects.create(name='تهران')
        self.client.force_login(self.admin)
        response = self.client.get(reverse('national:api_provinces'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['provinces']), 1)


class NationalExportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin_export', password='test123', role='country_admin')
        self.client.force_login(self.admin)
        Province.objects.create(name='تهران', code='01')

    def test_export_provinces_csv(self):
        response = self.client.get(reverse('national:export_provinces_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8-sig')

    def test_export_denied_for_teacher(self):
        teacher = User.objects.create_user(
            username='teacher_export', password='test123', role='teacher')
        self.client.force_login(teacher)
        response = self.client.get(reverse('national:export_provinces_csv'))
        self.assertEqual(response.status_code, 302)


class NationalSecurityTests(TestCase):
    """تست‌های امنیتی: جلوگیری از دسترسی با تغییر پارامتر"""
    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user(
            username='teacher_sec', password='test123', role='teacher')
        self.province = Province.objects.create(name='تهران', code='01')

    def test_teacher_cannot_access_province_detail(self):
        self.client.force_login(self.teacher)
        response = self.client.get(
            reverse('national:province_detail', args=[self.province.id]))
        self.assertEqual(response.status_code, 302)

    def test_student_cannot_access_api(self):
        student = User.objects.create_user(
            username='student_sec', password='test123', role='student')
        self.client.force_login(student)
        response = self.client.get(reverse('national:api_dashboard'))
        self.assertEqual(response.status_code, 403)