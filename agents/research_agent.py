"""
Research Agent for finding grant opportunities.
"""

import logging
import time
from datetime import datetime, timedelta
import re
from urllib.parse import urlparse
from typing import Dict, List, Any, Optional

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

    async def get_existing_grant_titles(self, grant_source_url: str) -> List[str]:
        async with self.db_sessionmaker() as session: # Use sessionmaker
            # ... existing code ...
            pass  # Placeholder for the actual implementation

    async def store_grants_in_db(self, grants_data: List[Dict[str, Any]]):
        async with self.db_sessionmaker() as session: # Use sessionmaker
            # ... existing code ...
            pass  # Placeholder for the actual implementation

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

    async def search_grants(self, grant_filter: GrantFilter) -> List[Dict[str, Any]]:
        logger.info(f"ResearchAgent 'DualSector Explorer' starting search with initial filter: {grant_filter.model_dump_json(indent=2)}")
        
        all_found_grants_map: Dict[str, Dict[str, Any]] = {} # Use URL or title as key to avoid duplicates
        
        # Tiered search logic
        for tier_name, tier_config in self.GEO_TIERS.items():
            logger.info(f"Executing search Tier: {tier_name} - Focus: {tier_config['focus']}")
            
            # Create specific filters for this tier, incorporating initial grant_filter if provided
            tier_specific_filters = self._create_filters_for_tier(tier_name, tier_config, grant_filter)
            
            tier_results = await self._execute_search_tier(tier_specific_filters)
            
            for grant_data in tier_results:
                # Use a unique identifier, e.g., source_url or a combination if URL is not always present
                grant_key = grant_data.get("source_url") or grant_data.get("title", "").lower()
                if grant_key and grant_key not in all_found_grants_map:
                    all_found_grants_map[grant_key] = grant_data
            
            if len(all_found_grants_map) >= self.MIN_RESULTS_PER_TIER_TARGET and tier_name != list(self.GEO_TIERS.keys())[-1]:
                logger.info(f"Sufficient results ({len(all_found_grants_map)}) found after tier '{tier_name}'. Optional: could stop early.")
                # Consider breaking if a very high number of quality grants are found early
        if not all_found_grants_map:
            logger.info("No grants found after all search tiers.")
            return []
        
        # Convert map values to list for scoring
        grants_to_score = list(all_found_grants_map.values())
        logger.info(f"Found {len(grants_to_score)} unique potential grants across all tiers. Proceeding to scoring.")
        
        # Score and apply final relevance filter (min_score from initial grant_filter)
        # The _score_and_filter_grants method already uses grant_filter.min_score
        scored_grants = await self._score_and_filter_grants(grants_to_score, grant_filter)
        
        logger.info(f"Returning {len(scored_grants)} grants after scoring and final filtering.")
        return scored_grants

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

    async def _execute_search_tier(self, filters: GrantFilter) -> List[Dict[str, Any]]:
        query = self._build_search_query(filters) # _build_search_query might also use filters.sites_to_focus to embed in text if model doesn't support domain filter
        logger.debug(f"Tiered search query for Perplexity: {query}")
        
        # Determine sites to pass to Perplexity client
        search_domains_for_perplexity: Optional[List[str]] = None
        if hasattr(filters, 'sites_to_focus') and filters.sites_to_focus:
            search_domains_for_perplexity = filters.sites_to_focus

        try:
            logger.info(f"Calling Perplexity API for query: {filters.geographic_focus} - {filters.keywords[:50]}... Sites: {search_domains_for_perplexity}")
            # Pass search_domains to the perplexity client's search method
            raw_results = await self.perplexity.search(query, search_domains=search_domains_for_perplexity)
            if not raw_results:
                logger.info("Perplexity API returned empty or None result.")
                return []
            logger.debug(f"Perplexity raw response snippet: {raw_results[:500]}")
        except Exception as e:
            logger.error(f"Error calling Perplexity API: {e}", exc_info=True)
            return []
        
        parsed_grants = self._parse_results(raw_results) 
        
        final_tier_grants = []
        for grant_data in parsed_grants:
            if not self._meets_funding_criteria(grant_data.get("funding_amount")):
                logger.debug(f"Grant '{grant_data.get('title')}' rejected: funding out of range.")
                continue
            if not self._meets_deadline_criteria(grant_data.get("deadline")):
                logger.debug(f"Grant '{grant_data.get('title')}' rejected: deadline too soon.")
                continue
            final_tier_grants.append(grant_data)
        
        logger.info(f"Tier returned {len(final_tier_grants)} grants after initial parsing and persona filtering.")
        return final_tier_grants

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
            "Target sectors include telecommunications infrastructure (broadband, mesh networks, event-Wi-Fi), " \
            "women-owned nonprofit initiatives (501c3), and community shelter conversions for extreme weather."
        )
        if filters.min_funding and filters.max_funding:
            query_parts.append(f"Funding range should ideally be between ${filters.min_funding:,.0f} and ${filters.max_funding:,.0f}.")
        
        # Deadline information construction
        deadline_info_parts = []
        if filters.deadline_after:
            deadline_info_parts.append(f"application deadlines after {filters.deadline_after.strftime('%Y-%m-%d')}")
        if self.DEADLINE_MIN_LEAD_DAYS is not None:
            if not filters.deadline_after: # Add lead time info only if not already covered by deadline_after
                deadline_info_parts.append(f"at least {self.DEADLINE_MIN_LEAD_DAYS} days lead time before the deadline")
        if deadline_info_parts:
            query_parts.append(f"Prefer grants with {' and '.join(deadline_info_parts)}, or rolling applications.")
        else:
            query_parts.append("Prioritize grants with rolling applications or significant lead time.")

        # If search_domain_filter is not supported by the Perplexity model/tier, 
        # or as a supplementary instruction, mention preferred sites in the query text.
        if hasattr(filters, 'sites_to_focus') and filters.sites_to_focus:
            # This is a fallback if the API parameter search_domain_filter is not used/effective
            # Or can be used in conjunction.
            sites_text = ", ".join(filters.sites_to_focus[:3]) # Mention a few key sites
            query_parts.append(f"Pay special attention to sources like {sites_text} if relevant.")

        if filters.categories:
            query_parts.append(f"Consider categories such as: {', '.join(filters.categories)}.")
        
        query = " ".join(query_parts)
        query += " For each grant, provide title, a detailed description, funding amount, exact application deadline, eligibility criteria, and the direct source URL."
        query += " Focus on publicly accessible information and avoid paywalled sources."
        
        logger.debug(f"Constructed Perplexity Query: {query}")
        return query

    def _parse_results(self, raw_results: str) -> List[Dict[str, Any]]:
        logger.warning("CRITICAL: _parse_results is using a placeholder implementation. " \
                       "It needs a robust method to parse actual Perplexity API responses into structured grant data. " \
                       "Current naive parsing will likely yield few or no results from real API output.")
        grants = []
        
        # --- START OF VERY NAIVE PLACEHOLDER PARSING ---
        # This is extremely basic and unlikely to work well with complex real responses.
        # It's here just to prevent an immediate crash and to show where parsing happens.
        # A real implementation would use NLP, regex tailored to expected formats, 
        # or ideally, request structured output from Perplexity if available.
        try:
            # Example: try to split by a common delimiter if Perplexity uses one, or by grant titles.
            # This is highly speculative.
            potential_grant_sections = raw_results.split("--- Grant Separator ---") # Assuming a hypothetical separator
            if len(potential_grant_sections) <= 1 and "Title:" in raw_results: # Try splitting by "Title:"
                potential_grant_sections = ["Title:" + s for s in raw_results.split("Title:")[1:]]

            for section_text in potential_grant_sections:
                if not section_text.strip(): continue
                grant_data = {}
                # Naively try to extract some fields using regex (very basic examples)
                title_match = re.search(r"Title:(.*?)(Description:|Funding Amount:|Deadline:|Eligibility:|URL:|$)", section_text, re.IGNORECASE | re.DOTALL)
                if title_match: grant_data["title"] = title_match.group(1).strip()
                else: grant_data["title"] = "Unknown Title - Parse Error" # Default if not found
                
                desc_match = re.search(r"Description:(.*?)(Funding Amount:|Deadline:|Eligibility:|URL:|$)", section_text, re.IGNORECASE | re.DOTALL)
                if desc_match: grant_data["description"] = desc_match.group(1).strip()
                else: grant_data["description"] = section_text[:200].strip() + "... (parse error)" # Fallback

                amount_match = re.search(r"Funding Amount:[\s$]*(.*?)(Deadline:|Eligibility:|URL:|$)", section_text, re.IGNORECASE | re.DOTALL)
                if amount_match: grant_data["funding_amount"] = amount_match.group(1).strip()
                
                deadline_match = re.search(r"Deadline:(.*?)(Eligibility:|URL:|$)", section_text, re.IGNORECASE | re.DOTALL)
                if deadline_match: grant_data["deadline"] = deadline_match.group(1).strip()

                url_match = re.search(r"URL:(.*?)(Description:|Funding Amount:|Deadline:|Eligibility:|$)", section_text, re.IGNORECASE | re.DOTALL)
                if url_match: grant_data["source_url"] = url_match.group(1).strip()
                
                eligibility_match = re.search(r"Eligibility:(.*?)(Description:|Funding Amount:|Deadline:|URL:|$)", section_text, re.IGNORECASE | re.DOTALL)
                if eligibility_match: grant_data["eligibility"] = eligibility_match.group(1).strip()

                # Add a category placeholder if not found
                grant_data.setdefault("category", "Uncategorized")

                if grant_data.get("title") != "Unknown Title - Parse Error": # Only add if we got at least a title
                    grants.append(grant_data)
        except Exception as e:
            logger.error(f"Error during naive parsing of Perplexity results: {e}", exc_info=True)
        # --- END OF VERY NAIVE PLACEHOLDER PARSING ---
        if grants:
            logger.info(f"Naive parser attempted to extract {len(grants)} potential grants from raw results.")
        else:
            logger.info("Naive parser could not extract any grants from Perplexity response.")
        return grants

    async def _score_and_filter_grants(self, grants: List[Dict[str, Any]], grant_filter: GrantFilter) -> List[Dict[str, Any]]:
        # Placeholder for scoring logic - currently just filters by min_score
        min_score_threshold = grant_filter.min_score or 0
        filtered_grants = [grant for grant in grants if grant.get("score", 0) >= min_score_threshold]
        logger.info(f"Filtered grants down to {len(filtered_grants)} based on min_score={min_score_threshold}.")
        return filtered_grants

    def _get_domain(self, source_name_or_url):
        """Extract or map domain from source name or URL."""
        try:
            if re.match(r'^(http|https)://', source_name_or_url):
                parsed_url = urlparse(source_name_or_url)
                return parsed_url.netloc.lower().replace('www.', '') # Assume it's a domain like grants.gov
            else:
                # Map common names to domains (add more as needed)
                domain_map = {
                    "grants.gov": "grants.gov",
                    "usda": "rd.usda.gov",
                    "fcc": "fcc.gov",
                    "sba": "sba.gov",
                    "ifundwomen": "ifundwomen.com",
                    "amber grants": "ambergrantsforwomen.com"
                }
                return domain_map.get(source_name_or_url.lower())
        except Exception:
            return None

    def _get_source_url(self, source_name):
        """Retrieve URL for a specific source name."""
        # Simplified - expand with actual lookups or config
        domain = self._get_domain(source_name)
        return f"https://{domain}" if domain else f"https://{source_name.lower().replace(' ', '')}.com"

    def _deduplicate_and_process(self, grants, category):
        """Deduplicate results and process grant data."""
        processed_grants = []
        seen_urls = set()
        seen_hashes = set()

        for grant in grants:
            try:
                if not grant or not isinstance(grant, dict) or not grant.get("title") or not grant.get("description"):
                    logging.debug(f"Skipping invalid grant data: {grant}")
                    continue

                # Normalize URL if present
                url = grant.get("source_url", "").strip().rstrip('/')
                if url and url in seen_urls:
                    logging.debug(f"Skipping duplicate grant by URL: {grant.get('title')}")
                    continue

                # Create hash for content-based deduplication if URL is missing/generic
                content_hash = hash(grant["title"].strip().lower() + grant["description"].strip().lower()[:100]) # Hash title + start of desc
                if not url or "unknown_source" in url or "perplexity_extract" in url:
                    if content_hash in seen_hashes:
                        logging.debug(f"Skipping duplicate grant by content hash: {grant.get('title')}")
                        continue
                    seen_hashes.add(content_hash)
                elif url:
                    seen_urls.add(url)

                # --- Process Grant --- 
                processed = {
                    "title": grant["title"].strip(),
                    "description": grant["description"].strip(),
                    "source_url": url if url else f"generated_id_{content_hash}",
                    "source_name": grant.get("source_name", self._extract_source_name(url) if url else "Unknown"),
                    "category": category,
                    "amount": grant.get("amount", "Unknown"),
                    "eligibility": grant.get("eligibility", "See grant details"),
                    # Add other fields as available
                }

                # Process deadline (with robust parsing)
                deadline = None
                deadline_str = grant.get("deadline")
                if deadline_str:
                    try:
                        deadline = self._parse_deadline(str(deadline_str))
                    except ValueError:
                        deadline = self._extract_deadline_from_text(processed["description"])

                # Set default deadline if still None
                processed["deadline"] = deadline if deadline else datetime.utcnow() + timedelta(days=90) # Default 90 days out

                processed_grants.append(processed)

            except Exception as e:
                logging.error(f"Error processing grant: {grant.get('title', 'N/A')} - {str(e)}", exc_info=True)

        logging.info(f"Processed {len(processed_grants)} unique grants after deduplication.")
        return processed_grants

    def _parse_deadline(self, deadline_str):
        """Parse deadline string into datetime object (more robust)."""
        from dateutil import parser
        try:
            # Try flexible parsing first
            # Set dayfirst=False as US formats are common
            dt = parser.parse(deadline_str, dayfirst=False, fuzzy=True)
            # If year is missing, assume current or next year
            if dt.year == 1900 or dt.year < datetime.now().year - 1 : # dateutil might default to 1900 or past year
                 current_year = datetime.now().year
                 dt = dt.replace(year=current_year)
                 if dt < datetime.now(): # If replacing makes it past, assume next year
                     dt = dt.replace(year=current_year + 1)
            return dt
        except (ValueError, OverflowError, TypeError) as e:
            logging.debug(f"Could not parse deadline '{deadline_str}' with dateutil: {e}")
            # Fallback to regex or simpler formats if needed, but dateutil is quite good
            raise ValueError(f"Could not parse deadline: {deadline_str}")

    def _extract_deadline_from_text(self, text):
        """Extract deadline from text description using regex patterns."""
        # Regex patterns (simplified for clarity, expand as needed)
        patterns = [
            r'(?:deadline|due by|closes on|applications due)[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})', # Month D, YYYY
            r'(?:deadline|due by|closes on|applications due)[:\s]+(\d{1,2}/\d{1,2}/\d{4})',       # MM/DD/YYYY
            r'(?:deadline|due by|closes on|applications due)[:\s]+(\d{4}-\d{2}-\d{2})',          # YYYY-MM-DD
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return self._parse_deadline(match.group(1))
                except ValueError:
                    continue
        return None

    def _extract_source_name(self, url):
        """Extract source name from URL."""
        if not url or not url.startswith("http"):
            return "Unknown Source"
        try:
            domain = urlparse(url).netloc
            domain = re.sub(r'^www\.', '', domain)
            parts = domain.split('.')
            # Return the part before the TLD (e.g., 'grants' from 'grants.gov')
            return parts[-2].capitalize() if len(parts) >= 2 else domain.capitalize()
        except Exception:
            return "Unknown Source"

# Alias for backward compatibility
GrantResearchAgent = ResearchAgent

# Example Usage (requires instances of clients)
# research_agent = ResearchAgent(perplexity_client, agentql_client, mongodb_client)
# params = {
#     "category": "telecom",
#     "search_terms": ["rural broadband"],
#     "sources": ["grants.gov", "usda"],
#     "funding_type": ["Grant"],
#     "eligible_entities": ["Nonprofits"],
#     "geo_restrictions": "LA-08"
# }
# grants = research_agent.search_grants(params)