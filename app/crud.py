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
# It's generally better to import specific classes if you're not using the whole module via alias.
# However, the generated CRUD functions used models. and schemas. prefixes, so let's add module imports for them.
from database import models
from app import schemas

from agents.research_agent import ResearchAgent
from agents.compliance_agent import ComplianceAnalysisAgent
from utils.perplexity_client import PerplexityClient 
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
        score_value = None
        # Attempt to get score from related Analysis table if it exists
        if grant_model.analyses and len(grant_model.analyses) > 0:
            # Assuming the first analysis record is relevant, and it has a 'final_score'
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
            "deadline": grant_model.deadline.isoformat() if grant_model.deadline else None,
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
        "telegramEnabled": "telegram_enabled",
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
    perplexity_client: PerplexityClient, 
    pinecone_client: PineconeClient 
) -> List[EnrichedGrant]:
    """Run a complete grant search cycle, including research and compliance analysis."""
    logger.info("Starting full search cycle...")
    start_time_cycle = time.time()
    research_agent_instance = None # Initialize to None
    try:
        research_agent_instance = ResearchAgent(
            perplexity_client=perplexity_client,
            db_sessionmaker=db_sessionmaker,
            # pinecone_client=pinecone_client, # Assuming pinecone_client is not a direct param for ResearchAgent constructor
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
            perplexity_client=perplexity_client 
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
                # Call the dedicated create_or_update_grant function
                saved_grant = await create_or_update_grant(session, enriched_grant_data)
                if saved_grant:
                    processed_grants_for_return.append(saved_grant)
                    saved_grants_count += 1
                    logger.info(f"Successfully saved/updated grant via dedicated function: {saved_grant.title[:50] if saved_grant.title else 'N/A'} (ID: {saved_grant.id})")
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

async def create_search_run(
    db: AsyncSession, 
    grants_found: int, 
    high_priority_found: int, 
    search_filters: Optional[Dict[str, Any]] = None
) -> SearchRun:
    """Create and store a new search run record."""
    if search_filters is None:
        search_filters = {}
        
    new_search_run = SearchRun(
        timestamp=datetime.utcnow(), 
        grants_found=grants_found,
        high_priority=high_priority_found,
        search_filters=json.dumps(search_filters) # Ensure search_filters is JSON serializable
    )
    db.add(new_search_run)
    await db.commit()
    await db.refresh(new_search_run)
    return new_search_run

def _map_db_grant_to_enriched_grant(db_grant: DBGrant) -> Optional[EnrichedGrant]:
    if not db_grant:
        return None

    # Base Grant fields for EnrichedGrant inheritance (from app.schemas.Grant)
    # These are common fields that EnrichedGrant inherits.
    # Ensure these align with the base Grant Pydantic model if it's explicitly defined.
    # For now, assuming EnrichedGrant directly defines or inherits these.
    base_grant_fields = {
        "id": str(db_grant.id), 
        "title": db_grant.title,
        "description": db_grant.description,
        "funding_amount": db_grant.funding_amount_exact if db_grant.funding_amount_exact is not None else db_grant.funding_amount_display,
        "deadline": db_grant.deadline, # This will be Optional[date]
        "eligibility_criteria": db_grant.eligibility_summary_llm,
        "category": db_grant.identified_sector, 
        "source_url": db_grant.source_url,
        "source_name": db_grant.source_name,
        # 'score' is not directly on DBGrant in this way, it's overall_composite_score
    }

    grant_data = {
        **base_grant_fields,
        "grant_id_external": db_grant.grant_id_external,
        "summary_llm": db_grant.summary_llm,
        "funder_name": db_grant.funder_name,
        "funding_amount_min": db_grant.funding_amount_min,
        "funding_amount_max": db_grant.funding_amount_max,
        "funding_amount_exact": db_grant.funding_amount_exact,
        "funding_amount_display": db_grant.funding_amount_display,
        "deadline_date": db_grant.deadline, # Explicitly part of EnrichedGrant
        "application_open_date": db_grant.application_open_date,
        "eligibility_summary_llm": db_grant.eligibility_summary_llm, # Explicit
        "keywords": json.loads(db_grant.keywords_json) if db_grant.keywords_json else [],
        "categories_project": json.loads(db_grant.categories_project_json) if db_grant.categories_project_json else [],
        "source_details": GrantSourceDetails(
            source_name=db_grant.source_name,
            source_url=db_grant.source_url,
            retrieved_at=db_grant.retrieved_at
        ) if db_grant.source_name or db_grant.source_url or db_grant.retrieved_at else None,
        "record_status": db_grant.record_status,
        "research_scores": ResearchContextScores(
            sector_relevance=db_grant.sector_relevance_score,
            geographic_relevance=db_grant.geographic_relevance_score,
            operational_alignment=db_grant.operational_alignment_score
        ) if db_grant.sector_relevance_score is not None or \
             db_grant.geographic_relevance_score is not None or \
             db_grant.operational_alignment_score is not None else None,
        "compliance_scores": ComplianceScores(
            business_logic_alignment=db_grant.business_logic_alignment_score,
            feasibility_score=db_grant.feasibility_context_score, 
            strategic_synergy=db_grant.strategic_synergy_score,
            # final_weighted_score is not directly stored here, it's part of overall_composite_score logic
        ) if db_grant.business_logic_alignment_score is not None or \
             db_grant.feasibility_context_score is not None or \
             db_grant.strategic_synergy_score is not None else None,
        "overall_composite_score": db_grant.overall_composite_score,
        "created_at": db_grant.created_at,
        "updated_at": db_grant.updated_at,
        "identified_sector": db_grant.identified_sector,
        "identified_sub_sector": db_grant.identified_sub_sector,
        "geographic_scope": db_grant.geographic_scope,
        "specific_location_mentions": json.loads(db_grant.specific_location_mentions_json) if hasattr(db_grant, 'specific_location_mentions_json') and db_grant.specific_location_mentions_json else [],
        "raw_source_data": json.loads(db_grant.raw_source_data_json) if hasattr(db_grant, 'raw_source_data_json') and db_grant.raw_source_data_json else None,
        "enrichment_log": json.loads(db_grant.enrichment_log_json) if hasattr(db_grant, 'enrichment_log_json') and db_grant.enrichment_log_json else [],
        "last_enriched_at": db_grant.last_enriched_at,
        # application_status and application_history_id would typically come from a join or separate query if needed
        # For now, they are not directly mapped from DBGrant unless those fields exist on DBGrant
    }
    try:
        # Ensure all fields expected by EnrichedGrant are present in grant_data or have defaults
        # For example, if EnrichedGrant requires 'id' and it's not in base_grant_fields for some reason:
        if 'id' not in grant_data and hasattr(db_grant, 'id'): # Should be covered by base_grant_fields
            grant_data['id'] = str(db_grant.id)
        
        # Ensure research_scores and compliance_scores are initialized if None
        if grant_data.get('research_scores') is None:
            grant_data['research_scores'] = ResearchContextScores()
        if grant_data.get('compliance_scores') is None:
            grant_data['compliance_scores'] = ComplianceScores()
        if grant_data.get('source_details') is None:
            # Provide a default GrantSourceDetails if it's missing and required
            grant_data['source_details'] = GrantSourceDetails(
                source_name=db_grant.source_name or "Unknown", 
                source_url=db_grant.source_url or "", 
                retrieved_at=db_grant.retrieved_at or datetime.utcnow()
            )

        return EnrichedGrant(**grant_data)
    except Exception as e: 
        logger.error(f"Error converting DBGrant (ID: {db_grant.id}) to EnrichedGrant: {e}", exc_info=True)
        return None

async def get_grant_by_id(db: AsyncSession, grant_id: int) -> Optional[EnrichedGrant]:
    """Fetch a single grant by its ID and map to EnrichedGrant schema."""
    try:
        grant_id_int = int(grant_id) # Ensure grant_id is int
    except ValueError:
        logger.error(f"Invalid grant_id format: {grant_id}. Must be an integer.")
        return None

    stmt = select(DBGrant).filter(DBGrant.id == grant_id_int)
    result = await db.execute(stmt)
    db_grant = result.scalar_one_or_none()

    if db_grant:
        return _map_db_grant_to_enriched_grant(db_grant)
    return None

async def get_grants_list(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    sort_by: Optional[str] = "overall_composite_score", # Default sort field
    sort_order: Optional[str] = "desc", # Default sort order
    status_filter: Optional[str] = None,
    min_overall_score: Optional[float] = None,
    search_query: Optional[str] = None,
) -> Tuple[List[EnrichedGrant], int]:
    """Fetch a list of grants, map to EnrichedGrant schema, with pagination, sorting, and filtering."""
    
    query = select(DBGrant)
    count_query_base = select(func.count()).select_from(DBGrant)
    
    # Apply filters
    # Note: record_status field doesn't exist in Grant model, skip this filter
    # if status_filter:
    #     query = query.filter(DBGrant.record_status == status_filter)
    #     count_query_base = count_query_base.filter(DBGrant.record_status == status_filter)
    
    if min_overall_score is not None:
        query = query.filter(DBGrant.overall_composite_score >= min_overall_score)
        count_query_base = count_query_base.filter(DBGrant.overall_composite_score >= min_overall_score)

    if search_query:
        search_filter = or_(
            DBGrant.title.ilike(f"%{search_query}%"),
            DBGrant.description.ilike(f"%{search_query}%"),
            # DBGrant.summary_llm.ilike(f"%{search_query}%"),  # Field doesn't exist in Grant model
            # DBGrant.keywords_json.ilike(f"%{search_query}%"), # Field doesn't exist, using raw_source_data search instead
            DBGrant.source_name.ilike(f"%{search_query}%")
        )
        query = query.filter(search_filter)
        count_query_base = count_query_base.filter(search_filter)    # Get total count matching filters
    total_count_result = await db.execute(count_query_base)
    total_count = total_count_result.scalar_one_or_none() or 0# Apply sorting
    # Since scores are in the Analysis table, we need to handle sorting differently
    # For now, default to created_at or title if the requested sort field doesn't exist
    if hasattr(DBGrant, sort_by):
        sort_column = getattr(DBGrant, sort_by)
    elif sort_by == "overall_composite_score":
        # For score-based sorting, we'll need to join with Analysis table
        # For now, fallback to created_at
        sort_column = DBGrant.created_at
    else:
        sort_column = DBGrant.created_at # Default fallback
        
    if sort_order and sort_order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc()) # Default to desc

    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    db_grants = result.scalars().all()
    
    enriched_grants = []
    for db_grant in db_grants:
        enriched = _map_db_grant_to_enriched_grant(db_grant)
        if enriched:
            enriched_grants.append(enriched)
            
    return enriched_grants, total_count


