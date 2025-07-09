"""
Test script for the new recursive research agent.
This will validate that the new chunked approach works correctly.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from agents.integrated_research_agent import IntegratedResearchAgent
from app.models import GrantFilter
from database.session import AsyncSessionLocal

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_recursive_search():
    """Test the new recursive search functionality."""
    logger.info("Testing recursive grant search...")
    
    try:
        # Create research agent
        research_agent = IntegratedResearchAgent(AsyncSessionLocal)
        
        # Create test filter for Kevin's focus areas
        test_filter = GrantFilter(
            keywords="telecommunications infrastructure, women-owned nonprofit, Natchitoches Parish",
            min_score=0.0,
            min_funding=5000,
            max_funding=100000,
            deadline_after=datetime.now(),
            deadline_before=datetime.now() + timedelta(days=180),
            geographic_focus="Louisiana",
            sites_to_focus=None
        )
        
        # Run the search
        logger.info("Starting recursive grant search test...")
        start_time = datetime.now()
        
        grants = await research_agent.search_grants(test_filter)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Report results
        logger.info(f"Search completed in {duration:.2f} seconds")
        logger.info(f"Found {len(grants)} grants")
        
        for i, grant in enumerate(grants[:5]):  # Show first 5 grants
            logger.info(f"Grant {i+1}: {grant.title}")
            logger.info(f"  Funder: {grant.funder_name}")
            logger.info(f"  Score: {grant.overall_composite_score}")
            logger.info(f"  Geographic: {grant.geographic_scope}")
            logger.info(f"  Sector: {grant.identified_sector}")
            logger.info(f"  Funding: {grant.funding_amount_display}")
            logger.info("---")
        
        # Test enrichment on first grant if available
        if grants:
            logger.info("Testing grant enrichment...")
            enriched_grant = await research_agent.enrich_grant_details(grants[0])
            logger.info(f"Enriched grant: {enriched_grant.title}")
            logger.info(f"Enrichment log: {enriched_grant.enrichment_log}")
        
        # Get statistics
        stats = await research_agent.get_search_statistics()
        logger.info(f"Search statistics: {stats}")
        
        logger.info("Recursive search test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = asyncio.run(test_recursive_search())
    if success:
        print("✅ Recursive search test passed!")
    else:
        print("❌ Recursive search test failed!")
