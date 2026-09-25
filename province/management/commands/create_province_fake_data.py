"""
کامند تولید داده‌های فیک و واقع‌گرایانه برای پنل مسئول استانی

استفاده:
    python manage.py create_province_fake_data
    python manage.py create_province_fake_data --provinces=3
    python manage.py create_province_fake_data --provinces=5 --students=50
"""
import random
from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from accounts.models import User, StudentProfile
from national.models import Province, District, School
from dashboard.models import (
    Classroom, ClassSession, AttendanceCheck, AttendanceRecord,
    Question, StudentAnswer, WeeklySchedule, AIGenerationJob,
    AttendanceRequest, AttendanceRequestQuestion, AttendanceResponse,
)
from face.models import FaceProfile, FaceEmbedding, FaceVerificationLog


# ──────────────────────────────────────────────────────────────
#  داده‌های پایه
# ──────────────────────────────────────────────────────────────

PROVINCES = [
    ('تهران', '01', ['منطقه ۱', 'منطقه ۲', 'منطقه ۳', 'منطقه ۴', 'منطقه ۵']),
    ('اصفهان', '02', ['منطقه ۱', 'منطقه ۲', 'منطقه ۳']),
    ('فارس', '03', ['منطقه ۱', 'منطقه ۲', 'منطقه ۳']),
    ('خراسان رضوی', '04', ['منطقه ۱', 'منطقه ۲']),
    ('آذربایجان شرقی', '05', ['منطقه ۱', 'منطقه ۲']),
]

SCHOOL_NAMES = [
    'دبیرستان شهید بهشتی', 'دبیرستان شهید رجایی', 'هنرستان فنی شهید چمران',
    'دبیرستان علامه طباطبایی', 'هنرستان صنعتی امام خمینی', 'دبیرستان خوارزمی',
    'دبیرستان فرزانگان', 'هنرستان شهید باهنر', 'دبیرستان ابن‌سینا',
    'دبیرستان شهید مطهری', 'هنرستان شهید فهمیده', 'دبیرستان کوشش',
]

FIRST_NAMES = ['رضا', 'علی', 'محمد', 'حسین', 'مهدی', 'امیر', 'سارا', 'نیکا',
               'پرهام', 'آرمین', 'کیان', 'زهرا', 'فاطمه', 'مریم', 'نرگس',
               'هانیه', 'پارمیس', 'یلدا', 'مبینا', 'ستایش']

LAST_NAMES = ['احمدی', 'محمدی', 'کریمی', 'رضوی', 'نوری', 'جعفری', 'تقوی',
              'کاظمی', 'صادقی', 'مرادی', 'حسینی', 'اکبری', 'قاسمی',
              'عباسی', 'موسوی', 'هاشمی', 'نجفی', 'رحیمی', 'سلطانی']

TEACHER_FIRST = ['علی', 'مریم', 'حسن', 'زهرا', 'رضا', 'مینا', 'جواد', 'سکینه']
TEACHER_LAST = ['محمدی', 'احمدی', 'کریمی', 'رضوی', 'نوری', 'جعفری', 'تقوی', 'کاظمی']

SUBJECTS = ['برنامه‌نویسی پایتون', 'شبکه‌های کامپیوتری', 'مدارهای الکتریکی',
            'ریاضی پایه دهم', 'فیزیک پایه دهم', 'ادبیات فارسی', 'زیست‌شناسی',
            'پایگاه داده', 'نصب و راه‌اندازی', 'سیستم‌عامل']

TOPICS = ['مقدمه و مفاهیم پایه', 'مفاهیم پیشرفته', 'تمرین عملی',
          'ارزیابی میان‌ترم', 'جمع‌بندی', 'مبحث جدید', 'مرور و حل تمرین']

QUESTION_TEXTS = [
    'کدام گزینه تعریف صحیح متغیر در برنامه‌نویسی است؟',
    'در یک مدار سری، جریان الکتریکی در تمام نقاط چگونه است؟',
    'حاصل عبارت ۲ به توان ۱۰ چند است؟',
    'کدام پروتکل برای انتقال فایل در شبکه استفاده می‌شود؟',
    'در پایتون، کدام کلمه کلیدی برای تعریف تابع استفاده می‌شود؟',
    'واحد اندازه‌گیری مقاومت الکتریکی چیست؟',
    'کدام ساختار داده به صورت پشته (Stack) عمل می‌کند؟',
    'در شبکه‌های کامپیوتری، آدرس IP نسخه ۴ چند بیتی است؟',
]


