"""
Research Agent for finding grant opportunities.
"""

import logging
import time
from datetime import datetime, timedelta
import re
from urllib.parse import urlparse
from typing import Dict, List, Any, Optional, Set
import json # Added import for JSON handling

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker # Added async_sessionmaker

from utils.perplexity_client import PerplexityClient
from utils.pinecone_client import PineconeClient
from app.models import Grant, GrantFilter
from database.models import Grant as DBGrant, Analysis

logger = logging.getLogger(__name__)

# Eligibility rules and site focus constants based on the persona and research document
ELIGIBILITY_RULES = {
    "sectors_primary_keywords": [ # Natchitoches focus
        "telecommunications infrastructure Natchitoches Parish grants",
        "broadband Natchitoches Parish grants",
        "mesh networks Natchitoches Parish grants",
        "event Wi-Fi Natchitoches Parish grants",
        "women-owned nonprofit Natchitoches Parish 501c3 grants",
        "community shelter Natchitoches Parish extreme weather grants"
    ],
    "sectors_secondary_keywords": [ # Statewide Louisiana
        "telecommunications infrastructure Louisiana grants",
        "broadband Louisiana grants",
        "women-owned nonprofit Louisiana 501c3 grants",
        "community shelter Louisiana extreme weather grants"
    ],
    "sectors_tertiary_keywords": [ # Federal
        "federal telecommunications infrastructure grants",
        "federal broadband grants",
        "federal women-owned nonprofit grants 501c3",
        "federal community shelter grants extreme weather"
    ],
    "funding_min": 5000,
    "funding_max": 100000,
    "deadline_lead_days": 30
}

# Example site focus lists (these would ideally be used by PerplexityClient if it supports site-specific searches)
SITE_FOCUS_PRIMARY = [
    "grants.gov", "rd.usda.gov", "natchitochesparishla.gov", 
    "louisianabelieves.com", "opportunitylouisiana.com", "www.louisiana-arts.org", # Added LA arts
    "www.lhc.la.gov" # LA Housing Corp
]
SITE_FOCUS_SECONDARY = [
    "sba.gov", "ifundwomen.com", "ambergrantsforwomen.com", 
    "foundationcenter.org", "candid.org", "techsoup.org" # Broader nonprofit/federal
]
SITE_FOCUS_TERTIARY = ["grants.gov", "sam.gov", "usda.gov/topics/farming/grants-and-loans"]


