"""
Celery task to cleanup expired grants.

Runs weekly on Sunday at 3 AM.
"""
from celery_app import celery_app
from database.models import Grant
from database.session import get_db
from datetime import datetime, timedelta
from sqlalchemy import select
import logging
import asyncio

logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_expired_grants():
    """
    Mark or delete grants past their deadline.

    Strategy:
    - Mark as EXPIRED 30 days after deadline
    - Delete 90 days after deadline (keep some history)

    Returns:
        Dict with cleanup statistics
    """
    try:
        result = asyncio.run(_cleanup_expired_grants_async())
        return result
    except Exception as e:
        logger.error(f"Failed to cleanup expired grants: {str(e)}", exc_info=True)
        raise


async def _cleanup_expired_grants_async():
    """Clean up expired grants asynchronously."""
    async for db in get_db():
        try:
            now = datetime.utcnow()
            expire_threshold = now - timedelta(days=30)  # 30 days past deadline
            delete_threshold = now - timedelta(days=90)  # 90 days past deadline

            # Mark grants as EXPIRED (30 days past deadline)
            result = await db.execute(
                select(Grant).where(
                    Grant.deadline < expire_threshold,
                    Grant.record_status == "ACTIVE"
                )
            )
            grants_to_expire = result.scalars().all()

            expired_count = 0
            for grant in grants_to_expire:
                grant.record_status = "EXPIRED"
                expired_count += 1

            # Delete old expired grants (90 days past deadline)
            result = await db.execute(
                select(Grant).where(
                    Grant.deadline < delete_threshold,
                    Grant.record_status == "EXPIRED"
                )
            )
            grants_to_delete = result.scalars().all()

            deleted_count = 0
            for grant in grants_to_delete:
                await db.delete(grant)
                deleted_count += 1

            await db.commit()

            logger.info(
                f"Cleanup complete: {expired_count} marked expired, "
                f"{deleted_count} deleted"
            )

            return {
                "expired_count": expired_count,
                "deleted_count": deleted_count,
                "expire_threshold": expire_threshold.isoformat(),
                "delete_threshold": delete_threshold.isoformat(),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error cleaning up expired grants: {str(e)}", exc_info=True)
            await db.rollback()
            raise
        finally:
            await db.close()
