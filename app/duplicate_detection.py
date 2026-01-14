"""
Duplicate grant detection utility.

Implements multiple strategies to identify duplicate grants:
1. Exact URL matching (primary)
2. Title + Deadline combination
3. Fuzzy title matching (85% similarity)
"""
import logging
from typing import Optional
from difflib import SequenceMatcher
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Grant as DBGrant

logger = logging.getLogger(__name__)


async def check_duplicate_grant(
    db: AsyncSession,
    grant_data: dict
) -> Optional[DBGrant]:
    """
    Check for duplicate grants using multiple strategies.

    Strategy 1: Exact URL match (most reliable)
    Strategy 2: Title + Deadline match (for same grant on different sites)
    Strategy 3: Fuzzy title matching for similar grants (85% threshold)

    Args:
        db: Database session
        grant_data: Grant dictionary with title, source_url, deadline

    Returns:
        Existing grant if duplicate found, None otherwise
    """
    source_url = grant_data.get('source_url', '').strip()
    title = grant_data.get('title', '').strip()
    deadline = grant_data.get('deadline')

    # Strategy 1: Exact URL match (most reliable)
    if source_url:
        result = await db.execute(
            select(DBGrant).where(DBGrant.source_url == source_url)
        )
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(f"Duplicate detected via URL: {source_url}")
            return existing

    # Strategy 2: Title + Deadline match (for same grant on different sites)
    if title and deadline:
        result = await db.execute(
            select(DBGrant).where(
                DBGrant.title == title,
                DBGrant.deadline == deadline
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(f"Duplicate detected via Title+Deadline: {title}")
            return existing

    # Strategy 3: Fuzzy title matching for similar grants
    if title and len(title) > 30:  # Only for titles > 30 chars
        # Search for grants with similar titles (first 30 chars)
        result = await db.execute(
            select(DBGrant).where(DBGrant.title.ilike(f"%{title[:30]}%"))
        )
        candidates = result.scalars().all()

        for candidate in candidates:
            similarity = SequenceMatcher(
                None,
                title.lower(),
                candidate.title.lower()
            ).ratio()

            if similarity > 0.85:  # 85% similarity threshold
                logger.info(
                    f"Duplicate detected via fuzzy match ({similarity:.2%}): "
                    f"{title} ~= {candidate.title}"
                )
                return candidate

    # No duplicate found
    return None


def normalize_url(url: str) -> str:
    """
    Normalize URL for comparison.

    Removes:
    - Trailing slashes
    - www. prefix
    - Query parameters (optional)
    - Fragments (#)

    Args:
        url: URL to normalize

    Returns:
        Normalized URL
    """
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(url.lower().strip())

    # Remove www. prefix
    netloc = parsed.netloc
    if netloc.startswith('www.'):
        netloc = netloc[4:]

    # Remove query and fragment
    normalized = urlunparse((
        parsed.scheme,
        netloc,
        parsed.path.rstrip('/'),
        '',  # params
        '',  # query (optional: can keep this for grant-specific URLs)
        ''   # fragment
    ))

    return normalized


async def update_duplicate_grant(
    db: AsyncSession,
    existing_grant: DBGrant,
    new_grant_data: dict
) -> DBGrant:
    """
    Update existing grant with new data if it's more recent.

    Args:
        db: Database session
        existing_grant: Existing grant in database
        new_grant_data: New grant data to potentially update with

    Returns:
        Updated grant
    """
    # Update fields if new data is more complete
    fields_to_update = [
        'description',
        'eligibility',
        'requirements',
        'amount',
        'deadline',
        'application_url',
        'contact_info'
    ]

    updated = False
    for field in fields_to_update:
        new_value = new_grant_data.get(field)
        existing_value = getattr(existing_grant, field, None)

        # Update if new value is more complete
        if new_value and (not existing_value or len(str(new_value)) > len(str(existing_value))):
            setattr(existing_grant, field, new_value)
            updated = True

    if updated:
        logger.info(f"Updated duplicate grant: {existing_grant.title}")
        await db.commit()
        await db.refresh(existing_grant)

    return existing_grant
