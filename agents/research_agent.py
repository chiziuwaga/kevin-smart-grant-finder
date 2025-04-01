import logging
import time
from datetime import datetime, timedelta
import re
from urllib.parse import urlparse # For extracting source name

# Import clients and scraper
from utils.agentql_client import AgentQLClient
from utils.perplexity_client import PerplexityClient, PerplexityError, PerplexityQuotaExceededError, PerplexityConnectionError
from scrapers.sources.louisiana_scraper import LouisianaGrantScraper
from database.mongodb_client import MongoDBClient

logger = logging.getLogger(__name__)

class ResearchAgent:
    def __init__(self, agentql_client: AgentQLClient, perplexity_client: PerplexityClient, mongodb_client: MongoDBClient):
        """Initialize Research Agent with necessary clients."""
        self.agentql_client = agentql_client
        self.perplexity_client = perplexity_client
        self.mongodb_client = mongodb_client
        self.louisiana_scraper = LouisianaGrantScraper()

        # Store AgentQL agent IDs (can be initialized later)
        self.agentql_agents = {}
        logger.info("Research Agent initialized")

    def _get_or_create_agentql_agent(self, category):
        """Get existing AgentQL agent ID or create a new one."""
        if category in self.agentql_agents and self.agentql_agents[category]:
            return self.agentql_agents[category]

        if not self.agentql_client or not self.agentql_client.is_available():
             logger.warning("AgentQL client not available, cannot create/get AgentQL agent.")
             return None

        # Define agent configurations based on category
        agent_configs = {
            "telecom": {
                "name": "SmartGrantFinder-TelecomV2", # Use versioning in name
                "description": "Searches for telecommunications, broadband, and related infrastructure grant opportunities.",
                "sources": [
                    "grants.gov",
                    "rd.usda.gov",
                    "fcc.gov",
                    "ntia.gov",
                    "broadbandusa.ntia.doc.gov",
                    "broadbandnow.com",
                    "ruralhealthinfo.org"
                    # Add specific state broadband office domains if known
                ]
            },
            "nonprofit": {
                "name": "SmartGrantFinder-NonprofitV2",
                "description": "Searches for grants targeted at nonprofits, especially women-owned or focused on community services.",
                "sources": [
                    "grants.gov",
                    "sba.gov",
                    "ifundwomen.com",
                    "ambergrantsforwomen.com",
                    "cartier.com/en/cartier-womens-initiative", # Updated path
                    "terravivagrants.org",
                    "techsoup.org",
                    "candideu.foundationcenter.org" # Foundation Directory Online (Candide)
                ]
            },
             "combined": {
                 "name": "SmartGrantFinder-CombinedV2",
                 "description": "Broad search across telecom and nonprofit grant sources.",
                 "sources": list(set( # Combine and deduplicate sources
                     agent_configs["telecom"]["sources"] + 
                     agent_configs["nonprofit"]["sources"]
                 ))
             }
        }

        config = agent_configs.get(category)
        if not config:
            logger.error(f"No AgentQL configuration found for category: {category}")
            return None

        agent_id = self.agentql_client.create_search_agent(**config)
        if agent_id:
            self.agentql_agents[category] = agent_id
            logger.info(f"Initialized AgentQL agent for category '{category}' with ID: {agent_id}")
            return agent_id
        else:
             logger.error(f"Failed to create or retrieve AgentQL agent for category: {category}")
             return None

    def search_grants(self, search_params):
        """Search for grants using AgentQL, Perplexity, and specific scrapers."""
        start_time = time.time()
        category = search_params.get("category", "combined") # Default to combined
        search_terms = search_params.get("search_terms", [])
        sources_from_params = search_params.get("sources", []) # Sources selected in UI
        geo_focus = search_params.get("geo_restrictions", "LA-08") # Default geo focus

        logger.info(f"Starting grant search for category '{category}'. Terms: {search_terms}")

        all_results = []
        perplexity_failed = False

        # --- 1. Perplexity Search (Broad reach, good for discovery) --- 
        if self.perplexity_client and self.perplexity_client.is_available():
            logger.info("Starting Perplexity deep search...")
            perplexity_query = " AND ".join([f'"{term}"' for term in search_terms])
            if category == "telecom":
                 perplexity_query += " telecommunications grant OR broadband funding"
            elif category == "nonprofit":
                 perplexity_query += " nonprofit grant OR women-owned business funding"

            # Define site restrictions (can be refined)
            site_restrictions = ["gov", "org"] # Broad search initially

            try:
                perplexity_response = self.perplexity_client.deep_search(
                    query=perplexity_query,
                    site_restrictions=site_restrictions # Use broad restrictions for discovery
                )
                if perplexity_response and "error" not in perplexity_response:
                    extracted_grants = self.perplexity_client.extract_grant_data(perplexity_response)
                    logger.info(f"Perplexity search yielded {len(extracted_grants)} potential grants.")
                    all_results.extend(extracted_grants)
                else:
                     logger.warning(f"Perplexity search returned an error or no results: {perplexity_response.get('error')}")
                     perplexity_failed = True # Mark failure for potential fallback

            except (PerplexityQuotaExceededError, PerplexityConnectionError, PerplexityRateLimitError) as e:
                 logger.error(f"Perplexity search failed due to API limits or connection issue: {e}. Skipping Perplexity.")
                 perplexity_failed = True
            except Exception as e:
                 logger.error(f"Unexpected error during Perplexity search: {e}", exc_info=True)
                 perplexity_failed = True
        else:
            logger.warning("Perplexity client not available. Skipping Perplexity search.")
            perplexity_failed = True # Treat as failure if unavailable

        # --- 2. AgentQL Search (Targeted sources) --- 
        if self.agentql_client and self.agentql_client.is_available():
            logger.info("Starting AgentQL targeted search...")
            agent_id = self._get_or_create_agentql_agent(category)
            if agent_id:
                agentql_query = " OR ".join([f'"{term}"' for term in search_terms])
                # Add parameters if AgentQL supports them (e.g., region, funding type)
                agentql_params = {"max_results": 30} # Example parameter
                agent_results = self.agentql_client.search_grants(
                    agent_id=agent_id,
                    query=agentql_query,
                    parameters=agentql_params
                )
                logger.info(f"AgentQL search yielded {len(agent_results)} potential grants.")
                all_results.extend(agent_results)
            else:
                 logger.warning("Could not get AgentQL agent ID. Skipping AgentQL search.")
        else:
            logger.warning("AgentQL client not available. Skipping AgentQL search.")

        # --- 3. Louisiana State Scraper --- 
        logger.info("Starting Louisiana state portal scraping...")
        try:
            la_grants = self.louisiana_scraper.scrape_all_portals()
            logger.info(f"Louisiana scraper yielded {len(la_grants)} potential grants.")
            # Filter LA grants based on keywords and geo-focus if needed
            # filtered_la_grants = self._filter_scraped_grants(la_grants, search_terms, geo_focus)
            # logger.info(f"Filtered Louisiana grants: {len(filtered_la_grants)}")
            # all_results.extend(filtered_la_grants)
            all_results.extend(la_grants) # Add all for now, filtering happens later
        except Exception as e:
            logger.error(f"Error during Louisiana scraping: {e}", exc_info=True)

        # --- 4. Deduplicate and Process Results --- 
        processed_grants = self._process_and_deduplicate(all_results, category)

        # --- 5. Store Search History --- 
        search_duration = time.time() - start_time
        try:
             self.mongodb_client.store_search_history(search_params, len(processed_grants), search_duration)
        except Exception as e:
             logger.error(f"Failed to store search history: {e}", exc_info=True)

        logger.info(f"Completed grant search for category '{category}'. Found {len(processed_grants)} unique grants. Duration: {search_duration:.2f}s")
        return processed_grants

    def _normalize_url(self, url):
        """Normalize URL to remove fragments and common tracking params for better deduplication."""
        if not url or not isinstance(url, str):
            return None
        try:
            parsed = urlparse(url)
            # Reconstruct without fragment, query params can be kept or removed selectively
            # Simple normalization: scheme + netloc + path
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".lower()
            # Remove trailing slash
            if normalized.endswith('/'):
                normalized = normalized[:-1]
            return normalized
        except Exception:
            return url # Return original if parsing fails

    def _process_and_deduplicate(self, grants, category):
        """Process grant data, parse deadlines, and remove duplicates based on URL."""
        unique_grants = {}
        processed_count = 0

        for grant in grants:
            processed_count += 1
            try:
                # Ensure core fields exist
                title = grant.get("title")
                desc = grant.get("description")
                raw_url = grant.get("source_url")

                if not title or not desc or not raw_url:
                     logger.debug(f"Skipping grant due to missing core fields (Title, Desc, URL): {str(grant)[:100]}...")
                     continue

                # Normalize URL for deduplication
                norm_url = self._normalize_url(raw_url)
                if not norm_url:
                     logger.debug(f"Skipping grant with invalid URL: {raw_url}")
                     continue

                # Parse deadline string
                parsed_deadline = None
                deadline_str = grant.get("deadline")
                if deadline_str:
                    if isinstance(deadline_str, datetime):
                         parsed_deadline = deadline_str # Already parsed
                    else:
                         parsed_deadline = self._parse_deadline_flexible(str(deadline_str))

                # Assign to category if not already set
                grant_category = grant.get("category") or category

                processed_grant = {
                    "title": title.strip(),
                    "description": desc.strip(),
                    "deadline": parsed_deadline, # Store as datetime or None
                    "amount": grant.get("amount"), # Keep amount flexible for now
                    "eligibility": grant.get("eligibility", "See grant details"),
                    "source_url": raw_url, # Store original URL
                    "normalized_url": norm_url, # Store normalized URL for checks
                    "source_name": grant.get("source_name", self._extract_source_name_from_url(raw_url)),
                    "category": grant_category,
                    "raw_data": grant.get("raw_data") # Store raw source if needed
                }

                # Deduplicate: Keep the entry with more detail (longer description?)
                if norm_url not in unique_grants or len(processed_grant["description"]) > len(unique_grants[norm_url]["description"]):
                    unique_grants[norm_url] = processed_grant

            except Exception as e:
                logger.error(f"Error processing grant entry: {e} - Grant: {str(grant)[:100]}...", exc_info=True)

        final_grants = list(unique_grants.values())
        logger.info(f"Processed {processed_count} raw grant entries, resulting in {len(final_grants)} unique grants.")
        return final_grants

    def _parse_deadline_flexible(self, deadline_str):
        """Attempt to parse various deadline string formats."""
        # Reuse the flexible parser from Perplexity client, or duplicate here
        # For simplicity, assume it's available or duplicate its logic
        from utils.perplexity_client import PerplexityClient # Temporary import for parsing
        return PerplexityClient._parse_deadline_flexible(None, deadline_str) # Call as static/helper

    def _extract_source_name_from_url(self, url):
        """Extract source name from URL."""
        # Reuse the helper from AgentQL client, or duplicate here
        from utils.agentql_client import AgentQLClient # Temporary import
        return AgentQLClient._extract_source_name(None, url)

    def _filter_scraped_grants(self, grants, search_terms, geo_focus):
        """Filter manually scraped grants based on keywords and geo-focus."""
        filtered = []
        from scrapers.sources.louisiana_scraper import LouisianaGrantScraper # Import geo checker

        for grant in grants:
            text_to_search = (grant.get("title", "") + " " + grant.get("description", "")).lower()
            # Check for keywords
            keywords_match = any(term.lower() in text_to_search for term in search_terms)
            # Check geo focus
            geo_match = LouisianaGrantScraper._matches_geo_focus(None, grant, geo_focus)

            if keywords_match and geo_match:
                filtered.append(grant)
        return filtered
