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
        self.quota_exceeded_until = None

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
            self.quota_exceeded_until = None
            
        # Check if quota exceeded period has passed
        if self.quota_exceeded_until and now >= self.quota_exceeded_until:
            self.quota_exceeded = False
            self.quota_exceeded_until = None
            logging.info("Perplexity API daily quota reset period has passed")

    def _update_counters(self) -> None:
        """Update request counters and check limits."""
        self.minute_requests += 1
        self.daily_requests += 1
        
        if self.daily_requests >= self.daily_limit:
            self.quota_exceeded = True
            self.quota_exceeded_until = datetime.now() + timedelta(hours=24)
            logging.warning(f"Daily quota exceeded. Reset at {self.quota_exceeded_until}")

    def _handle_rate_limit(self) -> Tuple[bool, float]:
        """Handle rate limiting and determine if request should proceed.

        Returns:
            Tuple[bool, float]: (should_proceed, wait_time)
        """
        self._should_reset_counters()
        
        if self.quota_exceeded:
            logging.warning("Daily quota exceeded, cannot proceed with request")
            return False, 0
        
        if self.minute_requests >= self.minute_limit:
            wait_time = self.backoff_time
            self.backoff_time = min(self.backoff_time * 2, self.max_backoff)
            logging.info(f"Rate limit hit. Waiting {wait_time}s before retry")
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
            "quota_exceeded": False,
            "success": False,
            "fallback_used": False
        }

        max_attempts = 5  # Maximum retry attempts
        while metadata["attempts"] < max_attempts:
            should_proceed, wait_time = self._handle_rate_limit()
            
            if not should_proceed:
                if self.quota_exceeded:
                    metadata["quota_exceeded"] = True
                    logging.warning("Switching to fallback mechanism due to quota exceeded")
                    return None, metadata
                
                metadata["rate_limited"] = True
                metadata["total_wait_time"] += wait_time
                metadata["attempts"] += 1
                
                # Wait for backoff period
                time.sleep(wait_time)
                continue
            
            try:
                self._update_counters()
                result = await func(*args, **kwargs)
                metadata["success"] = True
                return result, metadata
                
            except Exception as e:
                metadata["attempts"] += 1
                
                # Check for rate limit errors in exception message
                if "rate limit" in str(e).lower() or "429" in str(e) or "too many requests" in str(e).lower():
                    metadata["rate_limited"] = True
                    wait_time = self.backoff_time
                    self.backoff_time = min(self.backoff_time * 2, self.max_backoff)
                    
                    logging.warning(f"Rate limit error (attempt {metadata['attempts']}). Retrying in {wait_time}s")
                    time.sleep(wait_time)
                    metadata["total_wait_time"] += wait_time
                    continue
                    
                # Check for daily quota errors
                elif "quota" in str(e).lower() or "limit exceeded" in str(e).lower():
                    self.quota_exceeded = True
                    self.quota_exceeded_until = datetime.now() + timedelta(hours=24)
                    metadata["quota_exceeded"] = True
                    logging.error(f"API quota exceeded. Reset expected at {self.quota_exceeded_until}")
                    return None, metadata
                    
                # Other errors - re-raise
                else:
                    logging.error(f"Error executing function: {str(e)}")
                    raise
        
        # If we've reached here, we've exhausted all attempts
        logging.error(f"Failed after {max_attempts} attempts. Consider fallback mechanism")
        return None, metadata

    def get_quota_status(self) -> Dict:
        """Get current quota and rate limit status.

        Returns:
            Dict: Current quota and rate limit information.
        """
        self._should_reset_counters()
        
        # Calculate reset times
        minute_reset = (self.last_reset + timedelta(minutes=1) - datetime.now()).total_seconds()
        daily_reset = (self.daily_reset + timedelta(days=1) - datetime.now()).total_seconds()
        
        # If we've exceeded quota, use the specific reset time
        if self.quota_exceeded_until:
            daily_reset = (self.quota_exceeded_until - datetime.now()).total_seconds()
        
        return {
            "minute_requests": self.minute_requests,
            "minute_limit": self.minute_limit,
            "daily_requests": self.daily_requests,
            "daily_limit": self.daily_limit,
            "quota_exceeded": self.quota_exceeded,
            "reset_in": {
                "minute": max(0, minute_reset),
                "day": max(0, daily_reset)
            },
            "backoff_time": self.backoff_time
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
            if "daily" in error or "quota" in error:
                self.quota_exceeded = True
                self.quota_exceeded_until = datetime.now() + timedelta(hours=24)
                return f"Daily quota exceeded. Reset expected at {self.quota_exceeded_until.strftime('%H:%M:%S')}"
            else:
                self.minute_requests = self.minute_limit
                return f"Rate limited. Try again in {self.backoff_time} seconds"
        
        return None

    def use_fallback_mechanism(self, fallback_func: callable, *args, **kwargs) -> Any:
        """Use a fallback mechanism when rate limits are hit.
        
        Args:
            fallback_func (callable): Fallback function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
            
        Returns:
            Any: Result from fallback function.
        """
        try:
            logging.info("Using fallback mechanism due to rate limits")
            return fallback_func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in fallback mechanism: {str(e)}")
            return None