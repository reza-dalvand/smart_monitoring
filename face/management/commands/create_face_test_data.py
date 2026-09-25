"""
کامند برای ساخت داده تست احراز هویت چهره

این کامند:
- برای اولین دانش‌آموز موجود، امبدینگ‌های مرجع ماک می‌سازد.
- یک AttendanceRequest فعال برای تست اسکن چهره ایجاد می‌کند.

برای تست بدون مدل واقعی:
در settings مقدار FACE_AI_MOCK = True قرار دهید.
"""
from django.core.management.base import BaseCommand
from django.conf import settings

from accounts.models import User
from dashboard.models import Classroom, ClassSession, AttendanceRequest
from face.models import FaceProfile, FaceEmbedding

import numpy as np


class Command(BaseCommand):
    help = 'ساخت داده تست برای احراز هویت چهره در حضور و غیاب'

    def handle(self, *args, **options):
        student = User.objects.filter(role='student').first()

        if not student:
            self.stdout.write(self.style.ERROR('هیچ دانش‌آموزی پیدا نشد. ابتدا create_sample_data را اجرا کنید.'))
            return

        classroom = Classroom.objects.filter(students=student).first()

        if not classroom:
            classroom = Classroom.objects.first()

        if not classroom:
            self.stdout.write(self.style.ERROR('هیچ کلاسی پیدا نشد. ابتدا create_sample_data را اجرا کنید.'))
            return

        if not classroom.students.filter(pk=student.pk).exists():
            classroom.students.add(student)

        teacher = classroom.teacher

        if not teacher:
            teacher = User.objects.filter(role='teacher').first()

        if not teacher:
            teacher = User.objects.create_user(
                username='teacher_face_test',
                password='12345678',
                role='teacher',
                first_name='معلم',
                last_name='تست چهره'
            )

        session = ClassSession.objects.create(
            classroom=classroom,
            topic='جلسه تست احراز هویت چهره'
        )

        attendance_request = AttendanceRequest.objects.create(
            teacher=teacher,
            classroom=classroom,
            session=session,
            request_type='face_only',
            status='active',
            face_time_seconds=3600
        )

        min_reference_images = getattr(settings, 'FACE_MIN_REFERENCE_IMAGES', 3)
        existing_embeddings = FaceEmbedding.objects.filter(
            student=student,
            is_active=True
        ).count()

        if existing_embeddings < min_reference_images:
            for i in range(min_reference_images):
                embedding = np.random.rand(512).astype(np.float32).tobytes()

                FaceEmbedding.objects.create(
                    student=student,
                    embedding=embedding,
                    model_name='mock',
                    model_version='test',
                    embedding_dimension=512,
                    source_image=f'mock-reference-{i + 1}',
                    is_active=True
                )

        face_profile, _ = FaceProfile.objects.get_or_create(student=student)
        face_profile.update_enrollment_status()

        self.stdout.write(self.style.SUCCESS('داده تست احراز هویت چهره با موفقیت ساخته شد.'))
        self.stdout.write(self.style.WARNING(f'Attendance Request ID: {attendance_request.id}'))
        self.stdout.write(self.style.WARNING('اگر بدون مدل واقعی تست می‌کنید، در settings مقدار FACE_AI_MOCK = True را قرار دهید.'))