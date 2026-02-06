"""
RAG (Retrieval-Augmented Generation) system for business profile embeddings.
Uses fastembed for real vector embeddings and pgvector for semantic retrieval.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config.settings import Settings
from database.models import BusinessProfile, User, ProfileEmbedding

logger = logging.getLogger(__name__)
settings = Settings()


class ApplicationRAGService:
    """
    RAG service for business profile context retrieval.
    Delegates to EmbeddingService for real vector operations.
    """

    def __init__(self):
        self.settings = settings
        logger.info("ApplicationRAGService initialized (pgvector-backed)")

    async def generate_and_store_embeddings(
        self,
        db: AsyncSession,
        user_id: int,
        business_profile_id: int
    ) -> Dict[str, Any]:
        """Generate real vector embeddings for a business profile and store in pgvector."""
        try:
            from services.embedding_service import get_embedding_service
            svc = get_embedding_service()
            result = await svc.embed_business_profile(db, user_id, business_profile_id)
            if result.get("success"):
                await db.commit()
            return result
        except Exception as e:
            logger.error(f"Failed to generate embeddings for user {user_id}: {str(e)}")
            await db.rollback()
            return {"success": False, "error": str(e)}

    async def retrieve_relevant_context(
        self,
        db: AsyncSession,
        user_id: int,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant business context for a grant application query
        using real semantic similarity via pgvector.
        """
        try:
            from services.embedding_service import get_embedding_service
            svc = get_embedding_service()
            chunks = await svc.retrieve_relevant_context(db, user_id, query, top_k)

            if not chunks:
                # Fallback: return raw profile text chunks
                return await self._fallback_context(db, user_id, top_k)

            # Add business_name to each chunk
            profile = await self._get_profile(db, user_id)
            biz_name = profile.business_name if profile else ""
            for chunk in chunks:
                chunk["business_name"] = biz_name

            logger.info(f"Retrieved {len(chunks)} semantic context chunks for user {user_id}")
            return chunks

        except Exception as e:
            logger.error(f"Failed to retrieve context for user {user_id}: {str(e)}")
            return await self._fallback_context(db, user_id, top_k)

    async def _get_profile(self, db: AsyncSession, user_id: int):
        result = await db.execute(
            select(BusinessProfile).join(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def _fallback_context(
        self, db: AsyncSession, user_id: int, top_k: int
    ) -> List[Dict[str, Any]]:
        """Fallback when embeddings are unavailable: return stored text chunks."""
        rows = await db.execute(
            select(ProfileEmbedding)
            .where(ProfileEmbedding.user_id == user_id)
            .order_by(ProfileEmbedding.chunk_index)
            .limit(top_k)
        )
        chunks = []
        for r in rows.scalars():
            chunks.append({
                "text": r.text_content,
                "score": 0.5,
                "chunk_index": r.chunk_index,
                "business_name": "",
            })

        if not chunks:
            # No embeddings at all - build from profile text directly
            profile = await self._get_profile(db, user_id)
            if profile:
                from services.embedding_service import _chunk_text, EmbeddingService
                svc = EmbeddingService()
                text = svc._build_profile_text(profile)
                raw_chunks = _chunk_text(text)
                for idx, c in enumerate(raw_chunks[:top_k]):
                    chunks.append({
                        "text": c,
                        "score": 0.5,
                        "chunk_index": idx,
                        "business_name": profile.business_name or "",
                    })

        return chunks

    async def update_embeddings(
        self,
        db: AsyncSession,
        user_id: int,
        business_profile_id: int
    ) -> Dict[str, Any]:
        """Update embeddings when business profile changes."""
        return await self.generate_and_store_embeddings(
            db=db, user_id=user_id, business_profile_id=business_profile_id
        )

    async def delete_user_embeddings(self, user_id: int) -> bool:
        """Delete all embeddings for a user. Handled by CASCADE on profile_embeddings."""
        logger.info(f"Embeddings cleanup for user {user_id} (handled by CASCADE)")
        return True

    async def get_embedding_stats(self, db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """Get statistics about user's embeddings."""
        from sqlalchemy import func
        count_result = await db.execute(
            select(func.count(ProfileEmbedding.id)).where(ProfileEmbedding.user_id == user_id)
        )
        count = count_result.scalar() or 0
        return {
            "namespace": f"pg_user_{user_id}",
            "vector_count": count,
            "has_embeddings": count > 0,
        }


# Singleton instance
_rag_service = None


def get_rag_service() -> ApplicationRAGService:
    """Get or create RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = ApplicationRAGService()
    return _rag_service
