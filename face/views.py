"""ویوهای تشخیص چهره"""
import logging
from django.templatetags.static import static
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
import json
from datetime import timedelta
from django.db import connection, transaction
from django.urls import reverse
from core import settings
from face.models import FaceEmbedding, FaceVerificationSession
from face.constants import VerificationSessionStatus
from dashboard.models import AttendanceRequest, AttendanceResponse
from .models import FaceProfile, FaceVerificationLog
from .services.face.service import FaceRecognitionService
from .services.face.attendance_service import AttendanceFaceVerificationService
from .services.face.exceptions import (
    AttendanceNotActiveError,
    AttendanceNotForStudentError,
    EnrollmentError,
    EnrollmentRequiredError,
    FaceDeadlineExpiredError,
    ModelNotAvailableError,
    FaceServiceError,
    TooManyAttemptsError,
)

logger = logging.getLogger(__name__)


def _for_update(qs):
    try:
        if connection.features.has_select_for_update:
            return qs.select_for_update()
    except Exception:
        pass
    return qs


def _face_verification_config():
    return {
        'guide': {
            'minX': getattr(settings, 'FACE_GUIDE_MIN_X', 0.20),
            'maxX': getattr(settings, 'FACE_GUIDE_MAX_X', 0.80),
            'minY': getattr(settings, 'FACE_GUIDE_MIN_Y', 0.12),
            'maxY': getattr(settings, 'FACE_GUIDE_MAX_Y', 0.88),
            'minWidth': getattr(settings, 'FACE_GUIDE_MIN_WIDTH', 0.22),
            'maxWidth': getattr(settings, 'FACE_GUIDE_MAX_WIDTH', 0.70),
            'minHeight': getattr(settings, 'FACE_GUIDE_MIN_HEIGHT', 0.22),
            'maxHeight': getattr(settings, 'FACE_GUIDE_MAX_HEIGHT', 0.85),
        },
        'stableDurationMs': getattr(settings, 'FACE_STABLE_DURATION_MS', 700),
        'inferenceIntervalMs': int(1000 / max(1, getattr(settings, 'FACE_INFERENCE_FPS', 15))),
        'head': {
            'yawMinDeg': getattr(settings, 'HEAD_YAW_TURN_MIN_DEG', 18),
            'holdMs': getattr(settings, 'HEAD_TURN_HOLD_MS', 250),
        },
        'blink': {
            'closureThreshold': getattr(settings, 'BLINK_CLOSURE_THRESHOLD', 0.55),
            'openThreshold': getattr(settings, 'BLINK_OPEN_THRESHOLD', 0.25),
            'minDurationMs': getattr(settings, 'BLINK_MIN_DURATION_MS', 60),
            'maxDurationMs': getattr(settings, 'BLINK_MAX_DURATION_MS', 900),
        },
        'evidence': {
            'minFrames': min(
                getattr(settings, 'FACE_EVIDENCE_MIN_FRAMES', 5),
                getattr(settings, 'FACE_MAX_FRAMES', 15),
            ),
            'maxFrames': min(
                getattr(settings, 'FACE_EVIDENCE_MAX_FRAMES', 12),
                getattr(settings, 'FACE_MAX_FRAMES', 15),
            ),
            'captureIntervalMs': getattr(settings, 'FACE_EVIDENCE_CAPTURE_INTERVAL_MS', 130),
        },
    }


def _sanitize_challenge_result(raw):
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    allowed = {
        'TURN_LEFT',
        'TURN_RIGHT',
        'BLINK',
        'left',
        'right',
        'blink',
    }
    return {
        key: bool(value)
        for key, value in data.items()
        if key in allowed
    }

@login_required
def enrollment_page(request):
    if request.user.role != 'student':
        messages.error(request, 'دسترسی غیرمجاز.')
        return redirect('dashboard:home')

    face_profile, _ = FaceProfile.objects.get_or_create(student=request.user)

    context = {
        'face_profile': face_profile,
        'title': 'ثبت چهره',
    }
    return render(request, 'face/enrollment.html', context)


