# Database Migration Guide: Multi-User Support

## Overview

This guide covers the database migration to add comprehensive multi-user support with Auth0 authentication, Stripe subscriptions, and RAG-based AI application generation.

**Migration File**: `migrations/versions/e4f7a9b2c3d1_add_multi_user_support_with_auth0_and_stripe.py`

**Revision ID**: `e4f7a9b2c3d1`

**Revises**: `d896bf2738fb`

## What This Migration Does

### New Tables Created

1. **users** - User accounts with Auth0 authentication
   - Auth0 ID and email (unique indexes)
   - Subscription tier and status
   - Usage tracking (searches/applications used and limits)
   - Account status flags (is_active, is_admin)
   - Timestamps (created_at, updated_at, last_login)

2. **business_profiles** - Business profiles for RAG-based application generation
   - One-to-one relationship with users
   - Business information (name, mission, services, website)
   - Business details (sectors, revenue, years in operation, team size)
   - Narrative text (2000 char limit for RAG)
   - Document uploads tracking (files, sizes)
   - Vector embeddings references (Pinecone integration)

3. **subscriptions** - Stripe subscription management
   - One-to-one relationship with users
   - Stripe customer and subscription IDs (unique indexes)
   - Plan details (name, amount, currency)
   - Subscription status (using SubscriptionStatus enum)
   - Billing period tracking
   - Usage limits and remaining quota
   - Cancellation management

4. **generated_applications** - AI-generated grant applications
   - Many-to-one relationship with users and grants
   - Generated content and structured sections (JSON)
   - Application status (using ApplicationGenerationStatus enum)
   - User feedback and edit tracking
   - Generation metadata (model, time, tokens)

### Updated Tables

1. **grants** - Added user_id foreign key
   - Nullable for backward compatibility with legacy data
   - Indexed for performance
   - CASCADE delete when user is deleted

2. **search_runs** - Added user_id foreign key and enhanced tracking
   - Nullable user_id for legacy searches
   - New columns: run_type, status, duration, error details
   - Performance metrics (sources_searched, api_calls_made)
   - Indexed for performance

3. **application_history** - Updated user_id to proper foreign key
   - Changed from String to Integer FK
   - Old string user_id preserved as user_id_old (for data migration)
   - CASCADE delete when user is deleted

4. **user_settings** - Ensured proper foreign key constraint
   - Already had user_id, just ensuring FK relationship

### New Enum Types

1. **SubscriptionStatus**: ACTIVE, CANCELED, PAST_DUE, TRIALING, INCOMPLETE, INCOMPLETE_EXPIRED, UNPAID
2. **ApplicationGenerationStatus**: DRAFT, GENERATED, EDITED, SUBMITTED, AWARDED, REJECTED
3. **SearchRunType**: AUTOMATED, MANUAL, SCHEDULED
4. **SearchRunStatus**: SUCCESS, FAILED, PARTIAL, IN_PROGRESS

### Indexes Created

Performance indexes on:
- users: auth0_id (unique), email (unique)
- business_profiles: user_id (unique)
- subscriptions: user_id (unique), stripe_customer_id (unique), stripe_subscription_id (unique)
- generated_applications: user_id, grant_id
- grants: user_id
- search_runs: user_id
- application_history: user_id

## Prerequisites

Before running the migration:

1. **Backup your database**:
   ```bash
   pg_dump -U postgres -h localhost -d grantfinder > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Ensure all dependencies are installed**:
   ```bash
   pip install alembic sqlalchemy asyncpg psycopg2-binary python-dotenv
   ```

3. **Set environment variables** in `.env`:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/grantfinder
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_NAME=grantfinder
   ```

4. **Verify Alembic configuration**:
   ```bash
   alembic current
   ```

## Running the Migration

### Step 1: Check Current Database State

```bash
# Show current migration version
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic heads
```

Expected output: Current revision should be `d896bf2738fb`

### Step 2: Dry Run (Recommended)

Generate SQL without executing:

```bash
alembic upgrade e4f7a9b2c3d1 --sql > migration_preview.sql
```

