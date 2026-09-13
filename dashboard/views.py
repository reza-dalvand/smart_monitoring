from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Prefetch
from django.utils import timezone
from datetime import timedelta

from .models import (
    Classroom,
    ClassSession,
    AttendanceCheck,
    AttendanceRecord,
    Question,
    StudentAnswer,
    WeeklySchedule,
    AIGenerationJob,
    AttendanceRequest,
    AttendanceRequestQuestion,
    AttendanceResponse,
)
from accounts.models import User, StudentProfile
from .forms import (
    ClassroomForm,
    WeeklyScheduleForm,
    CopyScheduleForm,
    AIGenerationForm,
    QuestionForm,
    AttendanceRequestForm,
    SelectQuestionsForm,
    StartSessionForm,
)
from .services import (
    generate_questions_for_job,
    regenerate_rejected_questions,
)


def teacher_required(view_func):
    """
    فقط کاربرانی که نقش معلم دارند اجازه ورود به صفحات معلم را دارند.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role != 'teacher':
            messages.error(request, 'دسترسی فقط برای معلم مجاز است.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def get_teacher_classrooms(user):
    """
    فقط کلاس‌هایی را برمی‌گرداند که معلم آن‌ها خود کاربر است.
    """
    return Classroom.objects.filter(teacher=user).order_by('name')


@login_required
def dashboard_home(request):
    user = request.user
    if user.role == 'student':
        return student_dashboard(request)
    elif user.role == 'teacher':
        return teacher_dashboard(request)
    elif user.role == 'assistant':
        return assistant_dashboard(request)
    else:
        return admin_dashboard(request)


# ========== داشبورد دانش‌آموز ==========

def student_dashboard(request):
    """داشبورد مخصوص دانش‌آموز"""
    student = request.user
    classrooms = student.enrolled_classes.all()

    total_sessions = ClassSession.objects.filter(classroom__students=student).count()
    total_attendance_checks = AttendanceCheck.objects.filter(session__classroom__students=student).count()

    present_count = AttendanceRecord.objects.filter(
        student=student,
        status='present',
        attendance_check__session__classroom__students=student
    ).count()
    absent_count = max(total_attendance_checks - present_count, 0)

    attendance_percentage = 0
    if total_attendance_checks > 0:
        attendance_percentage = round((present_count / total_attendance_checks) * 100)

    total_questions = Question.objects.filter(classroom__students=student).count()
    answers = StudentAnswer.objects.filter(student=student, question__classroom__students=student)
    answered_questions = answers.count()
    correct_answers = answers.filter(is_correct=True).count()
    wrong_answers = answered_questions - correct_answers
    unanswered_questions = max(total_questions - answered_questions, 0)

    answer_percentage = 0
    if answered_questions > 0:
        answer_percentage = round((correct_answers / answered_questions) * 100)

    sessions = ClassSession.objects.filter(classroom__students=student).order_by('id')

    attendance_chart_data = {
        'labels': [],
        'present': [],
        'absent': []
    }
    for session in sessions:
        session_present = AttendanceRecord.objects.filter(
            attendance_check__session=session,
            student=student,
            status='present'
        ).count()
        session_total_checks = session.attendance_checks.count()
        session_absent = max(session_total_checks - session_present, 0)

        attendance_chart_data['labels'].append(session.topic or f'جلسه {session.id}')
        attendance_chart_data['present'].append(session_present)
        attendance_chart_data['absent'].append(session_absent)

    answer_chart_data = {
        'labels': ['پاسخ صحیح', 'پاسخ غلط', 'بدون پاسخ'],
        'values': [correct_answers, wrong_answers, unanswered_questions]
    }

    context = {
        'welcome_message': 'به داشبورد پایش هوشمند خوش آمدید',
        'student': student,
        'classrooms': classrooms,
        'total_sessions': total_sessions,
        'total_attendance_checks': total_attendance_checks,
        'present_count': present_count,
        'absent_count': absent_count,
        'attendance_percentage': attendance_percentage,
        'total_questions': total_questions,
        'answered_questions': answered_questions,
        'correct_answers': correct_answers,
        'wrong_answers': wrong_answers,
        'unanswered_questions': unanswered_questions,
        'answer_percentage': answer_percentage,
        'attendance_chart_data': attendance_chart_data,
        'answer_chart_data': answer_chart_data,
    }
    return render(request, 'dashboard/student_dashboard.html', context)


# ========== داشبورد معلم ==========

def teacher_dashboard(request):
    context = {'welcome_message': 'به داشبورد معلم خوش آمدید'}
    return render(request, 'dashboard/index.html', context)


# ========== داشبورد مدیریت ==========

def admin_dashboard(request):
    context = {'welcome_message': 'به داشبورد مدیریت خوش آمدید'}
    return render(request, 'dashboard/index.html', context)


# ========== برنامه هفتگی دانش‌آموز ==========

@login_required
def weekly_schedule_view(request):
    """صفحه برنامه هفتگی دانش‌آموز"""
    if request.user.role != 'student':
        return render(request, 'dashboard/index.html', {
            'welcome_message': 'دسترسی محدود به دانش‌آموزان'
        })

    student = request.user
    schedules = WeeklySchedule.objects.filter(
        classroom__students=student
    ).select_related('classroom', 'classroom__teacher').order_by(
        'day_of_week', 'start_time'
    )

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
        'schedule_days': schedule_days,
        'total_classes': schedules.count(),
    }
    return render(request, 'dashboard/weekly_schedule.html', context)


# ========== برنامه هفتگی معلم ==========

@teacher_required
def teacher_weekly_schedule(request):
    """
    برنامه هفتگی معلم
    فقط کلاس‌هایی که خود کاربر معلم آن‌ها است نمایش داده می‌شود.
    """
    schedules = WeeklySchedule.objects.filter(
        classroom__teacher=request.user
    ).select_related('classroom').order_by(
        'day_of_week', 'start_time'
    )

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

    total_sessions = schedules.count()
    total_classrooms = schedules.values('classroom').distinct().count()

    context = {
        'schedule_days': schedule_days,
        'total_sessions': total_sessions,
        'total_classrooms': total_classrooms,
        'title': 'برنامه هفتگی من',
    }
    return render(request, 'dashboard/teacher/weekly_schedule.html', context)


# ========== کلاس‌های فعال معلم ==========

@teacher_required
def teacher_active_classes(request):
    """
    لیست کلاس‌های فعال معلم
    """
    classrooms = get_teacher_classrooms(request.user).annotate(
        students_count=Count('students', distinct=True),
        sessions_count=Count('sessions', distinct=True),
        active_requests=Count(
            'attendance_requests',
            filter=Q(attendance_requests__status='active'),
            distinct=True
        )
    )

    # بررسی جلسات فعال
    active_sessions = ClassSession.objects.filter(
        classroom__teacher=request.user
    ).order_by('-session_date')

    context = {
        'classrooms': classrooms,
        'active_sessions': active_sessions[:5],
        'total_classrooms': classrooms.count(),
        'title': 'کلاس‌های فعال',
    }
    return render(request, 'dashboard/teacher/active_classes.html', context)


@teacher_required
def teacher_class_detail(request, classroom_id):
    """
    صفحه جزئیات یک کلاس
    """
    classroom = get_object_or_404(
        Classroom,
        id=classroom_id,
        teacher=request.user
    )

    # جلسات اخیر
    sessions = classroom.sessions.order_by('-session_date')[:10]

    # درخواست‌های فعال
    active_requests = classroom.attendance_requests.filter(
        status='active'
    ).order_by('-created_at')

    # درخواست‌های اخیر
    recent_requests = classroom.attendance_requests.order_by('-created_at')[:10]

    # فرم شروع جلسه
    start_form = StartSessionForm()

    # آمار
    students_count = classroom.students.count()
    sessions_count = classroom.sessions.count()
    questions_count = classroom.questions.filter(is_approved=True).count()

    context = {
        'classroom': classroom,
        'sessions': sessions,
        'active_requests': active_requests,
        'recent_requests': recent_requests,
        'start_form': start_form,
        'students_count': students_count,
        'sessions_count': sessions_count,
        'questions_count': questions_count,
        'title': f'کلاس {classroom.name}',
    }
    return render(request, 'dashboard/teacher/class_detail.html', context)


@teacher_required
def teacher_start_session(request, classroom_id):
    """
    شروع جلسه جدید برای یک کلاس
    """
    classroom = get_object_or_404(
        Classroom,
        id=classroom_id,
        teacher=request.user
    )

    if request.method == 'POST':
        form = StartSessionForm(request.POST)
        if form.is_valid():
            session = ClassSession.objects.create(
                classroom=classroom,
                topic=form.cleaned_data.get('topic', '')
            )
            messages.success(
                request,
                f'جلسه جدید با موفقیت شروع شد. (جلسه {session.id})'
            )
            return redirect('dashboard:teacher_class_detail', classroom_id=classroom.id)
    else:
        form = StartSessionForm()

    return redirect('dashboard:teacher_class_detail', classroom_id=classroom.id)


@teacher_required
def teacher_create_attendance_request(request, classroom_id, session_id):
    """
    ایجاد درخواست حضور و غیاب / سوال
    """
    classroom = get_object_or_404(
        Classroom,
        id=classroom_id,
        teacher=request.user
    )
    session = get_object_or_404(
        ClassSession,
        id=session_id,
        classroom=classroom
    )

    # بررسی اینکه کلاس دانش‌آموز دارد
    if classroom.students.count() == 0:
        messages.error(request, 'این کلاس هیچ دانش‌آموزی ندارد.')
        return redirect('dashboard:teacher_class_detail', classroom_id=classroom.id)

    if request.method == 'POST':
        form = AttendanceRequestForm(request.POST)
        questions_form = SelectQuestionsForm(request.POST, classroom=classroom)

        request_type = request.POST.get('request_type', 'face_only')

        if form.is_valid():
            # اگر شامل سوال است، فرم سوالات هم باید معتبر باشد
            if request_type in ('question_only', 'face_and_question'):
                if not questions_form.is_valid():
                    messages.error(request, 'لطفاً حداقل یک سوال انتخاب کنید.')
                    return redirect(
                        f'{request.path}'
                    )
                selected_questions = questions_form.cleaned_data['questions']
            else:
                selected_questions = []

            # ایجاد درخواست
            attendance_request = form.save(commit=False)
            attendance_request.teacher = request.user
            attendance_request.classroom = classroom
            attendance_request.session = session
            attendance_request.save()

            # اضافه کردن سوالات
            if selected_questions:
                for index, question in enumerate(selected_questions, 1):
                    AttendanceRequestQuestion.objects.create(
                        attendance_request=attendance_request,
                        question=question,
                        order=index,
                        timer_seconds=question.timer_seconds
                    )

            messages.success(
                request,
                f'درخواست با موفقیت ایجاد شد. '
                f'نوع: {attendance_request.get_request_type_display()}'
            )
            return redirect(
                'dashboard:teacher_request_results',
                request_id=attendance_request.id
            )
    else:
        form = AttendanceRequestForm()
        questions_form = SelectQuestionsForm(classroom=classroom)

    context = {
        'form': form,
        'questions_form': questions_form,
        'classroom': classroom,
        'session': session,
        'title': 'ایجاد درخواست حضور و غیاب / سوال',
    }
    return render(request, 'dashboard/teacher/attendance_request_form.html', context)


@teacher_required
def teacher_class_students(request, classroom_id):
    """
    لیست دانش‌آموزان یک کلاس
    """
    classroom = get_object_or_404(
        Classroom,
        id=classroom_id,
        teacher=request.user
    )

    students = classroom.students.select_related('profile').order_by(
        'last_name', 'first_name'
    )

    students_with_info = []
    for student in students:
        try:
            profile = student.profile
            parent_phone = profile.parent_phone or profile.parent_phone_2 or ''
        except StudentProfile.DoesNotExist:
            parent_phone = ''

        # آمار کلی دانش‌آموز در این کلاس
        total_answers = StudentAnswer.objects.filter(
            student=student,
            question__classroom=classroom
        ).count()
        correct_answers = StudentAnswer.objects.filter(
            student=student,
            question__classroom=classroom,
            is_correct=True
        ).count()

        students_with_info.append({
            'student': student,
            'parent_phone': parent_phone,
            'total_answers': total_answers,
            'correct_answers': correct_answers,
            'wrong_answers': total_answers - correct_answers,
            'percentage': round((correct_answers / total_answers * 100)) if total_answers > 0 else 0,
        })

    context = {
        'classroom': classroom,
        'students_with_info': students_with_info,
        'total_students': len(students_with_info),
        'title': f'دانش‌آموزان کلاس {classroom.name}',
    }
    return render(request, 'dashboard/teacher/class_students.html', context)


@teacher_required
def teacher_request_results(request, request_id):
    """
    نتایج یک درخواست حضور و غیاب / سوال
    """
    attendance_request = get_object_or_404(
        AttendanceRequest,
        id=request_id,
        teacher=request.user
    )

    classroom = attendance_request.classroom
    session = attendance_request.session

    # دریافت پاسخ‌ها
    responses = attendance_request.responses.select_related(
        'student', 'student__profile'
    ).order_by('student__last_name', 'student__first_name')

    # آمار حضور و غیاب
    total_students = responses.count()
    present_count = responses.filter(final_status='present').count()
    absent_count = responses.filter(final_status='absent').count()
    pending_count = responses.filter(final_status='pending').count()

    # آمار سوالات
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
            'correct_percentage': round((correct_count / total_students * 100)) if total_students > 0 else 0,
        })

    # لیست دانش‌آموزان با جزئیات
    students_detail = []
    for response in responses:
        student = response.student

        # پاسخ‌های این دانش‌آموز در این درخواست
        student_answers = StudentAnswer.objects.filter(
            attendance_request=attendance_request,
            student=student
        ).select_related('question')

        correct = student_answers.filter(is_correct=True).count()
        wrong = student_answers.filter(is_correct=False).count()
        total = student_answers.count()

        students_detail.append({
            'response': response,
            'student': student,
            'correct': correct,
            'wrong': wrong,
            'total': total,
            'no_answer': len(request_questions) - total if request_questions else 0,
            'answers': student_answers,
        })

    # فیلترها
    status_filter = request.GET.get('status', '')
    if status_filter == 'present':
        students_detail = [s for s in students_detail if s['response'].final_status == 'present']
    elif status_filter == 'absent':
        students_detail = [s for s in students_detail if s['response'].final_status == 'absent']
    elif status_filter == 'pending':
        students_detail = [s for s in students_detail if s['response'].final_status == 'pending']

    context = {
        'attendance_request': attendance_request,
        'classroom': classroom,
        'session': session,
        'responses': responses,
        'total_students': total_students,
        'present_count': present_count,
        'absent_count': absent_count,
        'pending_count': pending_count,
        'request_questions': request_questions,
        'questions_stats': questions_stats,
        'students_detail': students_detail,
        'status_filter': status_filter,
        'title': f'نتایج درخواست {request_id}',
    }
    return render(request, 'dashboard/teacher/request_results.html', context)


@teacher_required
def teacher_finish_request(request, request_id):
    """
    پایان دادن به یک درخواست فعال
    """
    attendance_request = get_object_or_404(
        AttendanceRequest,
        id=request_id,
        teacher=request.user,
        status='active'
    )

    if request.method == 'POST':
        # علامت‌گذاری دانش‌آموزانی که پاسخ ندادن
        for response in attendance_request.responses.filter(auto_status='pending'):
            response.mark_no_response()

        attendance_request.status = 'finished'
        attendance_request.save()

        messages.success(request, 'درخواست با موفقیت پایان یافت.')
        return redirect(
            'dashboard:teacher_request_results',
            request_id=attendance_request.id
        )

    return redirect('dashboard:teacher_request_results', request_id=request_id)


# ========== پنل معاون ==========

@login_required
def assistant_dashboard(request):
    """داشبورد اصلی معاون"""
    if request.user.role != 'assistant':
        messages.error(request, 'دسترسی غیرمجاز')
        return redirect('dashboard:home')

    total_classes = Classroom.objects.count()
    total_students = User.objects.filter(role='student').count()
    total_teachers = User.objects.filter(role='teacher').count()

    today = timezone.now().date()
    today_attendance = AttendanceRecord.objects.filter(
        status='absent',
        attendance_check__session__session_date__date=today
    ).select_related('student', 'attendance_check__session__classroom')
    today_absent_count = today_attendance.count()

    context = {
        'total_classes': total_classes,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'today_absent_count': today_absent_count,
        'recent_absences': today_attendance[:10],
    }
    return render(request, 'dashboard/assistant_dashboard.html', context)


@login_required
def absences_today_view(request):
    """لیست کامل غیبت‌های امروز با شماره والدین"""
    if request.user.role != 'assistant':
        messages.error(request, 'دسترسی غیرمجاز')
        return redirect('dashboard:home')

    today = timezone.now().date()
    grade_filter = request.GET.get('grade')
    field_filter = request.GET.get('field')
    class_filter = request.GET.get('classroom')

    absences = AttendanceRecord.objects.filter(
        status='absent',
        attendance_check__session__session_date__date=today
    ).select_related(
        'student',
        'attendance_check__session__classroom'
    ).order_by('attendance_check__session__classroom__name', 'student__last_name')

    if grade_filter:
        absences = absences.filter(attendance_check__session__classroom__grade=grade_filter)
    if field_filter:
        absences = absences.filter(attendance_check__session__classroom__field=field_filter)
    if class_filter:
        absences = absences.filter(attendance_check__session__classroom__id=class_filter)

    absences_with_parent = []
    for record in absences:
        parent_phone = ''
        parent_name = ''
        try:
            profile = record.student.profile
            parent_phone = profile.parent_phone or profile.parent_phone_2 or ''
            parent_name = profile.father_name or ''
        except StudentProfile.DoesNotExist:
            pass
        absences_with_parent.append({
            'record': record,
            'parent_phone': parent_phone,
            'parent_name': parent_name,
        })

    classrooms = Classroom.objects.all().order_by('grade', 'field', 'name')

    context = {
        'absences_with_parent': absences_with_parent,
        'total_absences': len(absences_with_parent),
        'today': today,
        'classrooms': classrooms,
        'grade_filter': grade_filter,
        'field_filter': field_filter,
        'class_filter': class_filter,
        'grades': Classroom.GRADE_CHOICES,
        'fields': Classroom.FIELD_CHOICES,
    }
    return render(request, 'dashboard/assistant/absences_today.html', context)


@login_required
def class_list_view(request):
    """لیست همه کلاس‌ها برای معاون"""
    if request.user.role != 'assistant':
        messages.error(request, 'دسترسی غیرمجاز')
        return redirect('dashboard:home')

    grade_filter = request.GET.get('grade')
    field_filter = request.GET.get('field')

    classrooms = Classroom.objects.all().order_by('grade', 'field', 'name')
    if grade_filter:
        classrooms = classrooms.filter(grade=grade_filter)
    if field_filter:
        classrooms = classrooms.filter(field=field_filter)

    context = {
        'classrooms': classrooms,
        'grades': Classroom.GRADE_CHOICES,
        'fields': Classroom.FIELD_CHOICES,
        'grade_filter': grade_filter,
        'field_filter': field_filter,
    }
    return render(request, 'dashboard/assistant/class_list.html', context)


@login_required
def class_create_view(request):
    """ساخت کلاس جدید توسط معاون"""
    if request.user.role != 'assistant':
        messages.error(request, 'دسترسی غیرمجاز')
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = ClassroomForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'کلاس جدید با موفقیت ایجاد شد')
            return redirect('dashboard:assistant_class_list')
    else:
        form = ClassroomForm()

    context = {
        'form': form,
        'title': 'ایجاد کلاس جدید'
    }
    return render(request, 'dashboard/assistant/class_form.html', context)


@login_required
def class_edit_view(request, pk):
    """ویرایش کلاس"""
    if request.user.role != 'assistant':
        messages.error(request, 'دسترسی غیرمجاز')
        return redirect('dashboard:home')

    classroom = get_object_or_404(Classroom, pk=pk)
    if request.method == 'POST':
        form = ClassroomForm(request.POST, instance=classroom)
        if form.is_valid():
            form.save()
            messages.success(request, 'کلاس با موفقیت ویرایش شد')
            return redirect('dashboard:assistant_class_list')
    else:
        form = ClassroomForm(instance=classroom)

    context = {
        'form': form,
        'classroom': classroom,
        'title': f'ویرایش کلاس {classroom.name}'
    }
    return render(request, 'dashboard/assistant/class_form.html', context)


@login_required
def class_delete_view(request, pk):
    """حذف کلاس"""
    if request.user.role != 'assistant':
        messages.error(request, 'دسترسی غیرمجاز')
        return redirect('dashboard:home')

    classroom = get_object_or_404(Classroom, pk=pk)
    if request.method == 'POST':
        classroom.delete()
        messages.success(request, 'کلاس با موفقیت حذف شد')
        return redirect('dashboard:assistant_class_list')

    context = {'classroom': classroom}
    return render(request, 'dashboard/assistant/class_confirm_delete.html', context)


@login_required
def schedule_builder_view(request):
    """ساخت و مدیریت برنامه هفتگی"""
    if request.user.role != 'assistant':
        messages.error(request, 'دسترسی غیرمجاز')
        return redirect('dashboard:home')

    classroom_id = request.GET.get('classroom')
    selected_classroom = None
    schedule_days = []

    if classroom_id:
        selected_classroom = get_object_or_404(Classroom, pk=classroom_id)
        schedules = WeeklySchedule.objects.filter(
            classroom=selected_classroom
        ).order_by('day_of_week', 'start_time')

        days_info = [
            ('saturday', 'شنبه'),
            ('sunday', 'یکشنبه'),
            ('monday', 'دوشنبه'),
            ('tuesday', 'سه‌شنبه'),
            ('wednesday', 'چهارشنبه'),
        ]

        for day_key, day_name in days_info:
            day_classes = [s for s in schedules if s.day_of_week == day_key]
            schedule_days.append({
                'key': day_key,
                'name': day_name,
                'classes': day_classes,
                'count': len(day_classes),
            })

    if request.method == 'POST':
        form = WeeklyScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'جلسه به برنامه هفتگی اضافه شد')
            classroom_id = form.cleaned_data['classroom'].id
            return redirect(f'{request.path}?classroom={classroom_id}')
    else:
        form = WeeklyScheduleForm()
        if selected_classroom:
            form.fields['classroom'].initial = selected_classroom

    classrooms = Classroom.objects.all().order_by('grade', 'field', 'name')

    context = {
        'form': form,
        'classrooms': classrooms,
        'selected_classroom': selected_classroom,
        'schedule_days': schedule_days,
    }
    return render(request, 'dashboard/assistant/schedule_builder.html', context)


@login_required
def schedule_delete_view(request, pk):
    """حذف یک جلسه از برنامه هفتگی"""
    if request.user.role != 'assistant':
        messages.error(request, 'دسترسی غیرمجاز')
        return redirect('dashboard:home')

    schedule = get_object_or_404(WeeklySchedule, pk=pk)
    classroom_id = schedule.classroom.id

    if request.method == 'POST':
        schedule.delete()
        messages.success(request, 'جلسه از برنامه حذف شد')
        return redirect(f'{request.META.get("HTTP_REFERER", "/assistant/schedule/")}?classroom={classroom_id}')


@login_required
def schedule_copy_view(request):
    """کپی برنامه هفتگی از یک کلاس به کلاس دیگر"""
    if request.user.role != 'assistant':
        messages.error(request, 'دسترسی غیرمجاز')
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = CopyScheduleForm(request.POST)
        if form.is_valid():
            source = form.cleaned_data['source_classroom']
            target = form.cleaned_data['target_classroom']
            source_schedules = WeeklySchedule.objects.filter(classroom=source)
            copied_count = 0
            for schedule in source_schedules:
                WeeklySchedule.objects.create(
                    classroom=target,
                    day_of_week=schedule.day_of_week,
                    start_time=schedule.start_time,
                    end_time=schedule.end_time,
                    room=schedule.room
                )
                copied_count += 1
            messages.success(
                request,
                f'برنامه هفتگی با {copied_count} جلسه از "{source.name}" به "{target.name}" کپی شد'
            )
            return redirect(f'/assistant/schedule/?classroom={target.id}')
    else:
        form = CopyScheduleForm()

    context = {
        'form': form,
        'title': 'کپی برنامه هفتگی'
    }
    return render(request, 'dashboard/assistant/schedule_copy.html', context)


@login_required
def schedule_print_view(request, classroom_id):
    """چاپ برنامه هفتگی یک کلاس"""
    if request.user.role != 'assistant':
        messages.error(request, 'دسترسی غیرمجاز')
        return redirect('dashboard:home')

    classroom = get_object_or_404(Classroom, pk=classroom_id)
    schedules = WeeklySchedule.objects.filter(
        classroom=classroom
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
        'classroom': classroom,
        'schedule_days': schedule_days,
        'print_mode': True,
    }
    return render(request, 'dashboard/assistant/schedule_print.html', context)


@login_required
def student_list_view(request):
    """لیست دانش‌آموزان با اطلاعات والدین"""
    if request.user.role != 'assistant':
        messages.error(request, 'دسترسی غیرمجاز')
        return redirect('dashboard:home')

    students = User.objects.filter(role='student').order_by('last_name', 'first_name')

    classroom_id = request.GET.get('classroom')
    if classroom_id:
        students = students.filter(enrolled_classes__id=classroom_id)

    students_with_parent = []
    for student in students:
        parent_phone = ''
        parent_name = ''
        try:
            profile = student.profile
            parent_phone = profile.parent_phone or profile.parent_phone_2 or ''
            parent_name = profile.father_name or ''
        except StudentProfile.DoesNotExist:
            pass
        students_with_parent.append({
            'student': student,
            'parent_phone': parent_phone,
            'parent_name': parent_name,
        })

    classrooms = Classroom.objects.all().order_by('grade', 'field', 'name')

    context = {
        'students_with_parent': students_with_parent,
        'total_students': len(students_with_parent),
        'classrooms': classrooms,
        'class_filter': classroom_id,
    }
    return render(request, 'dashboard/assistant/student_list.html', context)


# ========== فاز ۲: تولید سوال با هوش مصنوعی ==========

@teacher_required
def teacher_ai_new(request):
    """
    صفحه ساخت درخواست تولید سوال با هوش مصنوعی
    """
    classrooms = get_teacher_classrooms(request.user)
    if not classrooms.exists():
        messages.warning(
            request,
            'هیچ کلاسی برای شما ثبت نشده است. لطفاً با معاون مدرسه هماهنگ کنید.'
        )

    if request.method == 'POST':
        form = AIGenerationForm(request.POST, request.FILES, teacher=request.user)
        if form.is_valid():
            job = form.save(commit=False)
            job.teacher = request.user
            job.status = 'pending'
            job.save()

            generate_questions_for_job(job)
            job.refresh_from_db()

            if job.status == 'completed':
                generated_count = job.generated_questions.count()
                messages.success(
                    request,
                    f'{generated_count} سوال پیش‌نویس توسط هوش مصنوعی ماک تولید شد. '
                    f'حالا می‌توانید آن‌ها را بررسی، تایید یا رد کنید.'
                )
            else:
                messages.error(
                    request,
                    f'خطا در تولید سوال: {job.error_message}'
                )
            return redirect('dashboard:teacher_ai_review', job_id=job.id)
    else:
        form = AIGenerationForm(teacher=request.user)

    context = {
        'form': form,
        'classrooms_count': classrooms.count(),
        'title': 'تولید سوال با هوش مصنوعی',
    }
    return render(request, 'dashboard/teacher/ai_generate_form.html', context)


@teacher_required
def teacher_ai_review(request, job_id):
    """
    صفحه بررسی سوال‌های تولیدشده توسط هوش مصنوعی
    """
    job = get_object_or_404(
        AIGenerationJob,
        id=job_id,
        teacher=request.user
    )
    questions = job.generated_questions.all().order_by('id')
    pending_count = questions.filter(review_status='pending').count()
    approved_count = questions.filter(review_status='approved').count()
    rejected_count = questions.filter(review_status='rejected').count()

    context = {
        'job': job,
        'questions': questions,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'title': 'بررسی سوال‌های تولیدشده',
    }
    return render(request, 'dashboard/teacher/ai_review.html', context)


@teacher_required
def teacher_ai_question_approve(request, pk):
    """
    تایید یک سوال تولیدشده توسط هوش مصنوعی
    """
    question = get_object_or_404(
        Question,
        pk=pk,
        ai_job__teacher=request.user
    )
    if request.method == 'POST':
        question.review_status = 'approved'
        question.is_approved = True
        question.save()
        messages.success(request, 'سوال تایید شد و به بانک سوال اضافه شد.')
        return redirect('dashboard:teacher_ai_review', job_id=question.ai_job.id)


@teacher_required
def teacher_ai_question_reject(request, pk):
    """
    رد یک سوال تولیدشده توسط هوش مصنوعی
    """
    question = get_object_or_404(
        Question,
        pk=pk,
        ai_job__teacher=request.user
    )
    if request.method == 'POST':
        question.review_status = 'rejected'
        question.is_approved = False
        question.save()
        messages.warning(request, 'سوال رد شد. می‌توانید برای سوال‌های ردشده درخواست تولید مجدد بدهید.')
        return redirect('dashboard:teacher_ai_review', job_id=question.ai_job.id)


@teacher_required
def teacher_ai_regenerate_rejected(request, job_id):
    """
    تولید مجدد سوال‌های ردشده
    """
    job = get_object_or_404(
        AIGenerationJob,
        id=job_id,
        teacher=request.user
    )
    if request.method == 'POST':
        regenerated_count = regenerate_rejected_questions(job)
        if regenerated_count > 0:
            messages.success(
                request,
                f'{regenerated_count} سوال ردشده دوباره تولید شد.'
            )
        else:
            messages.info(request, 'سوال ردشده‌ای برای تولید مجدد وجود ندارد.')
        return redirect('dashboard:teacher_ai_review', job_id=job.id)


# ========== فاز ۲: بانک سوال و سوال دستی ==========

@teacher_required
def teacher_question_bank(request):
    """
    بانک سوال معلم
    معلم فقط سوال‌های کلاس‌های خودش را می‌بیند.
    """
    questions = Question.objects.filter(
        classroom__teacher=request.user
    ).select_related(
        'classroom',
        'session',
        'ai_job',
        'created_by'
    ).order_by('-created_at')

    classrooms = get_teacher_classrooms(request.user)

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

    context = {
        'questions': questions,
        'classrooms': classrooms,
        'classroom_filter': classroom_filter,
        'source_filter': source_filter,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_count': questions.count(),
        'title': 'بانک سوالات',
    }
    return render(request, 'dashboard/teacher/question_bank.html', context)


@teacher_required
def teacher_question_manual_create(request):
    """
    ساخت سوال دستی توسط معلم
    """
    if request.method == 'POST':
        form = QuestionForm(request.POST, teacher=request.user)
        if form.is_valid():
            question = form.save(commit=False)
            question.created_by = request.user
            question.source = 'manual'
            question.is_approved = True
            question.review_status = 'approved'
            question.save()
            messages.success(request, 'سوال دستی با موفقیت در بانک سوال ذخیره شد.')
            return redirect('dashboard:teacher_question_bank')
    else:
        form = QuestionForm(teacher=request.user)

    context = {
        'form': form,
        'title': 'ساخت سوال دستی',
    }
    return render(request, 'dashboard/teacher/question_form.html', context)


@teacher_required
def teacher_question_edit(request, pk):
    """
    ویرایش سوال توسط معلم
    معلم فقط سوال‌های کلاس‌های خودش را می‌تواند ویرایش کند.
    """
    question = get_object_or_404(
        Question,
        pk=pk,
        classroom__teacher=request.user
    )

    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question, teacher=request.user)
        if form.is_valid():
            question = form.save(commit=False)
            if question.source == 'manual':
                question.review_status = 'approved'
                question.is_approved = True
            elif question.review_status == 'rejected':
                question.review_status = 'pending'
                question.is_approved = False
            question.save()
            messages.success(request, 'سوال با موفقیت ویرایش شد.')
            return redirect('dashboard:teacher_question_bank')
    else:
        form = QuestionForm(instance=question, teacher=request.user)

    context = {
        'form': form,
        'question': question,
        'title': 'ویرایش سوال',
    }
    return render(request, 'dashboard/teacher/question_form.html', context)


@teacher_required
def teacher_question_delete(request, pk):
    """
    حذف سوال توسط معلم
    """
    question = get_object_or_404(
        Question,
        pk=pk,
        classroom__teacher=request.user
    )

    if request.method == 'POST':
        question.delete()
        messages.success(request, 'سوال حذف شد.')
        return redirect('dashboard:teacher_question_bank')

    context = {
        'question': question,
        'title': 'حذف سوال',
    }
    return render(request, 'dashboard/teacher/question_confirm_delete.html', context)