"""
Celery tasks for grant searching with DeepSeek reasoning and AgentQL scraping.
Implements thermodynamic prompting for comprehensive grant discovery.
"""

import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from celery import Task

from celery_app import celery_app
from database.session import get_db, AsyncSessionLocal
from database.models import User, Grant, SearchRun, SearchRunType, SearchRunStatus
from services.deepseek_client import get_deepseek_client
from services.resend_client import get_resend_client
from agents.integrated_research_agent import IntegratedResearchAgent
from app.models import GrantFilter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Base task with error callbacks."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Task {task_id} failed: {exc}")
        # Could send failure notification here


@celery_app.task(base=CallbackTask, bind=True, max_retries=3)
def scheduled_grant_search(self, user_id: int, search_params: Dict[str, Any] = None):
    """
    Scheduled grant search for a specific user.
    Uses DeepSeek reasoning and AgentQL scraping.

    Args:
        user_id: User ID to search for
        search_params: Optional search parameters

    Returns:
        Dict with search results and statistics
    """
    try:
        result = asyncio.run(_scheduled_search_async(user_id, search_params))
        return result
    except Exception as e:
        logger.error(f"Scheduled search failed for user {user_id}: {str(e)}")
        self.retry(exc=e, countdown=60)


@celery_app.task(base=CallbackTask, bind=True, max_retries=3)
def manual_grant_search(self, user_id: int, search_params: Dict[str, Any]):
    """
    Manual grant search triggered by user.

    Args:
        user_id: User ID performing search
        search_params: Search parameters from UI

    Returns:
        Dict with search results
    """
    try:
        result = asyncio.run(_manual_search_async(user_id, search_params))
        return result
    except Exception as e:
        logger.error(f"Manual search failed for user {user_id}: {str(e)}")
        self.retry(exc=e, countdown=30)


@celery_app.task
def run_scheduled_searches():
    """
    Run scheduled searches for all active users based on their preferences.
    Called by Celery Beat every 6 hours.
    """
    try:
        result = asyncio.run(_run_all_scheduled_searches())
        return result
    except Exception as e:
        logger.error(f"Failed to run scheduled searches: {str(e)}")
        raise


