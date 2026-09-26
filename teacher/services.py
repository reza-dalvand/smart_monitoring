"""
سرویس‌های ماژول معلم.
الگوی مشابه: district/services.py, school/services.py
"""
import logging
from datetime import timedelta
from typing import Dict, List, Any, Optional

from django.db.models import (
    Count, Q, Avg, F, Sum, Case, When,
    FloatField, Value,
)
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from accounts.models import User
from dashboard.models import (
    Classroom, ClassSession, AttendanceRecord,
    AttendanceRequest, AttendanceResponse,
    Question, StudentAnswer,
)
from .scope import TeacherScope
from .constants import (
    SessionStatus, ParticipationLevel,
    AssessmentStatus, HomeworkStatus, SubmissionStatus,
    RiskLevel, RISK_THRESHOLDS, PARTICIPATION_WEIGHTS,
)

logger = logging.getLogger(__name__)


class TeacherAnalyticsService:
    """محاسبه آمار و تحلیل‌های آموزشی معلم"""

    def __init__(self, scope: TeacherScope):
        self.scope = scope
        self.teacher = scope.user

    def _safe_rate(self, numerator, denominator, digits=1):
        if not denominator:
            return None
        return round((numerator / denominator) * 100, digits)

    # ──────────────────────────────────────────────
    #  Overview KPIs
    # ──────────────────────────────────────────────
    def get_overview(self) -> Dict[str, Any]:
        result = {
            'total_classes': 0,
            'total_students': 0,
            'total_sessions': 0,
            'active_session': None,
            'attendance_rate': None,
            'participation_rate': None,
            'assessment_average': None,
            'homework_completion_rate': None,
        }

        classes = self.scope.filter_classes()
        result['total_classes'] = classes.count()

        students = self.scope.filter_students()
        result['total_students'] = students.count()

        sessions = self.scope.filter_sessions()
        result['total_sessions'] = sessions.count()

        # Attendance
        att = self._get_attendance_stats()
        result['attendance_rate'] = att.get('present_rate')

        return result

    def _get_attendance_stats(self) -> Dict:
        records = self.scope.filter_attendance_responses()
        total = records.count()
        if total == 0:
            return {'present_rate': None, 'total': 0}
        present = records.filter(final_status='present').count()
        return {
            'present_rate': self._safe_rate(present, total),
            'total': total,
            'present': present,
        }

    def get_class_analytics(self, classroom_id: int) -> Dict:
        classroom = self.scope.get_class_or_404(classroom_id)

        # Attendance
        att_records = AttendanceRecord.objects.filter(
            attendance_check__session__classroom=classroom,
        )
        total_att = att_records.count()
        present = att_records.filter(status='present').count()
        attendance_rate = self._safe_rate(present, total_att)

        # Participation
        from .models import ParticipationRecord
        part_records = ParticipationRecord.objects.filter(
            session__classroom=classroom,
        )
        total_part = part_records.count()
        high_part = part_records.filter(level='high').count()
        participation_rate = self._safe_rate(high_part, total_part)

        # Questions
        answers = StudentAnswer.objects.filter(
            question__classroom=classroom,
        )
        total_answers = answers.count()
        correct = answers.filter(is_correct=True).count()
        avg_score = self._safe_rate(correct, total_answers)

        return {
            'classroom': classroom,
            'attendance_rate': attendance_rate,
            'participation_rate': participation_rate,
            'assessment_average': avg_score,
            'total_sessions': classroom.sessions.count(),
            'total_students': classroom.students.count(),
        }

    def get_topic_analytics(self, classroom_id: int) -> List[Dict]:
        """عملکرد بر اساس موضوع"""
        classroom = self.scope.get_class_or_404(classroom_id)

        answers = StudentAnswer.objects.filter(
            question__classroom=classroom,
        ).values(
            topic=F('question__topic')
        ).annotate(
            total=Count('id'),
            correct=Count('id', filter=Q(is_correct=True)),
        ).order_by('-total')[:20]

        result = []
        for item in answers:
            rate = self._safe_rate(item['correct'], item['total'])
            result.append({
                'topic': item['topic'] or 'بدون موضوع',
                'total': item['total'],
                'correct': item['correct'],
                'rate': rate,
                'needs_review': rate is not None and rate < 60,
            })
        return result


class TeacherParticipationService:
    """مدیریت مشارکت دانش‌آموزان"""

    def __init__(self, scope: TeacherScope):
        self.scope = scope

    def record_participation(
        self, session, student, level, note='', source='manual'
    ):
        from .models import ParticipationRecord
        from .constants import ParticipationLevel

        record, created = ParticipationRecord.objects.update_or_create(
            session=session,
            student=student,
            source=source,
            defaults={
                'level': level,
                'teacher': self.scope.user,
                'note': note,
                'score': ParticipationLevel.SCORE_MAP.get(level, 0),
            },
        )
        return record

    def batch_record_participation(
        self, session, participations: Dict[int, str]
    ):
        """ثبت دسته‌ای مشارکت {student_id: level}"""
        results = []
        for student_id, level in participations.items():
            try:
                student = self.scope.get_student_or_404(student_id)
                record = self.record_participation(
                    session, student, level
                )
                results.append(record)
            except Exception as e:
                logger.error(
                    f'Participation record failed: {e}'
                )
        return results

    def get_session_participation(self, session):
        from .models import ParticipationRecord
        return ParticipationRecord.objects.filter(
            session=session,
        ).select_related('student')

    def get_student_participation_trend(self, student, limit=10):
        from .models import ParticipationRecord
        return ParticipationRecord.objects.filter(
            student=student,
            session__classroom__teacher=self.scope.user,
        ).order_by('-created_at')[:limit]


