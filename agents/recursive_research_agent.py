"""
Recursive Research Agent - Refactored for chunked reasoning searches.
This replaces the problematic deep research API calls with recursive, chunked reasoning.
"""

import logging
import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from services.deepseek_client import DeepSeekClient
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.sql import select

from app.models import GrantFilter
from database.models import Grant as DBGrant, Analysis
from app.schemas import EnrichedGrant, ResearchContextScores, UserProfile
from config.settings import Settings

logger = logging.getLogger(__name__)

@dataclass
class SearchChunk:
    """Represents a chunk of search to be processed recursively."""
    keywords: List[str]
    geographic_focus: str
    sector_focus: str
    chunk_id: str
    priority: int = 1

@dataclass
class ChunkedSearchResult:
    """Result from a chunked search operation."""
    grants: List[Dict[str, Any]]
    search_metadata: Dict[str, Any]
    chunk_info: SearchChunk

class RecursiveResearchAgent:
    """
    Refactored Research Agent using recursive, chunked reasoning searches.
    Replaces deep research API calls with more efficient and stable approach.
    """
    
    def __init__(self, db_session_maker: async_sessionmaker):
        self.db_session_maker = db_session_maker
        self.deepseek_client = DeepSeekClient()

        # Use DeepSeek's chat model for reasoning
        self.PRIMARY_MODEL = "deepseek-chat"  # Main reasoning model
        self.FALLBACK_MODEL = "deepseek-chat"  # Same model for consistency
        self.FAST_MODEL = "deepseek-chat"  # Same model for consistency
        
        # Chunking configuration
        self.MAX_KEYWORDS_PER_CHUNK = 3
        self.MAX_CONCURRENT_CHUNKS = 5
        self.CHUNK_DELAY_SECONDS = 1.5  # Respect rate limits
        
        # Kevin's specific focus areas for chunking
        self.FOCUS_AREAS = {
            "telecommunications": [
                "telecommunications infrastructure",
                "broadband deployment",
                "mesh networks",
                "event Wi-Fi"
            ],
            "women_owned_nonprofit": [
                "women-owned nonprofit",
                "501c3 women entrepreneurs",
                "female-led organizations"
            ],
            "community_resilience": [
                "community shelter",
                "extreme weather preparedness",
                "disaster resilience"
            ],
            "rural_development": [
                "rural infrastructure",
                "Natchitoches Parish development",
                "Louisiana rural grants"
            ]
        }
        
        # Geographic priority tiers
        self.GEOGRAPHIC_TIERS = {
            "local": ["Natchitoches Parish", "Northwestern Louisiana", "Louisiana Region 7"],
            "state": ["Louisiana", "LA state grants"],
            "regional": ["Southern United States", "Gulf Coast region"],
            "federal": ["federal grants", "nationwide opportunities"]
        }

    async def search_grants_recursive(self, grant_filter: GrantFilter) -> List[EnrichedGrant]:
        """
        Main entry point for recursive grant searching.
        Breaks down the search into manageable chunks and processes them recursively.
        """
        logger.info("Starting recursive grant search with chunked reasoning approach")
        start_time = time.time()
        
        # Create search chunks based on Kevin's focus areas
        search_chunks = self._create_search_chunks(grant_filter)
        logger.info(f"Created {len(search_chunks)} search chunks for processing")
        
        all_grants = []
        processed_urls = set()
        
        # Process chunks in batches to respect rate limits
        chunk_batches = [search_chunks[i:i + self.MAX_CONCURRENT_CHUNKS] 
                        for i in range(0, len(search_chunks), self.MAX_CONCURRENT_CHUNKS)]
        
        for batch_idx, chunk_batch in enumerate(chunk_batches):
            logger.info(f"Processing chunk batch {batch_idx + 1}/{len(chunk_batches)} ({len(chunk_batch)} chunks)")
            
            # Process batch concurrently but with rate limiting
            batch_tasks = []
            for chunk in chunk_batch:
                task = self._process_search_chunk_with_delay(chunk, processed_urls)
                batch_tasks.append(task)
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Collect results and handle exceptions
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing chunk {chunk_batch[i].chunk_id}: {result}")
                    continue
                
                if result and isinstance(result, ChunkedSearchResult) and result.grants:
                    all_grants.extend(result.grants)
                    logger.info(f"Chunk {chunk_batch[i].chunk_id} found {len(result.grants)} grants")
            
            # Delay between batches to respect rate limits
            if batch_idx < len(chunk_batches) - 1:
                await asyncio.sleep(self.CHUNK_DELAY_SECONDS * 2)
        
        # Remove duplicates and enrich results
        unique_grants = self._deduplicate_grants(all_grants)
        logger.info(f"Found {len(unique_grants)} unique grants after deduplication")

        # Make grant limit configurable
        settings = Settings()
        max_grants = getattr(settings, 'MAX_GRANTS_PER_SEARCH', 20)

        # Convert to EnrichedGrant objects and perform additional enrichment
        enriched_grants = []
        for grant_data in unique_grants[:max_grants]:  # Limit based on configuration
            try:
                enriched = await self._create_enriched_grant(grant_data)
                if enriched:
                    enriched_grants.append(enriched)
            except Exception as e:
                logger.warning(f"Failed to enrich grant {grant_data.get('title', 'Unknown')}: {e}")
        
        total_time = time.time() - start_time
        logger.info(f"Recursive search completed in {total_time:.2f}s. Found {len(enriched_grants)} enriched grants")
        
        return enriched_grants

    def _create_search_chunks(self, grant_filter: GrantFilter) -> List[SearchChunk]:
        """Create search chunks based on focus areas and geographic tiers."""
        chunks = []
        chunk_counter = 0
        
        # Get base keywords from filter
        base_keywords = []
        if grant_filter.keywords:
            base_keywords = [kw.strip() for kw in grant_filter.keywords.split(',') if kw.strip()]
        
        # Create chunks for each focus area and geographic tier combination
        for focus_area, focus_keywords in self.FOCUS_AREAS.items():
            for geo_tier, geo_keywords in self.GEOGRAPHIC_TIERS.items():
                
                # Combine focus keywords with geographic keywords
                combined_keywords = focus_keywords[:self.MAX_KEYWORDS_PER_CHUNK]
                if geo_keywords:
                    combined_keywords.append(geo_keywords[0])  # Add primary geo keyword
                
                # Add base keywords if there's space
                remaining_slots = self.MAX_KEYWORDS_PER_CHUNK - len(combined_keywords)
                if remaining_slots > 0 and base_keywords:
                    combined_keywords.extend(base_keywords[:remaining_slots])
                
                # Assign priority based on geographic tier (local = highest priority)
                priority = {"local": 1, "state": 2, "regional": 3, "federal": 4}.get(geo_tier, 4)
                
                chunk = SearchChunk(
                    keywords=combined_keywords,
                    geographic_focus=geo_tier,
                    sector_focus=focus_area,
                    chunk_id=f"{focus_area}_{geo_tier}_{chunk_counter}",
                    priority=priority
                )
                chunks.append(chunk)
                chunk_counter += 1
        
        # Sort by priority (lower number = higher priority)
        chunks.sort(key=lambda x: x.priority)
        
        return chunks

    async def _process_search_chunk_with_delay(self, chunk: SearchChunk, processed_urls: Set[str]) -> ChunkedSearchResult:
        """Process a single search chunk with appropriate delay for rate limiting."""
        await asyncio.sleep(self.CHUNK_DELAY_SECONDS * chunk.priority)  # Stagger based on priority
        return await self._process_search_chunk(chunk, processed_urls)

    async def _process_search_chunk(self, chunk: SearchChunk, processed_urls: Set[str]) -> ChunkedSearchResult:
        """Process a single search chunk using recursive reasoning."""
        logger.debug(f"Processing chunk {chunk.chunk_id}: {chunk.keywords}")
        
        try:
            # Build focused query for this chunk
            query = self._build_chunk_query(chunk)

            # Use DeepSeek for reasoning
            messages = [
                {"role": "system", "content": "You are an expert grant researcher. Provide structured grant information with details."},
                {"role": "user", "content": query}
            ]
            response = await self.deepseek_client.chat_completion(
                messages=messages,
                model=self.PRIMARY_MODEL,
                temperature=0.7,
                max_tokens=2000
            )
            
            # Extract grants from response
            grants = await self._extract_grants_from_response(response, chunk)
            
            # Filter out already processed grants
            new_grants = []
            for grant in grants:
                grant_url = grant.get('source_url', '')
                grant_title = grant.get('title', '').lower()
                
                # Create unique identifier
                unique_id = grant_url if grant_url else grant_title
                if unique_id and unique_id not in processed_urls:
                    processed_urls.add(unique_id)
                    new_grants.append(grant)
            
            # Perform recursive refinement if we got good results
            if len(new_grants) >= 3:
                refined_grants = await self._recursive_refine_grants(new_grants, chunk)
                new_grants.extend(refined_grants)
            
            search_metadata = {
                "query_used": query,
                "model_used": self.PRIMARY_MODEL,
                "response_time": time.time(),
                "grants_found": len(new_grants)
            }
            
            return ChunkedSearchResult(
                grants=new_grants,
                search_metadata=search_metadata,
                chunk_info=chunk
            )
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk.chunk_id}: {e}")
            return ChunkedSearchResult(grants=[], search_metadata={}, chunk_info=chunk)

    def _build_chunk_query(self, chunk: SearchChunk) -> str:
        """Build a focused query for a specific chunk using recursive rationale approach."""
        # Create multi-step reasoning query for sonar-reasoning-pro
        base_query = (
            f"Using multi-step reasoning, analyze and find current grant opportunities that match these criteria:\n\n"
            f"Step 1: Identify grants for {' and '.join(chunk.keywords[:3])}\n"
            f"Step 2: Filter for {chunk.geographic_focus} geographic scope\n"
            f"Step 3: Validate eligibility for {chunk.sector_focus} sector\n"
            f"Step 4: Extract key details (title, amount, deadline, URL)\n\n"
            f"Search criteria:\n"
            f"- Keywords: {', '.join(chunk.keywords)}\n"
        )
        
        # Add geographic context with recursive reasoning
        if chunk.geographic_focus == "local":
            base_query += "- Geographic focus: Natchitoches Parish, Louisiana (prioritize local/parish grants)\n"
        elif chunk.geographic_focus == "state":
            base_query += "- Geographic focus: Louisiana state-wide programs\n"
        elif chunk.geographic_focus == "regional":
            base_query += "- Geographic focus: Southern United States regional programs\n"
        else:
            base_query += "- Geographic focus: Federal/nationwide programs\n"
        
        # Add sector-specific reasoning context
        sector_reasoning = {
            "telecommunications": (
                "- Sector: Telecommunications infrastructure, broadband deployment, mesh networks\n"
                "- Reasoning: Look for technology infrastructure grants, digital divide initiatives, rural broadband programs\n"
                "- Target: Small nonprofits and community organizations serving rural areas"
            ),
            "women_owned_nonprofit": (
                "- Sector: Women-owned nonprofits, 501(c)(3) organizations\n"
                "- Reasoning: Focus on grants specifically for women entrepreneurs, female-led organizations, gender equity programs\n"
                "- Target: Small to medium nonprofits led by women"
            ),
            "community_resilience": (
                "- Sector: Community resilience, disaster preparedness, emergency shelter\n"
                "- Reasoning: Search for emergency preparedness grants, disaster mitigation funding, community safety programs\n"
                "- Target: Community organizations focused on disaster preparedness"
            ),
            "rural_development": (
                "- Sector: Rural development, infrastructure improvement\n"
                "- Reasoning: Look for rural community development grants, infrastructure improvement funding\n"
                "- Target: Rural communities and development organizations"
            )
        }
        
        if chunk.sector_focus in sector_reasoning:
            base_query += f"{sector_reasoning[chunk.sector_focus]}\n"
        
        # Add recursive search instructions with URL requirement
        base_query += (
            f"\nUsing recursive reasoning:\n"
            f"1. First, search for direct matches to the keywords\n"
            f"2. Then, expand to related terms and synonyms\n"
            f"3. Cross-reference with geographic and sector requirements\n"
            f"4. Validate funding amounts are reasonable ($5,000-$100,000 preferred)\n"
            f"5. Ensure deadlines are future-dated and realistic for application\n"
            f"6. **CRITICAL: Only include grants with direct application URLs**\n\n"
            f"For each grant found, provide:\n"
            f"- Exact title\n"
            f"- Funding amount or range\n"
            f"- Application deadline\n"
            f"- Eligibility requirements\n"
            f"- **MANDATORY: Direct application URL (must start with http/https)**\n"
            f"- Brief rationale for why this grant matches the criteria\n\n"
            f"**IMPORTANT: Skip any grants that don't have a direct application URL. No URL = no grant.**"
        )
        
        return base_query

    async def _extract_grants_from_response(self, response: Dict[str, Any], chunk: SearchChunk) -> List[Dict[str, Any]]:
        """Extract grant data from DeepSeek response."""
        grants = []

        if not response or not response.get("choices"):
            return grants

        content = response["choices"][0]["message"]["content"]

        # Extract grant data from response (simplified parsing)
        extracted_grants = await self._parse_grant_data(content)
        
        # Add chunk context to each grant
        for grant in extracted_grants:
            grant["search_chunk_id"] = chunk.chunk_id
            grant["geographic_focus"] = chunk.geographic_focus
            grant["sector_focus"] = chunk.sector_focus
            grants.append(grant)

        return grants

    async def _parse_grant_data(self, content: str) -> List[Dict[str, Any]]:
        """Parse grant data from AI response content."""
        grants = []

        # Simple parsing logic - extract structured information from the response
        # This is a simplified version that looks for common patterns
        import re

        # Try to find grant entries in the content
        # Look for patterns like "Title:", "Funding:", "Deadline:", etc.
        grant_blocks = re.split(r'\n\n+', content)

        for block in grant_blocks:
            grant_data = {}

            # Extract title
            title_match = re.search(r'(?:Title|Grant)[:\s]+(.+?)(?:\n|$)', block, re.IGNORECASE)
            if title_match:
                grant_data['title'] = title_match.group(1).strip()

            # Extract funding
            funding_match = re.search(r'(?:Funding|Amount)[:\s]+\$?([\d,]+(?:\.\d{2})?)', block, re.IGNORECASE)
            if funding_match:
                try:
                    funding_str = funding_match.group(1).replace(',', '')
                    grant_data['funding_amount'] = float(funding_str)
                    grant_data['funding_amount_display'] = f"${funding_match.group(1)}"
                except ValueError:
                    pass

            # Extract deadline
            deadline_match = re.search(r'(?:Deadline|Due)[:\s]+(.+?)(?:\n|$)', block, re.IGNORECASE)
            if deadline_match:
                grant_data['deadline'] = deadline_match.group(1).strip()

            # Extract URL
            url_match = re.search(r'(?:URL|Link|Website)[:\s]+(https?://[^\s]+)', block, re.IGNORECASE)
            if url_match:
                grant_data['source_url'] = url_match.group(1).strip()

            # Extract funder
            funder_match = re.search(r'(?:Funder|Agency|Organization)[:\s]+(.+?)(?:\n|$)', block, re.IGNORECASE)
            if funder_match:
                grant_data['funder_name'] = funder_match.group(1).strip()

            # Extract description/eligibility
            desc_match = re.search(r'(?:Description|Eligibility)[:\s]+(.+?)(?:\n\n|\n[A-Z]|$)', block, re.IGNORECASE | re.DOTALL)
            if desc_match:
                grant_data['description'] = desc_match.group(1).strip()

            # Only add if we found at least a title and URL
            if grant_data.get('title') and grant_data.get('source_url'):
                grants.append(grant_data)

        return grants

    async def _recursive_refine_grants(self, grants: List[Dict[str, Any]], chunk: SearchChunk) -> List[Dict[str, Any]]:
        """Recursively refine grant information with additional targeted searches."""
        refined_grants = []
        
        # Select top grants for refinement (limit to avoid rate limits)
        top_grants = grants[:3]
        
        for grant in top_grants:
            try:
                # Create refinement query
                refinement_query = (
                    f"Find detailed information about the grant '{grant.get('title', '')}' "
                    f"from {grant.get('funder_name', 'the funding agency')}. "
                    f"Focus on specific eligibility requirements, application process, "
                    f"and any additional context that would help determine if this grant "
                    f"is suitable for a {chunk.sector_focus} project in {chunk.geographic_focus} area."
                )
                
                # Use DeepSeek for refinement
                messages = [
                    {"role": "system", "content": "You are an expert grant researcher. Provide detailed grant information."},
                    {"role": "user", "content": refinement_query}
                ]
                refinement_response = await self.deepseek_client.chat_completion(
                    messages=messages,
                    model=self.FALLBACK_MODEL,
                    temperature=0.5,
                    max_tokens=1500
                )
                
                # Extract additional details
                if refinement_response and refinement_response.get("choices"):
                    refinement_content = refinement_response["choices"][0]["message"]["content"]
                    
                    # Create refined grant entry
                    refined_grant = grant.copy()
                    refined_grant["detailed_analysis"] = refinement_content
                    refined_grant["refinement_completed"] = True
                    refined_grants.append(refined_grant)
                
                # Small delay between refinements
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Failed to refine grant {grant.get('title', 'Unknown')}: {e}")
        
        return refined_grants

    def _deduplicate_grants(self, grants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate grants based on title and URL."""
        seen_grants = set()
        unique_grants = []
        
        for grant in grants:
            # Create unique identifier with proper null handling
            title = (grant.get('title') or '').lower().strip()
            url = (grant.get('source_url') or '').strip()
            
            # Use URL if available, otherwise use title
            identifier = url if url else title
            
            if identifier and identifier not in seen_grants:
                seen_grants.add(identifier)
                unique_grants.append(grant)
        
        return unique_grants

    async def _create_enriched_grant(self, grant_data: Dict[str, Any]) -> Optional[EnrichedGrant]:
        """Create an EnrichedGrant object from grant data. ONLY creates grants with valid URLs."""
        try:
            # MANDATORY URL VALIDATION - Skip grants without valid URLs
            source_url = (grant_data.get("source_url") or "").strip()
            if not source_url or not source_url.startswith(("http://", "https://")):
                logger.info(f"Skipping grant '{grant_data.get('title', 'Unknown')}' - no valid URL: {source_url}")
                return None
            
            # Calculate relevance score based on chunk context
            relevance_score = self._calculate_relevance_score(grant_data)
            
            # Parse deadline with proper error handling
            deadline_parsed = self._parse_deadline(grant_data.get("deadline"))
            
            enriched_grant = EnrichedGrant(
                id=grant_data.get("grant_id", f"recursive_{int(time.time())}"),
                grant_id_external=grant_data.get("grant_id_external"),
                title=grant_data.get("title", "").strip(),
                description=grant_data.get("description", ""),
                summary_llm=grant_data.get("detailed_analysis", grant_data.get("description", "")),
                funder_name=grant_data.get("funder_name", ""),
                funding_amount_min=grant_data.get("funding_amount_min"),
                funding_amount_max=grant_data.get("funding_amount_max"),
                funding_amount_exact=grant_data.get("funding_amount"),
                funding_amount_display=grant_data.get("funding_amount_display", ""),
                deadline=deadline_parsed,
                eligibility_criteria=grant_data.get("eligibility", ""),
                source_url=source_url,  # Use validated URL
                keywords=grant_data.get("keywords", []),
                geographic_scope=grant_data.get("geographic_focus", ""),
                identified_sector=grant_data.get("sector_focus", ""),
                overall_composite_score=relevance_score,
                enrichment_log=[
                    f"Created from recursive search chunk: {grant_data.get('search_chunk_id', 'unknown')}",
                    f"Geographic focus: {grant_data.get('geographic_focus', 'unknown')}",
                    f"Sector focus: {grant_data.get('sector_focus', 'unknown')}",
                    f"URL validated: {source_url}"
                ],
                last_enriched_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            
            return enriched_grant
            
        except Exception as e:
            logger.error(f"Failed to create EnrichedGrant: {e}")
            return None

    def _calculate_relevance_score(self, grant_data: Dict[str, Any]) -> float:
        """Calculate relevance score based on grant characteristics and chunk context."""
        score = 0.0
        
        # Base score from funding amount
        funding_amount = grant_data.get("funding_amount", 0)
        if isinstance(funding_amount, (int, float)) and funding_amount > 0:
            if 5000 <= funding_amount <= 100000:  # Kevin's sweet spot
                score += 0.3
            elif funding_amount >= 5000:
                score += 0.2
        
        # Geographic relevance
        geo_focus = grant_data.get("geographic_focus", "")
        if geo_focus == "local":
            score += 0.4
        elif geo_focus == "state":
            score += 0.3
        elif geo_focus == "regional":
            score += 0.2
        else:
            score += 0.1
        
        # Sector match
        sector_focus = grant_data.get("sector_focus", "")
        if sector_focus in ["telecommunications", "women_owned_nonprofit"]:
            score += 0.3
        elif sector_focus in ["community_resilience", "rural_development"]:
            score += 0.2
        
        # Deadline urgency (closer deadlines get slightly higher scores)
        deadline = grant_data.get("deadline")
        if deadline:
            try:
                deadline_date = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                days_until_deadline = (deadline_date - datetime.now(timezone.utc)).days
                if 30 <= days_until_deadline <= 90:  # Sweet spot for application preparation
                    score += 0.1
                elif days_until_deadline > 0:
                    score += 0.05
            except:
                pass
        
        return min(score, 1.0)  # Cap at 1.0

    def _parse_deadline(self, deadline_value: Any) -> Optional[datetime]:
        """Parse deadline value with proper error handling for various formats."""
        if not deadline_value:
            return None
            
        if isinstance(deadline_value, datetime):
            return deadline_value
            
        if isinstance(deadline_value, str):
            # Handle common non-date strings
            deadline_lower = deadline_value.lower().strip()
            if deadline_lower in ['ongoing', 'null', 'none', 'n/a', 'tbd', 'rolling', 'continuous']:
                return None
                
            # Try to parse date strings
            try:
                from dateutil import parser
                return parser.parse(deadline_value)
            except (ValueError, TypeError):
                # If dateutil parsing fails, try some common formats
                import re
                date_patterns = [
                    r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
                    r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
                    r'(\d{1,2})-(\d{1,2})-(\d{4})',  # MM-DD-YYYY
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, deadline_value)
                    if match:
                        try:
                            if pattern.startswith(r'(\d{4})'):  # YYYY-MM-DD
                                year, month, day = match.groups()
                            else:  # MM/DD/YYYY or MM-DD-YYYY
                                month, day, year = match.groups()
                            return datetime(int(year), int(month), int(day))
                        except ValueError:
                            continue
                
                logger.warning(f"Could not parse deadline: {deadline_value}")
                return None
        
        return None
