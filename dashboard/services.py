# dashboard/services.py (اصلاح شده)

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



def generate_questions_for_job(job: AIGenerationJob, count: Optional[int] = None):
    """
    Generate questions for an AI job using real AI service
    """
    count = count or job.requested_count
    count = max(1, min(int(count), 20))
    
    job.status = 'processing'
    job.save()
    
    try:
        # Get class info
        classroom = job.classroom
        grade = classroom.get_grade_display()
        field = classroom.get_field_display()
        course = classroom.subject
        class_name = classroom.name
        
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
        job.error_message = ai_response.message
        
    except TopicValidationError as e:
        job.status = 'failed'
        job.error_message = f"موضوع نامعتبر: {e.message}"
        logger.error(f"Topic validation failed: {e}")
        
    except InsufficientContentError as e:
        job.status = 'completed'  # Partial success
        job.error_message = e.message
        logger.warning(f"Insufficient content: {e}")
        
    except AIQuestionGenerationError as e:
        job.status = 'failed'
        job.error_message = f"خطا در تولید سوال: {str(e)}"
        logger.error(f"AI generation error: {e}")
        
    except Exception as e:
        job.status = 'failed'
        job.error_message = f"خطای غیرمنتظره: {str(e)}"
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