@login_required
def verify_page(request, request_id):
    if request.user.role != 'student':
        messages.error(request, 'دسترسی غیرمجاز.')
        return redirect('dashboard:home')

    attendance_request = get_object_or_404(
        AttendanceRequest,
        id=request_id,
    )

    if request.user not in attendance_request.classroom.students.all():
        messages.error(request, 'شما در این کلاس ثبت‌نام نشده‌اید.')
        return redirect('dashboard:home')

    response = AttendanceResponse.objects.filter(
        attendance_request=attendance_request,
        student=request.user,
    ).first()

    already_verified = bool(
        response and response.face_verified and response.final_status == 'present'
    )

    context = {
        'attendance_request': attendance_request,
        'response': response,
        'already_verified': already_verified,
        'title': 'احراز هویت چهره',
        'start_url': reverse('face:api_verification_start', args=[attendance_request.id]),
        'complete_url_base': reverse(
            'face:api_verification_complete',
            args=['00000000-0000-0000-0000-000000000000']
        ),
        'mediapipe_module_url': static(getattr(settings, 'FACE_MEDIAPIPE_MODULE_URL', '')),
        'mediapipe_wasm_base': static(getattr(settings, 'FACE_MEDIAPIPE_WASM_BASE', '')),
        'mediapipe_model_url': static(getattr(settings, 'FACE_MEDIAPIPE_MODEL', '')),
    }
    return render(request, 'face/verify.html', context)


@login_required
@require_POST
def api_enrollment(request):
    if request.user.role != 'student':
        return JsonResponse({
            'success': False,
            'code': 'FORBIDDEN',
            'message': 'دسترسی غیرمجاز.'
        }, status=403)

    images = request.FILES.getlist('images')
    replace_existing = request.POST.get('replace_existing', 'false').lower() == 'true'

    if not images:
        return JsonResponse({
            'success': False,
            'code': 'MISSING_IMAGES',
            'message': 'تصویری ارسال نشده است.'
        }, status=400)

    try:
        service = FaceRecognitionService.get_instance()
        result = service.enroll_student(
            student_id=request.user.id,
            images=images,
            replace_existing=replace_existing
        )

        face_profile, _ = FaceProfile.objects.get_or_create(student=request.user)
        face_profile.update_enrollment_status()

        return JsonResponse({
            'success': True,
            'message': result['message'],
            'processed': result['processed'],
            'failed': result['failed'],
            'errors': result['errors'],
            'enrollment_status': face_profile.enrollment_status,
        })

    except EnrollmentError as e:
        return JsonResponse({
            'success': False,
            'code': e.code,
            'message': e.message
        }, status=400)

    except ModelNotAvailableError as e:
        return JsonResponse({
            'success': False,
            'code': e.code,
            'message': e.message
        }, status=503)

    except Exception as e:
        logger.error('Enrollment error: %s', e)
        return JsonResponse({
            'success': False,
            'code': 'ENROLLMENT_ERROR',
            'message': 'خطا در ثبت چهره.'
        }, status=500)


@login_required
@require_POST
def api_enrollment_validate(request):
    if request.user.role != 'student':
        return JsonResponse({
            'success': False,
            'code': 'FORBIDDEN',
            'message': 'دسترسی غیرمجاز.'
        }, status=403)

    image = request.FILES.get('image')
    if not image:
        return JsonResponse({
            'success': False,
            'code': 'MISSING_IMAGE',
            'message': 'تصویری ارسال نشده است.'
        }, status=400)

    try:
        service = FaceRecognitionService.get_instance()
        result = service.validate_enrollment_image(image)

        return JsonResponse({
            'success': result['valid'],
            'valid': result['valid'],
            'status': result['status'],
            'message': result['message'],
        })

    except Exception as e:
        logger.error('Image validation error: %s', e)
        return JsonResponse({
            'success': False,
            'code': 'VALIDATION_ERROR',
            'message': 'خطا در اعتبارسنجی.'
        }, status=500)


