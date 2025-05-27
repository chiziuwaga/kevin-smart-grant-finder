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
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "grantcluster") # Using existing 3072-dim index
        self.expected_dimension = 3072 # For text-embedding-3-large
        self.mock_relevance_range = (70.0, 95.0)
        self.pc = None
        self.index = None
        self.openai_client = None

        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if not pinecone_api_key:
            logging.critical("CRITICAL: PINECONE_API_KEY is missing. Pinecone client cannot be initialized.")
            self.use_mock = True # Fallback to mock if essential keys are missing
            self._setup_mock()
            return
        if not openai_api_key:
            logging.critical("CRITICAL: OPENAI_API_KEY is missing. Pinecone client cannot generate embeddings.")
            self.use_mock = True # Fallback to mock if essential keys are missing
            self._setup_mock()
            return

        try:
            self.openai_client = openai.OpenAI(api_key=openai_api_key)
            self.pc = Pinecone(api_key=pinecone_api_key)

            index_description = None
            available_indexes = self.pc.list_indexes().names()
            if self.index_name in available_indexes:
                logging.info(f"Pinecone index '{self.index_name}' found. Describing index...")
                index_description = self.pc.describe_index(self.index_name)
                if index_description.dimension != self.expected_dimension:
                    logging.critical(
                        f"CRITICAL: Pinecone index '{self.index_name}' exists but has dimension {index_description.dimension}, "
                        f"expected {self.expected_dimension} for model 'text-embedding-3-small'. "
                        f"Please ensure index name in .env (PINECONE_INDEX_NAME) matches an index with dimension {self.expected_dimension}, "
                        f"or update the embedding model and expected_dimension in pinecone_client.py."
                    )
                    # Do not connect to this index, effectively disabling real Pinecone ops
                    self.use_mock = True
                    self._setup_mock()
                    return 
                self.index = self.pc.Index(self.index_name)
                logging.info(f"Successfully connected to Pinecone index: '{self.index_name}' with dimension {index_description.dimension}.")
            else:
                logging.warning(f"Pinecone index '{self.index_name}' not found. Attempting to create it.")
                self._create_index() # This might raise an exception if it fails
                self.index = self.pc.Index(self.index_name)
                logging.info(f"Successfully created and connected to Pinecone index: '{self.index_name}'.")

        except Exception as e:
            logging.error(f"Failed to initialize real Pinecone client: {str(e)}. Falling back to mock Pinecone client.", exc_info=True)
            self.use_mock = True
            self._setup_mock()

    def _setup_mock(self):
        """Set up mock attributes and log message."""
        logging.warning("PineconeClient: Operating in MOCK mode. Real Pinecone operations will be skipped.")
        # self.index, self.pc, self.openai_client are already None or will be if init fails before this

    def _create_index(self):
        """Create Pinecone index if it doesn't exist."""
        if self.use_mock: # Should not happen if we intend to create
            logging.debug("Mock mode: Skipping _create_index call.")
            return
        try:
            dimension = self.expected_dimension
            region = "us-east-1" # As per user's existing grant-cluster index
            metric = "cosine"
            
            logging.info(f"Creating new Pinecone index: '{self.index_name}' in region '{region}' with dimension {dimension}, metric '{metric}'.")
            self.pc.create_index(
                name=self.index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(cloud="aws", region=region)
            )
            # Wait for index to be ready
            while not self.pc.describe_index(self.index_name).status['ready']:
                logging.info("Waiting for Pinecone index to be ready...")
                time.sleep(5)
            logging.info(f"Pinecone index '{self.index_name}' created and ready.")
        except Exception as e:
            logging.error(f"Error creating Pinecone index '{self.index_name}': {str(e)}", exc_info=True)
            # If creation fails, we must fallback to mock or signal critical failure
            self.use_mock = True 
            self._setup_mock() # Ensure mock setup is called on creation failure
            raise # Re-raise the exception to make the failure clear during startup
    
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
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI's API."""
        if self.use_mock:
            # Return mock embedding of correct dimension
            return [random.uniform(-1, 1) for _ in range(self.expected_dimension)]
        
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-large",  # Updated to match 3072 dimensions
            input=text
        )
        return response.data[0].embedding

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