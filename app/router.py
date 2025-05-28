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
    # analysis_agent=Depends(get_analysis_agent) # Analysis is part of research_agent.search_grants now
    # Or, if you want a separate analysis step via API, AnalysisAgent can be used here.
    # For now, assuming research_agent.search_grants does enough.
    db: AsyncSession = Depends(get_db_session) # Pass session to search_with_agent
):
    """Advanced grant search with custom filters"""
    # The crud.search_with_agent seems more appropriate if it exists and fits
    # If research_agent.search_grants is meant to be the primary search entry point:
    # results = await research_agent.search_grants(filters) 
    # return results
    # Using a hypothetical crud function for consistency, assuming it takes the agent
    # This part needs to align with how search_grants in ResearchAgent is designed
    # and what crud.search_with_agent does.
    # For now, let's assume research_agent.search_grants is the direct way.
    # The crud.search_with_agent takes (db, pinecone, research_agent, filters)
    # We need to ensure research_agent is correctly initialized and passed.
    
    # Option 1: Direct call to agent (if agent handles its own DB session via sessionmaker)
    # results = await research_agent.search_grants(filters)
    # return results

    # Option 2: Using a CRUD function that orchestrates (preferred for consistency)
    # This assumes crud.search_with_agent is designed for this endpoint.
    # The existing crud.search_with_agent stores results, which might be what you want.
    # It expects research_agent to be passed, which is fine.
    # It also expects pinecone to be passed to it, which is not available directly here.
    # Let's adjust to use the injected research_agent and pass the db session to a more direct search if needed.
    # The current crud.search_with_agent is: 
    # async def search_with_agent(db, pinecone, research_agent, filters)
    # This means the dependency for pinecone needs to be available to this endpoint if using that crud.

    # Simpler: Assuming research_agent.search_grants is the main entry point and handles its DB needs.
    # This was the original structure.
    results = await research_agent.search_grants(filters)
    # If analysis is a separate step and needed:
    # analysis_agent = get_analysis_agent(pinecone=Depends(get_pinecone)) # This would need pinecone dependency
    # analyzed = await analysis_agent.analyze_grants(results)
    # return analyzed
    return results # Returning results from research_agent directly for now


@api_router.get("/user/settings")
async def get_user_settings_route(db: AsyncSession = Depends(get_db_session)):
    """Get user notification and schedule settings"""
    settings = await crud.load_user_settings(db) # Use crud function
    return settings or {}

@api_router.put("/user/settings")
async def update_user_settings_route(
    settings_data: Dict[str, Any], # Renamed from settings to avoid conflict
    db: AsyncSession = Depends(get_db_session),
    notifier=Depends(get_notifier)
):
    """Update user settings and notification preferences"""
    updated_settings = await crud.save_user_settings(db, settings_data) # Use crud function
    # Update notification settings if changed
    # The notifier.update_settings might need to be called based on the content of settings_data
    if "telegram_enabled" in settings_data: # Example check
        await notifier.update_settings({"telegram_enabled": settings_data["telegram_enabled"]})
    return {"status": "success", "settings": updated_settings}

@api_router.post("/system/run-search")
async def trigger_search(
    # research_agent=Depends(get_research_agent),
    # analysis_agent=Depends(get_analysis_agent),
    # notifier=Depends(get_notifier),
    db: AsyncSession = Depends(get_db_session), # For crud.run_full_search_cycle
    pinecone_client = Depends(get_pinecone), # For crud.run_full_search_cycle
    research_agent = Depends(get_research_agent) # For crud.run_full_search_cycle
):
    """Manually trigger a grant search and notify."""
    # This endpoint should ideally call a service layer function that encapsulates the whole process.
    # Using crud.run_full_search_cycle as it seems to do most of this.
    
    high_priority_grants = await crud.run_full_search_cycle(
        db=db, 
        pinecone=pinecone_client, 
        research_agent=research_agent
    )
    
    notifier_service = get_notifier() # Get notifier instance
    if high_priority_grants and notifier_service:
        await notifier_service.notify_new_grants(high_priority_grants)
        return {"status": "success", "new_grants_notified": len(high_priority_grants)}
    elif not high_priority_grants:
        return {"status": "success", "message": "No new high-priority grants found."}
    else:
        return {"status": "success", "new_grants_found": len(high_priority_grants), "notification_status": "Notifier not available or no grants to notify."}

# ... (any other routes) ...