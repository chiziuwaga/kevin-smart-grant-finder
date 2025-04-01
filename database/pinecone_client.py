import os
import logging
import time
from dotenv import load_dotenv
import openai
from pinecone import Pinecone, ServerlessSpec
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

class PineconeClient:
    def __init__(self):
        """Initialize Pinecone client for vector storage and similarity search."""
        try:
            # Get API keys and config from environment variables
            pinecone_api_key = os.getenv("PINECONE_API_KEY")
            self.index_name = os.getenv("PINECONE_INDEX_NAME", "grant_priorities")
            
            if not pinecone_api_key:
                raise ValueError("Pinecone API key not found in environment variables")
            
            # Initialize OpenAI (for embeddings)
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OpenAI API key not found in environment variables")
            
            self.openai_client = openai.OpenAI(api_key=openai_api_key)
            
            # Initialize Pinecone
            self.pc = Pinecone(api_key=pinecone_api_key)
            
            # Check if index exists, create if it doesn't
            if self.index_name not in self.pc.list_indexes().names():
                self._create_index()
            
            # Connect to the index
            self.index = self.pc.Index(self.index_name)
            logging.info(f"Connected to Pinecone index: {self.index_name}")
        except Exception as e:
            logging.error(f"Failed to initialize Pinecone: {str(e)}")
            raise
    
    def _create_index(self):
        """Create Pinecone index if it doesn't exist."""
        try:
            self.pc.create_index(
                name=self.index_name,
                dimension=1536,  # Dimension for OpenAI text-embedding-3-small model
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-west-2")
            )
            logging.info(f"Created new Pinecone index: {self.index_name}")
        except Exception as e:
            logging.error(f"Error creating Pinecone index: {str(e)}")
            raise
    
    def calculate_relevance(self, grant_description, grant_title=None):
        """Calculate relevance score for a grant."""
        try:
            combined_text = grant_description
            if grant_title:
                combined_text = f"Title: {grant_title}\n\n{combined_text}"
                
            # Generate embedding
            vector = self._generate_embedding(combined_text)
            
            # Query Pinecone
            results = self.index.query(
                vector=vector,
                top_k=5,
                include_metadata=True
            )
            
            # Calculate weighted score
            total_score = 0
            total_weight = 0
            
            for match in results.matches:
                similarity = match.score
                weight = match.metadata.get("weight", 1.0)
                
                total_score += similarity * weight
                total_weight += weight
            
            # Normalize score to 0-1 range
            if total_weight > 0:
                # Convert cosine similarity (0 to 1) to relevance (0 to 100)
                # Assuming higher cosine score means more relevant
                normalized_score = (total_score / total_weight) * 100.0
            else:
                normalized_score = 0.0
            
            return round(normalized_score, 2) # Return score 0-100
            
        except Exception as e:
            logging.error(f"Error calculating relevance score: {str(e)}")
            return 0.0  # Default fallback score 0
    
    def _generate_embedding(self, text):
        """Generate vector embedding for text using OpenAI."""
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    async def store_grant_embedding(self, 
                                  grant_id: str, 
                                  embedding: List[float], 
                                  metadata: Dict[str, Any]) -> bool:
        """Store grant embedding and metadata in Pinecone.
        
        Args:
            grant_id (str): Unique identifier for the grant
            embedding (List[float]): Vector embedding of grant content
            metadata (Dict[str, Any]): Additional grant metadata
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure embedding is normalized
            embedding_np = np.array(embedding)
            normalized_embedding = embedding_np / np.linalg.norm(embedding_np)
            
            # Add timestamp to metadata
            metadata["stored_at"] = datetime.utcnow().isoformat()
            
            # Upsert the vector
            self.index.upsert(
                vectors=[(grant_id, normalized_embedding.tolist(), metadata)]
            )
            return True
            
        except Exception as e:
            logging.error(f"Error storing grant embedding: {str(e)}")
            return False
    
    async def find_similar_grants(self, 
                                query_embedding: List[float], 
                                top_k: int = 10, 
                                filter: Optional[Dict] = None) -> List[Dict]:
        """Find similar grants using vector similarity search.
        
        Args:
            query_embedding (List[float]): Query vector
            top_k (int): Number of results to return
            filter (Optional[Dict]): Metadata filters
            
        Returns:
            List[Dict]: Similar grants with scores and metadata
        """
        try:
            # Normalize query embedding
            query_np = np.array(query_embedding)
            normalized_query = query_np / np.linalg.norm(query_np)
            
            # Query the index
            results = self.index.query(
                vector=normalized_query.tolist(),
                top_k=top_k,
                include_metadata=True,
                filter=filter
            )
            
            # Process results
            similar_grants = []
            for match in results.matches:
                similar_grants.append({
                    "grant_id": match.id,
                    "similarity_score": match.score,
                    "metadata": match.metadata
                })
            
            return similar_grants
            
        except Exception as e:
            logging.error(f"Error searching similar grants: {str(e)}")
            return []
    
    async def update_grant_metadata(self, grant_id: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for a stored grant.
        
        Args:
            grant_id (str): Grant identifier
            metadata (Dict[str, Any]): Updated metadata
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get existing vector
            vector_data = self.index.fetch([grant_id])
            
            if not vector_data.vectors:
                return False
            
            # Update with new metadata
            existing_vector = vector_data.vectors[grant_id]
            self.index.upsert(
                vectors=[(
                    grant_id,
                    existing_vector.values,
                    {**existing_vector.metadata, **metadata}
                )]
            )
            return True
            
        except Exception as e:
            logging.error(f"Error updating grant metadata: {str(e)}")
            return False
    
    async def delete_grant(self, grant_id: str) -> bool:
        """Delete a grant from the vector database.
        
        Args:
            grant_id (str): Grant identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.index.delete(ids=[grant_id])
            return True
        except Exception as e:
            logging.error(f"Error deleting grant: {str(e)}")
            return False