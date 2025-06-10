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
    get_analysis_agent,
    get_perplexity, # Fixed function name
    get_db_sessionmaker # Added for run_full_search_cycle
)
from app import crud
from app.schemas import (
    Grant, # This might be deprecated in favor of EnrichedGrant for responses
    EnrichedGrant, # Added
    GrantSearchFilters,
    DashboardStats,
    DistributionData,
    UserSettings,
    APIResponse,
    PaginatedResponse,
    SingleEnrichedGrantResponse, # Added
    PaginatedEnrichedGrantResponse, # Added
    ApplicationHistoryCreate, # Added
    ApplicationHistoryResponse # Added
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

@api_router.get("/grants", response_model=PaginatedEnrichedGrantResponse) # Changed to PaginatedEnrichedGrantResponse
async def list_grants(
    # min_score: float = 0.0, # Replaced by min_overall_score
    # category: Optional[str] = None, # Replaced by more specific filters if needed or search_query
    # deadline_before: Optional[str] = None, # Can be part of a more generic date filter if needed
    page: int = 1,
    page_size: int = 20,
    sort_by: Optional[str] = "overall_composite_score",
    sort_order: Optional[str] = "desc",
    status_filter: Optional[str] = None,
    min_overall_score: Optional[float] = None,
    search_query: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
    # pinecone_client=Depends(get_pinecone) # Not directly used by crud.get_grants_list
):
    """Get grants with advanced filtering, sorting, and pagination, returning EnrichedGrant objects."""
    start_time_req = time.time()
    try:
        grants, total = await crud.get_grants_list(
            db=db,
            skip=(page - 1) * page_size,
            limit=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            status_filter=status_filter,
            min_overall_score=min_overall_score,
            search_query=search_query
        )
        duration_req = time.time() - start_time_req
        log_api_metrics("/grants", duration_req, 200, page=page, page_size=page_size, total_items=total)
        return PaginatedEnrichedGrantResponse(
            items=grants,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        duration_req = time.time() - start_time_req
        log_api_metrics("/grants", duration_req, 500, error=str(e))
        logging.error(f"Error in /grants endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/grants/{grant_id}", response_model=SingleEnrichedGrantResponse) # Changed to SingleEnrichedGrantResponse
async def get_grant_detail(
    grant_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a single grant by its ID, returning an EnrichedGrant object."""
    start_time_req = time.time()
    try:
        grant = await crud.get_grant_by_id(db=db, grant_id=grant_id)
        if not grant:
            duration_req = time.time() - start_time_req
            log_api_metrics("/grants/{grant_id}", duration_req, 404, grant_id=grant_id)
            raise HTTPException(status_code=404, detail="Grant not found")
        duration_req = time.time() - start_time_req
        log_api_metrics("/grants/{grant_id}", duration_req, 200, grant_id=grant_id)
        return SingleEnrichedGrantResponse(data=grant)
    except HTTPException: # Re-raise HTTPException to preserve status code
        raise
    except Exception as e:
        duration_req = time.time() - start_time_req
        log_api_metrics("/grants/{grant_id}", duration_req, 500, grant_id=grant_id, error=str(e))
        logging.error(f"Error in /grants/{{grant_id}} endpoint for ID {grant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/grants/search", response_model=PaginatedEnrichedGrantResponse) # Changed to PaginatedEnrichedGrantResponse
async def search_grants_endpoint(
    filters: GrantSearchFilters, # GrantSearchFilters might need update for EnrichedGrant fields
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db_session)
    # research_agent=Depends(get_research_agent) # This endpoint should now use crud.get_grants_list
):
    """Advanced grant search using filters, returning EnrichedGrant objects."""
    # This endpoint now mirrors /grants but with a POST body for filters.
    # It will use the same crud.get_grants_list function.
    # The GrantSearchFilters schema might need to be aligned with parameters of get_grants_list.
    start_time_req = time.time()
    try:
        # Adapt GrantSearchFilters to the parameters of crud.get_grants_list
        # For now, we assume GrantSearchFilters contains fields like search_text, min_score (min_overall_score)
        # and potentially status_filter, sort_by, sort_order if added to GrantSearchFilters.
        grants, total = await crud.get_grants_list(
            db=db,
            skip=(page - 1) * page_size,
            limit=page_size,
            sort_by="overall_composite_score", # Default or from filters
            sort_order="desc", # Default or from filters
            status_filter=None, # Or from filters.category if mapped
            min_overall_score=filters.min_score,
            search_query=filters.search_text
        )
        duration_req = time.time() - start_time_req
        log_api_metrics("/grants/search", duration_req, 200, page=page, page_size=page_size, total_items=total)
        return PaginatedEnrichedGrantResponse(
            items=grants,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        duration_req = time.time() - start_time_req
        log_api_metrics("/grants/search", duration_req, 500, error=str(e))
        logging.error(f"Error in /grants/search endpoint: {e}", exc_info=True)
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
    # db: AsyncSession = Depends(get_db_session), # db_sessionmaker is used by run_full_search_cycle
    db_sessionmaker = Depends(get_db_sessionmaker),
    perplexity_client = Depends(get_perplexity),
    pinecone_client = Depends(get_pinecone)
    # research_agent = Depends(get_research_agent) # Not needed directly, agents are instantiated in crud
):
    """Manually trigger a full grant search and enrichment cycle."""
    start_time = datetime.now()
    try:
        # crud.run_full_search_cycle now takes db_sessionmaker, perplexity_client, pinecone_client
        fully_analyzed_grants = await crud.run_full_search_cycle(
            db_sessionmaker=db_sessionmaker, 
            perplexity_client=perplexity_client, 
            pinecone_client=pinecone_client
        )
        
        notifier_service = get_notifier() # Assuming get_notifier() is correctly set up
        notified_count = 0
        if fully_analyzed_grants and notifier_service:
            # Assuming notifier_service.notify_new_grants expects List[EnrichedGrant]
            # And we only want to notify for high-priority ones
            high_priority_to_notify = [g for g in fully_analyzed_grants if g.overall_composite_score is not None and g.overall_composite_score >= 0.7]
            if high_priority_to_notify:
                await notifier_service.notify_new_grants(high_priority_to_notify)
                notified_count = len(high_priority_to_notify)
            result_message = f"Search completed. {len(fully_analyzed_grants)} grants processed. {notified_count} high-priority grants notified."
        elif not fully_analyzed_grants:
            result_message = "Search completed. No grants found or processed."
        else: # Grants found, but no notifier or no high-priority ones
            result_message = f"Search completed. {len(fully_analyzed_grants)} grants processed. Notifier not available or no high-priority grants to notify."

        result = {"status": "success", "message": result_message, "grants_processed": len(fully_analyzed_grants), "notified_count": notified_count}
        
        duration = (datetime.now() - start_time).total_seconds()
        log_api_metrics(
            "/system/run-search",
            duration,
            200,
            grants_processed=len(fully_analyzed_grants),
            notifications_sent=notified_count > 0
        )
        log_audit_event(
            "triggered_grant_search_cycle",
            {
                "grants_processed": len(fully_analyzed_grants),
                "notified_count": notified_count,
                "duration": duration
            }
        )
        return result
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        log_api_metrics("/system/run-search", duration, 500, error=str(e))
        logging.error(f"Error in /system/run-search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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
                "timestamp": datetime.utcnow().isoformat()            }
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

# Endpoint for Application History CRUD
@api_router.post("/applications/feedback", response_model=APIResponse[ApplicationHistoryResponse], status_code=201)
async def create_application_feedback(
    application_data: ApplicationHistoryCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Submit feedback for a grant application."""
    start_time_req = time.time()
    try:
        # TODO: Add user_id to application_data if implementing multi-user support
        # For now, assuming a single-user context or user_id is handled in crud or default.
        # Example: application_data_dict = application_data.dict()
        # application_data_dict["user_id"] = "default_user" # Or from auth
        
        created_feedback = await crud.create_application_history_entry(
            db=db, 
            application_history_data=application_data
        )
        duration_req = time.time() - start_time_req
        log_api_metrics("/applications/feedback", duration_req, 201, grant_id=created_feedback.grant_id)
        log_audit_event(
            "application_feedback_created",
            {
                "application_history_id": created_feedback.id,
                "grant_id": created_feedback.grant_id,
                "status": created_feedback.status
            }
        )
        return APIResponse(data=created_feedback, message="Application feedback submitted successfully.", status="created")
    except Exception as e:
        duration_req = time.time() - start_time_req
        log_api_metrics("/applications/feedback", duration_req, 500, error=str(e))
        logging.error(f"Error in /applications/feedback endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# TODO: Add GET, PUT, DELETE endpoints for ApplicationHistory if needed as per Task 5.2
# For example:
# @api_router.get("/applications/feedback/{history_id}", response_model=APIResponse[ApplicationHistoryResponse])
# async def get_application_feedback_entry(...)

# @api_router.get("/grants/{grant_id}/feedback", response_model=APIResponse[List[ApplicationHistoryResponse]])
# async def get_feedback_for_grant(...)
