"""
Embedding service using fastembed (ONNX-based, no PyTorch).
Generates 384-dim vectors via BAAI/bge-small-en-v1.5 and stores them in pgvector.
"""

import logging
from typing import List, Dict, Any, Optional

import numpy as np
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import GrantEmbedding, ProfileEmbedding, BusinessProfile

logger = logging.getLogger(__name__)

# Lazy-loaded fastembed model (downloads ~50MB on first use)
_embedding_model = None
_model_load_failed = False

EMBEDDING_DIM = 384
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def _get_model():
    """Lazy-load the fastembed model."""
    global _embedding_model, _model_load_failed
    if _model_load_failed:
        return None
    if _embedding_model is None:
        try:
            from fastembed import TextEmbedding
            _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            logger.info("Loaded fastembed model BAAI/bge-small-en-v1.5 (384-dim)")
        except Exception as e:
            _model_load_failed = True
            logger.error(f"Failed to load fastembed model: {e}. Falling back to neutral scores.")
            return None
    return _embedding_model


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks at sentence boundaries."""
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
            for sep in ['. ', '! ', '? ']:
                brk = text.rfind(sep, start, end)
                if brk > start:
                    end = brk + 1
                    break
        chunks.append(text[start:end].strip())
        start = end - overlap
    return [c for c in chunks if c]


class EmbeddingService:
    """Central embedding service wrapping fastembed + pgvector storage."""

    def generate_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Generate 384-dim embeddings for a list of texts.
        Returns None if fastembed is unavailable.
        """
        if not texts:
            return []
        model = _get_model()
        if model is None:
            return None
        try:
            embeddings = list(model.embed(texts))
            return [e.tolist() if isinstance(e, np.ndarray) else list(e) for e in embeddings]
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    async def embed_grant(
        self, db: AsyncSession, grant_id: int, title: str, description: str
    ) -> bool:
        """Generate and store embeddings for a grant."""
        text = f"{title}\n\n{description}" if description else title
        chunks = _chunk_text(text)
        if not chunks:
            return False

        vectors = self.generate_embeddings(chunks)
        if vectors is None:
            logger.warning(f"Skipping grant {grant_id} embedding (model unavailable)")
            return False

        # Delete old embeddings for this grant
        await db.execute(
            delete(GrantEmbedding).where(GrantEmbedding.grant_id == grant_id)
        )

        for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
            db.add(GrantEmbedding(
                grant_id=grant_id,
                embedding=vec,
                text_content=chunk,
                chunk_index=idx,
            ))
        await db.flush()
        logger.info(f"Stored {len(vectors)} embeddings for grant {grant_id}")
        return True

    async def embed_business_profile(
        self, db: AsyncSession, user_id: int, business_profile_id: int
    ) -> Dict[str, Any]:
        """Generate and store embeddings for a business profile."""
        result = await db.execute(
            select(BusinessProfile).where(BusinessProfile.id == business_profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return {"success": False, "error": "Profile not found"}

        profile_text = self._build_profile_text(profile)
        chunks = _chunk_text(profile_text)
        if not chunks:
            return {"success": False, "error": "No text content to embed"}

        vectors = self.generate_embeddings(chunks)
        if vectors is None:
            logger.warning(f"Skipping profile embedding for user {user_id} (model unavailable)")
            return {"success": False, "error": "Embedding model unavailable"}

        # Delete old profile embeddings
        await db.execute(
            delete(ProfileEmbedding).where(
                ProfileEmbedding.user_id == user_id,
                ProfileEmbedding.business_profile_id == business_profile_id,
            )
        )

        for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
            db.add(ProfileEmbedding(
                user_id=user_id,
                business_profile_id=business_profile_id,
                embedding=vec,
                text_content=chunk,
                chunk_index=idx,
            ))

        profile.vector_embeddings_id = f"pg_user_{user_id}"
        from datetime import datetime
        profile.embeddings_generated_at = datetime.utcnow()

        await db.flush()
        logger.info(f"Stored {len(vectors)} profile embeddings for user {user_id}")
        return {
            "success": True,
            "chunks_created": len(chunks),
            "embeddings_stored": len(vectors),
        }

    async def find_similar_grants(
        self,
        db: AsyncSession,
        query_embedding: List[float],
        user_id: Optional[int] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find grants most similar to query_embedding using pgvector cosine distance."""
        vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        sql = text(f"""
            SELECT ge.grant_id, ge.text_content, ge.chunk_index,
                   1 - (ge.embedding <=> :qvec::vector) AS similarity
            FROM grant_embeddings ge
            JOIN grants g ON g.id = ge.grant_id
            WHERE g.record_status = 'ACTIVE'
            {"AND g.user_id = :uid" if user_id else ""}
            ORDER BY ge.embedding <=> :qvec::vector
            LIMIT :topk
        """)

        params = {"qvec": vec_str, "topk": top_k}
        if user_id:
            params["uid"] = user_id

        rows = await db.execute(sql, params)
        results = []
        for row in rows:
            results.append({
                "grant_id": row.grant_id,
                "text_content": row.text_content,
                "chunk_index": row.chunk_index,
                "similarity": float(row.similarity),
            })
        return results

    async def score_grant_relevance(
        self, db: AsyncSession, grant_id: int, user_id: int
    ) -> float:
        """Compute similarity between a grant and a user's business profile.
        Returns 0.0-1.0 score. Falls back to 0.5 if embeddings unavailable.
        """
        # Get grant embedding (average of chunks)
        grant_rows = await db.execute(
            select(GrantEmbedding.embedding).where(GrantEmbedding.grant_id == grant_id)
        )
        grant_vecs = [row[0] for row in grant_rows]

        # Get profile embeddings
        profile_rows = await db.execute(
            select(ProfileEmbedding.embedding).where(ProfileEmbedding.user_id == user_id)
        )
        profile_vecs = [row[0] for row in profile_rows]

        if not grant_vecs or not profile_vecs:
            return 0.5  # Neutral fallback

        # Average vectors
        grant_avg = np.mean([np.array(v) for v in grant_vecs], axis=0)
        profile_avg = np.mean([np.array(v) for v in profile_vecs], axis=0)

        # Cosine similarity
        dot = np.dot(grant_avg, profile_avg)
        norm = np.linalg.norm(grant_avg) * np.linalg.norm(profile_avg)
        if norm == 0:
            return 0.5

        similarity = float(dot / norm)
        # Clamp to 0-1 range
        return max(0.0, min(1.0, (similarity + 1) / 2))

    async def retrieve_relevant_context(
        self, db: AsyncSession, user_id: int, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """RAG retrieval: find profile chunks most relevant to a query."""
        query_vecs = self.generate_embeddings([query])
        if query_vecs is None or not query_vecs:
            # Fallback: return profile chunks ordered by index
            rows = await db.execute(
                select(ProfileEmbedding)
                .where(ProfileEmbedding.user_id == user_id)
                .order_by(ProfileEmbedding.chunk_index)
                .limit(top_k)
            )
            return [
                {"text": r.text_content, "score": 0.5, "chunk_index": r.chunk_index}
                for r in rows.scalars()
            ]

        qvec = query_vecs[0]
        vec_str = "[" + ",".join(str(v) for v in qvec) + "]"

        sql = text("""
            SELECT pe.text_content, pe.chunk_index,
                   1 - (pe.embedding <=> :qvec::vector) AS similarity
            FROM profile_embeddings pe
            WHERE pe.user_id = :uid
            ORDER BY pe.embedding <=> :qvec::vector
            LIMIT :topk
        """)
        rows = await db.execute(sql, {"qvec": vec_str, "uid": user_id, "topk": top_k})
        return [
            {
                "text": row.text_content,
                "score": float(row.similarity),
                "chunk_index": row.chunk_index,
            }
            for row in rows
        ]

    def _build_profile_text(self, profile: BusinessProfile) -> str:
        """Build comprehensive text from all profile fields."""
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
        narrative = profile.narrative_text or ""
        if narrative:
            if len(narrative) > 2000:
                narrative = narrative[:2000]
            parts.append(f"Detailed Description: {narrative}")
        return "\n\n".join(parts)


# Singleton
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
