# Database Migration Quick Reference

## Multi-User Support Migration (e4f7a9b2c3d1)

### Quick Start (Development)

```bash
# 1. Backup database
pg_dump -U postgres -d grantfinder > backup.sql

# 2. Run migration
alembic upgrade head

# 3. Verify success
alembic current

# 4. Migrate legacy data (optional)
python scripts/migrate_legacy_data.py --dry-run  # Preview
python scripts/migrate_legacy_data.py            # Execute
```

### Quick Start (Production)

```bash
# 1. Backup database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Preview migration
alembic upgrade e4f7a9b2c3d1 --sql > migration.sql
cat migration.sql  # Review carefully

# 3. Run migration
alembic upgrade e4f7a9b2c3d1

# 4. Verify
alembic current
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"

# 5. Migrate legacy data
python scripts/migrate_legacy_data.py --dry-run
python scripts/migrate_legacy_data.py
```

### Rollback (Emergency)

```bash
# 1. Backup current state
pg_dump $DATABASE_URL > backup_before_rollback.sql

# 2. Downgrade
alembic downgrade d896bf2738fb

# 3. Verify
alembic current
```

### Common Commands

```bash
# Check current version
alembic current

# Show migration history
alembic history --verbose

# Show pending migrations
alembic heads

# Upgrade to latest
alembic upgrade head

# Upgrade to specific version
alembic upgrade e4f7a9b2c3d1

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade d896bf2738fb

# Generate SQL without executing
alembic upgrade head --sql

# Mark migration as applied (without running)
alembic stamp e4f7a9b2c3d1
```

### Verification Queries

```sql
-- Check tables exist
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('users', 'business_profiles', 'subscriptions', 'generated_applications');

-- Check enums exist
SELECT typname FROM pg_type
WHERE typname IN ('subscriptionstatus', 'applicationgenerationstatus', 'searchruntype', 'searchrunstatus');

-- Check indexes exist
SELECT indexname FROM pg_indexes
WHERE schemaname = 'public'
AND tablename IN ('users', 'business_profiles', 'subscriptions', 'generated_applications');

-- Count legacy data (NULL user_id)
SELECT
    (SELECT COUNT(*) FROM grants WHERE user_id IS NULL) as grants_without_user,
    (SELECT COUNT(*) FROM search_runs WHERE user_id IS NULL) as searches_without_user,
    (SELECT COUNT(*) FROM application_history WHERE user_id IS NULL) as apps_without_user;

-- Check user data
SELECT id, email, subscription_tier, searches_used, applications_used FROM users;
```

### Troubleshooting

#### "relation already exists"
```bash
# Check if partially applied
alembic current
psql -c "\dt"
# If tables exist, mark as complete
alembic stamp e4f7a9b2c3d1
```

#### "type already exists"
```sql
-- Check existing types
\dT

-- Drop and let migration recreate
DROP TYPE IF EXISTS subscriptionstatus CASCADE;
```

#### "column already exists"
```bash
# Check table schema
psql -c "\d grants"
# Edit migration to skip that column
```

#### "foreign key violation"
```sql
-- Find orphaned records
SELECT COUNT(*) FROM grants
WHERE user_id IS NOT NULL
AND user_id NOT IN (SELECT id FROM users);
```

### Migration File Location

**Path**: `c:\Users\chizi\OneDrive\Documents\GitHub\kevin-smart-grant-finder\migrations\versions\e4f7a9b2c3d1_add_multi_user_support_with_auth0_and_stripe.py`

**Revision**: `e4f7a9b2c3d1`

**Revises**: `d896bf2738fb`

### What Gets Created

**New Tables:**
- `users` - User accounts (Auth0)
- `business_profiles` - Business info (RAG)
- `subscriptions` - Stripe subscriptions
- `generated_applications` - AI applications

**New Columns:**
- `grants.user_id` (FK to users, nullable)
- `search_runs.user_id` (FK to users, nullable)
- `application_history.user_id` (FK to users, nullable)
- `application_history.user_id_old` (String, legacy)

**New Enums:**
- `SubscriptionStatus`
- `ApplicationGenerationStatus`
- `SearchRunType`
- `SearchRunStatus`

**New Indexes:**
- `ix_users_auth0_id` (unique)
- `ix_users_email` (unique)
- `ix_business_profiles_user_id` (unique)
- `ix_subscriptions_user_id` (unique)
- `ix_subscriptions_stripe_customer_id` (unique)
- `ix_subscriptions_stripe_subscription_id` (unique)
- `ix_generated_applications_user_id`
- `ix_generated_applications_grant_id`
- `ix_grants_user_id`
- `ix_search_runs_user_id`
- `ix_application_history_user_id`

### Important Notes

1. **Backward Compatible**: Existing data remains accessible
   - Legacy grants have `user_id = NULL`
   - Legacy searches have `user_id = NULL`
   - Application code must handle NULL user_id

2. **Data Migration Required**: Run `scripts/migrate_legacy_data.py` to:
   - Create system user for legacy data
   - Assign legacy grants to system user
   - Map old application_history user IDs

3. **Cascade Deletes**: User deletion removes:
   - Business profile
   - Subscription
   - Generated applications
   - Associated grants (if user_id set)
   - Search runs (if user_id set)
   - Application history (if user_id set)

4. **Performance**: All foreign keys are indexed
   - Queries on user_id are fast
   - Join operations are optimized
   - Monitor slow queries after migration

### Support

For detailed documentation, see:
- `MIGRATION_GUIDE.md` - Comprehensive guide
- `database/models.py` - Model definitions
- `config/settings.py` - Configuration

For issues:
1. Check `alembic.log`
2. Check PostgreSQL logs
3. Review migration file
4. Restore from backup if needed
