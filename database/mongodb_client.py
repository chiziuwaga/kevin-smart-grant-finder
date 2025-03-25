import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionError, OperationFailure

class MongoDBClient:
    def __init__(self):
        """Initialize MongoDB client with connection to grant database."""
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            raise ValueError("MongoDB URI not found in environment variables")
        
        try:
            self.client = MongoClient(mongodb_uri)
            self.db = self.client.grant_finder
            self.grants = self.db.grants
            self.priorities = self.db.priorities
            self._create_indexes()
            logging.info("Successfully connected to MongoDB")
        except ConnectionError as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            raise

    def _create_indexes(self):
        """Create necessary indexes for efficient querying."""
        try:
            self.grants.create_index([("score", DESCENDING)])
            self.grants.create_index([("deadline", ASCENDING)])
            self.grants.create_index([("category", ASCENDING)])
            logging.info("Successfully created MongoDB indexes")
        except OperationFailure as e:
            logging.error(f"Failed to create indexes: {e}")
            raise

    def store_grant(self, grant_data: Dict) -> bool:
        """Store a single grant in the database.

        Args:
            grant_data (Dict): Grant information including title, description,
                              amount, deadline, source, and relevance score.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            grant_data["created_at"] = datetime.utcnow()
            grant_data["updated_at"] = datetime.utcnow()
            
            # Upsert based on unique identifiers to avoid duplicates
            result = self.grants.update_one(
                {
                    "title": grant_data["title"],
                    "source": grant_data["source"]
                },
                {"$set": grant_data},
                upsert=True
            )
            return bool(result.acknowledged)
        except Exception as e:
            logging.error(f"Error storing grant: {e}")
            return False

    def store_grants(self, grants_list: List[Dict]) -> int:
        """Store multiple grants in the database.

        Args:
            grants_list (List[Dict]): List of grant dictionaries.

        Returns:
            int: Number of successfully stored grants.
        """
        successful_stores = 0
        for grant in grants_list:
            if self.store_grant(grant):
                successful_stores += 1
        return successful_stores

    def get_grants(self, min_score: Optional[float] = None,
                  days_to_deadline: Optional[int] = None,
                  category: Optional[str] = None,
                  limit: int = 100) -> List[Dict]:
        """Retrieve grants based on filters.

        Args:
            min_score (float, optional): Minimum relevance score.
            days_to_deadline (int, optional): Maximum days until deadline.
            category (str, optional): Grant category to filter by.
            limit (int): Maximum number of grants to return.

        Returns:
            List[Dict]: List of matching grants.
        """
        query = {}
        
        if min_score is not None:
            query["score"] = {"$gte": min_score}
            
        if days_to_deadline is not None:
            deadline_date = datetime.utcnow()
            query["deadline"] = {"$gte": deadline_date}
            
        if category:
            query["category"] = category

        try:
            return list(self.grants.find(query)
                       .sort("score", DESCENDING)
                       .limit(limit))
        except Exception as e:
            logging.error(f"Error retrieving grants: {e}")
            return []

    def store_priorities(self, priorities_data: Dict) -> bool:
        """Store or update priority settings.

        Args:
            priorities_data (Dict): Priority configuration including keywords,
                                   categories, and weights.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            priorities_data["updated_at"] = datetime.utcnow()
            result = self.priorities.replace_one(
                {"type": "grant_priorities"},
                priorities_data,
                upsert=True
            )
            return bool(result.acknowledged)
        except Exception as e:
            logging.error(f"Error storing priorities: {e}")
            return False

    def get_priorities(self) -> Dict:
        """Retrieve current priority settings.

        Returns:
            Dict: Priority configuration or empty dict if not found.
        """
        try:
            priorities = self.priorities.find_one({"type": "grant_priorities"})
            return priorities if priorities else {}
        except Exception as e:
            logging.error(f"Error retrieving priorities: {e}")
            return {}