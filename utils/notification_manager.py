import os
from twilio.rest import Client
import telegram
import logging
from typing import Dict, Any, Union, List
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class NotificationManager:
    def __init__(self):
        """Initialize notification clients for SMS and Telegram."""
        # Twilio setup
        self.twilio_client = None
        self.twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
        
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        if twilio_sid and twilio_token:
            self.twilio_client = Client(twilio_sid, twilio_token)
        
        # Telegram setup
        self.telegram_bot = None
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if telegram_token:
            self.telegram_bot = telegram.Bot(token=telegram_token)
    
    def format_grant_message(self, grant: Dict[str, Any]) -> str:
        """Format a grant notification message."""
        deadline = grant['deadline'].strftime('%B %d, %Y') if grant['deadline'] else 'Rolling'
        amount = f"${grant['amount']:,.2f}" if grant['amount'] else 'Varies'
        
        return f"""
🔔 New High-Priority Grant Alert!

Title: {grant['title']}
Deadline: {deadline}
Amount: {amount}
Score: {grant['relevance_score']}%

{grant['description'][:200]}...

Source: {grant['source_name']}
"""
    
    def send_sms(self, message: str, to_number: str) -> bool:
        """Send an SMS notification."""
        if not self.twilio_client or not self.twilio_phone:
            logging.warning("Twilio not configured. SMS notification skipped.")
            return False
        
        try:
            self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_phone,
                to=to_number
            )
            return True
        except Exception as e:
            logging.error(f"Failed to send SMS: {str(e)}")
            return False
    
    def send_telegram(self, message: str) -> bool:
        """Send a Telegram notification."""
        if not self.telegram_bot or not self.telegram_chat_id:
            logging.warning("Telegram not configured. Notification skipped.")
            return False
        
        try:
            self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='HTML'
            )
            return True
        except Exception as e:
            logging.error(f"Failed to send Telegram message: {str(e)}")
            return False
    
    def send_grant_alert(self, grants: Union[Dict[str, Any], List[Dict[str, Any]]]) -> bool:
        """Send notifications about new grants through all configured channels."""
        if isinstance(grants, dict):
            grants = [grants]
        
        success = True
        for grant in grants:
            message = self.format_grant_message(grant)
            
            # Send via SMS if configured
            if os.getenv("NOTIFICATION_SMS_ENABLED", "true").lower() == "true":
                to_number = os.getenv("NOTIFICATION_PHONE_NUMBER")
                if to_number:
                    success = success and self.send_sms(message, to_number)
            
            # Send via Telegram if configured
            if os.getenv("NOTIFICATION_TELEGRAM_ENABLED", "true").lower() == "true":
                success = success and self.send_telegram(message)
        
        return success
