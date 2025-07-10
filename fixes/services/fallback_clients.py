"""
Fallback service implementations for when external services are unavailable.
Provides graceful degradation with mock functionality.
"""

import asyncio
import logging
import random
import time
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class FallbackConfig:
    """Configuration for fallback services"""
    enable_fallback: bool = True
    fallback_response_delay: float = 0.1  # Simulate network delay
    mock_data_enabled: bool = True
    log_fallback_usage: bool = True

class FallbackService(ABC):
    """Base class for fallback services"""
    
    def __init__(self, service_name: str, config: Optional[FallbackConfig] = None):
        self.service_name = service_name
        self.config = config or FallbackConfig()
        self.fallback_usage_count = 0
        self.last_fallback_time = None
        
    async def _simulate_delay(self):
        """Simulate network delay for realistic behavior"""
        if self.config.fallback_response_delay > 0:
            await asyncio.sleep(self.config.fallback_response_delay)
    
    def _log_fallback_usage(self, method_name: str):
        """Log fallback service usage"""
        if self.config.log_fallback_usage:
            self.fallback_usage_count += 1
            self.last_fallback_time = datetime.utcnow()
            logger.info(f"Using fallback for {self.service_name}.{method_name} (usage count: {self.fallback_usage_count})")

class FallbackPineconeClient(FallbackService):
    """Fallback implementation for Pinecone client"""
    
    def __init__(self, config: Optional[FallbackConfig] = None):
        super().__init__("PineconeClient", config)
        self.mock_vectors = {}
        self.next_id = 1
        
    async def upsert_vectors(self, vectors: List[Dict[str, Any]], namespace: str = "") -> Dict[str, Any]:
        """Mock vector upsert operation"""
        self._log_fallback_usage("upsert_vectors")
        await self._simulate_delay()
        
        # Store vectors in mock storage
        for vector in vectors:
            vector_id = vector.get("id", str(self.next_id))
            self.mock_vectors[vector_id] = {
                "id": vector_id,
                "values": vector.get("values", []),
                "metadata": vector.get("metadata", {}),
                "namespace": namespace,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.next_id += 1
        
        return {
            "upserted_count": len(vectors),
            "status": "success",
            "fallback": True
        }
    
    async def query_vectors(self, query_vector: List[float], top_k: int = 10, 
                          namespace: str = "", include_metadata: bool = True) -> Dict[str, Any]:
        """Mock vector query operation"""
        self._log_fallback_usage("query_vectors")
        await self._simulate_delay()
        
        # Generate mock similarity scores
        matches = []
        available_vectors = [v for v in self.mock_vectors.values() if v["namespace"] == namespace]
        
        # Simulate similarity scoring
        for vector in available_vectors[:top_k]:
            similarity_score = random.uniform(0.7, 0.95)  # Mock high similarity
            match = {
                "id": vector["id"],
                "score": similarity_score,
                "values": vector["values"] if include_metadata else None,
                "metadata": vector["metadata"] if include_metadata else None
            }
            matches.append(match)
        
        # Sort by score (descending)
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "matches": matches,
            "namespace": namespace,
            "usage": {
                "read_units": 1
            },
            "fallback": True
        }
    
    async def delete_vectors(self, ids: List[str], namespace: str = "") -> Dict[str, Any]:
        """Mock vector deletion operation"""
        self._log_fallback_usage("delete_vectors")
        await self._simulate_delay()
        
        deleted_count = 0
        for vector_id in ids:
            if vector_id in self.mock_vectors:
                del self.mock_vectors[vector_id]
                deleted_count += 1
        
        return {
            "deleted_count": deleted_count,
            "status": "success",
            "fallback": True
        }
    
    async def describe_index_stats(self, namespace: str = "") -> Dict[str, Any]:
        """Mock index statistics"""
        self._log_fallback_usage("describe_index_stats")
        await self._simulate_delay()
        
        namespace_vectors = [v for v in self.mock_vectors.values() if v["namespace"] == namespace]
        
        return {
            "namespaces": {
                namespace: {
                    "vector_count": len(namespace_vectors)
                }
            },
            "dimension": 1536,  # Common dimension for embeddings
            "index_fullness": 0.1,
            "total_vector_count": len(self.mock_vectors),
            "fallback": True
        }

