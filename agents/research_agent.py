"""
Research Agent for finding grant opportunities.
"""

import logging
import time
from datetime import datetime, timedelta
import re
from urllib.parse import urlparse

class ResearchAgent:
    def __init__(self, perplexity_client, agentql_client, mongodb_client):
        """Initialize Research Agent."""
        self.perplexity_client = perplexity_client
        self.agentql_client = agentql_client  # Added agentql_client
        self.mongodb_client = mongodb_client

        # Initialize agent IDs (from the updated description)
        self.telecom_agent_id = None
        self.nonprofit_agent_id = None
        logging.info("Research Agent initialized")

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

    def search_grants(self, search_params):
        """Search for grants using the provided parameters."""
        start_time = time.time()
        logging.info(f"Starting grant search with params: {search_params}")

        # Extract core search parameters
        category = search_params.get("category", "unknown")
        search_terms = search_params.get("search_terms", [])
        sources = search_params.get("sources", []) # Base sources

        # Extract advanced filter parameters
        funding_types = search_params.get("funding_type", []) # List of strings
        eligible_entities = search_params.get("eligible_entities", []) # List of strings
        geo_restrictions = search_params.get("geo_restrictions", None) # String like 'LA-08'
        priority_keywords = search_params.get("priority_keywords", []) # List of strings for nonprofit
        funding_range = search_params.get("funding_range", None) # Tuple (min, max)
        compliance_check = search_params.get("compliance_check", False) # Boolean for 501c3
        custom_search_text = search_params.get("search_text", "") # User-entered text

        # Store sources in database
        for source in sources:
            self.mongodb_client.store_source({
                "name": source,
                "domain": category,
                "url": self._get_source_url(source),
                "last_searched": datetime.utcnow()
            })

        # --- AgentQL Search --- (Enhanced Query Construction)
        results = []
        agent_id = self.telecom_agent_id if category == "telecom" else self.nonprofit_agent_id
        if not agent_id:
            self.setup_search_agents()
            agent_id = self.telecom_agent_id if category == "telecom" else self.nonprofit_agent_id

        if agent_id and self.agentql_client:
            # Combine base terms and priority keywords
            all_keywords = list(set(search_terms + priority_keywords + ([custom_search_text] if custom_search_text else [])))
            if not all_keywords:
                all_keywords = [category] # Default to category if no keywords

            query = " OR ".join([f'"{term}"' for term in all_keywords if term])

            # Add structured parameters if supported by AgentQL (assuming capability)
            agentql_params = {"max_results": 20}
            if funding_types:
                agentql_params["funding_type"] = funding_types
            if eligible_entities:
                agentql_params["eligibility"] = eligible_entities
            if geo_restrictions:
                agentql_params["geographic_area"] = geo_restrictions
            if funding_range:
                agentql_params["funding_min"] = funding_range[0]
                agentql_params["funding_max"] = funding_range[1]
            if compliance_check:
                 agentql_params["requirements"] = "501(c)(3)"

            logging.info(f"Executing AgentQL search with query: {query} and params: {agentql_params}")
            agent_results = self.agentql_client.search_grants(
                agent_id=agent_id,
                query=query,
                parameters=agentql_params
            )
            results.extend(agent_results)
            logging.info(f"AgentQL search returned {len(agent_results)} results.")
        else:
            logging.warning("AgentQL search skipped: Client or Agent ID not available.")

        # --- Perplexity Search --- (Enhanced Query Construction)
        if self.perplexity_client:
            # Combine keywords for broader search
            perplexity_keywords = list(set(search_terms + priority_keywords + ([custom_search_text] if custom_search_text else [])))
            if not perplexity_keywords:
                perplexity_keywords = [category]

            query_parts = [" OR ".join([f'"{term}"' for term in perplexity_keywords if term])]

            # Add filters as natural language parts of the query
            if funding_types:
                query_parts.append(f"funding type: ({' OR '.join(funding_types)})" )
            if eligible_entities:
                query_parts.append(f"eligible entities: ({' OR '.join(eligible_entities)})" )
            if geo_restrictions:
                query_parts.append(f'in geographic area "{geo_restrictions}"' )
            if funding_range:
                query_parts.append(f"funding between ${funding_range[0]:,} and ${funding_range[1]:,}")
            if compliance_check:
                query_parts.append("requires 501(c)(3) status")

            perplexity_query = " AND ".join(query_parts)
            perplexity_query += ' "application deadline" OR "grant deadline" OR "submission deadline"' # Keep deadline focus

            # Prepare site restrictions (ensure valid domains)
            site_restrictions = [f"site:{self._get_domain(s)}" for s in sources if self._get_domain(s)]
            if not site_restrictions:
                site_restrictions = ["site:gov", "site:org", "site:edu"] # Defaults

            logging.info(f"Executing Perplexity search with query: {perplexity_query}")
            perplexity_search_results = self.perplexity_client.deep_search(
                query=perplexity_query,
                site_restrictions=site_restrictions,
                max_results=50
            )
            extracted_grants = self.perplexity_client.extract_grant_data(perplexity_search_results)
            logging.info(f"Perplexity search returned {len(extracted_grants)} potential grants.")
            results.extend(extracted_grants)
        else:
             logging.warning("Perplexity search skipped: Client not available.")

        # Deduplicate results based on source_url or title+description hash
        processed_grants = self._deduplicate_and_process(results, category)

        # Store processed grants
        stored_count = self.mongodb_client.store_grants(processed_grants)

        # Log search history
        search_duration = time.time() - start_time
        self.mongodb_client.store_search_history(search_params, stored_count, search_duration)

        logging.info(f"Completed grant search for category '{category}'. Found {len(results)} raw, processed {len(processed_grants)}, stored {stored_count} grants in {search_duration:.2f}s.")
        return processed_grants

    def _get_domain(self, source_name_or_url):
        """Extract domain name from a source name or URL."""
        try:
            if source_name_or_url.startswith("http://") or source_name_or_url.startswith("https://"):
                return urlparse(source_name_or_url).netloc
            elif '.' in source_name_or_url:
                return source_name_or_url.lower().replace(' ', '') # Assume it's a domain like grants.gov
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