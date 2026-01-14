"""Add multi-user support with Auth0 and Stripe

Revision ID: e4f7a9b2c3d1
Revises: d896bf2738fb
Create Date: 2026-01-13 23:30:00.000000

This migration adds comprehensive multi-user support with:
- User accounts with Auth0 authentication
- Business profiles for RAG-based application generation
- Stripe subscription management
- AI-generated applications tracking
- Foreign key relationships to existing tables
- Proper indexes for performance
- Enum types for status management

IMPORTANT: This migration is designed to be reversible and handles existing data gracefully.
Legacy data (grants, search_runs, etc.) will have NULL user_id initially.
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e4f7a9b2c3d1'
down_revision: Union[str, None] = 'd896bf2738fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema to support multi-user functionality.

    This migration:
    1. Creates new enum types for subscriptions and applications
    2. Creates users table with Auth0 integration
    3. Creates business_profiles table for RAG
    4. Creates subscriptions table for Stripe integration
    5. Creates generated_applications table for AI applications
    6. Adds user_id foreign keys to existing tables
    7. Creates necessary indexes for performance
    8. Updates application_history with proper foreign key
    """

    # ============================================================================
    # STEP 1: Create ENUM types
    # ============================================================================

    # Create SubscriptionStatus enum (if not exists)
    subscription_status_enum = postgresql.ENUM(
        'ACTIVE', 'CANCELED', 'PAST_DUE', 'TRIALING',
        'INCOMPLETE', 'INCOMPLETE_EXPIRED', 'UNPAID',
        name='subscriptionstatus',
        create_type=True
    )
    subscription_status_enum.create(op.get_bind(), checkfirst=True)

    # Create ApplicationGenerationStatus enum (if not exists)
    application_generation_status_enum = postgresql.ENUM(
        'DRAFT', 'GENERATED', 'EDITED', 'SUBMITTED',
        'AWARDED', 'REJECTED',
        name='applicationgenerationstatus',
        create_type=True
    )
    application_generation_status_enum.create(op.get_bind(), checkfirst=True)

    # Create SearchRunType enum (if not exists)
    search_run_type_enum = postgresql.ENUM(
        'AUTOMATED', 'MANUAL', 'SCHEDULED',
        name='searchruntype',
        create_type=True
    )
    search_run_type_enum.create(op.get_bind(), checkfirst=True)

    # Create SearchRunStatus enum (if not exists)
    search_run_status_enum = postgresql.ENUM(
        'SUCCESS', 'FAILED', 'PARTIAL', 'IN_PROGRESS',
        name='searchrunstatus',
        create_type=True
    )
    search_run_status_enum.create(op.get_bind(), checkfirst=True)

    # ============================================================================
    # STEP 2: Create users table
    # ============================================================================

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('auth0_id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('company_name', sa.String(), nullable=True),

        # Subscription tier and status
        sa.Column('subscription_tier', sa.String(), nullable=True, server_default='free'),
        sa.Column('subscription_status', subscription_status_enum, nullable=True, server_default='INCOMPLETE'),

        # Usage tracking
        sa.Column('searches_used', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('applications_used', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('searches_limit', sa.Integer(), nullable=True, server_default='50'),
        sa.Column('applications_limit', sa.Integer(), nullable=True, server_default='20'),

        # Usage period tracking
        sa.Column('usage_period_start', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('usage_period_end', sa.DateTime(), nullable=True),

        # Account status
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('is_admin', sa.Boolean(), nullable=True, server_default='false'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('last_login', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes on users table
    op.create_index(op.f('ix_users_auth0_id'), 'users', ['auth0_id'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # ============================================================================
    # STEP 3: Create business_profiles table
    # ============================================================================

    op.create_table(
        'business_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        # Basic business information
        sa.Column('business_name', sa.String(), nullable=False),
        sa.Column('mission_statement', sa.Text(), nullable=True),
        sa.Column('service_description', sa.Text(), nullable=True),
        sa.Column('website_url', sa.String(), nullable=True),

        # Business details
        sa.Column('target_sectors', sa.JSON(), nullable=True),
        sa.Column('revenue_range', sa.String(), nullable=True),
        sa.Column('years_in_operation', sa.Integer(), nullable=True),
        sa.Column('geographic_focus', sa.String(), nullable=True),
        sa.Column('team_size', sa.Integer(), nullable=True),

        # Long-form narrative for RAG
        sa.Column('narrative_text', sa.Text(), nullable=True),

        # Document uploads
        sa.Column('uploaded_documents', sa.JSON(), nullable=True),
        sa.Column('documents_total_size_bytes', sa.Integer(), nullable=True, server_default='0'),

        # Vector embeddings reference
        sa.Column('vector_embeddings_id', sa.String(), nullable=True),
        sa.Column('embeddings_generated_at', sa.DateTime(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),

        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create unique index on user_id (one profile per user)
    op.create_index(op.f('ix_business_profiles_user_id'), 'business_profiles', ['user_id'], unique=True)

    # ============================================================================
    # STEP 4: Create subscriptions table
    # ============================================================================

    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        # Stripe identifiers
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(), nullable=True),

        # Plan details
        sa.Column('plan_name', sa.String(), nullable=True, server_default='basic'),
        sa.Column('amount', sa.Integer(), nullable=True, server_default='3500'),
        sa.Column('currency', sa.String(), nullable=True, server_default='usd'),

        # Subscription status
        sa.Column('status', subscription_status_enum, nullable=True, server_default='INCOMPLETE'),

        # Billing period
        sa.Column('current_period_start', sa.DateTime(), nullable=True),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),

        # Usage limits
        sa.Column('searches_remaining', sa.Integer(), nullable=True, server_default='50'),
        sa.Column('applications_remaining', sa.Integer(), nullable=True, server_default='20'),

        # Subscription management
        sa.Column('auto_renew', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('canceled_at', sa.DateTime(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),

        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes on subscriptions table
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=True)
    op.create_index(op.f('ix_subscriptions_stripe_customer_id'), 'subscriptions', ['stripe_customer_id'], unique=True)
    op.create_index(op.f('ix_subscriptions_stripe_subscription_id'), 'subscriptions', ['stripe_subscription_id'], unique=True)

    # ============================================================================
    # STEP 5: Create generated_applications table
    # ============================================================================

    op.create_table(
        'generated_applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('grant_id', sa.Integer(), nullable=False),

        # Application content
        sa.Column('generated_content', sa.Text(), nullable=True),
        sa.Column('sections', sa.JSON(), nullable=True),

        # Application metadata
        sa.Column('generation_date', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('last_edited', sa.DateTime(), nullable=True),
        sa.Column('status', application_generation_status_enum, nullable=True, server_default='DRAFT'),

        # User feedback and notes
        sa.Column('feedback_notes', sa.Text(), nullable=True),
        sa.Column('user_edits', sa.JSON(), nullable=True),

        # Generation metadata
        sa.Column('model_used', sa.String(), nullable=True, server_default='deepseek'),
        sa.Column('generation_time_seconds', sa.Float(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),

        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['grant_id'], ['grants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes on generated_applications table
    op.create_index(op.f('ix_generated_applications_user_id'), 'generated_applications', ['user_id'], unique=False)
    op.create_index(op.f('ix_generated_applications_grant_id'), 'generated_applications', ['grant_id'], unique=False)

    # ============================================================================
    # STEP 6: Add user_id foreign keys to existing tables
    # ============================================================================

    # Add user_id to grants table (nullable for legacy data)
    op.add_column('grants', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_grants_user_id', 'grants', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_grants_user_id'), 'grants', ['user_id'], unique=False)

    # Add user_id to search_runs table (nullable for legacy data)
    op.add_column('search_runs', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_search_runs_user_id', 'search_runs', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_search_runs_user_id'), 'search_runs', ['user_id'], unique=False)

    # Update application_history: change user_id from String to Integer FK
    # First, we need to handle existing data

    # Drop existing user_id index if it exists
    try:
        op.drop_index('ix_application_history_user_id', table_name='application_history')
    except:
        pass  # Index might not exist

    # Rename old user_id column to user_id_old (temporary)
    op.alter_column('application_history', 'user_id',
                    new_column_name='user_id_old',
                    existing_type=sa.String(),
                    existing_nullable=False)

    # Add new user_id column as Integer FK (nullable for now)
    op.add_column('application_history', sa.Column('user_id', sa.Integer(), nullable=True))

    # Create foreign key constraint
    op.create_foreign_key('fk_application_history_user_id', 'application_history', 'users',
                          ['user_id'], ['id'], ondelete='CASCADE')

    # Create index on new user_id
    op.create_index(op.f('ix_application_history_user_id'), 'application_history', ['user_id'], unique=False)

    # Note: Migration script for data conversion would go here if needed
    # For now, keeping both columns - user_id_old (String) and user_id (Integer FK)
    # Application code should handle the migration of old string IDs to new user IDs

    # Update user_settings: ensure user_id is properly constrained
    # The table should already have user_id, just ensuring FK constraint
    try:
        op.create_foreign_key('fk_user_settings_user_id', 'user_settings', 'users',
                              ['user_id'], ['id'], ondelete='CASCADE')
    except:
        pass  # FK might already exist

    # ============================================================================
    # STEP 7: Add enhanced columns to search_runs (if not already present)
    # ============================================================================

    # Add run_type column if not exists
    try:
        op.add_column('search_runs', sa.Column('run_type', search_run_type_enum, nullable=True, server_default='MANUAL'))
    except:
        pass  # Column might already exist

    # Add status column if not exists
    try:
        op.add_column('search_runs', sa.Column('status', search_run_status_enum, nullable=True, server_default='SUCCESS'))
    except:
        pass  # Column might already exist

    # Add additional tracking columns if not exists
    columns_to_add = [
        ('duration_seconds', sa.Float(), None),
        ('error_message', sa.Text(), None),
        ('error_details', sa.JSON(), None),
        ('search_query', sa.String(), None),
        ('user_triggered', sa.Boolean(), 'false'),
        ('sources_searched', sa.Integer(), '0'),
        ('api_calls_made', sa.Integer(), '0'),
        ('processing_time_ms', sa.Integer(), None),
    ]

    for col_name, col_type, default in columns_to_add:
        try:
            if default:
                op.add_column('search_runs', sa.Column(col_name, col_type, nullable=True, server_default=default))
            else:
                op.add_column('search_runs', sa.Column(col_name, col_type, nullable=True))
        except:
            pass  # Column might already exist


def downgrade() -> None:
    """
    Downgrade schema to remove multi-user functionality.

    WARNING: This will remove all user data, subscriptions, and generated applications!
    """

    # ============================================================================
    # STEP 1: Remove user_id foreign keys from existing tables
    # ============================================================================

    # Remove from grants
    op.drop_index(op.f('ix_grants_user_id'), table_name='grants')
    op.drop_constraint('fk_grants_user_id', 'grants', type_='foreignkey')
    op.drop_column('grants', 'user_id')

    # Remove from search_runs
    op.drop_index(op.f('ix_search_runs_user_id'), table_name='search_runs')
    op.drop_constraint('fk_search_runs_user_id', 'search_runs', type_='foreignkey')
    op.drop_column('search_runs', 'user_id')

    # Revert application_history changes
    op.drop_index(op.f('ix_application_history_user_id'), table_name='application_history')
    op.drop_constraint('fk_application_history_user_id', 'application_history', type_='foreignkey')
    op.drop_column('application_history', 'user_id')

    # Restore old user_id column
    op.alter_column('application_history', 'user_id_old',
                    new_column_name='user_id',
                    existing_type=sa.String(),
                    existing_nullable=False)

    # Recreate old index
    op.create_index('ix_application_history_user_id', 'application_history', ['user_id'], unique=False)

    # Remove enhanced search_runs columns
    columns_to_remove = [
        'processing_time_ms', 'api_calls_made', 'sources_searched',
        'user_triggered', 'search_query', 'error_details',
        'error_message', 'duration_seconds', 'status', 'run_type'
    ]

    for col_name in columns_to_remove:
        try:
            op.drop_column('search_runs', col_name)
        except:
            pass  # Column might not exist

    # ============================================================================
    # STEP 2: Drop new tables (in reverse order of creation)
    # ============================================================================

    # Drop generated_applications table
    op.drop_index(op.f('ix_generated_applications_grant_id'), table_name='generated_applications')
    op.drop_index(op.f('ix_generated_applications_user_id'), table_name='generated_applications')
    op.drop_table('generated_applications')

    # Drop subscriptions table
    op.drop_index(op.f('ix_subscriptions_stripe_subscription_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_stripe_customer_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_table('subscriptions')

    # Drop business_profiles table
    op.drop_index(op.f('ix_business_profiles_user_id'), table_name='business_profiles')
    op.drop_table('business_profiles')

    # Drop users table
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_auth0_id'), table_name='users')
    op.drop_table('users')

    # ============================================================================
    # STEP 3: Drop ENUM types
    # ============================================================================

    # Drop enum types
    postgresql.ENUM(name='searchrunstatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='searchruntype').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='applicationgenerationstatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='subscriptionstatus').drop(op.get_bind(), checkfirst=True)