class FallbackPerplexityClient(FallbackService):
    """Fallback implementation for Perplexity client"""
    
    def __init__(self, config: Optional[FallbackConfig] = None):
        super().__init__("PerplexityClient", config)
        self.mock_responses = self._generate_mock_responses()
        
    def _generate_mock_responses(self) -> List[Dict[str, Any]]:
        """Generate mock grant search responses"""
        return [
            {
                "query_match": ["technology", "innovation", "startup"],
                "response": {
                    "choices": [{
                        "message": {
                            "content": """Based on current grant opportunities, here are relevant funding sources:

1. **Small Business Innovation Research (SBIR)** - Federal program offering $500K-$1.5M for technology development
   - Deadline: Rolling applications
   - Focus: Innovative technology solutions
   - URL: https://sbir.gov

2. **National Science Foundation (NSF) Small Business Innovation Research** - $256K Phase I, $1M Phase II
   - Deadline: Multiple per year
   - Focus: Scientific and technological innovation
   - URL: https://nsf.gov/sbir

3. **ARPA-E Technology-to-Market** - Up to $1.5M for energy technology commercialization
   - Deadline: Annual solicitation
   - Focus: Advanced energy technologies
   - URL: https://arpa-e.energy.gov
   
These grants support innovative technology development with strong commercial potential."""
                        }
                    }]
                }
            },
            {
                "query_match": ["healthcare", "medical", "biotech"],
                "response": {
                    "choices": [{
                        "message": {
                            "content": """Healthcare and biotech funding opportunities:

1. **NIH Small Business Innovation Research (SBIR)** - $300K-$2M for medical innovation
   - Deadline: Multiple per year
   - Focus: Health technology solutions
   - URL: https://nih.gov/sbir

2. **Gates Foundation Global Health** - $100K-$10M for global health innovations
   - Deadline: Ongoing
   - Focus: Health equity and access
   - URL: https://gatesfoundation.org

3. **CDC Public Health Emergency Preparedness** - $50K-$500K
   - Deadline: Annual
   - Focus: Public health infrastructure
   - URL: https://cdc.gov/phep"""
                        }
                    }]
                }
            }
        ]
    
    async def search(self, query: str, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Mock search operation"""
        self._log_fallback_usage("search")
        await self._simulate_delay()
        
        # Find best matching response
        query_lower = query.lower()
        best_match = None
        best_score = 0
        
        for response_data in self.mock_responses:
            score = sum(1 for keyword in response_data["query_match"] if keyword in query_lower)
            if score > best_score:
                best_score = score
                best_match = response_data
        
        # Use first response if no good match
        if not best_match:
            best_match = self.mock_responses[0]
        
        response = best_match["response"].copy()
        response["fallback"] = True
        response["model"] = model or "mock-model"
        response["usage"] = {
            "prompt_tokens": len(query.split()) * 2,
            "completion_tokens": 200,
            "total_tokens": len(query.split()) * 2 + 200
        }
        
        return response

class FallbackNotificationManager(FallbackService):
    """Fallback implementation for notification manager"""
    
    def __init__(self, config: Optional[FallbackConfig] = None):
        super().__init__("NotificationManager", config)
        self.mock_notifications = []
        
    async def send_notification(self, message: str, priority: str = "normal", 
                              notification_type: str = "info") -> Dict[str, Any]:
        """Mock notification sending"""
        self._log_fallback_usage("send_notification")
        await self._simulate_delay()
        
        notification = {
            "id": f"mock_notification_{len(self.mock_notifications)}",
            "message": message,
            "priority": priority,
            "type": notification_type,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "sent",
            "fallback": True
        }
        
        self.mock_notifications.append(notification)
        logger.info(f"Mock notification sent: {message}")
        
        return {
            "success": True,
            "notification_id": notification["id"],
            "fallback": True
        }
    
    async def send_batch_notifications(self, notifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mock batch notification sending"""
        self._log_fallback_usage("send_batch_notifications")
        await self._simulate_delay()
        
        results = []
        for notification in notifications:
            result = await self.send_notification(
                notification.get("message", ""),
                notification.get("priority", "normal"),
                notification.get("type", "info")
            )
            results.append(result)
        
        return {
            "success": True,
            "sent_count": len(results),
            "results": results,
            "fallback": True
        }

class FallbackResearchAgent(FallbackService):
    """Fallback implementation for research agent"""
    
    def __init__(self, config: Optional[FallbackConfig] = None):
        super().__init__("ResearchAgent", config)
        self.mock_grants = self._generate_mock_grants()
        
    def _generate_mock_grants(self) -> List[Dict[str, Any]]:
        """Generate mock grant data"""
        return [
            {
                "id": "mock_grant_1",
                "title": "Innovation in Technology Development",
                "description": "Support for innovative technology solutions with commercial potential",
                "funding_amount": 500000,
                "funding_amount_display": "$500,000",
                "deadline": (datetime.now() + timedelta(days=90)).isoformat(),
                "eligibility_criteria": "Small businesses with innovative technology solutions",
                "category": "Technology",
                "source_url": "https://example.gov/grants/tech",
                "source_name": "Federal Technology Initiative",
                "score": 0.85,
                "keywords": ["technology", "innovation", "development"],
                "funder_name": "Department of Commerce"
            },
            {
                "id": "mock_grant_2", 
                "title": "Healthcare Innovation Grant",
                "description": "Funding for healthcare technology and medical device development",
                "funding_amount": 750000,
                "funding_amount_display": "$750,000",
                "deadline": (datetime.now() + timedelta(days=120)).isoformat(),
                "eligibility_criteria": "Healthcare organizations and medical device companies",
                "category": "Healthcare",
                "source_url": "https://example.gov/grants/health",
                "source_name": "Healthcare Innovation Program",
                "score": 0.78,
                "keywords": ["healthcare", "medical", "innovation"],
                "funder_name": "Department of Health"
            },
            {
                "id": "mock_grant_3",
                "title": "Sustainable Energy Research",
                "description": "Support for renewable energy and clean technology research",
                "funding_amount": 1000000,
                "funding_amount_display": "$1,000,000",
                "deadline": (datetime.now() + timedelta(days=180)).isoformat(),
                "eligibility_criteria": "Research institutions and clean energy companies",
                "category": "Energy",
                "source_url": "https://example.gov/grants/energy",
                "source_name": "Clean Energy Initiative",
                "score": 0.72,
                "keywords": ["energy", "renewable", "sustainability"],
                "funder_name": "Department of Energy"
            }
        ]
    
    async def search_grants(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Mock grant search"""
        self._log_fallback_usage("search_grants")
        await self._simulate_delay()
        
        # Filter mock grants based on criteria
        filtered_grants = []
        search_text = filters.get("search_text", "").lower()
        min_score = filters.get("min_score", 0.0)
        category = filters.get("category")
        
        for grant in self.mock_grants:
            # Text matching
            if search_text:
                text_match = (
                    search_text in grant["title"].lower() or
                    search_text in grant["description"].lower() or
                    any(keyword in search_text for keyword in grant["keywords"])
                )
                if not text_match:
                    continue
            
            # Score filtering
            if grant["score"] < min_score:
                continue
            
            # Category filtering
            if category and grant["category"].lower() != category.lower():
                continue
            
            # Add fallback indicator
            grant_copy = grant.copy()
            grant_copy["fallback"] = True
            filtered_grants.append(grant_copy)
        
        return filtered_grants

class FallbackAnalysisAgent(FallbackService):
    """Fallback implementation for analysis agent"""
    
    def __init__(self, config: Optional[FallbackConfig] = None):
        super().__init__("AnalysisAgent", config)
        
    async def analyze_grant(self, grant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock grant analysis"""
        self._log_fallback_usage("analyze_grant")
        await self._simulate_delay()
        
        # Generate mock analysis scores
        analysis = {
            "grant_id": grant_data.get("id"),
            "research_scores": {
                "sector_relevance": random.uniform(0.6, 0.9),
                "geographic_relevance": random.uniform(0.5, 0.8),
                "operational_alignment": random.uniform(0.7, 0.9)
            },
            "compliance_scores": {
                "business_logic_alignment": random.uniform(0.6, 0.9),
                "feasibility_score": random.uniform(0.7, 0.9),
                "strategic_synergy": random.uniform(0.6, 0.8),
                "final_weighted_score": random.uniform(0.65, 0.85)
            },
            "analysis_summary": {
                "strengths": [
                    "Strong alignment with funding priorities",
                    "Clear commercial potential",
                    "Experienced team capabilities"
                ],
                "concerns": [
                    "Competitive landscape considerations",
                    "Timeline may be ambitious"
                ],
                "recommendations": [
                    "Strengthen partnership strategy",
                    "Consider phased implementation approach"
                ]
            },
            "risk_assessment": {
                "overall_risk": "Medium",
                "technical_risk": "Low",
                "market_risk": "Medium",
                "funding_risk": "Low"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "fallback": True
        }
        
        return analysis
    
    async def batch_analyze_grants(self, grants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Mock batch grant analysis"""
        self._log_fallback_usage("batch_analyze_grants")
        await self._simulate_delay()
        
        results = []
        for grant in grants:
            analysis = await self.analyze_grant(grant)
            results.append(analysis)
        
        return results

# Factory function to create fallback services
def create_fallback_service(service_type: str, config: Optional[FallbackConfig] = None) -> FallbackService:
    """Create appropriate fallback service based on type"""
    fallback_classes = {
        "pinecone": FallbackPineconeClient,
        "perplexity": FallbackPerplexityClient,
        "notification": FallbackNotificationManager,
        "research_agent": FallbackResearchAgent,
        "analysis_agent": FallbackAnalysisAgent
    }
    
    service_class = fallback_classes.get(service_type.lower())
    if not service_class:
        raise ValueError(f"Unknown fallback service type: {service_type}")
    
    return service_class(config)
