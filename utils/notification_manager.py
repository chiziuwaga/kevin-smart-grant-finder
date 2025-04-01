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
        # self.use_mock = use_mock # Commented out
        
        # if not use_mock: # Commented out
        # Twilio setup
        self.twilio_client = None
        self.twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
        
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        if twilio_sid and twilio_token:
            try:
                self.twilio_client = Client(twilio_sid, twilio_token)
                logging.info("Twilio client initialized.")
            except Exception as e:
                 logging.error(f"Failed to initialize Twilio client: {e}")
        else:
             logging.warning("Twilio SID or Auth Token missing. SMS disabled.")
        
        # Telegram setup
        self.telegram_bot = None
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if telegram_token:
            try:
                self.telegram_bot = telegram.Bot(token=telegram_token)
                logging.info("Telegram bot initialized.")
            except Exception as e:
                 logging.error(f"Failed to initialize Telegram bot: {e}")
        else:
             logging.warning("Telegram Bot Token missing. Telegram disabled.")
        # else: # Commented out
        #     logging.info("Using mock notification manager") # Commented out
        #     self.mock_notifications = [] # Commented out
    
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
        # if self.use_mock: # Commented out
        #     # ... mock sms logic ... # Commented out
        #     return True # Commented out
            
        if not self.twilio_client or not self.twilio_phone:
            logging.warning("Twilio not configured or failed to initialize. Cannot send SMS.")
            return False
        
        if not to_number:
             logging.warning("Recipient phone number (to_number) is missing. Cannot send SMS.")
             return False
             
        try:
            self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_phone,
                to=to_number
            )
            logging.info(f"SMS sent successfully to {to_number[:5]}...{to_number[-2:]}")
            return True
        except Exception as e:
            logging.error(f"Failed to send SMS: {str(e)}")
            return False
    
    # Change: Made send_telegram async
    async def send_telegram_async(self, message: str) -> bool:
        """Send a Telegram notification asynchronously."""
        # if self.use_mock: # Commented out
        #     # ... mock telegram logic ... # Commented out
        #     return True # Commented out
            
        if not self.telegram_bot or not self.telegram_chat_id:
            logging.warning("Telegram not configured or failed to initialize. Cannot send Telegram message.")
            return False
        
        try:
            await self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='HTML' # Or Markdown, depending on format_grant_message
            )
            logging.info("Telegram message sent successfully.")
            return True
        except Exception as e:
            logging.error(f"Failed to send Telegram message: {str(e)}")
            return False
    
    def send_grant_alert(self, grants: Union[Dict[str, Any], List[Dict[str, Any]]], user_settings: Dict) -> bool:
        """Send notifications about new grants through enabled channels."""
        if isinstance(grants, dict):
            grants = [grants]
        if not grants:
             return True # Nothing to send

        # Get notification preferences and details from user_settings
        prefs = user_settings.get("notifications", {})
        sms_enabled = prefs.get("sms_enabled", False)
        telegram_enabled = prefs.get("telegram_enabled", False)
        sms_number = prefs.get("sms_number")
        # Telegram username/chat_id might be needed here if different from global config
        # telegram_target = prefs.get("telegram_username") or self.telegram_chat_id

        overall_success = True
        num_grants = len(grants)
        logger.info(f"Preparing alerts for {num_grants} grant(s). SMS: {sms_enabled}, Telegram: {telegram_enabled}")

        # Combine messages if sending multiple grants to avoid spamming
        # For simplicity, sending one message per grant for now
        for grant in grants:
            grant_success = True
            message = self.format_grant_message(grant)
            
            # Send via SMS if configured and number available
            if sms_enabled and sms_number:
                sms_sent = self.send_sms(message, sms_number)
                if not sms_sent:
                     grant_success = False
                     logger.warning(f"Failed to send SMS for grant: {grant.get('title')}")
            elif sms_enabled and not sms_number:
                 logger.warning(f"SMS enabled but no phone number configured in settings for user {user_settings.get('user_id')}")
            
            # Send via Telegram if configured
            if telegram_enabled:
                # Run the async telegram send in a sync context if needed
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running (like in Streamlit), create a new task
                        task = loop.create_task(self.send_telegram_async(message))
                        # This won't block, need to decide if we wait or not
                        # For now, just schedule it
                        # telegram_sent = await task # This would require send_grant_alert to be async
                        pass # Fire and forget for now
                    else:
                        telegram_sent = asyncio.run(self.send_telegram_async(message))
                        if not telegram_sent:
                            grant_success = False
                            logger.warning(f"Failed to send Telegram for grant: {grant.get('title')}")
                except RuntimeError as e:
                     # Handle cases where there's no current event loop or it's closed
                     if "Cannot run the event loop" in str(e):
                          # Create and run in a new loop
                          telegram_sent = asyncio.run(self.send_telegram_async(message))
                          if not telegram_sent:
                               grant_success = False
                               logger.warning(f"Failed to send Telegram for grant: {grant.get('title')}")
                     else:
                          logger.error(f"RuntimeError sending Telegram message: {e}")
                          grant_success = False

            if not grant_success:
                 overall_success = False # Mark overall failure if any grant fails
        
        return overall_success
