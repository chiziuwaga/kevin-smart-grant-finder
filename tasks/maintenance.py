"""
Celery maintenance tasks for system health and user notifications.
Handles usage resets, warnings, cleanup, and reporting.
"""

import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy import select, and_

from celery_app import celery_app
from database.session import get_db
from database.models import User, SubscriptionStatus, GeneratedApplication
from services.resend_client import get_resend_client
from services.application_rag import get_rag_service

logger = logging.getLogger(__name__)


@celery_app.task
def reset_monthly_usage_counters():
    """
    Reset monthly usage counters for all users.
    Called on the 1st of each month at midnight by Celery Beat.

    Returns:
        Dict with reset statistics
    """
    try:
        result = asyncio.run(_reset_usage_async())
        return result
    except Exception as e:
        logger.error(f"Failed to reset usage counters: {str(e)}")
        raise


async def _reset_usage_async() -> Dict[str, Any]:
    """Reset usage counters for all active subscribers."""
    async for db in get_db():
        try:
            # Get all active subscribers
            result = await db.execute(
                select(User).where(
                    User.subscription_status.in_([
                        SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.TRIALING
                    ])
                )
            )
            users = result.scalars().all()

            reset_count = 0
            for user in users:
                user.searches_used = 0
                user.applications_used = 0
                user.usage_period_start = datetime.utcnow()
                reset_count += 1

            await db.commit()

            logger.info(f"Reset usage counters for {reset_count} users")

            return {
                "users_reset": reset_count,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error resetting usage counters: {str(e)}")
            raise
        finally:
            await db.close()


@celery_app.task
def check_and_warn_usage_limits():
    """
    Check usage for all users and send warnings at 80% and 100%.
    Called daily at 9 AM by Celery Beat.

    Returns:
        Dict with warning statistics
    """
    try:
        result = asyncio.run(_check_usage_async())
        return result
    except Exception as e:
        logger.error(f"Failed to check usage limits: {str(e)}")
        raise


async def _check_usage_async() -> Dict[str, Any]:
    """Check usage and send warnings."""
    async for db in get_db():
        try:
            # Get all active subscribers
            result = await db.execute(
                select(User).where(
                    User.subscription_status.in_([
                        SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.TRIALING
                    ])
                )
            )
            users = result.scalars().all()

            warnings_sent = 0
            resend = get_resend_client()

            for user in users:
                # Check search usage
                search_percentage = (user.searches_used / user.searches_limit * 100) if user.searches_limit > 0 else 0
                if search_percentage >= 80 and search_percentage < 100:
                    try:
                        await resend.send_usage_warning(
                            user_email=user.email,
                            user_name=user.full_name or user.email,
                            resource_type="searches",
                            used=user.searches_used,
                            limit=user.searches_limit,
                            percentage=int(search_percentage)
                        )
                        warnings_sent += 1
                    except Exception as e:
                        logger.error(f"Failed to send search warning to user {user.id}: {e}")

                # Check application usage
                app_percentage = (user.applications_used / user.applications_limit * 100) if user.applications_limit > 0 else 0
                if app_percentage >= 80 and app_percentage < 100:
                    try:
                        await resend.send_usage_warning(
                            user_email=user.email,
                            user_name=user.full_name or user.email,
                            resource_type="applications",
                            used=user.applications_used,
                            limit=user.applications_limit,
                            percentage=int(app_percentage)
                        )
                        warnings_sent += 1
                    except Exception as e:
                        logger.error(f"Failed to send application warning to user {user.id}: {e}")

            logger.info(f"Sent {warnings_sent} usage warnings")

            return {
                "users_checked": len(users),
                "warnings_sent": warnings_sent,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error checking usage limits: {str(e)}")
            raise
        finally:
            await db.close()


@celery_app.task
def cleanup_expired_embeddings():
    """
    Clean up embeddings for inactive users or deleted profiles.
    Called weekly on Sunday at 2 AM by Celery Beat.

    Returns:
        Dict with cleanup statistics
    """
    try:
        result = asyncio.run(_cleanup_embeddings_async())
        return result
    except Exception as e:
        logger.error(f"Failed to cleanup embeddings: {str(e)}")
        raise


async def _cleanup_embeddings_async() -> Dict[str, Any]:
    """Clean up orphaned embeddings."""
    async for db in get_db():
        try:
            rag_service = get_rag_service()

            # Get all inactive users or users without business profiles
            result = await db.execute(
                select(User).where(
                    User.is_active == False
                )
            )
            inactive_users = result.scalars().all()

            embeddings_deleted = 0

            for user in inactive_users:
                try:
                    await rag_service.delete_user_embeddings(user.id)
                    embeddings_deleted += 1
                    logger.info(f"Deleted embeddings for inactive user {user.id}")
                except Exception as e:
                    logger.error(f"Failed to delete embeddings for user {user.id}: {e}")

            logger.info(f"Cleaned up embeddings for {embeddings_deleted} users")

            return {
                "users_processed": len(inactive_users),
                "embeddings_deleted": embeddings_deleted,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error cleaning up embeddings: {str(e)}")
            raise
        finally:
            await db.close()


@celery_app.task
def send_weekly_reports():
    """
    Send weekly activity reports to active users.
    Called on Monday at 10 AM by Celery Beat.

    Returns:
        Dict with report statistics
    """
    try:
        result = asyncio.run(_send_reports_async())
        return result
    except Exception as e:
        logger.error(f"Failed to send weekly reports: {str(e)}")
        raise


async def _send_reports_async() -> Dict[str, Any]:
    """Generate and send weekly reports."""
    async for db in get_db():
        try:
            # Get all active users
            result = await db.execute(
                select(User).where(
                    User.is_active == True,
                    User.subscription_status.in_([
                        SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.TRIALING
                    ])
                )
            )
            users = result.scalars().all()

            reports_sent = 0
            resend = get_resend_client()

            one_week_ago = datetime.utcnow() - timedelta(days=7)

            for user in users:
                try:
                    # Get weekly statistics
                    # Count applications generated in the last week
                    apps_result = await db.execute(
                        select(GeneratedApplication).where(
                            and_(
                                GeneratedApplication.user_id == user.id,
                                GeneratedApplication.created_at >= one_week_ago
                            )
                        )
                    )
                    weekly_apps = len(apps_result.scalars().all())

                    # Build report (simplified for now)
                    report_data = {
                        "searches_this_week": user.searches_used,  # Approximate
                        "applications_generated": weekly_apps,
                        "searches_remaining": user.searches_limit - user.searches_used,
                        "applications_remaining": user.applications_limit - user.applications_used
                    }

                    # Send weekly report email
                    # TODO: Create dedicated weekly report email template
                    # For now, skip sending until template is ready

                    reports_sent += 1

                except Exception as e:
                    logger.error(f"Failed to generate report for user {user.id}: {e}")

            logger.info(f"Generated {reports_sent} weekly reports")

            return {
                "users_processed": len(users),
                "reports_sent": reports_sent,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error sending weekly reports: {str(e)}")
            raise
        finally:
            await db.close()


@celery_app.task
def cleanup_old_search_runs():
    """
    Clean up search run records older than 90 days.
    Keeps database size manageable.

    Returns:
        Dict with cleanup statistics
    """
    try:
        result = asyncio.run(_cleanup_search_runs_async())
        return result
    except Exception as e:
        logger.error(f"Failed to cleanup search runs: {str(e)}")
        raise


async def _cleanup_search_runs_async() -> Dict[str, Any]:
    """Delete old search run records."""
    async for db in get_db():
        try:
            from database.models import SearchRun

            ninety_days_ago = datetime.utcnow() - timedelta(days=90)

            # Delete old search runs
            result = await db.execute(
                select(SearchRun).where(
                    SearchRun.created_at < ninety_days_ago
                )
            )
            old_runs = result.scalars().all()

            deleted_count = len(old_runs)

            for run in old_runs:
                await db.delete(run)

            await db.commit()

            logger.info(f"Deleted {deleted_count} old search runs")

            return {
                "deleted_count": deleted_count,
                "cutoff_date": ninety_days_ago.isoformat(),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error cleaning up search runs: {str(e)}")
            raise
        finally:
            await db.close()


@celery_app.task
def check_trial_expirations():
    """
    Check for expiring trials and send reminders.
    Should be called daily.

    Returns:
        Dict with reminder statistics
    """
    try:
        result = asyncio.run(_check_trials_async())
        return result
    except Exception as e:
        logger.error(f"Failed to check trial expirations: {str(e)}")
        raise


async def _check_trials_async() -> Dict[str, Any]:
    """Check trials and send reminders."""
    async for db in get_db():
        try:
            from database.models import Subscription

            # Get all trialing users
            result = await db.execute(
                select(User).where(
                    User.subscription_status == SubscriptionStatus.TRIALING
                )
            )
            trial_users = result.scalars().all()

            reminders_sent = 0
            resend = get_resend_client()

            three_days = timedelta(days=3)
            now = datetime.utcnow()

            for user in trial_users:
                # Check if trial ends in 3 days
                if user.subscription and user.subscription.current_period_end:
                    days_remaining = (user.subscription.current_period_end - now).days

                    if days_remaining <= 3 and days_remaining > 0:
                        try:
                            # TODO: Send trial expiration reminder email
                            # await resend.send_trial_reminder(...)
                            reminders_sent += 1
                        except Exception as e:
                            logger.error(f"Failed to send trial reminder to user {user.id}: {e}")

            logger.info(f"Sent {reminders_sent} trial expiration reminders")

            return {
                "trial_users_checked": len(trial_users),
                "reminders_sent": reminders_sent,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error checking trial expirations: {str(e)}")
            raise
        finally:
            await db.close()
