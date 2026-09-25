# dashboard/ai/service.py

import logging
from typing import List, Optional
from django.conf import settings
from .client import AIClient
from .prompts import PromptBuilder
from .validators import ResponseValidator
from .schemas import AIResponse, TopicValidationResponse, Question
from .exceptions import (
    TopicValidationError,
    InsufficientContentError,
    AIQuestionGenerationError
)

logger = logging.getLogger(__name__)

class AIQuestionService:
    def __init__(self):
        self.client = AIClient()
        self.prompt_builder = PromptBuilder()
        self.validator = ResponseValidator()
        self.enable_topic_validation = settings.AI_QUESTION_GENERATION['ENABLE_TOPIC_VALIDATION']

    def validate_topic(
        self,
        grade: str,
        field: str,
        course: str,
        topic: str
    ) -> TopicValidationResponse:
        """
        Validate if topic is relevant to the course
        
        Returns:
            TopicValidationResponse
            
        Raises:
            TopicValidationError: If topic is not relevant
        """
        logger.info(f"Validating topic '{topic}' for course '{course}'")
        
        # Build prompt
        user_prompt = self.prompt_builder.build_topic_validation_prompt(
            grade=grade,
            field=field,
            course=course,
            topic=topic
        )
        
        system_prompt = "شما یک متخصص اعتبارسنجی موضوعات آموزشی هستید."
        
        # Get AI response
        response_text = self.client.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        # Validate response
        validation_response = self.validator.validate_topic_response(response_text)
        
        # Check relevance
        self.validator.validate_topic_relevance(
            validation_response,
            topic,
            course
        )
        
        logger.info(f"Topic validation passed with confidence {validation_response.confidence}")
        
        return validation_response

    def generate_questions(
        self,
        grade: str,
        field: str,
        course: str,
        class_name: str,
        topic: str,
        question_count: int,
        educational_context: str = "محتوای آموزشی درس",
        validate_topic: bool = True
    ) -> AIResponse:
        """
        Generate questions using AI
        
        Args:
            grade: Grade level
            field: Field of study
            course: Course name
            class_name: Class name
            topic: Topic for questions
            question_count: Number of questions to generate
            educational_context: Educational context (optional)
            validate_topic: Whether to validate topic first
            
        Returns:
            AIResponse with generated questions
            
        Raises:
            TopicValidationError: If topic is not relevant
            InsufficientContentError: If not enough content
            AIQuestionGenerationError: For other errors
        """
        logger.info(f"Generating {question_count} questions for topic '{topic}' in course '{course}'")
        
        # Validate topic if enabled
        if validate_topic and self.enable_topic_validation:
            self.validate_topic(grade, field, course, topic)
        
        # Build prompt
        user_prompt = self.prompt_builder.build_question_generation_prompt(
            grade=grade,
            field=field,
            course=course,
            class_name=class_name,
            topic=topic,
            question_count=question_count,
            educational_context=educational_context
        )
        
        system_prompt = self.prompt_builder.get_system_prompt()
        
        # Get AI response
        response_text = self.client.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        # Validate response
        ai_response = self.validator.validate_question_response(response_text)
        
        # Check if topic is valid
        if not ai_response.is_valid_topic:
            raise TopicValidationError(
                message=ai_response.message,
                topic=topic,
                course=course
            )
        
        # Check if we got enough questions
        generated_count = len(ai_response.questions)
        if generated_count == 0:
            raise InsufficientContentError(
                message=f"هیچ سوالی برای موضوع '{topic}' تولید نشد. {ai_response.message}",
                requested=question_count,
                generated=0
            )
        
        if generated_count < question_count:
            logger.warning(
                f"Requested {question_count} questions but only {generated_count} were generated"
            )
        
        logger.info(f"Successfully generated {generated_count} questions")
        
        return ai_response

    def generate_replacement_question(
        self,
        grade: str,
        field: str,
        course: str,
        class_name: str,
        topic: str,
        rejected_question: Question,
        educational_context: str = "محتوای آموزشی درس"
    ) -> Question:
        """
        Generate a replacement question for a rejected one
        
        Args:
            grade: Grade level
            field: Field of study
            course: Course name
            class_name: Class name
            topic: Topic
            rejected_question: The rejected question
            educational_context: Educational context
            
        Returns:
            Question: New question
        """
        logger.info(f"Generating replacement question for topic '{topic}'")
        
        # Build prompt with rejected question
        user_prompt = self.prompt_builder.build_question_generation_prompt(
            grade=grade,
            field=field,
            course=course,
            class_name=class_name,
            topic=topic,
            question_count=1,
            educational_context=educational_context
        )
        
        user_prompt += f"\n\nسوال قبلی رد شده بود: {rejected_question.question}\nلطفاً سوال جدید و متفاوتی تولید کن."
        
        system_prompt = self.prompt_builder.get_system_prompt()
        
        # Get AI response
        response_text = self.client.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        # Validate response
        ai_response = self.validator.validate_question_response(response_text)
        
        if not ai_response.questions:
            raise AIQuestionGenerationError("Failed to generate replacement question")
        
        return ai_response.questions[0]