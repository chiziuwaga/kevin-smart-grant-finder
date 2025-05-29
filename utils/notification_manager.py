import logging
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)
metrics_logger = logging.getLogger("metrics")

class RateLimiter:
    """Simple token bucket rate limiter"""
    def __init__(self, rate: int, per: int):
        self.rate = rate  # Number of tokens
        self.per = per   # Time period in seconds
        self.tokens = rate
        self.last_update = datetime.now()
        
    async def acquire(self):
        now = datetime.now()
        time_passed = (now - self.last_update).total_seconds()
        self.tokens = min(
            self.rate,
            self.tokens + time_passed * (self.rate / self.per)
        )
        
        if self.tokens < 1:
            wait_time = (1 - self.tokens) * (self.per / self.rate)
            await asyncio.sleep(wait_time)
            self.tokens = 0
            self.last_update = datetime.now()
        else:
            self.tokens -= 1
            self.last_update = now

class NotificationManager:
    def __init__(self, telegram_token: str, telegram_chat_id: str):
        """Initialize notification manager with rate limiting and batching."""
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.telegram_api_base = f"https://api.telegram.org/bot{telegram_token}"
        self.rate_limiter = RateLimiter(rate=30, per=60)  # 30 messages per minute
        self.notification_queue = deque()
        self.batch_size = 5  # Number of grants to batch in one message
        self.enabled = True
        logger.info("Notification manager initialized with rate limiting and batching")
        
    async def notify_new_grants(self, grants: List[Dict[str, Any]]) -> None:
        """Send notification about new high-priority grants with batching."""
        if not grants or not self.enabled:
            return

        start_time = datetime.now()
        total_grants = len(grants)
        sent_count = 0
        error_count = 0

        try:
            # Split grants into batches
            for i in range(0, len(grants), self.batch_size):
                batch = grants[i:i + self.batch_size]
                
                # Format grant information
                grant_details = []
                for grant in batch:
                    deadline = grant.get('deadline', 'No deadline specified')
                    funding = grant.get('funding_amount', 'Amount not specified')
                    
                    details = (
                        f"📋 {grant['title']}\n"
                        f"💰 Funding: {funding}\n"
                        f"⏰ Deadline: {deadline}\n"
                        f"🏷️ Category: {grant.get('category', 'Unspecified')}\n"
                    )
                    grant_details.append(details)

                # Create message
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                message = f"🔔 New High-Priority Grants ({timestamp}) - Batch {i//self.batch_size + 1}\n\n"
                message += "\n---\n".join(grant_details)
                
                # Rate limit and send
                await self.rate_limiter.acquire()
                
                try:
                    url = f"{self.telegram_api_base}/sendMessage"
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json={
                            "chat_id": self.telegram_chat_id,
                            "text": message,
                            "parse_mode": "HTML"
                        }) as response:
                            if response.status != 200:
                                error_data = await response.text()
                                logger.error(f"Failed to send Telegram notification: {error_data}")
                                error_count += 1
                            else:
                                sent_count += len(batch)
                                logger.info(f"Successfully sent notification batch {i//self.batch_size + 1}")
                
                except Exception as e:
                    logger.error(f"Error sending Telegram notification batch: {str(e)}")
                    error_count += 1

        finally:
            # Log metrics
            duration = (datetime.now() - start_time).total_seconds()
            metrics_logger.info(
                "Notification Metrics",
                extra={
                    "metrics": {
                        "total_grants": total_grants,
                        "sent_count": sent_count,
                        "error_count": error_count,
                        "duration_ms": round(duration * 1000, 2),
                        "timestamp": datetime.now().isoformat()
                    }
                }
            )

    async def update_settings(self, settings: Dict[str, Any]) -> None:
        """Update notification settings."""
        enabled = settings.get("telegram_enabled", True)
        self.enabled = enabled
        
        logger.info(
            "Notification settings updated",
            extra={
                "extra_fields": {
                    "telegram_enabled": enabled,
                    "timestamp": datetime.now().isoformat()
                }
            }
        )
