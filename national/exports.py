"""سرویس خروجی‌گیری (CSV / Excel)"""
import csv
import io
from typing import List, Dict
from django.http import HttpResponse


class ExportService:

    @staticmethod
    def to_csv(rows: List[Dict], headers: List[str],
               filename: str = 'report') -> HttpResponse:
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        response.write('\ufeff')  # BOM for Excel
        writer = csv.DictWriter(
            io.TextIOWrapper(response, encoding='utf-8-sig', newline=''),
            fieldnames=headers, extrasaction='ignore'
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return response

    @staticmethod
    def province_comparison_to_csv(data: List[Dict]) -> HttpResponse:
        headers = ['name', 'students', 'schools', 'classrooms',
                   'attendance_rate', 'participation_rate', 'performance_rate']
        return ExportService.to_csv(data, headers, 'province_comparison')

    @staticmethod
    def schools_to_csv(data: List[Dict]) -> HttpResponse:
        headers = ['name', 'district', 'province', 'school_type',
                   'classrooms_count', 'attendance_rate']
        return ExportService.to_csv(data, headers, 'schools_report')