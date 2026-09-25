"""ایجاد داده‌های نمونه برای پنل مسئول کشوری"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from national.models import Province, District, School
from dashboard.models import Classroom

User = get_user_model()

PROVINCES_DATA = [
    ('تهران', '01'), ('اصفهان', '02'), ('فارس', '03'),
    ('خوزستان', '04'), ('آذربایجان شرقی', '05'), ('آذربایجان غربی', '06'),
    ('خراسان رضوی', '07'), ('البرز', '08'), ('مازندران', '09'),
    ('گیلان', '10'), ('کرمان', '11'), ('سیستان و بلوچستان', '12'),
]


class Command(BaseCommand):
    help = 'ایجاد داده‌های نمونه ساختار سازمانی (استان، منطقه، مدرسه)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🔄 در حال ایجاد ساختار سازمانی...'))

        admin, created = User.objects.get_or_create(
            username='national_admin',
            defaults={'role': 'country_admin', 'first_name': 'مسئول',
                      'last_name': 'کشوری', 'email': 'national@example.com'})
        if created:
            admin.set_password('12345678')
            admin.save()
            self.stdout.write(self.style.SUCCESS(
                '✅ کاربر national_admin ایجاد شد (رمز: 12345678)'))

        for name, code in PROVINCES_DATA:
            province, _ = Province.objects.get_or_create(name=name, defaults={'code': code})
            for i in range(1, 3):
                district, _ = District.objects.get_or_create(
                    province=province, name=f'منطقه {i}',
                    defaults={'code': f'{code}{i:02d}'})
                for j in range(1, 3):
                    School.objects.get_or_create(
                        district=district,
                        name=f'مدرسه نمونه {j} - {district.name}',
                        defaults={'school_type': 'technical'})

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ ساختار سازمانی ایجاد شد:\n'
            f'   استان‌ها: {Province.objects.count()}\n'
            f'   مناطق: {District.objects.count()}\n'
            f'   مدارس: {School.objects.count()}'))

        classrooms = Classroom.objects.filter(school__isnull=True)
        schools = list(School.objects.all())
        if schools and classrooms.exists():
            import random
            for classroom in classrooms:
                classroom.school = random.choice(schools)
                classroom.save(update_fields=['school'])
            self.stdout.write(self.style.SUCCESS(
                f'✅ {classrooms.count()} کلاس به مدارس متصل شد.'))