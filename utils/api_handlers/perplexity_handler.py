import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any

class PerplexityRateLimitHandler:
    def __init__(self):
        """Initialize rate limit handler with default limits."""
        self.minute_limit = 60  # requests per minute
        self.daily_limit = 10000  # requests per day
        self.minute_requests = 0
        self.daily_requests = 0
        self.last_reset = datetime.now()
        self.daily_reset = datetime.now()
        self.backoff_time = 1  # initial backoff in seconds
        self.max_backoff = 64  # maximum backoff in seconds
        self.quota_exceeded = False

    def _should_reset_counters(self) -> None:
        """Reset request counters if time windows have elapsed."""
        now = datetime.now()
        
        # Reset minute counter
        if (now - self.last_reset) >= timedelta(minutes=1):
            self.minute_requests = 0
            self.last_reset = now
            self.backoff_time = 1  # reset backoff on new minute
        
        # Reset daily counter
        if (now - self.daily_reset) >= timedelta(days=1):
            self.daily_requests = 0
            self.daily_reset = now
            self.quota_exceeded = False

    def _update_counters(self) -> None:
        """Update request counters and check limits."""
        self.minute_requests += 1
        self.daily_requests += 1
        
        if self.daily_requests >= self.daily_limit:
            self.quota_exceeded = True
            logging.warning("Daily quota exceeded")

    def _handle_rate_limit(self) -> Tuple[bool, float]:
        """Handle rate limiting and determine if request should proceed.

        Returns:
            Tuple[bool, float]: (should_proceed, wait_time)
        """
        self._should_reset_counters()
        
        if self.quota_exceeded:
            return False, 0
        
        if self.minute_requests >= self.minute_limit:
            wait_time = self.backoff_time
            self.backoff_time = min(self.backoff_time * 2, self.max_backoff)
            return False, wait_time
        
        return True, 0

    async def execute_with_rate_limit(self, func: callable, *args, **kwargs) -> Tuple[Any, Dict]:
        """Execute a function with rate limiting.

        Args:
            func (callable): Function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            Tuple[Any, Dict]: (Result, metadata about the execution)
        """
        metadata = {
            "attempts": 0,
            "total_wait_time": 0,
            "rate_limited": False,
            "quota_exceeded": False
        }

        while metadata["attempts"] < 3:  # maximum 3 retry attempts
            should_proceed, wait_time = self._handle_rate_limit()
            
            if not should_proceed:
                if self.quota_exceeded:
                    metadata["quota_exceeded"] = True
                    return None, metadata
                
                metadata["rate_limited"] = True
                metadata["total_wait_time"] += wait_time
                time.sleep(wait_time)
                metadata["attempts"] += 1
                continue
            
            try:
                self._update_counters()
                result = await func(*args, **kwargs)
                return result, metadata
                
            except Exception as e:
                if "rate limit" in str(e).lower():
                    metadata["rate_limited"] = True
                    metadata["attempts"] += 1
                    continue
                raise
        
        return None, metadata

    def get_quota_status(self) -> Dict:
        """Get current quota and rate limit status.

        Returns:
            Dict: Current quota and rate limit information.
        """
        self._should_reset_counters()
        
        return {
            "minute_requests": self.minute_requests,
            "minute_limit": self.minute_limit,
            "daily_requests": self.daily_requests,
            "daily_limit": self.daily_limit,
            "quota_exceeded": self.quota_exceeded,
            "reset_in": {
                "minute": (self.last_reset + timedelta(minutes=1) - datetime.now()).total_seconds(),
                "day": (self.daily_reset + timedelta(days=1) - datetime.now()).total_seconds()
            }
        }

    def handle_error_response(self, response: Dict) -> Optional[str]:
        """Handle error response and update rate limit status.

        Args:
            response (Dict): Error response from API.

        Returns:
            Optional[str]: Error message if rate limited.
        """
        if "error" not in response:
            return None
            
        error = response["error"].lower()
        
        if "rate limit" in error:
            if "daily" in error:
                self.quota_exceeded = True
                return "Daily quota exceeded"
            else:
                self.minute_requests = self.minute_limit
                return f"Rate limited. Try again in {self.backoff_time} seconds"
                
        return None