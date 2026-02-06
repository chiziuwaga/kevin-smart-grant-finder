import logging # Added logger
import time # Added time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import json
from sqlalchemy import select, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker 
from sqlalchemy.orm import selectinload

from database.models import Grant as DBGrant, Analysis, SearchRun, UserSettings, ApplicationHistory # Added ApplicationHistory
from utils.pinecone_client import PineconeClient # Added back PineconeClient import
from app.schemas import EnrichedGrant, ResearchContextScores, ComplianceScores, GrantSourceDetails, ApplicationHistoryCreate # Added ApplicationHistoryCreate
from app.duplicate_detection import check_duplicate_grant, update_duplicate_grant # Added duplicate detection
# It's generally better to import specific classes if you're not using the whole module via alias.
# However, the generated CRUD functions used models. and schemas. prefixes, so let's add module imports for them.
from database import models
from app import schemas

from agents.research_agent import ResearchAgent
from agents.compliance_agent import ComplianceAnalysisAgent
from services.deepseek_client import DeepSeekClient
from config.settings import get_settings # Changed from settings to get_settings()

logger = logging.getLogger(__name__) # Added logger instance
settings = get_settings() # Initialize settings

async def fetch_grants(
    db: AsyncSession,
    pinecone: PineconeClient,
    min_score: float = 0.0,
    category: Optional[str] = None,
    deadline_before: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> tuple[List[Dict[str, Any]], int]:
    """
    Fetch grants with optional filtering using SQLAlchemy.
    Returns a tuple of (grants_list, total_count).    """
    query = select(DBGrant).outerjoin(Analysis).options(selectinload(DBGrant.analyses))
    
    if min_score > 0:
        # This filter assumes 'score' is on the Analysis table and there's a join.
        # If 'overall_composite_score' on DBGrant should be used, adjust accordingly.
        # For now, sticking to original logic which might be for a different 'score'.
        query = query.filter(Analysis.final_score >= min_score) # Assuming Analysis.final_score is the target
    
    if category:
        # Assuming 'category' refers to 'identified_sector' on DBGrant
        query = query.filter(DBGrant.identified_sector == category)
    
    if deadline_before:
        deadline = datetime.fromisoformat(deadline_before)
        query = query.filter(DBGrant.deadline <= deadline) # Using deadline from DBGrant
    
    count_query = select(func.count()).select_from(query.subquery())
    total_count_result = await db.execute(count_query)
    total = total_count_result.scalar_one_or_none() or 0
    
    query = query.order_by(DBGrant.deadline.asc()) # Using deadline
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    grants_models = result.scalars().all()
    grants_data = []
    for grant_model in grants_models:
        score_value = 0.0  # Default score value
        # Attempt to get score from related Analysis table if it exists
        if grant_model.analyses and len(grant_model.analyses) > 0:
            # Assuming the first analysis record is relevant, and it has a 'final_score'
            if grant_model.analyses[0].final_score is not None:
                score_value = grant_model.analyses[0].final_score
        elif hasattr(grant_model, 'overall_composite_score') and grant_model.overall_composite_score is not None:
            # Fallback to overall_composite_score on the grant itself if no analysis score
            score_value = grant_model.overall_composite_score

        # Eligibility criteria: DBGrant does not have a direct 'eligibility' field anymore.
        # It has 'eligibility_summary_llm'. We'll use that.
        eligibility_str = grant_model.eligibility_summary_llm
        
        grant_dict = {
            "id": str(grant_model.id),
            "title": grant_model.title,
            "description": grant_model.description,
            # funding_amount: Use funding_amount_display or exact from DBGrant
            "funding_amount": grant_model.funding_amount_exact or grant_model.funding_amount_display,
            "deadline": grant_model.deadline.isoformat() if grant_model.deadline is not None else None,
            "eligibility_criteria": eligibility_str,
            "category": grant_model.identified_sector, # Mapped from identified_sector
            "source_url": grant_model.source_url,
            "source_name": grant_model.source_name, # Using source_name from DBGrant
            "score": score_value # Use the determined score
        }
        grants_data.append(grant_dict)
    
    return grants_data, total

async def fetch_stats(db: AsyncSession) -> Dict[str, Any]:
    """Get dashboard statistics using SQLAlchemy."""
    total_query = select(func.count()).select_from(DBGrant)
    total_result = await db.execute(total_query)
    total_grants = total_result.scalar_one_or_none() or 0

    # Average score: Use overall_composite_score from DBGrant
    avg_score_query = select(func.avg(DBGrant.overall_composite_score)).select_from(DBGrant)
    avg_score_result = await db.execute(avg_score_query)
    average_score = round(float(avg_score_result.scalar_one_or_none() or 0.0), 2)

    current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_query = (
        select(func.count())
        .select_from(DBGrant)
        .filter(DBGrant.created_at >= current_month_start)
    )
    monthly_result = await db.execute(monthly_query)
    grants_this_month = monthly_result.scalar_one_or_none() or 0
    
    upcoming_deadline_query = (
        select(func.count())
        .select_from(DBGrant)
        .filter(            DBGrant.deadline >= datetime.now(),
            DBGrant.deadline <= datetime.now() + timedelta(days=30)
        )
    )
    upcoming_result = await db.execute(upcoming_deadline_query)
    upcoming_deadlines = upcoming_result.scalar_one_or_none() or 0

    return {
        "totalGrants": total_grants,
        "averageScore": average_score,
        "grantsThisMonth": grants_this_month,
        "upcomingDeadlines": upcoming_deadlines
    }

async def fetch_distribution(db: AsyncSession) -> Dict[str, List[Dict[str, Any]]]:
    """Get analytics distribution using SQLAlchemy, formatted for frontend charts."""
    category_query = (
        select(
            DBGrant.identified_sector, 
            func.count(DBGrant.id).label('count')
        )
        .filter(DBGrant.identified_sector.isnot(None))
        .group_by(DBGrant.identified_sector)
    )
    
    category_result = await db.execute(category_query)
    categories = [
        {"name": str(cat or "Uncategorized"), "value": int(count)}
        for cat, count in category_result.all()
    ]

    deadline_query = (
        select(
            func.date_trunc('month', DBGrant.deadline).label('month'),
            func.count(DBGrant.id).label('count')
        )
        .filter(DBGrant.deadline.isnot(None))
        .group_by(text('month'))
        .order_by(text('month'))
    )
    
    deadline_result = await db.execute(deadline_query)
    deadlines = [
        {"name": row[0].strftime('%Y-%m'), "count": int(row[1])}
        for row in deadline_result.all()
        if row[0]
    ]

    score_query = (
        select(
            func.floor(DBGrant.overall_composite_score / 10.0).label('range_start'), 
            func.count(DBGrant.id).label('count')
        )
        .select_from(DBGrant)
        .filter(DBGrant.overall_composite_score.isnot(None))
        .group_by(text('range_start'))
        .order_by(text('range_start'))
    )
    
    score_result = await db.execute(score_query)
    scores = []
    for row in score_result.all():
        if row[0] is not None: 
            range_start_val = int(float(row[0]) * 10) 
            range_end_val = range_start_val + 9 
            scores.append({"name": f"{range_start_val}-{range_end_val}", "count": int(row[1])})

    return {
        "categories": categories,
        "deadlines": deadlines,
        "scores": scores
    }

async def save_user_settings(db: AsyncSession, settings_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save user settings using SQLAlchemy."""
    query = select(UserSettings).limit(1)
    result = await db.execute(query)
    user_settings = result.scalar_one_or_none()
    
    field_mapping = {
        "emailNotifications": "email_notifications",
        "minimumScore": "minimum_score", 
        "searchFrequency": "schedule_frequency",
        "categories": "notify_categories"
    }
    
    if user_settings:
        for key, value in settings_data.items():
            db_field = field_mapping.get(key, key)
            if hasattr(user_settings, db_field):
                setattr(user_settings, db_field, value)
    else:
        mapped_data = {}
        for key, value in settings_data.items():
            db_field = field_mapping.get(key, key)
            mapped_data[db_field] = value
        user_settings = UserSettings(**mapped_data)
        db.add(user_settings)
    
    await db.commit()
    await db.refresh(user_settings)
    return user_settings.to_dict()

async def load_user_settings(db: AsyncSession) -> Dict[str, Any]:
    """Load user settings using SQLAlchemy."""
    query = select(UserSettings).limit(1)
    result = await db.execute(query)
    user_settings = result.scalar_one_or_none()
    
    if not user_settings:
        user_settings = UserSettings()
        db.add(user_settings)
        await db.commit()
        await db.refresh(user_settings)
    
    return user_settings.to_dict()

# search_with_agent can be removed or commented out if fully replaced by run_full_search_cycle
# async def search_with_agent(...):
#    ...

async def run_full_search_cycle(
    db_sessionmaker: async_sessionmaker, 
    deepseek_client: DeepSeekClient, 
    pinecone_client: PineconeClient 
) -> List[EnrichedGrant]:
    """Run a complete grant search cycle, including research and compliance analysis."""
    logger.info("Starting full search cycle...")
    start_time_cycle = time.time()
    research_agent_instance = None # Initialize to None
    try:        research_agent_instance = ResearchAgent(
            deepseek_client=deepseek_client,
            db_session_maker=db_sessionmaker,
            config_path=settings.CONFIG_DIR # Corrected from config_dir to config_path
        )
    except Exception as e:
        logger.error(f"Failed to initialize ResearchAgent: {e}", exc_info=True)
        # Record a search run with 0 grants if agent init fails
        async with db_sessionmaker() as session:
            try:
                search_run = SearchRun(
                    timestamp=datetime.utcnow(),
                    grants_found=0,
                    high_priority=0,
                    search_filters=json.dumps({}) # Empty filters as search didn't run
                )
                session.add(search_run)
                await session.commit()
                logger.info(f"Search run recorded (ResearchAgent init failed): {search_run.id}")
            except Exception as db_e:
                logger.error(f"Error recording search run after ResearchAgent init failure: {db_e}", exc_info=True)
                await session.rollback()
        return [] # Return empty list if research agent fails to initialize
    
    try:
        compliance_agent_instance = ComplianceAnalysisAgent(
            compliance_config_path=settings.COMPLIANCE_RULES_CONFIG_PATH,
            profile_config_path=settings.KEVIN_PROFILE_CONFIG_PATH,
            deepseek_client=deepseek_client
        )
    except Exception as e:
        logger.error(f"Failed to initialize ComplianceAnalysisAgent: {e}", exc_info=True)
        logger.warning("Continuing with research results only (no compliance analysis)")
        # Continue with research grants only, without compliance analysis
        compliance_agent_instance = None

    logger.info("Running ResearchAgent to discover and perform initial scoring on grants...")
    initial_filters = {} 
    
    researched_grants: List[EnrichedGrant] = await research_agent_instance.search_grants(initial_filters)
    logger.info(f"ResearchAgent found {len(researched_grants)} grants with initial research scores.")

    if not researched_grants:
        logger.info("No grants found by ResearchAgent. Ending search cycle.")
        async with db_sessionmaker() as session:
            try:
                search_run = SearchRun(
                    timestamp=datetime.utcnow(),
                    grants_found=0,
                    high_priority=0,
                    search_filters=json.dumps(initial_filters)
                )
                session.add(search_run)
                await session.commit()
                logger.info(f"Search run recorded with ID: {search_run.id} (0 grants found).")
            except Exception as e:
                logger.error(f"Error recording search run (0 grants): {e}", exc_info=True)
                await session.rollback()
        return []

    # Only run compliance analysis if the compliance agent was successfully initialized
    if compliance_agent_instance is not None:
        logger.info("Running ComplianceAnalysisAgent for detailed compliance and final scoring...")
        fully_analyzed_grants: List[EnrichedGrant] = []
        for grant_to_analyze in researched_grants:
            try:
                if grant_to_analyze.compliance_scores is None:
                    grant_to_analyze.compliance_scores = ComplianceScores() # Initialize if None

                # The ComplianceAnalysisAgent's analyze_grant method is expected to populate
                # grant_to_analyze.overall_composite_score and grant_to_analyze.record_status
                analyzed_grant = await compliance_agent_instance.analyze_grant(grant_to_analyze)
                fully_analyzed_grants.append(analyzed_grant)
                logger.debug(f"Compliance analysis complete for grant: {analyzed_grant.title if analyzed_grant.title else 'N/A'}")
            except Exception as e:
                logger.error(f"Error during compliance analysis for grant {grant_to_analyze.title if grant_to_analyze.title else 'N/A'}: {e}", exc_info=True)
                continue
        
        logger.info(f"ComplianceAnalysisAgent processed {len(fully_analyzed_grants)} grants.")
    else:
        logger.warning("Skipping compliance analysis due to ComplianceAnalysisAgent initialization failure")
        fully_analyzed_grants = researched_grants  # Use research grants without compliance analysis

    saved_grants_count = 0
    processed_grants_for_return: List[EnrichedGrant] = [] # New list to store results of create_or_update_grant
    async with db_sessionmaker() as session: 
        logger.info(f"Saving/updating {len(fully_analyzed_grants)} grants to the database...")
        for enriched_grant_data in fully_analyzed_grants:
            try:
                # Convert EnrichedGrant to dict for database saving
                grant_dict = enriched_grant_data.dict(exclude_none=True) if hasattr(enriched_grant_data, 'dict') else enriched_grant_data.__dict__
                
                # Call the dedicated create_or_update_grant function
                saved_grant = await create_or_update_grant(session, grant_dict)
                if saved_grant:
                    # Convert saved grant back to EnrichedGrant for return
                    enriched_saved = safe_convert_to_enriched_grant(saved_grant)
                    if enriched_saved:
                        processed_grants_for_return.append(enriched_saved)
                    saved_grants_count += 1
                    # Safe access to title attribute
                    grant_title = getattr(saved_grant, 'title', None)
                    title_display = grant_title[:50] if grant_title else 'N/A'
                    logger.info(f"Successfully saved/updated grant via dedicated function: {title_display} (ID: {saved_grant.id})")
                else:
                    logger.error(f"Failed to save/update grant: {enriched_grant_data.title[:50] if enriched_grant_data.title else 'N/A'} using dedicated function.")
            except Exception as e:
                logger.error(f"Error during save/update via dedicated function for grant {enriched_grant_data.title if enriched_grant_data.title else 'N/A'}: {e}", exc_info=True)
                # Ensure rollback is handled within create_or_update_grant or here if necessary,
                # but create_or_update_grant already handles its own rollback on commit failure.
                # await session.rollback() # This might not be needed if create_or_update_grant handles it.
                continue 

        logger.info(f"Successfully processed {saved_grants_count} grants for saving/updating to the database.")

        try:
            search_run = SearchRun(
                timestamp=datetime.utcnow(),
                grants_found=len(fully_analyzed_grants), 
                high_priority=len([g for g in fully_analyzed_grants if g.overall_composite_score is not None and g.overall_composite_score >= 0.7]), 
                search_filters=json.dumps(initial_filters) 
            )
            session.add(search_run)
            await session.commit()
            logger.info(f"Search run recorded with ID: {search_run.id}")
        except Exception as e:
            logger.error(f"Error recording search run: {e}", exc_info=True)
            await session.rollback()


    total_cycle_duration = time.time() - start_time_cycle
    logger.info(f"Full search cycle completed. Total duration: {total_cycle_duration:.2f}s. Returning {len(processed_grants_for_return)} grants.")
    
    return processed_grants_for_return

# Search Run Management Functions

async def create_search_run(
    db: AsyncSession,
    run_type: str = "manual",
    search_query: Optional[str] = None,
    search_filters: Optional[Dict[str, Any]] = None,
    user_triggered: bool = False
) -> models.SearchRun:
    """Create a new search run record."""
    search_run = models.SearchRun(
        run_type=run_type,
        search_query=search_query,
        search_filters=search_filters or {},
        user_triggered=user_triggered,
        status="in_progress"
    )
    db.add(search_run)
    await db.commit()
    await db.refresh(search_run)
    return search_run

async def update_search_run_result(
    db: AsyncSession,
    search_run_id: int,
    status: str,
    grants_found: int = 0,
    high_priority: int = 0,
    duration_seconds: Optional[float] = None,
    error_message: Optional[str] = None,
    error_details: Optional[Dict[str, Any]] = None,
    sources_searched: int = 0,
    api_calls_made: int = 0,
    processing_time_ms: Optional[int] = None
) -> models.SearchRun:
    """Update search run with results using safe SQL update."""
    try:
        # Prepare update data
        update_data = {
            'status': status,
            'grants_found': grants_found,
            'high_priority': high_priority,
            'duration_seconds': duration_seconds,
            'error_message': error_message,
            'error_details': json.dumps(error_details) if error_details else None,
            'sources_searched': sources_searched,
            'api_calls_made': api_calls_made,
            'processing_time_ms': processing_time_ms,
            'updated_at': datetime.utcnow()
        }
        
        # Use safe update helper
        success = await safe_update_model(db, models.SearchRun, search_run_id, update_data)
        
        if not success:
            raise ValueError(f"Failed to update SearchRun with id {search_run_id}")
        
        await db.commit()
        
        # Fetch and return updated search run
        query = select(models.SearchRun).where(models.SearchRun.id == search_run_id)
        result = await db.execute(query)
        search_run = result.scalar_one_or_none()
        
        if not search_run:
            raise ValueError(f"SearchRun with id {search_run_id} not found after update")
            
        return search_run
        
    except Exception as e:
        logger.error(f"Error updating search run {search_run_id}: {str(e)}", exc_info=True)
        await db.rollback()
        raise

async def get_search_runs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    run_type: Optional[str] = None,
    status: Optional[str] = None,
    days_back: int = 30
) -> Tuple[List[Dict[str, Any]], int]:
    """Get paginated search runs with optional filtering."""
    # Base query
    query = select(models.SearchRun)
    
    # Add filters
    if run_type:
        query = query.where(models.SearchRun.run_type == run_type)
    
    if status:
        query = query.where(models.SearchRun.status == status)
    
    # Filter by date range
    cutoff_date = datetime.now() - timedelta(days=days_back)
    query = query.where(models.SearchRun.created_at >= cutoff_date)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one() or 0
    
    # Add pagination and ordering
    query = query.order_by(models.SearchRun.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    search_runs = result.scalars().all()
    
    # Convert to dictionaries
    runs_data = []
    for run in search_runs:
        run_dict = {
            "id": run.id,
            "timestamp": run.timestamp.isoformat(),
            "created_at": run.created_at.isoformat(),
            "run_type": run.run_type,
            "status": run.status,
            "grants_found": run.grants_found,
            "high_priority": run.high_priority,
            "duration_seconds": run.duration_seconds,
            "search_query": run.search_query,
            "search_filters": run.search_filters,
            "error_message": run.error_message,
            "error_details": run.error_details,
            "user_triggered": run.user_triggered,
            "sources_searched": run.sources_searched,
            "api_calls_made": run.api_calls_made,
            "processing_time_ms": run.processing_time_ms
        }
        runs_data.append(run_dict)
    
    return runs_data, total

async def get_latest_automated_run(db: AsyncSession) -> Optional[Dict[str, Any]]:
    """Get the latest automated search run."""
    query = select(models.SearchRun).where(
        models.SearchRun.run_type == "automated"
    ).order_by(models.SearchRun.created_at.desc()).limit(1)
    
    result = await db.execute(query)
    run = result.scalar_one_or_none()
    
    if not run:
        return None
    
    return {
        "id": run.id,
        "timestamp": run.timestamp.isoformat(),
        "status": run.status,
        "grants_found": run.grants_found,
        "high_priority": run.high_priority,
        "duration_seconds": run.duration_seconds,
        "error_message": run.error_message
    }

async def get_search_run_statistics(db: AsyncSession, days_back: int = 7) -> Dict[str, Any]:
    """Get search run statistics for the dashboard."""
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    # Total runs
    total_query = select(func.count()).select_from(models.SearchRun).where(
        models.SearchRun.created_at >= cutoff_date
    )
    total_result = await db.execute(total_query)
    total_runs = total_result.scalar_one() or 0
    
    # Successful runs
    success_query = select(func.count()).select_from(models.SearchRun).where(
        models.SearchRun.created_at >= cutoff_date,
        models.SearchRun.status == "success"
    )
    success_result = await db.execute(success_query)
    successful_runs = success_result.scalar_one() or 0
    
    # Failed runs
    failed_query = select(func.count()).select_from(models.SearchRun).where(
        models.SearchRun.created_at >= cutoff_date,
        models.SearchRun.status == "failed"
    )
    failed_result = await db.execute(failed_query)
    failed_runs = failed_result.scalar_one() or 0
    
    # Average grants found
    avg_grants_query = select(func.avg(models.SearchRun.grants_found)).where(
        models.SearchRun.created_at >= cutoff_date,
        models.SearchRun.status == "success"
    )
    avg_grants_result = await db.execute(avg_grants_query)
    avg_grants = avg_grants_result.scalar_one() or 0
    
    # Average duration
    avg_duration_query = select(func.avg(models.SearchRun.duration_seconds)).where(
        models.SearchRun.created_at >= cutoff_date,
        models.SearchRun.duration_seconds.isnot(None)
    )
    avg_duration_result = await db.execute(avg_duration_query)
    avg_duration = avg_duration_result.scalar_one() or 0
    
    return {
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "success_rate": (successful_runs / total_runs * 100) if total_runs > 0 else 0,
        "average_grants_found": round(avg_grants, 1),
        "average_duration_seconds": round(avg_duration, 2),
        "days_analyzed": days_back
    }

# --- ApplicationHistory CRUD Functions ---

async def create_application_history_entry(
    db: AsyncSession, 
    history_entry_data: schemas.ApplicationHistoryCreate, 
    user_id: str
) -> models.ApplicationHistory:
    """
    Create a new application history entry.
    """
    logger.info(f"Creating application history for grant_id: {history_entry_data.grant_id} by user_id: {user_id}")
    
    try:
        status_enum = models.ApplicationStatus(history_entry_data.status)
    except ValueError:
        logger.error(f"Invalid application status: {history_entry_data.status}")
        raise ValueError(f"Invalid application status: {history_entry_data.status}")

    is_successful = None
    if status_enum == models.ApplicationStatus.AWARDED:
        is_successful = True
    elif status_enum in [models.ApplicationStatus.REJECTED, models.ApplicationStatus.WITHDRAWN]:
        is_successful = False

    combined_feedback_notes = ""
    if history_entry_data.outcome_notes:
        combined_feedback_notes += f"Outcome Notes: {history_entry_data.outcome_notes}\\n"
    if history_entry_data.feedback_for_profile_update:
        combined_feedback_notes += f"Feedback for Profile Update: {history_entry_data.feedback_for_profile_update}"
    
    db_entry = models.ApplicationHistory(
        grant_id=history_entry_data.grant_id,
        user_id=user_id,
        application_date=history_entry_data.submission_date,
        status=status_enum,
        feedback_notes=combined_feedback_notes.strip() if combined_feedback_notes else None,
        is_successful_outcome=is_successful,
        # award_amount and status_reason might be set via update or if schema expands
    )
    
    db.add(db_entry)
    await db.commit()
    await db.refresh(db_entry)
    logger.info(f"Successfully created application history entry with id: {db_entry.id}")
    return db_entry

async def get_application_history_by_id(
    db: AsyncSession, 
    history_id: int,
    user_id: str # Added user_id for authorization/scoping if needed
) -> Optional[models.ApplicationHistory]:
    """
    Get a specific application history entry by its ID.
    Optionally, user_id can be used to ensure the user has access.
    """
    logger.debug(f"Fetching application history entry with id: {history_id} for user_id: {user_id}")
    # If strict user scoping is needed for GET by ID: .filter(models.ApplicationHistory.user_id == user_id)
    stmt = select(models.ApplicationHistory).filter(models.ApplicationHistory.id == history_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    
    # Safe check for entry existence and user authorization
    if entry is not None:
        entry_user_id = getattr(entry, 'user_id', None)
        if entry_user_id != user_id:
            logger.warning(f"User {user_id} attempted to access history entry {history_id} owned by {entry_user_id}")
            return None # Or raise HTTPException(status_code=403, detail="Not authorized")
    
    return entry

async def get_application_history_for_grant(
    db: AsyncSession, 
    grant_id: str, 
    user_id: str
) -> List[models.ApplicationHistory]:
    """
    Fetches all application history entries for a specific grant, ensuring user has access.
    """
    # First, verify the grant exists
    grant_check = await db.execute(select(models.Grant).filter(models.Grant.id == grant_id))
    if not grant_check.scalar_one_or_none():
        raise ValueError("Grant not found.")

    # Fetch history, assuming a simple ownership model for now
    # In a real multi-tenant app, you'd filter by user_id more robustly
    query = select(models.ApplicationHistory).filter(models.ApplicationHistory.grant_id == grant_id).order_by(models.ApplicationHistory.submission_date.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_application_history_entry(
    db: AsyncSession, 
    history_id: int, 
    history_update_data: schemas.ApplicationHistoryCreate, # Using Create schema for update fields
    user_id: str
) -> Optional[models.ApplicationHistory]:
    """
    Update an existing application history entry.
    """
    logger.info(f"Updating application history entry id: {history_id} by user_id: {user_id}")
    db_entry = await get_application_history_by_id(db, history_id, user_id) # Re-use get for fetch and auth check

    if not db_entry:
        logger.warning(f"Application history entry with id: {history_id} not found or user {user_id} not authorized.")
        return None

    # Prepare update data
    update_data = {}
    
    if history_update_data.submission_date is not None:
        update_data['application_date'] = history_update_data.submission_date
    
    if history_update_data.status:
        try:
            status_enum = models.ApplicationStatus(history_update_data.status)
            update_data['status'] = status_enum.value
            
            if status_enum == models.ApplicationStatus.AWARDED:
                update_data['is_successful_outcome'] = True
            elif status_enum in [models.ApplicationStatus.REJECTED, models.ApplicationStatus.WITHDRAWN]:
                update_data['is_successful_outcome'] = False
            else:
                update_data['is_successful_outcome'] = None
        except ValueError:
            logger.error(f"Invalid application status for update: {history_update_data.status}")
            raise ValueError(f"Invalid application status for update: {history_update_data.status}")

    combined_feedback_notes = ""
    if history_update_data.outcome_notes:
        combined_feedback_notes += f"Outcome Notes: {history_update_data.outcome_notes}\\n"
    if history_update_data.feedback_for_profile_update:
        combined_feedback_notes += f"Feedback for Profile Update: {history_update_data.feedback_for_profile_update}"
    
    if combined_feedback_notes:
        update_data['feedback_notes'] = combined_feedback_notes.strip()

    update_data['updated_at'] = datetime.utcnow()
    
    # Use safe update helper
    success = await safe_update_model(db, models.ApplicationHistory, history_id, update_data)
    
    if not success:
        logger.error(f"Failed to update application history entry {history_id}")
        return None
    
    await db.commit()
    
    # Fetch updated entry
    query = select(models.ApplicationHistory).where(models.ApplicationHistory.id == history_id)
    result = await db.execute(query)
    updated_entry = result.scalar_one_or_none()
    
    logger.info(f"Successfully updated application history entry with id: {history_id}")
    return updated_entry

async def delete_application_history_entry(
    db: AsyncSession, 
    history_id: int, 
    user_id: str
) -> bool:
    """
    Delete an application history entry.
    """
    logger.info(f"Attempting to delete application history entry id: {history_id} by user_id: {user_id}")
    db_entry = await get_application_history_by_id(db, history_id, user_id) # Re-use for fetch and auth

    if not db_entry:
        logger.warning(f"Application history entry id: {history_id} not found for deletion or user {user_id} not authorized.")
        return False

    await db.delete(db_entry)
    await db.commit()
    logger.info(f"Successfully deleted application history entry id: {history_id}")
    return True

# Grant retrieval and upsert functions

async def get_grant_by_id(db: AsyncSession, grant_id: int) -> Optional[EnrichedGrant]:
    """Get a single grant by ID with robust error handling"""
    try:
        from app.defensive import RobustGrantConverter
        
        logger.info(f"Fetching grant with ID: {grant_id}")
        
        query = select(DBGrant).options(selectinload(DBGrant.analyses)).where(DBGrant.id == grant_id)
        result = await db.execute(query)
        grant_model = result.scalar_one_or_none()

        if not grant_model:
            logger.warning(f"Grant with ID {grant_id} not found")
            return None

        # Use robust converter
        enriched_grant = RobustGrantConverter.convert_db_grant_to_enriched(grant_model)
        if enriched_grant:
            logger.info(f"Successfully converted grant {grant_id} to EnrichedGrant")
        else:
            logger.warning(f"Failed to convert grant {grant_id} to EnrichedGrant")
        
        return enriched_grant

    except Exception as e:
        logger.error(f"Error fetching grant {grant_id}: {str(e)}", exc_info=True)
        return None

async def create_or_update_grant(db: AsyncSession, grant_data: dict) -> Optional[DBGrant]:
    """Create or update a grant in the database with defensive programming. REQUIRES valid URL."""
    try:
        # MANDATORY URL VALIDATION - Skip grants without valid URLs
        source_url = (grant_data.get('source_url') or '').strip()
        if not source_url or not source_url.startswith(('http://', 'https://')):
            logger.warning(f"Skipping grant '{grant_data.get('title', 'Unknown')}' - no valid URL: {source_url}")
            return None

        # Check for duplicates using multiple strategies
        existing_grant = await check_duplicate_grant(db, grant_data)
        if existing_grant:
            logger.info(f"Duplicate grant detected, updating existing: {existing_grant.id}")
            return await update_duplicate_grant(db, existing_grant, grant_data)

        grant_id = grant_data.get('id')
        external_id = grant_data.get('grant_id_external')

        # Try to find existing grant by ID or external ID (fallback)
        if grant_id:
            try:
                query = select(DBGrant).where(DBGrant.id == grant_id)
                result = await db.execute(query)
                existing_grant = result.scalar_one_or_none()
            except Exception:
                pass
        
        if not existing_grant and external_id:
            try:
                query = select(DBGrant).where(DBGrant.grant_id_external == external_id)
                result = await db.execute(query)
                existing_grant = result.scalar_one_or_none()
            except Exception:
                pass
        
        if existing_grant:
            # Update existing grant - use SQL UPDATE statement
            update_data = {k: v for k, v in grant_data.items() if v is not None and hasattr(DBGrant, k)}
            update_data['updated_at'] = datetime.utcnow()
            
            from sqlalchemy import update
            update_stmt = update(DBGrant).where(DBGrant.id == existing_grant.id).values(**update_data)
            await db.execute(update_stmt)
            await db.flush()
            
            # Fetch updated grant
            result = await db.execute(select(DBGrant).where(DBGrant.id == existing_grant.id))
            updated_grant = result.scalar_one_or_none()
            logger.info(f"Updated existing grant {existing_grant.id}")
            return updated_grant
        
        else:
            # Create new grant
            create_data = {k: v for k, v in grant_data.items() if v is not None and hasattr(DBGrant, k)}
            create_data['created_at'] = datetime.utcnow()
            create_data['updated_at'] = datetime.utcnow()
            
            new_grant = DBGrant(**create_data)
            db.add(new_grant)
            await db.flush()
            logger.info(f"Created new grant {new_grant.id}")
            return new_grant
            
    except Exception as e:
        logger.error(f"Error creating/updating grant: {str(e)}", exc_info=True)
        return None

# Defensive programming utility functions
def safe_parse_json(json_field, default=None):
    """Safely parse JSON field with default fallback"""
    if json_field is None:
        return default
    try:
        if isinstance(json_field, (dict, list)):
            return json_field
        return json.loads(json_field) if json_field else default
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse JSON field: {e}")
        return default

def safe_getattr(obj, attr, default=None):
    """Safely get attribute with None check"""
    if obj is None:
        return default
    return getattr(obj, attr, default)

def safe_float_conversion(value, default=None):
    """Safely convert value to float"""
    if value is None:
        return default
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def safe_datetime_conversion(value, default=None):
    """Safely convert value to datetime"""
    if value is None:
        return default
    if isinstance(value, datetime):
        return value
    return default

def safe_list_conversion(value, default=None):
    """Safely convert value to List[str]"""
    if value is None:
        return default or []
    if isinstance(value, list):
        return [str(item) for item in value]
    return default or []

def safe_dict_conversion(value, default=None):
    """Safely convert value to Dict[str, Any]"""
    if value is None:
        return default
    if isinstance(value, dict):
        return value
    return default

def safe_convert_to_enriched_grant(grant_model) -> Optional[EnrichedGrant]:
    """Safely convert database grant model to EnrichedGrant schema with defensive checks"""
    try:
        if grant_model is None:
            logger.warning("Received None grant_model in conversion")
            return None
        
        # Safe attribute access with defaults
        grant_id = safe_getattr(grant_model, 'id')
        if grant_id is None:
            logger.warning("Grant model missing required ID field")
            return None
        
        # Extract scores with safe access
        overall_composite_score = safe_getattr(grant_model, 'overall_composite_score', 0.0)
        
        # Safely access analysis data
        analyses = safe_getattr(grant_model, 'analyses', [])
        
        # Build research context scores safely using correct field names
        research_scores = None
        compliance_scores = None
        if analyses and len(analyses) > 0:
            analysis = analyses[0]
            research_scores = ResearchContextScores(
                sector_relevance=safe_getattr(analysis, 'sector_relevance_score', 0.0),
                geographic_relevance=safe_getattr(analysis, 'geographic_relevance_score', 0.0),
                operational_alignment=safe_getattr(analysis, 'operational_alignment_score', 0.0)
            )
            
            compliance_scores = ComplianceScores(
                business_logic_alignment=safe_getattr(analysis, 'business_logic_alignment_score', 0.0),
                feasibility_score=safe_getattr(analysis, 'feasibility_score', 0.0),
                strategic_synergy=safe_getattr(analysis, 'strategic_synergy_score', 0.0),
                final_weighted_score=safe_getattr(analysis, 'final_score', 0.0)
            )
        
        # Build source details safely using correct field names
        source_details = GrantSourceDetails(
            source_name=safe_getattr(grant_model, 'source_name', ''),
            source_url=safe_getattr(grant_model, 'source_url', ''),
            retrieved_at=safe_datetime_conversion(safe_getattr(grant_model, 'retrieved_at'))
        )
        
        # Create EnrichedGrant with correct field names from schema
        enriched_grant = EnrichedGrant(
            # Basic fields from Grant base class
            id=str(grant_id),
            title=safe_getattr(grant_model, 'title', 'Untitled Grant'),
            description=safe_getattr(grant_model, 'description', ''),
            funding_amount=safe_float_conversion(safe_getattr(grant_model, 'funding_amount')),
            deadline=safe_datetime_conversion(safe_getattr(grant_model, 'deadline')),
            eligibility_criteria=safe_getattr(grant_model, 'eligibility_summary_llm', ''),
            category=safe_getattr(grant_model, 'identified_sector', 'General'),
            source_url=safe_getattr(grant_model, 'source_url', ''),
            source_name=safe_getattr(grant_model, 'source_name', 'Unknown'),
            
            # EnrichedGrant specific fields
            grant_id_external=safe_getattr(grant_model, 'grant_id_external'),
            summary_llm=safe_getattr(grant_model, 'summary_llm'),
            eligibility_summary_llm=safe_getattr(grant_model, 'eligibility_summary_llm', ''),
            funder_name=safe_getattr(grant_model, 'funder_name'),
            
            # Funding details
            funding_amount_min=safe_float_conversion(safe_getattr(grant_model, 'funding_amount_min')),
            funding_amount_max=safe_float_conversion(safe_getattr(grant_model, 'funding_amount_max')),
            funding_amount_exact=safe_float_conversion(safe_getattr(grant_model, 'funding_amount_exact')),
            funding_amount_display=safe_getattr(grant_model, 'funding_amount_display', 'Not specified'),
            
            # Date fields
            deadline_date=safe_datetime_conversion(safe_getattr(grant_model, 'deadline_date')),
            application_open_date=safe_datetime_conversion(safe_getattr(grant_model, 'application_open_date')),
            
            # Keywords and categories
            keywords=safe_list_conversion(safe_parse_json(safe_getattr(grant_model, 'keywords_json'), [])),
            categories_project=safe_list_conversion(safe_parse_json(safe_getattr(grant_model, 'categories_project_json'), [])),
            
            # Source details
            source_details=source_details,
            
            # Contextual fields
            identified_sector=safe_getattr(grant_model, 'identified_sector', 'General'),
            identified_sub_sector=safe_getattr(grant_model, 'identified_sub_sector'),
            geographic_scope=safe_getattr(grant_model, 'geographic_scope'),
            specific_location_mentions=safe_list_conversion(safe_parse_json(safe_getattr(grant_model, 'specific_location_mentions_json'), [])),
            
            # Scoring systems
            research_scores=research_scores,
            compliance_scores=compliance_scores,
            overall_composite_score=overall_composite_score,
            
            # Compliance and feasibility
            compliance_summary=safe_dict_conversion(safe_parse_json(safe_getattr(grant_model, 'compliance_summary_json'))),
            feasibility_score=safe_float_conversion(safe_getattr(grant_model, 'feasibility_score')),
            risk_assessment=safe_dict_conversion(safe_parse_json(safe_getattr(grant_model, 'risk_assessment_json'))),
            
            # Additional metadata
            raw_source_data=safe_dict_conversion(safe_parse_json(safe_getattr(grant_model, 'raw_source_data_json'))),
            enrichment_log=safe_list_conversion(safe_parse_json(safe_getattr(grant_model, 'enrichment_log_json'), []))
        )
        
        return enriched_grant
        
    except Exception as e:
        logger.error(f"Error converting grant model to EnrichedGrant: {e}", exc_info=True)
        return None

async def get_grants_list(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    sort_by: str = "overall_composite_score",
    sort_order: str = "desc",
    status_filter: Optional[str] = None,
    min_overall_score: Optional[float] = None,
    max_overall_score: Optional[float] = None,
    category: Optional[str] = None,
    search_query: Optional[str] = None
) -> Tuple[List[EnrichedGrant], int]:
    """
    Get grants list with advanced filtering, sorting, and pagination.
    Returns EnrichedGrant objects with defensive error handling.
    """
    try:
        logger.info(f"get_grants_list called with skip={skip}, limit={limit}, sort_by={sort_by}")
        
        # Build base query with safe joins - FILTER OUT GRANTS WITHOUT URLs
        query = select(DBGrant).outerjoin(Analysis).options(selectinload(DBGrant.analyses))
        
        # MANDATORY: Only include grants with valid source URLs
        query = query.filter(DBGrant.source_url.isnot(None))
        query = query.filter(DBGrant.source_url != "")
        query = query.filter(DBGrant.source_url.like("http%"))  # Must be a valid URL
        
        # Apply filters with safe checks
        if min_overall_score is not None:
            query = query.filter(DBGrant.overall_composite_score >= min_overall_score)
        
        if max_overall_score is not None:
            query = query.filter(DBGrant.overall_composite_score <= max_overall_score)
        
        if category:
            query = query.filter(DBGrant.identified_sector == category)
        
        if status_filter:
            query = query.filter(DBGrant.application_status == status_filter)
        
        if search_query:
            search_filter = or_(
                DBGrant.title.ilike(f"%{search_query}%"),
                DBGrant.description.ilike(f"%{search_query}%")
            )
            query = query.filter(search_filter)
        
        # Get total count safely
        count_query = select(func.count()).select_from(query.subquery())
        try:
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0
        except Exception as e:
            logger.warning(f"Error getting total count, using 0: {e}")
            total = 0
        
        # Apply sorting with safe attribute access
        sort_column = None
        if sort_by == "overall_composite_score":
            sort_column = DBGrant.overall_composite_score
        elif sort_by == "deadline":
            sort_column = DBGrant.deadline
        elif sort_by == "title":
            sort_column = DBGrant.title
        elif sort_by == "priority_score":
            sort_column = DBGrant.priority_score
        else:
            # Default to overall_composite_score if invalid sort_by
            sort_column = DBGrant.overall_composite_score
        
        if sort_order.lower() == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query safely
        try:
            result = await db.execute(query)
            grant_models = result.scalars().all()
        except Exception as e:
            logger.error(f"Error executing grants query: {e}")
            return [], 0
        
        # Convert to EnrichedGrant objects with defensive programming
        enriched_grants = []
        for grant_model in grant_models:
            try:
                enriched_grant = safe_convert_to_enriched_grant(grant_model)
                if enriched_grant is not None:
                    enriched_grants.append(enriched_grant)
            except Exception as e:
                logger.warning(f"Skipping grant conversion due to error: {e}")
                continue
        
        logger.info(f"Successfully converted {len(enriched_grants)} grants out of {len(grant_models)} models")
        return enriched_grants, total
        
    except Exception as e:
        logger.error(f"Error in get_grants_list: {e}", exc_info=True)
        return [], 0

async def safe_update_model(db: AsyncSession, model_class, model_id: int, update_data: dict):
    """Safely update a SQLAlchemy model using UPDATE statement"""
    try:
        from sqlalchemy import update as sql_update
        
        # Filter out None values and non-existent columns
        filtered_data = {k: v for k, v in update_data.items() 
                        if v is not None and hasattr(model_class, k)}
        
        if not filtered_data:
            return False
            
        # Use SQL UPDATE statement
        update_stmt = sql_update(model_class).where(model_class.id == model_id).values(**filtered_data)
        await db.execute(update_stmt)
        return True
        
    except Exception as e:
        logger.error(f"Error updating {model_class.__name__} {model_id}: {e}")
        return False