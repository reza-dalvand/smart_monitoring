"""سرویس ارزیابی‌های دانش‌آموز"""
from typing import Dict
from django.db.models import Sum

from ..scope import StudentScope


class StudentAssessmentService:
    """سرویس ارزیابی‌های دانش‌آموز"""

    def __init__(self, scope: StudentScope):
        self.scope = scope

    def get_assessment_result(self, assessment, student) -> Dict:
        """محاسبه نتیجه آزمون برای دانش‌آموز"""
        from teacher.models import StudentAssessmentResponse, AssessmentQuestion

        responses = StudentAssessmentResponse.objects.filter(
            assessment=assessment,
            student=student,
        )
        total_questions = AssessmentQuestion.objects.filter(
            assessment=assessment
        ).count()
        answered = responses.count()
        correct = responses.filter(is_correct=True).count()
        total_score = responses.aggregate(total=Sum('score'))['total'] or 0

        return {
            'total_questions': total_questions,
            'answered': answered,
            'correct': correct,
            'wrong': answered - correct,
            'total_score': total_score,
            'max_score': assessment.total_score,
            'percentage': round((correct / answered) * 100, 1) if answered > 0 else 0,
        }