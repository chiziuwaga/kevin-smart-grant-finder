import os
import logging
from typing import Dict, List, Optional

import pinecone
import openai
from openai import OpenAI

class PineconeClient:
    def __init__(self):
        """Initialize Pinecone client for vector similarity search."""
        api_key = os.getenv("PINECONE_API_KEY")
        environment = os.getenv("PINECONE_ENVIRONMENT")
        index_name = os.getenv("PINECONE_INDEX_NAME")
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        if not all([api_key, environment, index_name, openai.api_key]):
            raise ValueError("Missing required environment variables for Pinecone/OpenAI setup")

        try:
            pinecone.init(api_key=api_key, environment=environment)
            
            # Create index if it doesn't exist
            if index_name not in pinecone.list_indexes():
                self._create_index(index_name)
                
            self.index = pinecone.Index(index_name)
            self.openai_client = OpenAI()
            logging.info("Successfully initialized Pinecone client")
        except Exception as e:
            logging.error(f"Failed to initialize Pinecone: {e}")
            raise

    def _create_index(self, index_name: str):
        """Create a new Pinecone index.

        Args:
            index_name (str): Name of the index to create.
        """
        try:
            pinecone.create_index(
                name=index_name,
                dimension=1536,  # OpenAI embedding dimension
                metric="cosine"
            )
            logging.info(f"Created new Pinecone index: {index_name}")
        except Exception as e:
            logging.error(f"Failed to create Pinecone index: {e}")
            raise

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text using OpenAI.

        Args:
            text (str): Text to generate embedding for.

        Returns:
            List[float]: Embedding vector.
        """
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logging.error(f"Failed to generate embedding: {e}")
            raise

    def store_priority_vectors(self, priorities: Dict) -> bool:
        """Store priority vectors in Pinecone.

        Args:
            priorities (Dict): Priority configuration including keywords and categories.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Clear existing vectors
            self.index.delete(deleteAll=True)
            
            vectors_to_upsert = []
            
            # Process keywords with weights
            for category, keywords in priorities.get("keywords", {}).items():
                for keyword in keywords:
                    vector = self._generate_embedding(keyword)
                    vectors_to_upsert.append((
                        f"kw_{category}_{keyword}",
                        vector,
                        {"type": "keyword", "category": category}
                    ))
            
            # Process categories
            for category, weight in priorities.get("categories", {}).items():
                vector = self._generate_embedding(category)
                vectors_to_upsert.append((
                    f"cat_{category}",
                    vector,
                    {"type": "category", "weight": weight}
                ))
            
            # Upsert vectors in batches
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                self.index.upsert(vectors=[
                    (id, vec, meta) for id, vec, meta in batch
                ])
            
            return True
        except Exception as e:
            logging.error(f"Failed to store priority vectors: {e}")
            return False

    def calculate_relevance(self, grant_description: str) -> float:
        """Calculate relevance score for a grant description.

        Args:
            grant_description (str): Grant description text.

        Returns:
            float: Relevance score between 0 and 1.
        """
        try:
            # Generate embedding for grant description
            query_vector = self._generate_embedding(grant_description)
            
            # Query similar vectors
            results = self.index.query(
                vector=query_vector,
                top_k=10,
                include_metadata=True
            )
            
            if not results.matches:
                return 0.0
            
            # Calculate weighted relevance score
            total_score = 0.0
            total_weight = 0.0
            
            for match in results.matches:
                similarity = match.score
                metadata = match.metadata
                
                if metadata["type"] == "category":
                    weight = metadata.get("weight", 1.0)
                else:  # keyword match
                    weight = 1.0
                
                total_score += similarity * weight
                total_weight += weight
            
            # Normalize score
            normalized_score = (total_score / total_weight) if total_weight > 0 else 0
            
            return round(normalized_score, 3)
        except Exception as e:
            logging.error(f"Failed to calculate relevance: {e}")
            return 0.0