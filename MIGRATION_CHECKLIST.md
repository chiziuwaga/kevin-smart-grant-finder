# Database Migration Execution Checklist

## Pre-Migration Checklist

### 1. Preparation
- [ ] Review `MIGRATION_SUMMARY.md` for overview
- [ ] Review `MIGRATION_GUIDE.md` for detailed instructions
- [ ] Review `MIGRATION_QUICK_REFERENCE.md` for commands
- [ ] Review migration file: `migrations/versions/e4f7a9b2c3d1_add_multi_user_support_with_auth0_and_stripe.py`

### 2. Environment Setup
- [ ] Python dependencies installed:
  ```bash
  pip install alembic sqlalchemy asyncpg psycopg2-binary python-dotenv
  ```
- [ ] Environment variables set in `.env`:
  - [ ] `DATABASE_URL` or (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`)
  - [ ] `AUTH0_DOMAIN`
  - [ ] `AUTH0_API_AUDIENCE`
  - [ ] `STRIPE_SECRET_KEY`
  - [ ] `STRIPE_PUBLISHABLE_KEY`
  - [ ] `STRIPE_WEBHOOK_SECRET`

### 3. Database State
- [ ] Check current Alembic revision:
  ```bash
  alembic current
  ```
  Expected: `d896bf2738fb` (or earlier)

- [ ] Database is accessible:
  ```bash
  psql $DATABASE_URL -c "SELECT version();"
  ```

- [ ] Check database size before migration:
  ```sql
  SELECT pg_size_pretty(pg_database_size('grantfinder'));
  ```

### 4. Backup (CRITICAL!)
- [ ] Create full database backup:
  ```bash
  pg_dump -U postgres -d grantfinder > backup_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] Verify backup file exists and has content:
  ```bash
  ls -lh backup_*.sql
  ```

- [ ] Store backup in safe location (S3, external drive, etc.)

- [ ] Test backup restoration (on dev/staging):
  ```bash
  createdb grantfinder_test
  psql -d grantfinder_test < backup_*.sql
  ```

## Migration Execution Checklist

### Step 1: Preview Migration (Development)
- [ ] Generate SQL preview:
  ```bash
  alembic upgrade e4f7a9b2c3d1 --sql > migration_preview.sql
  ```

- [ ] Review `migration_preview.sql` carefully
- [ ] Check for potential issues (duplicates, conflicts, etc.)

### Step 2: Test Migration (Development/Staging)
- [ ] Run migration on development database:
  ```bash
  alembic upgrade e4f7a9b2c3d1
  ```

- [ ] Check for errors in output
- [ ] Verify current revision:
  ```bash
  alembic current
  ```
  Expected: `e4f7a9b2c3d1 (head)`

- [ ] Verify tables created:
  ```bash
  psql -d grantfinder -c "\dt"
  ```
  Should see: `users`, `business_profiles`, `subscriptions`, `generated_applications`

- [ ] Verify enum types created:
  ```bash
  psql -d grantfinder -c "\dT"
  ```
  Should see: `subscriptionstatus`, `applicationgenerationstatus`, `searchruntype`, `searchrunstatus`

- [ ] Verify indexes created:
  ```bash
  psql -d grantfinder -c "\di" | grep -E "(users|business_profiles|subscriptions|generated_applications|grants|search_runs)"
  ```

- [ ] Test rollback:
  ```bash
  alembic downgrade d896bf2738fb
  ```

- [ ] Re-run migration:
  ```bash
  alembic upgrade e4f7a9b2c3d1
  ```

### Step 3: Data Migration (Development/Staging)
- [ ] Run data migration script (dry-run):
  ```bash
  python scripts/migrate_legacy_data.py --dry-run
  ```

- [ ] Review dry-run output carefully
- [ ] Run data migration script:
  ```bash
  python scripts/migrate_legacy_data.py
  ```

- [ ] Verify system user created:
  ```sql
  SELECT id, email, subscription_tier FROM users WHERE email = 'system@grantfinder.internal';
  ```

