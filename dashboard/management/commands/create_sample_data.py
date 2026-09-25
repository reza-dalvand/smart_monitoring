import random
from datetime import time, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User, StudentProfile
from dashboard.models import (
    Classroom, ClassSession, AttendanceCheck,
    AttendanceRecord, Question, StudentAnswer, WeeklySchedule,
    AIGenerationJob, AttendanceRequest, AttendanceResponse
)


class Command(BaseCommand):
    help = 'ایجاد داده‌های نمونه کامل، گسترده و واقع‌گرایانه برای تست تمام بخش‌های سامانه'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🔄 در حال پاکسازی داده‌های قدیمی...'))
        
        # پاکسازی کامل همه داده‌های وابسته
        AttendanceResponse.objects.all().delete()
        AttendanceRequest.objects.all().delete()
        StudentAnswer.objects.all().delete()
        Question.objects.all().delete()
        AIGenerationJob.objects.all().delete()
        AttendanceRecord.objects.all().delete()
        AttendanceCheck.objects.all().delete()
        ClassSession.objects.all().delete()
        WeeklySchedule.objects.all().delete()
        Classroom.objects.all().delete()

        self.stdout.write('🔄 در حال ساخت داده‌های نمونه جدید...')
        
        # ===== ۱. ساخت کاربران =====
        self.stdout.write('   👤 در حال ساخت کاربران...')
        
        # مدیر مدرسه
        principal, _ = User.objects.get_or_create(
            username='principal1',
            defaults={'role': 'principal', 'first_name': 'دکتر احمد', 'last_name': 'مدیری', 'email': 'principal@example.com'}
        )
        principal.set_password('12345678')
        principal.save()

        # معاون
        assistant, _ = User.objects.get_or_create(
            username='assistant1',
            defaults={'role': 'assistant', 'first_name': 'محمد', 'last_name': 'رضایی', 'email': 'assistant@example.com'}
        )
        assistant.set_password('12345678')
        assistant.save()
        
        # معلم‌ها
        teachers_data = [
            ('teacher1', 'علی', 'محمدی', 'ریاضی'),
            ('teacher2', 'مریم', 'احمدی', 'فیزیک'),
            ('teacher3', 'حسن', 'کریمی', 'ادبیات'),
            ('teacher4', 'زهرا', 'رضوی', 'کامپیوتر'),
            ('teacher5', 'رضا', 'نوری', 'برق'),
        ]
        teachers = []
        for username, first, last, _ in teachers_data:
            teacher, _ = User.objects.get_or_create(
                username=username,
                defaults={'role': 'teacher', 'first_name': first, 'last_name': last, 'email': f'{username}@example.com'}
            )
            teacher.set_password('12345678')
            teacher.save()
            teachers.append(teacher)
        
        # دانش‌آموزان (۱۰ نفر)
        students_data = [
            ('student1', 'رضا', 'احمدی', '09121111111', 'احمد'),
            ('student2', 'علی', 'محمدی', '09122222222', 'محمد'),
            ('student3', 'حسین', 'کریمی', '09123333333', 'کریم'),
            ('student4', 'مهدی', 'رضوی', '09124444444', 'رضا'),
            ('student5', 'امیر', 'نوری', '09125555555', 'نور'),
            ('student6', 'سارا', 'جعفری', '09126666666', 'حسن'),
            ('student7', 'نیکا', 'تقوی', '09127777777', 'علی'),
            ('student8', 'پرهام', 'کاظمی', '09128888888', 'رضا'),
            ('student9', 'آرمین', 'صادقی', '09129999999', 'محمد'),
            ('student10', 'کیان', 'مرادی', '09120000000', 'حسین'),
        ]
        students = []
        for username, first, last, phone, father in students_data:
            student, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    'role': 'student', 'first_name': first, 'last_name': last,
                    'email': f'{username}@example.com', 
                    'national_id': f'00{random.randint(10000000, 99999999)}'
                }
            )
            student.set_password('12345678')
            student.save()
            students.append(student)
            
            StudentProfile.objects.get_or_create(
                user=student,
                defaults={'father_name': father, 'parent_phone': phone, 'phone': phone, 'city': 'تهران'}
            )
        
        self.stdout.write(f'   👨‍💼 مدیر: principal1 | 👨‍💼 معاون: assistant1')
        self.stdout.write(f'   👨‍🏫 {len(teachers)} معلم ساخته شد')
        self.stdout.write(f'   👨‍🎓 {len(students)} دانش‌آموز با پروفایل ساخته شد')
        
        # ===== ۲. ساخت کلاس‌ها =====
        self.stdout.write('   📚 در حال ساخت کلاس‌ها...')
        classrooms_data = [
            {'name': '۱۰۱ کامپیوتر', 'subject': 'برنامه‌نویسی پایتون', 'grade': '10', 'field': 'computer', 'teacher': teachers[3]},
            {'name': '۱۰۲ کامپیوتر', 'subject': 'شبکه‌های کامپیوتری', 'grade': '10', 'field': 'computer', 'teacher': teachers[3]},
            {'name': '۲۰۱ ریاضی', 'subject': 'ریاضی پایه دهم', 'grade': '10', 'field': 'math', 'teacher': teachers[0]},
            {'name': '۲۰۲ ریاضی', 'subject': 'فیزیک پایه دهم', 'grade': '10', 'field': 'math', 'teacher': teachers[1]},
            {'name': '۳۰۱ برق', 'subject': 'مدارهای الکتریکی', 'grade': '11', 'field': 'electrical', 'teacher': teachers[4]},
            {'name': '۴۰۱ تجربی', 'subject': 'زیست‌شناسی', 'grade': '11', 'field': 'experimental', 'teacher': teachers[1]},
            {'name': '۵۰۱ انسانی', 'subject': 'ادبیات فارسی', 'grade': '12', 'field': 'humanities', 'teacher': teachers[2]},
            {'name': '۵۰۲ انسانی', 'subject': 'تاریخ', 'grade': '12', 'field': 'humanities', 'teacher': teachers[2]},
        ]
        classrooms = []
        for data in classrooms_data:
            classroom, _ = Classroom.objects.get_or_create(
                name=data['name'],
                defaults={
                    'subject': data['subject'], 'grade': data['grade'], 'field': data['field'],
                    'teacher_name': f"{data['teacher'].first_name} {data['teacher'].last_name}",
                    'teacher': data['teacher'],
                }
            )
            classrooms.append(classroom)
        
        # توزیع دانش‌آموزان در کلاس‌ها
        classrooms[0].students.set(students[0:4])   # ۱۰۱ کامپیوتر
        classrooms[1].students.set(students[2:6])   # ۱۰۲ کامپیوتر
        classrooms[2].students.set(students[0:3])   # ۲۰۱ ریاضی
        classrooms[3].students.set(students[3:7])   # ۲۰۲ ریاضی
        classrooms[4].students.set(students[5:8])   # ۳۰۱ برق
        classrooms[5].students.set(students[6:9])   # ۴۰۱ تجربی
        classrooms[6].students.set(students[7:10])  # ۵۰۱ انسانی
        classrooms[7].students.set(students[0:2] + students[8:10])  # ۵۰۲ انسانی
        
        self.stdout.write(f'   📚 {len(classrooms)} کلاس با توزیع دانش‌آموزان ساخته شد')
        
        # ===== ۳. ساخت جلسات و حضور و غیاب =====
        self.stdout.write('   📅 در حال ساخت جلسات و حضور و غیاب...')
        TOTAL_SESSIONS_PER_CLASS = 15
        
        for classroom in classrooms:
            sessions = []
            checks = []
            now = timezone.now()
            
            # ساخت ۱۵ جلسه در ۱۵ روز گذشته
            for i in range(TOTAL_SESSIONS_PER_CLASS):
                session = ClassSession.objects.create(
                    classroom=classroom,
                    topic=f'جلسه {i+1}: مبحث نمونه و مرور'
                )
                # آپدیت session_date چون auto_now_add=True است
                session_date = now - timedelta(days=(TOTAL_SESSIONS_PER_CLASS - i - 1))
                ClassSession.objects.filter(id=session.id).update(session_date=session_date)
                
                sessions.append(session)
                checks.append(AttendanceCheck.objects.create(session=session))
            
            # برای هر دانش‌آموز، دقیقاً ۱۰ حضور و ۵ غیبت تخصیص می‌دهیم
            for student in classroom.students.all():
                # ایجاد لیستی با ۱۰ 'present' و ۵ 'absent' و به‌هم‌ریختن تصادفی آن
                statuses = ['present'] * 10 + ['absent'] * 5
                random.shuffle(statuses)
                
                for i, check in enumerate(checks):
                    AttendanceRecord.objects.create(
                        attendance_check=check,
                        student=student,
                        status=statuses[i]
                    )
        
        self.stdout.write(f'   ✅ {TOTAL_SESSIONS_PER_CLASS} جلسه برای هر کلاس + رکوردهای حضور/غیاب ساخته شد')

        # ===== ۴. ساخت سوالات و پاسخ‌های دانش‌آموزان =====
        self.stdout.write('   ❓ در حال ساخت سوالات و پاسخ‌ها...')
        topics = ['مقدمه', 'مفاهیم پایه', 'تمرین عملی', 'ارزیابی میان‌ترم', 'جمع‌بندی']
        
        for classroom in classrooms:
            # ساخت ۸ سوال برای هر کلاس
            for i in range(8):
                q = Question.objects.create(
                    classroom=classroom,
                    session=random.choice(classroom.sessions.all()) if classroom.sessions.exists() else None,
                    topic=random.choice(topics),
                    source=random.choice(['ai', 'manual']),
                    review_status='approved',
                    is_approved=True,
                    text=f'سوال نمونه شماره {i+1} مربوط به مبحث {random.choice(topics)} در کلاس {classroom.name} چیست؟',
                    choice_a='گزینه الف که کاملاً صحیح به نظر می‌رسد',
                    choice_b='گزینه ب که کمی گمراه‌کننده است',
                    choice_c='گزینه ج که اصلاً مرتبط نیست',
                    choice_d='گزینه د که ناقص است',
                    correct_answer='a',
                    timer_seconds=120
                )
                
                # تولید پاسخ برای دانش‌آموزان این کلاس (۷۰٪ احتمال پاسخ صحیح)
                for student in classroom.students.all():
                    is_correct = random.choices([True, False], weights=[70, 30])[0]
                    StudentAnswer.objects.create(
                        question=q,
                        student=student,
                        selected_choice='a' if is_correct else random.choice(['b', 'c', 'd']),
                        is_correct=is_correct
                    )
        
        self.stdout.write('   ❓ سوالات و پاسخ‌های دانش‌آموزان (با نرخ موفقیت ~۷۰٪) ساخته شد')

        # ===== ۵. ساخت درخواست‌های حضور و غیاب (Attendance Request) =====
        self.stdout.write('   📸 در حال ساخت درخواست‌های حضور و غیاب...')
        
        for classroom in classrooms[:4]:  # برای ۴ کلاس اول
            session = classroom.sessions.last()
            req = AttendanceRequest.objects.create(
                teacher=classroom.teacher,
                classroom=classroom,
                session=session,
                request_type=random.choice(['face_only', 'face_and_question']),
                status='finished',
                face_time_seconds=120
            )
            
            # 🔧 اصلاح مهم: مدل AttendanceRequest در save خودش AttendanceResponse می‌سازد
            # پس باید رکوردهای موجود را آپدیت کنیم نه create کنیم
            for response in req.responses.all():
                auto_status = random.choice(['present', 'present', 'present', 'suspicious'])
                response.auto_status = auto_status
                response.final_status = 'present' if auto_status == 'present' else 'pending'
                response.confidence = round(random.uniform(0.85, 0.99), 2)
                
                # پر کردن فیلدهای اسکن چهره برای واقع‌گرایانه شدن آمار
                if auto_status == 'present':
                    response.face_verified = True
                    response.face_status = 'VERIFIED'
                    response.similarity_score = response.confidence
                    response.liveness_status = 'passed'
                    response.face_submitted_at = timezone.now()
                else:
                    response.face_verified = False
                    response.face_status = 'SUSPICIOUS'
                    response.similarity_score = round(random.uniform(0.20, 0.40), 2)
                    response.failure_reason = 'MATCH_BELOW_THRESHOLD'
                    response.face_submitted_at = timezone.now()
                    
                response.save()
                
        self.stdout.write('   📸 نمونه درخواست‌های حضور و غیاب هوشمند ساخته شد')

        # ===== ۶. ساخت نمونه کارهای هوش مصنوعی (AI Generation Jobs) =====
        self.stdout.write('   🤖 در حال ساخت کارهای هوش مصنوعی...')
        
        for teacher in teachers[:2]:
            classroom = teacher.taught_classes.first()
            if classroom:
                job = AIGenerationJob.objects.create(
                    teacher=teacher,
                    classroom=classroom,
                    topic='هوش مصنوعی و یادگیری ماشین',
                    prompt='لطفاً ۵ سوال چهارگزینه‌ای مفهومی از مبحث هوش مصنوعی طراحی کن.',
                    requested_count=5,
                    default_timer_seconds=180,
                    status='completed',
                    raw_response='{"questions": []}'
                )
                
                # ساخت چند سوال نمونه متصل به این جاب
                for i in range(3):
                    Question.objects.create(
                        classroom=classroom,
                        created_by=teacher,
                        ai_job=job,
                        source='ai',
                        review_status='pending',
                        is_approved=False,
                        topic='هوش مصنوعی',
                        text=f'سوال تولیدشده توسط هوش مصنوعی شماره {i+1}؟',
                        choice_a='پاسخ صحیح', 
                        choice_b='غلط', 
                        choice_c='غلط', 
                        choice_d='غلط',
                        correct_answer='a',
                        timer_seconds=180
                    )
        
        self.stdout.write('   🤖 نمونه درخواست‌ها و سوالات تولیدشده توسط هوش مصنوعی ساخته شد')

        # ===== ۷. ساخت برنامه هفتگی =====
        self.stdout.write('   📅 در حال ساخت برنامه هفتگی...')
        schedule_data = [
            {'classroom': classrooms[0], 'day': 'saturday', 'start': time(8, 0), 'end': time(9, 30), 'room': '۱۰۱'},
            {'classroom': classrooms[0], 'day': 'sunday', 'start': time(10, 0), 'end': time(11, 30), 'room': '۱۰۲'},
            {'classroom': classrooms[2], 'day': 'monday', 'start': time(8, 0), 'end': time(9, 30), 'room': '۲۰۱'},
            {'classroom': classrooms[4], 'day': 'tuesday', 'start': time(13, 0), 'end': time(14, 30), 'room': '۳۰۱'},
            {'classroom': classrooms[6], 'day': 'wednesday', 'start': time(9, 0), 'end': time(10, 30), 'room': '۵۰۱'},
        ]
        
        for item in schedule_data:
            WeeklySchedule.objects.create(
                classroom=item['classroom'], 
                day_of_week=item['day'],
                start_time=item['start'], 
                end_time=item['end'], 
                room=item['room']
            )
        
        self.stdout.write(f'   📅 {len(schedule_data)} برنامه هفتگی ساخته شد')
        
        # ===== پایان =====
        self.stdout.write(self.style.SUCCESS('\n✅ داده‌های نمونه با موفقیت و به‌صورت گسترده ایجاد شد!'))
        self.stdout.write(self.style.WARNING('\n🔑 کاربران پیش‌فرض (رمز عبور همه: 12345678):'))
        self.stdout.write(f'   👨‍💼 مدیر: principal1')
        self.stdout.write(f'   👨‍💼 معاون: assistant1')
        self.stdout.write(f'   👨‍🏫 معلم‌ها: teacher1 تا teacher5')
        self.stdout.write(f'   👨‍🎓 دانش‌آموزان: student1 تا student10')