# district/management/commands/create_district_fake_data.py
"""
کامند تولید داده‌های فیک و واقع‌گرایانه برای پنل مسئول منطقه (District Admin)

ساختار داده‌های تولیدشده:
  استان ← منطقه ← مدارس ← کلاس‌ها ← دانش‌آموزان / معلمان / مدیران مدارس

استفاده:
  python manage.py create_district_fake_data
  python manage.py create_district_fake_data --province=تهران --district="منطقه ۱"
  python manage.py create_district_fake_data --schools=6 --students=50 --teachers=10
  python manage.py create_district_fake_data --username=admin_d1 --password=12345678
"""

import random
from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User, StudentProfile
from dashboard.models import (
    AIGenerationJob,
    AttendanceCheck,
    AttendanceRecord,
    AttendanceRequest,
    AttendanceRequestQuestion,
    AttendanceResponse,
    ClassSession,
    Classroom,
    Question,
    StudentAnswer,
    WeeklySchedule,
)
from face.models import FaceEmbedding, FaceProfile, FaceVerificationLog
from national.models import District, Province, School

# ──────────────────────────────────────────────────────────────
#  داده‌های پایه
# ──────────────────────────────────────────────────────────────

DEFAULT_PROVINCE = 'تهران'
DEFAULT_DISTRICT = 'منطقه ۱'

SCHOOL_NAMES = [
    'دبیرستان شهید بهشتی',
    'دبیرستان شهید رجایی',
    'هنرستان فنی شهید چمران',
    'دبیرستان علامه طباطبایی',
    'هنرستان صنعتی امام خمینی',
    'دبیرستان خوارزمی',
    'دبیرستان فرزانگان',
    'هنرستان شهید باهنر',
    'دبیرستان ابن‌سینا',
    'دبیرستان شهید مطهری',
    'هنرستان شهید فهمیده',
    'دبیرستان کوشش',
]

SCHOOL_TYPES = ['public', 'public', 'public', 'technical', 'private', 'special']

STUDENT_FIRST_NAMES = [
    'رضا', 'علی', 'محمد', 'حسین', 'مهدی', 'امیر', 'سارا', 'نیکا',
    'پرهام', 'آرمین', 'کیان', 'زهرا', 'فاطمه', 'مریم', 'نرگس',
    'هانیه', 'پارمیس', 'یلدا', 'مبینا', 'ستایش', 'ابوالفضل',
    'دانیال', 'آرش', 'بهار', 'ترانه',
]

STUDENT_LAST_NAMES = [
    'احمدی', 'محمدی', 'کریمی', 'رضوی', 'نوری', 'جعفری', 'تقوی',
    'کاظمی', 'صادقی', 'مرادی', 'حسینی', 'اکبری', 'قاسمی',
    'عباسی', 'موسوی', 'هاشمی', 'نجفی', 'رحیمی', 'سلطانی',
    'فرهادی', 'جمشیدی', 'بهرامی',
]

TEACHER_FIRST_NAMES = [
    'علی', 'مریم', 'حسن', 'زهرا', 'رضا', 'مینا', 'جواد', 'سکینه',
    'محمد', 'فاطمه', 'حسین', 'نرگس',
]

TEACHER_LAST_NAMES = [
    'محمدی', 'احمدی', 'کریمی', 'رضوی', 'نوری', 'جعفری',
    'تقوی', 'کاظمی', 'صادقی', 'مرادی',
]

PRINCIPAL_FIRST_NAMES = ['دکتر احمد', 'دکتر محمد', 'مهندس رضا', 'دکتر زهرا', 'دکتر مریم']
PRINCIPAL_LAST_NAMES = ['مدیری', 'رهبری', 'سرپرست', 'ناظمی', 'مدیرزاده']

SUBJECTS = [
    'برنامه‌نویسی پایتون',
    'شبکه‌های کامپیوتری',
    'مدارهای الکتریکی',
    'ریاضی پایه دهم',
    'فیزیک پایه دهم',
    'ادبیات فارسی',
    'زیست‌شناسی',
    'پایگاه داده',
    'نصب و راه‌اندازی',
    'سیستم‌عامل',
    'شیمی',
    'عربی',
]

