"""
RAG (Retrieval-Augmented Generation) system for business profile embeddings.
Manages vector embeddings for business profiles to enhance grant application generation.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re

from pinecone import Pinecone, ServerlessSpec
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config.settings import Settings
from services.deepseek_client import get_deepseek_client
from database.models import BusinessProfile, User

logger = logging.getLogger(__name__)
settings = Settings()


class ApplicationRAGService:
    """
    RAG service for business profile embeddings and retrieval.
    Handles vector storage in Pinecone with user namespace isolation.
    """

    def __init__(self):
        """Initialize RAG service with Pinecone and DeepSeek clients."""
        self.settings = settings
        self.deepseek_client = get_deepseek_client()

        # Initialize Pinecone
        self.pinecone_client = None
        self.index = None

        if settings.pinecone_api_key:
            try:
                self.pinecone_client = Pinecone(api_key=settings.pinecone_api_key)
                self.index_name = settings.pinecone_index_name
                self._initialize_index()
                logger.info(f"Pinecone initialized with index: {self.index_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Pinecone: {str(e)}")
        else:
            logger.warning("Pinecone API key not configured - RAG system disabled")

    def _initialize_index(self):
        """Initialize or connect to Pinecone index."""
        try:
            # Check if index exists
            existing_indexes = self.pinecone_client.list_indexes()
            index_names = [idx.name for idx in existing_indexes]

            if self.index_name not in index_names:
                logger.info(f"Creating Pinecone index: {self.index_name}")
                # Create index with DeepSeek embedding dimensions (assumed 1536)
                self.pinecone_client.create_index(
                    name=self.index_name,
                    dimension=1536,  # DeepSeek embeddings dimension
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )

            # Connect to index
            self.index = self.pinecone_client.Index(self.index_name)
            logger.info(f"Connected to Pinecone index: {self.index_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Pinecone index: {str(e)}")
            raise

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Chunk text into smaller pieces for embedding.

        Args:
            text: Text to chunk
            chunk_size: Maximum characters per chunk
            overlap: Character overlap between chunks

        Returns:
            List of text chunks
        """
        if not text or len(text.strip()) == 0:
            return []

        # Clean text
        text = text.strip()

        # If text is shorter than chunk size, return as single chunk
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                sentence_break = text.rfind('. ', start, end)
                if sentence_break == -1:
                    sentence_break = text.rfind('! ', start, end)
                if sentence_break == -1:
                    sentence_break = text.rfind('? ', start, end)

                # If found, use it; otherwise use chunk_size
                if sentence_break != -1 and sentence_break > start:
                    end = sentence_break + 1

            chunks.append(text[start:end].strip())
            start = end - overlap

        return chunks

    def _get_user_namespace(self, user_id: int) -> str:
        """
        Get Pinecone namespace for user isolation.

        Args:
            user_id: User ID

        Returns:
            Namespace string
        """
        return f"user_{user_id}"

    async def generate_and_store_embeddings(
        self,
        db: AsyncSession,
        user_id: int,
        business_profile_id: int
    ) -> Dict[str, Any]:
        """
        Generate embeddings for business profile and store in Pinecone.

        Args:
            db: Database session
            user_id: User ID
            business_profile_id: Business profile ID

        Returns:
            Dict with embedding metadata
        """
        try:
            # Fetch business profile
            result = await db.execute(
                select(BusinessProfile).where(BusinessProfile.id == business_profile_id)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                raise ValueError(f"Business profile {business_profile_id} not found")

            # Enforce 2000 character limit on narrative_text
            narrative_text = profile.narrative_text or ""
            if len(narrative_text) > 2000:
                logger.warning(f"Narrative text exceeds 2000 chars, truncating for user {user_id}")
                narrative_text = narrative_text[:2000]

            # Build comprehensive text for embedding
            profile_text = self._build_profile_text(profile, narrative_text)

            # Chunk text
            chunks = self._chunk_text(profile_text, chunk_size=500, overlap=50)
            logger.info(f"Created {len(chunks)} chunks for user {user_id}")

            if not chunks:
                logger.warning(f"No text to embed for user {user_id}")
                return {
                    "success": False,
                    "error": "No text content to embed"
                }

            # Generate embeddings
            embeddings = await self.deepseek_client.generate_embeddings(chunks)

            # Prepare vectors for Pinecone
            namespace = self._get_user_namespace(user_id)
            vectors = []

            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector_id = f"profile_{business_profile_id}_chunk_{idx}"
                metadata = {
                    "user_id": user_id,
                    "profile_id": business_profile_id,
                    "chunk_index": idx,
                    "text": chunk,
                    "business_name": profile.business_name or "",
                    "created_at": datetime.utcnow().isoformat()
                }
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata
                })

            # Store in Pinecone
            self.index.upsert(vectors=vectors, namespace=namespace)
            logger.info(f"Stored {len(vectors)} embeddings for user {user_id}")

            # Update business profile
            profile.vector_embeddings_id = namespace
            profile.embeddings_generated_at = datetime.utcnow()
            await db.commit()

            return {
                "success": True,
                "chunks_created": len(chunks),
                "embeddings_stored": len(vectors),
                "namespace": namespace,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to generate embeddings for user {user_id}: {str(e)}")
            await db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    def _build_profile_text(self, profile: BusinessProfile, narrative_text: str) -> str:
        """
        Build comprehensive profile text from all fields.

        Args:
            profile: BusinessProfile model
            narrative_text: Narrative text (already truncated to 2000 chars)

        Returns:
            Combined text for embedding
        """
        parts = []

        # Business basics
        if profile.business_name:
            parts.append(f"Business Name: {profile.business_name}")

        if profile.mission_statement:
            parts.append(f"Mission: {profile.mission_statement}")

        if profile.service_description:
            parts.append(f"Services: {profile.service_description}")

        # Business details
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

        # Narrative (most important - should be last for prominence)
        if narrative_text:
            parts.append(f"Detailed Description: {narrative_text}")

        return "\n\n".join(parts)

    async def retrieve_relevant_context(
        self,
        user_id: int,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant business context for a grant application query.

        Args:
            user_id: User ID
            query: Query text (grant description, requirements, etc.)
            top_k: Number of top results to retrieve

        Returns:
            List of relevant text chunks with metadata
        """
        try:
            # Generate query embedding
            query_embeddings = await self.deepseek_client.generate_embeddings([query])
            query_embedding = query_embeddings[0]

            # Query Pinecone
            namespace = self._get_user_namespace(user_id)
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True
            )

            # Format results
            context_chunks = []
            for match in results.matches:
                context_chunks.append({
                    "text": match.metadata.get("text", ""),
                    "score": match.score,
                    "chunk_index": match.metadata.get("chunk_index"),
                    "business_name": match.metadata.get("business_name", "")
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
        """
        Update embeddings when business profile changes.

        Args:
            db: Database session
            user_id: User ID
            business_profile_id: Business profile ID

        Returns:
            Update result dict
        """
        try:
            # Delete old embeddings
            namespace = self._get_user_namespace(user_id)

            # Delete all vectors in namespace for this profile
            try:
                self.index.delete(
                    delete_all=True,
                    namespace=namespace
                )
                logger.info(f"Deleted old embeddings for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to delete old embeddings: {str(e)}")

            # Generate new embeddings
            result = await self.generate_and_store_embeddings(
                db=db,
                user_id=user_id,
                business_profile_id=business_profile_id
            )

            return result

        except Exception as e:
            logger.error(f"Failed to update embeddings for user {user_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def delete_user_embeddings(self, user_id: int) -> bool:
        """
        Delete all embeddings for a user.

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        try:
            namespace = self._get_user_namespace(user_id)
            self.index.delete(delete_all=True, namespace=namespace)
            logger.info(f"Deleted all embeddings for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete embeddings for user {user_id}: {str(e)}")
            return False

    async def get_embedding_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get statistics about user's embeddings.

        Args:
            user_id: User ID

        Returns:
            Stats dict
        """
        try:
            namespace = self._get_user_namespace(user_id)
            stats = self.index.describe_index_stats()

            namespace_stats = stats.namespaces.get(namespace, {})

            return {
                "namespace": namespace,
                "vector_count": namespace_stats.get("vector_count", 0),
                "has_embeddings": namespace_stats.get("vector_count", 0) > 0
            }
        except Exception as e:
            logger.error(f"Failed to get embedding stats for user {user_id}: {str(e)}")
            return {
                "namespace": self._get_user_namespace(user_id),
                "vector_count": 0,
                "has_embeddings": False,
                "error": str(e)
            }


# Singleton instance
_rag_service = None


def get_rag_service() -> ApplicationRAGService:
    """Get or create RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = ApplicationRAGService()
    return _rag_service