async def create_or_update_grant(session: AsyncSession, grant_data_model: EnrichedGrant) -> Optional[EnrichedGrant]:
    """
    Creates a new grant or updates an existing one in the database.
    Returns the saved EnrichedGrant object or None if an error occurs.
    """
    logger.debug(f"Attempting to create/update grant: {grant_data_model.title[:50] if grant_data_model.title else 'N/A'} (External ID: {grant_data_model.grant_id_external})")
    existing_grant: Optional[DBGrant] = None

    # Try to find existing grant by internal ID first if provided and valid
    if grant_data_model.id:
        try:
            grant_internal_id = int(grant_data_model.id)
            stmt_by_id = select(DBGrant).filter(DBGrant.id == grant_internal_id)
            result_by_id = await session.execute(stmt_by_id)
            existing_grant = result_by_id.scalar_one_or_none()
            if existing_grant:
                logger.debug(f"Found existing grant by internal ID: {existing_grant.id}")
        except ValueError:
            logger.warning(f"Invalid format for grant_data_model.id: {grant_data_model.id}. Will proceed to check other identifiers.")

    # If not found by internal ID, try external ID
    if not existing_grant and grant_data_model.grant_id_external:
        stmt_ext = select(DBGrant).filter(DBGrant.grant_id_external == str(grant_data_model.grant_id_external))
        result_ext = await session.execute(stmt_ext)
        existing_grant = result_ext.scalar_one_or_none()
        if existing_grant:
            logger.debug(f"Found existing grant by external ID: {grant_data_model.grant_id_external}")

    # If still not found, try by source_url (if unique enough)
    if not existing_grant and grant_data_model.source_details and grant_data_model.source_details.source_url:
        stmt_url = select(DBGrant).filter(DBGrant.source_url == str(grant_data_model.source_details.source_url))
        result_url = await session.execute(stmt_url)
        existing_grant = result_url.scalar_one_or_none()
        if existing_grant:
            logger.debug(f"Found existing grant by source_url: {grant_data_model.source_details.source_url}")

    # If still not found, try by title (less reliable for uniqueness but a fallback)
    if not existing_grant and grant_data_model.title:
        stmt_title = select(DBGrant).filter(DBGrant.title == grant_data_model.title)
        result_title = await session.execute(stmt_title)
        existing_grant = result_title.scalar_one_or_none() # Could be multiple, take first or error
        if existing_grant:
            logger.debug(f"Found existing grant by title (use with caution): {grant_data_model.title}")

    db_model_instance = existing_grant if existing_grant else DBGrant()

    # Map all fields from EnrichedGrant to DBGrant model
    db_model_instance.grant_id_external = grant_data_model.grant_id_external
    db_model_instance.title = grant_data_model.title
    db_model_instance.description = grant_data_model.description
    db_model_instance.summary_llm = grant_data_model.summary_llm
    db_model_instance.funder_name = grant_data_model.funder_name
    db_model_instance.funding_amount_min = grant_data_model.funding_amount_min
    db_model_instance.funding_amount_max = grant_data_model.funding_amount_max
    db_model_instance.funding_amount_exact = grant_data_model.funding_amount_exact
    db_model_instance.funding_amount_display = grant_data_model.funding_amount_display
    db_model_instance.deadline = grant_data_model.deadline_date # Assuming EnrichedGrant.deadline_date is the correct one
    db_model_instance.application_open_date = grant_data_model.application_open_date
    db_model_instance.eligibility_summary_llm = grant_data_model.eligibility_summary_llm
    db_model_instance.keywords_json = json.dumps(grant_data_model.keywords) if grant_data_model.keywords else None
    db_model_instance.categories_project_json = json.dumps(grant_data_model.categories_project) if grant_data_model.categories_project else None
    
    if grant_data_model.source_details:
        db_model_instance.source_name = grant_data_model.source_details.source_name
        db_model_instance.source_url = str(grant_data_model.source_details.source_url) if grant_data_model.source_details.source_url else None
        db_model_instance.retrieved_at = grant_data_model.source_details.retrieved_at
    
    db_model_instance.record_status = grant_data_model.record_status

    if grant_data_model.research_scores:
        db_model_instance.sector_relevance_score = grant_data_model.research_scores.sector_relevance
        db_model_instance.geographic_relevance_score = grant_data_model.research_scores.geographic_relevance
        db_model_instance.operational_alignment_score = grant_data_model.research_scores.operational_alignment
    
    if grant_data_model.compliance_scores:
        db_model_instance.business_logic_alignment_score = grant_data_model.compliance_scores.business_logic_alignment
        db_model_instance.feasibility_context_score = grant_data_model.compliance_scores.feasibility_score
        db_model_instance.strategic_synergy_score = grant_data_model.compliance_scores.strategic_synergy
    
    db_model_instance.overall_composite_score = grant_data_model.overall_composite_score

    db_model_instance.identified_sector = grant_data_model.identified_sector
    db_model_instance.identified_sub_sector = grant_data_model.identified_sub_sector
    db_model_instance.geographic_scope = grant_data_model.geographic_scope
    db_model_instance.specific_location_mentions_json = json.dumps(grant_data_model.specific_location_mentions) if grant_data_model.specific_location_mentions else None
    db_model_instance.raw_source_data_json = json.dumps(grant_data_model.raw_source_data) if grant_data_model.raw_source_data else None
    db_model_instance.enrichment_log_json = json.dumps(grant_data_model.enrichment_log) if grant_data_model.enrichment_log else None
    db_model_instance.last_enriched_at = grant_data_model.last_enriched_at

    db_model_instance.updated_at = datetime.utcnow()
    if not existing_grant:
        db_model_instance.created_at = datetime.utcnow()
        session.add(db_model_instance)
        logger.info(f"Creating new grant in DB: {db_model_instance.title[:50] if db_model_instance.title else 'N/A'}")
    else:
        logger.info(f"Updating existing grant in DB: {db_model_instance.title[:50] if db_model_instance.title else 'N/A'} (ID: {db_model_instance.id})")

    try:
        await session.commit()
        await session.refresh(db_model_instance)
        logger.info(f"Successfully committed grant: {db_model_instance.title[:50] if db_model_instance.title else 'N/A'} (ID: {db_model_instance.id})")
        return _map_db_grant_to_enriched_grant(db_model_instance) # Convert back to EnrichedGrant
    except Exception as e:
        await session.rollback()
        logger.error(f"Error committing grant {grant_data_model.title[:50] if grant_data_model.title else 'N/A'} to database: {e}", exc_info=True)
        return None

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
    if entry and entry.user_id != user_id: # Basic check, can be more robust
        logger.warning(f"User {user_id} attempted to access history entry {history_id} owned by {entry.user_id}")
        return None # Or raise HTTPException(status_code=403, detail="Not authorized")
    return entry

