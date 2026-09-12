import json
import os
import random

from .models import Question


def _make_mock_question_payload(job, index):
    """
    یک سوال چهار گزینه‌ای نمونه می‌سازد.

    فعلاً سرویس هوش مصنوعی واقعی نیست.
    بعداً همین تابع می‌تواند خروجی LLM محلی مثل Gemma را برگرداند.
    """

    topic = job.topic.strip() if job.topic else 'مبحث مشخص‌شده'

    pdf_name = 'فایل PDF'
    if job.pdf_file:
        pdf_name = os.path.basename(job.pdf_file.name)

    correct_answer = random.choice(['a', 'b', 'c', 'd'])

    return {
        'text': (
            f"سوال نمونه {index} از مبحث «{topic}» بر اساس فایل «{pdf_name}» "
            f"و قالب محدودشده درسی تولید شد. این سوال فعلاً توسط سرویس ماک ساخته شده است."
        ),
        'choice_a': f"گزینه الف برای سوال {index} از مبحث {topic}",
        'choice_b': f"گزینه ب برای سوال {index} از مبحث {topic}",
        'choice_c': f"گزینه ج برای سوال {index} از مبحث {topic}",
        'choice_d': f"گزینه د برای سوال {index} از مبحث {topic}",
        'correct_answer': correct_answer,
        'timer_seconds': job.default_timer_seconds,
    }


def generate_questions_for_job(job, count=None):
    """
    برای یک AIGenerationJob تعدادی سوال پیش‌نویس تولید می‌کند.

    این تابع فعلاً با ماک کار می‌کند.
    بعداً فقط داخل همین تابع، سرویس واقعی AI صدا زده می‌شود.
    """

    count = count or job.requested_count
    count = max(1, min(int(count), 20))

    job.status = 'processing'
    job.save()

    try:
        existing_count = job.generated_questions.count()

        # seed برای اینکه خروجی کمی نسبت به تعداد سوال‌های قبلی تغییر کند
        random.seed(f"ai-job-{job.id}-count-{count}-existing-{existing_count}")

        payload = []
        for i in range(1, count + 1):
            payload.append(_make_mock_question_payload(job, i))

        for item in payload:
            Question.objects.create(
                classroom=job.classroom,
                session=None,
                created_by=job.teacher,
                ai_job=job,
                source='ai',
                is_approved=False,
                review_status='pending',
                topic=job.topic,
                text=item['text'],
                choice_a=item['choice_a'],
                choice_b=item['choice_b'],
                choice_c=item['choice_c'],
                choice_d=item['choice_d'],
                correct_answer=item['correct_answer'],
                timer_seconds=item.get('timer_seconds', job.default_timer_seconds),
            )

        job.raw_response = json.dumps(payload, ensure_ascii=False, indent=2)
        job.status = 'completed'
        job.error_message = ''

    except Exception as exc:
        job.status = 'failed'
        job.error_message = str(exc)

    job.save()

    return job.generated_questions.count()


def regenerate_rejected_questions(job):
    """
    سوال‌های ردشده‌ی یک درخواست هوش مصنوعی را حذف می‌کند
    و به تعداد آن‌ها سوال جدید پیش‌نویس می‌سازد.
    """

    rejected_questions = job.generated_questions.filter(review_status='rejected')
    rejected_count = rejected_questions.count()

    if rejected_count == 0:
        return 0

    rejected_questions.delete()
    generate_questions_for_job(job, count=rejected_count)

    return rejected_count