class Command(BaseCommand):
    help = 'تولید داده‌های فیک واقع‌گرایانه برای داشبورد مسئول استانی'

    def add_arguments(self, parser):
        parser.add_argument('--provinces', type=int, default=3,
                            help='تعداد استان‌ها (پیش‌فرض: ۳)')
        parser.add_argument('--students', type=int, default=30,
                            help='تعداد دانش‌آموزان (پیش‌فرض: ۳۰)')

    @transaction.atomic
    def handle(self, *args, **options):
        province_count = min(options['provinces'], len(PROVINCES))
        student_count = options['students']
        now = timezone.now()

        self.stdout.write(self.style.WARNING('🔄 در حال پاکسازی داده‌های قدیمی...'))
        self._cleanup()

        self.stdout.write(self.style.WARNING('🏗️  در حال ساخت ساختار سازمانی...'))
        provinces, districts, schools = self._create_structure(province_count)

        self.stdout.write(self.style.WARNING('👥 در حال ساخت کاربران...'))
        teachers, students_map, province_admins = self._create_users(
            provinces, student_count)

        self.stdout.write(self.style.WARNING('📚 در حال ساخت کلاس‌ها...'))
        classrooms = self._create_classrooms(schools, teachers, students_map)

        self.stdout.write(self.style.WARNING('📅 در حال ساخت جلسات و حضور و غیاب...'))
        self._create_sessions_attendance(classrooms, now)

        self.stdout.write(self.style.WARNING('❓ در حال ساخت سوالات و پاسخ‌ها...'))
        self._create_questions_answers(classrooms)

        self.stdout.write(self.style.WARNING('📸 در حال ساخت درخواست‌های حضور و غیاب...'))
        self._create_attendance_requests(classrooms, students_map)

        self.stdout.write(self.style.WARNING('🤖 در حال ساخت داده‌های هوش مصنوعی...'))
        self._create_ai_data(classrooms, teachers)

        self.stdout.write(self.style.WARNING('🔐 در حال ساخت داده‌های احراز هویت چهره...'))
        self._create_face_data(students_map, classrooms, now)

        self.stdout.write(self.style.WARNING('📆 در حال ساخت برنامه هفتگی...'))
        self._create_schedules(classrooms)

        # ── خلاصه ──
        self.stdout.write(self.style.SUCCESS('\n✅ داده‌های فیک با موفقیت ساخته شد!\n'))
        self.stdout.write(f'   🏛️  استان‌ها:            {Province.objects.count()}')
        self.stdout.write(f'   📍 مناطق:               {District.objects.count()}')
        self.stdout.write(f'   🏫 مدارس:               {School.objects.count()}')
        self.stdout.write(f'   👨‍🎓 دانش‌آموزان:          {User.objects.filter(role="student").count()}')
        self.stdout.write(f'   👨‍🏫 معلمان:              {User.objects.filter(role="teacher").count()}')
        self.stdout.write(f'   👨‍💼 مسئولان استانی:      {User.objects.filter(role="province_admin").count()}')
        self.stdout.write(f'   📚 کلاس‌ها:              {Classroom.objects.count()}')
        self.stdout.write(f'   📅 جلسات:               {ClassSession.objects.count()}')
        self.stdout.write(f'   ❓ سوالات:               {Question.objects.count()}')
        self.stdout.write(f'   📝 پاسخ‌ها:              {StudentAnswer.objects.count()}')
        self.stdout.write(f'   📸 احراز هویت چهره:      {FaceVerificationLog.objects.count()}')

        self.stdout.write(self.style.WARNING('\n🔑 کاربران پیش‌فرض (رمز عبور همه: 12345678):'))
        for admin in province_admins:
            self.stdout.write(f'   👨‍💼 {admin.username} → استان {admin.province.name}')
        self.stdout.write('   👨‍🏫 teacher_1 تا teacher_8')
        self.stdout.write(f'   👨‍🎓 student_1 تا student_{student_count}')

    # ──────────────────────────────────────────────
    def _cleanup(self):
        StudentAnswer.objects.all().delete()
        AttendanceRequestQuestion.objects.all().delete()
        AttendanceResponse.objects.all().delete()
        AttendanceRequest.objects.all().delete()
        Question.objects.all().delete()
        AIGenerationJob.objects.all().delete()
        AttendanceRecord.objects.all().delete()
        AttendanceCheck.objects.all().delete()
        ClassSession.objects.all().delete()
        WeeklySchedule.objects.all().delete()
        FaceVerificationLog.objects.all().delete()
        FaceEmbedding.objects.all().delete()
        FaceProfile.objects.all().delete()
        Classroom.objects.all().delete()
        StudentProfile.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()
        School.objects.all().delete()
        District.objects.all().delete()
        Province.objects.all().delete()

    # ──────────────────────────────────────────────
    def _create_structure(self, province_count):
        provinces, districts, schools = [], [], []

        for p_name, p_code, district_names in PROVINCES[:province_count]:
            province = Province.objects.create(name=p_name, code=p_code)
            provinces.append(province)

            for d_name in district_names:
                district = District.objects.create(
                    province=province, name=d_name,
                    code=f'{p_code}{len(districts)+1:02d}')
                districts.append(district)

                num_schools = random.randint(2, 4)
                for s in random.sample(SCHOOL_NAMES, num_schools):
                    school = School.objects.create(
                        district=district,
                        name=f'{s} - {district.name}',
                        school_type=random.choice(
                            ['public', 'public', 'technical', 'private']),
                        phone=f'021-{random.randint(22000000, 88999999)}',
                        is_active=random.random() > 0.05,  # ۵٪ غیرفعال
                    )
                    schools.append(school)

        return provinces, districts, schools

    # ──────────────────────────────────────────────
    def _create_users(self, provinces, student_count):
        teachers = []
        for i in range(8):
            t, _ = User.objects.get_or_create(
                username=f'teacher_{i+1}',
                defaults={
                    'role': 'teacher',
                    'first_name': TEACHER_FIRST[i % len(TEACHER_FIRST)],
                    'last_name': TEACHER_LAST[i % len(TEACHER_LAST)],
                    'email': f'teacher_{i+1}@example.com',
                    'national_id': f'00{random.randint(10000000, 99999999)}',
                })
            t.set_password('12345678')
            t.save()
            teachers.append(t)

        students = []
        for i in range(student_count):
            s, _ = User.objects.get_or_create(
                username=f'student_{i+1}',
                defaults={
                    'role': 'student',
                    'first_name': FIRST_NAMES[i % len(FIRST_NAMES)],
                    'last_name': LAST_NAMES[i % len(LAST_NAMES)],
                    'email': f'student_{i+1}@example.com',
                    'national_id': f'00{random.randint(10000000, 99999999)}',
                })
            s.set_password('12345678')
            s.save()
            StudentProfile.objects.get_or_create(
                user=s,
                defaults={
                    'father_name': random.choice(FIRST_NAMES),
                    'parent_phone': f'0912{random.randint(1000000, 9999999)}',
                    'phone': f'0912{random.randint(1000000, 9999999)}',
                    'city': 'تهران',
                })
            students.append(s)

        province_admins = []
        for i, province in enumerate(provinces):
            admin, _ = User.objects.get_or_create(
                username=f'admin_{province.code}',
                defaults={
                    'role': 'province_admin',
                    'province': province,
                    'first_name': 'مسئول',
                    'last_name': f'استان {province.name}',
                    'email': f'admin_{province.code}@example.com',
                })
            admin.set_password('12345678')
            admin.province = province
            admin.role = 'province_admin'
            admin.save()
            province_admins.append(admin)

        # توزیع دانش‌آموزان بین استان‌ها
        students_map = {}
        per_province = max(1, len(students) // len(provinces))
        idx = 0
        for province in provinces:
            end = idx + per_province
            students_map[province.id] = students[idx:end]
            idx = end
        # باقی‌مانده به استان اول
        if idx < len(students):
            students_map[provinces[0].id].extend(students[idx:])

        return teachers, students_map, province_admins

    # ──────────────────────────────────────────────
    def _create_classrooms(self, schools, teachers, students_map):
        classrooms = []
        school_provinces = {s.id: s.district.province for s in schools}

        for school in schools:
            if not school.is_active:
                continue
            province = school_provinces[school.id]
            students_in_province = students_map.get(province.id, [])

            for j in range(random.randint(2, 4)):
                teacher = random.choice(teachers)
                subject = random.choice(SUBJECTS)
                grade = random.choice(['10', '11', '12'])
                field = random.choice(['computer', 'electrical', 'math', 'experimental'])

                classroom = Classroom.objects.create(
                    name=f'{grade}{random.choice(["۰۱","۰۲","۰۳"])} {school.district.name}',
                    subject=subject,
                    grade=grade,
                    field=field,
                    teacher_name=f'{teacher.first_name} {teacher.last_name}',
                    teacher=teacher,
                    school=school,
                )
                if students_in_province:
                    selected = random.sample(
                        students_in_province,
                        min(random.randint(4, 10), len(students_in_province)))
                    classroom.students.set(selected)
                classrooms.append(classroom)

        return classrooms

    # ──────────────────────────────────────────────
    def _create_sessions_attendance(self, classrooms, now):
        for classroom in classrooms:
            num_sessions = random.randint(8, 15)
            for i in range(num_sessions):
                session = ClassSession.objects.create(
                    classroom=classroom,
                    topic=f'جلسه {i+1}: {random.choice(TOPICS)}',
                )
                session_date = now - timedelta(
                    days=random.randint(0, 30),
                    hours=random.randint(0, 12))
                ClassSession.objects.filter(id=session.id).update(
                    session_date=session_date)

                check = AttendanceCheck.objects.create(session=session)

                for student in classroom.students.all():
                    status = random.choices(
                        ['present', 'absent'],
                        weights=[random.uniform(75, 95), 100],
                    )[0]
                    AttendanceRecord.objects.create(
                        attendance_check=check,
                        student=student,
                        status=status,
                    )

    # ──────────────────────────────────────────────
    def _create_questions_answers(self, classrooms):
        for classroom in classrooms:
            num_questions = random.randint(5, 10)
            for i in range(num_questions):
                q = Question.objects.create(
                    classroom=classroom,
                    session=random.choice(list(classroom.sessions.all()))
                    if classroom.sessions.exists() else None,
                    topic=random.choice(TOPICS),
                    source=random.choice(['ai', 'manual']),
                    review_status='approved',
                    is_approved=True,
                    text=f'{random.choice(QUESTION_TEXTS)} (کلاس {classroom.name})',
                    choice_a='گزینه الف - پاسخ صحیح',
                    choice_b='گزینه ب - نادرست',
                    choice_c='گزینه ج - نادرست',
                    choice_d='گزینه د - نادرست',
                    correct_answer='a',
                    timer_seconds=random.choice([60, 120, 180, 300]),
                )
                for student in classroom.students.all():
                    is_correct = random.choices([True, False], weights=[70, 30])[0]
                    StudentAnswer.objects.create(
                        question=q,
                        student=student,
                        selected_choice='a' if is_correct else random.choice(['b', 'c', 'd']),
                        is_correct=is_correct,
                    )

    # ──────────────────────────────────────────────
    def _create_attendance_requests(self, classrooms, students_map):
        for classroom in classrooms:
            if not classroom.students.exists():
                continue
            session = classroom.sessions.first()
            if not session:
                continue

            teacher = classroom.teacher
            if not teacher:
                continue

            req_type = random.choice(['face_only', 'face_and_question', 'question_only'])
            req = AttendanceRequest.objects.create(
                teacher=teacher,
                classroom=classroom,
                session=session,
                request_type=req_type,
                status='finished',
                face_time_seconds=120,
            )

            questions = list(classroom.questions.filter(is_approved=True)[:3])
            for idx, q in enumerate(questions, 1):
                AttendanceRequestQuestion.objects.create(
                    attendance_request=req,
                    question=q,
                    order=idx,
                    timer_seconds=q.timer_seconds,
                )

            for response in req.responses.all():
                auto_status = random.choices(
                    ['present', 'present', 'present', 'suspicious', 'absent_mismatch'],
                    weights=[60, 15, 10, 8, 7],
                )[0]
                if auto_status == 'present':
                    response.auto_status = 'present'
                    response.final_status = 'present'
                    response.face_verified = True
                    response.face_status = 'VERIFIED'
                    response.similarity_score = round(random.uniform(0.75, 0.98), 3)
                    response.liveness_status = 'passed'
                elif auto_status == 'suspicious':
                    response.auto_status = 'suspicious'
                    response.final_status = 'pending'
                    response.face_verified = False
                    response.face_status = 'SUSPICIOUS'
                    response.similarity_score = round(random.uniform(0.25, 0.44), 3)
                    response.failure_reason = 'MATCH_BELOW_THRESHOLD'
                else:
                    response.auto_status = 'absent_mismatch'
                    response.final_status = 'absent'
                    response.face_verified = False
                    response.face_status = 'FAILED'
                    response.similarity_score = round(random.uniform(0.10, 0.30), 3)
                response.face_submitted_at = timezone.now()
                response.save()

    # ──────────────────────────────────────────────
    def _create_ai_data(self, classrooms, teachers):
        for classroom in classrooms[:10]:
            teacher = classroom.teacher or random.choice(teachers)
            status = random.choices(
                ['completed', 'completed', 'failed', 'pending'],
                weights=[60, 20, 10, 10],
            )[0]
            job = AIGenerationJob.objects.create(
                teacher=teacher,
                classroom=classroom,
                topic=random.choice(TOPICS),
                prompt=f'لطفاً ۵ سوال چهارگزینه‌ای از مبحث {random.choice(TOPICS)} طراحی کن.',
                requested_count=5,
                default_timer_seconds=180,
                status=status,
            )
            if status == 'completed':
                for i in range(random.randint(2, 5)):
                    Question.objects.create(
                        classroom=classroom,
                        created_by=teacher,
                        ai_job=job,
                        source='ai',
                        review_status=random.choice(['approved', 'approved', 'pending', 'rejected']),
                        is_approved=random.random() > 0.3,
                        topic=job.topic,
                        text=f'سوال تولیدشده توسط هوش مصنوعی شماره {i+1} ({classroom.name})',
                        choice_a='پاسخ صحیح',
                        choice_b='غلط ۱',
                        choice_c='غلط ۲',
                        choice_d='غلط ۳',
                        correct_answer='a',
                        timer_seconds=180,
                    )

    # ──────────────────────────────────────────────
    def _create_face_data(self, students_map, classrooms, now):
        all_students = User.objects.filter(role='student')

        for student in all_students:
            FaceProfile.objects.get_or_create(
                student=student,
                defaults={
                    'enrollment_status': random.choices(
                        ['enrolled', 'pending'], weights=[85, 15])[0],
                    'reference_images_count': random.randint(0, 5),
                    'last_enrollment_at': now - timedelta(days=random.randint(0, 30)),
                })

            if random.random() > 0.15:
                for _ in range(random.randint(3, 5)):
                    FaceEmbedding.objects.create(
                        student=student,
                        embedding=b'0' * 2048,
                        model_name='mock',
                        model_version='test',
                        embedding_dimension=512,
                        source_image=f'ref-{student.username}',
                        is_active=True,
                    )

        # لاگ‌های احراز هویت
        for i in range(200):
            student = random.choice(list(all_students))
            status = random.choices(
                ['verified', 'verified', 'suspicious', 'failed', 'error'],
                weights=[55, 20, 10, 8, 7],
            )[0]
            FaceVerificationLog.objects.create(
                student=student,
                status=status,
                similarity_score=round(random.uniform(0.2, 0.99), 3),
                liveness_passed=status == 'verified',
                total_frames=random.randint(5, 15),
                valid_frames=random.randint(3, 12),
                failure_reason='' if status == 'verified' else random.choice(
                    ['MATCH_BELOW_THRESHOLD', 'LIVENESS_FAILED', 'NO_FACE']),
                created_at=now - timedelta(days=random.randint(0, 30)),
            )

    # ──────────────────────────────────────────────
    def _create_schedules(self, classrooms):
        days = ['saturday', 'sunday', 'monday', 'tuesday', 'wednesday']
        times = [(time(8, 0), time(9, 30)), (time(10, 0), time(11, 30)),
                 (time(13, 0), time(14, 30))]

        for classroom in classrooms:
            for _ in range(random.randint(2, 4)):
                start, end = random.choice(times)
                WeeklySchedule.objects.create(
                    classroom=classroom,
                    day_of_week=random.choice(days),
                    start_time=start,
                    end_time=end,
                    room=str(random.randint(101, 305)),
                )