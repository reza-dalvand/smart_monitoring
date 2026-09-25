import csv
import io
from django.http import HttpResponse


class ProvinceExportService:

    @staticmethod
    def district_comparison_to_csv(data):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="province_districts.csv"'
        response.write('\ufeff')
        writer = csv.writer(io.TextIOWrapper(response, encoding='utf-8-sig', newline=''))
        writer.writerow(['منطقه', 'مدارس', 'دانش‌آموزان', 'نرخ حضور', 'مشارکت', 'عملکرد'])
        for row in data:
            writer.writerow([
                row['name'], row['schools'], row['students'],
                f"{row.get('attendance_rate') or '-'}٪",
                f"{row.get('participation_rate') or '-'}٪",
                f"{row.get('performance_rate') or '-'}٪",
            ])
        return response

    @staticmethod
    def schools_to_csv(data):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="province_schools.csv"'
        response.write('\ufeff')
        writer = csv.writer(io.TextIOWrapper(response, encoding='utf-8-sig', newline=''))
        writer.writerow(['مدرسه', 'منطقه', 'استان', 'نوع', 'کلاس‌ها', 'نرخ حضور'])
        for row in data:
            writer.writerow([
                row['name'], row['district'], row['province'],
                row['school_type'], row['classrooms_count'],
                f"{row.get('attendance_rate') or '-'}٪",
            ])
        return response