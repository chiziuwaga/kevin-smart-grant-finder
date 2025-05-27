from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.dependencies import (
    get_mongo,
    get_pinecone,
    get_perplexity,
    get_notifier,
    get_research_agent,
    get_analysis_agent
)

api_router = APIRouter()

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(db=Depends(get_mongo)):
    """Get overview statistics for the dashboard"""
    stats = await db.get_stats()
    return stats

@api_router.get("/analytics/distribution")
async def get_analytics_distribution(db=Depends(get_mongo)):
    """Get grant distribution by category and deadline"""
    distribution = await db.get_distribution()
    return distribution

@api_router.get("/grants")
async def list_grants(
    min_score: float = 0.0,
    category: Optional[str] = None,
    deadline_before: Optional[str] = None,
    db=Depends(get_mongo),
    pinecone=Depends(get_pinecone)
):
    """Get grants with optional filtering"""
    grants = await db.get_grants(
        min_score=min_score,
        category=category,
        deadline_before=deadline_before
    )
    return grants

@api_router.post("/grants/search")
async def search_grants(
    filters: Dict[str, Any],
    research_agent=Depends(get_research_agent),
    analysis_agent=Depends(get_analysis_agent)
):
    """Advanced grant search with custom filters"""
    results = await research_agent.search_grants(filters)
    analyzed = await analysis_agent.analyze_grants(results)
    return analyzed

@api_router.get("/user/settings")
async def get_user_settings(db=Depends(get_mongo)):
    """Get user notification and schedule settings"""
    settings = await db.get_user_settings()
    return settings or {}

@api_router.put("/user/settings")
async def update_user_settings(
    settings: Dict[str, Any],
    db=Depends(get_mongo),
    notifier=Depends(get_notifier)
):
    """Update user settings and notification preferences"""
    await db.save_user_settings(settings)
    # Update notification settings if changed
    if "notifications" in settings:
        await notifier.update_settings(settings["notifications"])
    return {"status": "success"}

@api_router.post("/system/run-search")
async def trigger_search(
    research_agent=Depends(get_research_agent),
    analysis_agent=Depends(get_analysis_agent),
    notifier=Depends(get_notifier)
):
    """Manually trigger a grant search"""
    results = await research_agent.search_grants({})
    analyzed = await analysis_agent.analyze_grants(results)
    await notifier.notify_new_grants(analyzed)
    return {"status": "success", "new_grants": len(analyzed)}