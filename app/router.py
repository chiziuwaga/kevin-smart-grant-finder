from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import time
from fastapi.responses import JSONResponse
from sqlalchemy import text

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
            pageSize=page_size
        )        return PaginatedResponse(
            items=grants,
            total=total,
            page=page,
            pageSize=page_size
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
            pageSize=page_size
        )        return PaginatedResponse(
            items=results,
            total=total,
            page=page,
            pageSize=page_size
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

# System endpoints for search run tracking
@api_router.get("/system/last-run")
async def get_last_run(db: AsyncSession = Depends(get_db_session)):
    """Get information about the last search run"""
    try:
        from database.models import SearchRun
        from sqlalchemy import select
        
        # Get the most recent search run
        query = select(SearchRun).order_by(SearchRun.timestamp.desc()).limit(1)
        result = await db.execute(query)
        last_run = result.scalar_one_or_none()
        
        if last_run:
            return {
                "status": "success",
                "start": last_run.timestamp.isoformat(),
                "end": last_run.timestamp.isoformat(),  # For compatibility
                "grants_found": last_run.grants_found or 0,
                "high_priority": last_run.high_priority or 0
            }
        else:
            return {
                "status": "none",
                "message": "No search runs found"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/system/run-history")
async def get_run_history(
    limit: int = 10,
    db: AsyncSession = Depends(get_db_session)
):
    """Get history of recent search runs"""
    try:
        from database.models import SearchRun
        from sqlalchemy import select
        
        # Get recent search runs
        query = select(SearchRun).order_by(SearchRun.timestamp.desc()).limit(limit)
        result = await db.execute(query)
        search_runs = result.scalars().all()
        
        history = []
        for run in search_runs:
            history.append({
                "start": run.timestamp.isoformat(),
                "status": "completed",  # Assuming completed if in database
                "results": run.grants_found or 0,
                "stored": run.grants_found or 0,
                "total": run.grants_found or 0,
                "high_priority": run.high_priority or 0
            })
        
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced health check endpoint
@api_router.get("/health")
async def health_check():
    """Enhanced health check endpoint that checks all critical service statuses"""
    logger = logging.getLogger(__name__)
    
    try:
        from app.services import services
        
        health_status = {
            "status": "initializing", 
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "services": {},
            "uptime": time.time() - (services.start_time or time.time()) if services.start_time else 0
        }
    except Exception as import_error:
        logger.error(f"Health check import error: {import_error}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": f"Import error: {str(import_error)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )    
    try:
        logger.info("Starting detailed health check...")
        
        # Check database
        if services.db_sessionmaker:
            try:
                logger.info("Testing database connection...")
                async with services.db_sessionmaker() as session:
                    await session.execute(text("SELECT 1"))
                health_status["services"]["database"] = "healthy"
                logger.info("Database health check passed")
            except Exception as e:
                logger.error(f"Database health check failed: {str(e)}", exc_info=True)
                health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
        else:
            logger.warning("Database sessionmaker not available")
            health_status["services"]["database"] = {"status": "unhealthy", "error": "No database sessionmaker"}

        # Check Perplexity Client
        if services.perplexity_client:
            try:
                logger.info("Testing Perplexity client...")
                rate_limit = services.perplexity_client.get_rate_limit_status()
                health_status["services"]["perplexity"] = {
                    "status": "healthy",
                    "rate_limit_remaining": rate_limit
                }
                logger.info("Perplexity health check passed")
            except Exception as e:
                logger.error(f"Perplexity client check failed: {str(e)}", exc_info=True)
                health_status["services"]["perplexity"] = {"status": "unhealthy", "error": str(e)}
        else:
            logger.warning("Perplexity client not available")
            health_status["services"]["perplexity"] = {"status": "unhealthy", "error": "No Perplexity client"}        
        
        # Check Pinecone
        if services.pinecone_client:
            try:
                logger.info("Testing Pinecone connection...")
                # Use the verify_connection method
                is_connected = await services.pinecone_client.verify_connection()
                if is_connected:
                    health_status["services"]["pinecone"] = {
                        "status": "healthy",
                        "connection": "verified"
                    }
                    logger.info("Pinecone health check passed")
                else:
                    health_status["services"]["pinecone"] = {
                        "status": "unhealthy",
                        "error": "Connection verification failed"
                    }
                    logger.warning("Pinecone connection verification failed")
            except Exception as e:
                logger.error(f"Pinecone check failed: {str(e)}", exc_info=True)
                health_status["services"]["pinecone"] = {"status": "unhealthy", "error": str(e)}
        else:
            logger.warning("Pinecone client not available")
            health_status["services"]["pinecone"] = {"status": "unhealthy", "error": "No Pinecone client"}
        
        # Determine overall status
        logger.info("Determining overall health status...")
        service_statuses = [
            s.get("status", s) if isinstance(s, dict) else s 
            for s in health_status["services"].values()
        ]
        
        healthy_count = sum(1 for s in service_statuses if s == "healthy")
        total_count = len(service_statuses)
        
        health_status["status"] = (
            "healthy" if all(s == "healthy" for s in service_statuses)
            else "degraded" if any(s == "healthy" for s in service_statuses)
            else "unhealthy"
        )
        
        health_status["health_summary"] = f"{healthy_count}/{total_count} services healthy"
        
        logger.info(f"Health check completed: {health_status['status']} ({health_status['health_summary']})")

        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(
            status_code=status_code,
            content=health_status
        )

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )
