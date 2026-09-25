from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from unittest.mock import Mock

from dashboard.models import (
    Classroom,
    ClassSession,
    AttendanceRequest,
    AttendanceResponse,
)

from face.models import FaceEmbedding
from face.services.face.attendance_service import AttendanceFaceVerificationService
from face.services.face.exceptions import (
    LivenessFailedError,
    AttendanceNotActiveError,
    AttendanceNotForStudentError,
    EnrollmentRequiredError,
    TooManyAttemptsError,
)
from face.constants import MatchDecision, FaceStatus

User = get_user_model()


def make_frames(count=6):
    frames = []
    for i in range(count):
        frames.append(
            SimpleUploadedFile(
                name=f'frame_{i}.jpg',
                content=b'x' * 100,
                content_type='image/jpeg'
            )
        )
    return frames


@override_settings(
    FACE_AI_ENABLED=True,
    FACE_MIN_REFERENCE_IMAGES=3,
    FACE_MAX_ATTEMPTS=3,
    FACE_MIN_FRAMES=5,
    FACE_MAX_FRAMES=15,
    FACE_MAX_FRAME_SIZE_MB=2,
    FACE_MATCH_THRESHOLD=0.45
)
class AttendanceFaceVerificationTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username='student_test',
            password='test123456',
            role='student',
            first_name='دانش‌آموز',
            last_name='تست'
        )

        self.teacher = User.objects.create_user(
            username='teacher_test',
            password='test123456',
            role='teacher',
            first_name='معلم',
            last_name='تست'
        )

        self.classroom = Classroom.objects.create(
            name='کلاس تست',
            subject='درس تست',
            teacher=self.teacher,
            teacher_name='معلم تست'
        )
        self.classroom.students.add(self.student)

        self.session = ClassSession.objects.create(
            classroom=self.classroom,
            topic='جلسه تست'
        )

        self.attendance_request = AttendanceRequest.objects.create(
            teacher=self.teacher,
            classroom=self.classroom,
            session=self.session,
            request_type='face_only',
            status='active',
            face_time_seconds=3600
        )

        for i in range(3):
            FaceEmbedding.objects.create(
                student=self.student,
                embedding=b'0' * 2048,
                model_name='mock',
                model_version='test',
                embedding_dimension=512,
                source_image=f'test-{i}',
                is_active=True
            )

    def _get_service_with_result(self, result):
        face_service = Mock()
        face_service.verify_frames.return_value = result
        return AttendanceFaceVerificationService(face_service=face_service)

    def test_success_verified(self):
        result = {
            'decision': MatchDecision.MATCH,
            'face_status': FaceStatus.VERIFIED,
            'similarity_score': 0.93,
            'valid_frames': 6,
            'total_frames': 6,
            'liveness_result': {
                'is_live': True,
                'confidence': 1.0,
                'method': 'mock'
            }
        }

        service = self._get_service_with_result(result)

        output = service.verify_attendance(
            student=self.student,
            attendance_request=self.attendance_request,
            frames=make_frames(6)
        )

        response = AttendanceResponse.objects.get(
            attendance_request=self.attendance_request,
            student=self.student
        )

        self.assertTrue(output['success'])
        self.assertEqual(output['status'], FaceStatus.VERIFIED)
        self.assertTrue(response.face_verified)
        self.assertEqual(response.final_status, 'present')
        self.assertEqual(response.face_status, FaceStatus.VERIFIED)
        self.assertEqual(response.attempts, 1)

    def test_suspicious(self):
        result = {
            'decision': MatchDecision.SUSPICIOUS,
            'face_status': FaceStatus.SUSPICIOUS,
            'similarity_score': 0.31,
            'valid_frames': 6,
            'total_frames': 6,
            'liveness_result': {
                'is_live': True,
                'confidence': 1.0,
                'method': 'mock'
            }
        }

        service = self._get_service_with_result(result)

        output = service.verify_attendance(
            student=self.student,
            attendance_request=self.attendance_request,
            frames=make_frames(6)
        )

        response = AttendanceResponse.objects.get(
            attendance_request=self.attendance_request,
            student=self.student
        )

        self.assertTrue(output['success'])
        self.assertEqual(output['status'], FaceStatus.SUSPICIOUS)
        self.assertFalse(response.face_verified)
        self.assertEqual(response.final_status, 'pending')
        self.assertEqual(response.auto_status, 'suspicious')

    def test_no_enrollment(self):
        FaceEmbedding.objects.filter(student=self.student).delete()

        service = AttendanceFaceVerificationService(face_service=Mock())

        with self.assertRaises(EnrollmentRequiredError):
            service.verify_attendance(
                student=self.student,
                attendance_request=self.attendance_request,
                frames=make_frames(6)
            )

    def test_inactive_request(self):
        self.attendance_request.status = 'finished'
        self.attendance_request.save()

        service = AttendanceFaceVerificationService(face_service=Mock())

        with self.assertRaises(AttendanceNotActiveError):
            service.verify_attendance(
                student=self.student,
                attendance_request=self.attendance_request,
                frames=make_frames(6)
            )

    def test_unauthorized_student(self):
        other_student = User.objects.create_user(
            username='student_other',
            password='test123456',
            role='student'
        )

        service = AttendanceFaceVerificationService(face_service=Mock())

        with self.assertRaises(AttendanceNotForStudentError):
            service.verify_attendance(
                student=other_student,
                attendance_request=self.attendance_request,
                frames=make_frames(6)
            )

    def test_too_many_attempts(self):
        response = AttendanceResponse.objects.get(
            attendance_request=self.attendance_request,
            student=self.student
        )
        response.attempts = 3
        response.save()

        service = AttendanceFaceVerificationService(face_service=Mock())

        with self.assertRaises(TooManyAttemptsError):
            service.verify_attendance(
                student=self.student,
                attendance_request=self.attendance_request,
                frames=make_frames(6)
            )

    def test_liveness_failed(self):
        face_service = Mock()
        face_service.verify_frames.side_effect = LivenessFailedError()

        service = AttendanceFaceVerificationService(face_service=face_service)

        with self.assertRaises(LivenessFailedError):
            service.verify_attendance(
                student=self.student,
                attendance_request=self.attendance_request,
                frames=make_frames(6)
            )

        response = AttendanceResponse.objects.get(
            attendance_request=self.attendance_request,
            student=self.student
        )

        self.assertEqual(response.attempts, 1)
        self.assertEqual(response.face_status, FaceStatus.FAILED)
        self.assertEqual(response.failure_reason, 'LIVENESS_FAILED')