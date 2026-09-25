from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from national.models import District

User = get_user_model()


class Command(BaseCommand):
    help = 'ایجاد مسئول منطقه با منطقه اختصاصی'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True)
        parser.add_argument('--password', type=str, required=True)
        parser.add_argument('--district', type=str, required=True,
                            help='نام منطقه (مثلاً: منطقه ۱)')
        parser.add_argument('--province', type=str, required=True,
                            help='نام استان (مثلاً: تهران)')

    def handle(self, *args, **options):
        try:
            district = District.objects.get(
                name=options['district'],
                province__name=options['province'],
            )
        except District.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                f'منطقه "{options["district"]}" در استان "{options["province"]}" یافت نشد.'))
            return

        user, created = User.objects.get_or_create(
            username=options['username'],
            defaults={
                'role': 'district_admin',
                'district': district,
                'first_name': 'مسئول',
                'last_name': f'منطقه {district.name}',
            }
        )
        if created:
            user.set_password(options['password'])
            user.role = 'district_admin'
            user.district = district
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f'✅ مسئول منطقه "{options["username"]}" برای '
                f'منطقه "{district.name}" در استان "{district.province.name}" ایجاد شد.'))
        else:
            self.stdout.write(self.style.WARNING('کاربر از قبل وجود داشت.'))