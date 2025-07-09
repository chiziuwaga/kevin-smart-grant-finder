"""
Research Agent for finding grant opportunities.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Set # Added Set
import asyncio
import json
import time
import yaml # Added yaml
import re # Added re
from datetime import datetime, timedelta, timezone # Added timezone

from utils import perplexity_client as perplexity
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession # Added AsyncSession
from sqlalchemy.sql import select # Added select

from utils.pinecone_client import PineconeClient
from app.models import GrantFilter # Assuming GrantFilter is a Pydantic model here
from database.models import Grant as DBGrant, Analysis
# Import new schemas
from app.schemas import EnrichedGrant, ResearchContextScores, UserProfile, GrantSource, SectorConfig, GeographicConfig, KevinProfileConfig, ComplianceScores, GrantSourceDetails # Added GrantSourceDetails
from pydantic import ValidationError # Added ValidationError

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
        db_session_maker: async_sessionmaker,
        perplexity_client: Optional[perplexity.PerplexityClient] = None, # Changed Perplexity to PerplexityClient
        config_path: str = "config"
    ):
        """Initialize Research Agent with configuration loading."""
        if not perplexity_client:
            raise ValueError("Perplexity client cannot be None.")
        if not db_session_maker:
            raise ValueError("Database session maker cannot be None.")

        self.db_session_maker = db_session_maker
        self.perplexity_client = perplexity_client
        self.config_path = Path(config_path)
        self.logger = logging.getLogger(__name__) # Ensure logger is initialized here

        # Initialize config attributes before loading
        self.sector_config: Dict[str, Any] = {}
        self.geographic_config: Dict[str, Any] = {}
        self.kevin_profile_config: Dict[str, Any] = {}
        self.grant_sources_config: Dict[str, Any] = {}
        # self.user_profile: Dict[str, Any] = {} # If still used, initialize here

        self.load_all_configs()

    def load_all_configs(self):
        """Load all necessary configuration files."""
        try:
            self.sector_config = self._load_config("sector_config.yaml")
            self.geographic_config = self._load_config("geographic_config.yaml")
            self.kevin_profile_config = self._load_config("kevin_profile_config.yaml")
            self.grant_sources_config = self._load_config("grant_sources.yaml")
            # self.user_profile = self._load_config("user_profile.yaml") # if you use a separate user_profile.yaml
            self.logger.info("Successfully loaded all configuration files")
        except Exception as e:
            self.logger.error(f"Error loading configurations: {e}", exc_info=True)
            # Agent proceeds with empty configs; methods should handle this.

    def _load_config(self, filename: str) -> Dict[str, Any]:
        file_path = self.config_path / filename
        if not file_path.is_file():
            raise FileNotFoundError(f"Config file not found: {file_path}")
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)

    async def _get_db_session(self) -> AsyncSession: # Helper to get a session
        return self.db_session_maker()

    async def get_existing_grant_titles(self) -> Set[str]:
        """Return set of existing grant titles to avoid duplicates."""
        async with self.db_session_maker() as session:
            result = await session.execute(select(DBGrant.title))
            return set(result.scalars().all())

    async def store_grants_in_db(self, grants_data: List[Dict[str, Any]]):
        """Store list of grant dicts into the database if not existing."""
        async with self.db_session_maker() as session:
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

    async def search_grants(self, grant_filter: Dict[str, Any] | GrantFilter) -> List[EnrichedGrant]: # Changed return type
        """Execute tiered grant search, enrich, score, and fallback to deep research for comprehensive results."""
        start_time = time.time()
        
        if isinstance(grant_filter, dict):
            try:
                grant_filter = GrantFilter(**grant_filter)
            except Exception as e:
                logger.error(f"Error converting dict to GrantFilter: {e}")
                return [] # Or raise error
            
        try:
            filter_json = json.dumps(grant_filter.model_dump(mode='json'), indent=2)
        except AttributeError:
            filter_json = json.dumps(grant_filter.dict(), indent=2) # Fallback for older Pydantic
            
        logger.info(f"ResearchAgent starting advanced search with filter: {filter_json}")
        
        all_enriched_grants: List[EnrichedGrant] = []
        processed_grant_keys: Set[str] = set() # For deduplication based on URL or title
        tier_stats = {}
        
        # Get existing grant titles/URLs from DB to avoid re-processing fully
        # This is a simplified version; a more robust check would involve checking if an EnrichedGrant
        # for this source_url already exists and is recent.
        # existing_db_titles = await self.get_existing_grant_titles() # Assuming this returns titles or unique IDs

        for tier_name, tier_config in self.GEO_TIERS.items():
            logger.info(f"Executing search Tier: {tier_name} - Focus: {tier_config['focus']}")
            tier_start_time = time.time()
            
            tier_specific_filters = self._create_filters_for_tier(tier_name, tier_config, grant_filter)
            
            # Step 1: Fetch raw search results from Perplexity
            raw_perplexity_response = await self.perplexity_client.search(
                query=self._build_search_query(tier_specific_filters),
                model=self.SONAR_PRIMARY_MODEL, # Use primary model for broad search
                search_domain_filter=tier_specific_filters.sites_to_focus,
                # structured_output=True # PerplexityClient.search handles this if model supports
            )

            content_to_extract_from = ""
            if raw_perplexity_response and raw_perplexity_response.get("choices"):
                first_choice = raw_perplexity_response["choices"][0]
                if first_choice and first_choice.get("message"):
                    content_to_extract_from = first_choice["message"].get("content", "")

            if not content_to_extract_from:
                logger.warning(f"No content found in Perplexity response for tier {tier_name}")
                tier_stats[tier_name] = {"duration": time.time() - tier_start_time, "results_found": 0, "enriched_added": 0}
                continue

            # Step 2: Extract initial grant leads using PerplexityClient's LLM-based extractor
            initial_grant_leads: List[Dict[str, Any]] = await self.perplexity_client.extract_grant_data(content_to_extract_from)
            
            tier_enriched_count = 0
            for lead_data in initial_grant_leads:
                grant_title = lead_data.get("title", "Unknown Title").strip()
                source_url = lead_data.get("source_url")
                
                unique_key = source_url if source_url else grant_title.lower()
                if not unique_key or unique_key in processed_grant_keys:
                    logger.info(f"Skipping duplicate/processed grant lead: '{grant_title}' ({source_url})")
                    continue

                # Step 3: Further enrich with _enrich_grant_with_llm
                logger.info(f"Enriching grant lead: '{grant_title}'")
                enriched_details_dict = await self._enrich_grant_with_llm(lead_data)

                if not enriched_details_dict or not enriched_details_dict.get("title"):
                    logger.warning(f"Skipping grant lead due to missing title after LLM enrichment: {lead_data.get('title')}")
                    continue
                
                # Ensure title from enrichment is used, fallback to lead_data if somehow missing
                final_title = enriched_details_dict.get("title", grant_title).strip()


                # Step 4: Create EnrichedGrant Pydantic model
                try:
                    grant_obj = EnrichedGrant(
                        grant_id_external=enriched_details_dict.get("grant_id_external"),
                        title=final_title,
                        description=enriched_details_dict.get("description"),
                        summary_llm=enriched_details_dict.get("summary_llm"),
                        funder_name=enriched_details_dict.get("funder_name"),
                        funding_amount_min=enriched_details_dict.get("funding_amount_min"),
                        funding_amount_max=enriched_details_dict.get("funding_amount_max"),
                        funding_amount_exact=enriched_details_dict.get("funding_amount_exact"),
                        funding_amount_display=enriched_details_dict.get("funding_amount_display"),
                        deadline_date=enriched_details_dict.get("deadline_date"),
                        application_open_date=enriched_details_dict.get("application_open_date"),
                        eligibility_summary_llm=enriched_details_dict.get("eligibility_summary_llm"),
                        keywords=enriched_details_dict.get("keywords", []),
                        categories_project=enriched_details_dict.get("categories_project", []),
                        source_details=GrantSourceDetails(
                            source_name=enriched_details_dict.get("source_name", lead_data.get("source_name")),
                            source_url=enriched_details_dict.get("source_url", lead_data.get("source_url")),
                            retrieved_at=datetime.utcnow()
                        ),
                        record_status="NEW_UNSCORED",
                        research_scores=ResearchContextScores(), # Initialize
                        # Ensure all required fields for EnrichedGrant are present
                        id=None, # Assuming id is optional or will be set later by DB
                        specific_location_mentions=enriched_details_dict.get("specific_location_mentions", []),
                        enrichment_log=enriched_details_dict.get("enrichment_log", []),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                except Exception as e:
                    logger.error(f"Pydantic validation error for grant '{final_title}': {e}", exc_info=True)
                    continue

                # Step 5: Calculate research scores
                grant_obj.research_scores.sector_relevance = await self._calculate_sector_relevance(grant_obj)
                grant_obj.research_scores.geographic_relevance = await self._calculate_geographic_relevance(grant_obj)
                grant_obj.research_scores.operational_alignment = await self._calculate_operational_alignment(grant_obj)
                grant_obj.updated_at = datetime.utcnow()

                all_enriched_grants.append(grant_obj)
                if unique_key:
                    processed_grant_keys.add(unique_key)
                tier_enriched_count += 1
                logger.info(f"Successfully enriched and scored grant: '{grant_obj.title}'")

            tier_stats[tier_name] = {
                "duration": time.time() - tier_start_time,
                "initial_leads": len(initial_grant_leads),
                "enriched_added": tier_enriched_count
            }
        
        initial_results_count = len(all_enriched_grants)
        logger.info(f"Initial search phase found and enriched {initial_results_count} grants.")
        logger.info(f"Tier stats: {json.dumps(tier_stats, indent=2)}")

        # Deep research fallback if insufficient results
        if initial_results_count < self.MIN_RESULTS_PER_TIER_TARGET: # Use configured target
            logger.info(f"Insufficient results ({initial_results_count} < {self.MIN_RESULTS_PER_TIER_TARGET}), initiating deep research fallback.")
            fallback_start_time = time.time()
            
            # Use a broader filter for deep research, potentially combining keywords or focusing on general terms
            # For simplicity, using the original grant_filter's keywords and categories.
            # The sites_to_focus could be broadened or removed for deep search.
            deep_search_query_text = self._build_search_query(grant_filter) # Build a general query

            raw_fallback_response = await self.perplexity_client.search(
                query=deep_search_query_text,
                model=self.SONAR_DEEP_MODEL, # Use deep research model
                # search_domain_filter=None, # Optionally broaden sites for deep search
            )

            fallback_content_to_extract = ""
            if raw_fallback_response and raw_fallback_response.get("choices"):
                first_choice = raw_fallback_response["choices"][0]
                if first_choice and first_choice.get("message"):
                    fallback_content_to_extract = first_choice["message"].get("content", "")

            fallback_enriched_count = 0
            if fallback_content_to_extract:
                fallback_grant_leads = await self.perplexity_client.extract_grant_data(fallback_content_to_extract)
                
                for lead_data in fallback_grant_leads:
                    grant_title = lead_data.get("title", "Unknown Title").strip()
                    source_url = lead_data.get("source_url")
                    unique_key = source_url if source_url else grant_title.lower()

                    if not unique_key or unique_key in processed_grant_keys:
                        logger.info(f"Skipping duplicate/processed grant from fallback: '{grant_title}'")
                        continue
                    
                    logger.info(f"Enriching grant lead from fallback: '{grant_title}'")
                    enriched_details_dict = await self._enrich_grant_with_llm(lead_data)

                    if not enriched_details_dict or not enriched_details_dict.get("title"):
                        logger.warning(f"Skipping fallback grant lead due to missing title after enrichment: {lead_data.get('title')}")
                        continue
                        
                    final_title = enriched_details_dict.get("title", grant_title).strip()

                    try:
                        grant_obj = EnrichedGrant(
                            grant_id_external=enriched_details_dict.get("grant_id_external"),
                            title=final_title,
                            description=enriched_details_dict.get("description"),
                            summary_llm=enriched_details_dict.get("summary_llm"),
                            funder_name=enriched_details_dict.get("funder_name"),
                            funding_amount_min=enriched_details_dict.get("funding_amount_min"),
                            funding_amount_max=enriched_details_dict.get("funding_amount_max"),
                            funding_amount_exact=enriched_details_dict.get("funding_amount_exact"),
                            funding_amount_display=enriched_details_dict.get("funding_amount_display"),
                            deadline_date=enriched_details_dict.get("deadline_date"),
                            application_open_date=enriched_details_dict.get("application_open_date"),
                            eligibility_summary_llm=enriched_details_dict.get("eligibility_summary_llm"),
                            keywords=enriched_details_dict.get("keywords", []),
                            categories_project=enriched_details_dict.get("categories_project", []),
                            source_details=GrantSourceDetails(
                                source_name=enriched_details_dict.get("source_name", lead_data.get("source_name")),
                                source_url=enriched_details_dict.get("source_url", lead_data.get("source_url")),
                                retrieved_at=datetime.utcnow()
                            ),
                            record_status="NEW_UNSCORED_FALLBACK", # Mark as from fallback
                            research_scores=ResearchContextScores(),
                            # Ensure all required fields for EnrichedGrant are present
                            id=None, # Assuming id is optional or will be set later by DB
                            specific_location_mentions=enriched_details_dict.get("specific_location_mentions", []),
                            enrichment_log=enriched_details_dict.get("enrichment_log", []),
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                    except Exception as e:
                        logger.error(f"Pydantic validation error for fallback grant '{final_title}': {e}", exc_info=True)
                        continue

                    grant_obj.research_scores.sector_relevance = await self._calculate_sector_relevance(grant_obj)
                    grant_obj.research_scores.geographic_relevance = await self._calculate_geographic_relevance(grant_obj)
                    grant_obj.research_scores.operational_alignment = await self._calculate_operational_alignment(grant_obj)
                    grant_obj.updated_at = datetime.utcnow()

                    all_enriched_grants.append(grant_obj)
                    if unique_key:
                        processed_grant_keys.add(unique_key)
                    fallback_enriched_count +=1
                    logger.info(f"Successfully enriched and scored fallback grant: '{grant_obj.title}'")

                tier_stats["deep_research_fallback"] = {
                    "duration": time.time() - fallback_start_time,
                    "initial_leads": len(fallback_grant_leads),
                    "enriched_added": fallback_enriched_count
                }
                logger.info(f"Deep research fallback added {fallback_enriched_count} new grants.")
            else:
                logger.info("No content from deep research fallback to process.")
                tier_stats["deep_research_fallback"] = {
                    "duration": time.time() - fallback_start_time,
                    "initial_leads": 0,
                    "enriched_added": 0
                }
        
        total_duration = time.time() - start_time
        logger.info(f"ResearchAgent finished search. Total grants enriched: {len(all_enriched_grants)}. Total duration: {total_duration:.2f}s")
        logger.info(f"Final Tier stats: {json.dumps(tier_stats, indent=2)}")
        
        return all_enriched_grants

    async def _parse_and_validate(self, raw_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        # This method is now largely superseded by the new flow in search_grants.
        # Kept for now if any part of it is still called, but should be removed if fully unused.
        logger.warning("_parse_and_validate is deprecated and may be removed. Its logic is now in search_grants.")
        # ... (original content of _parse_and_validate, if any part needs to be temporarily kept or reviewed)
        # For now, let's assume it's fully replaced and make it do nothing or return empty.
        return []


    def _create_filters_for_tier(self, tier_name: str, tier_config: Dict[str, Any], base_filter: GrantFilter) -> GrantFilter:
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
        if filters.deadline_before:
            deadline_info_parts.append(f"before {filters.deadline_before.strftime('%Y-%m-%d')}")
        
        if deadline_info_parts:
            query_parts.append(" ".join(deadline_info_parts))
        
        # Geographic focus
        query_parts.append(f"Geographic focus: {filters.geographic_focus}.")
        
        # Sites to focus (if any)
        if filters.sites_to_focus:
            query_parts.append(f"Preferred sources: {', '.join(filters.sites_to_focus)}.")
        
        return " ".join(query_parts)

    async def _enrich_grant_with_llm(self, grant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich grant data using LLM-based analysis and external context.
        
        Steps:
        1. Generate a detailed summary and eligibility analysis using LLM.
        2. Extract and structure relevant data points from the LLM response.
        3. Perform additional enrichment like fetching funder details, if applicable.
        
        Args:
            grant_data: Initial grant data dictionary with at least title and description
            
        Returns:
            Enriched grant data dictionary with additional insights and structured fields
        """
        grant_title = grant_data.get("title", "Untitled Grant")
        grant_description = grant_data.get("description", "")
        
        # Step 1: LLM-based summary and analysis
        llm_prompt = (
            f"Grant Title: {grant_title}\n"
            f"Description: {grant_description}\n\n"
            "Please provide a detailed summary of this grant opportunity, including key eligibility criteria, "
            "funding amount, application deadlines, and any other relevant details. "
            "Structure the response in a machine-readable format with clear labels for each piece of information."
        )
        
        try:
            llm_response = await self.perplexity_client.generate_completion(llm_prompt, max_tokens=300)
            llm_content = llm_response.get("choices")[0].get("message").get("content")
            
            # Step 2: Parse LLM response (assuming it's in a structured format like JSON or key-value pairs)
            enriched_data = self._parse_llm_enrichment(llm_content)
            
            # Step 3: Additional enrichment (e.g., fetch funder details if not present)
            if not enriched_data.get("funder_name") and enriched_data.get("source_url"):
                funder_details = await self._fetch_funder_details(enriched_data["source_url"])
                enriched_data["funder_name"] = funder_details.get("funder_name", enriched_data.get("funder_name"))
            
            return {**grant_data, **enriched_data} # Merge original and enriched data
        except Exception as e:
            logger.error(f"Error enriching grant with LLM for '{grant_title}': {e}", exc_info=True)
            return grant_data # Return original data on error

    def _parse_llm_enrichment(self, llm_content: str) -> Dict[str, Any]:
        """Parse the structured content from LLM enrichment response.
        
        This function will vary based on how the LLM response is structured.
        For now, let's assume it's a simple key-value pair format like:
        Title: Grant Title
        Description: Grant description...
        
        Args:
            llm_content: Raw content string from LLM response
            
        Returns:
            Parsed dictionary with structured grant information
        """
        enriched_data = {}
        
        # Naive parsing logic: split by newlines and then by colon
        for line in llm_content.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                enriched_data[key.strip().lower()] = value.strip()
        
        return enriched_data

    async def _fetch_funder_details(self, source_url: str) -> Dict[str, Any]:
        """Fetch detailed funder information from external sources if not available.
        
        This is a placeholder for any external API calls or database lookups to fetch funder details.
        
        Args:
            source_url: The source URL where the grant was found
            
        Returns:
            Dictionary with funder details like funder_name, contact_info, etc.
        """
        # Example: Extract funder name from URL or perform a lookup
        if "grants.gov" in source_url:
            return {"funder_name": "U.S. Government - Grants.gov"}
        elif "rd.usda.gov" in source_url:
            return {"funder_name": "U.S. Department of Agriculture"}
        # Add more rules or API calls as needed
        
        return {} # Default to empty if no match

    async def _calculate_sector_relevance(self, grant_data: EnrichedGrant) -> float:
        """Calculate sector relevance score based on keywords and LLM assessment."""
        score = 0.0
        matched_keywords = []
        
        # Use direct attribute access for Pydantic models
        grant_text_corpus = f"{grant_data.title or ''} {grant_data.description or ''} {grant_data.summary_llm or ''} {' '.join(grant_data.keywords or [])} {' '.join(grant_data.categories_project or [])}"
        
        # Keyword matching from self.sector_config (or a predefined list if config is empty)
        primary_keywords = self.sector_config.get("primary_keywords", [])
        secondary_keywords = self.sector_config.get("secondary_keywords", [])
        
        for kw in primary_keywords:
            if kw.lower() in grant_text_corpus.lower():
                score += 2.0 # Higher weight for primary
                matched_keywords.append(kw)
        for kw in secondary_keywords:
            if kw.lower() in grant_text_corpus.lower():
                score += 1.0
                matched_keywords.append(kw)

        # LLM-based assessment (simplified example)
        if self.perplexity_client:
            try:
                # Ensure grant_data.summary_llm is not None before using it
                summary_to_assess = grant_data.summary_llm if grant_data.summary_llm else grant_data.description
                if summary_to_assess: # Only proceed if there's text to assess
                    prompt = (
                        f"Assess the sector relevance of the following grant summary for projects related to "
                        f"{', '.join(self.sector_config.get('focus_areas', ['telecommunications', 'nonprofit support']))}. "
                        f"Respond with a relevance score from 0.0 to 10.0. Summary: {summary_to_assess}"
                    )
                    response = await self.perplexity_client.generate_completion(prompt, max_tokens=10) # Using generate_completion
                    # Ensure response is not None and has choices
                    if response and response.get("choices") and response["choices"][0].get("message"):
                        llm_score_text = response["choices"][0]["message"].get("content", "0.0")
                        try:
                            llm_score = float(llm_score_text.strip())
                            score += llm_score  # Add LLM's score (0-10 range)
                        except ValueError:
                            self.logger.warning(f"Could not parse LLM relevance score: {llm_score_text}")
                else:
                    self.logger.info(f"No summary or description available for LLM sector relevance assessment of grant: {grant_data.title}")

            except Exception as e:
                self.logger.error(f"Error during LLM sector relevance assessment for grant {grant_data.title}: {e}")

        self.logger.info(f"Sector relevance for '{grant_data.title}': {score}. Matched keywords: {matched_keywords}")
        return min(max(score, 0.0), 10.0) # Normalize to 0-10

    async def _calculate_geographic_relevance(self, grant_data: EnrichedGrant) -> float:
        """Calculate geographic relevance based on location mentions and LLM assessment."""
        score = 0.0
        
        # Use direct attribute access
        grant_text_corpus = f"{grant_data.title or ''} {grant_data.description or ''} {grant_data.summary_llm or ''} {' '.join(grant_data.specific_location_mentions or [])}"
        
        primary_locations = self.geographic_config.get("primary_locations", []) # e.g., ["Natchitoches Parish", "LA-08"]
        secondary_locations = self.geographic_config.get("secondary_locations", []) # e.g., ["Louisiana"]

        for loc in primary_locations:
            if loc.lower() in grant_text_corpus.lower():
                score += 5.0
        for loc in secondary_locations:
            if loc.lower() in grant_text_corpus.lower():
                score += 2.0
        
        # Add points if specific_location_mentions (from enrichment) match configured locations
        if grant_data.specific_location_mentions:
            for mentioned_loc in grant_data.specific_location_mentions:
                if any(pl.lower() in mentioned_loc.lower() for pl in primary_locations):
                    score += 1.5 # Bonus for explicit mentions matching primary
                elif any(sl.lower() in mentioned_loc.lower() for sl in secondary_locations):
                    score += 0.5 # Bonus for explicit mentions matching secondary
        
        # Simplified LLM check (can be expanded)
        if self.perplexity_client:
            try:
                # Ensure grant_data.summary_llm is not None
                summary_to_assess = grant_data.summary_llm if grant_data.summary_llm else grant_data.description
                if summary_to_assess:
                    prompt = (
                        f"Assess the geographic relevance of the following grant summary for '{self.geographic_config.get('primary_focus_area', 'Natchitoches Parish, LA')}'. "
                        f"Respond with a relevance score from 0.0 to 10.0. Summary: {summary_to_assess}"
                    )
                    response = await self.perplexity_client.generate_completion(prompt, max_tokens=10)
                    if response and response.get("choices") and response["choices"][0].get("message"):
                        llm_score_text = response["choices"][0]["message"].get("content", "0.0")
                        try:
                            llm_score = float(llm_score_text.strip())
                            score += llm_score / 2 # Adjust LLM score influence
                        except ValueError:
                             self.logger.warning(f"Could not parse LLM geographic score: {llm_score_text}")
                else:
                    self.logger.info(f"No summary or description available for LLM geographic relevance assessment of grant: {grant_data.title}")
            except Exception as e:
                self.logger.error(f"Error during LLM geographic relevance assessment for grant {grant_data.title}: {e}")

        self.logger.info(f"Geographic relevance for '{grant_data.title}': {score}")
        return min(max(score, 0.0), 10.0) # Normalize

    async def _calculate_operational_alignment(self, grant_data: EnrichedGrant) -> float:
        """Calculate operational alignment score based on Kevin's profile (user profile)."""
        if not self.kevin_profile_config: # Changed from self.user_profile
            logger.warning("Kevin profile config not loaded, returning default alignment.")
            return 0.1 # Default score

        score = 0.0
        alignment_factors_matched = []
        grant_text_corpus = f"{grant_data.title or ''} {grant_data.description or ''} {grant_data.summary_llm or ''} {grant_data.eligibility_criteria or ''} {grant_data.keywords or []}".lower()

        # Focus Areas
        focus_match_score = 0.0
        # Ensure kevin_profile_config is a dict or an object with attributes
        focus_areas_keywords = []
        if isinstance(self.kevin_profile_config, dict):
            focus_areas_keywords = self.kevin_profile_config.get("focus_areas_keywords", [])
        elif hasattr(self.kevin_profile_config, 'focus_areas_keywords'):
            focus_areas_keywords = self.kevin_profile_config.focus_areas_keywords

        if focus_areas_keywords:
            matched_focus = [kw for kw in focus_areas_keywords if kw.lower() in grant_text_corpus]
            if matched_focus:
                focus_match_score = 0.4 # Base score for any match
                alignment_factors_matched.extend([f"Focus: {mf}" for mf in matched_focus])
        
        # Expertise
        expertise_match_score = 0.0
        expertise_keywords = []
        if isinstance(self.kevin_profile_config, dict):
            expertise_keywords = self.kevin_profile_config.get("expertise_keywords", [])
        elif hasattr(self.kevin_profile_config, 'expertise_keywords'):
            expertise_keywords = self.kevin_profile_config.expertise_keywords

        if expertise_keywords:
            matched_expertise = [kw for kw in expertise_keywords if kw.lower() in grant_text_corpus]
            if matched_expertise:
                expertise_match_score = 0.3 # Base score for any match
                alignment_factors_matched.extend([f"Expertise: {me}" for me in matched_expertise])

        # Strategic Goals
        strategic_match_score = 0.0
        strategic_goals_keywords = []
        if isinstance(self.kevin_profile_config, dict):
            strategic_goals_keywords = self.kevin_profile_config.get("strategic_goals_keywords", [])
        elif hasattr(self.kevin_profile_config, 'strategic_goals_keywords'):
            strategic_goals_keywords = self.kevin_profile_config.strategic_goals_keywords

        if strategic_goals_keywords:
            matched_strategic = [kw for kw in strategic_goals_keywords if kw.lower() in grant_text_corpus]
            if matched_strategic:
                strategic_match_score = 0.3 # Base score for any match
                alignment_factors_matched.extend([f"Strategic: {ms}" for ms in matched_strategic])

        # Project Constraints (Negative Keywords)
        project_constraints = None
        if isinstance(self.kevin_profile_config, dict):
            project_constraints = self.kevin_profile_config.get("project_constraints")
        elif hasattr(self.kevin_profile_config, 'project_constraints'):
            project_constraints = self.kevin_profile_config.project_constraints
        
        negative_keywords = []
        if project_constraints:
            if isinstance(project_constraints, dict):
                 negative_keywords = project_constraints.get("negative_keywords_in_grant", [])
            elif hasattr(project_constraints, 'negative_keywords_in_grant'):
                 negative_keywords = project_constraints.negative_keywords_in_grant

        if negative_keywords:
            for neg_kw in negative_keywords:
                if neg_kw.lower() in grant_text_corpus:
                    logger.info(f"Negative keyword '{neg_kw}' found in grant '{grant_data.title}'. Reducing operational alignment significantly.")
                    grant_data.enrichment_log.append(f"Operational alignment penalized due to negative keyword: {neg_kw}")
                    return 0.0 # Penalize heavily

        # Combine scores (simple sum, capped at 1.0)
        score = min(1.0, focus_match_score + expertise_match_score + strategic_match_score)

        if not alignment_factors_matched:
            default_score = 0.05
            if isinstance(self.kevin_profile_config, dict):
                default_score = self.kevin_profile_config.get("default_alignment_score", 0.05)
            elif hasattr(self.kevin_profile_config, 'default_alignment_score'):
                default_score = self.kevin_profile_config.default_alignment_score
            score = default_score

        grant_data.enrichment_log.append(f"Operational alignment calculated: {score:.2f}. Matched factors: {alignment_factors_matched}")
        return score





    async def _extract_keywords_llm(self, text_content: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text content using LLM. Handles malformed JSON responses."""
        if not text_content:
            return []

        prompt = f"""{{
            "model": "llama-3-sonar-small-32k-online",
            "messages": [
                {{"role": "system", "content": "You are a keyword extraction assistant. Respond in JSON."}},
                {{"role": "user", "content": "Extract up to {max_keywords} relevant keywords from the following text. Keywords should be concise and represent the main topics. Return the keywords as a JSON list of strings. For example: ['keyword1', 'keyword2']. Text: {text_content}"}}
            ]
        }}"""
        try:
            # Assuming perplexity_client.ask or a similar method returns a string that needs parsing
            # If perplexity_client.extract_grant_data or chat.completions.create already parse JSON,
            # this method might need to adapt to how those methods signal errors.
            # For now, assuming a raw string response that should be JSON.
            
            # The original code used self.perplexity_client.chat.completions.create
            # Let's simulate its response structure for the purpose of this method
            response = await self.perplexity_client.chat.completions.create(
                model=self.SONAR_PRIMARY_MODEL, # Or a smaller model suitable for keyword extraction
                messages=[
                    {"role": "system", "content": "You are a keyword extraction assistant. Respond in JSON."},
                    {"role": "user", "content": prompt}
                ],
                # response_format={"type": "json_object"} # If supported by Perplexity API
            )
            
            # Assuming the response structure is similar to OpenAI's
            # response.choices[0].message.content should contain the JSON string
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                json_string = response.choices[0].message.content
                # Attempt to clean the string if it's not perfect JSON (e.g., remove markdown backticks)
                cleaned_json_string = re.sub(r'^```json\\n?|\'\'\'\\n?json\\n?|\'\'\'\\n?|\\n?```$', '', json_string, flags=re.IGNORECASE).strip()

                try:
                    keywords = json.loads(cleaned_json_string)
                    if isinstance(keywords, list) and all(isinstance(k, str) for k in keywords):
                        return keywords[:max_keywords]
                    else:
                        self.logger.warning(f"LLM keyword extraction returned non-list or non-string items: {keywords}")
                        return []
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON from LLM for keyword extraction: {e}. Response: '{cleaned_json_string}'")
                    return [] # Return empty list on JSON parsing error
            else:
                self.logger.warning("LLM response for keyword extraction was empty or malformed.")
                return []
        except Exception as e:
            self.logger.error(f"Error during LLM keyword extraction: {e}", exc_info=True)
            return [] # Return empty list on any other error

    async def _assess_relevance_llm(self, grant_text_corpus: str, assessment_area_description: str) -> float:
        """Assesses relevance of grant text to a specific area using Perplexity API, returns a score 0.0-1.0."""
        if not self.perplexity_client or not grant_text_corpus.strip():
            return 0.0

        llm_prompt = (
            f"Assess the relevance of the following grant information to the area: '{assessment_area_description}'. "
            f"Provide a relevance score as a single floating-point number between 0.0 (not relevant) and 1.0 (highly relevant). "
            f"Return ONLY the number. Grant Information: \n{grant_text_corpus[:2000]}" # Limit input text
        )
        try:
            response = await self.perplexity_client.chat.completions.create(
                model="llama-3-sonar-small-32k-online",
                messages=[
                    {"role": "system", "content": "You are a relevance assessment assistant. Return a single float score between 0.0 and 1.0."},
                    {"role": "user", "content": llm_prompt}
                ],
                max_tokens=10 # Expecting a short numerical response
            )
            # logger.debug(f"Relevance assessment LLM response: {response}")
            if response and response.choices:
                content = response.choices[0].message.content.strip()
                try:
                    score = float(content)
                    return max(0.0, min(1.0, score)) # Clamp score to [0,1]
                except ValueError:
                    logger.warning(f"Could not parse relevance score float from LLM: {content}")
        except Exception as e:
            logger.error(f"Error during LLM relevance assessment: {e}")
        return 0.0 # Default to no relevance on error

    async def _calculate_sector_relevance(self, grant_data: EnrichedGrant) -> float:
        """Calculate sector relevance score based on keywords and LLM assessment."""
        score = 0.0
        matched_keywords = []
        # Use direct attribute access for Pydantic models
        grant_text_corpus = f"{grant_data.title or ''} {grant_data.description or ''} {grant_data.summary_llm or ''} {' '.join(grant_data.keywords or [])} {' '.join(grant_data.categories_project or [])}"
        grant_text_corpus = grant_text_corpus.lower()

        if not self.sector_config:
            logger.warning("Sector config not loaded, returning default sector relevance.")
            return 0.1 # Default score if no config

        # Keyword matching score
        keyword_score = 0.0
        total_weight = 0.0

        for pk in self.sector_config.priority_keywords:
            if pk.keyword.lower() in grant_text_corpus:
                keyword_score += pk.weight * self.sector_config.priority_weight
                matched_keywords.append(pk.keyword)
            total_weight += pk.weight * self.sector_config.priority_weight
        
        for sk in self.sector_config.secondary_keywords:
            if sk.keyword.lower() in grant_text_corpus:
                keyword_score += sk.weight * (1 - self.sector_config.priority_weight)
                matched_keywords.append(sk.keyword)
            total_weight += sk.weight * (1 - self.sector_config.priority_weight)

        if total_weight > 0:
            normalized_keyword_score = keyword_score / total_weight
        else:
            normalized_keyword_score = 0.0

        for ek in self.sector_config.exclusion_keywords:
            if ek.lower() in grant_text_corpus:
                logger.info(f"Exclusion keyword '{ek}' found in grant '{grant_data.title}'. Reducing sector score significantly.")
                return 0.0  # Penalize heavily if exclusion keyword is found
        
        # LLM-based assessment (optional, could be a setting)
        # For simplicity, we'll average with keyword score if used, or rely on keywords.
        # This part can be expanded significantly.
        # llm_relevance_score = await self._assess_relevance_llm(grant_text_corpus, "relevant sectors based on user profile and sector configuration")
        # score = (normalized_keyword_score + llm_relevance_score) / 2
        score = normalized_keyword_score # Using only keyword score for now

        if not matched_keywords:
            score = self.sector_config.default_relevance_score # Apply default if no keywords matched
        
        grant_data.enrichment_log.append(f"Sector relevance calculated: {score:.2f}. Matched: {matched_keywords}")
        return score

    async def _calculate_geographic_relevance(self, grant_data: EnrichedGrant) -> float:
        """Calculate geographic relevance score."""
        score = 0.0
        matched_geo_terms = []
        grant_text_corpus = f"{grant_data.title or ''} {grant_data.description or ''} {grant_data.summary_llm or ''} {grant_data.geographic_scope or ''} {' '.join(grant_data.specific_location_mentions or [])}".lower()

        if not self.geographic_config:
            logger.warning("Geographic config not loaded, returning default geo relevance.")
            return 0.1 # Default score

        # Keyword matching for geographic terms
        geo_keyword_score = 0.0
        total_geo_weight = 0.0

        for pk in self.geographic_config.priority_keywords:
            if pk.keyword.lower() in grant_text_corpus:
                geo_keyword_score += pk.weight * self.geographic_config.priority_weight
                matched_geo_terms.append(pk.keyword)
            total_geo_weight += pk.weight * self.geographic_config.priority_weight

        for sk in self.geographic_config.secondary_keywords:
            if sk.keyword.lower() in grant_text_corpus:
                geo_keyword_score += sk.weight * (1 - self.geographic_config.priority_weight)
                matched_geo_terms.append(sk.keyword)
            total_geo_weight += sk.weight * (1 - self.geographic_config.priority_weight)
        
        if total_geo_weight > 0:
            normalized_geo_keyword_score = geo_keyword_score / total_geo_weight
        else:
            normalized_geo_keyword_score = 0.0

        # Boost for national scope if applicable
        if self.geographic_config.national_scope_boost and (grant_data.geographic_scope or "").lower() == "national":
            normalized_geo_keyword_score = min(1.0, normalized_geo_keyword_score + self.geographic_config.national_scope_boost)
            matched_geo_terms.append("National Scope Boost")

        score = normalized_geo_keyword_score
        if not matched_geo_terms:
            score = self.geographic_config.default_relevance_score

        grant_data.enrichment_log.append(f"Geographic relevance calculated: {score:.2f}. Matched: {matched_geo_terms}")
        return score

    async def _calculate_operational_alignment(self, grant_data: EnrichedGrant) -> float:
        """Calculate operational alignment score based on Kevin's profile (user profile)."""
        if not self.kevin_profile_config: # Changed from self.user_profile
            logger.warning("Kevin profile config not loaded, returning default alignment.")
            return 0.1 # Default score

        score = 0.0
        alignment_factors_matched = []
        grant_text_corpus = f"{grant_data.title or ''} {grant_data.description or ''} {grant_data.summary_llm or ''} {grant_data.eligibility_criteria or ''} {grant_data.keywords or []}".lower()

        # Focus Areas
        focus_match_score = 0.0
        # Ensure kevin_profile_config is a dict or an object with attributes
        focus_areas_keywords = []
        if isinstance(self.kevin_profile_config, dict):
            focus_areas_keywords = self.kevin_profile_config.get("focus_areas_keywords", [])
        elif hasattr(self.kevin_profile_config, 'focus_areas_keywords'):
            focus_areas_keywords = self.kevin_profile_config.focus_areas_keywords

        if focus_areas_keywords:
            matched_focus = [kw for kw in focus_areas_keywords if kw.lower() in grant_text_corpus]
            if matched_focus:
                focus_match_score = 0.4 # Base score for any match
                alignment_factors_matched.extend([f"Focus: {mf}" for mf in matched_focus])
        
        # Expertise
        expertise_match_score = 0.0
        expertise_keywords = []
        if isinstance(self.kevin_profile_config, dict):
            expertise_keywords = self.kevin_profile_config.get("expertise_keywords", [])
        elif hasattr(self.kevin_profile_config, 'expertise_keywords'):
            expertise_keywords = self.kevin_profile_config.expertise_keywords

        if expertise_keywords:
            matched_expertise = [kw for kw in expertise_keywords if kw.lower() in grant_text_corpus]
            if matched_expertise:
                expertise_match_score = 0.3 # Base score for any match
                alignment_factors_matched.extend([f"Expertise: {me}" for me in matched_expertise])

        # Strategic Goals
        strategic_match_score = 0.0
        strategic_goals_keywords = []
        if isinstance(self.kevin_profile_config, dict):
            strategic_goals_keywords = self.kevin_profile_config.get("strategic_goals_keywords", [])
        elif hasattr(self.kevin_profile_config, 'strategic_goals_keywords'):
            strategic_goals_keywords = self.kevin_profile_config.strategic_goals_keywords

        if strategic_goals_keywords:
            matched_strategic = [kw for kw in strategic_goals_keywords if kw.lower() in grant_text_corpus]
            if matched_strategic:
                strategic_match_score = 0.3 # Base score for any match
                alignment_factors_matched.extend([f"Strategic: {ms}" for ms in matched_strategic])

        # Project Constraints (Negative Keywords)
        project_constraints = None
        if isinstance(self.kevin_profile_config, dict):
            project_constraints = self.kevin_profile_config.get("project_constraints")
        elif hasattr(self.kevin_profile_config, 'project_constraints'):
            project_constraints = self.kevin_profile_config.project_constraints
        
        negative_keywords = []
        if project_constraints:
            if isinstance(project_constraints, dict):
                 negative_keywords = project_constraints.get("negative_keywords_in_grant", [])
            elif hasattr(project_constraints, 'negative_keywords_in_grant'):
                 negative_keywords = project_constraints.negative_keywords_in_grant

        if negative_keywords:
            for neg_kw in negative_keywords:
                if neg_kw.lower() in grant_text_corpus:
                    logger.info(f"Negative keyword '{neg_kw}' found in grant '{grant_data.title}'. Reducing operational alignment significantly.")
                    grant_data.enrichment_log.append(f"Operational alignment penalized due to negative keyword: {neg_kw}")
                    return 0.0 # Penalize heavily        # Combine scores (simple sum, capped at 1.0)
        score = min(1.0, focus_match_score + expertise_match_score + strategic_match_score)

        if not alignment_factors_matched:
            default_score = 0.05
            if isinstance(self.kevin_profile_config, dict):
                default_score = self.kevin_profile_config.get("default_alignment_score", 0.05)
            elif hasattr(self.kevin_profile_config, 'default_alignment_score'):
                default_score = self.kevin_profile_config.default_alignment_score
            score = default_score

        grant_data.enrichment_log.append(f"Operational alignment calculated: {score:.2f}. Matched factors: {alignment_factors_matched}")
        return score

    async def get_grant_by_id_from_db(self, grant_id: int) -> Optional[EnrichedGrant]:
        """Fetches a single grant by its ID from the database."""
        from app.crud import get_grant_by_id as crud_get_grant_by_id
        try:
            async with self.db_session_maker() as session:
                try:
                    enriched_grant = await crud_get_grant_by_id(session, grant_id)
                    return enriched_grant or None
                except Exception as db_err:
                    logger.error(f"Error fetching grant by ID {grant_id}: {db_err}", exc_info=True)
                    return None
        except Exception as cm_err:
            logger.error(f"Error using db_session_maker for fetching grant {grant_id}: {cm_err}", exc_info=True)
            return None

    async def save_grant_to_db(self, grant: EnrichedGrant) -> Optional[EnrichedGrant]:
        """Saves (creates or updates) an enriched grant to the database."""
        from app.crud import create_or_update_grant as crud_create_or_update_grant
        async with self.db_session_maker() as session:
            try:
                # Use crud_create_or_update_grant, handling both coroutine and direct returns
                result = crud_create_or_update_grant(session, grant)
                saved_grant = await result if asyncio.iscoroutine(result) else result
                # The commit is handled within crud_create_or_update_grant or should be called after it if not.
                # For now, assuming crud_create_or_update_grant handles its own commit or the session is managed by a context that commits.
                # If explicit commit is needed here after the call, it would be: await session.commit()
                if saved_grant:
                    logger.info(f"Grant '{saved_grant.title}' (ID: {saved_grant.id}) processed by CRUD operation.")
                    return saved_grant
                else:
                    logger.error(f"Failed to save grant '{grant.title}' via CRUD, operation returned None.")
                    return None
            except ValidationError as ve:
                logger.error(f"Validation error while preparing grant for DB via CRUD: {ve}")
                # Rollback might be handled by the session context manager or crud_create_or_update_grant
                # await session.rollback() # If explicit rollback needed here
                return None
            except Exception as e:
                logger.error(f"Database error saving grant '{grant.title}' via CRUD: {e}")
                # await session.rollback() # If explicit rollback needed here
                return None

    def update_configs(self, sector_config_data: Optional[Dict] = None, 
                         geographic_config_data: Optional[Dict] = None, 
                         kevin_profile_data: Optional[Dict] = None,
                         grant_sources_data: Optional[List[Dict]] = None):
        """Updates agent configurations dynamically."""
        if sector_config_data:
            try:
                self.sector_config = SectorConfig(**sector_config_data)
                logger.info("Sector config updated.")
            except ValidationError as e:
                logger.error(f"Error updating sector config: {e}")
        if geographic_config_data:
            try:
                self.geographic_config = GeographicConfig(**geographic_config_data)
                logger.info("Geographic config updated.")
            except ValidationError as e:
                logger.error(f"Error updating geographic config: {e}")
        if kevin_profile_data:
            try:
                self.kevin_profile_config = KevinProfileConfig(**kevin_profile_data)
                # Potentially reload user_profile if it depends on kevin_profile_config and a user_id is active
                logger.info("Kevin profile config updated.")
            except ValidationError as e:
                logger.error(f"Error updating Kevin profile config: {e}")
        if grant_sources_data:
            try:
                self.grant_sources_config = [GrantSource(**src) for src in grant_sources_data]
                logger.info("Grant sources config updated.")
            except ValidationError as e:
                logger.error(f"Error updating grant sources config: {e}")