@login_required
@require_POST
def api_verify(request, attendance_request_id):
    """
    API اصلی احراز هویت چهره برای حضور و غیاب

    هویت دانش‌آموز فقط از request.user گرفته می‌شود.
    هیچ student_id از سمت کلاینت پذیرفته نمی‌شود.
    """
    if request.user.role != 'student':
        return JsonResponse({
            'success': False,
            'status': 'UNAUTHORIZED',
            'code': 'UNAUTHORIZED',
            'message': 'دسترسی غیرمجاز.'
        }, status=403)

    try:
        attendance_request = AttendanceRequest.objects.get(id=attendance_request_id)
    except AttendanceRequest.DoesNotExist:
        return JsonResponse({
            'success': False,
            'status': 'ATTENDANCE_NOT_FOUND',
            'code': 'ATTENDANCE_NOT_FOUND',
            'message': 'درخواست حضور و غیاب یافت نشد.'
        }, status=404)

    frames = request.FILES.getlist('frames[]') or request.FILES.getlist('frames')

    service = AttendanceFaceVerificationService()

    try:
        result = service.verify_attendance(
            student=request.user,
            attendance_request=attendance_request,
            frames=frames
        )
        return JsonResponse(result)

    except FaceServiceError as e:
        status_code = _api_error_status(e.code)
        return JsonResponse({
            'success': False,
            'status': e.code,
            'code': e.code,
            'message': e.message,
        }, status=status_code)

    except Exception as e:
        logger.error('Verification error: %s', e)
        return JsonResponse({
            'success': False,
            'status': 'PROCESSING_ERROR',
            'code': 'PROCESSING_ERROR',
            'message': 'خطا در احراز هویت.'
        }, status=500)


@login_required
def api_profile(request):
    if request.user.role != 'student':
        return JsonResponse({
            'success': False,
            'code': 'FORBIDDEN',
            'message': 'دسترسی غیرمجاز.'
        }, status=403)

    try:
        face_profile = FaceProfile.objects.get(student=request.user)
        return JsonResponse({
            'success': True,
            'profile': {
                'enrollment_status': face_profile.enrollment_status,
                'reference_images_count': face_profile.reference_images_count,
                'last_enrollment_at': str(face_profile.last_enrollment_at) if face_profile.last_enrollment_at else None,
                'last_verification_at': str(face_profile.last_verification_at) if face_profile.last_verification_at else None,
            }
        })
    except FaceProfile.DoesNotExist:
        return JsonResponse({
            'success': True,
            'profile': None,
            'message': 'چهره‌ای ثبت نشده است.'
        })


@login_required
def api_status(request):
    try:
        service = FaceRecognitionService.get_instance()
        status_info = service.get_service_status()
        return JsonResponse({
            'success': True,
            'status': status_info
        })
    except Exception as e:
        logger.error('Status check error: %s', e)
        return JsonResponse({
            'success': False,
            'code': 'STATUS_ERROR',
            'message': 'خطا در بررسی وضعیت.'
        }, status=500)


def _api_error_status(code: str) -> int:
    if code in ('UNAUTHORIZED', 'FORBIDDEN'):
        return 403

    if code == 'TOO_MANY_ATTEMPTS':
        return 429

    if code == 'MODEL_UNAVAILABLE':
        return 503

    if code in (
        'ATTENDANCE_NOT_FOUND',
        'ATTENDANCE_NOT_ACTIVE',
        'FACE_DEADLINE_EXPIRED',
        'ENROLLMENT_REQUIRED',
        'NO_REFERENCE_EMBEDDING',
        'NO_FACE',
        'MULTIPLE_FACES',
        'LOW_QUALITY_FACE',
        'LIVENESS_FAILED',
        'INVALID_IMAGE',
        'MATCH_FAILED',
        'SUSPICIOUS',
        'FACE_OUT_OF_FRAME',
        'FACE_NOT_CENTERED',
        'FACE_TOO_FAR',
        'FACE_TOO_CLOSE',
        'HEAD_TURN_LEFT_REQUIRED',
        'HEAD_TURN_RIGHT_REQUIRED',
        'BLINK_REQUIRED',
        'CHALLENGE_TIMEOUT',
        'VERIFICATION_SESSION_INVALID',
        'VERIFICATION_SESSION_EXPIRED',
        'VERIFICATION_ALREADY_COMPLETED',
    ):
        return 400

    return 500


