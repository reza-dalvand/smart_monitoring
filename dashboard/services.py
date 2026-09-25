from typing import Optional

from .ai.service import AIQuestionService
from .ai.exceptions import (
    TopicValidationError,
    InsufficientContentError,
    AIQuestionGenerationError
)
from .models import Question, AIGenerationJob
import logging


logger = logging.getLogger(__name__)


def _get_error_message(exception: Exception) -> str:
    """
    استخراج پیام خطا از exception به صورت امن
    - اگر exception دارای attribute 'message' باشد، آن را برمی‌گرداند
    - در غیر این صورت str(exception) را برمی‌گرداند
    - اگر نتیجه خالی باشد، نام کلاس exception را برمی‌گرداند
    """
    msg = getattr(exception, 'message', None)
    if msg:
        return str(msg)
    msg = str(exception)
    if msg:
        return msg
    return exception.__class__.__name__


def generate_questions_for_job(job: AIGenerationJob, count: Optional[int] = None):
    count = count or job.requested_count
    count = max(1, min(int(count), 20))
    job.status = 'processing'
    job.save()
    
    try:
        classroom = job.classroom
        grade = classroom.get_grade_display()
        field = classroom.get_field_display()
        course = classroom.subject
        class_name = classroom.name
        
        # ✅ استفاده از پرامپت معلم به عنوان محتوای آموزشی
        educational_context = job.prompt if job.prompt and job.prompt.strip() else f"سرفصل رسمی درس {course} پایه {grade} رشته {field}"
        
        ai_service = AIQuestionService()
        
        ai_response = ai_service.generate_questions(
            grade=grade,
            field=field,
            course=course,
            class_name=class_name,
            topic=job.topic,
            question_count=count,
            educational_context=educational_context
        )
                
        # Initialize AI service
        ai_service = AIQuestionService()
        
        # Generate questions
        ai_response = ai_service.generate_questions(
            grade=grade,
            field=field,
            course=course,
            class_name=class_name,
            topic=job.topic,
            question_count=count,
            educational_context="محتوای آموزشی درس"
        )
        
        # Save questions
        existing_count = job.generated_questions.count()
        
        for idx, question_data in enumerate(ai_response.questions, start=existing_count + 1):
            Question.objects.create(
                classroom=classroom,
                session=None,
                created_by=job.teacher,
                ai_job=job,
                source='ai',
                is_approved=False,
                review_status='pending',
                topic=job.topic,
                text=question_data.question,
                choice_a=question_data.options[0],
                choice_b=question_data.options[1],
                choice_c=question_data.options[2],
                choice_d=question_data.options[3],
                correct_answer=['a', 'b', 'c', 'd'][question_data.correct_option],
                timer_seconds=job.default_timer_seconds,
            )
        
        job.raw_response = ai_response.model_dump_json(indent=2)
        job.status = 'completed'
        job.error_message = getattr(ai_response, 'message', '')
        
    except TopicValidationError as e:
        job.status = 'failed'
        # 🔧 اصلاح: استفاده از تابع کمکی برای استخراج امن پیام خطا
        error_msg = _get_error_message(e)
        job.error_message = f"موضوع نامعتبر: {error_msg}"
        logger.error(f"Topic validation failed: {e}")
        
    except InsufficientContentError as e:
        job.status = 'completed'  # Partial success
        # 🔧 اصلاح: استفاده از تابع کمکی
        error_msg = _get_error_message(e)
        job.error_message = error_msg
        logger.warning(f"Insufficient content: {e}")
        
    except AIQuestionGenerationError as e:
        job.status = 'failed'
        job.error_message = f"خطا در تولید سوال: {_get_error_message(e)}"
        logger.error(f"AI generation error: {e}")
        
    except Exception as e:
        job.status = 'failed'
        job.error_message = f"خطای غیرمنتظره: {_get_error_message(e)}"
        logger.exception(f"Unexpected error: {e}")
    
    job.save()
    return job.generated_questions.count()


def regenerate_rejected_question(job: AIGenerationJob, rejected_question: Question):
    """
    Generate a replacement for a rejected question
    """
    try:
        # Get class info
        classroom = job.classroom
        grade = classroom.get_grade_display()
        field = classroom.get_field_display()
        course = classroom.subject
        class_name = classroom.name
        
        # Initialize AI service
        ai_service = AIQuestionService()
        
        # Create Question object from rejected question
        from .ai.schemas import Question as AIQuestion
        rejected_ai_question = AIQuestion(
            question=rejected_question.text,
            options=[
                rejected_question.choice_a,
                rejected_question.choice_b,
                rejected_question.choice_c,
                rejected_question.choice_d
            ],
            correct_option=['a', 'b', 'c', 'd'].index(rejected_question.correct_answer)
        )
        
        # Generate replacement
        new_question = ai_service.generate_replacement_question(
            grade=grade,
            field=field,
            course=course,
            class_name=class_name,
            topic=job.topic,
            rejected_question=rejected_ai_question
        )
        
        # Delete old question
        rejected_question.delete()
        
        # Create new question
        Question.objects.create(
            classroom=classroom,
            session=None,
            created_by=job.teacher,
            ai_job=job,
            source='ai',
            is_approved=False,
            review_status='pending',
            topic=job.topic,
            text=new_question.question,
            choice_a=new_question.options[0],
            choice_b=new_question.options[1],
            choice_c=new_question.options[2],
            choice_d=new_question.options[3],
            correct_answer=['a', 'b', 'c', 'd'][new_question.correct_option],
            timer_seconds=job.default_timer_seconds,
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate replacement question: {e}")
        return False