import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict

from database.mongodb_client import MongoDBClient
from database.pinecone_client import PineconeClient
try:
    from scrapers.sources.louisiana_scraper import LouisianaGrantScraper
except ImportError:
    logger.warning("Could not import LouisianaGrantScraper from scrapers.sources, trying utils.scrapers")
    from utils.scrapers.louisiana_scraper import LouisianaGrantScraper

from utils.notification_manager import NotificationManager
from utils.helpers import calculate_days_remaining

try:
    from utils.api_handlers.perplexity_handler import PerplexityRateLimitHandler
except ImportError:
    logger.warning("Could not import PerplexityRateLimitHandler")
    PerplexityRateLimitHandler = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GrantSearchJob:
    def __init__(self):
        """Initialize grant search job with necessary clients."""
        self.use_mock = os.getenv("SCHEDULED_JOB_MOCK_MODE", "False").lower() == "true"
        logger.info(f"GrantSearchJob initializing (Mock Mode: {self.use_mock})")

        self.mongodb_client = MongoDBClient(use_mock=self.use_mock)
        self.pinecone_client = PineconeClient(use_mock=self.use_mock)
        self.la_scraper = LouisianaGrantScraper(use_mock=self.use_mock)
        self.notifier = NotificationManager(use_mock=self.use_mock)

        if PerplexityRateLimitHandler:
            self.perplexity_handler = PerplexityRateLimitHandler()
        else:
            self.perplexity_handler = None
        
    async def _process_grants(self, grants: List[Dict], user_settings: Dict) -> List[Dict]:
        """Process grants through relevance scoring and filtering based on user settings.

        Args:
            grants (List[Dict]): Raw grant data.
            user_settings (Dict): User settings containing relevance threshold.

        Returns:
            List[Dict]: Processed grants meeting the relevance threshold.
        """
        processed_grants = []
        relevance_threshold_setting = user_settings.get("relevance_threshold", 85)
        relevance_threshold = relevance_threshold_setting / 100.0
        logger.info(f"Using relevance threshold: {relevance_threshold:.2f} (from setting: {relevance_threshold_setting})")

        for grant in grants:
            try:
                description = grant.get('description', '')
                if not description:
                    logger.debug(f"Skipping grant with no description: {grant.get('title', 'N/A')}")
                    continue
                    
                score = self.pinecone_client.calculate_relevance(description)
                grant['relevance_score'] = score
                
                if score >= relevance_threshold:
                    logger.debug(f"Grant '{grant.get('title', 'N/A')}' met relevance threshold ({score:.2f} >= {relevance_threshold:.2f})")
                    processed_grants.append(grant)
                else:
                    logger.debug(f"Grant '{grant.get('title', 'N/A')}' did NOT meet relevance threshold ({score:.2f} < {relevance_threshold:.2f})")
                    
            except Exception as e:
                logger.error(f"Error processing grant '{grant.get('title', 'N/A')}': {e}", exc_info=True)
                continue
                
        return processed_grants

    async def run(self):
        """Execute the grant search job, including scraping, processing, storing, and alerting."""
        try:
            start_time = datetime.now()
            logger.info("Starting grant search job")
            
            user_id = "default_user"
            user_settings = self.mongodb_client.get_user_settings(user_id)
            if not user_settings:
                logger.warning(f"Could not retrieve settings for user '{user_id}'. Using defaults.")
                user_settings = {
                    "relevance_threshold": 85,
                    "deadline_threshold": 30,
                    "notifications": {"sms_enabled": False, "telegram_enabled": False}
                 }

            logger.info("Scraping Louisiana grants...")
            la_grants = self.la_scraper.scrape_grants()
            logger.info(f"Found {len(la_grants)} raw Louisiana grants")
            
            logger.info("Processing grants for relevance...")
            processed_grants = await self._process_grants(la_grants, user_settings)
            logger.info(f"Found {len(processed_grants)} grants meeting relevance threshold.")

            stored_count = 0
            if processed_grants:
                logger.info(f"Storing {len(processed_grants)} processed grants in database...")
                stored_count = self.mongodb_client.store_grants(processed_grants)
                logger.info(f"Stored/Updated {stored_count} grants in database")
            else:
                logger.info("No relevant grants to store.")

            grants_to_alert = []
            ALERT_RECENCY_DAYS = 7 # Don't re-alert for grants alerted within this period
            deadline_threshold_days = user_settings.get("deadline_threshold", 30) # Default 30 days
            notification_prefs = user_settings.get("notifications", {})
            sms_enabled = notification_prefs.get("sms_enabled", False)
            telegram_enabled = notification_prefs.get("telegram_enabled", False)

            if (sms_enabled or telegram_enabled) and processed_grants:
                logger.info(f"Filtering {len(processed_grants)} relevant grants for alerts (Deadline <= {deadline_threshold_days} days, Recency <= {ALERT_RECENCY_DAYS} days)...")
                now = datetime.now()
                grant_ids_to_record = [] # Keep track of grants we actually alert on

                for grant in processed_grants:
                    grant_id = grant.get('_id')
                    if not grant_id:
                        logger.warning(f"Skipping grant for alert check due to missing _id: {grant.get('title')}")
                        continue

                    # Check 1: Deadline
                    deadline = grant.get('deadline')
                    meets_deadline = False
                    if isinstance(deadline, datetime):
                        days_remaining = calculate_days_remaining(deadline, now) # Use helper
                        if 0 <= days_remaining <= deadline_threshold_days:
                             meets_deadline = True
                        else:
                             logger.debug(f"Grant '{grant.get('title', 'N/A')}' ID {grant_id} does NOT meet deadline criteria ({days_remaining} days remaining)")
                    else:
                        logger.debug(f"Grant '{grant.get('title', 'N/A')}' ID {grant_id} has no deadline, skipping for alert.")
                        continue # Skip grants without deadlines for alerts

                    if not meets_deadline:
                        continue

                    # Check 2: Alert Recency
                    already_alerted = self.mongodb_client.check_alert_sent(user_id, grant_id, ALERT_RECENCY_DAYS)

                    if not already_alerted:
                        logger.debug(f"Grant '{grant.get('title', 'N/A')}' ID {grant_id} meets criteria and was not alerted recently.")
                        grants_to_alert.append(grant)
                        grant_ids_to_record.append(grant_id) # Mark this grant for recording
                    else:
                        logger.debug(f"Grant '{grant.get('title', 'N/A')}' ID {grant_id} meets criteria BUT was already alerted within {ALERT_RECENCY_DAYS} days. Skipping.")

            # 6. Send Alerts if needed
            if grants_to_alert:
                logger.info(f"Attempting to send alerts for {len(grants_to_alert)} NEW grants...")
                # Pass user settings to notifier if it needs contact details etc.
                alert_success = self.notifier.send_grant_alert(grants_to_alert, user_settings)
                if alert_success:
                    logger.info("Successfully sent grant alerts.")
                    # Record that alerts were sent for these specific grants
                    for alerted_grant_id in grant_ids_to_record:
                         self.mongodb_client.record_alert_sent(user_id, alerted_grant_id)
                else:
                    logger.error("Failed to send one or more grant alerts.")
            elif sms_enabled or telegram_enabled:
                 logger.info("No new grants met the alerting criteria (relevance, deadline, and recency).")
            else:
                 logger.info("Notifications are disabled in settings.")

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Completed grant search job in {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Critical error in grant search job: {e}", exc_info=True)
            raise

async def main():
    """Main entry point for the grant search job."""
    try:
        job = GrantSearchJob()
        await job.run()
    except Exception as e:
        logger.error(f"Failed to run grant search job: {e}", exc_info=True)
        import sys
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())