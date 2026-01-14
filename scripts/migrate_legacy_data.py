"""
Data Migration Script: Migrate Legacy Data to Multi-User Schema

This script helps migrate existing data after running the database schema migration.
It handles:
1. Creating a default system user for legacy data
2. Assigning legacy grants to the system user
3. Assigning legacy search runs to the system user
4. Migrating old application_history string user IDs to integer FKs

Usage:
    python scripts/migrate_legacy_data.py --dry-run  # Preview changes
    python scripts/migrate_legacy_data.py            # Execute migration

Requirements:
    - Database migration e4f7a9b2c3d1 must be applied first
    - Environment variables must be set (DATABASE_URL or DB_* vars)
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from config.settings import get_settings
from database.models import User, Grant, SearchRun, ApplicationHistory


async def create_system_user(db: AsyncSession, dry_run: bool = False) -> User:
    """
    Create a system user for legacy data.

    Args:
        db: Database session
        dry_run: If True, don't commit changes

    Returns:
        System user object
    """
    print("\n=== Step 1: Creating System User ===")

    # Check if system user already exists
    result = await db.execute(
        select(User).where(User.email == "system@grantfinder.internal")
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        print(f"✓ System user already exists (ID: {existing_user.id})")
        return existing_user

    # Create system user
    system_user = User(
        auth0_id="system_internal",
        email="system@grantfinder.internal",
        full_name="System User (Legacy Data)",
        company_name="Grant Finder System",
        subscription_tier="admin",
        subscription_status="ACTIVE",
        is_active=True,
        is_admin=True,
        searches_limit=999999,
        applications_limit=999999,
    )

    if dry_run:
        print(f"[DRY RUN] Would create system user: {system_user.email}")
        # For dry run, assign a temporary ID
        system_user.id = -1
    else:
        db.add(system_user)
        await db.flush()  # Flush to get the ID
        print(f"✓ Created system user (ID: {system_user.id})")

    return system_user


async def migrate_legacy_grants(db: AsyncSession, system_user: User, dry_run: bool = False):
    """
    Assign legacy grants (user_id = NULL) to system user.

    Args:
        db: Database session
        system_user: System user object
        dry_run: If True, don't commit changes
    """
    print("\n=== Step 2: Migrating Legacy Grants ===")

    # Count legacy grants
    result = await db.execute(
        select(func.count()).select_from(Grant).where(Grant.user_id.is_(None))
    )
    count = result.scalar()

    if count == 0:
        print("✓ No legacy grants found (all grants have user_id)")
        return

    print(f"Found {count} legacy grants without user_id")

    if dry_run:
        print(f"[DRY RUN] Would assign {count} grants to system user (ID: {system_user.id})")
    else:
        # Update grants to assign to system user
        await db.execute(
            update(Grant)
            .where(Grant.user_id.is_(None))
            .values(user_id=system_user.id)
        )
        print(f"✓ Assigned {count} legacy grants to system user")


async def migrate_legacy_search_runs(db: AsyncSession, system_user: User, dry_run: bool = False):
    """
    Assign legacy search runs (user_id = NULL) to system user.

    Args:
        db: Database session
        system_user: System user object
        dry_run: If True, don't commit changes
    """
    print("\n=== Step 3: Migrating Legacy Search Runs ===")

    # Count legacy search runs
    result = await db.execute(
        select(func.count()).select_from(SearchRun).where(SearchRun.user_id.is_(None))
    )
    count = result.scalar()

    if count == 0:
        print("✓ No legacy search runs found (all runs have user_id)")
        return

    print(f"Found {count} legacy search runs without user_id")

    if dry_run:
        print(f"[DRY RUN] Would assign {count} search runs to system user (ID: {system_user.id})")
    else:
        # Update search runs to assign to system user
        await db.execute(
            update(SearchRun)
            .where(SearchRun.user_id.is_(None))
            .values(user_id=system_user.id)
        )
        print(f"✓ Assigned {count} legacy search runs to system user")


async def migrate_application_history_users(db: AsyncSession, system_user: User, dry_run: bool = False):
    """
    Migrate old string user IDs to new integer user FKs in application_history.

    This function attempts several strategies to match old user IDs:
    1. Exact email match
    2. Partial email match
    3. Fallback to system user

    Args:
        db: Database session
        system_user: System user object
        dry_run: If True, don't commit changes
    """
    print("\n=== Step 4: Migrating Application History User IDs ===")

    # Get all application_history records with old user_id but no new user_id
    result = await db.execute(
        select(ApplicationHistory).where(
            ApplicationHistory.user_id.is_(None),
            ApplicationHistory.user_id_old.isnot(None)
        )
    )
    records = result.scalars().all()

    if not records:
        print("✓ No application history records need migration")
        return

    print(f"Found {len(records)} application history records to migrate")

    # Get all users for matching
    all_users_result = await db.execute(select(User))
    all_users = {user.email: user for user in all_users_result.scalars().all()}

    migrated_count = 0
    fallback_count = 0
    not_found = []

    for record in records:
        old_id = record.user_id_old
        matched_user = None

        # Strategy 1: Assume old_id is email (exact match)
        if old_id in all_users:
            matched_user = all_users[old_id]
            print(f"  ✓ Matched '{old_id}' -> User '{matched_user.email}' (ID: {matched_user.id})")
            migrated_count += 1

        # Strategy 2: Partial email match (old_id might be username part)
        elif '@' not in old_id:
            for email, user in all_users.items():
                if email.startswith(old_id + '@'):
                    matched_user = user
                    print(f"  ✓ Partial match '{old_id}' -> User '{user.email}' (ID: {user.id})")
                    migrated_count += 1
                    break

        # Strategy 3: Fallback to system user
        if not matched_user:
            matched_user = system_user
            not_found.append(old_id)
            fallback_count += 1
            print(f"  ⚠ No match for '{old_id}', assigning to system user")

        if not dry_run:
            record.user_id = matched_user.id

    print(f"\nMigration Summary:")
    print(f"  ✓ Matched users: {migrated_count}")
    print(f"  ⚠ Fallback to system user: {fallback_count}")

    if not_found:
        print(f"\nUnmatched old user IDs (assigned to system user):")
        for old_id in not_found[:10]:  # Show first 10
            print(f"    - {old_id}")
        if len(not_found) > 10:
            print(f"    ... and {len(not_found) - 10} more")

    if dry_run:
        print(f"\n[DRY RUN] Would update {len(records)} application history records")
    else:
        print(f"✓ Updated {len(records)} application history records")


async def run_migration(dry_run: bool = False):
    """
    Run the complete data migration.

    Args:
        dry_run: If True, preview changes without committing
    """
    settings = get_settings()

    # Create async engine
    engine = create_async_engine(
        settings.db_url,
        echo=settings.app_debug,
        future=True,
    )

    # Create async session
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    print("=" * 70)
    print("Legacy Data Migration Script")
    print("=" * 70)

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be committed")
    else:
        print("\n⚠️  LIVE MODE - Changes will be committed to database")
        print("Press Ctrl+C within 5 seconds to cancel...")
        await asyncio.sleep(5)

    print(f"\nConnecting to database: {settings.db_name}@{settings.db_host}")

    try:
        async with async_session() as db:
            # Step 1: Create or get system user
            system_user = await create_system_user(db, dry_run)

            # Step 2: Migrate legacy grants
            await migrate_legacy_grants(db, system_user, dry_run)

            # Step 3: Migrate legacy search runs
            await migrate_legacy_search_runs(db, system_user, dry_run)

            # Step 4: Migrate application history users
            await migrate_application_history_users(db, system_user, dry_run)

            # Commit all changes
            if not dry_run:
                await db.commit()
                print("\n✓ All changes committed successfully")
            else:
                print("\n[DRY RUN] No changes were committed")

        print("\n" + "=" * 70)
        print("Migration completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        await engine.dispose()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate legacy data to multi-user schema"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without committing to database"
    )

    args = parser.parse_args()

    # Run the async migration
    asyncio.run(run_migration(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
