"""Add grant_embeddings and profile_embeddings tables

Revision ID: h7i8j9k0l1m2
Revises: g6h7i8j9k0l1
Create Date: 2026-02-05 12:00:00.000000

This migration creates:
- grant_embeddings table with Vector(384) column + HNSW index
- profile_embeddings table with Vector(384) column + HNSW index
Both use pgvector extension (enabled in previous migration g6h7i8j9k0l1).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = 'h7i8j9k0l1m2'
down_revision: Union[str, None] = 'g6h7i8j9k0l1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create grant_embeddings table
    op.create_table(
        'grant_embeddings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('grant_id', sa.Integer(), sa.ForeignKey('grants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('embedding', Vector(384), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('chunk_index', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_grant_embeddings_grant_id', 'grant_embeddings', ['grant_id'])

    # Create profile_embeddings table
    op.create_table(
        'profile_embeddings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('business_profile_id', sa.Integer(), sa.ForeignKey('business_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('embedding', Vector(384), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('chunk_index', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_profile_embeddings_user_id', 'profile_embeddings', ['user_id'])
    op.create_index('ix_profile_embeddings_business_profile_id', 'profile_embeddings', ['business_profile_id'])

    # Create HNSW indexes for fast cosine similarity search
    # HNSW (Hierarchical Navigable Small World) gives ~99% recall with much faster queries
    op.execute("""
        CREATE INDEX ix_grant_embeddings_hnsw
        ON grant_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    op.execute("""
        CREATE INDEX ix_profile_embeddings_hnsw
        ON profile_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_profile_embeddings_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_grant_embeddings_hnsw")
    op.drop_table('profile_embeddings')
    op.drop_table('grant_embeddings')
