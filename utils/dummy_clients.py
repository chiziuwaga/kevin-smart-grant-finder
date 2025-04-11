"""
Dummy client implementations for fallback when services are unavailable.
These implementations ensure the application can continue to function
with limited capabilities even when external services fail.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DummyAgentQLClient:
    """Fallback implementation when AgentQL service is unavailable."""
    
    def __init__(self):
        logger.warning("Using DummyAgentQLClient - limited search capabilities available")
    
    def create_search_agent(self, name, description, sources):
        """Return a dummy agent ID."""
        logger.info(f"DummyAgentQLClient: Would create search agent '{name}'")
        return f"dummy_agent_{hash(name)}"
    
    def search_grants(self, agent_id, query, parameters=None):
        """Return empty results instead of throwing errors."""
        logger.info(f"DummyAgentQLClient: Would search with agent {agent_id} for '{query}'")
        return []
    
    def _process_search_results(self, results):
        """Process dummy results."""
        return []

class DummyPerplexityClient:
    """Fallback implementation when Perplexity service is unavailable."""
    
    def __init__(self):
        logger.warning("Using DummyPerplexityClient - limited search capabilities available")
    
    def deep_search(self, query, site_restrictions=None, max_results=50):
        """Return empty search results."""
        logger.info(f"DummyPerplexityClient: Would search for '{query}'")
        return {"choices": []}
    
    def extract_grant_data(self, search_results):
        """Return empty grant data."""
        return []
    
    def _extract_grants_with_regex(self, text):
        """Return empty grant data for regex extraction."""
        return []

class FallbackRelevanceScorer:
    """Fallback for Pinecone vector similarity when the service is unavailable."""
    
    def __init__(self):
        logger.warning("Using FallbackRelevanceScorer - reduced accuracy for relevance scoring")
    
    def store_priority_vectors(self, priorities):
        """Simulate storing vectors but just store priorities locally."""
        self.priorities = priorities
        logger.info("FallbackRelevanceScorer: Stored priorities locally")
        return len(priorities.get("weights", {}).keys()) if isinstance(priorities, dict) else 0
    
    def calculate_relevance(self, grant_description, grant_title=None, grant_eligibility=None):
        """Simplified keyword-based scoring as fallback."""
        if not hasattr(self, 'priorities') or not isinstance(self.priorities, dict):
            return 50.0  # Default mid-range score
        
        # Create combined text for matching
        combined_text = (grant_title or "") + " " + grant_description + " " + (grant_eligibility or "")
        combined_text = combined_text.lower()
        
        # Simple keyword matching with priority weights
        total_score = 0.0
        total_weight = 0.0
        match_count = 0
        
        for category, items in self.priorities.items():
            if category in ["weights", "_id", "updated_at"]:
                continue
                
            weight = self.priorities.get("weights", {}).get(category, 1.0)
            
            for item in items:
                if isinstance(item, str) and item.lower() in combined_text:
                    total_score += weight
                    total_weight += weight
                    match_count += 1
        
        # Calculate normalized score (0-100)
        if total_weight > 0 and match_count > 0:
            normalized_score = (total_score / total_weight) * 100
            # Cap at 100
            normalized_score = min(normalized_score, 100.0)
        else:
            # No matches or weights, assign a neutral score
            normalized_score = 50.0
        
        logger.debug(f"FallbackRelevanceScorer: Calculated score {normalized_score:.2f} for grant")
        return round(normalized_score, 2)

class DummyResearchAgent:
    """Fallback implementation when Research Agent cannot be initialized."""
    
    def __init__(self):
        logger.warning("Using DummyResearchAgent - limited grant search capabilities")
    
    def setup_search_agents(self):
        """Simulate agent setup."""
        return True
    
    def search_grants(self, search_params):
        """Return empty grant results with a message."""
        logger.info(f"DummyResearchAgent: Would search with params: {search_params}")
        
        # Return a single dummy grant to show the system is working but limited
        dummy_grant = {
            "title": "Grant Search Limited",
            "description": "The grant search capability is currently limited due to service unavailability. Please try again later.",
            "deadline": datetime.utcnow() + timedelta(days=30),
            "amount": "Unknown",
            "eligibility": "N/A",
            "source_url": "https://example.com/dummy",
            "source_name": "System Message",
            "category": search_params.get("category", "unknown"),
            "relevance_score": 50.0,
        }
        
        return [dummy_grant]

class DummyAnalysisAgent:
    """Fallback implementation when Grant Analysis Agent cannot be initialized."""
    
    def __init__(self):
        logger.warning("Using DummyAnalysisAgent - limited grant analysis capabilities")
    
    def rank_grants(self, grants, priorities=None):
        """Pass through grants with minimal processing."""
        if not grants:
            return []
            
        # Add a basic relevance score if missing
        for grant in grants:
            if "relevance_score" not in grant:
                grant["relevance_score"] = 50.0  # Neutral score
                
            # Add simple summary if missing and score is high enough
            if "summary" not in grant and grant.get("relevance_score", 0) >= 70:
                grant["summary"] = f"Summary unavailable for {grant.get('title', 'this grant')}. Please check the full description."
        
        # Simple sort by deadline
        return sorted(grants, key=lambda x: x.get("deadline", datetime.max))
    
    def generate_grant_summary(self, grant):
        """Generate a basic summary."""
        return f"Summary unavailable for {grant.get('title', 'this grant')}. Please check the full description." 