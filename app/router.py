from fastapi import APIRouter, Depends, HTTPException, Query
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

def log_api_metrics(endpoint: str, duration: float, status: int, **extra: Any):
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

@api_router.get("/grants", response_model=PaginatedEnrichedGrantResponse)
async def list_grants(
    page: int = 1,
    page_size: int = 20,
    sort_by: Optional[str] = "overall_composite_score",
    sort_order: Optional[str] = "desc",
    status_filter: Optional[str] = None,
    min_overall_score: Optional[float] = Query(None, alias="minOverallScore"),
    max_overall_score: Optional[float] = Query(None, alias="maxOverallScore"),
    category: Optional[str] = None,
    searchText: Optional[str] = None, # Renamed from search_query to match frontend
    db: AsyncSession = Depends(get_db_session)
):
    """Get grants with advanced filtering, sorting, and pagination, returning EnrichedGrant objects."""
    start_time_req = time.time()
    try:
        grants, total = await crud.get_grants_list(
            db=db,
            skip=(page - 1) * page_size,
            limit=page_size,
            sort_by=sort_by or "overall_composite_score",
            sort_order=sort_order or "desc",
            status_filter=status_filter,
            min_overall_score=min_overall_score,
            max_overall_score=max_overall_score,
            category=category,
            search_query=searchText  # Pass searchText to the crud function
        )
        duration_req = time.time() - start_time_req
        log_api_metrics("/grants", duration_req, 200, page=page, page_size=page_size, total_items=total)
        return PaginatedEnrichedGrantResponse(
            items=grants,
            total=total,
            page=page,
            pageSize=page_size
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
            pageSize=page_size
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
                # Convert EnrichedGrant objects to dictionaries for the notification service
                grants_dict = [g.model_dump() for g in high_priority_to_notify]
                await notifier_service.notify_new_grants(grants_dict)
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

# Search Run Endpoints

@api_router.get("/search-runs", response_model=Dict[str, Any])
async def get_search_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    run_type: Optional[str] = Query(None, description="Filter by run type: automated, manual, scheduled"),
    status: Optional[str] = Query(None, description="Filter by status: success, failed, partial, in_progress"),
    days_back: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db_session)
):
    """Get paginated search run history with optional filtering."""
    start_time = time.time()
    
    try:
        runs_data, total = await crud.get_search_runs(
            db=db,
            page=page,
            page_size=page_size,
            run_type=run_type,
            status=status,
            days_back=days_back
        )
        
        duration = time.time() - start_time
        log_api_metrics("GET /search-runs", duration, 200, total_results=total)
        
        return {
            "items": runs_data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": (page * page_size) < total,
            "has_prev": page > 1
        }
        
    except Exception as e:
        duration = time.time() - start_time
        log_api_metrics("GET /search-runs", duration, 500, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch search runs: {str(e)}")

@api_router.get("/search-runs/latest-automated", response_model=Dict[str, Any])
async def get_latest_automated_run(db: AsyncSession = Depends(get_db_session)):
    """Get the latest automated search run status."""
    start_time = time.time()
    
    try:
        latest_run = await crud.get_latest_automated_run(db)
        
        duration = time.time() - start_time
        log_api_metrics("GET /search-runs/latest-automated", duration, 200)
        
        if not latest_run:
            return {
                "status": "no_runs",
                "message": "No automated runs found",
                "data": None
            }
        
        # Determine health status
        if latest_run["status"] == "success":
            health = "healthy"
        elif latest_run["status"] == "failed":
            health = "error"
        else:
            health = "warning"
        
        return {
            "status": "success",
            "health": health,
            "data": latest_run,
            "message": f"Latest run: {latest_run['status']}"
        }
        
    except Exception as e:
        duration = time.time() - start_time
        log_api_metrics("GET /search-runs/latest-automated", duration, 500, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch latest automated run: {str(e)}")

@api_router.get("/search-runs/statistics", response_model=Dict[str, Any])
async def get_search_run_statistics(
    days_back: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db_session)
):
    """Get search run statistics for the specified time period."""
    start_time = time.time()
    
    try:
        stats = await crud.get_search_run_statistics(db, days_back)
        
        duration = time.time() - start_time
        log_api_metrics("GET /search-runs/statistics", duration, 200)
        
        return {
            "status": "success",
            "data": stats,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        duration = time.time() - start_time
        log_api_metrics("GET /search-runs/statistics", duration, 500, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch search run statistics: {str(e)}")

# NEW SEARCH MONITORING ENDPOINTS

@api_router.post("/search-runs", response_model=Dict[str, Any])
async def create_search_run(
    search_query: Optional[str] = None,
    search_filters: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new search run to track manual searches."""
    start_time = time.time()
    
    try:
        from database.models import SearchRun
        from datetime import datetime
        
        search_run = SearchRun(
            timestamp=datetime.utcnow(),
            run_type="manual",
            status="in_progress",
            grants_found=0,
            high_priority=0,
            search_query=search_query,
            search_filters=search_filters,
            user_triggered=True
        )
        
        db.add(search_run)
        await db.commit()
        await db.refresh(search_run)
        
        duration = time.time() - start_time
        log_api_metrics("POST /search-runs", duration, 201)
        
        return {
            "status": "success",
            "message": "Search run created successfully",
            "data": {
                "id": search_run.id,
                "timestamp": search_run.timestamp.isoformat(),
                "run_type": search_run.run_type,
                "status": search_run.status
            }
        }
        
    except Exception as e:
        duration = time.time() - start_time
        log_api_metrics("POST /search-runs", duration, 500, error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create search run: {str(e)}")

@api_router.get("/search-runs/live-status/{run_id}", response_model=Dict[str, Any])
async def get_search_run_live_status(
    run_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """Get real-time status of a running search with detailed progress."""
    start_time = time.time()
    
    try:
        from database.models import SearchRun
        from sqlalchemy import select
        
        query = select(SearchRun).where(SearchRun.id == run_id)
        result = await db.execute(query)
        search_run = result.scalar_one_or_none()
        
        if not search_run:
            raise HTTPException(status_code=404, detail="Search run not found")
        
        # Calculate progress based on status and timing
        progress_percentage = 0
        current_step = "Unknown"
        
        status_value = search_run.status.value if hasattr(search_run.status, 'value') else str(search_run.status)
        
        if status_value == "in_progress":
            # Estimate progress based on elapsed time (rough estimate)
            if search_run.timestamp is not None:
                elapsed = (datetime.now() - search_run.timestamp).total_seconds()
                # Assume search takes ~60 seconds on average
                progress_percentage = min(90, (elapsed / 60) * 100)
                current_step = "Searching for grants..."
        elif status_value == "success":
            progress_percentage = 100
            current_step = "Complete"
        elif status_value == "failed":
            progress_percentage = 0
            current_step = "Failed"
        
        duration = time.time() - start_time
        log_api_metrics("GET /search-runs/live-status", duration, 200)
        
        return {
            "status": "success",
            "data": {
                "id": search_run.id,
                "status": search_run.status,
                "progress_percentage": progress_percentage,
                "current_step": current_step,
                "grants_found": search_run.grants_found or 0,
                "high_priority": search_run.high_priority or 0,
                "duration_seconds": search_run.duration_seconds,
                "error_message": search_run.error_message,
                "error_details": search_run.error_details,
                "timestamp": search_run.timestamp.isoformat(),
                "processing_time_ms": search_run.processing_time_ms
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        duration = time.time() - start_time
        log_api_metrics("GET /search-runs/live-status", duration, 500, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch search run status: {str(e)}")

@api_router.get("/search-runs/analytics", response_model=Dict[str, Any])
async def get_search_analytics(
    days_back: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db_session)
):
    """Get search performance analytics and trends."""
    start_time = time.time()
    
    try:
        from database.models import SearchRun
        from sqlalchemy import select, func
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Get overall statistics
        stats_query = select(
            func.count(SearchRun.id).label('total_runs'),
            func.sum(func.case((SearchRun.status == 'success', 1), else_=0)).label('successful_runs'),
            func.sum(func.case((SearchRun.status == 'failed', 1), else_=0)).label('failed_runs'),
            func.avg(SearchRun.grants_found).label('avg_grants_found'),
            func.avg(SearchRun.duration_seconds).label('avg_duration'),
            func.max(SearchRun.grants_found).label('max_grants_found'),
            func.min(SearchRun.grants_found).label('min_grants_found')
        ).where(SearchRun.created_at >= cutoff_date)
        
        stats_result = await db.execute(stats_query)
        stats = stats_result.first()
        
        # Get daily trends
        daily_query = select(
            func.date(SearchRun.created_at).label('date'),
            func.count(SearchRun.id).label('runs'),
            func.sum(func.case((SearchRun.status == 'success', 1), else_=0)).label('successes'),
            func.avg(SearchRun.grants_found).label('avg_grants')
        ).where(
            SearchRun.created_at >= cutoff_date
        ).group_by(
            func.date(SearchRun.created_at)
        ).order_by(
            func.date(SearchRun.created_at)
        )
        
        daily_result = await db.execute(daily_query)
        daily_trends = [
            {
                "date": row.date.isoformat(),
                "runs": row.runs,
                "success_rate": (row.successes / row.runs * 100) if row.runs > 0 else 0,
                "avg_grants": float(row.avg_grants) if row.avg_grants else 0
            }
            for row in daily_result
        ]
        
        # Get error frequency analysis
        error_query = select(
            SearchRun.error_message,
            func.count(SearchRun.id).label('count')
        ).where(
            SearchRun.created_at >= cutoff_date,
            SearchRun.status == 'failed',
            SearchRun.error_message.isnot(None)
        ).group_by(
            SearchRun.error_message
        ).order_by(
            func.count(SearchRun.id).desc()
        ).limit(10)
        
        error_result = await db.execute(error_query)
        common_errors = [
            {
                "error": row.error_message,
                "count": row.count
            }
            for row in error_result
        ]
        
        duration = time.time() - start_time
        log_api_metrics("GET /search-runs/analytics", duration, 200)
        
        return {
            "status": "success",
            "data": {
                "period_days": days_back,
                "summary": {
                    "total_runs": getattr(stats, 'total_runs', 0) or 0,
                    "successful_runs": getattr(stats, 'successful_runs', 0) or 0,
                    "failed_runs": getattr(stats, 'failed_runs', 0) or 0,
                    "success_rate": ((getattr(stats, 'successful_runs', 0) or 0) / (getattr(stats, 'total_runs', 1) or 1)) * 100,
                    "avg_grants_found": round(float(getattr(stats, 'avg_grants_found', 0) or 0), 1),
                    "avg_duration_seconds": round(float(getattr(stats, 'avg_duration', 0) or 0), 2),
                    "max_grants_found": getattr(stats, 'max_grants_found', 0) or 0,
                    "min_grants_found": getattr(stats, 'min_grants_found', 0) or 0
                },
                "daily_trends": daily_trends,
                "common_errors": common_errors
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        duration = time.time() - start_time
        log_api_metrics("GET /search-runs/analytics", duration, 500, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch search analytics: {str(e)}")

@api_router.get("/system/scheduler-status", response_model=Dict[str, Any])
async def get_scheduler_status(db: AsyncSession = Depends(get_db_session)):
    """Check Heroku scheduler status and automated run health."""
    start_time = time.time()
    
    try:
        from database.models import SearchRun
        from sqlalchemy import select, func
        from datetime import datetime, timedelta
        
        # Get last automated run
        latest_automated_query = select(SearchRun).where(
            SearchRun.run_type == 'automated'
        ).order_by(SearchRun.created_at.desc()).limit(1)
        
        latest_result = await db.execute(latest_automated_query)
        latest_run = latest_result.scalar_one_or_none()
        
        # Calculate expected next run (assuming twice weekly: Monday & Thursday at 10 AM)
        now = datetime.now()
        next_run_estimate = None
        
        # Simple logic for twice weekly schedule
        if now.weekday() < 1:  # Before Monday
            next_run_estimate = now.replace(hour=10, minute=0, second=0, microsecond=0)
            next_run_estimate = next_run_estimate.replace(day=now.day + (1 - now.weekday()))
        elif now.weekday() < 4:  # Before Thursday
            next_run_estimate = now.replace(hour=10, minute=0, second=0, microsecond=0)
            next_run_estimate = next_run_estimate.replace(day=now.day + (4 - now.weekday()))
        else:  # After Thursday, next Monday
            days_to_monday = 7 - now.weekday()
            next_run_estimate = now + timedelta(days=days_to_monday)
            next_run_estimate = next_run_estimate.replace(hour=10, minute=0, second=0, microsecond=0)
        
        # Check if automated runs are on schedule
        scheduler_health = "healthy"
        issues = []
        
        if latest_run:
            time_since_last = now - latest_run.created_at
            
            # If more than 4 days since last automated run, flag as issue
            if time_since_last.days > 4:
                scheduler_health = "warning"
                issues.append(f"Last automated run was {time_since_last.days} days ago")
            
            # If last run failed
            latest_status = latest_run.status.value if hasattr(latest_run.status, 'value') else str(latest_run.status)
            if latest_status == 'failed':
                scheduler_health = "error"
                issues.append(f"Last automated run failed: {latest_run.error_message}")
        else:
            scheduler_health = "warning"
            issues.append("No automated runs found in database")
        
        # Get recent automated run statistics
        week_ago = now - timedelta(days=7)
        recent_runs_query = select(
            func.count(SearchRun.id).label('total'),
            func.sum(func.case((SearchRun.status == 'success', 1), else_=0)).label('successful')
        ).where(
            SearchRun.run_type == 'automated',
            SearchRun.created_at >= week_ago
        )
        
        recent_result = await db.execute(recent_runs_query)
        recent_stats = recent_result.first()
        
        duration = time.time() - start_time
        log_api_metrics("GET /system/scheduler-status", duration, 200)
        
        return {
            "status": "success",
            "scheduler_health": scheduler_health,
            "issues": issues,
            "data": {
                "last_automated_run": {
                    "timestamp": latest_run.created_at.isoformat() if latest_run else None,
                    "status": latest_run.status if latest_run else None,
                    "grants_found": latest_run.grants_found if latest_run else None,
                    "error_message": latest_run.error_message if latest_run else None
                },
                "next_expected_run": next_run_estimate.isoformat() if next_run_estimate else None,
                "recent_week_stats": {
                    "total_runs": getattr(recent_stats, 'total', 0) or 0,
                    "successful_runs": getattr(recent_stats, 'successful', 0) or 0,
                    "success_rate": ((getattr(recent_stats, 'successful', 0) or 0) / (getattr(recent_stats, 'total', 1) or 1)) * 100
                },
                "configuration": {
                    "schedule": "Twice weekly (Monday & Thursday at 10 AM)",
                    "type": "Heroku Scheduler",
                    "command": "python run_grant_search.py"
                }
            }
        }
        
    except Exception as e:
        duration = time.time() - start_time
        log_api_metrics("GET /system/scheduler-status", duration, 500, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch scheduler status: {str(e)}")
