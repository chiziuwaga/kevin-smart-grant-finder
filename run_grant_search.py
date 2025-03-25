#!/usr/bin/env python
"""
Grant Search Execution Script for Kevin's Smart Grant Finder

This script is executed by the Heroku scheduler at scheduled intervals
to search for grants, process results, and send notifications for high-priority matches.
"""

import os
import logging
import time
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Log to console (for Heroku logs)
        logging.FileHandler('logs/grant_search.log')  # Log to file
    ]
)

logger = logging.getLogger('grant_search')

# Load environment variables
load_dotenv()

def main():
    """Main execution function for grant search."""
    start_time = time.time()
    logger.info(f"Starting scheduled grant search at {datetime.now()}")
    
    try:
        # Import here to avoid circular imports
        from database.mongodb_client import MongoDBClient
        from database.pinecone_client import PineconeClient
        from agents.research_agent import ResearchAgent
        from agents.analysis_agent import AnalysisAgent
        from utils.notification_manager import NotificationManager
        from scrapers.sources.louisiana_scraper import LouisianaGrantScraper
        
        # Initialize components with error handling
        try:
            mongodb_client = MongoDBClient()
            pinecone_client = PineconeClient()
            notifier = NotificationManager()
            louisiana_scraper = LouisianaGrantScraper()
            
            logger.info("Initialized all required clients successfully")
        except Exception as e:
            logger.error(f"Failed to initialize clients: {str(e)}")
            return False
        
        # Initialize agents
        research_agent = ResearchAgent(None, None, mongodb_client)  # Clients will be initialized inside
        analysis_agent = AnalysisAgent(pinecone_client, mongodb_client)
        
        # Execute telecommunications grant search
        telecom_params = {
            "category": "telecom",
            "search_terms": ["broadband deployment", "rural connectivity", "telecommunications infrastructure"],
            "funding_type": ["grant", "cooperative agreement"],
            "eligible_entities": ["nonprofits", "municipalities"],
            "geo_restrictions": "LA-08",
            "sources": ["Grants.gov", "USDA", "FCC", "NTIA BroadbandUSA"]
        }
        
        logger.info("Starting telecommunications grant search")
        telecom_grants = research_agent.search_grants(telecom_params)
        logger.info(f"Found {len(telecom_grants)} telecommunications grants")
        
        # Execute women-owned nonprofit grant search
        nonprofit_params = {
            "category": "nonprofit",
            "search_terms": ["women-owned", "women-led", "nonprofit", "501c3"],
            "funding_type": ["grant"],
            "eligible_entities": ["nonprofits"],
            "sources": ["Grants.gov", "SBA", "IFundWomen", "Amber Grant Foundation"]
        }
        
        logger.info("Starting women-owned nonprofit grant search")
        nonprofit_grants = research_agent.search_grants(nonprofit_params)
        logger.info(f"Found {len(nonprofit_grants)} women-owned nonprofit grants")
        
        # Execute Louisiana-specific grant search
        logger.info("Starting Louisiana-specific grant search")
        louisiana_grants = louisiana_scraper.scrape_grants(geo_focus="LA-08")
        
        # Add category to Louisiana grants
        for grant in louisiana_grants:
            grant["category"] = "state"
        
        logger.info(f"Found {len(louisiana_grants)} Louisiana-specific grants")
        
        # Store Louisiana grants in MongoDB
        if louisiana_grants:
            mongodb_client.store_grants(louisiana_grants)
        
        # Load user priorities
        priorities = mongodb_client.get_priorities()
        if not priorities:
            logger.warning("No priorities found in database, using default priorities")
            
            # Default priorities if none found in database
            priorities = {
                "telecom": [
                    "broadband deployment in rural areas",
                    "telecom infrastructure for underserved communities",
                    "closing the digital divide",
                    "high-speed internet access in Louisiana",
                    "5G and advanced networking technologies"
                ],
                "nonprofit": [
                    "women-owned small business support",
                    "nonprofit capacity building",
                    "minority business development",
                    "economic opportunities for disadvantaged communities",
                    "social enterprise development"
                ],
                "weights": {
                    "telecom": 1.0,
                    "nonprofit": 1.0
                }
            }
            
            # Store default priorities
            mongodb_client.store_priorities(priorities)
        
        # Rank grants based on relevance
        logger.info("Ranking telecommunications grants")
        ranked_telecom = analysis_agent.rank_grants(telecom_grants, priorities)
        
        logger.info("Ranking women-owned nonprofit grants")
        ranked_nonprofit = analysis_agent.rank_grants(nonprofit_grants, priorities)
        
        logger.info("Ranking Louisiana-specific grants")
        ranked_louisiana = analysis_agent.rank_grants(louisiana_grants, priorities)
        
        # Get all high-priority grants
        relevance_threshold = float(os.getenv("RELEVANCE_THRESHOLD", "85"))
        
        high_priority_telecom = [g for g in ranked_telecom if g.get("relevance_score", 0) >= relevance_threshold]
        high_priority_nonprofit = [g for g in ranked_nonprofit if g.get("relevance_score", 0) >= relevance_threshold]
        high_priority_louisiana = [g for g in ranked_louisiana if g.get("relevance_score", 0) >= relevance_threshold]
        
        # Combine all high-priority grants
        all_high_priority = high_priority_telecom + high_priority_nonprofit + high_priority_louisiana
        
        # Send notifications for high-priority grants
        if all_high_priority:
            logger.info(f"Sending notification for {len(all_high_priority)} high-priority grants")
            notifier.send_grant_alert(all_high_priority)
        else:
            logger.info("No high-priority grants found. No notifications sent.")
        
        # Log search statistics
        search_stats = {
            "search_date": datetime.now(),
            "total_grants_found": len(telecom_grants) + len(nonprofit_grants) + len(louisiana_grants),
            "high_priority_count": len(all_high_priority),
            "execution_time_seconds": time.time() - start_time,
            "categories": {
                "telecom": len(telecom_grants),
                "nonprofit": len(nonprofit_grants),
                "state": len(louisiana_grants)
            }
        }
        
        logger.info(f"Search statistics: {search_stats}")
        
        # Record search history in MongoDB
        telecom_history = {
            "search_date": datetime.now(),
            "parameters": telecom_params,
            "results_count": len(telecom_grants),
            "high_priority_count": len(high_priority_telecom),
            "category": "telecom"
        }
        
        nonprofit_history = {
            "search_date": datetime.now(),
            "parameters": nonprofit_params,
            "results_count": len(nonprofit_grants),
            "high_priority_count": len(high_priority_nonprofit),
            "category": "nonprofit"
        }
        
        # Store search history
        mongodb_client.store_search_history(telecom_history)
        mongodb_client.store_search_history(nonprofit_history)
        
        logger.info(f"Grant search completed successfully in {time.time() - start_time:.2f} seconds")
        return True
        
    except Exception as e:
        logger.error(f"Error during grant search execution: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    # Execute the search
    success = main()
    
    # Return appropriate exit code
    exit(0 if success else 1) 