from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from face.models import FaceVerificationSession
from dashboard.models import AttendanceResponse, AttendanceRequest


class Command(BaseCommand):
    help = 'منقضی کردن نشست‌های احراز هویت و ثبت غیبت برای درخواست‌های منقضی‌شده'

    def handle(self, *args, **options):
        now = timezone.now()
        expired_sessions = 0
        marked_absent = 0

        with transaction.atomic():
            expired_sessions = FaceVerificationSession.objects.filter(
                status__in=['pending', 'in_progress'],
                deadline_at__lt=now,
            ).update(
                status='expired',
                completed_at=now,
                failure_code='EXPIRED',
            )

            expired_requests = AttendanceRequest.objects.filter(
                status='active',
                request_type__in=['face_only', 'face_and_question'],
                face_deadline_at__lt=now,
            )

            pending_responses = AttendanceResponse.objects.filter(
                attendance_request__in=expired_requests,
                auto_status='pending',
            ).select_related('attendance_request')

            for response in pending_responses:
                response.mark_no_response()
                marked_absent += 1

        self.stdout.write(self.style.SUCCESS(
            f'Expired sessions: {expired_sessions}, marked no-response: {marked_absent}'
        ))