- [ ] Verify legacy data migrated:
  ```sql
  -- Check grants with system user
  SELECT COUNT(*) FROM grants WHERE user_id = (SELECT id FROM users WHERE email = 'system@grantfinder.internal');

  -- Check search runs with system user
  SELECT COUNT(*) FROM search_runs WHERE user_id = (SELECT id FROM users WHERE email = 'system@grantfinder.internal');

  -- Check application history migrated
  SELECT COUNT(*) FROM application_history WHERE user_id IS NOT NULL;
  ```

### Step 4: Testing
- [ ] Run unit tests:
  ```bash
  pytest tests/test_database.py -v
  ```

- [ ] Run integration tests:
  ```bash
  pytest tests/test_integration.py -v
  ```

- [ ] Test user creation:
  ```python
  python -c "
  from database.models import User
  from database.db import get_db
  import asyncio

  async def test():
      async with get_db() as db:
          user = User(
              auth0_id='test_auth0_123',
              email='test@example.com',
              full_name='Test User'
          )
          db.add(user)
          await db.commit()
          print(f'✓ User created with ID: {user.id}')

  asyncio.run(test())
  "
  ```

- [ ] Test grant creation with user_id:
  ```python
  # Similar test for Grant with user_id
  ```

- [ ] Test cascade delete:
  ```python
  # Test that deleting user deletes related data
  ```

- [ ] Test application endpoints (if available):
  ```bash
  curl http://localhost:8000/api/users/me
  curl http://localhost:8000/api/grants?user_id=1
  ```

### Step 5: Production Migration
- [ ] Schedule maintenance window
- [ ] Notify users of downtime
- [ ] Create production backup:
  ```bash
  pg_dump $DATABASE_URL > backup_prod_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] Verify backup:
  ```bash
  ls -lh backup_prod_*.sql
  ```

- [ ] Run migration:
  ```bash
  alembic upgrade e4f7a9b2c3d1
  ```

- [ ] Monitor for errors
- [ ] Verify current revision:
  ```bash
  alembic current
  ```

- [ ] Run data migration:
  ```bash
  python scripts/migrate_legacy_data.py --dry-run
  python scripts/migrate_legacy_data.py
  ```

- [ ] Smoke test critical endpoints:
  ```bash
  curl https://api.grantfinder.com/health
  curl https://api.grantfinder.com/api/users/me
  ```

## Post-Migration Checklist

### 1. Verification
- [ ] All tables exist:
  ```sql
  SELECT tablename FROM pg_tables
  WHERE schemaname = 'public'
  AND tablename IN ('users', 'business_profiles', 'subscriptions', 'generated_applications');
  ```
  Expected: 4 rows

- [ ] All columns exist in updated tables:
  ```sql
  SELECT column_name FROM information_schema.columns
  WHERE table_name = 'grants' AND column_name = 'user_id';
  ```

- [ ] All indexes created:
  ```sql
  SELECT indexname FROM pg_indexes
  WHERE schemaname = 'public'
  AND tablename IN ('users', 'business_profiles', 'subscriptions', 'generated_applications');
  ```
  Expected: 13 rows

- [ ] All foreign keys exist:
  ```sql
  SELECT conname FROM pg_constraint
  WHERE contype = 'f'
  AND connamespace = 'public'::regnamespace;
  ```

- [ ] Enum types exist:
  ```sql
  SELECT typname FROM pg_type
  WHERE typname IN ('subscriptionstatus', 'applicationgenerationstatus', 'searchruntype', 'searchrunstatus');
  ```
  Expected: 4 rows

### 2. Data Integrity
- [ ] Count records in new tables:
  ```sql
  SELECT
    (SELECT COUNT(*) FROM users) as users_count,
    (SELECT COUNT(*) FROM business_profiles) as profiles_count,
    (SELECT COUNT(*) FROM subscriptions) as subscriptions_count,
    (SELECT COUNT(*) FROM generated_applications) as applications_count;
  ```

- [ ] Verify no NULL user_id in critical tables:
  ```sql
  SELECT
    (SELECT COUNT(*) FROM grants WHERE user_id IS NULL) as grants_without_user,
    (SELECT COUNT(*) FROM search_runs WHERE user_id IS NULL) as searches_without_user;
  ```

- [ ] Check for orphaned records:
  ```sql
  SELECT COUNT(*) FROM grants
  WHERE user_id IS NOT NULL
  AND user_id NOT IN (SELECT id FROM users);
  ```
  Expected: 0

- [ ] Verify application_history migration:
  ```sql
  SELECT
    COUNT(*) as total_records,
    COUNT(user_id) as with_new_user_id,
    COUNT(user_id_old) as with_old_user_id
  FROM application_history;
  ```

### 3. Performance
- [ ] Check index usage:
  ```sql
  SELECT schemaname, tablename, indexname, idx_scan
  FROM pg_stat_user_indexes
  WHERE schemaname = 'public'
  AND tablename IN ('users', 'grants', 'search_runs')
  ORDER BY idx_scan DESC;
  ```

- [ ] Check table sizes:
  ```sql
  SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables
  WHERE schemaname = 'public'
  AND tablename IN ('users', 'business_profiles', 'subscriptions', 'generated_applications', 'grants', 'search_runs')
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
  ```

- [ ] Test query performance:
  ```sql
  EXPLAIN ANALYZE SELECT * FROM grants WHERE user_id = 1;
  EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';
  ```

### 4. Application Testing
- [ ] User registration flow works
- [ ] User login flow works (Auth0)
- [ ] Business profile creation works
- [ ] Grant search filtered by user works
- [ ] Application generation works
- [ ] Subscription creation works (Stripe webhook)
- [ ] All API endpoints return correct data
- [ ] Frontend displays user-specific data
- [ ] Admin interface works (if applicable)

### 5. Monitoring
- [ ] Set up monitoring for new tables
- [ ] Set up alerts for foreign key violations
- [ ] Monitor query performance
- [ ] Monitor database size growth
- [ ] Monitor error rates
- [ ] Monitor slow queries

### 6. Documentation
- [ ] Update API documentation with new endpoints
- [ ] Update database schema documentation
- [ ] Update developer onboarding docs
- [ ] Create runbook for common operations
- [ ] Document rollback procedure

## Rollback Checklist (If Needed)

### Emergency Rollback
- [ ] Create backup of current state:
  ```bash
  pg_dump $DATABASE_URL > backup_before_rollback_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] Run rollback:
  ```bash
  alembic downgrade d896bf2738fb
  ```

