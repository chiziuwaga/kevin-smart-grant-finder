"""
Analysis Agent for processing and evaluating grant opportunities.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from utils.mongodb_client import MongoDBClient
from utils.pinecone_client import PineconeClient

logger = logging.getLogger(__name__)

class AnalysisAgent:
    def __init__(
        self,
        mongodb_client: MongoDBClient,
        pinecone_client: PineconeClient
    ):
        self.mongodb = mongodb_client
        self.pinecone = pinecone_client
        
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
    
    async def _get_existing_grant_titles(self) -> set:
        """Get titles of existing grants to avoid duplicates."""
        existing = await self.mongodb.grants.distinct("title")
        return set(existing)
    
    async def _analyze_single_grant(self, grant: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single grant for various factors."""
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