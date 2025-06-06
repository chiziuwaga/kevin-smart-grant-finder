"""
Analysis Agent for processing and evaluating grant opportunities.
"""

import logging
import re # Added import for regular expressions
from typing import List, Dict, Any, Set, Optional # Added Optional
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker # Added async_sessionmaker
from utils.pinecone_client import PineconeClient
from database.models import Grant, Analysis, GrantStatus # Corrected import for GrantStatus
# from app.models import GrantStatus # Incorrect import

logger = logging.getLogger(__name__)

class AnalysisAgent:
    def __init__(
        self,
        db_sessionmaker: async_sessionmaker, # Changed from db_session: AsyncSession
        pinecone_client: PineconeClient
    ):
        self.db_sessionmaker = db_sessionmaker # Store the sessionmaker
        self.pinecone = pinecone_client
        logger.info("Analysis Agent initialized")
    
    async def analyze_grants(self, grants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze grants for relevance and priority, ensuring robust handling of input data."""
        if not grants:
            logger.info("AnalysisAgent received no grants to analyze.")
            return []
            
        analyzed_and_stored_grants = []
        try:
            existing_titles = await self._get_existing_grant_titles()
            
            for grant_data in grants:
                if not isinstance(grant_data, dict):
                    logger.warning(f"Skipping non-dictionary item in grants list: {type(grant_data)}")
                    continue

                title = grant_data.get("title")
                if not title or not isinstance(title, str):
                    logger.warning(f"Skipping grant with missing or invalid title: {grant_data}")
                    continue # Essential field

                if title in existing_titles:
                    logger.info(f"Skipping duplicate grant by title: {title}")
                    continue
                    
                # Add to existing_titles immediately to handle potential duplicates within the current batch
                existing_titles.add(title)

                processed_grant = await self._analyze_and_store_single_grant(grant_data)
                if processed_grant:
                    analyzed_and_stored_grants.append(processed_grant)
            
            logger.info(f"AnalysisAgent processed {len(grants)} grants, successfully analyzed and stored {len(analyzed_and_stored_grants)} new grants.")
            return analyzed_and_stored_grants
            
        except Exception as e:
            logger.error(f"Error during grant analysis batch: {str(e)}", exc_info=True)
            return analyzed_and_stored_grants # Return what was processed so far

    async def _get_existing_grant_titles(self) -> Set[str]:
        """Get titles of existing grants to avoid duplicates."""
        async with self.db_sessionmaker() as session: # Use sessionmaker
            result = await session.execute(
                select(Grant.title).distinct()
            )
            return set(result.scalars().all())
    
    async def _analyze_and_store_single_grant(self, grant_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze a single grant, store it, and return its analyzed representation."""
        # Safe extraction of fields from grant_data
        title = grant_data.get("title", "Unknown Grant Title") # Already checked but good practice
        description = grant_data.get("description", "No description provided.")
        raw_funding_amount = grant_data.get("funding_amount") # Processed in _calculate_funding_score
        raw_deadline = grant_data.get("deadline") # Processed in _calculate_deadline_score
        source_name = grant_data.get("source_name", "Unknown Source")
        source_url = grant_data.get("source_url")
        category = grant_data.get("category", "Uncategorized")
        eligibility_info = grant_data.get("eligibility_criteria", grant_data.get("eligibility")) # Check both keys
        if isinstance(eligibility_info, str): # Ensure eligibility is a dict for JSON field
            eligibility_json = {"text_summary": eligibility_info}
        elif isinstance(eligibility_info, dict):
            eligibility_json = eligibility_info
        else:
            eligibility_json = {"details": "Not specified or invalid format"}

        # Scores
        # The 'score' from ResearchAgent is Pinecone's relevance. We'll call it pinecone_score here.
        pinecone_relevance_score = grant_data.get("score", 0.0) 
        deadline_score = self._calculate_deadline_score(raw_deadline)
        funding_score = self._calculate_funding_score(raw_funding_amount)
        
        # Combine scores (weighted average)
        # Weights can be tuned
        final_score = (
            (deadline_score * 0.3) +
            (funding_score * 0.3) +
            (pinecone_relevance_score * 0.4) 
        )
        
        parsed_deadline_dt = self._parse_deadline_to_datetime(raw_deadline)

        async with self.db_sessionmaker() as session:
            try:
                db_grant = Grant(
                    title=title,
                    description=description,
                    # funding_amount is tricky if it's a range. Store raw or parse to a representative float?
                    # For now, let's try to parse a primary numeric value for the DB field if it's a float.
                    funding_amount=self._parse_funding_to_float(raw_funding_amount), 
                    deadline=parsed_deadline_dt, # Store as datetime
                    source=source_name,
                    source_url=source_url,
                    category=category,
                    eligibility=eligibility_json, # Stored as JSON
                    status=GrantStatus.ACTIVE # Default status
                )
                session.add(db_grant)
                await session.flush() # To get db_grant.id for the Analysis record
                
                db_analysis = Analysis(
                    grant_id=db_grant.id, # Link to the grant
                    score=final_score,
                    notes=f"Deadline Score: {deadline_score:.2f}, Funding Score: {funding_score:.2f}, Pinecone Relevance: {pinecone_relevance_score:.2f}"
                )
                session.add(db_analysis)
                await session.commit()
                
                logger.info(f"Successfully analyzed and stored grant: '{title}' with final score: {final_score:.2f}")
                
                # Return a dictionary representing the analyzed grant for further processing (e.g., notifications)
                return {
                    "id": db_grant.id, # Include DB id
                    "title": title,
                    "description": description,
                    "funding_amount_display": str(raw_funding_amount or "N/A"), # Keep display string
                    "deadline_display": str(raw_deadline or "N/A"),
                    "source_url": source_url,
                    "category": category,
                    "final_score": final_score,
                    "pinecone_relevance_score": pinecone_relevance_score,
                    "deadline_score": deadline_score,
                    "funding_score": funding_score,
                    "analyzed_at": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error processing/storing grant '{title}': {str(e)}", exc_info=True)
                await session.rollback()
                return None
    
    def _parse_deadline_to_datetime(self, deadline_input: Any) -> Optional[datetime]:
        if not deadline_input: return None
        if isinstance(deadline_input, datetime): return deadline_input
        if isinstance(deadline_input, str):
            try:
                # Try ISO format first (YYYY-MM-DD), which ResearchAgent might produce
                return datetime.fromisoformat(deadline_input.split('T')[0]) # Handle YYYY-MM-DDTHH:MM:SS
            except ValueError:
                pass # Continue to other parsing attempts
            
            # Add more robust parsing here if various string formats are expected
            # For now, relying on ResearchAgent to provide a somewhat standard string if not datetime
            # Example: from dateutil import parser; return parser.parse(deadline_input)
            try:
                from dateutil import parser # Lazy import
                # Set dayfirst=False as US formats are common
                dt = parser.parse(deadline_input, dayfirst=False, fuzzy=True)
                # If year is missing or seems off, dateutil might default to current year or 1900
                if dt.year < datetime.now().year - 5 : # Arbitrary check for very old year
                     current_year = datetime.now().year
                     dt = dt.replace(year=current_year)
                     if dt < datetime.now() - timedelta(days=365): # If replacing makes it more than a year in past
                         dt = dt.replace(year=current_year + 1)
                return dt
            except (ImportError, ValueError, TypeError) as e:
                logger.warning(f"Could not parse deadline string '{deadline_input}' to datetime: {e}. Returning None.")
                return None
        return None

    def _calculate_deadline_score(self, deadline_input: Any) -> float:
        """Calculate score based on deadline proximity."""
        deadline_dt = self._parse_deadline_to_datetime(deadline_input)
        if not deadline_dt:
            return 0.0  # Treat unknown/unparsable deadlines as expired
            
        try:
            days_until = (deadline_dt - datetime.now()).days
            if days_until < 0: return 0.0  # Expired
            if days_until < 7: return 0.9  # Urgent
            if days_until < 30: return 0.7  # Soon
            if days_until < 90: return 0.5  # Medium term
            return 0.3  # Long term
        except Exception as e:
            logger.warning(f"Error calculating deadline score for '{deadline_input}': {e}")
            return 0.5
    
    def _parse_funding_to_float(self, funding_input: Any) -> Optional[float]:
        if funding_input is None: return None
        if isinstance(funding_input, (int, float)): return float(funding_input)
        if isinstance(funding_input, str):
            try:
                # Remove $, commas, and text like "Up to", "Approx."
                cleaned_funding = funding_input.lower()
                cleaned_funding = re.sub(r"(up to|approx\.|approximately|about|around)", "", cleaned_funding)
                cleaned_funding = re.sub(r"[$,kmb]", "", cleaned_funding).strip()
                # Handle ranges like "10000 - 20000" -> take the first number or average
                if '-' in cleaned_funding:
                    parts = [p.strip() for p in cleaned_funding.split('-')]
                    return float(parts[0]) # Take the lower bound for simplicity
                return float(cleaned_funding)
            except ValueError:
                logger.warning(f"Could not parse funding string '{funding_input}' to float. Returning None.")
                return None
        return None

    def _calculate_funding_score(self, funding_input: Any) -> float:
        """Calculate score based on funding amount."""
        numeric_funding = self._parse_funding_to_float(funding_input)
        if numeric_funding is None:
            return 0.5  # Middle score for unknown/unparsable amounts
            
        try:
            if numeric_funding >= 100000: return 0.9 # Adjusted threshold based on persona max $100k
            if numeric_funding >= 50000: return 0.7  
            if numeric_funding >= self.pinecone.FUNDING_MIN: return 0.5 # Assuming FUNDING_MIN is defined in pinecone_client or agent
            # Let's use the FUNDING_MIN from ResearchAgent persona if available, or a default
            # This requires AnalysisAgent to know about ResearchAgent.FUNDING_MIN or have its own.
            # For now, using a hardcoded value or assuming it's available via self.pinecone (which is not ideal)
            # A better way would be to pass config/persona to AnalysisAgent or use a shared config.
            # Let's assume a general small grant threshold for now.
            if numeric_funding >= 5000: return 0.5 # Small grants (using ResearchAgent.FUNDING_MIN)
            return 0.3  # Micro grants
        except Exception as e:
            logger.warning(f"Error calculating funding score for '{funding_input}' (parsed as {numeric_funding}): {e}")
            return 0.5