TOPICS = [
    'مقدمه و مفاهیم پایه',
    'مفاهیم پیشرفته',
    'تمرین عملی',
    'ارزیابی میان‌ترم',
    'جمع‌بندی',
    'مبحث جدید',
    'مرور و حل تمرین',
    'پروژه کلاسی',
]

QUESTION_TEXTS = [
    'کدام گزینه تعریف صحیح متغیر در برنامه‌نویسی است؟',
    'در یک مدار سری، جریان الکتریکی در تمام نقاط چگونه است؟',
    'حاصل عبارت ۲ به توان ۱۰ چند است؟',
    'کدام پروتکل برای انتقال فایل در شبکه استفاده می‌شود؟',
    'در پایتون، کدام کلمه کلیدی برای تعریف تابع استفاده می‌شود؟',
    'واحد اندازه‌گیری مقاومت الکتریکی چیست؟',
    'کدام ساختار داده به صورت پشته (Stack) عمل می‌کند؟',
    'در شبکه‌های کامپیوتری، آدرس IP نسخه ۴ چند بیتی است؟',
    'نماد شیمیایی اکسیژن کدام است؟',
    'مترادف کلمه «فراوان» کدام گزینه است؟',
]

GRADES = ['10', '11', '12']
FIELDS = ['computer', 'electrical', 'math', 'experimental', 'humanities', 'accounting']
WEEKDAYS = ['saturday', 'sunday', 'monday', 'tuesday', 'wednesday']
TIME_SLOTS = [
    (time(8, 0), time(9, 30)),
    (time(10, 0), time(11, 30)),
    (time(13, 0), time(14, 30)),
]


