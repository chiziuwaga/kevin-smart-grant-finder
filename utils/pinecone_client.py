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

logger = logging.getLogger(__name__)

class PineconeClient:
    def __init__(self):
        """Initialize Pinecone client, with fallback to mock data if needed."""
        self.use_mock = False
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "grantcluster")
        self.expected_dimension = 3072 
        self.mock_relevance_range = (70.0, 95.0)
        self.pc = None
        self.index = None
        self.openai_client = None

        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")

        logger.info(f"Attempting to initialize PineconeClient with index_name: '{self.index_name}' and dimension: {self.expected_dimension}")

        if not pinecone_api_key:
            logging.critical("CRITICAL: PINECONE_API_KEY is missing. Pinecone client cannot be initialized.")
            self.use_mock = True
            self._setup_mock()
            return
        # else:
            # logger.info(f"Pinecone API Key found (Key: ...{pinecone_api_key[-4:] if len(pinecone_api_key) > 4 else 'SHORT_KEY'})")
            # Avoid logging the key directly, even partially, in most production scenarios unless for specific debugging.
            # For now, just confirming its presence is enough.
            # logger.info("Pinecone API Key is present.")

        if not openai_api_key:
            logging.critical("CRITICAL: OPENAI_API_KEY is missing. Pinecone client cannot generate embeddings.")
            self.use_mock = True
            self._setup_mock()
            return
        # else:
            # logger.info("OpenAI API Key is present.")

        try:
            logger.info("Initializing OpenAI client...")
            self.openai_client = openai.OpenAI(api_key=openai_api_key)
            logger.info("OpenAI client initialized successfully.")

            logger.info("Attempting to initialize Pinecone with API key...")
            try:
                self.pc = Pinecone(api_key=pinecone_api_key)
                logger.info("Pinecone client library initialized successfully (Pinecone object created).")
            except Exception as e_init:
                # This is a critical point. If Pinecone() itself fails, it might be the source of the "Name" error.
                logger.error(f"CRITICAL ERROR during Pinecone library initialization (Pinecone(api_key=...)): {str(e_init)}", exc_info=True)
                logger.error("This often indicates an issue with the API key itself, or how the client library interacts with your Pinecone project/environment configuration before any index-specific operations.")
                logger.error("Please verify your Pinecone Project Name on the dashboard for valid characters (lowercase alphanumeric, hyphens).")
                self.use_mock = True
                self._setup_mock()
                return

            index_description = None
            logger.info("Listing available Pinecone indexes...")
            available_indexes = self.pc.list_indexes().names()
            logger.info(f"Available indexes: {available_indexes}")

            if self.index_name in available_indexes:
                logger.info(f"Pinecone index '{self.index_name}' found. Describing index...")
                index_description = self.pc.describe_index(self.index_name)
                logger.info(f"Description for index '{self.index_name}': {index_description}")
                if index_description.dimension != self.expected_dimension:
                    logging.critical(
                        f"CRITICAL: Pinecone index '{self.index_name}' exists but has dimension {index_description.dimension}, "
                        f"expected {self.expected_dimension} for model 'text-embedding-3-large'. "
                        f"Please ensure index name in .env (PINECONE_INDEX_NAME) matches an index with dimension {self.expected_dimension}, "
                        f"or delete this index and let the client recreate it, or update the embedding model and expected_dimension."
                    )
                    self.use_mock = True
                    self._setup_mock()
                    return 
                self.index = self.pc.Index(self.index_name)
                logger.info(f"Successfully connected to Pinecone index: '{self.index_name}' with dimension {index_description.dimension}.")
            else:
                logger.warning(f"Pinecone index '{self.index_name}' not found in available list {available_indexes}. Attempting to create it.")
                self._create_index() 
                self.index = self.pc.Index(self.index_name)
                logger.info(f"Successfully created and connected to Pinecone index: '{self.index_name}'.")

        except Exception as e:
            logger.error(f"Failed to initialize real Pinecone client during main try block: {str(e)}. Falling back to mock Pinecone client.", exc_info=True)
            self.use_mock = True
            self._setup_mock()

    def _setup_mock(self):
        """Set up mock attributes and log message."""
        logging.warning("PineconeClient: Operating in MOCK mode. Real Pinecone operations will be skipped.")
        # self.index, self.pc, self.openai_client are already None or will be if init fails before this

    def _create_index(self):
        """Create Pinecone index if it doesn't exist."""
        if self.use_mock: 
            logging.debug("Mock mode: Skipping _create_index call.")
            return
        try:
            dimension = self.expected_dimension
            # Pinecone has deprecated `environment` in Pinecone() init, region/cloud are in spec for serverless.
            # For starter (free tier) indexes, they are serverless by default.
            # Ensure your Pinecone project is on a serverless-compatible tier if creating new indexes.
            # The region should ideally match where your app/other services are, or a default like "us-east-1".
            region = os.getenv("PINECONE_REGION", "us-east-1") # Make region configurable
            cloud = os.getenv("PINECONE_CLOUD", "aws") # Make cloud configurable
            metric = "cosine"
            
            logger.info(f"Creating new Pinecone index: '{self.index_name}' in cloud '{cloud}', region '{region}' with dimension {dimension}, metric '{metric}'.")
            self.pc.create_index(
                name=self.index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(cloud=cloud, region=region)
            )
            logger.info("Waiting for Pinecone index to be ready (up to 60s)...")
            # Wait for index to be ready - increased timeout slightly
            for _ in range(12): # Check every 5 seconds for up to 60 seconds
                if self.pc.describe_index(self.index_name).status['ready']:
                    logger.info(f"Pinecone index '{self.index_name}' created and ready.")
                    return
                time.sleep(5)
            logger.error(f"Pinecone index '{self.index_name}' did not become ready in time.")
            raise Exception(f"Index '{self.index_name}' not ready after timeout.")

        except Exception as e:
            logger.error(f"Error creating Pinecone index '{self.index_name}': {str(e)}", exc_info=True)
            # If creation fails, we must fallback to mock or signal critical failure
            logger.warning("Falling back to mock mode due to index creation failure.")
            self.use_mock = True 
            self._setup_mock()

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
                total_weight += weight            # Normalize score to 0-1 range
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
    
    async def verify_connection(self) -> bool:
        """Verify connection to Pinecone index for health checks."""
        try:
            if self.use_mock:
                logger.info("Pinecone health check: Running in mock mode - connection verified")
                return True
            
            if not self.index:
                logger.error("Pinecone health check failed: No index connection")
                return False
            
            # Try to get index stats as a connection test
            try:
                stats = self.index.describe_index_stats()
                total_vectors = getattr(stats, 'total_vector_count', 0)
                logger.info(f"Pinecone health check successful: {total_vectors} vectors in index")
                return True
            except Exception as stats_error:
                # If describe_index_stats fails, try a simpler connection test
                logger.warning(f"describe_index_stats failed: {stats_error}, trying alternative connection test")
                # Try to perform a simple query to test connection
                test_vector = [0.0] * self.expected_dimension
                _ = self.index.query(vector=test_vector, top_k=1)
                logger.info("Pinecone health check successful: Connection verified via query test")
                return True
            
        except Exception as e:
            logger.error(f"Pinecone health check failed: {str(e)}")
            return False
    
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
            metadata (Dict[str, Any): Updated metadata
            
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