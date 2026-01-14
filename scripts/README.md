# Scripts Directory

This directory contains utility scripts for the Grant Finder application.

## Available Scripts

### 1. migrate_legacy_data.py

**Purpose**: Migrate existing data to the new multi-user schema after running the database migration.

**Usage**:
```bash
# Preview changes (dry-run mode)
python scripts/migrate_legacy_data.py --dry-run

# Execute migration
python scripts/migrate_legacy_data.py
```

**What it does**:
1. Creates a system user for legacy data (email: `system@grantfinder.internal`)
2. Assigns all grants without user_id to the system user
3. Assigns all search_runs without user_id to the system user
4. Migrates application_history old string user IDs to new integer foreign keys

**Requirements**:
- Database migration `e4f7a9b2c3d1` must be applied first
- Environment variables must be set (DATABASE_URL or DB_* variables)
- Python packages: sqlalchemy, asyncpg, python-dotenv

**Output**:
```
======================================================================
Legacy Data Migration Script
======================================================================

⚠️  LIVE MODE - Changes will be committed to database
Press Ctrl+C within 5 seconds to cancel...

Connecting to database: grantfinder@localhost

=== Step 1: Creating System User ===
✓ Created system user (ID: 1)

=== Step 2: Migrating Legacy Grants ===
Found 150 legacy grants without user_id
✓ Assigned 150 legacy grants to system user

=== Step 3: Migrating Legacy Search Runs ===
Found 45 legacy search runs without user_id
✓ Assigned 45 legacy search runs to system user

=== Step 4: Migrating Application History User IDs ===
Found 23 application history records to migrate
  ✓ Matched 'user@example.com' -> User 'user@example.com' (ID: 2)
  ⚠ No match for 'old_user', assigning to system user
...

✓ All changes committed successfully

======================================================================
Migration completed successfully!
======================================================================
```

**Error Handling**:
- Creates system user if it doesn't exist
- Handles missing user matches gracefully (assigns to system user)
- Rolls back on errors
- Provides detailed logging

**Safety Features**:
- Dry-run mode to preview changes
- 5-second cancellation window in live mode
- Automatic rollback on errors
- Detailed logging of all operations

---

### 2. setup.ps1

**Purpose**: PowerShell script for initial project setup on Windows.

**Usage**:
```powershell
.\scripts\setup.ps1
```

---

### 3. organize_project.py

**Purpose**: Organize and restructure project files.

**Usage**:
```bash
python scripts/organize_project.py
```

---

### 4. verify_setup.py

**Purpose**: Verify project setup and dependencies.

**Usage**:
```bash
python scripts/verify_setup.py
```

## Migration Script Details

### System User

The migration script creates a special system user with these properties:

- **Email**: `system@grantfinder.internal`
- **Auth0 ID**: `system_internal`
- **Subscription Tier**: `admin`
- **Subscription Status**: `ACTIVE`
- **Is Admin**: `True`
- **Search Limit**: 999,999
- **Application Limit**: 999,999

This user serves as the owner for all legacy data that existed before multi-user support was added.

### Matching Strategies

The script attempts to match old application_history user IDs using these strategies:

1. **Exact Email Match**: If the old user_id is an email address that exists in the users table
2. **Partial Match**: If the old user_id is a username (no @), tries to match with `username@domain`
3. **Fallback**: If no match found, assigns to system user

### Idempotency

The script is safe to run multiple times:
- Checks if system user already exists before creating
- Only migrates records that need migration (user_id IS NULL)
- Uses database transactions for atomicity

### Logging

The script provides detailed logging:
- ✓ Success messages (green checkmarks)
- ⚠ Warning messages (yellow warning symbols)
- ✗ Error messages (red X symbols)
- Summary statistics at the end

### Example Scenarios

#### Scenario 1: New Installation (No Legacy Data)

```bash
$ python scripts/migrate_legacy_data.py

=== Step 1: Creating System User ===
✓ System user already exists (ID: 1)

=== Step 2: Migrating Legacy Grants ===
✓ No legacy grants found (all grants have user_id)

=== Step 3: Migrating Legacy Search Runs ===
✓ No legacy search runs found (all runs have user_id)

=== Step 4: Migrating Application History User IDs ===
✓ No application history records need migration

✓ All changes committed successfully
```

#### Scenario 2: Existing Data Migration

```bash
$ python scripts/migrate_legacy_data.py --dry-run

[DRY RUN] Would create system user: system@grantfinder.internal
[DRY RUN] Would assign 150 grants to system user (ID: -1)
[DRY RUN] Would assign 45 search runs to system user (ID: -1)
[DRY RUN] Would update 23 application history records

[DRY RUN] No changes were committed
```

## Best Practices

1. **Always run dry-run first**: Use `--dry-run` to preview changes
2. **Backup before running**: Create a database backup before executing
3. **Review output carefully**: Check for warnings and unexpected matches
4. **Run in stages**: Test on development, then staging, then production
5. **Monitor after migration**: Check for issues with legacy data access

## Troubleshooting

### Issue: System user already exists with different properties

**Solution**: Update the existing system user instead of creating a new one. The script checks for existing users by email.

### Issue: Many unmatched old user IDs

**Solution**: Create a mapping file or update the script with custom matching logic for your specific old user ID format.

### Issue: Transaction timeout

**Solution**: If migrating large amounts of data, consider batching the updates or increasing the database timeout.

### Issue: Foreign key violations

**Solution**: Ensure the users table has the correct user IDs before running application_history migration.

## Related Documentation

- **Database Models**: `database/models.py`
- **Migration Guide**: `MIGRATION_GUIDE.md`
- **Quick Reference**: `MIGRATION_QUICK_REFERENCE.md`
- **Migration Summary**: `MIGRATION_SUMMARY.md`
- **Execution Checklist**: `MIGRATION_CHECKLIST.md`

## Support

For questions or issues with the migration scripts:

1. Check the migration documentation
2. Review the script source code for detailed comments
3. Test in development environment first
4. Create a database backup before running in production
5. Contact the development team if issues persist

## Future Enhancements

Potential improvements for the migration script:

- [ ] Add progress bars for large data migrations
- [ ] Support custom mapping files for user ID translation
- [ ] Add email notifications when migration completes
- [ ] Support incremental migration (migrate in batches)
- [ ] Add rollback functionality
- [ ] Generate migration report (CSV or JSON)
- [ ] Add validation checks before and after migration
