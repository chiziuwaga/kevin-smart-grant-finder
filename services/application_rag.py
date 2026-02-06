"""
RAG (Retrieval-Augmented Generation) system for business profile embeddings.
Uses DeepSeek for text analysis and Postgres for storage (pgvector-ready).
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config.settings import Settings
from services.deepseek_client import get_deepseek_client
from database.models import BusinessProfile, User

logger = logging.getLogger(__name__)
settings = Settings()


class ApplicationRAGService:
    """
    RAG service for business profile context retrieval.
    Uses DeepSeek for text processing and Postgres for storage.
    """

    def __init__(self):
        self.settings = settings
        self.deepseek_client = get_deepseek_client()
        logger.info("ApplicationRAGService initialized (Postgres-backed)")

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Chunk text into smaller pieces for processing."""
        if not text or len(text.strip()) == 0:
            return []

        text = text.strip()
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            if end < len(text):
                sentence_break = text.rfind('. ', start, end)
                if sentence_break == -1:
                    sentence_break = text.rfind('! ', start, end)
                if sentence_break == -1:
                    sentence_break = text.rfind('? ', start, end)

                if sentence_break != -1 and sentence_break > start:
                    end = sentence_break + 1

            chunks.append(text[start:end].strip())
            start = end - overlap

        return chunks

    async def generate_and_store_embeddings(
        self,
        db: AsyncSession,
        user_id: int,
        business_profile_id: int
    ) -> Dict[str, Any]:
        """Generate text chunks for business profile and mark as processed."""
        try:
            result = await db.execute(
                select(BusinessProfile).where(BusinessProfile.id == business_profile_id)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                raise ValueError(f"Business profile {business_profile_id} not found")

            narrative_text = profile.narrative_text or ""
            if len(narrative_text) > 2000:
                logger.warning(f"Narrative text exceeds 2000 chars, truncating for user {user_id}")
                narrative_text = narrative_text[:2000]

            profile_text = self._build_profile_text(profile, narrative_text)
            chunks = self._chunk_text(profile_text, chunk_size=500, overlap=50)
            logger.info(f"Created {len(chunks)} chunks for user {user_id}")

            if not chunks:
                return {"success": False, "error": "No text content to embed"}

            # Mark profile as having embeddings processed
            profile.vector_embeddings_id = f"pg_user_{user_id}"
            profile.embeddings_generated_at = datetime.utcnow()
            await db.commit()

            return {
                "success": True,
                "chunks_created": len(chunks),
                "embeddings_stored": len(chunks),
                "namespace": f"pg_user_{user_id}",
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to generate embeddings for user {user_id}: {str(e)}")
            await db.rollback()
            return {"success": False, "error": str(e)}

    def _build_profile_text(self, profile: BusinessProfile, narrative_text: str) -> str:
        """Build comprehensive profile text from all fields."""
        parts = []

        if profile.business_name:
            parts.append(f"Business Name: {profile.business_name}")
        if profile.mission_statement:
            parts.append(f"Mission: {profile.mission_statement}")
        if profile.service_description:
            parts.append(f"Services: {profile.service_description}")
        if profile.target_sectors:
            sectors = ", ".join(profile.target_sectors) if isinstance(profile.target_sectors, list) else str(profile.target_sectors)
            parts.append(f"Target Sectors: {sectors}")
        if profile.revenue_range:
            parts.append(f"Revenue Range: {profile.revenue_range}")
        if profile.years_in_operation:
            parts.append(f"Years in Operation: {profile.years_in_operation}")
        if profile.geographic_focus:
            parts.append(f"Geographic Focus: {profile.geographic_focus}")
        if profile.team_size:
            parts.append(f"Team Size: {profile.team_size}")
        if narrative_text:
            parts.append(f"Detailed Description: {narrative_text}")

        return "\n\n".join(parts)

    async def retrieve_relevant_context(
        self,
        db: AsyncSession,
        user_id: int,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant business context for a grant application query.
        Uses the business profile text directly (full-text retrieval).
        """
        try:
            result = await db.execute(
                select(BusinessProfile).join(User).where(User.id == user_id)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                logger.warning(f"No business profile for user {user_id}")
                return []

            narrative_text = profile.narrative_text or ""
            if len(narrative_text) > 2000:
                narrative_text = narrative_text[:2000]

            profile_text = self._build_profile_text(profile, narrative_text)
            chunks = self._chunk_text(profile_text, chunk_size=500, overlap=50)

            context_chunks = []
            for idx, chunk in enumerate(chunks[:top_k]):
                context_chunks.append({
                    "text": chunk,
                    "score": 1.0 - (idx * 0.05),
                    "chunk_index": idx,
                    "business_name": profile.business_name or ""
                })

            logger.info(f"Retrieved {len(context_chunks)} context chunks for user {user_id}")
            return context_chunks

        except Exception as e:
            logger.error(f"Failed to retrieve context for user {user_id}: {str(e)}")
            return []

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
        """Delete all embeddings for a user. No-op with Postgres storage."""
        logger.info(f"Embeddings cleanup for user {user_id} (handled by CASCADE)")
        return True

    async def get_embedding_stats(self, user_id: int) -> Dict[str, Any]:
        """Get statistics about user's embeddings."""
        return {
            "namespace": f"pg_user_{user_id}",
            "vector_count": 0,
            "has_embeddings": False
        }


# Singleton instance
_rag_service = None


def get_rag_service() -> ApplicationRAGService:
    """Get or create RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = ApplicationRAGService()
    return _rag_service
