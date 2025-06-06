from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.dependencies import (
    get_db_session,
    get_pinecone,
    get_notifier,
    get_research_agent,
    get_analysis_agent
)
from app import crud
from app.schemas import (
    Grant,
    GrantSearchFilters,
    DashboardStats,
    DistributionData,
    UserSettings,
    APIResponse,
    PaginatedResponse
)

api_router = APIRouter()

metrics_logger = logging.getLogger("metrics")
audit_logger = logging.getLogger("audit")

def log_api_metrics(endpoint: str, duration: float, status: int, **extra: Dict[str, Any]):
    """Log API metrics in structured format"""
    metrics_logger.info(
        f"API Request: {endpoint}",
        extra={
            "metrics": {
                "endpoint": endpoint,
                "duration_ms": round(duration * 1000, 2),
                "status": status,
                "timestamp": datetime.now().isoformat(),
                **extra
            }
        }
    )

def log_audit_event(event_type: str, details: Dict[str, Any]):
    """Log audit events in structured format"""
    audit_logger.info(
        f"Audit Event: {event_type}",
        extra={
            "extra_fields": {
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                **details
            }
        }
    )

@api_router.get("/dashboard/stats", response_model=APIResponse[DashboardStats])
async def get_dashboard_stats(db: AsyncSession = Depends(get_db_session)):
    """Get overview statistics for the dashboard"""
    try:
        stats = await crud.fetch_stats(db)
        return APIResponse(data=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/analytics/distribution", response_model=APIResponse[DistributionData])
async def get_analytics_distribution(db: AsyncSession = Depends(get_db_session)):
    """Get grant distribution by category and deadline"""
    try:
        distribution = await crud.fetch_distribution(db)
        return APIResponse(data=distribution)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/grants", response_model=PaginatedResponse[Grant])
async def list_grants(
    min_score: float = 0.0,
    category: Optional[str] = None,
    deadline_before: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db_session),
    pinecone_client=Depends(get_pinecone)
):
    """Get grants with optional filtering"""
    try:
        grants, total = await crud.fetch_grants(
            db=db,
            pinecone=pinecone_client,
            min_score=min_score,
            category=category,
            deadline_before=deadline_before,
            page=page,
            page_size=page_size
        )
        return PaginatedResponse(
            items=grants,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/grants/search", response_model=PaginatedResponse[Grant])
async def search_grants_endpoint(
    filters: GrantSearchFilters,
    page: int = 1,
    page_size: int = 20,
    research_agent=Depends(get_research_agent),
    db: AsyncSession = Depends(get_db_session) 
):
    """Advanced grant search with custom filters"""
    try:
        results, total = await research_agent.search_grants(
            filters.dict(by_alias=True),
            page=page,
            page_size=page_size
        )
        return PaginatedResponse(
            items=results,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/user/settings", response_model=APIResponse[UserSettings])
async def get_user_settings_route(db: AsyncSession = Depends(get_db_session)):
    """Get user notification and schedule settings"""
    try:
        settings = await crud.load_user_settings(db)
        return APIResponse(data=settings or {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/user/settings", response_model=APIResponse[UserSettings])
async def update_user_settings_route(
    settings: UserSettings,
    db: AsyncSession = Depends(get_db_session),
    notifier=Depends(get_notifier)
):
    """Update user settings and notification preferences"""
    start_time = datetime.now()
    try:
        settings_dict = settings.dict(by_alias=True)
        updated_settings = await crud.save_user_settings(db, settings_dict)
        if settings.telegram_enabled is not None:
            await notifier.update_settings({"telegram_enabled": settings.telegram_enabled})
            
        # Log audit
        log_audit_event(
            "settings_update",
            {
                "telegram_enabled": settings.telegram_enabled,
                "settings_changed": list(settings_dict.keys())
            }
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        log_api_metrics(
            "/user/settings",
            duration,
            200
        )
        
        return APIResponse(
            data=updated_settings,
            message="Settings updated successfully"
        )
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        log_api_metrics(
            "/user/settings",
            duration,
            500,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/system/run-search")
async def trigger_search(
    db: AsyncSession = Depends(get_db_session),
    pinecone_client = Depends(get_pinecone),
    research_agent = Depends(get_research_agent)
):
    """Manually trigger a grant search and notify."""
    start_time = datetime.now()
    try:
        high_priority_grants = await crud.run_full_search_cycle(
            db=db, 
            pinecone=pinecone_client, 
            research_agent=research_agent
        )
        
        notifier_service = get_notifier()
        if high_priority_grants and notifier_service:
            await notifier_service.notify_new_grants(high_priority_grants)
            result = {"status": "success", "new_grants_notified": len(high_priority_grants)}
        elif not high_priority_grants:
            result = {"status": "success", "message": "No new high-priority grants found."}
        else:
            result = {"status": "success", "new_grants_found": len(high_priority_grants), "notification_status": "Notifier not available or no grants to notify."}
        
        # Log metrics
        duration = (datetime.now() - start_time).total_seconds()
        log_api_metrics(
            "/system/run-search",
            duration,
            200,
            grants_found=len(high_priority_grants) if high_priority_grants else 0,
            notifications_sent=bool(high_priority_grants and notifier_service)
        )
        
        # Log audit
        log_audit_event(
            "grant_search",
            {
                "grants_found": len(high_priority_grants) if high_priority_grants else 0,
                "notifications_sent": bool(high_priority_grants and notifier_service),
                "duration": duration
            }
        )
        
        return result
        
    except Exception as e:        # Log error metrics
        duration = (datetime.now() - start_time).total_seconds()
        log_api_metrics(
            "/system/run-search",
            duration,
            500,
            error=str(e)
        )
        raise

# Simple health endpoint removed - use main app /health endpoint for detailed health check