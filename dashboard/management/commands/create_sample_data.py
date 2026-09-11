from django.core.management.base import BaseCommand
from accounts.models import User, StudentProfile
from dashboard.models import (
    Classroom, ClassSession, AttendanceCheck,
    AttendanceRecord, Question, StudentAnswer, WeeklySchedule
)
import random
from datetime import time, date


class Command(BaseCommand):
    help = 'ایجاد داده‌های نمونه کامل برای تست سامانه'

    def handle(self, *args, **options):
        self.stdout.write('🔄 در حال ساخت داده‌های نمونه...')
        
        # ===== ساخت معاون =====
        assistant, _ = User.objects.get_or_create(
            username='assistant1',
            defaults={
                'role': 'assistant',
                'first_name': 'محمد',
                'last_name': 'رضایی',
                'email': 'assistant@example.com'
            }
        )
        assistant.set_password('12345678')
        assistant.save()
        
        # ===== ساخت معلم‌ها =====
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
                defaults={
                    'role': 'teacher',
                    'first_name': first,
                    'last_name': last,
                    'email': f'{username}@example.com'
                }
            )
            teacher.set_password('12345678')
            teacher.save()
            teachers.append(teacher)
        
        # ===== ساخت دانش‌آموزان =====
        students_data = [
            ('student1', 'رضا', 'احمدی', '09121234567', 'احمد'),
            ('student2', 'علی', 'محمدی', '09122345678', 'محمد'),
            ('student3', 'حسین', 'کریمی', '09123456789', 'کریم'),
            ('student4', 'مهدی', 'رضوی', '09124567890', 'رضا'),
            ('student5', 'امیر', 'نوری', '09125678901', 'نور'),
        ]
        
        students = []
        for username, first, last, phone, father in students_data:
            student, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'role': 'student',
                    'first_name': first,
                    'last_name': last,
                    'email': f'{username}@example.com',
                    'national_id': f'00{random.randint(10000000, 99999999)}'
                }
            )
            student.set_password('12345678')
            student.save()
            students.append(student)
            
            # ساخت StudentProfile
            profile, _ = StudentProfile.objects.get_or_create(
                user=student,
                defaults={
                    'father_name': father,
                    'parent_phone': phone,
                    'phone': phone,
                    'city': 'تهران',
                }
            )
        
        self.stdout.write(f'   👨‍💼 معاون: assistant1 / 12345678')
        self.stdout.write(f'   👨‍🏫 {len(teachers)} معلم ساخته شد')
        self.stdout.write(f'   👨‍🎓 {len(students)} دانش‌آموز با پروفایل ساخته شد')
        
        # ===== ساخت کلاس‌ها با مقطع و رشته =====
        classrooms_data = [
            # دهم کامپیوتر
            {'name': '۱۰۱ کامپیوتر', 'subject': 'برنامه‌نویسی پایتون', 'grade': '10', 'field': 'computer', 'teacher': teachers[3]},
            {'name': '۱۰۲ کامپیوتر', 'subject': 'شبکه‌های کامپیوتری', 'grade': '10', 'field': 'computer', 'teacher': teachers[3]},
            
            # دهم ریاضی
            {'name': '۲۰۱ ریاضی', 'subject': 'ریاضی پایه دهم', 'grade': '10', 'field': 'math', 'teacher': teachers[0]},
            {'name': '۲۰۲ ریاضی', 'subject': 'فیزیک پایه دهم', 'grade': '10', 'field': 'math', 'teacher': teachers[1]},
            
            # یازدهم برق
            {'name': '۳۰۱ برق', 'subject': 'مدارهای الکتریکی', 'grade': '11', 'field': 'electrical', 'teacher': teachers[4]},
            
            # یازدهم تجربی
            {'name': '۴۰۱ تجربی', 'subject': 'زیست‌شناسی', 'grade': '11', 'field': 'experimental', 'teacher': teachers[1]},
            
            # دوازدهم انسانی
            {'name': '۵۰۱ انسانی', 'subject': 'ادبیات فارسی', 'grade': '12', 'field': 'humanities', 'teacher': teachers[2]},
            {'name': '۵۰۲ انسانی', 'subject': 'تاریخ', 'grade': '12', 'field': 'humanities', 'teacher': teachers[2]},
        ]
        
        classrooms = []
        for data in classrooms_data:
            classroom, _ = Classroom.objects.get_or_create(
                name=data['name'],
                defaults={
                    'subject': data['subject'],
                    'grade': data['grade'],
                    'field': data['field'],
                    'teacher_name': f"{data['teacher'].first_name} {data['teacher'].last_name}",
                    'teacher': data['teacher'],
                }
            )
            classrooms.append(classroom)
        
        # اضافه کردن دانش‌آموزان به کلاس‌ها
        classrooms[0].students.add(*students[:3])  # ۱۰۱ کامپیوتر
        classrooms[1].students.add(*students[1:4])  # ۱۰۲ کامپیوتر
        classrooms[2].students.add(*students[:2])  # ۲۰۱ ریاضی
        classrooms[3].students.add(*students[2:5])  # ۲۰۲ ریاضی
        classrooms[4].students.add(students[0], students[4])  # ۳۰۱ برق
        classrooms[5].students.add(students[1], students[3])  # ۴۰۱ تجربی
        classrooms[6].students.add(students[2], students[4])  # ۵۰۱ انسانی
        classrooms[7].students.add(students[0], students[3])  # ۵۰۲ انسانی
        
        self.stdout.write(f'   📚 {len(classrooms)} کلاس با مقطع و رشته ساخته شد')
        
        # ===== ساخت جلسات و حضور و غیاب =====
        AttendanceRecord.objects.all().delete()
        AttendanceCheck.objects.all().delete()
        ClassSession.objects.all().delete()
        
        for classroom in classrooms[:3]:  # فقط برای ۳ کلاس اول
            for i in range(4):
                session = ClassSession.objects.create(
                    classroom=classroom,
                    topic=f'جلسه {i+1}'
                )
                check = AttendanceCheck.objects.create(session=session)
                
                for student in classroom.students.all():
                    status = random.choices(
                        ['present', 'absent'],
                        weights=[85, 15]
                    )[0]
                    AttendanceRecord.objects.create(
                        attendance_check=check,
                        student=student,
                        status=status
                    )
        
        self.stdout.write(f'   ✅ جلسات و حضور و غیاب ساخته شد')
        
        # ===== ساخت برنامه هفتگی =====
        WeeklySchedule.objects.all().delete()
        
        schedule_data = [
            # برنامه دهم کامپیوتر ۱۰۱
            {'classroom': classrooms[0], 'day': 'saturday', 'start': time(8, 0), 'end': time(9, 30), 'room': '۱۰۱'},
            {'classroom': classrooms[0], 'day': 'saturday', 'start': time(10, 0), 'end': time(11, 30), 'room': '۱۰۲'},
            {'classroom': classrooms[0], 'day': 'sunday', 'start': time(8, 0), 'end': time(9, 30), 'room': '۱۰۱'},
            {'classroom': classrooms[0], 'day': 'monday', 'start': time(11, 0), 'end': time(12, 30), 'room': '۱۰۳'},
            {'classroom': classrooms[0], 'day': 'tuesday', 'start': time(8, 0), 'end': time(9, 30), 'room': '۱۰۱'},
            {'classroom': classrooms[0], 'day': 'wednesday', 'start': time(10, 0), 'end': time(11, 30), 'room': '۱۰۲'},
            
            # برنامه دهم ریاضی ۲۰۱
            {'classroom': classrooms[2], 'day': 'saturday', 'start': time(8, 0), 'end': time(9, 30), 'room': '۲۰۱'},
            {'classroom': classrooms[2], 'day': 'sunday', 'start': time(10, 0), 'end': time(11, 30), 'room': '۲۰۲'},
            {'classroom': classrooms[2], 'day': 'monday', 'start': time(8, 0), 'end': time(9, 30), 'room': '۲۰۱'},
            {'classroom': classrooms[2], 'day': 'tuesday', 'start': time(11, 0), 'end': time(12, 30), 'room': '۲۰۳'},
            {'classroom': classrooms[2], 'day': 'wednesday', 'start': time(8, 0), 'end': time(9, 30), 'room': '۲۰۱'},
            
            # برنامه یازدهم برق ۳۰۱
            {'classroom': classrooms[4], 'day': 'saturday', 'start': time(13, 0), 'end': time(14, 30), 'room': '۳۰۱'},
            {'classroom': classrooms[4], 'day': 'monday', 'start': time(13, 0), 'end': time(14, 30), 'room': '۳۰۱'},
            {'classroom': classrooms[4], 'day': 'wednesday', 'start': time(13, 0), 'end': time(14, 30), 'room': '۳۰۱'},
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
        
        self.stdout.write(self.style.SUCCESS('\n✅ داده‌های نمونه با موفقیت ایجاد شد!'))
        self.stdout.write(self.style.WARNING('\n🔑 کاربران پیش‌فرض (رمز همه: 12345678):'))
        self.stdout.write(f'   👨‍💼 معاون: assistant1')
        self.stdout.write(f'   👨‍🏫 معلم‌ها: teacher1 تا teacher5')
        self.stdout.write(f'   👨‍🎓 دانش‌آموزان: student1 تا student5')