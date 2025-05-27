import logging
import aiohttp
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self, telegram_token: str, telegram_chat_id: str):
        """Initialize Telegram notification client.
        
        Args:
            telegram_token: The Telegram bot token
            telegram_chat_id: The chat ID to send notifications to
        """
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.telegram_api_base = f"https://api.telegram.org/bot{telegram_token}"
        logger.info("Notification manager initialized with Telegram config")
    
    async def notify_new_grants(self, grants: List[Dict[str, Any]]) -> None:
        """Send notification about new high-priority grants."""
        if not grants:
            return

        # Format grant information
        grant_details = []
        for grant in grants:
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
        message = f"🔔 New High-Priority Grants Found ({timestamp})\n\n"
        message += "\n---\n".join(grant_details)
        
        # Send via Telegram
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
                    else:
                        logger.info(f"Successfully sent notification for {len(grants)} grants")
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {str(e)}")

    async def update_settings(self, settings: Dict[str, Any]) -> None:
        """Update notification settings."""
        # Currently only supports enabling/disabling Telegram
        # Can be extended for other notification methods in the future
        enabled = settings.get("telegram_enabled", True)
        if not enabled:
            logger.info("Telegram notifications disabled")
        else:
            logger.info("Telegram notifications enabled")
