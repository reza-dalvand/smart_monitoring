# dashboard/ai/exceptions.py

class AIQuestionGenerationError(Exception):
    """Base exception for AI question generation"""
    pass

class TopicValidationError(AIQuestionGenerationError):
    """Raised when topic is not relevant to the course"""
    def __init__(self, message: str, topic: str, course: str):
        self.topic = topic
        self.course = course
        super().__init__(message)

class InsufficientContentError(AIQuestionGenerationError):
    """Raised when there's not enough content to generate requested questions"""
    def __init__(self, message: str, requested: int, generated: int):
        self.requested = requested
        self.generated = generated
        super().__init__(message)

class AIResponseError(AIQuestionGenerationError):
    """Raised when AI returns invalid response"""
    pass

class AIServiceUnavailableError(AIQuestionGenerationError):
    """Raised when AI service is unavailable"""
    pass

class RateLimitExceededError(AIQuestionGenerationError):
    """Raised when rate limit is exceeded"""
    pass