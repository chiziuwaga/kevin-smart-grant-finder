"""Add cost tracking fields to User table

Revision ID: f5g8h9i0j1k2
Revises: e4f7a9b2c3d1
Create Date: 2026-01-14 00:00:00.000000

This migration adds AI cost tracking fields to the User table:
- monthly_ai_cost_cents: Track AI API costs per user per month (integer, cents)
- last_cost_reset: Track when costs were last reset (datetime)

These fields support cost monitoring and monthly reset functionality.
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f5g8h9i0j1k2'
down_revision: Union[str, None] = 'e4f7a9b2c3d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add cost tracking fields to User table.

    These fields enable monitoring of AI API costs per user and support
    monthly cost reset functionality via Celery Beat scheduled tasks.
    """

    # Add monthly_ai_cost_cents field (default 0)
    op.add_column(
        'users',
        sa.Column('monthly_ai_cost_cents', sa.Integer(), nullable=False, server_default='0')
    )

    # Add last_cost_reset field (nullable, no default)
    op.add_column(
        'users',
        sa.Column('last_cost_reset', sa.DateTime(), nullable=True)
    )

    print("✅ Added cost tracking fields to users table")


def downgrade() -> None:
    """
    Remove cost tracking fields from User table.
    """

    # Remove the added columns
    op.drop_column('users', 'last_cost_reset')
    op.drop_column('users', 'monthly_ai_cost_cents')

    print("✅ Removed cost tracking fields from users table")