Review `migration_preview.sql` to understand what will be executed.

### Step 3: Run the Migration

**Development/Staging Environment**:

```bash
# Upgrade to the multi-user migration
alembic upgrade e4f7a9b2c3d1

# Or upgrade to latest (head)
alembic upgrade head
```

**Production Environment**:

```bash
# Use transaction wrapping (safer)
alembic upgrade e4f7a9b2c3d1

# Monitor logs closely
tail -f alembic.log
```

### Step 4: Verify Migration Success

```bash
# Check current version
alembic current

# Should show: e4f7a9b2c3d1 (head)

# Verify tables were created
psql -U postgres -d grantfinder -c "\dt"

# Check new tables exist
psql -U postgres -d grantfinder -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('users', 'business_profiles', 'subscriptions', 'generated_applications');"

# Verify enum types
psql -U postgres -d grantfinder -c "\dT+"
```

### Step 5: Test the Migration

Run application tests to ensure everything works:

```bash
# Run database tests
pytest tests/test_database.py -v

# Run integration tests
pytest tests/test_integration.py -v

# Test user creation
python -c "from app.crud import create_user; from database.db import get_db; print('Database connection OK')"
```

## Rollback Instructions

If you need to revert the migration:

### Step 1: Backup Current State

```bash
pg_dump -U postgres -h localhost -d grantfinder > backup_before_rollback_$(date +%Y%m%d_%H%M%S).sql
```

### Step 2: Downgrade

```bash
# Downgrade one version back
alembic downgrade -1

# Or downgrade to specific version
alembic downgrade d896bf2738fb
```

**WARNING**: Downgrading will **DELETE ALL DATA** from:
- users table
- business_profiles table
- subscriptions table
- generated_applications table
- user_id columns in grants, search_runs, application_history

### Step 3: Verify Rollback

```bash
# Check current version
alembic current

# Should show: d896bf2738fb

# Verify tables were removed
psql -U postgres -d grantfinder -c "\dt"
```

## Data Migration Notes

### Legacy Data Handling

The migration is designed to handle existing data gracefully:

1. **Grants**: Existing grants will have `user_id = NULL`
   - These are considered "legacy" or "system" grants
   - Application code should handle NULL user_id appropriately
   - Can be assigned to users later through admin interface

2. **Search Runs**: Existing search runs will have `user_id = NULL`
   - These are historical searches before multi-user support
   - Statistics and reporting should account for NULL user_id

3. **Application History**:
   - Old string user_id preserved in `user_id_old` column
   - New integer `user_id` FK is NULL initially
   - Need to run data migration script to map old IDs to new user records

### Recommended Data Migration Script

After running the migration, run this script to migrate old user IDs:

```python
# data_migration_script.py
import asyncio
from sqlalchemy import select, update
from database.db import get_db
from database.models import ApplicationHistory, User

async def migrate_application_history_users():
    """
    Migrate old string user IDs to new integer user FKs.

    This assumes you have a mapping of old IDs to Auth0 IDs or emails.
    """
    async with get_db() as db:
        # Get all application_history records with old user_id
        result = await db.execute(
            select(ApplicationHistory).where(
                ApplicationHistory.user_id.is_(None),
                ApplicationHistory.user_id_old.isnot(None)
            )
        )
        records = result.scalars().all()

        print(f"Found {len(records)} records to migrate")

        # For each record, try to find matching user
        for record in records:
            old_id = record.user_id_old

            # Strategy 1: Assume old_id is email
            user = await db.execute(
                select(User).where(User.email == old_id)
            )
            user = user.scalar_one_or_none()

            if user:
                record.user_id = user.id
                print(f"Mapped {old_id} -> User ID {user.id}")
            else:
                print(f"WARNING: No user found for old ID: {old_id}")

        await db.commit()
        print("Migration complete")

# Run the migration
if __name__ == "__main__":
    asyncio.run(migrate_application_history_users())
```

## Troubleshooting

### Issue: "relation already exists"