async def _run_all_scheduled_searches() -> Dict[str, Any]:
    """Run searches for all active users who are due for a search."""
    async for db in get_db():
        try:
            # Get all active users with subscriptions
            result = await db.execute(
                select(User).where(
                    User.is_active == True,
                    User.subscription_status.in_(["active", "trialing"])
                )
            )
            users = result.scalars().all()

            total_users = len(users)
            searches_triggered = 0
            searches_skipped = 0

            for user in users:
                # Check if user has searches remaining
                if user.searches_used >= user.searches_limit:
                    logger.info(f"User {user.id} has no searches remaining")
                    searches_skipped += 1
                    continue

                # Check user settings for search frequency
                # For now, run for all active users
                try:
                    scheduled_grant_search.delay(user.id)
                    searches_triggered += 1
                except Exception as e:
                    logger.error(f"Failed to trigger search for user {user.id}: {e}")

            logger.info(f"Scheduled searches: {searches_triggered} triggered, {searches_skipped} skipped")

            return {
                "total_users": total_users,
                "searches_triggered": searches_triggered,
                "searches_skipped": searches_skipped,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error in scheduled searches: {str(e)}")
            raise
        finally:
            await db.close()


async def _scheduled_search_async(user_id: int, search_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute scheduled search with DeepSeek reasoning.

    Args:
        user_id: User ID
        search_params: Optional search parameters

    Returns:
        Search results dict
    """
    async for db in get_db():
        try:
            start_time = datetime.utcnow()

            # Load user
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                raise Exception(f"User {user_id} not found")

            # Check usage limit
            if user.searches_used >= user.searches_limit:
                raise Exception(f"User {user_id} has exceeded search limit")

            # Create search run record
            search_run = SearchRun(
                user_id=user_id,
                run_type=SearchRunType.SCHEDULED,
                status=SearchRunStatus.IN_PROGRESS,
                search_filters=search_params or {}
            )
            db.add(search_run)
            await db.commit()
            await db.refresh(search_run)

            # Step 1: Use DeepSeek for reasoning-based search strategy
            deepseek = get_deepseek_client()

            business_context = ""
            if user.business_profile:
                business_context = f"""
                Business: {user.business_profile.business_name}
                Sectors: {', '.join(user.business_profile.target_sectors or [])}
                Geographic Focus: {user.business_profile.geographic_focus or 'Not specified'}
                """

            query = search_params.get("query", "telecommunications and women-owned nonprofit grants")

            logger.info(f"Starting reasoning search for user {user_id}")
            reasoning_result = await deepseek.search_with_reasoning(
                query=query,
                context=business_context,
                search_depth="standard"
            )

            # Step 2: Execute grant discovery
            # TODO: Integrate with AgentQL for actual scraping
            # For now, simulate grant discovery
            grants_found = await _discover_grants_with_reasoning(
                db=db,
                user=user,
                reasoning=reasoning_result["reasoning"],
                search_params=search_params or {}
            )

            # Update search run
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            search_run.status = SearchRunStatus.SUCCESS
            search_run.grants_found = len(grants_found)
            search_run.duration_seconds = duration
            search_run.high_priority = sum(1 for g in grants_found if g.get("priority") == "high")

            # Increment search counter
            user.searches_used += 1

            await db.commit()

            # Send post-run summary email (always)
            high_priority_grants = [g for g in grants_found if g.get("priority") == "high"]
            searches_remaining = user.searches_limit - user.searches_used
            resend = get_resend_client()

            try:
                await resend.send_search_complete_email(
                    user_email=user.email,
                    user_name=user.full_name or user.email,
                    grants_found=len(grants_found),
                    high_priority=len(high_priority_grants),
                    duration_seconds=duration,
                    searches_remaining=searches_remaining,
                )
            except Exception as e:
                logger.error(f"Failed to send search complete email: {e}")

            # Also send detailed grant alert if high-priority grants found
            if high_priority_grants:
                try:
                    await resend.send_grant_alert(
                        user_email=user.email,
                        user_name=user.full_name or user.email,
                        grants=high_priority_grants
                    )
                except Exception as e:
                    logger.error(f"Failed to send grant alert email: {e}")

            logger.info(f"Search completed for user {user_id}: {len(grants_found)} grants found")

            return {
                "user_id": user_id,
                "search_run_id": search_run.id,
                "grants_found": len(grants_found),
                "high_priority": len(high_priority_grants),
                "duration_seconds": duration,
                "searches_used": user.searches_used,
                "searches_remaining": user.searches_limit - user.searches_used
            }

        except Exception as e:
            # Update search run as failed
            if 'search_run' in locals():
                search_run.status = SearchRunStatus.FAILED
                search_run.error_message = str(e)
                await db.commit()

            logger.error(f"Scheduled search failed for user {user_id}: {str(e)}")
            raise
        finally:
            await db.close()


async def _manual_search_async(user_id: int, search_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute manual search triggered by user.
    Similar to scheduled search but with user-specified parameters.
    """
    async for db in get_db():
        try:
            # Similar implementation to scheduled search
            # but with MANUAL run type and custom search params
            return await _scheduled_search_async(user_id, search_params)

        except Exception as e:
            logger.error(f"Manual search failed: {str(e)}")
            raise
        finally:
            await db.close()


async def _discover_grants_with_reasoning(
    db: AsyncSession,
    user: User,
    reasoning: str,
    search_params: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Discover grants using DeepSeek via the IntegratedResearchAgent pipeline.

    Pipeline:
    1. Build GrantFilter from user profile + search params
    2. IntegratedResearchAgent uses RecursiveResearchAgent internally
    3. RecursiveResearchAgent calls DeepSeek with chunked queries
    4. Grants are scored, deduplicated, and stored in Postgres

    Args:
        db: Database session
        user: User object
        reasoning: DeepSeek reasoning output
        search_params: Search parameters

    Returns:
        List of grant dictionaries
    """
    logger.info("Discovering grants with DeepSeek reasoning pipeline")
    logger.info(f"Reasoning strategy: {reasoning[:200]}...")

    # Build GrantFilter from user profile and search params
    keywords = search_params.get("query", "")
    geographic_focus = None
    target_sectors = []

    if user.business_profile:
        geographic_focus = user.business_profile.geographic_focus
        target_sectors = user.business_profile.target_sectors or []
        if not keywords:
            keywords = ", ".join(target_sectors[:3]) if target_sectors else "grants"

    grant_filter = GrantFilter(
        keywords=keywords,
        min_score=0.0,
        min_funding=search_params.get("min_funding", 5000),
        max_funding=search_params.get("max_funding", 1000000),
        geographic_focus=geographic_focus,
    )

    # Use the IntegratedResearchAgent (wraps RecursiveResearchAgent + DeepSeek)
    try:
        research_agent = IntegratedResearchAgent(AsyncSessionLocal)
        enriched_grants = await research_agent.search_grants(grant_filter)
        logger.info(f"Research agent returned {len(enriched_grants)} grants")
    except Exception as e:
        logger.error(f"Research agent search failed: {e}", exc_info=True)
        enriched_grants = []

    # Convert EnrichedGrant objects → dicts and store in database
    grants_discovered = []
    for eg in enriched_grants:
        try:
            # Check for existing grant by title
            existing = await db.execute(
                select(Grant).where(Grant.title == eg.title, Grant.user_id == user.id)
            )
            if existing.scalar_one_or_none():
                logger.info(f"Skipping duplicate grant: {eg.title}")
                continue

            # Store in database
            db_grant = Grant(
                user_id=user.id,
                title=eg.title,
                description=eg.description or "",
                summary_llm=eg.summary_llm,
                eligibility_summary_llm=eg.eligibility_summary_llm,
                funder_name=eg.funder_name,
                funding_amount=eg.funding_amount_min or 0,
                funding_amount_min=eg.funding_amount_min,
                funding_amount_max=eg.funding_amount_max,
                funding_amount_display=eg.funding_amount_display,
                deadline=eg.deadline_date,
                deadline_date=eg.deadline_date,
                source_url=eg.source_url,
                source_name=eg.source_name,
                identified_sector=eg.identified_sector,
                geographic_scope=eg.geographic_scope,
                overall_composite_score=eg.overall_composite_score,
                keywords_json=eg.keywords,
                categories_project_json=eg.categories_project,
                record_status="ACTIVE",
            )
            db.add(db_grant)
            await db.flush()

            # Determine priority
            score = eg.overall_composite_score or 0
            priority = "high" if score >= 0.7 else ("medium" if score >= 0.4 else "low")

            grants_discovered.append({
                "id": db_grant.id,
                "title": eg.title,
                "description": eg.description,
                "funding_amount_display": eg.funding_amount_display,
                "deadline": eg.deadline_date.isoformat() if eg.deadline_date else None,
                "source_url": eg.source_url,
                "priority": priority,
                "overall_composite_score": score,
                "summary_llm": eg.summary_llm,
                "funder_name": eg.funder_name,
            })

        except Exception as e:
            logger.error(f"Failed to process grant '{getattr(eg, 'title', '?')}': {e}")
            continue

    await db.commit()
    logger.info(f"Stored {len(grants_discovered)} new grants for user {user.id}")
    return grants_discovered


@celery_app.task
def bulk_grant_analysis(user_id: int, grant_ids: List[int]):
    """
    Analyze multiple grants in bulk for a user.

    Args:
        user_id: User ID
        grant_ids: List of grant IDs to analyze

    Returns:
        Analysis results
    """
    try:
        result = asyncio.run(_bulk_analysis_async(user_id, grant_ids))
        return result
    except Exception as e:
        logger.error(f"Bulk analysis failed: {str(e)}")
        raise


async def _bulk_analysis_async(user_id: int, grant_ids: List[int]) -> Dict[str, Any]:
    """Execute bulk grant analysis."""
    async for db in get_db():
        try:
            deepseek = get_deepseek_client()
            analyzed_count = 0

            for grant_id in grant_ids:
                try:
                    # Load grant
                    result = await db.execute(select(Grant).where(Grant.id == grant_id))
                    grant = result.scalar_one_or_none()

                    if not grant:
                        continue

                    # Analyze with DeepSeek
                    analysis = await deepseek.analyze_grant(
                        grant_data=grant.__dict__,
                        business_context=None  # Could load user's business profile
                    )

                    # Update grant with analysis scores
                    if "relevance_score" in analysis:
                        grant.overall_composite_score = analysis["relevance_score"]

                    analyzed_count += 1

                except Exception as e:
                    logger.error(f"Failed to analyze grant {grant_id}: {e}")
                    continue

            await db.commit()

            return {
                "user_id": user_id,
                "total_grants": len(grant_ids),
                "analyzed": analyzed_count,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Bulk analysis failed: {str(e)}")
            raise
        finally:
            await db.close()
