#!/usr/bin/env python
"""
Grant Search Execution Script for Kevin's Smart Grant Finder

This script is executed by the Heroku scheduler to search for grants and send notifications.
"""

import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('grant_search')

# Load environment variables
load_dotenv()

async def main():
    """Main execution function for grant search."""
    logger.info("Starting scheduled grant search")
    
    try:
        # Import services and agents
        from app.services import init_services, services
        from agents.research_agent import ResearchAgent
        from agents.analysis_agent import AnalysisAgent

        # Initialize all services
        logger.info("Initializing services...")
        await init_services()
        
        # Create agents
        research_agent = ResearchAgent(
            perplexity_client=services.perplexity_client,
            mongodb_client=services.mongodb_client,
            pinecone_client=services.pinecone_client
        )
        
        analysis_agent = AnalysisAgent(
            mongodb_client=services.mongodb_client,
            pinecone_client=services.pinecone_client
        )
        
        # Run search with default parameters
        logger.info("Starting grant search...")
        results = await research_agent.search_grants({})
        
        logger.info("Analyzing results...")
        analyzed = await analysis_agent.analyze_grants(results)
        
        # Notify if new grants found
        if analyzed:
            logger.info(f"Found {len(analyzed)} new high-priority grants. Sending notification...")
            await services.notifier.notify_new_grants(analyzed)
        else:
            logger.info("No new high-priority grants found")
            
        # Store search metadata
        await services.mongodb_client.store_search_run({
            "timestamp": datetime.now(),
            "grants_found": len(results),
            "high_priority": len(analyzed)
        })
        
        logger.info("Grant search completed successfully")
        
    except Exception as e:
        logger.error(f"Error during grant search: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())