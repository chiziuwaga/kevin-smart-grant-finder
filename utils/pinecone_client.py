import os
import logging
import time
from dotenv import load_dotenv
import openai
from pinecone import Pinecone, ServerlessSpec
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random # For mock data

class PineconeClient:
    def __init__(self):
        """Initialize Pinecone client, with fallback to mock data if needed."""
        self.use_mock = False
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "grant_priorities")
        self.mock_relevance_range = (70.0, 95.0) # Range for mock scores

        try:
            # Get API keys and config from environment variables
            pinecone_api_key = os.getenv("PINECONE_API_KEY")
            openai_api_key = os.getenv("OPENAI_API_KEY")

            if not pinecone_api_key or not openai_api_key:
                logging.warning("Pinecone or OpenAI API key missing. Falling back to mock Pinecone client.")
                self.use_mock = True
                self._setup_mock()
                return # Stop initialization here if mocking

            # Initialize OpenAI (for embeddings)
            self.openai_client = openai.OpenAI(api_key=openai_api_key)

            # Initialize Pinecone
            self.pc = Pinecone(api_key=pinecone_api_key)

            # Check if index exists, create if it doesn't
            if self.index_name not in self.pc.list_indexes().names():
                self._create_index() # This might still fail if permissions/config wrong

            # Connect to the index
            self.index = self.pc.Index(self.index_name)
            logging.info(f"Successfully connected to Pinecone index: {self.index_name}")

        except Exception as e:
            logging.error(f"Failed to initialize real Pinecone client: {str(e)}. Falling back to mock Pinecone client.")
            self.use_mock = True
            self._setup_mock()

    def _setup_mock(self):
        """Set up mock attributes and log message."""
        logging.info("Using Mock PineconeClient. Relevance scores will be simulated.")
        self.index = None # No real index connection for mock
        self.pc = None
        self.openai_client = None

    def _create_index(self):
        """Create Pinecone index if it doesn't exist."""
        if self.use_mock:
            logging.debug("Mock mode: Skipping _create_index")
            return
        try:
            # Corrected dimension and region based on user info and OpenAI model
            dimension = 1536 # For text-embedding-3-small
            region = "us-east-1" # Aligned with existing index
            metric = "cosine"
            
            self.pc.create_index(
                name=self.index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(cloud="aws", region=region)
            )
            logging.info(f"Created new Pinecone index: {self.index_name} in region {region} with dimension {dimension}")
        except Exception as e:
            logging.error(f"Error creating Pinecone index: {str(e)}")
            raise
    
    def calculate_relevance(self, grant_description, grant_title=None):
        """Calculate relevance score (real or mock)."""
        if self.use_mock:
            # Simulate a plausible relevance score
            mock_score = round(random.uniform(*self.mock_relevance_range), 2)
            logging.debug(f"Mock mode: Returning simulated relevance score: {mock_score}")
            return mock_score

        # --- Real implementation --- #
        try:
            if not self.index or not self.openai_client:
                logging.error("Real Pinecone/OpenAI client not initialized properly for relevance calculation.")
                return 0.0 # Fallback score

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
            logging.error(f"Error calculating real relevance score: {str(e)}")
            return 0.0  # Default fallback score 0
    
    def _generate_embedding(self, text):
        """Generate vector embedding (real or mock)."""
        if self.use_mock or not self.openai_client:
            logging.debug("Mock mode: Skipping _generate_embedding")
            # Return a dummy vector of the correct dimension if needed by callers
            # Dimension for text-embedding-3-small is 1536
            return [random.random() for _ in range(1536)]

        # --- Real implementation --- #
        try:
             response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
             )
             return response.data[0].embedding
        except Exception as e:
            logging.error(f"Error generating OpenAI embedding: {str(e)}")
            # Need to decide how to handle this - raise error or return dummy?
            # Returning dummy vector for now to potentially allow flow continuation
            return [0.0] * 1536

    async def store_grant_embedding(self, 
                                  grant_id: str, 
                                  embedding: List[float], 
                                  metadata: Dict[str, Any]) -> bool:
        """Store grant embedding (real or mock)."""
        if self.use_mock:
            logging.debug(f"Mock mode: Pretending to store embedding for grant {grant_id}")
            return True # Simulate success

        # --- Real implementation --- #
        try:
            if not self.index:
                logging.error("Real Pinecone index not initialized. Cannot store embedding.")
                return False

            # Ensure embedding is normalized (important for cosine metric)
            embedding_np = np.array(embedding)
            norm = np.linalg.norm(embedding_np)
            if norm == 0:
                # Handle zero vectors if they occur
                 logging.warning(f"Attempted to store zero vector for grant {grant_id}")
                 return False
            normalized_embedding = (embedding_np / norm).tolist()

            # Add timestamp to metadata
            metadata["stored_at"] = datetime.utcnow().isoformat()
            
            # Upsert the vector
            self.index.upsert(
                vectors=[(grant_id, normalized_embedding, metadata)]
            )
            logging.info(f"Stored embedding for grant {grant_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error storing real grant embedding for {grant_id}: {str(e)}")
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
        if self.use_mock:
            logging.debug("Mock mode: Returning empty list for find_similar_grants")
            return []
        # --- Real implementation --- #
        try:
            if not self.index:
                 logging.error("Real Pinecone index not initialized. Cannot find similar grants.")
                 return []

            # Normalize query embedding
            query_np = np.array(query_embedding)
            norm = np.linalg.norm(query_np)
            if norm == 0:
                 logging.warning("Attempted find_similar_grants with zero vector query.")
                 return []
            normalized_query = (query_np / norm).tolist()

            # Query the index
            results = self.index.query(
                vector=normalized_query,
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
        if self.use_mock:
             logging.debug(f"Mock mode: Pretending to update metadata for grant {grant_id}")
             return True
        # --- Real implementation --- #
        try:
            if not self.index:
                logging.error("Real Pinecone index not initialized. Cannot update metadata.")
                return False

            # Update requires upserting with the full vector
            vector_data = self.index.fetch([grant_id])

            if not vector_data.vectors or grant_id not in vector_data.vectors:
                logging.warning(f"Attempted to update metadata for non-existent grant {grant_id}")
                return False

            existing_vector = vector_data.vectors[grant_id]
            # Merge old and new metadata, preferring new values
            updated_metadata = {**existing_vector.metadata, **metadata}
            updated_metadata["updated_at"] = datetime.utcnow().isoformat() # Add update timestamp

            self.index.upsert(
                vectors=[(grant_id, existing_vector.values, updated_metadata)]
            )
            logging.info(f"Updated metadata for grant {grant_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error updating grant metadata for {grant_id}: {str(e)}")
            return False
    
    async def delete_grant(self, grant_id: str) -> bool:
        """Delete a grant from the vector database.
        
        Args:
            grant_id (str): Grant identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.use_mock:
            logging.debug(f"Mock mode: Pretending to delete grant {grant_id}")
            return True
        # --- Real implementation --- #
        try:
             if not self.index:
                logging.error("Real Pinecone index not initialized. Cannot delete grant.")
                return False

             self.index.delete(ids=[grant_id])
             logging.info(f"Deleted grant {grant_id} from Pinecone.")
             return True
        except Exception as e:
            logging.error(f"Error deleting grant {grant_id}: {str(e)}")
            return False