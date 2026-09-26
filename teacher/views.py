"""
ویوهای ماژول معلم.
تمام ویوها از TeacherScope استفاده می‌کنند.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q

from dashboard.models import Classroom, ClassSession, Question
from .decorators import teacher_scope_required, teacher_permission_required
from .constants import (
    TeacherPermission, SessionStatus,
    ParticipationLevel, AssessmentStatus,
)
from .services import (
    TeacherAnalyticsService,
    TeacherParticipationService,
    TeacherSessionService,
    StudentRiskService,
)
from .audit import TeacherAuditService
from .models import (
    SessionExtension, ParticipationRecord,
    Assessment, Homework, TeacherNote,
    FollowUpSuggestion,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
#  Dashboard
# ══════════════════════════════════════════════════════════
@teacher_scope_required
def teacher_dashboard(request):
    scope = request.teacher_scope
    analytics = TeacherAnalyticsService(scope)
    session_service = TeacherSessionService(scope)
    risk_service = StudentRiskService(scope)

    overview = analytics.get_overview()
    active_session = session_service.get_active_session()

    # کارهای نیازمند اقدام
    pending_questions = scope.filter_questions().filter(
        review_status='pending'
    ).count()

    # دانش‌آموزان نیازمند توجه
    students_at_risk = risk_service.get_students_needing_attention()

    # کلاس‌های امروز
    today = timezone.now().date()
    today_classes = scope.filter_classes().filter(
        schedules__day_of_week=today.strftime('%A').lower()
    ).distinct()

    context = {
        'title': 'داشبورد معلم',
        'overview': overview,
        'active_session': active_session,
        'pending_questions': pending_questions,
        'students_at_risk': students_at_risk[:5],
        'today_classes': today_classes,
    }
    return render(request, 'teacher/dashboard.html', context)


# ══════════════════════════════════════════════════════════
#  Classes
# ══════════════════════════════════════════════════════════
@teacher_scope_required
def teacher_classes(request):
    scope = request.teacher_scope
    analytics = TeacherAnalyticsService(scope)

    classrooms = scope.filter_classes().annotate(
        students_count=Count('students', distinct=True),
        sessions_count=Count('sessions', distinct=True),
    )

    context = {
        'title': 'کلاس‌های من',
        'classrooms': classrooms,
    }
    return render(request, 'teacher/classes/list.html', context)


@teacher_scope_required
def teacher_class_detail(request, classroom_id):
    scope = request.teacher_scope
    classroom = scope.get_class_or_404(classroom_id)
    analytics = TeacherAnalyticsService(scope)

    class_analytics = analytics.get_class_analytics(classroom_id)
    sessions = classroom.sessions.order_by('-session_date')[:10]
    students_count = classroom.students.count()

    context = {
        'title': f'کلاس {classroom.name}',
        'classroom': classroom,
        'analytics': class_analytics,
        'sessions': sessions,
        'students_count': students_count,
    }
    return render(request, 'teacher/classes/detail.html', context)


@teacher_scope_required
def teacher_class_students(request, classroom_id):
    scope = request.teacher_scope
    classroom = scope.get_class_or_404(classroom_id)
    students = scope.filter_students(classroom=classroom).select_related(
        'profile'
    ).order_by('last_name', 'first_name')

    context = {
        'title': f'دانش‌آموزان {classroom.name}',
        'classroom': classroom,
        'students': students,
    }
    return render(request, 'teacher/classes/students.html', context)


# ══════════════════════════════════════════════════════════
#  Sessions
# ══════════════════════════════════════════════════════════
@teacher_scope_required
def teacher_sessions(request):
    scope = request.teacher_scope
    sessions = scope.filter_sessions().select_related(
        'classroom'
    ).order_by('-session_date')[:50]

    context = {
        'title': 'جلسات آموزشی',
        'sessions': sessions,
    }
    return render(request, 'teacher/sessions/list.html', context)


@teacher_scope_required
@teacher_permission_required(TeacherPermission.SESSION_CREATE)
def teacher_session_create(request):
    scope = request.teacher_scope
    classrooms = scope.filter_classes()

    if request.method == 'POST':
        classroom_id = request.POST.get('classroom')
        topic = request.POST.get('topic', '')
        objectives = request.POST.get('objectives', '')
        description = request.POST.get('description', '')

        try:
            classroom = scope.get_class_or_404(classroom_id)
            service = TeacherSessionService(scope)
            session = service.create_session(
                classroom,
                topic=topic,
                learning_objectives=objectives,
                description=description,
            )
            messages.success(request, 'جلسه با موفقیت ایجاد شد.')
            return redirect(
                'teacher:session_detail', session_id=session.id
            )
        except Exception as e:
            messages.error(request, f'خطا در ایجاد جلسه: {e}')

    context = {
        'title': 'ایجاد جلسه جدید',
        'classrooms': classrooms,
    }
    return render(request, 'teacher/sessions/create.html', context)


@teacher_scope_required
def teacher_session_detail(request, session_id):
    scope = request.teacher_scope
    session = scope.get_session_or_404(session_id)

    ext = SessionExtension.objects.filter(
        session=session
    ).first()

    context = {
        'title': f'جلسه {session.id}',
        'session': session,
        'extension': ext,
    }
    return render(request, 'teacher/sessions/detail.html', context)


@teacher_scope_required
@teacher_permission_required(TeacherPermission.SESSION_START)
def teacher_session_start(request, session_id):
    scope = request.teacher_scope
    session = scope.get_session_or_404(session_id)

    try:
        service = TeacherSessionService(scope)
        service.start_session(session)
        messages.success(request, 'جلسه فعال شد.')
        return redirect(
            'teacher:session_panel', session_id=session.id
        )
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('teacher:sessions')


@teacher_scope_required
@teacher_permission_required(TeacherPermission.SESSION_END)
def teacher_session_end(request, session_id):
    scope = request.teacher_scope
    session = scope.get_session_or_404(session_id)

    try:
        service = TeacherSessionService(scope)
        service.end_session(session)
        messages.success(request, 'جلسه پایان یافت.')
        return redirect(
            'teacher:session_detail', session_id=session.id
        )
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('teacher:session_panel', session_id=session.id)


@teacher_scope_required
def teacher_session_panel(request, session_id):
    """Session Control Panel"""
    scope = request.teacher_scope
    session = scope.get_session_or_404(session_id)
    ext = SessionExtension.objects.filter(session=session).first()

    classroom = session.classroom
    students = classroom.students.all()

    # آمار حضور
    from dashboard.models import AttendanceResponse
    att_responses = AttendanceResponse.objects.filter(
        attendance_request__session=session,
    )
    present = att_responses.filter(final_status='present').count()
    absent = att_responses.filter(final_status='absent').count()
    suspicious = att_responses.filter(
        auto_status='suspicious'
    ).count()
    pending = att_responses.filter(final_status='pending').count()

    context = {
        'title': f'پنل جلسه {session.id}',
        'session': session,
        'extension': ext,
        'classroom': classroom,
        'students_count': students.count(),
        'present_count': present,
        'absent_count': absent,
        'suspicious_count': suspicious,
        'pending_count': pending,
    }
    return render(request, 'teacher/sessions/panel.html', context)


# ══════════════════════════════════════════════════════════
#  Attendance
# ══════════════════════════════════════════════════════════
@teacher_scope_required
def teacher_attendance(request):
    scope = request.teacher_scope
    requests = scope.filter_attendance_requests().select_related(
        'classroom', 'session'
    ).order_by('-created_at')[:30]

    context = {
        'title': 'حضور و غیاب',
        'attendance_requests': requests,
    }
    return render(request, 'teacher/attendance/list.html', context)


@teacher_scope_required
def teacher_attendance_detail(request, request_id):
    scope = request.teacher_scope
    att_request = scope.get_attendance_request_or_404(request_id)

    responses = att_request.responses.select_related(
        'student'
    ).order_by('student__last_name')

    context = {
        'title': f'جزئیات حضور - درخواست {request_id}',
        'attendance_request': att_request,
        'responses': responses,
    }
    return render(request, 'teacher/attendance/detail.html', context)


@teacher_scope_required
@teacher_permission_required(TeacherPermission.ATTENDANCE_CORRECT)
def teacher_attendance_correct(request, response_id):
    scope = request.teacher_scope
    response = scope.get_attendance_response_or_404(response_id)

    if request.method == 'POST':
        new_status = request.POST.get('new_status')
        reason = request.POST.get('reason', '')

        if new_status not in ('present', 'absent'):
            messages.error(request, 'وضعیت نامعتبر است.')
            return redirect(
                'teacher:attendance_detail',
                request_id=response.attendance_request_id,
            )

        if not reason.strip():
            messages.error(request, 'دلیل تغییر الزامی است.')
            return redirect(
                'teacher:attendance_correct',
                response_id=response_id,
            )

        old_status = response.final_status

        # Audit
        TeacherAuditService.log(
            request,
            action='attendance_correction',
            object_type='AttendanceResponse',
            object_id=response_id,
            old_values={'final_status': old_status},
            new_values={'final_status': new_status, 'reason': reason},
            reason=reason,
            classroom=response.attendance_request.classroom,
        )

        response.final_status = new_status
        response.reviewed_by = request.user
        response.reviewed_at = timezone.now()
        response.save()

        messages.success(request, 'وضعیت حضور اصلاح شد.')
        return redirect(
            'teacher:attendance_detail',
            request_id=response.attendance_request_id,
        )

    context = {
        'title': 'اصلاح وضعیت حضور',
        'response': response,
    }
    return render(request, 'teacher/attendance/correct.html', context)


# ══════════════════════════════════════════════════════════
#  Participation
# ══════════════════════════════════════════════════════════
@teacher_scope_required
def teacher_participation(request):
    scope = request.teacher_scope
    sessions = scope.filter_sessions().select_related(
        'classroom'
    ).order_by('-session_date')[:20]

    context = {
        'title': 'مشارکت دانش‌آموزان',
        'sessions': sessions,
    }
    return render(request, 'teacher/participation/list.html', context)


@teacher_scope_required
@teacher_permission_required(TeacherPermission.PARTICIPATION_EDIT)
def teacher_participation_record(request, session_id):
    scope = request.teacher_scope
    session = scope.get_session_or_404(session_id)
    classroom = session.classroom
    students = classroom.students.order_by('last_name')

    if request.method == 'POST':
        service = TeacherParticipationService(scope)
        participations = {}

        for student in students:
            level = request.POST.get(f'level_{student.id}')
            if level in ('high', 'medium', 'low'):
                participations[student.id] = level

        if participations:
            service.batch_record_participation(
                session, participations
            )
            messages.success(
                request,
                f'{len(participations)} رکورد مشارکت ثبت شد.'
            )
        return redirect(
            'teacher:participation_record', session_id=session_id
        )

    # رکوردهای موجود
    service = TeacherParticipationService(scope)
    existing = service.get_session_participation(session)
    existing_map = {r.student_id: r for r in existing}

    context = {
        'title': f'ثبت مشارکت - جلسه {session_id}',
        'session': session,
        'students': students,
        'existing_map': existing_map,
        'levels': ParticipationLevel.CHOICES,
    }
    return render(request, 'teacher/participation/record.html', context)


# ══════════════════════════════════════════════════════════
#  Students
# ══════════════════════════════════════════════════════════
@teacher_scope_required
def teacher_students(request):
    scope = request.teacher_scope
    students = scope.filter_students().select_related(
        'profile'
    ).order_by('last_name', 'first_name')

    context = {
        'title': 'دانش‌آموزان',
        'students': students,
    }
    return render(request, 'teacher/students/list.html', context)


@teacher_scope_required
def teacher_student_detail(request, student_id):
    scope = request.teacher_scope
    student = scope.get_student_or_404(student_id)
    analytics = TeacherAnalyticsService(scope)

    # آمار دانش‌آموز
    att_records = scope.filter_attendance_responses().filter(
        student=student,
    )
    total_att = att_records.count()
    present = att_records.filter(final_status='present').count()
    attendance_rate = (
        round((present / total_att) * 100, 1) if total_att > 0
        else None
    )

    answers = scope.filter_student_answers().filter(student=student)
    total_answers = answers.count()
    correct = answers.filter(is_correct=True).count()
    performance_rate = (
        round((correct / total_answers) * 100, 1)
        if total_answers > 0 else None
    )

    context = {
        'title': f'پروفایل {student.get_full_name()}',
        'student': student,
        'attendance_rate': attendance_rate,
        'performance_rate': performance_rate,
        'total_answers': total_answers,
    }
    return render(request, 'teacher/students/detail.html', context)


# ══════════════════════════════════════════════════════════
#  Notes
# ══════════════════════════════════════════════════════════
@teacher_scope_required
def teacher_student_notes(request, student_id):
    scope = request.teacher_scope
    student = scope.get_student_or_404(student_id)

    notes = TeacherNote.objects.filter(
        teacher=request.user,
        student=student,
    ).order_by('-created_at')

    context = {
        'title': f'یادداشت‌ها - {student.get_full_name()}',
        'student': student,
        'notes': notes,
    }
    return render(request, 'teacher/students/notes.html', context)


@teacher_scope_required
@teacher_permission_required(TeacherPermission.NOTE_CREATE)
def teacher_note_add(request, student_id):
    scope = request.teacher_scope
    student = scope.get_student_or_404(student_id)

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if not content:
            messages.error(request, 'متن یادداشت الزامی است.')
        else:
            TeacherNote.objects.create(
                teacher=request.user,
                student=student,
                content=content,
            )
            messages.success(request, 'یادداشت ثبت شد.')
        return redirect(
            'teacher:student_notes', student_id=student_id
        )

    return redirect('teacher:student_notes', student_id=student_id)


# ══════════════════════════════════════════════════════════
#  Follow-up Suggestion
# ══════════════════════════════════════════════════════════
@teacher_scope_required
@teacher_permission_required(TeacherPermission.FOLLOWUP_SUGGEST)
def teacher_followup_suggest(request):
    scope = request.teacher_scope

    if request.method == 'POST':
        student_id = request.POST.get('student')
        classroom_id = request.POST.get('classroom')
        reason = request.POST.get('reason', '')
        details = request.POST.get('details', '')

        try:
            student = scope.get_student_or_404(student_id)
            classroom = scope.get_class_or_404(classroom_id)

            FollowUpSuggestion.objects.create(
                teacher=request.user,
                student=student,
                classroom=classroom,
                reason=reason,
                details=details,
            )
            messages.success(
                request,
                'پیشنهاد پیگیری ثبت شد و به معاون ارسال خواهد شد.'
            )
        except Exception as e:
            messages.error(request, f'خطا: {e}')

        return redirect('teacher:students')

    students = scope.filter_students()
    classrooms = scope.filter_classes()

    context = {
        'title': 'پیشنهاد پیگیری',
        'students': students,
        'classrooms': classrooms,
    }
    return render(request, 'teacher/followup/suggest.html', context)


# ══════════════════════════════════════════════════════════
#  Assessments
# ══════════════════════════════════════════════════════════
@teacher_scope_required
def teacher_assessments(request):
    scope = request.teacher_scope

    assessments = Assessment.objects.filter(
        teacher=request.user,
    ).select_related('classroom').order_by('-created_at')

    context = {
        'title': 'ارزیابی‌ها',
        'assessments': assessments,
    }
    return render(request, 'teacher/assessments/list.html', context)


@teacher_scope_required
@teacher_permission_required(TeacherPermission.ASSESSMENT_CREATE)
def teacher_assessment_create(request):
    scope = request.teacher_scope
    classrooms = scope.filter_classes()
    questions = scope.filter_questions().filter(is_approved=True)

    if request.method == 'POST':
        title = request.POST.get('title', '')
        classroom_id = request.POST.get('classroom')
        topic = request.POST.get('topic', '')
        duration = int(request.POST.get('duration', 30))

        try:
            classroom = scope.get_class_or_404(classroom_id)
            assessment = Assessment.objects.create(
                title=title,
                teacher=request.user,
                classroom=classroom,
                topic=topic,
                duration_minutes=duration,
            )
            messages.success(request, 'ارزیابی ایجاد شد.')
            return redirect(
                'teacher:assessment_detail',
                assessment_id=assessment.id,
            )
        except Exception as e:
            messages.error(request, f'خطا: {e}')

    context = {
        'title': 'ایجاد ارزیابی',
        'classrooms': classrooms,
        'questions': questions,
    }
    return render(request, 'teacher/assessments/create.html', context)


@teacher_scope_required
def teacher_assessment_detail(request, assessment_id):
    scope = request.teacher_scope
    assessment = scope.get_assessment_or_404(assessment_id)

    questions = assessment.questions.select_related(
        'question'
    ).order_by('order')

    context = {
        'title': assessment.title,
        'assessment': assessment,
        'questions': questions,
    }
    return render(request, 'teacher/assessments/detail.html', context)


@teacher_scope_required
@teacher_permission_required(TeacherPermission.ASSESSMENT_PUBLISH)
def teacher_assessment_publish(request, assessment_id):
    scope = request.teacher_scope
    assessment = scope.get_assessment_or_404(assessment_id)

    if request.method == 'POST':
        if assessment.status != AssessmentStatus.DRAFT:
            messages.error(request, 'فقط پیش‌نویس قابل انتشار است.')
        else:
            assessment.status = AssessmentStatus.PUBLISHED
            assessment.start_time = timezone.now()
            assessment.save()

            TeacherAuditService.log(
                request,
                action='assessment_publish',
                object_type='Assessment',
                object_id=assessment_id,
                classroom=assessment.classroom,
            )
            messages.success(request, 'ارزیابی منتشر شد.')

    return redirect(
        'teacher:assessment_detail', assessment_id=assessment_id
    )


# ══════════════════════════════════════════════════════════
#  Homework
# ══════════════════════════════════════════════════════════
@teacher_scope_required
def teacher_homework(request):
    homeworks = Homework.objects.filter(
        teacher=request.user,
    ).select_related('classroom').order_by('-created_at')

    context = {
        'title': 'تکالیف',
        'homeworks': homeworks,
    }
    return render(request, 'teacher/homework/list.html', context)


@teacher_scope_required
@teacher_permission_required(TeacherPermission.HOMEWORK_CREATE)
def teacher_homework_create(request):
    scope = request.teacher_scope
    classrooms = scope.filter_classes()

    if request.method == 'POST':
        title = request.POST.get('title', '')
        description = request.POST.get('description', '')
        classroom_id = request.POST.get('classroom')
        deadline = request.POST.get('deadline')

        try:
            classroom = scope.get_class_or_404(classroom_id)
            Homework.objects.create(
                title=title,
                description=description,
                teacher=request.user,
                classroom=classroom,
                deadline=deadline,
            )
            messages.success(request, 'تکلیف ایجاد شد.')
            return redirect('teacher:homework')
        except Exception as e:
            messages.error(request, f'خطا: {e}')

    context = {
        'title': 'ایجاد تکلیف',
        'classrooms': classrooms,
    }
    return render(request, 'teacher/homework/create.html', context)


@teacher_scope_required
def teacher_homework_detail(request, homework_id):
    scope = request.teacher_scope
    homework = scope.get_homework_or_404(homework_id)

    submissions = homework.submissions.select_related(
        'student'
    ).order_by('student__last_name')

    context = {
        'title': homework.title,
        'homework': homework,
        'submissions': submissions,
    }
    return render(request, 'teacher/homework/detail.html', context)


# ══════════════════════════════════════════════════════════
#  Analytics
# ══════════════════════════════════════════════════════════
@teacher_scope_required
def teacher_analytics(request):
    scope = request.teacher_scope
    analytics = TeacherAnalyticsService(scope)

    overview = analytics.get_overview()
    classes = scope.filter_classes()

    context = {
        'title': 'تحلیل عملکرد',
        'overview': overview,
        'classes': classes,
    }
    return render(request, 'teacher/analytics/overview.html', context)


@teacher_scope_required
def teacher_class_analytics(request, classroom_id):
    scope = request.teacher_scope
    classroom = scope.get_class_or_404(classroom_id)
    analytics = TeacherAnalyticsService(scope)

    class_analytics = analytics.get_class_analytics(classroom_id)

    context = {
        'title': f'تحلیل کلاس {classroom.name}',
        'classroom': classroom,
        'analytics': class_analytics,
    }
    return render(request, 'teacher/analytics/class.html', context)


@teacher_scope_required
def teacher_topic_analytics(request, classroom_id):
    scope = request.teacher_scope
    classroom = scope.get_class_or_404(classroom_id)
    analytics = TeacherAnalyticsService(scope)

    topic_data = analytics.get_topic_analytics(classroom_id)

    context = {
        'title': f'عملکرد موضوعی - {classroom.name}',
        'classroom': classroom,
        'topic_data': topic_data,
    }
    return render(request, 'teacher/analytics/topics.html', context)


# ══════════════════════════════════════════════════════════
#  Reports
# ══════════════════════════════════════════════════════════
@teacher_scope_required
def teacher_reports(request):
    scope = request.teacher_scope
    analytics = TeacherAnalyticsService(scope)
    overview = analytics.get_overview()

    context = {
        'title': 'گزارش‌ها',
        'overview': overview,
    }
    return render(request, 'teacher/reports/index.html', context)


# ══════════════════════════════════════════════════════════
#  AI
# ══════════════════════════════════════════════════════════
@teacher_scope_required
def teacher_ai(request):
    scope = request.teacher_scope
    from dashboard.models import AIGenerationJob

    jobs = AIGenerationJob.objects.filter(
        teacher=request.user,
    ).order_by('-created_at')[:10]

    context = {
        'title': 'دستیار هوشمند',
        'jobs': jobs,
    }
    return render(request, 'teacher/ai/index.html', context)


# ══════════════════════════════════════════════════════════
#  Questions (بانک سوال)
# ══════════════════════════════════════════════════════════
@teacher_scope_required
def teacher_questions(request):
    """بانک سوال معلم"""
    scope = request.teacher_scope
    questions = scope.filter_questions().select_related(
        'classroom', 'session', 'ai_job', 'created_by'
    ).order_by('-created_at')

    # فیلترها
    classroom_filter = request.GET.get('classroom', '')
    source_filter = request.GET.get('source', '')
    status_filter = request.GET.get('review_status', '')
    search_query = request.GET.get('q', '')

    if classroom_filter:
        questions = questions.filter(classroom_id=classroom_filter)
    if source_filter:
        questions = questions.filter(source=source_filter)
    if status_filter:
        questions = questions.filter(review_status=status_filter)
    if search_query:
        questions = questions.filter(
            Q(text__icontains=search_query) |
            Q(topic__icontains=search_query)
        )

    classrooms = scope.filter_classes()

    context = {
        'title': 'بانک سوالات',
        'questions': questions,
        'classrooms': classrooms,
        'classroom_filter': classroom_filter,
        'source_filter': source_filter,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_count': questions.count(),
    }
    return render(request, 'teacher/questions/list.html', context)


@teacher_scope_required
@teacher_permission_required(TeacherPermission.QUESTION_CREATE)
def teacher_question_create(request):
    """ساخت سوال دستی"""
    scope = request.teacher_scope
    classrooms = scope.filter_classes()

    if request.method == 'POST':
        classroom_id = request.POST.get('classroom')
        text = request.POST.get('text', '')
        choice_a = request.POST.get('choice_a', '')
        choice_b = request.POST.get('choice_b', '')
        choice_c = request.POST.get('choice_c', '')
        choice_d = request.POST.get('choice_d', '')
        correct_answer = request.POST.get('correct_answer', 'a')
        topic = request.POST.get('topic', '')
        timer = request.POST.get('timer_seconds', '300')

        try:
            classroom = scope.get_class_or_404(classroom_id)
            Question.objects.create(
                classroom=classroom,
                created_by=request.user,
                source='manual',
                is_approved=True,
                review_status='approved',
                topic=topic,
                text=text,
                choice_a=choice_a,
                choice_b=choice_b,
                choice_c=choice_c,
                choice_d=choice_d,
                correct_answer=correct_answer,
                timer_seconds=int(timer),
            )
            messages.success(request, 'سوال با موفقیت ایجاد شد.')
            return redirect('teacher:questions')
        except Exception as e:
            messages.error(request, f'خطا در ایجاد سوال: {e}')

    context = {
        'title': 'ساخت سوال دستی',
        'classrooms': classrooms,
    }
    return render(request, 'teacher/questions/form.html', context)


@teacher_scope_required
@teacher_permission_required(TeacherPermission.QUESTION_CREATE)
def teacher_question_edit(request, pk):
    """ویرایش سوال"""
    scope = request.teacher_scope
    question = scope.get_question_or_404(pk)

    if request.method == 'POST':
        question.text = request.POST.get('text', question.text)
        question.choice_a = request.POST.get('choice_a', question.choice_a)
        question.choice_b = request.POST.get('choice_b', question.choice_b)
        question.choice_c = request.POST.get('choice_c', question.choice_c)
        question.choice_d = request.POST.get('choice_d', question.choice_d)
        question.correct_answer = request.POST.get('correct_answer', question.correct_answer)
        question.topic = request.POST.get('topic', question.topic)
        question.timer_seconds = int(request.POST.get('timer_seconds', question.timer_seconds))
        question.save()

        messages.success(request, 'سوال با موفقیت ویرایش شد.')
        return redirect('teacher:questions')

    classrooms = scope.filter_classes()
    context = {
        'title': 'ویرایش سوال',
        'question': question,
        'classrooms': classrooms,
    }
    return render(request, 'teacher/questions/form.html', context)


@teacher_scope_required
@teacher_permission_required(TeacherPermission.QUESTION_DELETE)
def teacher_question_delete(request, pk):
    """حذف سوال"""
    scope = request.teacher_scope
    question = scope.get_question_or_404(pk)

    if request.method == 'POST':
        TeacherAuditService.log(
            request,
            action='question_delete',
            object_type='Question',
            object_id=question.id,
            reason='حذف سوال توسط معلم',
            classroom=question.classroom,
        )
        question.delete()
        messages.success(request, 'سوال حذف شد.')
        return redirect('teacher:questions')

    context = {
        'title': 'حذف سوال',
        'question': question,
    }
    return render(request, 'teacher/questions/confirm_delete.html', context)


# ══════════════════════════════════════════════════════════
#  Homework Grade (تصحیح تکلیف)
# ══════════════════════════════════════════════════════════
@teacher_scope_required
@teacher_permission_required(TeacherPermission.HOMEWORK_GRADE)
def teacher_homework_grade(request, homework_id):
    """تصحیح تکلیف"""
    scope = request.teacher_scope
    homework = scope.get_homework_or_404(homework_id)

    from .models import HomeworkSubmission
    from .constants import SubmissionStatus

    # دریافت ارسال خاص از کوئری پارامتر
    submission_id = request.GET.get('submission')
    if submission_id:
        submission = get_object_or_404(
            HomeworkSubmission,
            id=submission_id,
            homework=homework,
        )
    else:
        # اولین ارسال بدون نمره
        submission = HomeworkSubmission.objects.filter(
            homework=homework,
            score__isnull=True,
        ).exclude(
            status=SubmissionStatus.NOT_SUBMITTED
        ).first()

    if request.method == 'POST':
        if not submission:
            messages.error(request, 'ارسالی برای تصحیح یافت نشد.')
            return redirect('teacher:homework_detail', homework_id=homework_id)

        score = request.POST.get('score', '')
        feedback = request.POST.get('feedback', '')

        if not score:
            messages.error(request, 'نمره الزامی است.')
        else:
            try:
                score_val = float(score)
                if score_val > homework.max_score:
                    messages.error(
                        request,
                        f'نمره نمی‌تواند بیشتر از {homework.max_score} باشد.'
                    )
                else:
                    submission.score = score_val
                    submission.feedback = feedback
                    submission.status = SubmissionStatus.REVIEWED
                    submission.reviewed_by = request.user
                    submission.reviewed_at = timezone.now()
                    submission.save()

                    TeacherAuditService.log(
                        request,
                        action='homework_grade',
                        object_type='HomeworkSubmission',
                        object_id=submission.id,
                        new_values={'score': score_val},
                        classroom=homework.classroom,
                    )

                    messages.success(request, 'نمره ثبت شد.')
            except ValueError:
                messages.error(request, 'نمره باید عدد باشد.')

        return redirect('teacher:homework_detail', homework_id=homework_id)

    context = {
        'title': f'تصحیح - {homework.title}',
        'homework': homework,
        'submission': submission,
        'max_score': homework.max_score,
    }
    return render(request, 'teacher/homework/grade.html', context)


# ══════════════════════════════════════════════════════════
#  ویوهای منتقل‌شده از dashboard
# ══════════════════════════════════════════════════════════
from django.db.models import Count, Q, Prefetch
from django.http import JsonResponse
from datetime import datetime, timedelta
from dashboard.forms import (
    AIGenerationForm,
    AttendanceRequestForm,
    SelectQuestionsForm,
    StartSessionForm,
)
from dashboard.services import (
    generate_questions_for_job,
    regenerate_rejected_question,
)
from accounts.models import StudentProfile


@teacher_scope_required
def teacher_weekly_schedule(request):
    """برنامه هفتگی معلم"""
    scope = request.teacher_scope
    from dashboard.models import WeeklySchedule
    schedules = WeeklySchedule.objects.filter(
        classroom__teacher=request.user
    ).select_related('classroom').order_by('day_of_week', 'start_time')

    days_info = [
        ('saturday', 'شنبه'), ('sunday', 'یکشنبه'),
        ('monday', 'دوشنبه'), ('tuesday', 'سه‌شنبه'),
        ('wednesday', 'چهارشنبه'),
    ]
    schedule_days = []
    for day_key, day_name in days_info:
        day_classes = [s for s in schedules if s.day_of_week == day_key]
        schedule_days.append({
            'key': day_key, 'name': day_name,
            'classes': day_classes, 'count': len(day_classes),
        })

    context = {
        'title': 'برنامه هفتگی من',
        'schedule_days': schedule_days,
        'total_sessions': schedules.count(),
        'total_classrooms': schedules.values('classroom').distinct().count(),
    }
    return render(request, 'teacher/schedule/weekly.html', context)


@teacher_scope_required
def teacher_create_attendance_request(request, classroom_id, session_id):
    """ایجاد درخواست حضور و غیاب / سوال"""
    scope = request.teacher_scope
    classroom = scope.get_class_or_404(classroom_id)
    session = scope.get_session_or_404(session_id)

    if classroom.students.count() == 0:
        messages.error(request, 'این کلاس هیچ دانش‌آموزی ندارد.')
        return redirect('teacher:class_detail', classroom_id=classroom.id)

    if request.method == 'POST':
        form = AttendanceRequestForm(request.POST)
        questions_form = SelectQuestionsForm(request.POST, classroom=classroom)
        request_type = request.POST.get('request_type', 'face_only')

        if form.is_valid():
            if request_type in ('question_only', 'face_and_question'):
                if not questions_form.is_valid():
                    messages.error(request, 'لطفاً حداقل یک سوال انتخاب کنید.')
                    return redirect(request.path)
                selected_questions = questions_form.cleaned_data['questions']
            else:
                selected_questions = []

            attendance_request = form.save(commit=False)
            attendance_request.teacher = request.user
            attendance_request.classroom = classroom
            attendance_request.session = session
            attendance_request.save()

            if selected_questions:
                from dashboard.models import AttendanceRequestQuestion
                for index, question in enumerate(selected_questions, 1):
                    AttendanceRequestQuestion.objects.create(
                        attendance_request=attendance_request,
                        question=question,
                        order=index,
                        timer_seconds=question.timer_seconds
                    )

            messages.success(request, f'درخواست با موفقیت ایجاد شد.')
            return redirect('teacher:teacher_request_results', request_id=attendance_request.id)
    else:
        form = AttendanceRequestForm()
        questions_form = SelectQuestionsForm(classroom=classroom)

    context = {
        'title': 'ایجاد درخواست حضور / سوال',
        'form': form,
        'questions_form': questions_form,
        'classroom': classroom,
        'session': session,
    }
    return render(request, 'teacher/sessions/request_form.html', context)


@teacher_scope_required
def teacher_request_results(request, request_id):
    """نتایج یک درخواست"""
    scope = request.teacher_scope
    attendance_request = scope.get_attendance_request_or_404(request_id)

    from dashboard.models import StudentAnswer
    responses = attendance_request.responses.select_related(
        'student', 'student__profile'
    ).order_by('student__last_name')

    total_students = responses.count()
    present_count = responses.filter(final_status='present').count()
    absent_count = responses.filter(final_status='absent').count()
    pending_count = responses.filter(final_status='pending').count()

    request_questions = attendance_request.request_questions.select_related(
        'question'
    ).order_by('order')

    questions_stats = []
    for rq in request_questions:
        question = rq.question
        answers = StudentAnswer.objects.filter(
            attendance_request=attendance_request,
            question=question
        )
        total_answers = answers.count()
        correct_count = answers.filter(is_correct=True).count()
        wrong_count = total_answers - correct_count
        no_answer_count = total_students - total_answers
        questions_stats.append({
            'request_question': rq,
            'question': question,
            'total_answers': total_answers,
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'no_answer_count': no_answer_count,
        })

    students_detail = []
    for response in responses:
        student = response.student
        student_answers = StudentAnswer.objects.filter(
            attendance_request=attendance_request,
            student=student
        ).select_related('question')
        students_detail.append({
            'response': response,
            'student': student,
            'correct': student_answers.filter(is_correct=True).count(),
            'wrong': student_answers.filter(is_correct=False).count(),
            'total': student_answers.count(),
            'answers': student_answers,
        })

    context = {
        'title': f'نتایج درخواست {request_id}',
        'attendance_request': attendance_request,
        'classroom': attendance_request.classroom,
        'session': attendance_request.session,
        'total_students': total_students,
        'present_count': present_count,
        'absent_count': absent_count,
        'pending_count': pending_count,
        'request_questions': request_questions,
        'questions_stats': questions_stats,
        'students_detail': students_detail,
    }
    return render(request, 'teacher/sessions/request_results.html', context)


@teacher_scope_required
def teacher_finish_request(request, request_id):
    """پایان دادن به درخواست"""
    scope = request.teacher_scope
    attendance_request = scope.get_attendance_request_or_404(request_id)

    if request.method == 'POST' and attendance_request.status == 'active':
        for response in attendance_request.responses.filter(auto_status='pending'):
            response.mark_no_response()
        attendance_request.status = 'finished'
        attendance_request.save()
        messages.success(request, 'درخواست با موفقیت پایان یافت.')

    return redirect('teacher:teacher_request_results', request_id=request_id)


@teacher_scope_required
def teacher_ai_new(request):
    """صفحه تولید سوال با هوش مصنوعی"""
    scope = request.teacher_scope
    classrooms = scope.filter_classes()

    if request.method == 'POST':
        form = AIGenerationForm(request.POST, teacher=request.user)
        if form.is_valid():
            job = form.save(commit=False)
            job.teacher = request.user
            job.status = 'pending'
            job.save()

            generated_count = generate_questions_for_job(job)
            job.refresh_from_db()

            if job.status == 'completed':
                if generated_count > 0:
                    messages.success(request, f'{generated_count} سوال تولید شد.')
                else:
                    messages.warning(request, f'هشدار: {job.error_message}')
            else:
                messages.error(request, f'خطا: {job.error_message}')

            return redirect('teacher:teacher_ai_review', job_id=job.id)
    else:
        form = AIGenerationForm(teacher=request.user)

    context = {
        'title': 'تولید سوال با هوش مصنوعی',
        'form': form,
        'classrooms': classrooms,
    }
    return render(request, 'teacher/ai/generate_form.html', context)


@teacher_scope_required
def teacher_ai_review(request, job_id):
    """بررسی سوالات تولیدشده"""
    scope = request.teacher_scope
    from dashboard.models import AIGenerationJob
    job = get_object_or_404(AIGenerationJob, id=job_id, teacher=request.user)
    questions = job.generated_questions.all().order_by('id')

    context = {
        'title': 'بررسی سوالات تولیدشده',
        'job': job,
        'questions': questions,
        'pending_count': questions.filter(review_status='pending').count(),
        'approved_count': questions.filter(review_status='approved').count(),
        'rejected_count': questions.filter(review_status='rejected').count(),
    }
    return render(request, 'teacher/ai/review.html', context)


@teacher_scope_required
def teacher_ai_regenerate_rejected(request, job_id):
    """تولید مجدد سوالات ردشده"""
    scope = request.teacher_scope
    from dashboard.models import AIGenerationJob
    job = get_object_or_404(AIGenerationJob, id=job_id, teacher=request.user)

    if request.method == 'POST':
        rejected_questions = job.generated_questions.filter(review_status='rejected')
        regenerated_count = 0
        for question in rejected_questions:
            if regenerate_rejected_question(job, question):
                regenerated_count += 1
        if regenerated_count > 0:
            messages.success(request, f'{regenerated_count} سوال تولید شد.')
        else:
            messages.info(request, 'سوال ردشده‌ای وجود ندارد.')

    return redirect('teacher:teacher_ai_review', job_id=job.id)


@teacher_scope_required
def teacher_ai_question_approve(request, pk):
    """تایید سوال"""
    scope = request.teacher_scope
    question = scope.get_question_or_404(pk)
    if request.method == 'POST':
        question.review_status = 'approved'
        question.is_approved = True
        question.save()
        messages.success(request, 'سوال تایید شد.')
    return redirect('teacher:teacher_ai_review', job_id=question.ai_job.id)


@teacher_scope_required
def teacher_ai_question_reject(request, pk):
    """رد سوال"""
    scope = request.teacher_scope
    question = scope.get_question_or_404(pk)
    if request.method == 'POST':
        question.review_status = 'rejected'
        question.is_approved = False
        question.save()
        messages.warning(request, 'سوال رد شد.')
    return redirect('teacher:teacher_ai_review', job_id=question.ai_job.id)


@teacher_scope_required
def teacher_ai_question_reject_and_regenerate(request, pk):
    """رد و تولید مجدد"""
    scope = request.teacher_scope
    question = scope.get_question_or_404(pk)
    if request.method == 'POST':
        job = question.ai_job
        success = regenerate_rejected_question(job, question)
        if success:
            messages.success(request, 'سوال رد شد و جایگزین تولید شد.')
        else:
            messages.error(request, 'تولید جایگزین ناموفق بود.')
        return redirect('teacher:teacher_ai_review', job_id=job.id)
    return redirect('teacher:teacher_ai_review', job_id=question.ai_job.id)


@teacher_scope_required
def teacher_participation_stats(request):
    """آمار مشارکت"""
    scope = request.teacher_scope
    classrooms = scope.filter_classes()
    context = {
        'title': 'آمار مشارکت',
        'classrooms': classrooms,
    }
    return render(request, 'teacher/analytics/participation.html', context)


@teacher_scope_required
def teacher_session_detail_stats(request, session_id):
    """آمار یک جلسه"""
    scope = request.teacher_scope
    session = scope.get_session_or_404(session_id)
    classroom = session.classroom
    students = classroom.students.all().order_by('last_name')

    context = {
        'title': f'آمار جلسه {session.id}',
        'session': session,
        'classroom': classroom,
        'students': students,
    }
    return render(request, 'teacher/analytics/session_detail.html', context)


@teacher_scope_required
def teacher_period_stats(request, classroom_id):
    """آمار هفتگی/ماهانه"""
    scope = request.teacher_scope
    classroom = scope.get_class_or_404(classroom_id)
    period = request.GET.get('period', 'weekly')

    context = {
        'title': f'آمار {period}',
        'classroom': classroom,
        'period': period,
    }
    return render(request, 'teacher/analytics/period_stats.html', context)


@teacher_scope_required
def teacher_attendance(request):
    """لیست درخواست‌های حضور"""
    scope = request.teacher_scope
    requests_qs = scope.filter_attendance_requests().select_related(
        'classroom', 'session'
    ).order_by('-created_at')[:30]

    context = {
        'title': 'حضور و غیاب',
        'attendance_requests': requests_qs,
    }
    return render(request, 'teacher/attendance/list.html', context)


@teacher_scope_required
def teacher_attendance_detail(request, request_id):
    """جزئیات درخواست حضور"""
    scope = request.teacher_scope
    att_request = scope.get_attendance_request_or_404(request_id)
    responses = att_request.responses.select_related('student').order_by('student__last_name')

    context = {
        'title': f'جزئیات حضور {request_id}',
        'attendance_request': att_request,
        'responses': responses,
    }
    return render(request, 'teacher/attendance/detail.html', context)


@teacher_scope_required
def teacher_attendance_correct(request, response_id):
    """اصلاح وضعیت حضور"""
    scope = request.teacher_scope
    response = scope.get_attendance_response_or_404(response_id)

    if request.method == 'POST':
        new_status = request.POST.get('new_status')
        reason = request.POST.get('reason', '')
        if new_status in ('present', 'absent') and reason.strip():
            response.final_status = new_status
            response.reviewed_by = request.user
            response.reviewed_at = timezone.now()
            response.save()
            messages.success(request, 'وضعیت حضور اصلاح شد.')
            return redirect('teacher:attendance_detail', request_id=response.attendance_request_id)
        else:
            messages.error(request, 'وضعیت و دلیل الزامی است.')

    context = {
        'title': 'اصلاح وضعیت حضور',
        'response': response,
    }
    return render(request, 'teacher/attendance/correct.html', context)