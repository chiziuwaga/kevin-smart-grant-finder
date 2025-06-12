# Key change: Line ~38: Ensured consistency comment for db_sessionmaker parameter

#!/usr/bin/env python
import os
import logging
import asyncio
from dotenv import load_dotenv
from typing import List, Dict, Any
from app.models import GrantFilter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('grant_search')
load_dotenv()

async def main():
    """Main execution function for grant search."""
    logger.info("Starting scheduled grant search")
    
    try:
        from app.services import init_services, services
        from agents.research_agent import ResearchAgent
        from agents.analysis_agent import AnalysisAgent
        from app.crud import create_search_run
        from database.models import Grant as DBGrant

        logger.info("Initializing services...")
        await init_services()
        
        research_agent = ResearchAgent(
            perplexity_client=services.perplexity_client,
            db_sessionmaker=services.db_sessionmaker,  # Ensured consistency
            pinecone_client=services.pinecone_client
        )
        
        # ... rest of the main function implementation
        
    except Exception as e:
        logger.error(f"Error during grant search cycle: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