@login_required
@require_POST
def api_mark_absent(request, attendance_request_id):
    """
    ثبت غیبت دانش‌آموز وقتی در مهلت مقرر چهره خود را اسکن نکرده.
    این مکانیزم مکمل مکانیزم خودکار سرور (mark_no_response_if_expired) است.
    """
    if request.user.role != 'student':
        return JsonResponse({
            'success': False,
            'code': 'FORBIDDEN',
            'message': 'دسترسی غیرمجاز.'
        }, status=403)

    try:
        attendance_request = AttendanceRequest.objects.get(id=attendance_request_id)
    except AttendanceRequest.DoesNotExist:
        return JsonResponse({
            'success': False,
            'code': 'ATTENDANCE_NOT_FOUND',
            'message': 'درخواست حضور و غیاب یافت نشد.'
        }, status=404)

    if attendance_request.status != 'active':
        return JsonResponse({
            'success': False,
            'code': 'ATTENDANCE_NOT_ACTIVE',
            'message': 'درخواست حضور و غیاب فعال نیست.'
        }, status=400)

    # بررسی اینکه دانش‌آموز در کلاس ثبت‌نام شده
    if not attendance_request.classroom.students.filter(pk=request.user.pk).exists():
        return JsonResponse({
            'success': False,
            'code': 'UNAUTHORIZED',
            'message': 'شما در این کلاس ثبت‌نام نشده‌اید.'
        }, status=403)

    response, created = AttendanceResponse.objects.get_or_create(
        attendance_request=attendance_request,
        student=request.user,
        defaults={
            'auto_status': 'pending',
            'final_status': 'pending'
        }
    )

    # فقط اگر هنوز پاسخی ثبت نشده
    if response.auto_status == 'pending':
        response.mark_no_response()
        return JsonResponse({
            'success': True,
            'status': 'no_response',
            'message': 'مهلت اسکن چهره به پایان رسید. شما به عنوان غایب ثبت شدید.'
        })
    else:
        return JsonResponse({
            'success': True,
            'status': response.auto_status,
            'message': 'وضعیت شما قبلاً ثبت شده است.'
        })