**Solution**: Check if migration was partially applied:
```bash
alembic current
psql -U postgres -d grantfinder -c "\dt"

# If tables exist, mark migration as completed
alembic stamp e4f7a9b2c3d1
```

### Issue: "type already exists"

**Solution**: Enum types might already be created:
```bash
# Check existing types
psql -U postgres -d grantfinder -c "\dT"

# If types exist, comment out enum creation in migration file
# Or drop and recreate
psql -U postgres -d grantfinder -c "DROP TYPE IF EXISTS subscriptionstatus CASCADE;"
```

### Issue: "column already exists"

**Solution**: Some columns might already exist:
```bash
# Check table schema
psql -U postgres -d grantfinder -c "\d grants"

# If column exists, comment out that add_column line in migration
```

### Issue: "foreign key violation"

**Solution**: Ensure parent records exist before creating relationships:
```bash
# Check for orphaned records
psql -U postgres -d grantfinder -c "SELECT COUNT(*) FROM grants WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users);"
```

### Issue: "asyncpg.exceptions.UndefinedTableError"

**Solution**: Ensure previous migrations are applied:
```bash
# Check migration history
alembic history

# Apply all previous migrations
alembic upgrade head
```

## Performance Considerations

### Index Usage

The migration creates indexes on frequently queried columns:
- Foreign key columns (user_id)
- Unique identifiers (auth0_id, email, stripe IDs)
- Lookup columns (grant_id in generated_applications)

### Query Optimization

After migration, update queries to use indexes:

```python
# Good: Uses user_id index
grants = await db.execute(
    select(Grant).where(Grant.user_id == user_id)
)

# Good: Uses email index
user = await db.execute(
    select(User).where(User.email == email)
)

# Good: Uses composite index
apps = await db.execute(
    select(GeneratedApplication)
    .where(GeneratedApplication.user_id == user_id)
    .where(GeneratedApplication.grant_id == grant_id)
)
```

### Monitoring

Monitor query performance after migration:

```sql
-- Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;
```

## Security Considerations

### Database Access

1. **User Isolation**: Each user can only access their own data
   - Enforce through application logic
   - Use user_id filters in all queries
   - Validate user ownership before updates/deletes

2. **Sensitive Data**:
   - Auth0 IDs are indexed but not exposed in API
   - Stripe IDs are unique indexed for webhook validation
   - Email addresses are unique and should be validated

3. **Cascade Deletes**:
   - User deletion cascades to all related data
   - Implement soft deletes if needed
   - Consider data retention policies

### Best Practices

```python
# Always filter by user_id from authenticated session
async def get_user_grants(user_id: int, db: AsyncSession):
    result = await db.execute(
        select(Grant).where(Grant.user_id == user_id)
    )
    return result.scalars().all()

# Never expose internal IDs in URLs
# Use UUIDs or slugs instead
from uuid import uuid4

class Grant:
    id = Column(Integer, primary_key=True)
    uuid = Column(String, unique=True, default=lambda: str(uuid4()))
```

## Testing Checklist

After migration, verify:

- [ ] All tables created successfully
- [ ] All indexes created successfully
- [ ] All foreign keys working correctly
- [ ] Enum types created and usable
- [ ] User registration flow works
- [ ] Business profile creation works
- [ ] Subscription creation works (Stripe integration)
- [ ] Grant creation with user_id works
- [ ] Application generation works
- [ ] Search runs logged with user_id
- [ ] Legacy data (NULL user_id) still accessible
- [ ] Cascade deletes work correctly
- [ ] Performance is acceptable
- [ ] No orphaned records
- [ ] Application tests pass
- [ ] Integration tests pass

## Support

If you encounter issues:

1. Check Alembic logs: `tail -f alembic.log`
2. Check PostgreSQL logs: `tail -f /var/log/postgresql/postgresql-14-main.log`
3. Review migration file: `migrations/versions/e4f7a9b2c3d1_*.py`
4. Check database state: `psql -U postgres -d grantfinder`
5. Restore from backup if needed

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- Project README: `README.md`
- Database Models: `database/models.py`
- Settings Configuration: `config/settings.py`
