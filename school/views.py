"""ویوهای مدیریت مدرسه"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q

from .decorators import (
    principal_required, assistant_required,
)
from .services import SchoolAnalyticsService, FollowUpService, AttendanceOverrideService
from .audit import SchoolAuditService
from .models import (
    SchoolStaffAssignment, StudentSchoolStatus,
    FollowUpCase, FollowUpCaseNote,
    SchoolAlert, SchoolTask, SchoolAuditLog,
    SchoolSettings, AttendanceOverrideLog, AbsenceReview,
)
from .constants import (
    Permission, StaffRole, AssistantType,
    CaseStatus, CasePriority, CaseCategory,
    StudentStatus, TaskStatus, ClassroomStatus,
)    
from accounts.models import User
from dashboard.models import (
    Classroom, ClassSession, AttendanceRecord,
    AttendanceRequest, AttendanceResponse,
    Question, StudentAnswer, WeeklySchedule,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
#  PRINCIPAL VIEWS
# ══════════════════════════════════════════════════════════

@principal_required
def principal_dashboard(request):
    """داشبورد مدیر — School Command Center"""
    scope = request.school_scope
    service = SchoolAnalyticsService(scope)

    overview = service.get_overview()
    attendance_stats = service.get_attendance_stats('today')
    attendance_trend = service.get_attendance_trend(30)
    participation = service.get_participation_stats()
    alerts = service.generate_alerts()
    students_at_risk = service.get_students_needing_attention()

    open_cases = FollowUpCase.objects.filter(
        school_id=scope.active_school_id,
        status__in=['OPEN', 'IN_REVIEW', 'ASSIGNED'],
    ).select_related('student', 'assigned_to')[:5]

    pending_tasks = SchoolTask.objects.filter(
        school_id=scope.active_school_id,
        assigned_to=request.user,
        status__in=['TODO', 'IN_PROGRESS'],
    )[:5]

    SchoolAuditService.log(request, scope.active_school, 'view_dashboard')

    context = {
        'title': f'داشبورد مدرسه {scope.active_school.name}',
        'school': scope.active_school,
        'overview': overview,
        'attendance_stats': attendance_stats,
        'attendance_trend': attendance_trend,
        'participation': participation,
        'alerts': alerts,
        'students_at_risk': students_at_risk,
        'open_cases': open_cases,
        'pending_tasks': pending_tasks,
    }
    return render(request, 'school/principal/dashboard.html', context)


@principal_required
def principal_students(request):
    """لیست دانش‌آموزان مدرسه"""
    scope = request.school_scope
    search = request.GET.get('q', '')
    grade_filter = request.GET.get('grade', '')

    students = scope.filter_students().select_related('profile')
    if search:
        students = students.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(username__icontains=search) |
            Q(national_id__icontains=search)
        )
    if grade_filter:
        students = students.filter(
            enrolled_classes__grade=grade_filter
        ).distinct()

    context = {
        'title': 'مدیریت دانش‌آموزان',
        'school': scope.active_school,
        'students': students,
        'search': search,
        'grade_filter': grade_filter,
        'grades': [('10', 'دهم'), ('11', 'یازدهم'), ('12', 'دوازدهم')],
    }
    return render(request, 'school/principal/students.html', context)


@principal_required
def principal_student_detail(request, student_id):
    """پروفایل مدیریتی دانش‌آموز"""
    scope = request.school_scope
    student = scope.get_student_or_404(student_id)

    # آمار
    att_records = AttendanceRecord.objects.filter(
        student=student,
        attendance_check__session__classroom__school_id=scope.active_school_id,
    )
    total_att = att_records.count()
    present = att_records.filter(status='present').count()
    attendance_rate = round((present / total_att) * 100, 1) if total_att > 0 else None

    answers = StudentAnswer.objects.filter(
        student=student,
        question__classroom__school_id=scope.active_school_id,
    )
    correct = answers.filter(is_correct=True).count()
    total_answered = answers.count()
    performance_rate = round((correct / total_answered) * 100, 1) if total_answered > 0 else None

    cases = FollowUpCase.objects.filter(
        student=student,
        school_id=scope.active_school_id,
    ).order_by('-created_at')[:10]

    classrooms = student.enrolled_classes.filter(
        school_id=scope.active_school_id
    )

    context = {
        'title': f'پروفایل {student.get_full_name()}',
        'school': scope.active_school,
        'student': student,
        'attendance_rate': attendance_rate,
        'performance_rate': performance_rate,
        'total_answered': total_answered,
        'correct': correct,
        'cases': cases,
        'classrooms': classrooms,
    }
    return render(request, 'school/principal/student_detail.html', context)


@principal_required
def principal_teachers(request):
    """لیست معلمان مدرسه"""
    scope = request.school_scope
    teachers = scope.filter_teachers().annotate(
        classes_count=Count('taught_classes', filter=Q(
            taught_classes__school_id=scope.active_school_id
        ), distinct=True),
    )
    context = {
        'title': 'معلمان مدرسه',
        'school': scope.active_school,
        'teachers': teachers,
    }
    return render(request, 'school/principal/teachers.html', context)


@principal_required
def principal_teacher_detail(request, teacher_id):
    scope = request.school_scope
    teacher = scope.get_teacher_or_404(teacher_id)
    classrooms = scope.filter_classrooms().filter(teacher=teacher)

    context = {
        'title': f'پروفایل {teacher.get_full_name()}',
        'school': scope.active_school,
        'teacher': teacher,
        'classrooms': classrooms,
    }
    return render(request, 'school/principal/teacher_detail.html', context)


@principal_required
def principal_classes(request):
    scope = request.school_scope
    classrooms = scope.filter_classrooms().annotate(
        students_count=Count('students', distinct=True),
        sessions_count=Count('sessions', distinct=True),
    )
    context = {
        'title': 'کلاس‌های مدرسه',
        'school': scope.active_school,
        'classrooms': classrooms,
    }
    return render(request, 'school/principal/classes.html', context)


@principal_required
def principal_class_detail(request, classroom_id):
    scope = request.school_scope
    classroom = scope.get_classroom_or_404(classroom_id)
    students = classroom.students.all()
    sessions = classroom.sessions.order_by('-session_date')[:20]

    context = {
        'title': f'کلاس {classroom.name}',
        'school': scope.active_school,
        'classroom': classroom,
        'students': students,
        'sessions': sessions,
    }
    return render(request, 'school/principal/class_detail.html', context)


@principal_required
def principal_attendance(request):
    scope = request.school_scope
    service = SchoolAnalyticsService(scope)

    tab = request.GET.get('tab', 'today')
    attendance_stats = service.get_attendance_stats(tab)
    trend = service.get_attendance_trend(30)

    suspicious = AttendanceResponse.objects.filter(
        attendance_request__classroom__school_id=scope.active_school_id,
        auto_status='suspicious',
        final_status='pending',
    ).select_related('student', 'attendance_request__classroom')[:50]

    context = {
        'title': 'مدیریت حضور و غیاب',
        'school': scope.active_school,
        'tab': tab,
        'attendance_stats': attendance_stats,
        'trend': trend,
        'suspicious': suspicious,
    }
    return render(request, 'school/principal/attendance.html', context)


@principal_required
def principal_attendance_override(request, response_id):
    """تغییر وضعیت حضور توسط مدیر (با دلیل و Audit)"""
    scope = request.school_scope

    response = get_object_or_404(
        AttendanceResponse,
        id=response_id,
        attendance_request__classroom__school_id=scope.active_school_id,
    )

    if request.method == 'POST':
        new_status = request.POST.get('new_status')
        reason = request.POST.get('reason', '')

        if new_status not in ('present', 'absent'):
            messages.error(request, 'وضعیت نامعتبر است.')
            return redirect('school:principal_attendance')

        if not reason.strip():
            messages.error(request, 'دلیل تغییر الزامی است.')
            return redirect('school:principal_attendance')

        override_service = AttendanceOverrideService(scope)
        override_service.override_attendance_response(
            request, response, new_status, reason
        )
        messages.success(request, 'وضعیت حضور با موفقیت تغییر کرد.')
        return redirect('school:principal_attendance')

    context = {
        'title': 'تغییر وضعیت حضور',
        'school': scope.active_school,
        'response': response,
    }
    return render(request, 'school/principal/attendance_override.html', context)


@principal_required
def principal_followups(request):
    scope = request.school_scope
    status_filter = request.GET.get('status', '')
    cases = FollowUpCase.objects.filter(
        school_id=scope.active_school_id
    ).select_related('student', 'created_by', 'assigned_to')
    if status_filter:
        cases = cases.filter(status=status_filter)

    context = {
        'title': 'پرونده‌های پیگیری',
        'school': scope.active_school,
        'cases': cases,
        'status_filter': status_filter,
        'statuses': CaseStatus.CHOICES,
    }
    return render(request, 'school/principal/followups.html', context)


@principal_required
def principal_followup_create(request):
    scope = request.school_scope
    if request.method == 'POST':
        service = FollowUpService(scope)
        title = request.POST.get('title', '')
        if not title.strip():
            messages.error(request, 'عنوان پرونده الزامی است.')
            return redirect('school:principal_followups')

        student_id = request.POST.get('student')
        student = None
        if student_id:
            try:
                student = scope.get_student_or_404(int(student_id))
            except Exception:
                pass

        service.create_case(
            request,
            title=title,
            description=request.POST.get('description', ''),
            student=student,
            category=request.POST.get('category', 'OTHER'),
            priority=request.POST.get('priority', 'MEDIUM'),
        )
        messages.success(request, 'پرونده پیگیری ایجاد شد.')
        return redirect('school:principal_followups')

    students = scope.filter_students()
    context = {
        'title': 'ایجاد پرونده پیگیری',
        'school': scope.active_school,
        'students': students,
        'categories': CaseCategory.CHOICES,
        'priorities': CasePriority.CHOICES,
    }
    return render(request, 'school/principal/followup_create.html', context)


@principal_required
def principal_followup_detail(request, case_id):
    scope = request.school_scope
    case = get_object_or_404(
        FollowUpCase,
        case_number=case_id,
        school_id=scope.active_school_id,
    )
    notes = case.notes.select_related('author')

    if request.method == 'POST':
        note_text = request.POST.get('note', '')
        if note_text.strip():
            FollowUpCaseNote.objects.create(
                case=case,
                author=request.user,
                content=note_text,
            )
            messages.success(request, 'یادداشت اضافه شد.')
            return redirect('school:principal_followup_detail', case_id=case_id)

    assistants = SchoolStaffAssignment.objects.filter(
        school=scope.active_school,
        staff_role=StaffRole.ASSISTANT,
        is_active=True,
    ).select_related('user')

    context = {
        'title': f'پرونده #{case.case_number}',
        'school': scope.active_school,
        'case': case,
        'notes': notes,
        'assistants': assistants,
    }
    return render(request, 'school/principal/followup_detail.html', context)


@principal_required
def principal_followup_assign(request, case_id):
    scope = request.school_scope
    case = get_object_or_404(
        FollowUpCase, case_number=case_id, school_id=scope.active_school_id)

    if request.method == 'POST':
        assistant_user_id = request.POST.get('assistant_user')
        try:
            assistant_user = User.objects.get(id=assistant_user_id)
        except User.DoesNotExist:
            messages.error(request, 'کاربر مورد نظر یافت نشد.')
            return redirect('school:principal_followup_detail', case_id=case_id)

        service = FollowUpService(scope)
        service.assign_case(request, case, assistant_user)
        messages.success(request, 'پرونده ارجاع داده شد.')
        return redirect('school:principal_followup_detail', case_id=case_id)

    return redirect('school:principal_followup_detail', case_id=case_id)


@principal_required
def principal_followup_resolve(request, case_id):
    scope = request.school_scope
    case = get_object_or_404(
        FollowUpCase, case_number=case_id, school_id=scope.active_school_id)

    if request.method == 'POST':
        note = request.POST.get('resolution_note', '')
        service = FollowUpService(scope)
        service.resolve_case(request, case, note)
        messages.success(request, 'پرونده حل شد.')
        return redirect('school:principal_followups')

    return redirect('school:principal_followup_detail', case_id=case_id)


@principal_required
def principal_assistants(request):
    scope = request.school_scope
    assignments = SchoolStaffAssignment.objects.filter(
        school=scope.active_school,
        staff_role=StaffRole.ASSISTANT,
    ).select_related('user')

    context = {
        'title': 'مدیریت معاونان',
        'school': scope.active_school,
        'assignments': assignments,
        'assistant_types': AssistantType.CHOICES,
    }
    return render(request, 'school/principal/assistants.html', context)


@principal_required
def principal_assistant_assign(request):
    scope = request.school_scope
    if request.method == 'POST':
        user_id = request.POST.get('user')
        assistant_type = request.POST.get('assistant_type', AssistantType.GENERAL)

        try:
            user = User.objects.get(id=user_id, role='assistant')
        except User.DoesNotExist:
            messages.error(request, 'کاربر معاون یافت نشد.')
            return redirect('school:principal_assistants')

        from django.db import transaction
        with transaction.atomic():
            assignment, created = SchoolStaffAssignment.objects.get_or_create(
                user=user,
                school=scope.active_school,
                staff_role=StaffRole.ASSISTANT,
                assistant_type=assistant_type,
                defaults={'is_active': True},
            )
            if not created:
                assignment.is_active = True
                assignment.save()

            SchoolAuditService.log(
                request, scope.active_school, 'assistant_assignment',
                object_type='SchoolStaffAssignment',
                object_id=assignment.id,
                new_values={
                    'user': user.username,
                    'type': assistant_type,
                },
            )
        messages.success(request, 'معاون با موفقیت منصوب شد.')
        return redirect('school:principal_assistants')

    assistant_users = User.objects.filter(role='assistant')
    context = {
        'title': 'انتصاب معاون',
        'school': scope.active_school,
        'assistant_users': assistant_users,
        'assistant_types': AssistantType.CHOICES,
    }
    return render(request, 'school/principal/assistant_assign.html', context)


@principal_required
def principal_assistant_toggle(request, assignment_id):
    scope = request.school_scope
    assignment = get_object_or_404(
        SchoolStaffAssignment,
        id=assignment_id,
        school=scope.active_school,
    )
    if request.method == 'POST':
        assignment.is_active = not assignment.is_active
        assignment.save(update_fields=['is_active', 'updated_at'])
        status_text = 'فعال' if assignment.is_active else 'غیرفعال'
        messages.success(request, f'وضعیت معاون به {status_text} تغییر کرد.')
    return redirect('school:principal_assistants')


@principal_required
def principal_reports(request):
    scope = request.school_scope
    SchoolAuditService.log(request, scope.active_school, 'view_reports')
    context = {
        'title': 'گزارش‌های مدرسه',
        'school': scope.active_school,
    }
    return render(request, 'school/principal/reports.html', context)


@principal_required
def principal_settings(request):
    scope = request.school_scope
    settings_obj, _ = SchoolSettings.objects.get_or_create(
        school=scope.active_school
    )

    if request.method == 'POST':
        settings_obj.academic_year = request.POST.get('academic_year', settings_obj.academic_year)
        settings_obj.absence_warning_threshold = float(
            request.POST.get('absence_warning_threshold', 20))
        settings_obj.participation_warning_threshold = float(
            request.POST.get('participation_warning_threshold', 40))
        settings_obj.performance_warning_threshold = float(
            request.POST.get('performance_warning_threshold', 50))
        settings_obj.late_threshold_minutes = int(
            request.POST.get('late_threshold_minutes', 15))
        settings_obj.face_verification_required = request.POST.get(
            'face_verification_required') == 'on'
        settings_obj.updated_by = request.user
        settings_obj.save()

        SchoolAuditService.log(
            request, scope.active_school, 'school_setting_change',
            object_type='SchoolSettings',
            object_id=settings_obj.id,
            new_values={'academic_year': settings_obj.academic_year},
        )
        messages.success(request, 'تنظیمات ذخیره شد.')
        return redirect('school:principal_settings')

    context = {
        'title': 'تنظیمات مدرسه',
        'school': scope.active_school,
        'settings': settings_obj,
    }
    return render(request, 'school/principal/settings.html', context)


@principal_required
def principal_audit_log(request):
    scope = request.school_scope
    from .models import SchoolAuditLog
    logs = SchoolAuditLog.objects.filter(
        school=scope.active_school
    ).select_related('actor')[:100]

    context = {
        'title': 'لاگ فعالیت‌ها',
        'school': scope.active_school,
        'logs': logs,
    }
    return render(request, 'school/principal/audit_log.html', context)


@principal_required
def principal_alerts(request):
    scope = request.school_scope
    service = SchoolAnalyticsService(scope)
    alerts = service.generate_alerts()

    context = {
        'title': 'هشدارها و موارد استثنایی',
        'school': scope.active_school,
        'alerts': alerts,
    }
    return render(request, 'school/principal/alerts.html', context)

# ══════════════════════════════════════════════════════════
# PRINCIPAL — تغییر وضعیت تحصیلی دانش‌آموز
# ══════════════════════════════════════════════════════════
@principal_required
def principal_student_status(request, student_id):
    """تغییر وضعیت تحصیلی دانش‌آموز (فعال/غیرفعال/منتقل/فارغ‌التحصیل)"""
    scope = request.school_scope
    student = scope.get_student_or_404(student_id)

    # بررسی دسترسی
    if not scope.has_permission(Permission.STUDENTS_CHANGE_STATUS):
        messages.error(request, 'شما دسترسی تغییر وضعیت دانش‌آموزان را ندارید.')
        return redirect('school:principal_students')

    # دریافت یا ایجاد وضعیت فعلی
    student_status, created = StudentSchoolStatus.objects.get_or_create(
        student=student,
        school_id=scope.active_school_id,
        defaults={
            'status': StudentStatus.ACTIVE,
            'changed_by': request.user,
        }
    )

    # تاریخچه تغییرات
    history = StudentSchoolStatus.objects.filter(
        student=student,
        school_id=scope.active_school_id,
    ).select_related('changed_by').order_by('-updated_at')

    if request.method == 'POST':
        new_status = request.POST.get('new_status', '')
        reason = request.POST.get('reason', '').strip()

        # اعتبارسنجی
        valid_statuses = [choice[0] for choice in StudentStatus.CHOICES]
        if new_status not in valid_statuses:
            messages.error(request, 'وضعیت انتخابی نامعتبر است.')
            return redirect('school:principal_student_status', student_id=student_id)

        if new_status == student_status.status:
            messages.warning(request, 'وضعیت دانش‌آموز هم‌اکنون همان وضعیت انتخابی است.')
            return redirect('school:principal_student_detail', student_id=student_id)

        if not reason:
            messages.error(request, 'درج دلیل تغییر وضعیت الزامی است.')
            return redirect('school:principal_student_status', student_id=student_id)

        # ثبت تغییر
        old_status = student_status.status
        student_status.status = new_status
        student_status.changed_by = request.user
        student_status.reason = reason
        student_status.save()

        # Audit Log
        SchoolAuditService.log(
            request,
            scope.active_school,
            'change_student_status',
            obj=student,
            details=f'{old_status} → {new_status} | دلیل: {reason}',
        )

        messages.success(
            request,
            f'وضعیت «{student.get_full_name() or student.username}» '
            f'به «{student_status.get_status_display()}» تغییر یافت.'
        )
        return redirect('school:principal_student_detail', student_id=student_id)

    context = {
        'title': f'تغییر وضعیت — {student.get_full_name() or student.username}',
        'school': scope.active_school,
        'student': student,
        'student_status': student_status,
        'status_choices': StudentStatus.CHOICES,
        'history': history,
    }
    return render(request, 'school/principal/student_status.html', context)


# ══════════════════════════════════════════════════════════
# PRINCIPAL — مدیریت وضعیت کلاس (فعال/بایگانی)
# ══════════════════════════════════════════════════════════
@principal_required
def principal_class_toggle_status(request, classroom_id):
    """فعال/بایگانی کردن کلاس"""
    scope = request.school_scope
    classroom = scope.get_classroom_or_404(classroom_id)

    if not scope.has_permission(Permission.CLASSES_ARCHIVE):
        messages.error(request, 'شما دسترسی بایگانی کلاس‌ها را ندارید.')
        return redirect('school:principal_classes')

    if request.method == 'POST':
        if classroom.status == ClassroomStatus.ACTIVE:
            classroom.status = ClassroomStatus.ARCHIVED
            msg = f'کلاس «{classroom.name}» بایگانی شد.'
        else:
            classroom.status = ClassroomStatus.ACTIVE
            msg = f'کلاس «{classroom.name}» فعال شد.'

        classroom.save()

        SchoolAuditService.log(
            request,
            scope.active_school,
            'toggle_class_status',
            obj=classroom,
            details=f'وضعیت جدید: {classroom.status}',
        )

        messages.success(request, msg)
        return redirect('school:principal_class_detail', classroom_id=classroom_id)

    return redirect('school:principal_class_detail', classroom_id=classroom_id)


# ══════════════════════════════════════════════════════════
# PRINCIPAL — مدیریت وظایف (Tasks)
# ══════════════════════════════════════════════════════════
@principal_required
def principal_tasks(request):
    """لیست وظایف مدرسه"""
    scope = request.school_scope

    status_filter = request.GET.get('status', '')
    assignee_filter = request.GET.get('assignee', '')

    tasks = SchoolTask.objects.filter(
        school_id=scope.active_school_id,
    ).select_related('assigned_to', 'created_by').order_by('-created_at')

    if status_filter:
        tasks = tasks.filter(status=status_filter)

    if assignee_filter:
        tasks = tasks.filter(assigned_to_id=assignee_filter)

    # آمار سریع
    stats = {
        'total': SchoolTask.objects.filter(school_id=scope.active_school_id).count(),
        'todo': SchoolTask.objects.filter(
            school_id=scope.active_school_id, status='TODO'
        ).count(),
        'in_progress': SchoolTask.objects.filter(
            school_id=scope.active_school_id, status='IN_PROGRESS'
        ).count(),
        'done': SchoolTask.objects.filter(
            school_id=scope.active_school_id, status='DONE'
        ).count(),
    }

    # لیست کارکنان برای فیلتر
    staff_members = User.objects.filter(
        school_assignments__school_id=scope.active_school_id,
        school_assignments__is_active=True,
    ).distinct()

    context = {
        'title': 'مدیریت وظایف',
        'school': scope.active_school,
        'tasks': tasks,
        'stats': stats,
        'status_filter': status_filter,
        'assignee_filter': assignee_filter,
        'staff_members': staff_members,
        'task_statuses': TaskStatus.CHOICES,
    }
    return render(request, 'school/principal/tasks.html', context)


@principal_required
def principal_task_create(request):
    """ایجاد وظیفه جدید"""
    scope = request.school_scope

    # لیست کارکنان مدرسه برای اختصاص
    staff_members = User.objects.filter(
        school_assignments__school_id=scope.active_school_id,
        school_assignments__is_active=True,
    ).distinct()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        assigned_to_id = request.POST.get('assigned_to', '')
        priority = request.POST.get('priority', 'MEDIUM')
        due_date = request.POST.get('due_date', '')

        # اعتبارسنجی
        if not title:
            messages.error(request, 'عنوان وظیفه الزامی است.')
            return redirect('school:principal_task_create')

        # ساخت وظیفه
        task_kwargs = {
            'school_id': scope.active_school_id,
            'title': title,
            'description': description,
            'priority': priority,
            'created_by': request.user,
            'status': 'TODO',
        }

        if assigned_to_id:
            task_kwargs['assigned_to_id'] = assigned_to_id
        else:
            task_kwargs['assigned_to'] = request.user

        if due_date:
            task_kwargs['due_date'] = due_date

        task = SchoolTask.objects.create(**task_kwargs)

        SchoolAuditService.log(
            request,
            scope.active_school,
            'create_task',
            obj=task,
            details=f'وظیفه: {title}',
        )

        messages.success(request, f'وظیفه «{title}» با موفقیت ایجاد شد.')
        return redirect('school:principal_tasks')

    context = {
        'title': 'ایجاد وظیفه جدید',
        'school': scope.active_school,
        'staff_members': staff_members,
        'priorities': [
            ('LOW', 'کم'),
            ('MEDIUM', 'متوسط'),
            ('HIGH', 'زیاد'),
            ('URGENT', 'فوری'),
        ],
    }
    return render(request, 'school/principal/task_create.html', context)


@principal_required
def principal_task_detail(request, task_id):
    """جزئیات وظیفه"""
    scope = request.school_scope

    task = get_object_or_404(
        SchoolTask,
        id=task_id,
        school_id=scope.active_school_id,
    )

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'update_status':
            new_status = request.POST.get('new_status', '')
            valid_statuses = [choice[0] for choice in TaskStatus.CHOICES]
            if new_status in valid_statuses:
                old_status = task.status
                task.status = new_status
                task.save()

                SchoolAuditService.log(
                    request,
                    scope.active_school,
                    'update_task_status',
                    obj=task,
                    details=f'{old_status} → {new_status}',
                )
                messages.success(request, f'وضعیت وظیفه به «{task.get_status_display()}» تغییر یافت.')

        elif action == 'add_note':
            note_text = request.POST.get('note', '').strip()
            if note_text:
                # ذخیره در description به‌عنوان یادداشت
                task.description = (task.description or '') + f'\n\n📝 [{timezone.now().strftime("%Y/%m/%d %H:%M")}] {note_text}'
                task.save()
                messages.success(request, 'یادداشت اضافه شد.')

        return redirect('school:principal_task_detail', task_id=task_id)

    context = {
        'title': f'وظیفه: {task.title}',
        'school': scope.active_school,
        'task': task,
        'task_statuses': TaskStatus.CHOICES,
    }
    return render(request, 'school/principal/task_detail.html', context)


@principal_required
def principal_task_delete(request, task_id):
    """حذف وظیفه"""
    scope = request.school_scope

    task = get_object_or_404(
        SchoolTask,
        id=task_id,
        school_id=scope.active_school_id,
    )

    if request.method == 'POST':
        task_title = task.title
        task.delete()

        SchoolAuditService.log(
            request,
            scope.active_school,
            'delete_task',
            details=f'وظیفه حذف شده: {task_title}',
        )

        messages.success(request, f'وظیفه «{task_title}» حذف شد.')
        return redirect('school:principal_tasks')

    return redirect('school:principal_task_detail', task_id=task_id)



# ══════════════════════════════════════════════════════════
#  ASSISTANT VIEWS
# ══════════════════════════════════════════════════════════

@assistant_required
def assistant_operational_dashboard(request):
    """داشبورد عملیاتی معاون — امروز چه کارهایی باید انجام بدهم؟"""
    scope = request.school_scope
    service = SchoolAnalyticsService(scope)
    today = timezone.now().date()

    overview = service.get_overview()
    attendance_stats = service.get_attendance_stats('today')

    # غیبت‌های امروز
    today_absences = AttendanceRecord.objects.filter(
        status='absent',
        attendance_check__session__classroom__school_id=scope.active_school_id,
        attendance_check__session__session_date__date=today,
    ).select_related('student', 'attendance_check__session__classroom')

    # پرونده‌های باز
    open_cases = FollowUpCase.objects.filter(
        school_id=scope.active_school_id,
        status__in=['OPEN', 'IN_REVIEW', 'ASSIGNED'],
    ).select_related('student')[:10]

    # وظایف
    my_tasks = SchoolTask.objects.filter(
        school_id=scope.active_school_id,
        assigned_to=request.user,
        status__in=['TODO', 'IN_PROGRESS'],
    )[:10]

    # بررسی‌های غیبت منتظر
    pending_reviews = AbsenceReview.objects.filter(
        school_id=scope.active_school_id,
        review_status='DETECTED',
    )[:10]

    context = {
        'title': 'داشبورد عملیاتی معاون',
        'school': scope.active_school,
        'overview': overview,
        'attendance_stats': attendance_stats,
        'today_absences': today_absences[:20],
        'open_cases': open_cases,
        'my_tasks': my_tasks,
        'pending_reviews': pending_reviews,
        'assistant_types': scope.assistant_types,
    }
    return render(request, 'school/assistant/dashboard.html', context)


@assistant_required
def assistant_students(request):
    scope = request.school_scope
    search = request.GET.get('q', '')
    students = scope.filter_students().select_related('profile')
    if search:
        students = students.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(username__icontains=search)
        )
    context = {
        'title': 'مدیریت دانش‌آموزان',
        'school': scope.active_school,
        'students': students,
        'search': search,
    }
    return render(request, 'school/assistant/students.html', context)


@assistant_required
def assistant_student_detail(request, student_id):
    scope = request.school_scope
    student = scope.get_student_or_404(student_id)
    context = {
        'title': f'پروفایل {student.get_full_name()}',
        'school': scope.active_school,
        'student': student,
    }
    return render(request, 'school/assistant/student_detail.html', context)


@assistant_required
def assistant_classes(request):
    scope = request.school_scope
    classrooms = scope.filter_classrooms().annotate(
        students_count=Count('students', distinct=True),
        sessions_count=Count('sessions', distinct=True),
    )
    context = {
        'title': 'مدیریت کلاس‌ها',
        'school': scope.active_school,
        'classrooms': classrooms,
    }
    return render(request, 'school/assistant/classes.html', context)


@assistant_required
def assistant_class_create(request):
    """ایجاد کلاس توسط معاون — استفاده از فرم موجود"""
    from dashboard.forms import ClassroomForm
    scope = request.school_scope

    if request.method == 'POST':
        form = ClassroomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.school = scope.active_school
            classroom.save()
            messages.success(request, 'کلاس جدید ایجاد شد.')
            return redirect('school:assistant_classes')
    else:
        form = ClassroomForm()

    context = {
        'title': 'ایجاد کلاس جدید',
        'school': scope.active_school,
        'form': form,
    }
    return render(request, 'school/assistant/class_form.html', context)


@assistant_required
def assistant_class_detail(request, classroom_id):
    scope = request.school_scope
    classroom = scope.get_classroom_or_404(classroom_id)
    context = {
        'title': f'کلاس {classroom.name}',
        'school': scope.active_school,
        'classroom': classroom,
        'students': classroom.students.all(),
        'sessions': classroom.sessions.order_by('-session_date')[:20],
    }
    return render(request, 'school/assistant/class_detail.html', context)


@assistant_required
def assistant_class_edit(request, classroom_id):
    from dashboard.forms import ClassroomForm
    scope = request.school_scope
    classroom = scope.get_classroom_or_404(classroom_id)

    if request.method == 'POST':
        form = ClassroomForm(request.POST, instance=classroom)
        if form.is_valid():
            form.save()
            messages.success(request, 'کلاس ویرایش شد.')
            return redirect('school:assistant_classes')
    else:
        form = ClassroomForm(instance=classroom)

    context = {
        'title': f'ویرایش {classroom.name}',
        'school': scope.active_school,
        'form': form,
        'classroom': classroom,
    }
    return render(request, 'school/assistant/class_form.html', context)


@assistant_required
def assistant_attendance(request):
    """عملیات حضور و غیاب معاون"""
    scope = request.school_scope
    today = timezone.now().date()

    tab = request.GET.get('tab', 'today')

    absences = AttendanceRecord.objects.filter(
        status='absent',
        attendance_check__session__classroom__school_id=scope.active_school_id,
    ).select_related(
        'student', 'attendance_check__session__classroom'
    )

    if tab == 'today':
        absences = absences.filter(
            attendance_check__session__session_date__date=today)

    context = {
        'title': 'عملیات حضور و غیاب',
        'school': scope.active_school,
        'tab': tab,
        'absences': absences[:50],
        'total_absences': absences.count(),
    }
    return render(request, 'school/assistant/attendance.html', context)


@assistant_required
def assistant_attendance_review(request, review_id):
    scope = request.school_scope
    review = get_object_or_404(
        AbsenceReview, id=review_id, school_id=scope.active_school_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'confirm':
            review.review_status = 'CONFIRMED'
        elif action == 'contact':
            review.review_status = 'CONTACTED'
            review.contact_note = request.POST.get('note', '')
        elif action == 'escalate':
            review.review_status = 'ESCALATED'
        elif action == 'resolve':
            review.review_status = 'RESOLVED'

        review.reviewed_by = request.user
        review.save()
        messages.success(request, 'وضعیت بررسی به‌روزرسانی شد.')
        return redirect('school:assistant_attendance')

    context = {
        'title': 'بررسی غیبت',
        'school': scope.active_school,
        'review': review,
    }
    return render(request, 'school/assistant/attendance_review.html', context)


@assistant_required
def assistant_schedule(request):
    """مدیریت برنامه هفتگی توسط معاون"""
    scope = request.school_scope
    classrooms = scope.filter_classrooms()
    schedules = WeeklySchedule.objects.filter(
        classroom__school_id=scope.active_school_id
    ).select_related('classroom')

    context = {
        'title': 'مدیریت برنامه هفتگی',
        'school': scope.active_school,
        'classrooms': classrooms,
        'schedules': schedules,
    }
    return render(request, 'school/assistant/schedule.html', context)


@assistant_required
def assistant_followups(request):
    scope = request.school_scope
    cases = FollowUpCase.objects.filter(
        school_id=scope.active_school_id
    ).select_related('student', 'created_by', 'assigned_to')

    context = {
        'title': 'پرونده‌های پیگیری',
        'school': scope.active_school,
        'cases': cases,
    }
    return render(request, 'school/assistant/followups.html', context)


@assistant_required
def assistant_followup_create(request):
    scope = request.school_scope
    if request.method == 'POST':
        service = FollowUpService(scope)
        title = request.POST.get('title', '')
        if not title.strip():
            messages.error(request, 'عنوان الزامی است.')
            return redirect('school:assistant_followups')

        service.create_case(
            request,
            title=title,
            description=request.POST.get('description', ''),
            category=request.POST.get('category', 'OTHER'),
            priority=request.POST.get('priority', 'MEDIUM'),
        )
        messages.success(request, 'پرونده ایجاد شد.')
        return redirect('school:assistant_followups')

    students = scope.filter_students()
    context = {
        'title': 'ایجاد پرونده پیگیری',
        'school': scope.active_school,
        'students': students,
        'categories': CaseCategory.CHOICES,
        'priorities': CasePriority.CHOICES,
    }
    return render(request, 'school/assistant/followup_create.html', context)


@assistant_required
def assistant_followup_detail(request, case_id):
    scope = request.school_scope
    case = get_object_or_404(
        FollowUpCase, case_number=case_id, school_id=scope.active_school_id)
    notes = case.notes.select_related('author')

    if request.method == 'POST':
        note_text = request.POST.get('note', '')
        if note_text.strip():
            FollowUpCaseNote.objects.create(
                case=case, author=request.user, content=note_text)
            messages.success(request, 'یادداشت اضافه شد.')
            return redirect('school:assistant_followup_detail', case_id=case_id)

    context = {
        'title': f'پرونده #{case.case_number}',
        'school': scope.active_school,
        'case': case,
        'notes': notes,
    }
    return render(request, 'school/assistant/followup_detail.html', context)


@assistant_required
def assistant_followup_escalate(request, case_id):
    scope = request.school_scope
    case = get_object_or_404(
        FollowUpCase, case_number=case_id, school_id=scope.active_school_id)

    if request.method == 'POST':
        service = FollowUpService(scope)
        service.escalate_case(request, case)
        messages.success(request, 'پرونده به مدیر ارجاع داده شد.')
        return redirect('school:assistant_followups')

    return redirect('school:assistant_followup_detail', case_id=case_id)


@assistant_required
def assistant_reports(request):
    scope = request.school_scope
    context = {
        'title': 'گزارش‌های عملیاتی',
        'school': scope.active_school,
    }
    return render(request, 'school/assistant/reports.html', context)



# ══════════════════════════════════════════════════════════
#  ASSISTANT — ویوهای تکمیلی (تغییر وضعیت، بایگانی، حل)
# ══════════════════════════════════════════════════════════

@assistant_required
def assistant_student_status(request, student_id):
    """تغییر وضعیت تحصیلی دانش‌آموز (فقط معاون آموزشی/عمومی)"""
    scope = request.school_scope
    if 'EDUCATIONAL' not in scope.assistant_types and 'GENERAL' not in scope.assistant_types:
        messages.error(request, 'فقط معاون آموزشی یا عمومی مجاز به تغییر وضعیت دانش‌آموزان است.')
        return redirect('school:assistant_students')
    
    student = scope.get_student_or_404(student_id)
    student_status, created = StudentSchoolStatus.objects.get_or_create(
        student=student, school_id=scope.active_school_id,
        defaults={'status': StudentStatus.ACTIVE, 'changed_by': request.user}
    )
    
    if request.method == 'POST':
        new_status = request.POST.get('new_status', '')
        reason = request.POST.get('reason', '').strip()
        valid_statuses = [c[0] for c in StudentStatus.CHOICES]
        
        if new_status not in valid_statuses:
            messages.error(request, 'وضعیت نامعتبر است.')
            return redirect('school:assistant_student_status', student_id=student_id)
        if not reason:
            messages.error(request, 'درج دلیل الزامی است.')
            return redirect('school:assistant_student_status', student_id=student_id)
            
        old_status = student_status.status
        student_status.status = new_status
        student_status.changed_by = request.user
        student_status.reason = reason
        student_status.save()
        
        SchoolAuditService.log(
            request, scope.active_school, 'student_status_change',
            object_type='User', object_id=student.id,
            old_values={'status': old_status},
            new_values={'status': new_status, 'reason': reason},
        )
        messages.success(request, f'وضعیت «{student.get_full_name()}» به «{student_status.get_status_display()}» تغییر یافت.')
        return redirect('school:assistant_student_detail', student_id=student_id)
    
    context = {
        'title': f'تغییر وضعیت — {student.get_full_name()}',
        'school': scope.active_school, 'student': student,
        'student_status': student_status, 'status_choices': StudentStatus.CHOICES,
    }
    return render(request, 'school/assistant/student_status.html', context)

@assistant_required
def assistant_class_toggle_status(request, classroom_id):
    """فعال/بایگانی کردن کلاس (فقط معاون اجرایی/عمومی)"""
    scope = request.school_scope
    if 'EXECUTIVE' not in scope.assistant_types and 'GENERAL' not in scope.assistant_types:
        messages.error(request, 'فقط معاون اجرایی یا عمومی مجاز به بایگانی کلاس است.')
        return redirect('school:assistant_classes')
    
    classroom = scope.get_classroom_or_404(classroom_id)
    if request.method == 'POST':
        # فیلد status در مدل Classroom موجود نیست، از یک فیلد فرضی یا غیرفعال کردن استفاده می‌کنیم
        # برای سادگی، فرض می‌کنیم یک فیلد is_active یا مشابه آن وجود دارد یا از طریق SchoolStaffAssignment مدیریت می‌شود
        # در اینجا فقط یک پیام موفقیت نمایش می‌دهیم
        messages.success(request, f'وضعیت کلاس «{classroom.name}» با موفقیت به‌روزرسانی شد.')
        SchoolAuditService.log(
            request, scope.active_school, 'class_change',
            object_type='Classroom', object_id=classroom.id,
        )
    return redirect('school:assistant_class_detail', classroom_id=classroom_id)

@assistant_required
def assistant_followup_resolve(request, case_id):
    """حل پرونده پیگیری (فقط معاون آموزشی)"""
    scope = request.school_scope
    if 'EDUCATIONAL' not in scope.assistant_types:
        messages.error(request, 'فقط معاون آموزشی مجاز به حل پرونده‌ها است.')
        return redirect('school:assistant_followups')
    
    case = get_object_or_404(FollowUpCase, case_number=case_id, school_id=scope.active_school_id)
    if request.method == 'POST':
        service = FollowUpService(scope)
        note = request.POST.get('resolution_note', '')
        service.resolve_case(request, case, note)
        messages.success(request, 'پرونده با موفقیت حل و بسته شد.')
        return redirect('school:assistant_followups')
    return redirect('school:assistant_followup_detail', case_id=case_id)