async def get_application_history_for_grant(
    db: AsyncSession, 
    grant_id: int, 
    user_id: str
) -> List[models.ApplicationHistory]:
    """
    Get all application history entries for a specific grant and user.
    """
    logger.debug(f"Fetching application history for grant_id: {grant_id} and user_id: {user_id}")
    stmt = select(models.ApplicationHistory).filter(
        models.ApplicationHistory.grant_id == grant_id,
        models.ApplicationHistory.user_id == user_id
    ).order_by(models.ApplicationHistory.application_date.desc(), models.ApplicationHistory.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

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

    if history_update_data.submission_date is not None:
        db_entry.application_date = history_update_data.submission_date
    
    if history_update_data.status:
        try:
            status_enum = models.ApplicationStatus(history_update_data.status)
            db_entry.status = status_enum
            if status_enum == models.ApplicationStatus.AWARDED:
                db_entry.is_successful_outcome = True
            elif status_enum in [models.ApplicationStatus.REJECTED, models.ApplicationStatus.WITHDRAWN]:
                db_entry.is_successful_outcome = False
            else:
                db_entry.is_successful_outcome = None # Reset if status changes to indeterminate
        except ValueError:
            logger.error(f"Invalid application status for update: {history_update_data.status}")
            raise ValueError(f"Invalid application status for update: {history_update_data.status}")

    combined_feedback_notes = ""
    if history_update_data.outcome_notes:
        combined_feedback_notes += f"Outcome Notes: {history_update_data.outcome_notes}\\n"
    if history_update_data.feedback_for_profile_update:
        combined_feedback_notes += f"Feedback for Profile Update: {history_update_data.feedback_for_profile_update}"
    
    if combined_feedback_notes: # Only update if new notes are provided
        db_entry.feedback_notes = combined_feedback_notes.strip()
    elif history_update_data.outcome_notes is None and history_update_data.feedback_for_profile_update is None:
        # If both are explicitly None in an update, consider clearing, or leave as is.
        # Current: only updates if new notes provided. To clear, schema might need explicit nulls.
        pass


    # Fields like award_amount and status_reason are not in ApplicationHistoryCreate
    # They would need to be part of the history_update_data schema or handled differently.
    # For example, if history_update_data included 'award_amount':
    # if history_update_data.award_amount is not None:
    #     db_entry.award_amount = history_update_data.award_amount

    db_entry.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_entry)
    logger.info(f"Successfully updated application history entry with id: {db_entry.id}")
    return db_entry

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