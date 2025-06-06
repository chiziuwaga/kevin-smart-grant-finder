from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Grant, Analysis, SearchRun, UserSettings
from utils.pinecone_client import PineconeClient

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
    query = select(Grant).outerjoin(Analysis)
    
    if min_score > 0:
        query = query.filter(Analysis.score >= min_score)
    
    if category:
        query = query.filter(Grant.category == category)
    
    if deadline_before:
        deadline = datetime.fromisoformat(deadline_before)
        query = query.filter(Grant.deadline <= deadline)
    
    # Get total count for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.execute(count_query)
    total = total_count.scalar() or 0
    
    # Add pagination
    query = query.order_by(Grant.deadline.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    grants = result.scalars().all()
      # Convert SQLAlchemy models to dicts that match our schema
    grants_data = []
    for grant in grants:
        grant_dict = {
            "id": str(grant.id),
            "title": grant.title,
            "description": grant.description,
            "funding_amount": grant.funding_amount,
            "deadline": grant.deadline.isoformat() if grant.deadline else None,
            "eligibility_criteria": grant.eligibility,
            "category": grant.category,
            "source_url": grant.source_url,
            "source_name": grant.source,
            "score": grant.analyses[0].score if grant.analyses else None
        }
        grants_data.append(grant_dict)
    
    return grants_data, total

async def fetch_stats(db: AsyncSession) -> Dict[str, Any]:
    """Get dashboard statistics using SQLAlchemy."""
    # Get total grants
    total_query = select(func.count()).select_from(Grant)
    total_result = await db.execute(total_query)
    total_grants = total_result.scalar() or 0

    # Get average score
    avg_score_query = select(func.avg(Analysis.score)).select_from(Analysis)
    avg_score_result = await db.execute(avg_score_query)
    average_score = round(float(avg_score_result.scalar() or 0), 2)

    # Get grants added this month
    current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_query = select(func.count())\
        .select_from(Grant)\
        .filter(Grant.created_at >= current_month_start)
    monthly_result = await db.execute(monthly_query)
    grants_this_month = monthly_result.scalar() or 0    # Get upcoming deadlines (next 30 days)
    upcoming_deadline_query = select(func.count())\
        .select_from(Grant)\
        .filter(
            Grant.deadline >= datetime.now(),
            Grant.deadline <= datetime.now() + timedelta(days=30)
        )
    upcoming_result = await db.execute(upcoming_deadline_query)
    upcoming_deadlines = upcoming_result.scalar() or 0

    return {
        "totalGrants": total_grants,
        "averageScore": average_score,
        "grantsThisMonth": grants_this_month,
        "upcomingDeadlines": upcoming_deadlines
    }

async def fetch_distribution(db: AsyncSession) -> Dict[str, Dict[str, int]]:
    """Get analytics distribution using SQLAlchemy."""
    # Get category distribution
    category_query = select(
        Grant.category,
        func.count(Grant.id).label('count')
    ).filter(Grant.category.isnot(None))\
    .group_by(Grant.category)
    
    category_result = await db.execute(category_query)
    categories = {
        str(cat or "Uncategorized"): int(count)
        for cat, count in category_result.all()
    }

    # Get deadline distribution (grouped by month)
    deadline_query = select(
        func.date_trunc('month', Grant.deadline).label('month'),
        func.count(Grant.id).label('count')
    ).filter(Grant.deadline.isnot(None))\
    .group_by(text('month'))\
    .order_by(text('month'))
    
    deadline_result = await db.execute(deadline_query)
    deadlines = {
        row[0].strftime('%Y-%m'): int(row[1])
        for row in deadline_result.all()
        if row[0]
    }

    # Get score distribution (in ranges of 10)
    score_query = select(
        func.floor(Analysis.score * 10).label('range'),
        func.count(Analysis.id).label('count')
    ).select_from(Analysis)\
    .group_by(text('range'))\
    .order_by(text('range'))
    
    score_result = await db.execute(score_query)
    scores = {
        f"{int(range_*10)}-{int((range_+1)*10)}": int(count)
        for range_, count in score_result.all()
    }

    return {
        "categories": categories,
        "deadlines": deadlines,
        "scores": scores
    }

async def save_user_settings(db: AsyncSession, settings_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save user settings using SQLAlchemy."""
    # Get existing settings or create new
    query = select(UserSettings).limit(1)
    result = await db.execute(query)
    settings = result.scalar_one_or_none()
    
    if settings:
        for key, value in settings_data.items():
            setattr(settings, key, value)
    else:
        settings = UserSettings(**settings_data)
        db.add(settings)
    
    await db.commit()
    await db.refresh(settings)
    return settings.to_dict()

async def load_user_settings(db: AsyncSession) -> Dict[str, Any]:
    """Load user settings using SQLAlchemy."""
    query = select(UserSettings).limit(1)
    result = await db.execute(query)
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = UserSettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings.to_dict()

async def search_with_agent(
    db: AsyncSession,
    pinecone: PineconeClient,
    research_agent: Any,
    filters: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Execute grant search with filters using research agent."""
    # Execute search with research agent
    results = await research_agent.search_grants(filters)
    
    # Store results as Grant objects
    for result in results:
        grant = Grant(**result)
        db.add(grant)
        
        if "score" in result:
            analysis = Analysis(grant=grant, score=result["score"])
            db.add(analysis)
    
    await db.commit()
    return results

async def run_full_search_cycle(
    db: AsyncSession,
    pinecone: PineconeClient,
    research_agent: Any
) -> List[Dict[str, Any]]:
    """Run a complete grant search cycle."""
    # Execute search with research agent
    results = await research_agent.search_grants({})
    
    if results:
        # Store results as Grant objects
        for result in results:
            grant = Grant(**result)
            db.add(grant)
            
            if "score" in result:
                analysis = Analysis(grant=grant, score=result["score"])
                db.add(analysis)
        
        await db.commit()
        
        # Record search run
        search_run = SearchRun(
            grants_found=len(results),
            high_priority=len([g for g in results if g.get("score", 0) >= 0.7])
        )
        db.add(search_run)
        await db.commit()
    
    return [g for g in results if g.get("score", 0) >= 0.7]  # Return only high-priority grants

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
        timestamp=datetime.utcnow(), # Use UTC for timestamps
        grants_found=grants_found,
        high_priority=high_priority_found,
        search_filters=search_filters
    )
    db.add(new_search_run)
    await db.commit()
    await db.refresh(new_search_run)
    return new_search_run