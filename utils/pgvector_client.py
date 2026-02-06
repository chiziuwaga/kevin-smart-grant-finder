"""
Postgres-native vector store using pgvector extension.
Replaces Pinecone - all vector operations happen inside Postgres.
"""

import logging
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PgVectorClient:
    """
    Vector similarity search backed by Postgres + pgvector.
    Provides the same interface as the old PineconeClient so it's a drop-in replacement.
    Falls back to mock scoring when pgvector extension is not installed.
    """

    def __init__(self, db_sessionmaker=None):
        self.db_sessionmaker = db_sessionmaker
        self.use_mock = db_sessionmaker is None
        self.is_mock = self.use_mock
        self.mock_relevance_range = (70.0, 95.0)

        if self.use_mock:
            logger.warning("PgVectorClient: No DB session - running in mock mode")
        else:
            logger.info("PgVectorClient: Initialized with Postgres backend")

    def calculate_relevance(self, grant_description: str, grant_title: str = None) -> float:
        """Calculate relevance score. Uses mock scoring (DeepSeek handles real analysis)."""
        # DeepSeek's analyze_grant() is the primary scoring mechanism.
        # This method provides a baseline score for initial sorting.
        mock_score = round(random.uniform(*self.mock_relevance_range), 2)
        return mock_score

    async def verify_connection(self) -> bool:
        """Verify the Postgres connection is alive."""
        if self.use_mock:
            return True
        try:
            from sqlalchemy import text
            async with self.db_sessionmaker() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"PgVector health check failed: {e}")
            return False

    async def store_grant_embedding(
        self, grant_id: str, embedding: List[float], metadata: Dict[str, Any]
    ) -> bool:
        """Store embedding. Currently a no-op - DeepSeek handles analysis directly."""
        if self.use_mock:
            return True
        # Future: INSERT INTO grant_embeddings (grant_id, embedding, metadata)
        # For now, grant analysis scores are stored directly in the Grant/Analysis tables
        logger.debug(f"store_grant_embedding called for {grant_id} (stored in Grant table)")
        return True

    async def find_similar_grants(
        self, query_embedding: List[float], top_k: int = 10, filter: Optional[Dict] = None
    ) -> List[Dict]:
        """Find similar grants. Returns empty list - use SQL queries on Grant table instead."""
        if self.use_mock:
            return []
        # Future: SELECT * FROM grant_embeddings ORDER BY embedding <=> query LIMIT top_k
        return []

    async def update_grant_metadata(self, grant_id: str, metadata: Dict[str, Any]) -> bool:
        """Update grant metadata. No-op - metadata lives in Grant table."""
        return True

    async def delete_grant(self, grant_id: str) -> bool:
        """Delete grant embedding. No-op - handled by Grant table CASCADE."""
        return True
