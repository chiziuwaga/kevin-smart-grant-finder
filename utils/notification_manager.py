import os
# Removed: from twilio.rest import Client
import telegram
import logging
from typing import Dict, Any, Union, List
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class NotificationManager:
    def __init__(self):
        """Initialize notification clients for Telegram."""
        # Twilio setup REMOVED
        # self.twilio_client = None
        # self.twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
        # twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        # twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        # if twilio_sid and twilio_token:
        #     try:
        #         self.twilio_client = Client(twilio_sid, twilio_token)
        #         logging.info("Twilio client initialized.")
        #     except Exception as e:
        #          logging.error(f"Failed to initialize Twilio client: {e}")
        # else:
        #      logging.warning("Twilio SID or Auth Token missing. SMS disabled.")
        
        # Telegram setup
        self.telegram_bot = None
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID") # Used for general alerts
        
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if telegram_token:
            try:
                # Use telegram.Bot for sending, Application might be needed elsewhere for receiving
                self.telegram_bot = telegram.Bot(token=telegram_token)
                logging.info("Telegram bot initialized for sending.")
            except Exception as e:
                 logging.error(f"Failed to initialize Telegram bot: {e}")
        else:
             logging.warning("Telegram Bot Token missing. Telegram disabled.")
    
    def format_grant_message(self, grant: Dict[str, Any]) -> str:
        """Format a grant notification message."""
        deadline_dt = grant.get('deadline')
        deadline = deadline_dt.strftime('%B %d, %Y') if isinstance(deadline_dt, datetime) else 'Rolling'
        amount_val = grant.get('amount')
        amount = f"${amount_val:,.2f}" if isinstance(amount_val, (int, float)) else 'Varies'
        score = grant.get('relevance_score', 'N/A')
        desc = grant.get('description', '')
        desc_short = desc[:200] + "..." if len(desc) > 200 else desc
        source = grant.get('source_name', 'Unknown')
        url = grant.get('source_url')
        url_link = f'\n<a href="{url}">View Grant</a>' if url else '' # Add HTML link if URL exists
        
        # Using basic HTML for formatting for Telegram
        return f"""
🔔 <b>New High-Priority Grant Alert!</b>

<b>Title:</b> {grant.get('title', 'N/A')}
<b>Deadline:</b> {deadline}
<b>Amount:</b> {amount}
<b>Score:</b> {score}%

<i>{desc_short}</i>

<b>Source:</b> {source}{url_link}
"""
    
    # REMOVED send_sms method entirely
    # def send_sms(self, message: str, to_number: str) -> bool:
    #    ...
    
    async def send_telegram_async(self, message: str) -> bool:
        """Send a Telegram notification asynchronously."""
        if not self.telegram_bot or not self.telegram_chat_id:
            logging.warning("Telegram not configured or failed to initialize. Cannot send Telegram message.")
            return False
        
        try:
            await self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='HTML' # Ensure format_grant_message produces valid HTML
            )
            logging.info("Telegram message sent successfully.")
            return True
        except telegram.error.TelegramError as e:
            logging.error(f"Telegram API error sending message: {e}")
            return False
        except Exception as e:
            logging.error(f"Failed to send Telegram message: {str(e)}", exc_info=True)
            return False
    
    # Simplified: Assumes user_settings comes from a single source now
    # Removed user_settings parameter, uses configured chat_id
    def send_grant_alert(self, grants: Union[Dict[str, Any], List[Dict[str, Any]]]) -> bool:
        """Send notifications about new grants via Telegram."""
        if isinstance(grants, dict):
            grants = [grants]
        if not grants:
             return True # Nothing to send

        overall_success = True
        num_grants = len(grants)
        logger.info(f"Preparing Telegram alerts for {num_grants} grant(s).")

        for grant in grants:
            grant_success = True
            message = self.format_grant_message(grant)
            
            # Send via Telegram 
            # Run the async telegram send in a sync context if needed
            import asyncio
            try:
                # Use asyncio.run() to run the async function from sync code
                telegram_sent = asyncio.run(self.send_telegram_async(message))
                if not telegram_sent:
                    grant_success = False
                    logger.warning(f"Failed to send Telegram for grant: {grant.get('title')}")

            except RuntimeError as e:
                 # Handle asyncio errors, e.g., if an event loop is already running
                 # This might happen within Streamlit or other frameworks
                 logger.error(f"RuntimeError sending Telegram message (may need loop handling): {e}")
                 # Trying to get existing loop or create new one - careful with framework integration
                 try:
                     loop = asyncio.get_event_loop_policy().get_event_loop()
                     if loop.is_running():
                         # Schedule as task if loop is running
                         asyncio.ensure_future(self.send_telegram_async(message))
                         logger.info("Scheduled Telegram send in running loop.")
                         # Note: Success not guaranteed here, fire-and-forget
                     else:
                         # If loop exists but isn't running, run until complete
                         telegram_sent = loop.run_until_complete(self.send_telegram_async(message))
                         if not telegram_sent:
                            grant_success = False
                            logger.warning(f"Failed to send Telegram (existing loop) for grant: {grant.get('title')}")
                 except Exception as loop_e:
                    logger.error(f"Error handling asyncio loop for Telegram: {loop_e}")
                    grant_success = False
                 
            except Exception as e:
                 logger.error(f"Unexpected error sending Telegram: {e}", exc_info=True)
                 grant_success = False

            if not grant_success:
                 overall_success = False # Mark overall failure if any grant fails
        
        return overall_success