@login_required
@require_POST
def api_start_verification(request, attendance_request_id):
    if request.user.role != 'student':
        return JsonResponse({
            'success': False,
            'status': 'UNAUTHORIZED',
            'code': 'UNAUTHORIZED',
            'message': 'دسترسی غیرمجاز.'
        }, status=403)

    try:
        with transaction.atomic():
            attendance_request = _for_update(
                AttendanceRequest.objects.all()
            ).get(id=attendance_request_id)

            if attendance_request.status != 'active':
                raise AttendanceNotActiveError()

            if not attendance_request.requires_face:
                raise AttendanceNotActiveError('این درخواست نیاز به اسکن چهره ندارد.')

            if attendance_request.is_face_expired:
                raise FaceDeadlineExpiredError()

            if not attendance_request.classroom.students.filter(pk=request.user.pk).exists():
                raise AttendanceNotForStudentError()

            response, _ = _for_update(
                AttendanceResponse.objects.all()
            ).get_or_create(
                attendance_request=attendance_request,
                student=request.user,
                defaults={
                    'auto_status': 'pending',
                    'final_status': 'pending',
                }
            )

            if response.face_verified and response.final_status == 'present':
                return JsonResponse({
                    'success': True,
                    'status': 'VERIFIED',
                    'already_verified': True,
                    'message': 'حضور شما قبلاً تایید شده است.',
                })

            max_attempts = getattr(settings, 'FACE_MAX_ATTEMPTS', 3)
            if response.attempts >= max_attempts:
                raise TooManyAttemptsError()

            min_reference_images = getattr(settings, 'FACE_MIN_REFERENCE_IMAGES', 3)
            active_embeddings = FaceEmbedding.objects.filter(
                student_id=request.user.id,
                is_active=True,
            ).count()
            if active_embeddings < min_reference_images:
                raise EnrollmentRequiredError()

            now = timezone.now()

            active_session = _for_update(
                FaceVerificationSession.objects.filter(
                    student=request.user,
                    attendance_request=attendance_request,
                    status__in=[
                        VerificationSessionStatus.PENDING,
                        VerificationSessionStatus.IN_PROGRESS,
                    ]
                ).order_by('-created_at')
            ).first()

            if active_session:
                if active_session.is_expired:
                    active_session.mark_expired()
                else:
                    return JsonResponse({
                        'success': True,
                        'session_id': str(active_session.session_id),
                        'server_time': now.isoformat(),
                        'deadline_at': active_session.deadline_at.isoformat(),
                        'challenge': active_session.challenge_sequence,
                        'config': _face_verification_config(),
                        'reused_session': True,
                    })

            timeout_seconds = getattr(settings, 'FACE_VERIFICATION_TIMEOUT_SECONDS', 60)
            deadline = now + timedelta(seconds=timeout_seconds)

            if attendance_request.face_deadline_at:
                deadline = min(deadline, attendance_request.face_deadline_at)

            if deadline <= now:
                raise FaceDeadlineExpiredError()

            session = FaceVerificationSession.objects.create(
                student=request.user,
                attendance_request=attendance_request,
                status=VerificationSessionStatus.IN_PROGRESS,
                started_at=now,
                deadline_at=deadline,
                challenge_sequence=[
                    'TURN_LEFT',
                    'TURN_RIGHT',
                    'BLINK',
                ],
                challenge_state={
                    'current_index': 0,
                },
            )

            logger.info(
                'verification_session_created session_id=%s student_id=%s attendance_request_id=%s',
                session.session_id,
                request.user.id,
                attendance_request.id,
            )

            return JsonResponse({
                'success': True,
                'session_id': str(session.session_id),
                'server_time': now.isoformat(),
                'deadline_at': deadline.isoformat(),
                'challenge': session.challenge_sequence,
                'config': _face_verification_config(),
            })

    except AttendanceRequest.DoesNotExist:
        return JsonResponse({
            'success': False,
            'status': 'ATTENDANCE_NOT_FOUND',
            'code': 'ATTENDANCE_NOT_FOUND',
            'message': 'درخواست حضور و غیاب یافت نشد.'
        }, status=404)

    except FaceServiceError as e:
        return JsonResponse({
            'success': False,
            'status': e.code,
            'code': e.code,
            'message': e.message,
        }, status=_api_error_status(e.code))

    except Exception as e:
        logger.error('Start verification session error: %s', e)
        return JsonResponse({
            'success': False,
            'status': 'PROCESSING_ERROR',
            'code': 'PROCESSING_ERROR',
            'message': 'خطا در شروع نشست احراز هویت.'
        }, status=500)


