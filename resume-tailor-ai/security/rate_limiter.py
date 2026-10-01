"""
In-Memory Rate Limiter (Token Bucket).
Protects expensive LLM endpoints against abusive traffic and accidental loops.
"""
import time
from typing import Dict, Tuple
from collections import defaultdict
from core.config import settings
from core.logger import logger

class TokenBucketRateLimiter:
    """Thread-safe Token Bucket Rate Limiter."""

    def __init__(self, requests_per_minute: int = settings.RATE_LIMIT_REQUESTS_PER_MINUTE, burst: int = settings.RATE_LIMIT_BURST):
        self.rate = requests_per_minute / 60.0  # tokens added per second
        self.capacity = burst
        self.tokens: Dict[str, float] = defaultdict(lambda: float(self.capacity))
        self.last_update: Dict[str, float] = defaultdict(time.time)

    def is_allowed(self, client_id: str = "default_client") -> Tuple[bool, int]:
        """
        Checks if a request from client_id is allowed.
        Returns: (allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        # Add newly accrued tokens
        elapsed = now - self.last_update[client_id]
        self.last_update[client_id] = now
        self.tokens[client_id] = min(float(self.capacity), self.tokens[client_id] + (elapsed * self.rate))

        if self.tokens[client_id] >= 1.0:
            self.tokens[client_id] -= 1.0
            return True, 0

        # Calculate wait time for at least 1 token
        needed = 1.0 - self.tokens[client_id]
        retry_after = max(1, int(needed / self.rate)) if self.rate > 0 else 60
        logger.warning(f"Rate limit exceeded for client '{client_id}'. Retry in {retry_after}s.")
        return False, retry_after

rate_limiter = TokenBucketRateLimiter()
