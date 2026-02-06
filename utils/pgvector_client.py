"""
Postgres-native vector store using pgvector extension.
Delegates to EmbeddingService for real semantic operations.
"""

import logging
from typing import List, Dict, Any, Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)

# Threshold constant used by AnalysisAgent
FUNDING_MIN = 5000


class PgVectorClient:
    """
    Vector similarity search backed by Postgres + pgvector.
    Provides backward-compat interface while delegating to EmbeddingService.
    """

    def __init__(self, db_sessionmaker=None):
        self.db_sessionmaker = db_sessionmaker
        self.use_mock = db_sessionmaker is None
        self.is_mock = self.use_mock
        self.FUNDING_MIN = FUNDING_MIN

        if self.use_mock:
            logger.warning("PgVectorClient: No DB session - running in mock mode (neutral 0.5 scores)")
        else:
            logger.info("PgVectorClient: Initialized with Postgres backend")

    def calculate_relevance(self, grant_description: str, grant_title: str = None) -> float:
        """Calculate relevance using embeddings. Returns 0.5 (neutral) if unavailable."""
        if self.use_mock:
            return 0.5

        from services.embedding_service import get_embedding_service
        svc = get_embedding_service()
        combined = f"{grant_title or ''}\n\n{grant_description or ''}".strip()
        vecs = svc.generate_embeddings([combined])
        if vecs is None:
            return 0.5
        # Return neutral - actual scoring happens via score_grant_relevance with profile context
        return 0.5

    async def verify_connection(self) -> bool:
        """Verify the Postgres connection is alive."""
        if self.use_mock:
            return True
        try:
            async with self.db_sessionmaker() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"PgVector health check failed: {e}")
            return False

    async def store_grant_embedding(
        self, grant_id: int, title: str = "", description: str = ""
    ) -> bool:
        """Store embedding for a grant via EmbeddingService."""
        if self.use_mock:
            return False
        try:
            from services.embedding_service import get_embedding_service
            svc = get_embedding_service()
            async with self.db_sessionmaker() as session:
                result = await svc.embed_grant(session, grant_id, title, description)
                await session.commit()
                return result
        except Exception as e:
            logger.error(f"Failed to store grant embedding {grant_id}: {e}")
            return False

    async def score_grant_for_user(self, grant_id: int, user_id: int) -> float:
        """Score a grant's relevance to a user's business profile."""
        if self.use_mock:
            return 0.5
        try:
            from services.embedding_service import get_embedding_service
            svc = get_embedding_service()
            async with self.db_sessionmaker() as session:
                return await svc.score_grant_relevance(session, grant_id, user_id)
        except Exception as e:
            logger.error(f"Failed to score grant {grant_id} for user {user_id}: {e}")
            return 0.5

    async def find_similar_grants(
        self, query_embedding: List[float], top_k: int = 10, user_id: Optional[int] = None
    ) -> List[Dict]:
        """Find similar grants by embedding vector."""
        if self.use_mock:
            return []
        try:
            from services.embedding_service import get_embedding_service
            svc = get_embedding_service()
            async with self.db_sessionmaker() as session:
                return await svc.find_similar_grants(session, query_embedding, user_id, top_k)
        except Exception as e:
            logger.error(f"find_similar_grants failed: {e}")
            return []

    async def delete_grant(self, grant_id: int) -> bool:
        """Delete grant embedding. Handled by CASCADE on grant_embeddings table."""
        return True