@login_required
@require_POST
def api_complete_verification(request, session_id):
    if request.user.role != 'student':
        return JsonResponse({
            'success': False,
            'status': 'UNAUTHORIZED',
            'code': 'UNAUTHORIZED',
            'message': 'دسترسی غیرمجاز.'
        }, status=403)

    try:
        with transaction.atomic():
            session = _for_update(
                FaceVerificationSession.objects.filter(
                    session_id=session_id,
                    student=request.user,
                )
            ).first()

            if not session:
                return JsonResponse({
                    'success': False,
                    'status': 'VERIFICATION_SESSION_INVALID',
                    'code': 'VERIFICATION_SESSION_INVALID',
                    'message': 'نشست احراز هویت معتبر نیست.'
                }, status=404)

            if session.status == VerificationSessionStatus.PASSED:
                return JsonResponse({
                    'success': True,
                    'status': 'VERIFIED',
                    'already_completed': True,
                    'message': 'حضور شما قبلاً تایید شده است.',
                })

            if session.status == VerificationSessionStatus.EXPIRED:
                return JsonResponse({
                    'success': False,
                    'status': 'VERIFICATION_SESSION_EXPIRED',
                    'code': 'VERIFICATION_SESSION_EXPIRED',
                    'message': 'مهلت نشست احراز هویت به پایان رسیده است.'
                }, status=400)

            if session.status == VerificationSessionStatus.FAILED:
                return JsonResponse({
                    'success': False,
                    'status': session.failure_code or 'FAILED',
                    'code': session.failure_code or 'FAILED',
                    'message': 'این نشست احراز هویت قبلاً ناموفق شده است.'
                }, status=400)

            now = timezone.now()
            if session.deadline_at and now > session.deadline_at:
                session.mark_expired('VERIFICATION_SESSION_EXPIRED')
                return JsonResponse({
                    'success': False,
                    'status': 'VERIFICATION_SESSION_EXPIRED',
                    'code': 'VERIFICATION_SESSION_EXPIRED',
                    'message': 'مهلت نشست احراز هویت به پایان رسیده است.'
                }, status=400)

            frames = request.FILES.getlist('frames[]') or request.FILES.getlist('frames')
            if not frames:
                session.mark_failed('INVALID_IMAGE')
                return JsonResponse({
                    'success': False,
                    'status': 'INVALID_IMAGE',
                    'code': 'INVALID_IMAGE',
                    'message': 'هیچ فریمی ارسال نشده است.'
                }, status=400)

            challenge_result = _sanitize_challenge_result(
                request.POST.get('challenge_result')
            )

            service = AttendanceFaceVerificationService()

            try:
                result = service.verify_attendance(
                    student=request.user,
                    attendance_request=session.attendance_request,
                    frames=frames,
                    session=session,
                    challenge_result=challenge_result,
                )
            except FaceDeadlineExpiredError as e:
                session.mark_expired(e.code)
                return JsonResponse({
                    'success': False,
                    'status': e.code,
                    'code': e.code,
                    'message': e.message,
                }, status=_api_error_status(e.code))
            except FaceServiceError as e:
                session.mark_failed(e.code)
                return JsonResponse({
                    'success': False,
                    'status': e.code,
                    'code': e.code,
                    'message': e.message,
                }, status=_api_error_status(e.code))

            if result.get('already_verified'):
                session.mark_passed()
                return JsonResponse(result)

            if result.get('status') == 'VERIFIED':
                session.mark_passed()
                logger.info(
                    'verification_session_passed session_id=%s student_id=%s attendance_request_id=%s',
                    session.session_id,
                    request.user.id,
                    session.attendance_request_id,
                )
            else:
                session.mark_failed(result.get('status') or 'SUSPICIOUS')
                logger.info(
                    'verification_session_failed session_id=%s student_id=%s attendance_request_id=%s code=%s',
                    session.session_id,
                    request.user.id,
                    session.attendance_request_id,
                    result.get('status'),
                )

            return JsonResponse(result)

    except FaceServiceError as e:
        return JsonResponse({
            'success': False,
            'status': e.code,
            'code': e.code,
            'message': e.message,
        }, status=_api_error_status(e.code))

    except Exception as e:
        logger.error('Complete verification session error: %s', e)
        return JsonResponse({
            'success': False,
            'status': 'PROCESSING_ERROR',
            'code': 'PROCESSING_ERROR',
            'message': 'خطا در تکمیل احراز هویت.'
        }, status=500)

    