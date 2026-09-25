# dashboard/ai/client.py

import logging
import time
from typing import Optional
from openai import OpenAI
from django.conf import settings
from .exceptions import AIServiceUnavailableError, RateLimitExceededError

logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self):
        config = settings.AI_QUESTION_GENERATION
        self.client = OpenAI(
            api_key=config['API_KEY'],
            base_url=config['BASE_URL']
        )
        self.model = config['MODEL']
        self.max_tokens = config['MAX_TOKENS']
        self.temperature = config['TEMPERATURE']
        self.top_p = config['TOP_P']
        self.timeout = config['TIMEOUT']
        self.max_retries = config['MAX_RETRIES']
        self.retry_delay = config['RETRY_DELAY']
        
        # Rate limiting
        self.request_timestamps = []
        self.rate_limit_config = settings.AI_RATE_LIMIT

    def _check_rate_limit(self):
        """Check if rate limit is exceeded"""
        now = time.time()
        
        # Clean old timestamps (older than 1 hour)
        self.request_timestamps = [
            ts for ts in self.request_timestamps 
            if now - ts < 3600
        ]
        
        # Check per minute limit
        recent_requests = [
            ts for ts in self.request_timestamps 
            if now - ts < 60
        ]
        
        if len(recent_requests) >= self.rate_limit_config['REQUESTS_PER_MINUTE']:
            raise RateLimitExceededError(
                f"Rate limit exceeded: {self.rate_limit_config['REQUESTS_PER_MINUTE']} requests per minute"
            )
        
        # Check per hour limit
        if len(self.request_timestamps) >= self.rate_limit_config['REQUESTS_PER_HOUR']:
            raise RateLimitExceededError(
                f"Rate limit exceeded: {self.rate_limit_config['REQUESTS_PER_HOUR']} requests per hour"
            )

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: Optional[int] = None
    ) -> str:
        """
        Generate AI response with retry mechanism
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_retries: Maximum number of retries (default from config)
        
        Returns:
            str: AI response text
        
        Raises:
            AIServiceUnavailableError: If service is unavailable after retries
        """
        self._check_rate_limit()
        
        retries = max_retries or self.max_retries
        last_error = None
        
        for attempt in range(retries):
            try:
                logger.info(f"AI request attempt {attempt + 1}/{retries}")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    timeout=self.timeout
                )
                
                # Record successful request
                self.request_timestamps.append(time.time())
                
                content = response.choices[0].message.content
                logger.info(f"AI response received, length: {len(content)}")
                
                return content
                
            except Exception as e:
                last_error = e
                logger.error(f"AI request failed (attempt {attempt + 1}): {e}")
                
                if attempt < retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
        
        # All retries failed
        logger.error(f"All {retries} attempts failed")
        raise AIServiceUnavailableError(
            f"AI service unavailable after {retries} attempts: {last_error}"
        )