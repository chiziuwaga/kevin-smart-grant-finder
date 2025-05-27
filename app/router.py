from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession  # Added import

from app.dependencies import (
    get_db_session,  # Corrected: was get_mongo
    get_pinecone,
    get_perplexity,
    get_notifier,
    get_research_agent,
    get_analysis_agent
)

api_router = APIRouter()

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db_session)):  # Corrected
    """Get overview statistics for the dashboard"""
    # This will likely fail if db.get_stats() is MongoDB specific
    stats = await db.get_stats()
    return stats

@api_router.get("/analytics/distribution")
async def get_analytics_distribution(db: AsyncSession = Depends(get_db_session)):  # Corrected
    """Get grant distribution by category and deadline"""
    # This will likely fail if db.get_distribution() is MongoDB specific
    distribution = await db.get_distribution()
    return distribution

@api_router.get("/grants")
async def list_grants(
    min_score: float = 0.0,
    category: Optional[str] = None,
    deadline_before: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),  # Corrected
    pinecone=Depends(get_pinecone)
):
    """Get grants with optional filtering"""
    # This will likely fail if db.get_grants() is MongoDB specific
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
async def get_user_settings(db: AsyncSession = Depends(get_db_session)):  # Corrected
    """Get user notification and schedule settings"""
    # This will likely fail if db.get_user_settings() is MongoDB specific
    settings = await db.get_user_settings()
    return settings or {}

@api_router.put("/user/settings")
async def update_user_settings(
    settings: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session),  # Corrected
    notifier=Depends(get_notifier)
):
    """Update user settings and notification preferences"""
    # This will likely fail if db.save_user_settings() is MongoDB specific
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