class Command(BaseCommand):
    help = 'تولید داده‌های فیک واقع‌گرایانه برای داشبورد مسئول منطقه (District Admin)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--province', type=str, default=DEFAULT_PROVINCE,
            help=f'نام استان (پیش‌فرض: {DEFAULT_PROVINCE})',
        )
        parser.add_argument(
            '--district', type=str, default=DEFAULT_DISTRICT,
            help=f'نام منطقه (پیش‌فرض: {DEFAULT_DISTRICT})',
        )
        parser.add_argument(
            '--schools', type=int, default=4,
            help='تعداد مدارس (پیش‌فرض: ۴)',
        )
        parser.add_argument(
            '--students', type=int, default=40,
            help='تعداد دانش‌آموزان (پیش‌فرض: ۴۰)',
        )
        parser.add_argument(
            '--teachers', type=int, default=10,
            help='تعداد معلمان (پیش‌فرض: ۱۰)',
        )
        parser.add_argument(
            '--username', type=str, default='district_admin',
            help='نام کاربری مسئول منطقه (پیش‌فرض: district_admin)',
        )
        parser.add_argument(
            '--password', type=str, default='12345678',
            help='رمز عبور تمام کاربران (پیش‌فرض: 12345678)',
        )
        parser.add_argument(
            '--days', type=int, default=30,
            help='تعداد روز گذشته برای تولید داده (پیش‌فرض: ۳۰)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        province_name = options['province']
        district_name = options['district']
        school_count = max(1, min(options['schools'], len(SCHOOL_NAMES)))
        student_count = options['students']
        teacher_count = options['teachers']
        admin_username = options['username']
        password = options['password']
        days_back = options['days']

        now = timezone.now()

        self.stdout.write(self.style.WARNING('🔄 در حال پاکسازی داده‌های قدیمی...'))
        self._cleanup()

        self.stdout.write(self.style.WARNING('🏛️  در حال ساخت ساختار سازمانی (استان/منطقه)...'))
        province = self._create_province(province_name)
        district = self._create_district(province, district_name)

        self.stdout.write(self.style.WARNING('🏫 در حال ساخت مدارس...'))
        schools = self._create_schools(district, school_count)

        self.stdout.write(self.style.WARNING('👥 در حال ساخت کاربران...'))
        district_admin = self._create_district_admin(district, admin_username, password)
        teachers = self._create_teachers(teacher_count, password)
        principals = self._create_principals(schools, password)
        students = self._create_students(student_count, password)

        self.stdout.write(self.style.WARNING('📚 در حال ساخت کلاس‌ها...'))
        classrooms = self._create_classrooms(schools, teachers, students)

        self.stdout.write(self.style.WARNING('📅 در حال ساخت جلسات و حضور و غیاب...'))
        self._create_sessions_and_attendance(classrooms, days_back)

        self.stdout.write(self.style.WARNING('❓ در حال ساخت سوالات و پاسخ‌ها...'))
        self._create_questions_and_answers(classrooms)

        self.stdout.write(self.style.WARNING('📸 در حال ساخت درخواست‌های حضور و غیاب...'))
        self._create_attendance_requests(classrooms)

        self.stdout.write(self.style.WARNING('🤖 در حال ساخت داده‌های هوش مصنوعی...'))
        self._create_ai_data(classrooms)

        self.stdout.write(self.style.WARNING('🔐 در حال ساخت داده‌های احراز هویت چهره...'))
        self._create_face_data(students, classrooms, days_back)

        self.stdout.write(self.style.WARNING('📆 در حال ساخت برنامه هفتگی...'))
        self._create_weekly_schedules(classrooms)

        # ── خلاصه ──
        self.stdout.write(self.style.SUCCESS('\n✅ داده‌های فیک منطقه با موفقیت ساخته شد!\n'))
        self.stdout.write(f'   🏛️  استان:                 {province.name}')
        self.stdout.write(f'   📍 منطقه:                 {district.name}')
        self.stdout.write(f'   🏫 مدارس:                 {School.objects.filter(district=district).count()}')
        self.stdout.write(f'   👨‍💼 مسئول منطقه:          {district_admin.username}')
        self.stdout.write(f'   👨‍🏫 مدیران مدارس:          {len(principals)}')
        self.stdout.write(f'   👨‍🏫 معلمان:                {User.objects.filter(role="teacher").count()}')
        self.stdout.write(f'   👨‍🎓 دانش‌آموزان:            {User.objects.filter(role="student").count()}')
        self.stdout.write(f'   📚 کلاس‌ها:                {Classroom.objects.count()}')
        self.stdout.write(f'   📅 جلسات:                 {ClassSession.objects.count()}')
        self.stdout.write(f'   ❓ سوالات:                 {Question.objects.count()}')
        self.stdout.write(f'   📝 پاسخ‌ها:                {StudentAnswer.objects.count()}')
        self.stdout.write(f'   📸 احراز هویت چهره:        {FaceVerificationLog.objects.count()}')

        self.stdout.write(self.style.WARNING(f'\n🔑 کاربران پیش‌فرض (رمز عبور همه: {password}):'))
        self.stdout.write(f'   👨‍💼 {district_admin.username} → منطقه {district.name} (استان {province.name})')
        self.stdout.write(f'   👨‍🏫 معلمان: teacher_1 تا teacher_{teacher_count}')
        self.stdout.write(f'   👨‍🎓 دانش‌آموزان: student_1 تا student_{student_count}')
        self.stdout.write(f'   🏫 مدیران مدارس: principal_1 تا principal_{len(principals)}')

    # ──────────────────────────────────────────────
    #  پاکسازی
    # ──────────────────────────────────────────────
    def _cleanup(self):
        """حذف کامل داده‌های قدیمی برای جلوگیری از تداخل"""
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
        User.objects.filter(is_superuser=False).delete()
        School.objects.all().delete()
        District.objects.all().delete()
        Province.objects.all().delete()

    # ──────────────────────────────────────────────
    #  ساختار سازمانی
    # ──────────────────────────────────────────────
    def _create_province(self, name):
        province, _ = Province.objects.get_or_create(
            name=name,
            defaults={'code': f'{random.randint(10, 99)}'},
        )
        return province

    def _create_district(self, province, name):
        district, _ = District.objects.get_or_create(
            province=province,
            name=name,
            defaults={'code': f'{province.code}{random.randint(10, 99)}'},
        )
        return district

    def _create_schools(self, district, count):
        schools = []
        selected_names = random.sample(SCHOOL_NAMES, count)
        for name in selected_names:
            school = School.objects.create(
                district=district,
                name=name,
                school_type=random.choice(SCHOOL_TYPES),
                address=f'{district.province.name}، {district.name}، خیابان نمونه، پلاک {random.randint(1, 200)}',
                phone=f'021-{random.randint(22000000, 88999999)}',
                is_active=random.random() > 0.05,
            )
            schools.append(school)
        return schools

    # ──────────────────────────────────────────────
    #  کاربران
    # ──────────────────────────────────────────────
    def _create_district_admin(self, district, username, password):
        admin = User.objects.create_user(
            username=username,
            password=password,
            role='district_admin',
            district=district,
            first_name='مسئول',
            last_name=f'منطقه {district.name}',
            email=f'{username}@example.com',
            national_id=f'00{random.randint(10000000, 99999999)}',
        )
        return admin

    def _create_teachers(self, count, password):
        teachers = []
        for i in range(count):
            teacher = User.objects.create_user(
                username=f'teacher_{i + 1}',
                password=password,
                role='teacher',
                first_name=TEACHER_FIRST_NAMES[i % len(TEACHER_FIRST_NAMES)],
                last_name=TEACHER_LAST_NAMES[i % len(TEACHER_LAST_NAMES)],
                email=f'teacher_{i + 1}@example.com',
                national_id=f'00{random.randint(10000000, 99999999)}',
            )
            teachers.append(teacher)
        return teachers

    def _create_principals(self, schools, password):
        principals = []
        for i, school in enumerate(schools):
            principal = User.objects.create_user(
                username=f'principal_{i + 1}',
                password=password,
                role='principal',
                first_name=PRINCIPAL_FIRST_NAMES[i % len(PRINCIPAL_FIRST_NAMES)],
                last_name=PRINCIPAL_LAST_NAMES[i % len(PRINCIPAL_LAST_NAMES)],
                email=f'principal_{i + 1}@example.com',
                national_id=f'00{random.randint(10000000, 99999999)}',
            )
            school.principal = principal
            school.save(update_fields=['principal'])
            principals.append(principal)
        return principals

    def _create_students(self, count, password):
        students = []
        for i in range(count):
            student = User.objects.create_user(
                username=f'student_{i + 1}',
                password=password,
                role='student',
                first_name=STUDENT_FIRST_NAMES[i % len(STUDENT_FIRST_NAMES)],
                last_name=STUDENT_LAST_NAMES[i % len(STUDENT_LAST_NAMES)],
                email=f'student_{i + 1}@example.com',
                national_id=f'00{random.randint(10000000, 99999999)}',
            )
            StudentProfile.objects.create(
                user=student,
                father_name=random.choice(STUDENT_FIRST_NAMES),
                mother_name=random.choice(STUDENT_FIRST_NAMES),
                parent_phone=f'0912{random.randint(1000000, 9999999)}',
                phone=f'0912{random.randint(1000000, 9999999)}',
                city=random.choice(['تهران', 'کرج', 'قم', 'اصفهان']),
                enrollment_date=timezone.now().date() - timedelta(days=random.randint(30, 365)),
            )
            students.append(student)
        return students

    # ──────────────────────────────────────────────
    #  کلاس‌ها
    # ──────────────────────────────────────────────
    def _create_classrooms(self, schools, teachers, students):
        classrooms = []
        for school in schools:
            if not school.is_active:
                continue
            num_classes = random.randint(2, 5)
            for j in range(num_classes):
                teacher = random.choice(teachers)
                classroom = Classroom.objects.create(
                    name=f'{random.choice(GRADES)}{random.choice(["۰۱", "۰۲", "۰۳"])} {school.name[:15]}',
                    subject=random.choice(SUBJECTS),
                    grade=random.choice(GRADES),
                    field=random.choice(FIELDS),
                    teacher_name=f'{teacher.first_name} {teacher.last_name}',
                    teacher=teacher,
                    school=school,
                )
                # تخصیص ۵ تا ۱۲ دانش‌آموز به هر کلاس
                if students:
                    selected = random.sample(
                        students,
                        min(random.randint(5, 12), len(students)),
                    )
                    classroom.students.set(selected)
                classrooms.append(classroom)
        return classrooms

    # ──────────────────────────────────────────────
    #  جلسات و حضور و غیاب
    # ──────────────────────────────────────────────
    def _create_sessions_and_attendance(self, classrooms, days_back):
        now = timezone.now()
        for classroom in classrooms:
            num_sessions = random.randint(8, 15)
            for i in range(num_sessions):
                session = ClassSession.objects.create(
                    classroom=classroom,
                    topic=f'جلسه {i + 1}: {random.choice(TOPICS)}',
                )
                session_date = now - timedelta(
                    days=random.randint(0, days_back),
                    hours=random.randint(0, 12),
                )
                ClassSession.objects.filter(id=session.id).update(session_date=session_date)

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
    #  سوالات و پاسخ‌ها
    # ──────────────────────────────────────────────
    def _create_questions_and_answers(self, classrooms):
        for classroom in classrooms:
            num_questions = random.randint(5, 10)
            sessions = list(classroom.sessions.all())
            for i in range(num_questions):
                question = Question.objects.create(
                    classroom=classroom,
                    session=random.choice(sessions) if sessions else None,
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
                        question=question,
                        student=student,
                        selected_choice='a' if is_correct else random.choice(['b', 'c', 'd']),
                        is_correct=is_correct,
                    )

    # ──────────────────────────────────────────────
    #  درخواست‌های حضور و غیاب
    # ──────────────────────────────────────────────
    def _create_attendance_requests(self, classrooms):
        for classroom in classrooms:
            if not classroom.students.exists():
                continue
            session = classroom.sessions.first()
            if not session or not classroom.teacher:
                continue

            request_type = random.choice([
                'face_only', 'face_and_question', 'question_only',
            ])
            request = AttendanceRequest.objects.create(
                teacher=classroom.teacher,
                classroom=classroom,
                session=session,
                request_type=request_type,
                status='finished',
                face_time_seconds=120,
            )

            questions = list(classroom.questions.filter(is_approved=True)[:3])
            for idx, q in enumerate(questions, 1):
                AttendanceRequestQuestion.objects.create(
                    attendance_request=request,
                    question=q,
                    order=idx,
                    timer_seconds=q.timer_seconds,
                )

            for response in request.responses.all():
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
    #  داده‌های هوش مصنوعی
    # ──────────────────────────────────────────────
    def _create_ai_data(self, classrooms):
        for classroom in classrooms[:12]:
            teacher = classroom.teacher
            if not teacher:
                continue
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
                        review_status=random.choice([
                            'approved', 'approved', 'pending', 'rejected',
                        ]),
                        is_approved=random.random() > 0.3,
                        topic=job.topic,
                        text=f'سوال تولیدشده توسط هوش مصنوعی شماره {i + 1} ({classroom.name})',
                        choice_a='پاسخ صحیح',
                        choice_b='غلط ۱',
                        choice_c='غلط ۲',
                        choice_d='غلط ۳',
                        correct_answer='a',
                        timer_seconds=180,
                    )

    # ──────────────────────────────────────────────
    #  داده‌های احراز هویت چهره
    # ──────────────────────────────────────────────
    def _create_face_data(self, students, classrooms, days_back):
        now = timezone.now()
        for student in students:
            FaceProfile.objects.create(
                student=student,
                enrollment_status=random.choices(
                    ['enrolled', 'pending'], weights=[85, 15],
                )[0],
                reference_images_count=random.randint(0, 5),
                last_enrollment_at=now - timedelta(days=random.randint(0, days_back)),
            )
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

        # لاگ‌های احراز هویت در محدوده منطقه
        district_students = set()
        for classroom in classrooms:
            district_students.update(classroom.students.all())
        district_students = list(district_students)

        for _ in range(min(200, len(district_students) * 5)):
            student = random.choice(district_students)
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
                failure_reason='' if status == 'verified' else random.choice([
                    'MATCH_BELOW_THRESHOLD', 'LIVENESS_FAILED', 'NO_FACE',
                ]),
                created_at=now - timedelta(days=random.randint(0, days_back)),
            )

    # ──────────────────────────────────────────────
    #  برنامه هفتگی
    # ──────────────────────────────────────────────
    def _create_weekly_schedules(self, classrooms):
        for classroom in classrooms:
            for _ in range(random.randint(2, 4)):
                start, end = random.choice(TIME_SLOTS)
                WeeklySchedule.objects.create(
                    classroom=classroom,
                    day_of_week=random.choice(WEEKDAYS),
                    start_time=start,
                    end_time=end,
                    room=str(random.randint(101, 305)),
                )