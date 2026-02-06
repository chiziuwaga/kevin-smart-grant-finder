#!/usr/bin/env python
"""
Grant Search Execution Script for Kevin's Smart Grant Finder

This script is executed by Celery Beat to search for grants and send notifications.
"""

import os
import logging
import asyncio
from dotenv import load_dotenv
from typing import List, Dict, Any # Added import for type hints
from app.models import GrantFilter # Import GrantFilter Pydantic model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('grant_search')

# Load environment variables
load_dotenv()

async def main():
    """Main execution function for grant search."""
    logger.info("Starting scheduled grant search")
    
    try:
        from app.services import init_services, services
        from agents.research_agent import ResearchAgent
        from agents.analysis_agent import AnalysisAgent
        from app.crud import create_search_run # Assuming this function will be created in crud.py
        from database.models import Grant as DBGrant # For type hinting if needed        logger.info("Initializing services...")
        await init_services()
        
        research_agent = ResearchAgent(
            deepseek_client=services.deepseek_client,
            db_session_maker=services.db_sessionmaker
        )

        analysis_agent = AnalysisAgent(
            db_sessionmaker=services.db_sessionmaker,
            vector_client=services.vector_client
        )
        
        logger.info("Starting grant data retrieval...")
        # Instantiate GrantFilter, even if it's empty for a default broad search
        initial_filters = GrantFilter() # Create an instance of GrantFilter
        grant_data_list = await research_agent.search_grants(initial_filters) 
        
        logger.info(f"Retrieved {len(grant_data_list)} potential grants. Starting analysis and storage...")
        # analysis_agent.analyze_grants will handle scoring, deduplication, and DB storage (Grant & Analysis records)
        # It should return the list of grants that were actually processed and stored as high priority.
        high_priority_grants: List[Dict[str, Any]] = await analysis_agent.analyze_grants(grant_data_list)
        
        logger.info(f"Analysis complete. {len(high_priority_grants)} high-priority grants identified and stored.")

        # Record the search run
        async with services.db_sessionmaker() as session:
            await create_search_run(
                db=session, 
                grants_found=len(grant_data_list),
                high_priority_found=len(high_priority_grants),
                search_filters={} # Add actual filters if used
            )
        logger.info("Search run recorded.")
        
        if high_priority_grants:
            logger.info(f"Sending notification for {len(high_priority_grants)} high-priority grants...")
            if hasattr(services, 'notifier') and services.notifier:
                await services.notifier.notify_new_grants(high_priority_grants)
            else:
                logger.warning("Notifier service not available.")
        else:
            logger.info("No new high-priority grants to notify.")
            
        logger.info("Grant search cycle completed successfully.")
        
    except Exception as e:
        logger.error(f"Error during grant search cycle: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())