# dashboard/ai/schemas.py

from typing import List, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum

class QuestionDifficulty(str, Enum):
    EASY = 'easy'
    MEDIUM = 'medium'
    HARD = 'hard'

class QuestionType(str, Enum):
    CONCEPTUAL = 'conceptual'
    FACTUAL = 'factual'
    COMPUTATIONAL = 'computational'
    COMBINED = 'combined'

class Question(BaseModel):
    question: str = Field(..., description='متن سوال')
    options: List[str] = Field(..., min_items=4, max_items=4, description='چهار گزینه')
    correct_option: int = Field(..., ge=0, le=3, description='ایندکس پاسخ صحیح (0-3)')
    explanation: Optional[str] = Field(None, description='توضیح پاسخ صحیح')
    source: Optional[str] = Field(None, description='منبع محتوا')
    difficulty: QuestionDifficulty = Field(QuestionDifficulty.MEDIUM)
    question_type: QuestionType = Field(QuestionType.CONCEPTUAL)

    @validator('options')
    def validate_options(cls, v):
        if len(v) != 4:
            raise ValueError('هر سوال باید دقیقاً 4 گزینه داشته باشد')
        if len(set(v)) != 4:
            raise ValueError('گزینه‌ها نباید تکراری باشند')
        return v

    @validator('question')
    def validate_question(cls, v):
        if len(v.strip()) < 10:
            raise ValueError('متن سوال بسیار کوتاه است')
        if len(v) > 500:
            raise ValueError('متن سوال بسیار طولانی است')
        return v

class AIResponse(BaseModel):
    is_valid_topic: bool = Field(..., description='آیا موضوع معتبر است')
    message: str = Field(..., description='پیام سیستم')
    questions: List[Question] = Field(default_factory=list, description='لیست سوالات')

class TopicValidationResponse(BaseModel):
    is_valid_topic: bool
    reason: str
    confidence: float = Field(..., ge=0.0, le=1.0)

class ClassInfo(BaseModel):
    grade: str
    field: str
    course: str
    class_name: str
    teacher_name: str