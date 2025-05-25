import time
from typing import Optional
from redis import Redis

class ApiIntegrationRateLimiter:
    """
    Distributed rate limiter using Redis. Supports per-API configuration.
    Example usage:
        limiter = ApiIntegrationRateLimiter(redis_client, 'MillionVerifier', max_requests=60, period_seconds=60)
        if limiter.acquire():
            # Make API call
    """
    def __init__(self, redis_client: Redis, api_name: str, max_requests: int, period_seconds: int):
        self.redis = redis_client
        self.api_name = api_name
        self.max_requests = max_requests
        self.period_seconds = period_seconds
        self.key = f"ratelimit:{api_name}"

    def is_allowed(self) -> bool:
        """Check if a request is allowed without incrementing the counter."""
        current = self.redis.get(self.key)
        if current is None:
            return True
        return int(current) < self.max_requests

    def acquire(self, block: bool = False, timeout: Optional[int] = None) -> bool:
        """
        Attempt to acquire a rate limit slot. If block=True, wait until a slot is available or timeout is reached.
        Returns True if slot acquired, False otherwise.
        """
        start = time.time()
        while True:
            pipe = self.redis.pipeline()
            pipe.incr(self.key, 1)
            pipe.expire(self.key, self.period_seconds)
            count, _ = pipe.execute()
            if count <= self.max_requests:
                return True
            if not block:
                return False
            if timeout is not None and (time.time() - start) > timeout:
                return False
            # Wait a bit before retrying
            time.sleep(1)

    def get_remaining(self) -> int:
        """Return the number of requests remaining in the current window."""
        current = self.redis.get(self.key)
        if current is None:
            return self.max_requests
        return max(0, self.max_requests - int(current)) 