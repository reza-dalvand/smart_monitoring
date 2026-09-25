# dashboard/ai/validators.py

import json
import logging
from typing import Dict, Any
from .schemas import AIResponse, TopicValidationResponse
from .exceptions import AIResponseError, TopicValidationError

logger = logging.getLogger(__name__)

class ResponseValidator:
    @staticmethod
    def validate_topic_response(response_text: str) -> TopicValidationResponse:
        try:
            # Clean markdown code blocks if present
            cleaned = response_text.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            
            data = json.loads(cleaned.strip())
            return TopicValidationResponse(**data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise AIResponseError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Validation error: {e}")
            raise AIResponseError(f"Response validation failed: {e}")

    @staticmethod
    def validate_question_response(response_text: str) -> AIResponse:
        try:
            # Clean markdown code blocks if present
            cleaned = response_text.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            
            data = json.loads(cleaned.strip())
            return AIResponse(**data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise AIResponseError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Validation error: {e}")
            raise AIResponseError(f"Response validation failed: {e}")

    @staticmethod
    def validate_topic_relevance(
        validation_response: TopicValidationResponse,
        topic: str,
        course: str
    ) -> bool:
        if not validation_response.is_valid_topic:
            raise TopicValidationError(
                message=f"موضوع '{topic}' با درس '{course}' مرتبط نیست. {validation_response.reason}",
                topic=topic,
                course=course
            )
        
        # Check confidence threshold
        if validation_response.confidence < 0.7:
            logger.warning(
                f"Low confidence ({validation_response.confidence}) for topic '{topic}' in course '{course}'"
            )
        
        return True