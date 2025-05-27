"""
Analysis Agent for processing and evaluating grant opportunities.
"""

import logging
from typing import List, Dict, Any, Set
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker # Added async_sessionmaker
from utils.pinecone_client import PineconeClient
from database.models import Grant, Analysis

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
        """Analyze grants for relevance and priority."""
        if not grants:
            return []
            
        try:
            # Fetch existing grants for deduplication
            existing_titles = await self._get_existing_grant_titles()
            
            # Filter out duplicates and analyze remaining grants
            new_grants = []
            for grant in grants:
                if grant["title"] not in existing_titles:
                    analyzed = await self._analyze_single_grant(grant)
                    if analyzed:
                        new_grants.append(analyzed)
            
            return new_grants
            
        except Exception as e:
            logger.error(f"Error during grant analysis: {str(e)}", exc_info=True)
            return []
    
    async def _get_existing_grant_titles(self) -> Set[str]:
        """Get titles of existing grants to avoid duplicates."""
        async with self.db_sessionmaker() as session: # Use sessionmaker
            result = await session.execute(
                select(Grant.title).distinct()
            )
            return set(result.scalars().all())
    
    async def _analyze_single_grant(self, grant: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single grant for various factors."""
        async with self.db_sessionmaker() as session: # Use sessionmaker
            try:
                # Calculate priority score based on multiple factors
                deadline_score = self._calculate_deadline_score(grant.get("deadline"))
                funding_score = self._calculate_funding_score(grant.get("funding_amount"))
                relevance_score = grant.get("score", 0.0)
                
                # Combine scores (weighted average)
                final_score = (
                    (deadline_score * 0.3) +
                    (funding_score * 0.3) +
                    (relevance_score * 0.4)
                )
                
                # Store grant in database
                db_grant = Grant(
                    title=grant["title"],
                    description=grant["description"],
                    funding_amount=grant.get("funding_amount"),
                    deadline=grant.get("deadline"),
                    source=grant.get("source"),
                    source_url=grant.get("source_url"),
                    category=grant.get("category"),
                    eligibility=grant.get("eligibility", {}),
                    status="active"
                )
                session.add(db_grant) # Use the created session
                
                # Store analysis results
                db_analysis = Analysis(
                    grant=db_grant,
                    score=final_score,
                    notes=f"Deadline: {deadline_score:.2f}, Funding: {funding_score:.2f}, Relevance: {relevance_score:.2f}"
                )
                session.add(db_analysis) # Use the created session
                await session.commit() # Commit the session
                
                # Update grant with analysis
                grant.update({
                    "score": final_score,
                    "analyzed_at": datetime.now(),
                    "factors": {
                        "deadline_score": deadline_score,
                        "funding_score": funding_score,
                        "relevance_score": relevance_score
                    }
                })
                
                return grant
                
            except Exception as e:
                logger.error(f"Error analyzing grant: {str(e)}", exc_info=True)
                await session.rollback() # Rollback the session
                return None
    
    def _calculate_deadline_score(self, deadline: Any) -> float:
        """Calculate score based on deadline proximity."""
        if not deadline:
            return 0.5  # Middle score for unknown deadlines
            
        try:
            if isinstance(deadline, str):
                deadline = datetime.fromisoformat(deadline)
                
            days_until = (deadline - datetime.now()).days
            
            if days_until < 0:
                return 0.0  # Expired
            elif days_until < 7:
                return 0.9  # Urgent
            elif days_until < 30:
                return 0.7  # Soon
            elif days_until < 90:
                return 0.5  # Medium term
            else:
                return 0.3  # Long term
        except:
            return 0.5  # Default for parsing errors
    
    def _calculate_funding_score(self, funding: Any) -> float:
        """Calculate score based on funding amount."""
        if not funding:
            return 0.5  # Middle score for unknown amounts
            
        try:
            # Extract numeric value if it's a string
            if isinstance(funding, str):
                funding = ''.join(filter(str.isdigit, funding))
                funding = float(funding)
                
            # Score based on amount ranges
            if funding >= 1000000:
                return 0.9  # Large grants
            elif funding >= 100000:
                return 0.7  # Medium grants
            elif funding >= 10000:
                return 0.5  # Small grants
            else:
                return 0.3  # Micro grants
        except:
            return 0.5  # Default for parsing errors