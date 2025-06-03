import time
from typing import Optional
from redis import Redis

def get_api_rate_limits():
    """
    Get API rate limits from application configuration.
    
    This function dynamically loads rate limits from the application settings,
    allowing for environment-based configuration and runtime flexibility.
    
    Returns:
        dict: API rate limits configuration
    """
    from app.core.config import settings
    
    return {
        'MillionVerifier': {
            'max_requests': settings.MILLIONVERIFIER_RATE_LIMIT_REQUESTS,
            'period_seconds': settings.MILLIONVERIFIER_RATE_LIMIT_PERIOD
        },
        'OpenAI': {
            'max_requests': settings.OPENAI_RATE_LIMIT_REQUESTS,
            'period_seconds': settings.OPENAI_RATE_LIMIT_PERIOD
        },
        'Perplexity': {
            'max_requests': settings.PERPLEXITY_RATE_LIMIT_REQUESTS,
            'period_seconds': settings.PERPLEXITY_RATE_LIMIT_PERIOD
        },
        'Instantly': {
            'max_requests': settings.INSTANTLY_RATE_LIMIT_REQUESTS,
            'period_seconds': settings.INSTANTLY_RATE_LIMIT_PERIOD
        },
        'Apollo': {
            'max_requests': settings.APOLLO_RATE_LIMIT_REQUESTS,
            'period_seconds': settings.APOLLO_RATE_LIMIT_PERIOD
        },
    }

# Maintain backward compatibility - this will now be dynamically loaded
API_RATE_LIMITS = get_api_rate_limits()

class ApiIntegrationRateLimiter:
    """
    Distributed rate limiter using Redis. Supports per-API configuration.
    
    This rate limiter uses Redis for distributed rate limiting across multiple
    processes and servers. Rate limits are configurable per API service through
    environment variables managed by the application settings.
    
    Example usage:
        from app.core.config import get_redis_connection
        redis_client = get_redis_connection()
        limiter = ApiIntegrationRateLimiter(redis_client, 'MillionVerifier', max_requests=60, period_seconds=60)
        if limiter.acquire():
            # Make API call
            pass
        else:
            # Handle rate limit exceeded
            pass
    """
    def __init__(self, redis_client: Redis, api_name: str, max_requests: int, period_seconds: int):
        self.redis = redis_client
        self.api_name = api_name
        self.max_requests = max_requests
        self.period_seconds = period_seconds
        self.key = f"ratelimit:{api_name}"

    def is_allowed(self) -> bool:
        """
        Check if a request is allowed without incrementing the counter.
        
        Returns:
            bool: True if request is allowed, False if rate limit would be exceeded
        """
        try:
            current = self.redis.get(self.key)
            if current is None:
                return True
            return int(current) < self.max_requests
        except Exception:
            # If Redis is unavailable, allow the request (graceful degradation)
            return True

    def acquire(self, block: bool = False, timeout: Optional[int] = None) -> bool:
        """
        Attempt to acquire a rate limit slot.
        
        Args:
            block (bool): If True, wait until a slot is available or timeout is reached
            timeout (Optional[int]): Maximum time to wait in seconds (only used if block=True)
            
        Returns:
            bool: True if slot acquired, False otherwise
        """
        start = time.time()
        while True:
            try:
                pipe = self.redis.pipeline()
                pipe.incr(self.key, 1)
                pipe.expire(self.key, self.period_seconds)
                count, _ = pipe.execute()
                if count <= self.max_requests:
                    return True
            except Exception:
                # If Redis is unavailable, allow the request (graceful degradation)
                return True
                
            if not block:
                return False
            if timeout is not None and (time.time() - start) > timeout:
                return False
            # Wait a bit before retrying
            time.sleep(1)

    def get_remaining(self) -> int:
        """
        Return the number of requests remaining in the current window.
        
        Returns:
            int: Number of requests remaining (0 if limit exceeded)
        """
        try:
            current = self.redis.get(self.key)
            if current is None:
                return self.max_requests
            return max(0, self.max_requests - int(current))
        except Exception:
            # If Redis is unavailable, return max_requests (graceful degradation)
            return self.max_requests 