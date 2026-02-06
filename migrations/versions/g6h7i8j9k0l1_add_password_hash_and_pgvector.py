"""Add password_hash column and pgvector extension

Revision ID: g6h7i8j9k0l1
Revises: f5g8h9i0j1k2
Create Date: 2026-02-05 00:00:00.000000

This migration:
- Adds password_hash column to users table for email/password JWT auth
- Makes auth0_id nullable (no longer required, kept for migration compat)
- Enables pgvector extension for future vector similarity search
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'g6h7i8j9k0l1'
down_revision: Union[str, None] = 'f5g8h9i0j1k2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension (safe to call if already exists)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add password_hash column for email/password authentication
    op.add_column(
        'users',
        sa.Column('password_hash', sa.String(), nullable=True)
    )

    # Make auth0_id nullable (was NOT NULL in original migration)
    op.alter_column(
        'users',
        'auth0_id',
        existing_type=sa.String(),
        nullable=True
    )


def downgrade() -> None:
    # Revert auth0_id to NOT NULL (will fail if any NULL values exist)
    op.alter_column(
        'users',
        'auth0_id',
        existing_type=sa.String(),
        nullable=False
    )

    # Remove password_hash column
    op.drop_column('users', 'password_hash')

    # Note: We don't drop the pgvector extension on downgrade
    # as other tables may depend on it
