import csv
import io
from django.http import HttpResponse


class DistrictExportService:

    @staticmethod
    def school_comparison_to_csv(data):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="district_schools.csv"'
        response.write('\ufeff')
        writer = csv.writer(io.TextIOWrapper(response, encoding='utf-8-sig', newline=''))
        writer.writerow(['مدرسه', 'نوع', 'دانش‌آموزان', 'معلمان', 'کلاس‌ها',
                          'نرخ حضور', 'مشارکت', 'عملکرد', 'جلسات'])
        for row in data:
            writer.writerow([
                row['name'], row['school_type'],
                row['students'], row['teachers'], row['classrooms'],
                f"{row.get('attendance_rate') or '-'}٪",
                f"{row.get('participation_rate') or '-'}٪",
                f"{row.get('performance_rate') or '-'}٪",
                row['sessions'],
            ])
        return response

    @staticmethod
    def class_analytics_to_csv(data):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="district_classes.csv"'
        response.write('\ufeff')
        writer = csv.writer(io.TextIOWrapper(response, encoding='utf-8-sig', newline=''))
        writer.writerow(['کلاس', 'درس', 'پایه', 'رشته', 'معلم',
                          'دانش‌آموزان', 'جلسات', 'حضور', 'مشارکت', 'عملکرد'])
        for row in data:
            writer.writerow([
                row['name'], row['subject'], row['grade'], row['field'],
                row['teacher_name'], row['students_count'], row['sessions_count'],
                f"{row.get('attendance_rate') or '-'}٪",
                f"{row.get('participation_rate') or '-'}٪",
                f"{row.get('performance_rate') or '-'}٪",
            ])
        return response