class TeacherSessionService:
    """مدیریت جلسات آموزشی"""

    def __init__(self, scope: TeacherScope):
        self.scope = scope

    def create_session(self, classroom, topic='', **kwargs):
        session = ClassSession.objects.create(
            classroom=classroom,
            topic=topic,
        )
        # ایجاد فیلدهای تکمیلی
        from .models import SessionExtension
        SessionExtension.objects.create(
            session=session,
            teacher=self.scope.user,
            subject=classroom.subject,
            status=SessionStatus.SCHEDULED,
            **kwargs,
        )
        return session

    def start_session(self, session):
        from django.db import transaction
        from .models import SessionExtension

        with transaction.atomic():
            ext = SessionExtension.objects.filter(
                session=session,
                teacher=self.scope.user,
            ).select_for_update().first()

            if not ext:
                raise ValueError('جلسه یافت نشد.')

            if ext.status == SessionStatus.ACTIVE:
                raise ValueError('جلسه قبلاً فعال شده است.')

            ext.status = SessionStatus.ACTIVE
            ext.started_at = timezone.now()
            ext.save()

        return session

    def end_session(self, session):
        from django.db import transaction
        from .models import SessionExtension

        with transaction.atomic():
            ext = SessionExtension.objects.filter(
                session=session,
                teacher=self.scope.user,
            ).select_for_update().first()

            if not ext:
                raise ValueError('جلسه یافت نشد.')

            if ext.status != SessionStatus.ACTIVE:
                raise ValueError('جلسه فعال نیست.')

            ext.status = SessionStatus.COMPLETED
            ext.ended_at = timezone.now()
            ext.save()

        return session

    def get_active_session(self):
        from .models import SessionExtension
        return SessionExtension.objects.filter(
            teacher=self.scope.user,
            status=SessionStatus.ACTIVE,
        ).select_related('session', 'session__classroom').first()


class StudentRiskService:
    """
    شناسایی دانش‌آموزان نیازمند توجه.
    Rule-based و Explainable.
    """

    def __init__(self, scope: TeacherScope):
        self.scope = scope
        self.analytics = TeacherAnalyticsService(scope)
        self.thresholds = RISK_THRESHOLDS

    def get_students_needing_attention(
        self, classroom_id=None
    ) -> List[Dict]:
        students = self.scope.filter_students()
        if classroom_id:
            classroom = self.scope.get_class_or_404(classroom_id)
            students = students.filter(enrolled_classes=classroom)

        results = []
        for student in students[:200]:
            indicators = self._check_student(student)
            if indicators:
                risk_level = (
                    RiskLevel.NEEDS_ATTENTION
                    if len(indicators) >= 2
                    else RiskLevel.WATCH
                )
                results.append({
                    'student': student,
                    'risk_level': risk_level,
                    'indicators': indicators,
                    'indicator_count': len(indicators),
                })

        # مرتب‌سازی بر اساس تعداد شاخص‌ها
        results.sort(
            key=lambda x: x['indicator_count'], reverse=True
        )
        return results

    def _check_student(self, student) -> List[Dict]:
        indicators = []

        # 1. بررسی حضور
        att_records = self.scope.filter_attendance_responses().filter(
            student=student,
        )
        total_att = att_records.count()
        if total_att > 0:
            present = att_records.filter(
                final_status='present'
            ).count()
            att_rate = (present / total_att) * 100
            if att_rate < self.thresholds['attendance_min']:
                indicators.append({
                    'type': 'low_attendance',
                    'message': (
                        f'حضور {att_rate:.0f}٪ '
                        f'(کمتر از '
                        f'{self.thresholds["attendance_min"]:.0f}٪)'
                    ),
                    'value': att_rate,
                })

        # 2. بررسی مشارکت
        from .models import ParticipationRecord
        part_records = ParticipationRecord.objects.filter(
            student=student,
            session__classroom__teacher=self.scope.user,
        )
        total_part = part_records.count()
        if total_part > 0:
            avg_score = part_records.aggregate(
                avg=Avg('score')
            )['avg'] or 0
            if avg_score < self.thresholds['participation_min']:
                indicators.append({
                    'type': 'low_participation',
                    'message': (
                        f'مشارکت {avg_score:.0f} '
                        f'(کمتر از '
                        f'{self.thresholds["participation_min"]:.0f})'
                    ),
                    'value': avg_score,
                })

        # 3. بررسی عملکرد در سوالات
        answers = self.scope.filter_student_answers().filter(
            student=student,
        )
        total_answers = answers.count()
        if total_answers > 3:
            correct = answers.filter(is_correct=True).count()
            score_rate = (correct / total_answers) * 100
            # تبدیل به مقیاس ۲۰
            score_20 = score_rate / 5
            if score_20 < self.thresholds['assessment_min']:
                indicators.append({
                    'type': 'low_assessment',
                    'message': (
                        f'نمره تقریبی {score_20:.1f} از ۲۰ '
                        f'(کمتر از '
                        f'{self.thresholds["assessment_min"]:.0f})'
                    ),
                    'value': score_20,
                })

        # 4. بررسی تکالیف
        from .models import HomeworkSubmission
        submissions = HomeworkSubmission.objects.filter(
            student=student,
            homework__teacher=self.scope.user,
        )
        total_hw = submissions.count()
        if total_hw > 0:
            submitted = submissions.exclude(
                status=SubmissionStatus.NOT_SUBMITTED
            ).count()
            hw_rate = (submitted / total_hw) * 100
            if hw_rate < self.thresholds['homework_min']:
                indicators.append({
                    'type': 'low_homework',
                    'message': (
                        f'انجام تکلیف {hw_rate:.0f}٪ '
                        f'(کمتر از '
                        f'{self.thresholds["homework_min"]:.0f}٪)'
                    ),
                    'value': hw_rate,
                })

        return indicators