class ResearchAgent:
    # ELIGIBILITY CRITERIA FROM PERSONA
    SECTOR_KEYWORDS = [
        "telecommunications infrastructure", "broadband", "mesh networks", "event-Wi-Fi",
        "women-owned nonprofit", "501(c)(3)", "community shelter conversions", "extreme weather"
    ]
    FUNDING_MIN = 5000
    FUNDING_MAX = 100000
    DEADLINE_MIN_LEAD_DAYS = 30
    
    # GEOGRAPHIC TIERS (Primary, Secondary, Tertiary)
    SITE_FOCUS_PRIMARY = [
        "grants.gov", "rd.usda.gov", "natchitochesparishla.gov", 
        "louisianabelieves.com", "opportunitylouisiana.com", "www.louisiana-arts.org",
        "www.lhc.la.gov"
    ]
    SITE_FOCUS_SECONDARY = [
        "sba.gov", "ifundwomen.com", "ambergrantsforwomen.com", 
        "foundationcenter.org", "candid.org", "techsoup.org"
    ]
    SITE_FOCUS_TERTIARY = [ # More general federal/broad sources
        "grants.gov", "sam.gov", "usda.gov", "fcc.gov", "ntia.gov"
    ]

    GEO_TIERS = {
        "primary": {"focus": "Natchitoches Parish, LA-08 district", "keywords_modifier": [], "sites": SITE_FOCUS_PRIMARY},
        "secondary": {"focus": "Louisiana", "keywords_modifier": ["statewide"], "sites": SITE_FOCUS_SECONDARY},
        "tertiary": {"focus": "Federal grants", "keywords_modifier": ["federal", "national"], "sites": SITE_FOCUS_TERTIARY}
    }
    
    MIN_RESULTS_PER_TIER_TARGET = 3 # Aim for at least this many before broadening search (adjusted from 5 for testing)

    SONAR_PRIMARY_MODEL = "sonar-pro"
    SONAR_DEEP_MODEL = "sonar-deep-research"

    def __init__(
        self,
        perplexity_client: PerplexityClient,
        db_sessionmaker: async_sessionmaker, # Correct: Changed from db_session: AsyncSession
        pinecone_client: PineconeClient
    ):
        """Initialize Research Agent."""
        self.perplexity = perplexity_client
        self.db_sessionmaker = db_sessionmaker # Store the sessionmaker
        self.pinecone = pinecone_client
        logger.info("Research Agent initialized")

    async def _get_db_session(self) -> AsyncSession: # Helper to get a session
        return self.db_sessionmaker()

    async def get_existing_grant_titles(self) -> Set[str]:
        """Return set of existing grant titles to avoid duplicates."""
        async with self.db_sessionmaker() as session:
            result = await session.execute(select(DBGrant.title))
            return set(result.scalars().all())

    async def store_grants_in_db(self, grants_data: List[Dict[str, Any]]):
        """Store list of grant dicts into the database if not existing."""
        async with self.db_sessionmaker() as session:
            for data in grants_data:
                grant = DBGrant(
                    title=data.get('title'),
                    description=data.get('description'),
                    funding_amount=data.get('funding_amount'),
                    deadline=data.get('deadline'),
                    source=data.get('source_name'),
                    source_url=data.get('source_url'),
                    category=data.get('category'),
                    eligibility=data.get('eligibility_criteria')
                )  # status defaults to ACTIVE via model default
                session.add(grant)
            await session.commit()

    def setup_search_agents(self):
        """Set up AgentQL search agents for both domains."""
        if not self.agentql_client:
            logging.error("AgentQL client not provided, cannot set up agents.")
            return

        # Telecom agent (Sources from updated description)
        self.telecom_agent_id = self.agentql_client.create_search_agent(
            name="TelecomGrantFinder",
            description="Searches for telecommunications and broadband grant opportunities",
            sources=[
                "grants.gov",
                "rd.usda.gov",
                "fcc.gov",
                "ntia.gov",
                "broadbandusa.ntia.doc.gov",
                "broadbandnow.com",
                "ruralhealthinfo.org"
            ]
        )

        # Nonprofit agent (Sources from updated description)
        self.nonprofit_agent_id = self.agentql_client.create_search_agent(
            name="WomenOwnedNonprofitGrantFinder",
            description="Searches for grants for women-owned nonprofits and businesses",
            sources=[
                "grants.gov",
                "sba.gov",
                "ifundwomen.com",
                "ambergrantsforwomen.com",
                "cartier.com/en-us/philanthropy/womens-initiative",
                "terravivagrants.org",
                "techsoup.org"
            ]
        )

        logging.info(f"Set up AgentQL search agents: Telecom ID={self.telecom_agent_id}, Nonprofit ID={self.nonprofit_agent_id}")

    async def search_grants(self, grant_filter: Dict[str, Any] | GrantFilter) -> List[Dict[str, Any]]:
        """Execute tiered grant search with fallback to deep research for comprehensive results."""
        start_time = time.time()
        
        # Convert dict to GrantFilter if needed
        if isinstance(grant_filter, dict):
            grant_filter = GrantFilter(**grant_filter)
            
        # Use the model_dump method which is the new recommended way in Pydantic v2
        try:
            filter_json = json.dumps(grant_filter.model_dump(), indent=2)
        except AttributeError:
            # Fallback for older Pydantic versions
            filter_json = json.dumps(grant_filter.dict(), indent=2)
            
        logger.info(f"ResearchAgent 'DualSector Explorer' starting search with initial filter: {filter_json}")
        
        all_found_grants_map: Dict[str, Dict[str, Any]] = {}
        tier_stats = {}
        
        # Primary search with sonar-reasoning-pro
        for tier_name, tier_config in self.GEO_TIERS.items():
            logger.info(f"Executing search Tier: {tier_name} - Focus: {tier_config['focus']}")
            tier_start = time.time()
            
            # Create specific filters for this tier
            tier_specific_filters = self._create_filters_for_tier(tier_name, tier_config, grant_filter)
            raw_results = await self.perplexity.search(
                query=self._build_search_query(tier_specific_filters),
                model=self.SONAR_PRIMARY_MODEL,
                search_domain_filter=tier_specific_filters.sites_to_focus,
                structured_output=True
            )
            tier_results = await self._parse_and_validate(raw_results)
            
            # Track stats for this tier
            tier_stats[tier_name] = {
                "duration": time.time() - tier_start,
                "results_found": len(tier_results)
            }
            
            for grant_data in tier_results:
                grant_key = grant_data.get("source_url") or grant_data.get("title", "").lower()
                if grant_key and grant_key not in all_found_grants_map:
                    all_found_grants_map[grant_key] = grant_data
        
        initial_results_count = len(all_found_grants_map)
        logger.info(f"Initial search found {initial_results_count} grants")
        
        # If we have less than 2 results, try deep research fallback
        if initial_results_count < 2:
            logger.info("Insufficient results, initiating deep research fallback")
            fallback_start = time.time()
            
            # Create specialized filters for deep research
            deep_research_filters = GrantFilter(
                keywords=grant_filter.keywords,
                categories=grant_filter.categories,
                min_score=grant_filter.min_score,
                deadline_after=grant_filter.deadline_after,
                deadline_before=grant_filter.deadline_before,
                min_funding=grant_filter.min_funding,
                max_funding=grant_filter.max_funding,
                geographic_focus=grant_filter.geographic_focus,
                sites_to_focus=grant_filter.sites_to_focus
            )
            raw_fallback_results = await self.perplexity._execute_search(
                query=self._build_search_query(deep_research_filters),
                model=self.SONAR_DEEP_MODEL,
                search_domain_filter=deep_research_filters.sites_to_focus,
                structured_output=True
            )
            fallback_results = await self._parse_and_validate(raw_fallback_results)
            
            # Track fallback stats
            tier_stats["deep_research_fallback"] = {
                "duration": time.time() - fallback_start,
                "results_found": len(fallback_results)
            }
            
            # Merge fallback results
            for grant_data in fallback_results:
                grant_key = grant_data.get("source_url") or grant_data.get("title", "").lower()
                if grant_key and grant_key not in all_found_grants_map:
                    all_found_grants_map[grant_key] = grant_data
        
        # Final processing
        grants_to_score = list(all_found_grants_map.values())
        total_duration = time.time() - start_time
        
        logger.info(
            f"Search complete in {total_duration:.2f}s. "
            f"Found {len(grants_to_score)} unique grants. "
            f"Tier stats: {json.dumps(tier_stats, indent=2)}"
        )
        
        # Score and return results
        scored_grants = await self._score_and_filter_grants(grants_to_score, grant_filter)
        return scored_grants

    def _build_enhanced_query(self, grant_filter: GrantFilter) -> str:
        """Build a comprehensive query for deep research fallback."""
        base_query = (
            "Analyze and identify innovative grant opportunities with detailed "
            "funding information, eligibility criteria, and deadlines. "
            "Focus on comprehensive structured data including:\n"
            "- Exact funding amounts and ranges\n"
            "- Specific eligibility requirements\n"
            "- Clear application deadlines\n"
            "- Direct source URLs\n"
            "- Program objectives and priorities\n"
        )
        
        if grant_filter.keywords:
            base_query += f"\nSpecific focus areas: {grant_filter.keywords}"
        
        if grant_filter.geographic_focus:
            base_query += f"\nGeographic focus: {grant_filter.geographic_focus}"
        
        return base_query

    def _create_filters_for_tier(self, tier_name: str, tier_config: Dict, base_filter: GrantFilter) -> GrantFilter:
        tier_keywords = list(self.SECTOR_KEYWORDS) # Start with core persona keywords
        if tier_config.get("keywords_modifier"):
            tier_keywords.extend(tier_config["keywords_modifier"])
        if base_filter.keywords:
            # Split base_filter.keywords if it's a comma-separated string, then extend
            base_keywords_list = [k.strip() for k in base_filter.keywords.split(',') if k.strip()]
            tier_keywords.extend(base_keywords_list)
        
        # Determine deadline_after: use base_filter if set, else default from persona
        effective_deadline_after = base_filter.deadline_after
        if effective_deadline_after is None and self.DEADLINE_MIN_LEAD_DAYS is not None:
            effective_deadline_after = datetime.now() + timedelta(days=self.DEADLINE_MIN_LEAD_DAYS)
            
        # Get sites for the current tier
        current_tier_sites = tier_config.get("sites", [])

        # The GrantFilter Pydantic model needs a `sites_to_focus` field.
        # Assuming it was added (if not, this will cause an error during GrantFilter instantiation).
        # For now, I will proceed as if GrantFilter can accept `sites_to_focus`.
        # If GrantFilter does not have this field, we'll need to add it or pass domains differently.

        return GrantFilter(
            keywords=", ".join(list(set(tier_keywords))), # Ensure unique keywords
            categories=base_filter.categories, # Pass along if provided
            min_score=base_filter.min_score, # This will be used after scoring
            deadline_after=effective_deadline_after,
            deadline_before=base_filter.deadline_before,
            min_funding=self.FUNDING_MIN,
            max_funding=self.FUNDING_MAX,
            geographic_focus=tier_config["focus"],
            sites_to_focus=current_tier_sites # Pass the sites for this tier
        )

    async def _execute_search_tier(self, filters: dict, model: str = None, structured_output: bool = False) -> List[Dict[str, Any]]:
        """Execute search for a specific tier with model selection and output formatting.
        
        Args:
            filters: Search filters for this tier
            model: Perplexity model to use (sonar-reasoning-pro or sonar-deep-research)
            structured_output: Whether to request structured output format
        
        Returns:
            List of grant data dictionaries
        """
        query = self._build_search_query(filters)
        # Access Pydantic model fields directly, using None as fallback for Optional fields
        sites_to_focus = filters.sites_to_focus or []
        logger.info(f"Calling Perplexity API for query: {query[:100]}... Sites: {sites_to_focus}")
        
        try:
            raw_results = await self.perplexity._execute_search(
                query=query,
                model=model,
                search_domain_filter=sites_to_focus,
                structured_output=structured_output
            )
            
            # Parse results based on the model and format
            if structured_output:
                parsed_grants = self._parse_structured_results(raw_results)
            else:
                parsed_grants = self._parse_results(raw_results)
            
            logger.info(f"Retrieved {len(parsed_grants)} potential grants from tier search")
            return parsed_grants
            
        except Exception as e:
            logger.error(f"Error executing tier search: {str(e)}")
            return []

    def _meets_funding_criteria(self, funding_amount_str: Optional[Any]) -> bool:
        if funding_amount_str is None: return True
        try:
            if isinstance(funding_amount_str, (int, float)): amount = funding_amount_str
            else: amount = float(re.sub(r'[$,]', '', str(funding_amount_str)))
            return self.FUNDING_MIN <= amount <= self.FUNDING_MAX
        except ValueError:
            logger.warning(f"Could not parse funding amount: {funding_amount_str}")
            return False

    def _meets_deadline_criteria(self, deadline_obj: Optional[Any]) -> bool:
        if deadline_obj is None: return True 
        try:
            deadline_date: Optional[datetime] = None
            if isinstance(deadline_obj, datetime): 
                deadline_date = deadline_obj
            elif isinstance(deadline_obj, str):
                # Try parsing common date formats or relative terms like "in X days"
                match_days = re.search(r'in\\s*(\\d+)\\s*days', deadline_obj, re.IGNORECASE)
                if match_days:
                    days = int(match_days.group(1))
                    deadline_date = datetime.now() + timedelta(days=days)
                else:
                    # Attempt to parse absolute date strings
                    # This list can be expanded with more formats
                    date_formats = ["%Y-%m-%d", "%m/%d/%Y", "%b %d, %Y", "%d %b %Y"]
                    for fmt in date_formats:
                        try:
                            deadline_date = datetime.strptime(deadline_obj, fmt)
                            break
                        except ValueError:
                            continue
                    if deadline_date is None:
                        logger.warning(f"Could not parse deadline string: {deadline_obj} with known formats.")
                        return True # Be lenient if unparseable, or False to be strict
            else:
                logger.warning(f"Unknown deadline format: {type(deadline_obj)}, value: {deadline_obj}")
                return True # Be lenient
            
            if deadline_date is None: # Should not happen if parsing logic is complete
                return True 

            return deadline_date >= (datetime.now() + timedelta(days=self.DEADLINE_MIN_LEAD_DAYS))
        except Exception as e:
            logger.warning(f"Error parsing deadline: {deadline_obj}. Error: {e}")
            return True

    def _build_search_query(self, filters: GrantFilter) -> str:
        query_parts = [
            f"Find grant opportunities for '{filters.geographic_focus}' focusing on: {filters.keywords}."
        ]
        # Persona-specific instructions for Perplexity
        query_parts.append(
            "Target sectors include telecommunications infrastructure (broadband, mesh networks, event-Wi-Fi), "
            "women-owned nonprofit initiatives (501c3), and community shelter conversions for extreme weather."
        )
        # Handle funding range
        if filters.min_funding and filters.max_funding:
            query_parts.append(f"Funding range should ideally be between ${filters.min_funding:,.0f} and ${filters.max_funding:,.0f}.")
        # Deadline information construction
        deadline_info_parts = []
        if filters.deadline_after:
            deadline_info_parts.append(f"application deadlines after {filters.deadline_after.strftime('%Y-%m-%d')}")
        if self.DEADLINE_MIN_LEAD_DAYS is not None and not filters.deadline_after:
            deadline_info_parts.append(f"at least {self.DEADLINE_MIN_LEAD_DAYS} days lead time before the deadline")
        if deadline_info_parts:
            query_parts.append(f"Prefer grants with {' and '.join(deadline_info_parts)}, or rolling applications.")
        else:
            query_parts.append("Prioritize grants with rolling applications or significant lead time.")
        # Handle site focus
        if filters.sites_to_focus:
            sites_text = ", ".join(filters.sites_to_focus[:3])
            query_parts.append(f"Pay special attention to sources like {sites_text} if relevant.")
        if filters.categories:
            query_parts.append(f"Consider categories such as: {', '.join(filters.categories)}.")
        # Enforce structured output
        query_parts.append(
            "Return the results as a JSON array. Each grant must include: title, funding_amount, deadline, category, url, and description."
        )
        query = " ".join(query_parts)
        query += " For each grant, provide title, a detailed description, funding amount, exact application deadline, eligibility criteria, and the direct source URL."
        query += " Focus on publicly accessible information and avoid paywalled sources."
        logger.debug(f"Constructed Perplexity Query: {query}")
        return query

    async def _parse_and_validate(self, raw_response, retries=3):
        for attempt in range(retries):
            try:
                grants = json.loads(raw_response)
                missing = [
                    g for g in grants
                    if not all(k in g and g[k] for k in ["title", "funding_amount", "deadline", "category", "url", "description"])
                ]
                if not missing:
                    return grants
                # If missing fields, re-prompt
                prompt = (
                    f"Some grants are missing fields: {missing}. "
                    "Please provide all required fields for each grant."
                )
                raw_response = await self.perplexity.search(prompt)
            except Exception:
                # If not valid JSON, re-prompt for correct JSON
                prompt = (
                    "The previous response was not valid JSON. "
                    "Please return the grants as a JSON array with all required fields."
                )
                raw_response = await self.perplexity.search(prompt)
        return []  # Return empty if still incomplete after retries

    async def _score_and_filter_grants(self, grants_to_score: List[Dict[str, Any]], grant_filter: Dict[str, Any] | GrantFilter) -> List[Dict[str, Any]]:
        """Score and filter grants based on relevance criteria.
        
        Args:
            grants_to_score: List of grant dictionaries to score and filter
            grant_filter: Dictionary or GrantFilter object containing filtering criteria
            
        Returns:
            List of grants sorted by relevance score, filtered by minimum score
        """
        # Convert dict filter to GrantFilter if needed
        if isinstance(grant_filter, dict):
            grant_filter = GrantFilter(**grant_filter)

        scored_grants = []
        for grant in grants_to_score:
            if not grant:
                continue

            # Calculate base score
            base_score = 1.0
            
            # Score based on funding amount match
            if self._meets_funding_criteria(grant.get('funding_amount')):
                base_score += 0.3
                
            # Score based on deadline criteria
            if self._meets_deadline_criteria(grant.get('deadline')):
                base_score += 0.3
                
            # Score based on geographic focus match
            geo_focus = grant.get('geographic_focus', '').lower()
            if geo_focus:
                if grant_filter.geographic_focus and grant_filter.geographic_focus.lower() in geo_focus:
                    base_score += 0.4
                elif 'federal' in geo_focus or 'national' in geo_focus:
                    base_score += 0.2
                    
            # Score based on keyword matches in title and description
            if grant_filter.keywords:
                keywords = [k.strip().lower() for k in grant_filter.keywords.split(',')]
                text_to_search = f"{grant.get('title', '')} {grant.get('description', '')}".lower()
                keyword_matches = sum(1 for k in keywords if k in text_to_search)
                base_score += 0.1 * min(keyword_matches, 3)  # Cap at 0.3
                
            # Apply any category-based scoring
            if grant_filter.categories and grant.get('category'):
                matching_categories = sum(1 for c in grant_filter.categories if c.lower() in grant.get('category', '').lower())
                base_score += 0.1 * min(matching_categories, 2)  # Cap at 0.2
                
            grant['relevance_score'] = round(base_score, 2)
            
            # Filter by minimum score if specified
            if not grant_filter.min_score or grant['relevance_score'] >= grant_filter.min_score:
                scored_grants.append(grant)

        # Sort by relevance score (descending)
        return sorted(scored_grants, key=lambda x: x['relevance_score'], reverse=True)