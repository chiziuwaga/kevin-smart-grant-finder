import logging
import os
import sys
from datetime import datetime

# Ensure project root is in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

from config.logging_config import setup_logging
from database.mongodb_client import MongoDBClient
from database.pinecone_client import PineconeClient
from utils.agentql_client import AgentQLClient
from utils.perplexity_client import PerplexityClient
from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from utils.notification_manager import NotificationManager

# Setup Logging
setup_logging()
logger = logging.getLogger("grant_finder_scheduler")

def run_scheduled_search():
    """Runs the full grant search, analysis, and notification process."""
    logger.info(f"--- Starting Scheduled Grant Search: {datetime.now()} ---")

    try:
        # --- Initialize Clients and Agents ---
        logger.info("Initializing clients and agents...")
        try:
            mongo_client = MongoDBClient()
            pinecone_client = PineconeClient()
            agentql_client = AgentQLClient()
            perplexity_client = PerplexityClient()
            notifier = NotificationManager()
            research_agent = ResearchAgent(agentql_client, perplexity_client, mongo_client)
            analysis_agent = AnalysisAgent(pinecone_client, mongo_client)
            logger.info("Clients and agents initialized successfully.")
        except Exception as init_error:
            logger.critical(f"CRITICAL: Failed to initialize components during scheduled run: {init_error}", exc_info=True)
            # Potentially send a system alert here if initialization fails
            return # Stop execution if core components fail

        # --- Define Search Parameters (Load from settings or use defaults) ---
        # For scheduled runs, we typically search broadly for both categories
        # Could potentially fetch user settings from DB if multi-user or customizable schedule
        user_settings = mongo_client.get_user_settings() # Get default user settings
        relevance_threshold = user_settings.get("relevance_threshold", 85)

        telecom_params = {
            "category": "telecom",
            "search_terms": ["broadband deployment", "rural connectivity", "telecommunications infrastructure", "fiber optic grants"],
            "sources": [], # Let ResearchAgent use its default/configured sources
            # Add other specific filters if needed for scheduled run
        }
        nonprofit_params = {
            "category": "nonprofit",
            "search_terms": ["women-owned business grant", "nonprofit funding", "community development grant", "women entrepreneurs"],
            "sources": [], # Let ResearchAgent use its default/configured sources
            # Add other specific filters if needed for scheduled run
        }

        all_analyzed_grants = []

        # --- Run Search for Each Category ---
        for params in [telecom_params, nonprofit_params]:
            logger.info(f"Running search for category: {params['category']}")
            try:
                found_grants = research_agent.search_grants(params)
                if found_grants:
                     logger.info(f"Found {len(found_grants)} grants for {params['category']}. Analyzing...")
                     analyzed_grants = analysis_agent.rank_and_summarize_grants(found_grants)
                     # Store analyzed grants (includes upsert logic)
                     mongo_client.store_grants(analyzed_grants)
                     all_analyzed_grants.extend(analyzed_grants)
                     logger.info(f"Completed analysis for {params['category']}.")
                else:
                     logger.info(f"No grants found by ResearchAgent for category: {params['category']}")
            except Exception as search_error:
                logger.error(f"Error during search/analysis for category {params['category']}: {search_error}", exc_info=True)

        # --- Notification Logic ---
        if not all_analyzed_grants:
             logger.info("No new or updated grants found across categories. No notifications sent.")
             return

        logger.info(f"Total analyzed grants across categories: {len(all_analyzed_grants)}")
        
        # Filter for high-priority grants needing alerts
        # Check if alert was already sent recently to avoid duplicates
        alerts_to_send = []
        alert_check_days = 3 # Don't re-alert for the same grant within 3 days
        user_id = user_settings.get("user_id", "default_user")

        for grant in all_analyzed_grants:
            # Grant ID might be ObjectId or string depending on source, handle both
            grant_id_obj = grant.get('_id')
            if not grant_id_obj:
                 logger.warning(f"Grant missing _id, cannot check alert history: {grant.get('title')}")
                 continue
            grant_id_str = str(grant_id_obj)

            score = grant.get('relevance_score', 0)

            if score >= relevance_threshold:
                # Check if alert was sent recently
                try:
                    alert_already_sent = mongo_client.check_alert_sent(user_id, grant_id_str, days_since=alert_check_days)
                    if not alert_already_sent:
                        alerts_to_send.append(grant)
                        # Record that we are about to send the alert
                        mongo_client.record_alert_sent(user_id, grant_id_str)
                    else:
                         logger.debug(f"Alert for grant {grant_id_str} (Score: {score}) was sent within the last {alert_check_days} days. Skipping.")
                except Exception as alert_check_err:
                    logger.error(f"Error checking alert history for grant {grant_id_str}: {alert_check_err}")
                    # Decide whether to send anyway or skip on error
                    # alerts_to_send.append(grant) # Option: Send if check fails
            else:
                 logger.debug(f"Grant {grant_id_str} score ({score}) below threshold ({relevance_threshold}). Skipping alert.")

        if alerts_to_send:
            logger.info(f"Sending notifications for {len(alerts_to_send)} high-priority grants...")
            # Sort alerts by score before sending (optional)
            alerts_to_send.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # Send notifications using NotificationManager
            # Pass user_settings to send_grant_alert
            success = notifier.send_grant_alert(alerts_to_send, user_settings)
            if success:
                 logger.info("Notifications sent successfully.")
            else:
                 logger.warning("Some notifications may have failed to send. Check logs.")
                 # Note: record_alert_sent was already called, so failures won't cause immediate re-sends
        else:
            logger.info("No new high-priority grants require notification.")

    except Exception as e:
        logger.critical(f"CRITICAL ERROR during scheduled grant search: {e}", exc_info=True)
        # Consider sending a system failure alert

    finally:
        logger.info(f"--- Finished Scheduled Grant Search: {datetime.now()} ---")

if __name__ == "__main__":
    run_scheduled_search()
