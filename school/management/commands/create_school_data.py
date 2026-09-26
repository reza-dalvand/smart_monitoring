"""ایجاد داده‌های نمونه برای پنل مدرسه"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from national.models import Province, District, School
from dashboard.models import Classroom
from school.models import SchoolStaffAssignment, SchoolSettings
from school.constants import StaffRole, AssistantType

User = get_user_model()


class Command(BaseCommand):
    help = 'ایجاد داده‌های نمونه پنل مدرسه'

    def handle(self, *args, **options):
        # ساختار سازمانی
        province, _ = Province.objects.get_or_create(
            name='تهران', defaults={'code': '01'})
        district, _ = District.objects.get_or_create(
            province=province, name='منطقه ۱',
            defaults={'code': '0101'})
        school, _ = School.objects.get_or_create(
            district=district, name='دبیرستان شهید بهشتی',
            defaults={'school_type': 'public'})

        # مدیر
        principal, created = User.objects.get_or_create(
            username='principal_school',
            defaults={'role': 'principal', 'first_name': 'رضا',
                      'last_name': 'مدیری'})
        if created:
            principal.set_password('12345678')
            principal.save()

        SchoolStaffAssignment.objects.get_or_create(
            user=principal, school=school,
            staff_role=StaffRole.PRINCIPAL)

        # معاونان
        assistants_data = [
            ('assistant_exec', 'علی', 'محمدی', AssistantType.EXECUTIVE),
            ('assistant_edu', 'مریم', 'کریمی', AssistantType.EDUCATIONAL),
            ('assistant_gen', 'حسین', 'رضایی', AssistantType.GENERAL),
        ]
        for username, first, last, atype in assistants_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'role': 'assistant', 'first_name': first,
                          'last_name': last})
            if created:
                user.set_password('12345678')
                user.save()

            SchoolStaffAssignment.objects.get_or_create(
                user=user, school=school,
                staff_role=StaffRole.ASSISTANT,
                assistant_type=atype)

        # تنظیمات مدرسه
        SchoolSettings.objects.get_or_create(school=school)

        # اتصال کلاس‌های بدون مدرسه
        classrooms = Classroom.objects.filter(school__isnull=True)
        for c in classrooms[:5]:
            c.school = school
            c.save(update_fields=['school'])

        self.stdout.write(self.style.SUCCESS(
            f'✅ داده‌های نمونه مدرسه ایجاد شد.\n'
            f'   مدرسه: {school.name}\n'
            f'   مدیر: principal_school (رمز: 12345678)\n'
            f'   معاونان: assistant_exec, assistant_edu, assistant_gen\n'
            f'   کلاس‌ها: {Classroom.objects.filter(school=school).count()}'
        ))