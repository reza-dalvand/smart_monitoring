from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from unittest.mock import patch

from dashboard.models import (
    Classroom,
    ClassSession,
    AttendanceRequest,
    AttendanceResponse,
)
from face.models import (
    FaceEmbedding,
    FaceVerificationSession,
)
from face.services.face.exceptions import FaceMatchFailedError

User = get_user_model()


def make_frames(count=6, prefix='frame', content_type='image/jpeg'):
    frames = []
    for i in range(count):
        frames.append(
            SimpleUploadedFile(
                name=f'{prefix}_{i}.jpg',
                content=b'x' * 100,
                content_type=content_type,
            )
        )
    return frames


@override_settings(
    FACE_AI_ENABLED=True,
    FACE_AI_MOCK=True,
    FACE_MIN_REFERENCE_IMAGES=3,
    FACE_MAX_ATTEMPTS=3,
    FACE_MIN_FRAMES=5,
    FACE_MAX_FRAMES=15,
    FACE_MAX_FRAME_SIZE_MB=2,
    FACE_MATCH_THRESHOLD=0.45,
    FACE_VERIFICATION_TIMEOUT_SECONDS=60,
)
class VerificationSessionApiTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username='student_session_test',
            password='test123456',
            role='student',
            first_name='دانش‌آموز',
            last_name='تست',
        )
        self.other_student = User.objects.create_user(
            username='other_student_test',
            password='test123456',
            role='student',
            first_name='دانش‌آموز',
            last_name='دیگر',
        )
        self.teacher = User.objects.create_user(
            username='teacher_session_test',
            password='test123456',
            role='teacher',
            first_name='معلم',
            last_name='تست',
        )

        self.classroom = Classroom.objects.create(
            name='کلاس تست نشست',
            subject='درس تست نشست',
            teacher=self.teacher,
            teacher_name='معلم تست',
        )
        self.classroom.students.add(self.student)

        self.session = ClassSession.objects.create(
            classroom=self.classroom,
            topic='جلسه تست نشست',
        )

        self.attendance_request = AttendanceRequest.objects.create(
            teacher=self.teacher,
            classroom=self.classroom,
            session=self.session,
            request_type='face_only',
            status='active',
            face_time_seconds=3600,
        )

        for i in range(3):
            FaceEmbedding.objects.create(
                student=self.student,
                embedding=b'0' * 2048,
                model_name='mock',
                model_version='test',
                embedding_dimension=512,
                source_image=f'test-{i}',
                is_active=True,
            )

        self.client.force_login(self.student)
        self.start_url = reverse(
            'face:api_verification_start',
            args=[self.attendance_request.id]
        )

    def create_active_session(self):
        response = self.client.post(self.start_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        return data

    def complete_url_for(self, session_id):
        return reverse('face:api_verification_complete', args=[session_id])

    def test_start_valid_session(self):
        response = self.client.post(self.start_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('session_id', data)
        self.assertIn('deadline_at', data)
        self.assertEqual(data['challenge'], ['TURN_LEFT', 'TURN_RIGHT', 'BLINK'])

    def test_start_invalid_student_not_in_class(self):
        self.client.force_login(self.other_student)
        response = self.client.post(self.start_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'UNAUTHORIZED')

    def test_start_inactive_attendance(self):
        self.attendance_request.status = 'finished'
        self.attendance_request.save()

        response = self.client.post(self.start_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'ATTENDANCE_NOT_ACTIVE')

    def test_start_expired_attendance(self):
        self.attendance_request.face_deadline_at = timezone.now() - timedelta(seconds=10)
        self.attendance_request.save()

        response = self.client.post(self.start_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'FACE_DEADLINE_EXPIRED')

    def test_start_without_enrollment(self):
        FaceEmbedding.objects.filter(student=self.student).delete()

        response = self.client.post(self.start_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'ENROLLMENT_REQUIRED')

    def test_start_with_too_many_attempts(self):
        response_obj, _ = AttendanceResponse.objects.get_or_create(
            attendance_request=self.attendance_request,
            student=self.student,
        )
        response_obj.attempts = 3
        response_obj.save()

        response = self.client.post(self.start_url)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()['code'], 'TOO_MANY_ATTEMPTS')

    def test_complete_valid_session_marks_present(self):
        start_data = self.create_active_session()
        complete_url = self.complete_url_for(start_data['session_id'])

        response = self.client.post(complete_url, {'frames': make_frames(6)})
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['status'], 'VERIFIED')

        attendance_response = AttendanceResponse.objects.get(
            attendance_request=self.attendance_request,
            student=self.student,
        )
        self.assertTrue(attendance_response.face_verified)
        self.assertEqual(attendance_response.final_status, 'present')

        session = FaceVerificationSession.objects.get(session_id=start_data['session_id'])
        self.assertEqual(session.status, 'passed')

    def test_complete_wrong_student(self):
        start_data = self.create_active_session()
        complete_url = self.complete_url_for(start_data['session_id'])

        self.client.force_login(self.other_student)
        response = self.client.post(complete_url, {'frames': make_frames(6)})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'VERIFICATION_SESSION_INVALID')

    def test_complete_expired_session(self):
        start_data = self.create_active_session()
        session = FaceVerificationSession.objects.get(session_id=start_data['session_id'])
        session.deadline_at = timezone.now() - timedelta(seconds=1)
        session.save()

        complete_url = self.complete_url_for(start_data['session_id'])
        response = self.client.post(complete_url, {'frames': make_frames(6)})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'VERIFICATION_SESSION_EXPIRED')

    def test_complete_already_completed(self):
        start_data = self.create_active_session()
        complete_url = self.complete_url_for(start_data['session_id'])

        first = self.client.post(complete_url, {'frames': make_frames(6)})
        self.assertEqual(first.status_code, 200)

        second = self.client.post(complete_url, {'frames': make_frames(6)})
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json().get('already_completed'))

    def test_complete_without_frames(self):
        start_data = self.create_active_session()
        complete_url = self.complete_url_for(start_data['session_id'])

        response = self.client.post(complete_url, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'INVALID_IMAGE')

    def test_complete_too_many_frames(self):
        start_data = self.create_active_session()
        complete_url = self.complete_url_for(start_data['session_id'])

        response = self.client.post(complete_url, {'frames': make_frames(16)})
        self.assertEqual(response.status_code, 400)

    def test_complete_invalid_frame(self):
        start_data = self.create_active_session()
        complete_url = self.complete_url_for(start_data['session_id'])

        bad_frame = SimpleUploadedFile(
            name='bad.txt',
            content=b'hello',
            content_type='text/plain',
        )
        frames = make_frames(5) + [bad_frame]

        response = self.client.post(complete_url, {'frames': frames})
        self.assertEqual(response.status_code, 400)

    @override_settings(FACE_AI_MOCK_LIVENESS_PASS=False)
    def test_complete_liveness_failed(self):
        start_data = self.create_active_session()
        complete_url = self.complete_url_for(start_data['session_id'])

        response = self.client.post(complete_url, {'frames': make_frames(6)})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'LIVENESS_FAILED')

        attendance_response = AttendanceResponse.objects.get(
            attendance_request=self.attendance_request,
            student=self.student,
        )
        self.assertFalse(attendance_response.face_verified)
        self.assertEqual(attendance_response.final_status, 'pending')

        session = FaceVerificationSession.objects.get(session_id=start_data['session_id'])
        self.assertEqual(session.status, 'failed')

    @override_settings(FACE_AI_MOCK_SIMILARITY=0.30)
    def test_complete_suspicious_match(self):
        start_data = self.create_active_session()
        complete_url = self.complete_url_for(start_data['session_id'])

        response = self.client.post(complete_url, {'frames': make_frames(6)})
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['status'], 'SUSPICIOUS')

        attendance_response = AttendanceResponse.objects.get(
            attendance_request=self.attendance_request,
            student=self.student,
        )
        self.assertFalse(attendance_response.face_verified)
        self.assertEqual(attendance_response.final_status, 'pending')

        session = FaceVerificationSession.objects.get(session_id=start_data['session_id'])
        self.assertEqual(session.status, 'failed')

    def test_complete_match_failed_exception(self):
        start_data = self.create_active_session()
        complete_url = self.complete_url_for(start_data['session_id'])

        with patch(
            'face.services.face.mock_service.MockFaceRecognitionService.verify_frames',
            side_effect=FaceMatchFailedError()
        ):
            response = self.client.post(complete_url, {'frames': make_frames(6)})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'MATCH_FAILED')

        session = FaceVerificationSession.objects.get(session_id=start_data['session_id'])
        self.assertEqual(session.status, 'failed')