- [ ] Verify rollback:
  ```bash
  alembic current
  ```
  Expected: `d896bf2738fb`

- [ ] Verify tables removed:
  ```bash
  psql -d grantfinder -c "\dt" | grep -E "(users|business_profiles|subscriptions|generated_applications)"
  ```
  Expected: No results

- [ ] Test application functionality
- [ ] Restore from original backup if needed:
  ```bash
  psql $DATABASE_URL < backup_prod_*.sql
  ```

### After Rollback
- [ ] Investigate migration failure
- [ ] Fix issues in migration file
- [ ] Test migration again in development
- [ ] Schedule new migration attempt

## Sign-Off

### Development Environment
- [ ] Migration tested and verified
- [ ] Data migration tested and verified
- [ ] All tests passing
- [ ] Rollback tested and verified

**Signed off by**: _________________ Date: _______

### Staging Environment
- [ ] Migration tested and verified
- [ ] Data migration tested and verified
- [ ] All tests passing
- [ ] Performance acceptable
- [ ] Security checks passed

**Signed off by**: _________________ Date: _______

### Production Environment
- [ ] Migration executed successfully
- [ ] Data migration executed successfully
- [ ] All verification checks passed
- [ ] Monitoring set up
- [ ] Documentation updated

**Signed off by**: _________________ Date: _______

## Support Contacts

- **Database Admin**: _________________
- **Backend Lead**: _________________
- **DevOps**: _________________
- **On-Call**: _________________

## Additional Notes

_Add any notes, issues encountered, or lessons learned here_

---

**Migration ID**: e4f7a9b2c3d1

**Migration Name**: Add multi-user support with Auth0 and Stripe

**Created**: 2026-01-13

**Status**: [ ] Ready for Dev [ ] Ready for Staging [ ] Ready for Production [ ] Completed
