"""ایجاد مدیر مدرسه با انتصاب"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from national.models import School
from school.models import SchoolStaffAssignment, SchoolSettings
from school.constants import StaffRole

User = get_user_model()


class Command(BaseCommand):
    help = 'ایجاد مدیر مدرسه'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True)
        parser.add_argument('--password', type=str, required=True)
        parser.add_argument('--school', type=str, required=True,
                            help='نام مدرسه')

    def handle(self, *args, **options):
        try:
            school = School.objects.get(name=options['school'])
        except School.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                f'مدرسه "{options["school"]}" یافت نشد.'))
            return

        user, created = User.objects.get_or_create(
            username=options['username'],
            defaults={
                'role': 'principal',
                'first_name': 'مدیر',
                'last_name': school.name,
            }
        )
        if created:
            user.set_password(options['password'])
            user.save()

        SchoolStaffAssignment.objects.get_or_create(
            user=user, school=school,
            staff_role=StaffRole.PRINCIPAL)

        SchoolSettings.objects.get_or_create(school=school)

        self.stdout.write(self.style.SUCCESS(
            f'✅ مدیر "{options["username"]}" برای مدرسه '
            f'"{school.name}" ایجاد شد.'))