"""خروجی CSV برای پنل مدرسه"""
import csv
import io
from django.http import HttpResponse


class SchoolExportService:

    @staticmethod
    def students_to_csv(students):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="students.csv"'
        response.write('\ufeff')
        writer = csv.writer(io.TextIOWrapper(response, encoding='utf-8-sig', newline=''))
        writer.writerow(['نام', 'نام خانوادگی', 'کد ملی', 'وضعیت'])
        for s in students:
            writer.writerow([
                s.first_name, s.last_name,
                s.national_id or '-', 'فعال'
            ])
        return response

    @staticmethod
    def attendance_to_csv(records):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="attendance.csv"'
        response.write('\ufeff')
        writer = csv.writer(io.TextIOWrapper(response, encoding='utf-8-sig', newline=''))
        writer.writerow(['دانش‌آموز', 'کلاس', 'وضعیت', 'تاریخ'])
        for r in records:
            writer.writerow([
                r.student.get_full_name(),
                r.attendance_check.session.classroom.name,
                r.get_status_display(),
                r.attendance_check.check_time.strftime('%Y/%m/%d'),
            ])
        return response