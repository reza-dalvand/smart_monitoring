# dashboard/ai/validators.py
import json
import re
import logging
from .schemas import AIResponse, TopicValidationResponse
from .exceptions import AIResponseError, TopicValidationError

logger = logging.getLogger(__name__)

def fix_json_escapes(json_str: str) -> str:
    """
    اصلاح کاراکترهای escape نامعتبر در JSON.
    مدل‌های هوش مصنوعی گاهی در تولید متن سوالات، کاراکترهایی مانند \. یا \پ تولید می‌کنند
    که در استاندارد JSON مجاز نیستند و باعث خطای Invalid \escape می‌شوند.
    این تابع \ اضافی را قبل از کاراکترهای غیرمجاز حذف می‌کند.
    """
    def replace_escape(match):
        escape_char = match.group(1)
        # کاراکترهای escape مجاز در استاندارد JSON
        if escape_char in '"\\/bfnrtu':
            return match.group(0)  # حفظ escape معتبر
        else:
            return escape_char  # حذف \ و نگه داشتن خود کاراکتر
    
    return re.sub(r'\\(.)', replace_escape, json_str, flags=re.DOTALL)


class ResponseValidator:
    @staticmethod
    def _clean_markdown(response_text: str) -> str:
        """حذف مارک‌داون‌های احتمالی اطراف JSON"""
        cleaned = response_text.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        elif cleaned.startswith('```'):
            cleaned = cleaned[3:]
        
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
            
        return cleaned.strip()

    @staticmethod
    def validate_topic_response(response_text: str) -> TopicValidationResponse:
        try:
            cleaned = ResponseValidator._clean_markdown(response_text)
            # 🔧 اصلاح: رفع کاراکترهای escape نامعتبر قبل از پارس JSON
            cleaned = fix_json_escapes(cleaned)
            
            data = json.loads(cleaned)
            return TopicValidationResponse(**data)
        except json.JSONDecodeError as e:
            # لاگ کردن بخشی از متن خام برای دیباگ در صورت نیاز
            logger.error(f"JSON decode error: {e}\nRaw text snippet: {response_text[:500]}")
            raise AIResponseError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Validation error: {e}")
            raise AIResponseError(f"Response validation failed: {e}")

    @staticmethod
    def validate_question_response(response_text: str) -> AIResponse:
        try:
            cleaned = ResponseValidator._clean_markdown(response_text)
            # 🔧 اصلاح: رفع کاراکترهای escape نامعتبر قبل از پارس JSON
            cleaned = fix_json_escapes(cleaned)
            
            data = json.loads(cleaned)
            return AIResponse(**data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}\nRaw text snippet: {response_text[:500]}")
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
        if validation_response.confidence < 0.7:
            logger.warning(
                f"Low confidence ({validation_response.confidence}) for topic '{topic}' in course '{course}'"
            )
        return True