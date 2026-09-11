# debug_dashboard.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User
from dashboard.models import Classroom, ClassSession, AttendanceCheck, AttendanceRecord, Question, StudentAnswer

print("=" * 70)
print("🔍 بررسی وضعیت دیتابیس برای داشبورد دانش‌آموز")
print("=" * 70)

# بررسی student1
try:
    student = User.objects.get(username='student1')
    print(f"\n✅ کاربر student1 پیدا شد:")
    print(f"   - ID: {student.id}")
    print(f"   - Role: '{student.role}'")
    print(f"   - نام کامل: {student.get_full_name() or student.username}")
except User.DoesNotExist:
    print("\n❌ کاربر student1 وجود ندارد!")
    print("   لطفاً ابتدا این دستور را اجرا کنید:")
    print("   python manage.py create_sample_data")
    exit()

# بررسی کلاس‌های دانش‌آموز
classrooms = student.enrolled_classes.all()
print(f"\n📚 تعداد کلاس‌های ثبت‌نام شده: {classrooms.count()}")
for classroom in classrooms:
    print(f"   - {classroom.name} ({classroom.subject})")
    print(f"     ID کلاس: {classroom.id}")
    print(f"     تعداد جلسات: {classroom.sessions.count()}")
    print(f"     تعداد سوالات: {classroom.questions.count()}")
    print(f"     آیا student در students است؟ {student in classroom.students.all()}")

# بررسی جلسات
sessions = ClassSession.objects.filter(classroom__students=student)
print(f"\n📅 تعداد جلسات: {sessions.count()}")
for session in sessions:
    print(f"   - جلسه {session.id}: {session.topic or 'بدون موضوع'}")
    print(f"     تعداد حضور و غیاب‌ها: {session.attendance_checks.count()}")

# بررسی AttendanceCheck
checks = AttendanceCheck.objects.filter(session__classroom__students=student)
print(f"\n🔔 تعداد کل حضور و غیاب‌ها: {checks.count()}")

# بررسی رکوردهای حضور
attendance_records = AttendanceRecord.objects.filter(student=student)
print(f"\n✅ تعداد رکوردهای حضور دانش‌آموز: {attendance_records.count()}")
if attendance_records.count() > 0:
    print(f"   حاضر: {attendance_records.filter(status='present').count()}")
    print(f"   غایب: {attendance_records.filter(status='absent').count()}")
    print("\n   نمونه رکوردها:")
    for record in attendance_records[:5]:
        print(f"   - Check ID {record.attendance_check.id}: {record.status}")

# بررسی پاسخ‌ها
answers = StudentAnswer.objects.filter(student=student)
print(f"\n📝 تعداد پاسخ‌های دانش‌آموز: {answers.count()}")
if answers.count() > 0:
    print(f"   درست: {answers.filter(is_correct=True).count()}")
    print(f"   غلط: {answers.filter(is_correct=False).count()}")

# بررسی سوالات
questions = Question.objects.filter(classroom__students=student)
print(f"\n❓ تعداد سوالات: {questions.count()}")

print("\n" + "=" * 70)
print("📊 خلاصه نهایی:")
print(f"   کاربر: {student.username} (role: {student.role})")
print(f"   کلاس‌ها: {classrooms.count()}")
print(f"   جلسات: {sessions.count()}")
print(f"   حضور و غیاب‌ها: {checks.count()}")
print(f"   رکوردهای حضور: {attendance_records.count()}")
print(f"   پاسخ‌ها: {answers.count()}")
print("=" * 70)

# تشخیص مشکل
print("\n🔎 تشخیص مشکل:")
if classrooms.count() == 0:
    print("   ⚠️  مشکل اصلی: دانش‌آموز در هیچ کلاسی ثبت‌نام نشده!")
    print("   راه‌حل: دستور create_sample_data را دوباره اجرا کنید")
elif attendance_records.count() == 0:
    print("   ⚠️  مشکل اصلی: هیچ رکورد حضوری برای دانش‌آموز وجود ندارد!")
elif answers.count() == 0:
    print("   ⚠️  مشکل اصلی: هیچ پاسخی از دانش‌آموز ثبت نشده!")
else:
    print("   ✅ داده‌ها در دیتابیس وجود دارند. مشکل احتمالاً از view یا کاربر لاگین‌شده است.")