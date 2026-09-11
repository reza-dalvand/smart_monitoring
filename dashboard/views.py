from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import (
    Classroom, ClassSession, AttendanceCheck,
    AttendanceRecord, Question, StudentAnswer,
    WeeklySchedule
)
from accounts.models import User, StudentProfile
from .forms import ClassroomForm, WeeklyScheduleForm, CopyScheduleForm


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


# ========== پنل معاون ==========
@login_required
def assistant_dashboard(request):
    """داشبورد اصلی معاون"""
    if request.user.role != 'assistant':
        messages.error(request, 'دسترسی غیرمجاز')
        return redirect('dashboard:home')
    
    # آمار کلی
    total_classes = Classroom.objects.count()
    total_students = User.objects.filter(role='student').count()
    total_teachers = User.objects.filter(role='teacher').count()
    
    # غیبت‌های امروز
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
    
    # فیلتر بر اساس مقطع یا رشته
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
    
    # اضافه کردن اطلاعات والدین
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
    
    # لیست کلاس‌ها برای فیلتر
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
    
    # فیلتر
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
    
    # فیلتر بر اساس کلاس انتخاب شده
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
    
    # فرم افزودن برنامه جدید
    if request.method == 'POST':
        form = WeeklyScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'جلسه به برنامه هفتگی اضافه شد')
            classroom_id = form.cleaned_data['classroom'].id
            return redirect(f'{request.path}?classroom={classroom_id}')
    else:
        form = WeeklyScheduleForm()
    
    # اگر کلاس انتخاب شده، فرم را با آن مقداردهی اولیه کنیم
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
    
    # فیلتر
    classroom_id = request.GET.get('classroom')
    if classroom_id:
        students = students.filter(enrolled_classes__id=classroom_id)
    
    # اضافه کردن اطلاعات والدین
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