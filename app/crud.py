from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Grant, Analysis, SearchRun, UserSettings
from utils.pinecone_client import PineconeClient

async def fetch_grants(
    db: AsyncSession,
    pinecone: PineconeClient,
    min_score: float = 0.0,
    category: Optional[str] = None,
    deadline_before: Optional[str] = None
) -> List[Grant]:
    """Fetch grants with optional filtering using SQLAlchemy."""
    query = select(Grant).join(Analysis)
    
    if min_score > 0:
        query = query.filter(Analysis.score >= min_score)
    
    if category:
        query = query.filter(Grant.category == category)
    
    if deadline_before:
        deadline = datetime.fromisoformat(deadline_before)
        query = query.filter(Grant.deadline <= deadline)
    
    result = await db.execute(query)
    return result.scalars().all()

async def fetch_stats(db: AsyncSession) -> Dict[str, Any]:
    """Get dashboard statistics using SQLAlchemy."""
    # Get total grants
    total_query = select(func.count()).select_from(Grant)
    total_result = await db.execute(total_query)
    total = total_result.scalar()

    # Get high priority grants (score >= 0.7)
    high_priority_query = select(func.count())\
        .select_from(Grant)\
        .join(Analysis)\
        .filter(Analysis.score >= 0.7)
    high_priority_result = await db.execute(high_priority_query)
    high_priority = high_priority_result.scalar()

    # Get distinct categories
    categories_query = select(Grant.category).distinct()
    categories_result = await db.execute(categories_query)
    categories = categories_result.scalars().all()

    return {
        "total_grants": total,
        "high_priority": high_priority,
        "categories": categories,
        "last_updated": datetime.now().isoformat()
    }

async def fetch_distribution(db: AsyncSession) -> Dict[str, Any]:
    """Get grant distribution data using SQLAlchemy."""
    # Category distribution
    category_query = select(
        Grant.category,
        func.count(Grant.id).label('count')
    ).group_by(Grant.category).order_by(text('count DESC'))
    
    category_result = await db.execute(category_query)
    categories = [
        {"_id": cat, "count": count}
        for cat, count in category_result.all()
    ]

    # Deadline distribution
    deadline_query = select(
        func.date_trunc('month', Grant.deadline).label('month'),
        func.count(Grant.id).label('count')
    ).group_by(text('month')).order_by(text('month'))
    
    deadline_result = await db.execute(deadline_query)
    deadlines = [
        {"_id": month.strftime("%Y-%m"), "count": count}
        for month, count in deadline_result.all()
    ]

    return {
        "categories": categories,
        "deadlines": deadlines
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