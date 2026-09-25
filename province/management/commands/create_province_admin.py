from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from national.models import Province

User = get_user_model()


class Command(BaseCommand):
    help = 'ایجاد مسئول استانی با استان اختصاصی'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True)
        parser.add_argument('--password', type=str, required=True)
        parser.add_argument('--province', type=str, required=True,
                            help='نام استان (مثلاً: تهران)')

    def handle(self, *args, **options):
        try:
            province = Province.objects.get(name=options['province'])
        except Province.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                f'استان "{options["province"]}" یافت نشد.'))
            return

        user, created = User.objects.get_or_create(
            username=options['username'],
            defaults={
                'role': 'province_admin',
                'province': province,
                'first_name': 'مسئول',
                'last_name': f'استان {province.name}',
            }
        )
        if created:
            user.set_password(options['password'])
        user.role = 'province_admin'
        user.province = province
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f'✅ مسئول استانی "{options["username"]}" برای استان '
            f'"{province.name}" ایجاد شد.'))