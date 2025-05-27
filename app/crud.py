from datetime import datetime
from typing import List, Dict, Any, Optional
from utils.mongodb_client import MongoDBClient
from utils.pinecone_client import PineconeClient
from app.models import Grant, SearchRun, UserSettings, GrantFilter

async def fetch_grants(
    db: MongoDBClient,
    pinecone: PineconeClient,
    min_score: float = 0.0,
    category: Optional[str] = None,
    deadline_before: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Fetch grants with optional filtering."""
    query = {"score": {"$gte": min_score}}
    
    if category:
        query["category"] = category
    
    if deadline_before:
        query["deadline"] = {"$lte": datetime.fromisoformat(deadline_before)}
    
    grants = await db.grants.find(query).to_list(length=None)
    return [Grant(**grant).dict() for grant in grants]

async def fetch_stats(db: MongoDBClient) -> Dict[str, Any]:
    """Get dashboard statistics."""
    total = await db.grants.count_documents({})
    high_priority = await db.grants.count_documents({"score": {"$gte": 0.7}})
    categories = await db.grants.distinct("category")
    
    return {
        "total_grants": total,
        "high_priority": high_priority,
        "categories": categories,
        "last_updated": datetime.now().isoformat()
    }

async def fetch_distribution(db: MongoDBClient) -> Dict[str, Any]:
    """Get grant distribution data for analytics."""
    # Get category distribution
    category_pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$project": {"category": "$_id", "count": 1, "_id": 0}},
        {"$sort": {"count": -1}}
    ]
    categories = await db.grants.aggregate(category_pipeline).to_list(length=None)
    
    # Get deadline distribution
    deadline_pipeline = [
        {"$match": {"deadline": {"$exists": True}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m", "date": "$deadline"}},
            "count": {"$sum": 1}
        }},
        {"$project": {"deadline": "$_id", "count": 1, "_id": 0}},
        {"$sort": {"deadline": 1}}
    ]
    deadlines = await db.grants.aggregate(deadline_pipeline).to_list(length=None)
    
    return {
        "categories": categories,
        "deadlines": deadlines
    }

async def save_user_settings(db: MongoDBClient, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Save user notification and search settings."""
    validated = UserSettings(**settings).dict()
    await db.settings.update_one(
        {"_id": "user_settings"},
        {"$set": validated},
        upsert=True
    )
    return validated

async def load_user_settings(db: MongoDBClient) -> Dict[str, Any]:
    """Load user settings."""
    settings = await db.settings.find_one({"_id": "user_settings"})
    if not settings:
        # Return defaults
        return UserSettings().dict()
    return settings

async def search_with_agent(
    db: MongoDBClient, 
    pinecone: PineconeClient,
    research_agent: Any,  # Imported from agents.research_agent
    filters: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Execute grant search with filters using research agent."""
    validated = GrantFilter(**filters)
    
    # Execute search with research agent
    results = await research_agent.search_grants(validated.dict())
    
    # Store results
    if results:
        await db.grants.insert_many(results)
    
    return results

async def run_full_search_cycle(
    db: MongoDBClient,
    pinecone: PineconeClient,
    research_agent: Any,  # Imported from agents.research_agent
) -> List[Dict[str, Any]]:
    """Run a complete grant search cycle."""
    # Execute search with research agent
    results = await research_agent.search_grants({})
    
    if results:
        # Store results
        await db.grants.insert_many(results)
        
        # Record search run
        await db.search_runs.insert_one(
            SearchRun(
                grants_found=len(results),
                high_priority=len([g for g in results if g["score"] >= 0.7])
            ).dict()
        )
    
    return [g for g in results if g["score"] >= 0.7]  # Return only high-priority grants