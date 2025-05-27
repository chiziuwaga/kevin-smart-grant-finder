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
from sqlalchemy.ext.asyncio import AsyncSession

from utils.perplexity_client import PerplexityClient
from utils.pinecone_client import PineconeClient
from app.models import Grant, GrantFilter
from database.models import Grant as DBGrant, Analysis

logger = logging.getLogger(__name__)

class ResearchAgent:
    def __init__(
        self,
        perplexity_client: PerplexityClient,
        db_session: AsyncSession,
        pinecone_client: PineconeClient
    ):
        """Initialize Research Agent."""
        self.perplexity = perplexity_client
        self.db = db_session
        self.pinecone = pinecone_client

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

    async def search_grants(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for grants using Perplexity AI and filter results."""
        try:
            # Convert filters to validated model
            search_filters = GrantFilter(**filters)
            
            # Build search query
            query = self._build_search_query(search_filters)
            
            # Get results from Perplexity
            raw_results = await self.perplexity.query(query)
            
            # Parse and format results
            grants = self._parse_results(raw_results)
            
            # Score and filter results
            scored_grants = await self._score_and_filter_grants(grants, search_filters)
            
            return scored_grants
            
        except Exception as e:
            logger.error(f"Error during grant search: {str(e)}", exc_info=True)
            return []

    def _build_search_query(self, filters: GrantFilter) -> str:
        """Build a natural language query for Perplexity."""
        query_parts = ["Find available grants"]
        
        if filters.categories:
            query_parts.append(f"in categories: {', '.join(filters.categories)}")
        
        if filters.keywords:
            query_parts.append(f"matching keywords: {filters.keywords}")
            
        if filters.deadline_after:
            query_parts.append(f"with deadlines after {filters.deadline_after.strftime('%Y-%m-%d')}")
            
        if filters.deadline_before:
            query_parts.append(f"with deadlines before {filters.deadline_before.strftime('%Y-%m-%d')}")
        
        query = " ".join(query_parts)
        query += ". Include title, description, funding amount, deadline, and eligibility requirements."
        
        return query

    def _parse_results(self, raw_results: str) -> List[Dict[str, Any]]:
        """Parse Perplexity results into structured grant data."""
        # This would need proper implementation to parse the AI response
        # For now, return a placeholder
        return []

    async def _score_and_filter_grants(
        self,
        grants: List[Dict[str, Any]],
        filters: GrantFilter
    ) -> List[Dict[str, Any]]:
        """Score grants using Pinecone and filter by criteria."""
        if not grants:
            return []
            
        # Score grants using Pinecone
        for grant in grants:
            embedding = await self.pinecone.get_embedding(grant["description"])
            grant["score"] = await self.pinecone.calculate_relevance(embedding)
        
        # Filter by minimum score
        filtered_grants = [
            grant for grant in grants 
            if grant["score"] >= filters.min_score
        ]
        
        # Sort by score
        filtered_grants.sort(key=lambda x: x["score"], reverse=True)
        
        # Store the grants in the database
        for grant_data in filtered_grants:
            grant = DBGrant(
                title=grant_data["title"],
                description=grant_data["description"],
                funding_amount=grant_data.get("amount"),
                deadline=grant_data["deadline"],
                source=grant_data["source_name"],
                source_url=grant_data["source_url"],
                category=grant_data["category"],
                eligibility=grant_data.get("eligibility", {}),
                status="active"
            )
            self.db.add(grant)
            
            analysis = Analysis(
                grant=grant,
                score=grant_data["score"],
                notes="Analyzed by ResearchAgent"
            )
            self.db.add(analysis)
        
        await self.db.commit()
        return filtered_grants

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