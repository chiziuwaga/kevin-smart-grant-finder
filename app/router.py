from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_db_session,
    get_pinecone, # Keep if crud functions need it directly, or if agents passed to crud need it
    # get_perplexity, # Not directly used by router if agents are used via crud or if crud handles it
    get_notifier,
    get_research_agent,
    get_analysis_agent
)
# Import CRUD functions
from app import crud

api_router = APIRouter()

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db_session)):
    """Get overview statistics for the dashboard"""
    stats = await crud.fetch_stats(db) # Use crud function
    return stats

@api_router.get("/analytics/distribution")
async def get_analytics_distribution(db: AsyncSession = Depends(get_db_session)):
    """Get grant distribution by category and deadline"""
    distribution = await crud.fetch_distribution(db) # Use crud function
    return distribution

@api_router.get("/grants")
async def list_grants(
    min_score: float = 0.0,
    category: Optional[str] = None,
    deadline_before: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
    pinecone_client=Depends(get_pinecone) # Renamed for clarity, pinecone_client is the actual object
):
    """Get grants with optional filtering"""
    # Ensure crud.fetch_grants matches these parameters or adapt the call
    grants = await crud.fetch_grants(
        db=db, 
        pinecone=pinecone_client,  # Pass the actual Pinecone client
        min_score=min_score, 
        category=category, 
        deadline_before=deadline_before
    )
    return grants

@api_router.post("/grants/search")
async def search_grants_endpoint( # Renamed to avoid conflict with imported search_grants if any
    filters: Dict[str, Any],
    research_agent=Depends(get_research_agent),
    db: AsyncSession = Depends(get_db_session) 
):
    """Advanced grant search with custom filters"""
    results = await research_agent.search_grants(filters)
    return results


@api_router.get("/user/settings")
async def get_user_settings_route(db: AsyncSession = Depends(get_db_session)):
    """Get user notification and schedule settings"""
    settings = await crud.load_user_settings(db) # Use crud function
    return settings or {}

@api_router.put("/user/settings")
async def update_user_settings_route(
    settings_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    notifier=Depends(get_notifier)
):
    """Update user settings and notification preferences"""
    updated_settings = await crud.save_user_settings(db, settings_data)
    if "telegram_enabled" in settings_data:
        await notifier.update_settings({"telegram_enabled": settings_data["telegram_enabled"]})
    return {"status": "success", "settings": updated_settings}

@api_router.post("/system/run-search")
async def trigger_search(
    db: AsyncSession = Depends(get_db_session),
    pinecone_client = Depends(get_pinecone),
    research_agent = Depends(get_research_agent)
):
    """Manually trigger a grant search and notify."""
    high_priority_grants = await crud.run_full_search_cycle(
        db=db, 
        pinecone=pinecone_client, 
        research_agent=research_agent
    )
    
    notifier_service = get_notifier()
    if high_priority_grants and notifier_service:
        await notifier_service.notify_new_grants(high_priority_grants)
        return {"status": "success", "new_grants_notified": len(high_priority_grants)}
    elif not high_priority_grants:
        return {"status": "success", "message": "No new high-priority grants found."}
    else:
        return {"status": "success", "new_grants_found": len(high_priority_grants), "notification_status": "Notifier not available or no grants to notify."}

# ... (any other routes) ...