"""
ویوهای ماژول دانش‌آموز.
تمام ویوها از StudentScope استفاده می‌کنند.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Prefetch
from django.conf import settings  # ✅ اصلاح شد: از django.conf به جای core
from dashboard.models import (
    Classroom, ClassSession, Question, StudentAnswer,
    AttendanceRequest, AttendanceResponse, WeeklySchedule,
)
from .decorators import student_required
from .services import (
    StudentDashboardService,
    StudentAssessmentService,
    StudentHomeworkService,
    StudentRequestService,
    StudentStatusService,
)
from .services.face_service import StudentFaceService
from .models import (
    StudentRequest, StudentFaceChangeRequest,
    SessionMaterial, VirtualSessionInfo,
)
from .forms import StudentRequestForm, FaceChangeRequestForm, HomeworkSubmitForm
from .constants import (
    StudentRequestStatus, StudentRequestType,
    FaceChangeRequestStatus, EducationalStatusLevel,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
#  Dashboard
# ══════════════════════════════════════════════════════════

@student_required
def student_dashboard(request):
    """داشبورد دانش‌آموز — فقط Summary"""
    scope = request.student_scope
    service = StudentDashboardService(scope)
    data = service.get_dashboard_data()

    # ── جدید: احراز هویت چهره ──
    from .services.face_service import StudentFaceService
    face_service = StudentFaceService(scope)
    face_data = face_service.get_face_enrollment_status()
    active_face_count = face_service.get_active_face_count()
    # ──────────────────────────────

    context = {
        'title': 'داشبورد من',
        **data,
        'face_enrolled': face_data['is_enrolled'],
        'active_face_count': active_face_count,
    }
    return render(request, 'student/dashboard.html', context)


# ══════════════════════════════════════════════════════════
#  Profile
# ══════════════════════════════════════════════════════════

@student_required
def student_profile(request):
    """پروفایل دانش‌آموز — فقط مشاهده"""
    scope = request.student_scope
    student = scope.student

    profile = None
    try:
        profile = student.profile
    except Exception:
        pass

    classes = scope.filter_classes().select_related('school')

    context = {
        'title': 'پروفایل من',
        'student': student,
        'profile': profile,
        'classes': classes,
    }
    return render(request, 'student/profile.html', context)


# ══════════════════════════════════════════════════════════
#  Schedule
# ══════════════════════════════════════════════════════════

@student_required
def student_schedule(request):
    """برنامه هفتگی دانش‌آموز"""
    scope = request.student_scope
    schedules = scope.filter_schedules().select_related(
        'classroom', 'classroom__teacher'
    ).order_by('day_of_week', 'start_time')

    days_info = [
        ('saturday', 'شنبه'),
        ('sunday', 'یکشنبه'),
        ('monday', 'دوشنبه'),
        ('tuesday', 'سه‌شنبه'),
        ('wednesday', 'چهارشنبه'),
    ]
    schedule_days = []
    for day_key, day_name in days_info:
        day_classes = [s for s in schedules if s.day_of_week == day_key]
        schedule_days.append({
            'key': day_key,
            'name': day_name,
            'classes': day_classes,
            'count': len(day_classes),
        })

    context = {
        'title': 'برنامه هفتگی',
        'schedule_days': schedule_days,
        'total_classes': schedules.count(),
    }
    return render(request, 'student/schedule.html', context)


# ══════════════════════════════════════════════════════════
#  Classes
# ══════════════════════════════════════════════════════════

@student_required
def student_classes(request):
    """کلاس‌های من"""
    scope = request.student_scope
    classes = scope.filter_classes().select_related(
        'teacher', 'school'
    ).annotate(
        sessions_count=Count('sessions', distinct=True),
    ).order_by('name')

    context = {
        'title': 'کلاس‌های من',
        'classes': classes,
    }
    return render(request, 'student/classes.html', context)


@student_required
def student_class_detail(request, classroom_id):
    """جزئیات کلاس"""
    scope = request.student_scope
    classroom = scope.get_class_or_404(classroom_id)

    sessions = scope.filter_sessions().filter(
        classroom=classroom
    ).order_by('-session_date')[:20]

    # بررسی حضور دانش‌آموز در هر جلسه
    attendance_map = {}
    responses = scope.filter_attendance_responses().filter(
        attendance_request__classroom=classroom
    ).select_related('attendance_request__session')
    for resp in responses:
        session_id = resp.attendance_request.session_id
        attendance_map[session_id] = resp.final_status

    context = {
        'title': f'کلاس {classroom.name}',
        'classroom': classroom,
        'sessions': sessions,
        'attendance_map': attendance_map,
    }
    return render(request, 'student/class_detail.html', context)


# ══════════════════════════════════════════════════════════
#  Sessions
# ══════════════════════════════════════════════════════════

@student_required
def student_sessions(request):
    """جلسات کلاس‌های دانش‌آموز"""
    scope = request.student_scope
    sessions = scope.filter_sessions().select_related(
        'classroom'
    ).order_by('-session_date')[:50]

    context = {
        'title': 'جلسات',
        'sessions': sessions,
    }
    return render(request, 'student/sessions.html', context)


@student_required
def student_session_detail(request, session_id):
    """جزئیات جلسه"""
    scope = request.student_scope
    session = scope.get_session_or_404(session_id)

    # محتوای آموزشی
    materials = SessionMaterial.objects.filter(
        session=session,
        visible_to_students=True,
    )

    # اطلاعات کلاس مجازی
    virtual_info = None
    try:
        virtual_info = session.virtual_info
    except VirtualSessionInfo.DoesNotExist:
        pass

    # اطلاعات تکمیلی جلسه
    extension = None
    try:
        extension = session.extension
    except Exception:
        pass

    # سوالات فعال
    questions = scope.filter_questions().filter(
        session=session, is_approved=True
    )

    # ارزیابی‌ها
    from teacher.models import Assessment
    assessments = scope.filter_assessments().filter(session=session)

    # تکالیف
    from teacher.models import Homework
    homeworks = scope.filter_homeworks().filter(session=session)

    # وضعیت حضور
    attendance_status = None
    att_response = scope.filter_attendance_responses().filter(
        attendance_request__session=session
    ).first()
    if att_response:
        attendance_status = att_response.final_status

    context = {
        'title': f'جلسه {session.id}',
        'session': session,
        'materials': materials,
        'virtual_info': virtual_info,
        'extension': extension,
        'questions': questions,
        'assessments': assessments,
        'homeworks': homeworks,
        'attendance_status': attendance_status,
    }
    return render(request, 'student/session_detail.html', context)


@student_required
def student_attendance(request):
    scope = request.student_scope
    face_service = StudentFaceService(scope)
    active_face_items = face_service.get_active_face_requests()
    face_data = face_service.get_face_enrollment_status()

    base_responses = scope.filter_attendance_responses()
    total = base_responses.count()
    present = base_responses.filter(final_status='present').count()
    absent = base_responses.filter(final_status='absent').count()
    pending = base_responses.filter(final_status='pending').count()

    responses = base_responses.select_related(
        'attendance_request__classroom',
        'attendance_request__session',
    ).order_by('-created_at')[:30]

    context = {
        'title': 'حضور و غیاب',
        'active_face_items': active_face_items,
        'face_enrolled': face_data['is_enrolled'],
        'responses': responses,
        'total': total,
        'present': present,
        'absent': absent,
        'pending': pending,
        'attendance_rate': round((present / total) * 100, 1) if total > 0 else None,
    }
    return render(request, 'student/attendance.html', context)

# ══════════════════════════════════════════════════════════
#  Questions
# ══════════════════════════════════════════════════════════

@student_required
def student_questions(request):
    """سوالات فعال"""
    scope = request.student_scope

    # ── جدید: شمارش درخواست‌های احراز هویت فعال ──
    from .services.face_service import StudentFaceService
    face_service = StudentFaceService(scope)
    active_face_count = face_service.get_active_face_count()
    face_data = face_service.get_face_enrollment_status()

    active_requests = scope.filter_attendance_requests().filter(
        status='active',
        request_type__in=['question_only', 'face_and_question'],
    ).select_related('classroom', 'session', 'teacher').prefetch_related(
        'request_questions__question'
    ).order_by('-created_at')

    question_items = []
    for att_request in active_requests:
        total_questions = att_request.request_questions.count()
        answered_count = StudentAnswer.objects.filter(
            attendance_request=att_request,
            student=scope.student,
        ).count()

        response = AttendanceResponse.objects.filter(
            attendance_request=att_request,
            student=scope.student,
        ).first()

        requires_face = att_request.requires_face
        face_verified = False
        if response and response.face_verified and response.final_status == 'present':
            face_verified = True
        can_answer = not requires_face or face_verified

        question_items.append({
            'request': att_request,
            'response': response,
            'total_questions': total_questions,
            'answered_count': answered_count,
            'can_answer': can_answer,
            'all_answered': answered_count >= total_questions,
            'requires_face': requires_face,
            'face_verified': face_verified,
        })

    context = {
        'title': 'سوالات و فعالیت‌ها',
        'question_items': question_items,
        # ── جدید ──
        'active_face_count': active_face_count,
        'face_enrolled': face_data['is_enrolled'],
    }
    return render(request, 'student/questions.html', context)

# ══════════════════════════════════════════════════════════
#  Assessments
# ══════════════════════════════════════════════════════════

@student_required
def student_assessments(request):
    """ارزیابی‌های من"""
    scope = request.student_scope
    from teacher.models import Assessment

    assessments = scope.filter_assessments().select_related(
        'classroom', 'teacher'
    ).order_by('-created_at')

    # دسته‌بندی
    active = []
    completed = []
    upcoming = []

    from teacher.models import StudentAssessmentResponse
    for a in assessments:
        has_response = StudentAssessmentResponse.objects.filter(
            assessment=a, student=scope.student
        ).exists()
        if a.status in ('published', 'in_progress') and not has_response:
            active.append(a)
        elif has_response:
            completed.append(a)
        else:
            upcoming.append(a)

    context = {
        'title': 'ارزیابی‌های من',
        'active': active,
        'completed': completed,
        'upcoming': upcoming,
    }
    return render(request, 'student/assessments.html', context)


@student_required
def student_assessment_detail(request, assessment_id):
    """جزئیات ارزیابی"""
    scope = request.student_scope
    assessment = scope.get_assessment_or_404(assessment_id)

    questions_count = assessment.questions.count()

    # بررسی اینکه آیا دانش‌آموز قبلاً پاسخ داده
    from teacher.models import StudentAssessmentResponse
    has_responded = StudentAssessmentResponse.objects.filter(
        assessment=assessment,
        student=scope.student,
    ).exists()

    context = {
        'title': assessment.title,
        'assessment': assessment,
        'questions_count': questions_count,
        'has_responded': has_responded,
    }
    return render(request, 'student/assessment_detail.html', context)


@student_required
def student_assessment_take(request, assessment_id):
    """شروع و پاسخ به ارزیابی"""
    scope = request.student_scope
    assessment = scope.get_assessment_or_404(assessment_id)

    if assessment.status not in ('published', 'in_progress'):
        messages.error(request, 'این آزمون در حال حاضر فعال نیست.')
        return redirect('student:assessments')

    from teacher.models import StudentAssessmentResponse, AssessmentQuestion
    has_responded = StudentAssessmentResponse.objects.filter(
        assessment=assessment,
        student=scope.student,
    ).exists()
    if has_responded:
        messages.warning(request, 'شما قبلاً در این آزمون شرکت کرده‌اید.')
        return redirect('student:assessment_result', assessment_id=assessment_id)

    questions = assessment.questions.select_related(
        'question'
    ).order_by('order')

    if request.method == 'POST':
        correct_count = 0
        for aq in questions:
            selected = request.POST.get(f'question_{aq.question_id}')
            if selected in ('a', 'b', 'c', 'd'):
                is_correct = selected == aq.question.correct_answer
                if is_correct:
                    correct_count += 1
                StudentAssessmentResponse.objects.create(
                    assessment=assessment,
                    student=scope.student,
                    question=aq.question,
                    selected_choice=selected,
                    is_correct=is_correct,
                    score=aq.score if is_correct else 0,
                )

        messages.success(request, 'پاسخ‌های شما ثبت شد.')
        return redirect('student:assessment_result', assessment_id=assessment_id)

    context = {
        'title': f'آزمون: {assessment.title}',
        'assessment': assessment,
        'questions': questions,
    }
    return render(request, 'student/assessment_take.html', context)


@student_required
def student_assessment_result(request, assessment_id):
    """نتیجه ارزیابی"""
    scope = request.student_scope
    assessment = scope.get_assessment_or_404(assessment_id)

    service = StudentAssessmentService(scope)
    result = service.get_assessment_result(assessment, scope.student)

    if result['answered'] == 0:
        messages.warning(request, 'شما هنوز در این آزمون شرکت نکرده‌اید.')
        return redirect('student:assessments')

    # بازخورد مرتبط
    from teacher.models import TeacherFeedback
    feedback = TeacherFeedback.objects.filter(
        student=scope.student,
        related_assessment=assessment,
    ).first()

    context = {
        'title': f'نتیجه: {assessment.title}',
        'assessment': assessment,
        'result': result,
        'feedback': feedback,
    }
    return render(request, 'student/assessment_result.html', context)


# ══════════════════════════════════════════════════════════
#  Homework
# ══════════════════════════════════════════════════════════

@student_required
def student_homeworks(request):
    """تکالیف من"""
    scope = request.student_scope
    from teacher.models import Homework, HomeworkSubmission

    homeworks = scope.filter_homeworks().select_related(
        'classroom', 'teacher'
    ).order_by('-created_at')

    # وضعیت ارسال هر تکلیف
    submissions = {
        s.homework_id: s
        for s in scope.filter_homework_submissions().select_related('homework')
    }

    hw_list = []
    for hw in homeworks:
        sub = submissions.get(hw.id)
        hw_list.append({
            'homework': hw,
            'submission': sub,
            'is_late': timezone.now() > hw.deadline,
        })

    context = {
        'title': 'تکالیف من',
        'homeworks': hw_list,
    }
    return render(request, 'student/homeworks.html', context)


@student_required
def student_homework_detail(request, homework_id):
    """جزئیات تکلیف"""
    scope = request.student_scope
    homework = scope.get_homework_or_404(homework_id)

    hw_service = StudentHomeworkService(scope)
    submission, _ = hw_service.get_or_create_submission(homework)
    can_submit = hw_service.can_submit(homework)
    is_late = hw_service.is_late(homework)

    context = {
        'title': homework.title,
        'homework': homework,
        'submission': submission,
        'can_submit': can_submit,
        'is_late': is_late,
    }
    return render(request, 'student/homework_detail.html', context)


@student_required
def student_homework_submit(request, homework_id):
    """ارسال تکلیف"""
    scope = request.student_scope
    homework = scope.get_homework_or_404(homework_id)

    hw_service = StudentHomeworkService(scope)

    if not hw_service.can_submit(homework):
        if homework.deadline < timezone.now():
            messages.error(request, 'مهلت ارسال تکلیف به پایان رسیده است.')
        else:
            messages.error(request, 'این تکلیف در حال حاضر قابل ارسال نیست.')
        return redirect('student:homework_detail', homework_id=homework_id)

    submission, _ = hw_service.get_or_create_submission(homework)

    # اگر قبلاً نمره داده شده، اجازه ویرایش نیست
    if submission.status in ('REVIEWED', 'RETURNED'):
        messages.error(request, 'این تکلیف قبلاً بررسی شده و قابل ویرایش نیست.')
        return redirect('student:homework_detail', homework_id=homework_id)

    if request.method == 'POST':
        form = HomeworkSubmitForm(request.POST, request.FILES)
        if form.is_valid():
            submission.content = form.cleaned_data.get('content', '')
            if form.cleaned_data.get('attachment'):
                submission.attachment = form.cleaned_data['attachment']

            now = timezone.now()
            submission.submitted_at = now
            if now > homework.deadline:
                submission.status = 'LATE'
            else:
                submission.status = 'SUBMITTED'
            submission.save()

            messages.success(request, 'تکلیف شما با موفقیت ارسال شد.')
            return redirect('student:homework_detail', homework_id=homework_id)
    else:
        form = HomeworkSubmitForm(initial={
            'content': submission.content,
        })

    context = {
        'title': f'ارسال: {homework.title}',
        'homework': homework,
        'submission': submission,
        'form': form,
    }
    return render(request, 'student/homework_submit.html', context)


# ══════════════════════════════════════════════════════════
#  Feedback
# ══════════════════════════════════════════════════════════

@student_required
def student_feedback(request):
    """بازخوردهای من"""
    scope = request.student_scope
    from teacher.models import TeacherFeedback

    feedbacks = scope.filter_feedbacks().select_related(
        'teacher', 'related_assessment', 'related_homework'
    ).order_by('-created_at')

    context = {
        'title': 'بازخوردهای من',
        'feedbacks': feedbacks,
    }
    return render(request, 'student/feedback.html', context)


# ══════════════════════════════════════════════════════════
#  Educational Status
# ══════════════════════════════════════════════════════════

@student_required
def student_status(request):
    """وضعیت آموزشی من"""
    scope = request.student_scope
    service = StudentStatusService(scope)
    status_data = service.get_full_status()

    context = {
        'title': 'وضعیت آموزشی من',
        **status_data,
    }
    return render(request, 'student/status.html', context)


# ══════════════════════════════════════════════════════════
#  Requests
# ══════════════════════════════════════════════════════════

@student_required
def student_requests(request):
    """درخواست‌های من"""
    scope = request.student_scope
    reqs = scope.filter_student_requests().order_by('-created_at')

    context = {
        'title': 'درخواست‌های من',
        'requests': reqs,
    }
    return render(request, 'student/requests.html', context)


@student_required
def student_request_create(request):
    """ایجاد درخواست جدید"""
    scope = request.student_scope

    if request.method == 'POST':
        form = StudentRequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.student = scope.student
            req.save()
            messages.success(request, 'درخواست شما با موفقیت ثبت شد.')
            return redirect('student:request_detail', request_id=req.id)
    else:
        form = StudentRequestForm()

    context = {
        'title': 'ثبت درخواست جدید',
        'form': form,
    }
    return render(request, 'student/request_create.html', context)


@student_required
def student_request_detail(request, request_id):
    """جزئیات درخواست"""
    scope = request.student_scope
    req = scope.get_student_request_or_404(request_id)

    context = {
        'title': f'درخواست: {req.title}',
        'req': req,
    }
    return render(request, 'student/request_detail.html', context)


@student_required
def student_request_cancel(request, request_id):
    """لغو درخواست"""
    scope = request.student_scope
    req = scope.get_student_request_or_404(request_id)

    if request.method == 'POST':
        service = StudentRequestService(scope)
        if service.cancel_request(req):
            messages.success(request, 'درخواست شما لغو شد.')
        else:
            messages.error(request, 'این درخواست قابل لغو نیست.')
    return redirect('student:request_detail', request_id=request_id)


# ══════════════════════════════════════════════════════════
#  Face Management
# ══════════════════════════════════════════════════════════

@student_required
def student_face(request):
    """مدیریت احراز هویت چهره"""
    scope = request.student_scope
    from face.models import FaceProfile, FaceEmbedding

    face_profile = None
    try:
        face_profile = scope.student.face_profile
    except Exception:
        pass

    embeddings_count = FaceEmbedding.objects.filter(
        student=scope.student, is_active=True
    ).count()

    from django.conf import settings
    min_ref = getattr(settings, 'FACE_MIN_REFERENCE_IMAGES', 3)
    is_enrolled = embeddings_count >= min_ref

    # درخواست‌های تغییر چهره
    change_requests = StudentFaceChangeRequest.objects.filter(
        student=scope.student
    ).order_by('-created_at')[:5]

    context = {
        'title': 'احراز هویت چهره',
        'face_profile': face_profile,
        'embeddings_count': embeddings_count,
        'min_reference': min_ref,
        'is_enrolled': is_enrolled,
        'change_requests': change_requests,
    }
    return render(request, 'student/face.html', context)


@student_required
def student_face_change_request(request):
    """درخواست تغییر چهره"""
    scope = request.student_scope

    # بررسی درخواست فعال قبلی
    existing = StudentFaceChangeRequest.objects.filter(
        student=scope.student,
        status=FaceChangeRequestStatus.PENDING,
    ).exists()
    if existing:
        messages.warning(request, 'شما یک درخواست در انتظار بررسی دارید.')
        return redirect('student:face')

    if request.method == 'POST':
        form = FaceChangeRequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.student = scope.student
            req.save()
            messages.success(request, 'درخواست تغییر چهره ثبت شد و در انتظار بررسی است.')
            return redirect('student:face')
    else:
        form = FaceChangeRequestForm()

    context = {
        'title': 'درخواست تغییر چهره',
        'form': form,
    }
    return render(request, 'student/face_change_request.html', context)


# ══════════════════════════════════════════════════════════
#  Virtual Classes
# ══════════════════════════════════════════════════════════

@student_required
def student_virtual_classes(request):
    """کلاس‌های مجازی"""
    scope = request.student_scope

    sessions = scope.filter_sessions().filter(
        virtual_info__isnull=False,
    ).select_related('classroom', 'virtual_info').order_by('-session_date')[:30]

    context = {
        'title': 'کلاس‌های مجازی',
        'sessions': sessions,
    }
    return render(request, 'student/virtual_classes.html', context)


# ══════════════════════════════════════════════════════════
#  ویوهای پاسخ به سوالات (از dashboard منتقل شد)
# ══════════════════════════════════════════════════════════
from django.http import JsonResponse


@student_required
def student_questions_page(request):
    """سوالات فعال"""
    scope = request.student_scope
    student = scope.student

    from dashboard.models import AttendanceRequest, AttendanceResponse, StudentAnswer

    active_requests = scope.filter_attendance_requests().filter(
        status='active',
        request_type__in=['question_only', 'face_and_question'],
    ).select_related('classroom', 'session', 'teacher').prefetch_related(
        'request_questions__question'
    ).order_by('-created_at')

    question_items = []
    for att_request in active_requests:
        total_questions = att_request.request_questions.count()
        answered_count = StudentAnswer.objects.filter(
            attendance_request=att_request,
            student=student,
        ).count()
        response = AttendanceResponse.objects.filter(
            attendance_request=att_request,
            student=student,
        ).first()
        requires_face = att_request.requires_face
        face_verified = bool(response and response.face_verified and response.final_status == 'present')
        can_answer = not requires_face or face_verified

        question_items.append({
            'request': att_request,
            'response': response,
            'total_questions': total_questions,
            'answered_count': answered_count,
            'can_answer': can_answer,
            'all_answered': answered_count >= total_questions,
        })

    context = {
        'title': 'سوالات فعال',
        'question_items': question_items,
    }
    return render(request, 'student/questions.html', context)


@student_required
def student_answer_questions(request, request_id):
    """صفحه پاسخ به سوالات"""
    scope = request.student_scope
    student = scope.student
    att_request = scope.get_attendance_request_or_404(request_id)

    if att_request.status != 'active':
        messages.error(request, 'این درخواست فعال نیست.')
        return redirect('student:questions')

    if att_request.requires_face:
        from dashboard.models import AttendanceResponse
        response = AttendanceResponse.objects.filter(
            attendance_request=att_request,
            student=student,
        ).first()
        if not response or not response.face_verified or response.final_status != 'present':
            messages.warning(request, 'لطفاً ابتدا احراز هویت چهره را تکمیل کنید.')
            return redirect('student:attendance')

    from dashboard.models import StudentAnswer
    request_questions = att_request.request_questions.select_related(
        'question'
    ).order_by('order')

    existing_answers = {
        answer.question_id: answer
        for answer in StudentAnswer.objects.filter(
            attendance_request=att_request,
            student=student
        )
    }

    questions_with_answers = []
    for rq in request_questions:
        questions_with_answers.append({
            'request_question': rq,
            'question': rq.question,
            'answer': existing_answers.get(rq.question.id),
        })

    context = {
        'title': f'پاسخ به سوالات',
        'attendance_request': att_request,
        'questions': questions_with_answers,
        'total_questions': len(questions_with_answers),
        'answered_count': len(existing_answers),
    }
    return render(request, 'student/answer_questions.html', context)


@student_required
def student_submit_answer(request, request_id, question_id):
    """ثبت پاسخ سوال"""
    scope = request.student_scope
    student = scope.student

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'درخواست نامعتبر'}, status=400)

    from dashboard.models import AttendanceRequest, Question, StudentAnswer, AttendanceResponse

    try:
        att_request = AttendanceRequest.objects.get(
            id=request_id,
            classroom__students=student,
            status='active'
        )
    except AttendanceRequest.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'درخواست یافت نشد'}, status=404)

    if att_request.requires_face:
        response = AttendanceResponse.objects.filter(
            attendance_request=att_request,
            student=student,
        ).first()
        if not response or not response.face_verified:
            return JsonResponse({'success': False, 'message': 'احراز هویت لازم است'}, status=403)

    try:
        question = Question.objects.get(
            id=question_id,
            attendance_requests=att_request
        )
    except Question.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'سوال یافت نشد'}, status=404)

    selected_choice = request.POST.get('choice')
    if selected_choice not in ['a', 'b', 'c', 'd']:
        return JsonResponse({'success': False, 'message': 'پاسخ نامعتبر'}, status=400)

    is_correct = selected_choice == question.correct_answer

    StudentAnswer.objects.update_or_create(
        question=question,
        student=student,
        attendance_request=att_request,
        defaults={
            'selected_choice': selected_choice,
            'is_correct': is_correct,
        }
    )

    total_questions = att_request.request_questions.count()
    answered_count = StudentAnswer.objects.filter(
        attendance_request=att_request,
        student=student,
    ).count()

    return JsonResponse({
        'success': True,
        'is_correct': is_correct,
        'answered_count': answered_count,
        'total_questions': total_questions,
        'all_completed': answered_count >= total_questions,
    })


@student_required
def student_question_result(request, request_id):
    """نتیجه سوالات"""
    scope = request.student_scope
    student = scope.student
    att_request = scope.get_attendance_request_or_404(request_id)

    from dashboard.models import StudentAnswer
    answers = StudentAnswer.objects.filter(
        attendance_request=att_request,
        student=student
    ).select_related('question')

    total_questions = att_request.request_questions.count()
    answered_count = answers.count()
    correct_count = answers.filter(is_correct=True).count()
    wrong_count = answers.filter(is_correct=False).count()
    percentage = round((correct_count / answered_count) * 100) if answered_count > 0 else 0

    context = {
        'title': 'نتیجه سوالات',
        'attendance_request': att_request,
        'answers': answers,
        'total_questions': total_questions,
        'answered_count': answered_count,
        'correct_count': correct_count,
        'wrong_count': wrong_count,
        'percentage': percentage,
    }
    return render(request, 'student/question_result.html', context)