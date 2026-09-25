# dashboard/ai/schemas.py
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class Question(BaseModel):
    question: str = Field(..., description='متن سوال')
    # در Pydantic v2 به جای min_items از min_length استفاده می‌شود
    options: List[str] = Field(..., min_length=4, max_length=4, description='چهار گزینه')
    correct_option: int = Field(..., ge=0, le=3, description='ایندکس پاسخ صحیح (0-3)')
    explanation: Optional[str] = Field(None, description='توضیح پاسخ صحیح')
    source: Optional[str] = Field(None, description='منبع محتوا')
    
    # 🔧 اصلاح: تبدیل Enum به String ساده برای جلوگیری از خطای LLM
    difficulty: str = Field(default="medium", description="سطح سختی")
    question_type: str = Field(default="conceptual", description="نوع سوال")

    @field_validator('options')
    @classmethod
    def validate_options(cls, v):
        if len(v) != 4:
            raise ValueError('هر سوال باید دقیقاً 4 گزینه داشته باشد')
        if len(set(v)) != 4:
            raise ValueError('گزینه‌ها نباید تکراری باشند')
        return v

    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        if len(v.strip()) < 10:
            raise ValueError('متن سوال بسیار کوتاه است')
        if len(v) > 1500:  # محدودیت را کمی افزایش دادیم تا سوالات تشریحی‌تر ارور ندهند
            raise ValueError('متن سوال بسیار طولانی است')
        return v

    @field_validator('difficulty', 'question_type', mode='before')
    @classmethod
    def normalize_and_fallback(cls, v):
        """
        اگر هوش مصنوعی مقدار عجیبی (مثل problem_solving) برگرداند، 
        به جای خطا دادن، آن را به یک رشته ساده و تمیز تبدیل می‌کنیم.
        """
        if isinstance(v, str):
            return v.strip().lower().replace(' ', '_').replace('-', '_')
        return "conceptual" # Fallback

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