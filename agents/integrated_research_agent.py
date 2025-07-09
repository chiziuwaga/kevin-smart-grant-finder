"""
Integration module to switch from deep research to recursive chunked searches.
This module provides backward compatibility while using the new recursive approach.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from agents.recursive_research_agent import RecursiveResearchAgent
from app.models import GrantFilter
from app.schemas import EnrichedGrant
from sqlalchemy.ext.asyncio import async_sessionmaker

logger = logging.getLogger(__name__)

class IntegratedResearchAgent:
    """
    Integrated research agent that uses the new recursive approach
    while maintaining compatibility with existing code.
    """
    
    def __init__(self, db_session_maker: async_sessionmaker):
        self.db_session_maker = db_session_maker
        self.recursive_agent = RecursiveResearchAgent(db_session_maker)
        
        # Maintain compatibility flags
        self.use_recursive_search = True
        self.use_legacy_deep_research = False
        
        logger.info("Integrated Research Agent initialized with recursive search approach")

    async def search_grants(self, grant_filter: GrantFilter) -> List[EnrichedGrant]:
        """
        Main search method that uses recursive chunked approach.
        Replaces the old tier-based deep research method.
        """
        if self.use_recursive_search:
            logger.info("Using recursive chunked search approach")
            return await self.recursive_agent.search_grants_recursive(grant_filter)
        else:
            logger.warning("Legacy deep research is disabled. Using recursive search.")
            return await self.recursive_agent.search_grants_recursive(grant_filter)

    async def enrich_grant_details(self, grant: EnrichedGrant) -> EnrichedGrant:
        """
        Enrich a single grant with additional details using targeted recursive searches.
        Replaces the old deep research approach.
        """
        logger.info(f"Enriching grant details for: {grant.title}")
        
        try:
            # Create a focused search for this specific grant
            focused_filter = GrantFilter(
                keywords=f"{grant.title}, {grant.funder_name or ''}",
                min_score=0.0,
                min_funding=grant.funding_amount_min or 5000,
                max_funding=grant.funding_amount_max or 1000000,
                deadline_before=None,
                deadline_after=None,
                geographic_focus=grant.geographic_scope,
                sites_to_focus=None
            )
            
            # Use recursive agent to get additional details
            additional_grants = await self.recursive_agent.search_grants_recursive(focused_filter)
            
            # Find matching grant and merge details
            for additional_grant in additional_grants:
                if self._grants_match(grant, additional_grant):
                    grant = self._merge_grant_details(grant, additional_grant)
                    break
            
            # Update enrichment log
            grant.enrichment_log.append(f"Enhanced via recursive enrichment at {datetime.now(timezone.utc).isoformat()}")
            grant.last_enriched_at = datetime.now(timezone.utc)
            
            return grant
            
        except Exception as e:
            logger.error(f"Error enriching grant {grant.title}: {e}")
            grant.enrichment_log.append(f"Enrichment failed: {str(e)}")
            return grant

    def _grants_match(self, grant1: EnrichedGrant, grant2: EnrichedGrant) -> bool:
        """Check if two grants are the same opportunity."""
        # Match by title similarity
        title1 = grant1.title.lower().strip()
        title2 = grant2.title.lower().strip()
        
        # Match by URL if available
        if grant1.source_url and grant2.source_url:
            return grant1.source_url == grant2.source_url
        
        # Match by title similarity (simple approach)
        return title1 == title2 or (
            len(title1) > 10 and len(title2) > 10 and 
            (title1 in title2 or title2 in title1)
        )

    def _merge_grant_details(self, original: EnrichedGrant, additional: EnrichedGrant) -> EnrichedGrant:
        """Merge additional details into the original grant."""
        # Merge descriptions if additional has more detail
        if additional.summary_llm and len(additional.summary_llm) > len(original.summary_llm or ""):
            original.summary_llm = additional.summary_llm
        
        # Merge funding information if missing
        if not original.funding_amount_min and additional.funding_amount_min:
            original.funding_amount_min = additional.funding_amount_min
        if not original.funding_amount_max and additional.funding_amount_max:
            original.funding_amount_max = additional.funding_amount_max
        
        # Merge eligibility criteria
        if not original.eligibility_criteria and additional.eligibility_criteria:
            original.eligibility_criteria = additional.eligibility_criteria
        
        # Merge keywords
        if additional.keywords:
            original.keywords = list(set(original.keywords + additional.keywords))
        
        # Update scores if better
        if additional.overall_composite_score and (
            not original.overall_composite_score or 
            additional.overall_composite_score > original.overall_composite_score
        ):
            original.overall_composite_score = additional.overall_composite_score
        
        # Merge enrichment logs
        original.enrichment_log.extend([
            f"Merged with additional search result",
            f"Additional keywords: {additional.keywords}"
        ])
        
        return original

    async def get_search_statistics(self) -> Dict[str, Any]:
        """Get statistics about search performance."""
        return {
            "approach": "recursive_chunked_search",
            "models_used": [
                "sonar-reasoning-pro",
                "sonar-reasoning", 
                "sonar-pro"
            ],
            "deep_research_enabled": False,
            "chunking_enabled": True,
            "rate_limit_strategy": "batch_processing_with_delays"
        }

# Factory function for backward compatibility
def create_research_agent(db_session_maker: async_sessionmaker, **kwargs) -> IntegratedResearchAgent:
    """
    Factory function to create a research agent.
    Provides backward compatibility with existing code.
    """
    return IntegratedResearchAgent(db_session_maker)
