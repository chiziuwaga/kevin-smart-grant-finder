import os
import aiohttp
import logging
from typing import Dict, Any, Optional
from .perplexity_handler import PerplexityRateLimitHandler

class PerplexityClient:
    def __init__(self):
        """Initialize Perplexity API client."""
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY not found in environment variables")
        
        self.base_url = "https://api.perplexity.ai/v1"
        self.rate_limiter = PerplexityRateLimitHandler()
        
    async def search_grants(self, query: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Search for grants using Perplexity API.
        
        Args:
            query (str): Search query
            filters (Optional[Dict]): Additional search filters
            
        Returns:
            Dict[str, Any]: Search results and metadata
        """
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Prepare search parameters
            params = {
                "query": query,
                "mode": "deep_search",
                "domain_restrictions": ["grants.gov", "usda.gov", "broadbandusa.ntia.doc.gov", "fcc.gov"]
            }
            
            if filters:
                params.update(filters)
            
            async def _execute_search():
                async with session.post(
                    f"{self.base_url}/search",
                    headers=headers,
                    json=params
                ) as response:
                    return await response.json()
            
            # Execute with rate limiting
            result, metadata = await self.rate_limiter.execute_with_rate_limit(_execute_search)
            
            if metadata.get("quota_exceeded"):
                logging.error("Perplexity API daily quota exceeded")
                return {"error": "Daily quota exceeded", "metadata": metadata}
            
            if result:
                # Process and structure the results
                processed_results = self._process_search_results(result)
                return {
                    "results": processed_results,
                    "metadata": metadata
                }
            
            return {"error": "Search failed", "metadata": metadata}
    
    def _process_search_results(self, raw_results: Dict) -> Dict:
        """Process and structure raw search results.
        
        Args:
            raw_results (Dict): Raw API response
            
        Returns:
            Dict: Processed and structured results
        """
        processed = {
            "grants": [],
            "total_found": 0,
            "source_breakdown": {}
        }
        
        if "results" in raw_results:
            for result in raw_results["results"]:
                # Extract grant information
                grant = {
                    "title": result.get("title", ""),
                    "description": result.get("text", ""),
                    "url": result.get("url", ""),
                    "source": self._extract_source_domain(result.get("url", "")),
                    "relevance_score": result.get("relevance_score", 0),
                    "deadline": self._extract_deadline(result.get("text", "")),
                    "amount": self._extract_amount(result.get("text", "")),
                    "category": self._categorize_grant(result)
                }
                
                processed["grants"].append(grant)
                
                # Update source breakdown
                source = grant["source"]
                processed["source_breakdown"][source] = processed["source_breakdown"].get(source, 0) + 1
            
            processed["total_found"] = len(processed["grants"])
        
        return processed
    
    def _extract_source_domain(self, url: str) -> str:
        """Extract source domain from URL."""
        if "grants.gov" in url:
            return "grants.gov"
        elif "usda.gov" in url:
            return "usda.gov"
        elif "broadbandusa.ntia.doc.gov" in url:
            return "ntia.gov"
        elif "fcc.gov" in url:
            return "fcc.gov"
        return "other"
    
    def _extract_deadline(self, text: str) -> Optional[str]:
        """Extract application deadline from text."""
        # TODO: Implement deadline extraction logic
        return None
    
    def _extract_amount(self, text: str) -> Optional[str]:
        """Extract grant amount from text."""
        # TODO: Implement amount extraction logic
        return None
    
    def _categorize_grant(self, result: Dict) -> str:
        """Categorize grant based on content."""
        # TODO: Implement grant categorization logic
        return "uncategorized" 