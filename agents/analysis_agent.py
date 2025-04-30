"""
Analysis Agent for processing and evaluating grant opportunities.
"""

import logging

logger = logging.getLogger(__name__)

class GrantAnalysisAgent:
    def __init__(self, pinecone_client, mongo_client):
        """Initialize the agent with necessary clients."""
        self.pinecone_client = pinecone_client
        self.mongo_client = mongo_client
        self.criteria = {}
        logger.info("Grant Analysis Agent initialized")

    def analyze_grant(self, grant_data):
        """
        Analyze a grant opportunity against defined criteria.
        
        Args:
            grant_data (dict): Grant information to analyze
            
        Returns:
            dict: Analysis results with scoring and recommendations
        """
        pass

    def set_criteria(self, criteria):
        """
        Set analysis criteria for evaluating grants.
        
        Args:
            criteria (dict): Dictionary of criteria and their weights
        """
        self.criteria = criteria

    def get_recommendations(self, analysis_results):
        """
        Generate recommendations based on analysis results.
        
        Args:
            analysis_results (dict): Results from grant analysis
            
        Returns:
            list: List of recommendations
        """
        pass

    def rank_grants(self, grants, priorities=None):
        """Calculate relevance score for each grant and return list sorted desc."""
        ranked = []
        if priorities is None:
            priorities = self.mongo_client.get_priorities()
        for grant in grants:
            score = self.pinecone_client.calculate_relevance(
                grant.get("description", ""),
                grant_title=grant.get("title"),
                grant_eligibility=grant.get("eligibility")
            )
            # Boost score if Louisiana keyword appears
            text = (grant.get("title", "") + " " + grant.get("description", "")).lower()
            if any(k in text for k in ["louisiana", "la-08", "natchitoches"]):
                score = min(100, score + 10)

            grant["relevance_score"] = round(score, 2)
            ranked.append(grant)

        ranked.sort(key=lambda g: g["relevance_score"], reverse=True)
        return ranked

    def rank_and_store(self, grants):
        """Rank grants then upsert into Mongo, returns stats."""
        if not grants:
            return {"stored":0}
        ranked = self.rank_grants(grants)
        stored = self.mongo_client.store_grants(ranked)
        return {"stored": stored, "total": len(ranked)}