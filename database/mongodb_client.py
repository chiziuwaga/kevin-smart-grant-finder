import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError, OperationFailure
import pymongo
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MongoDBClient:
    def __init__(self):
        """Initialize MongoDB client with connection to the grant database."""
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            raise ValueError("MongoDB URI not found in environment variables")
        
        # Connect to MongoDB
        self.client = pymongo.MongoClient(mongodb_uri)
        self.db = self.client[os.getenv("MONGODB_DATABASE", "grant_finder")]
        
        # Collections
        self.grants = self.db["grants"]
        self.priorities = self.db["priorities"]
        self.search_history = self.db["search_history"]
        self.saved_grants = self.db["saved_grants"]
        
        # Create indexes for faster queries
        self._create_indexes()
        
        logging.info("MongoDB client initialized")
    
    def _create_indexes(self):
        """Create database indexes for optimized queries."""
        # Grants collection indexes
        self.grants.create_index([("relevance_score", pymongo.DESCENDING)])
        self.grants.create_index([("deadline", pymongo.ASCENDING)])
        self.grants.create_index([("category", pymongo.ASCENDING)])
        self.grants.create_index([("source_url", pymongo.ASCENDING)], unique=True)
        
        # Search history indexes
        self.search_history.create_index([("timestamp", pymongo.DESCENDING)])
        self.search_history.create_index([("category", pymongo.ASCENDING)])
        
        # Saved grants indexes
        self.saved_grants.create_index([("user_id", pymongo.ASCENDING)])
        self.saved_grants.create_index([("grant_id", pymongo.ASCENDING)])
    
    def store_grant(self, grant_data: Dict[str, Any]) -> str:
        """Store a single grant in the database."""
        # Add timestamps
        grant_data["first_found_at"] = datetime.utcnow()
        grant_data["last_updated"] = datetime.utcnow()
        
        # Check if grant already exists (using URL as unique identifier)
        existing_grant = self.grants.find_one({"source_url": grant_data["source_url"]})
        
        if existing_grant:
            # Update existing grant
            grant_data["first_found_at"] = existing_grant["first_found_at"]
            grant_data["last_updated"] = datetime.utcnow()
            
            # Update document
            self.grants.update_one(
                {"_id": existing_grant["_id"]},
                {"$set": grant_data}
            )
            return str(existing_grant["_id"])
        else:
            # Insert new grant
            result = self.grants.insert_one(grant_data)
            return str(result.inserted_id)
    
    def get_grants(self, 
                  min_score: Optional[float] = None, 
                  days_to_deadline: Optional[int] = None, 
                  category: Optional[str] = None,
                  search_text: Optional[str] = None,
                  limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve grants based on filtering criteria."""
        query = {}
        
        # Apply filters if provided
        if min_score is not None:
            query["relevance_score"] = {"$gte": min_score}
            
        if days_to_deadline is not None:
            deadline_threshold = datetime.utcnow() + timedelta(days=days_to_deadline)
            query["deadline"] = {"$lte": deadline_threshold}
            
        if category and category != "All":
            query["category"] = category
            
        if search_text:
            query["$or"] = [
                {"title": {"$regex": search_text, "$options": "i"}},
                {"description": {"$regex": search_text, "$options": "i"}}
            ]
        
        # Execute query
        cursor = self.grants.find(query).sort("relevance_score", pymongo.DESCENDING).limit(limit)
        
        # Convert cursor to list
        grants = list(cursor)
        
        return grants
    
    def save_grant_for_user(self, grant_id: str, user_id: str = "default") -> bool:
        """Save a grant for a specific user."""
        try:
            self.saved_grants.insert_one({
                "user_id": user_id,
                "grant_id": grant_id,
                "saved_at": datetime.utcnow()
            })
            return True
        except Exception as e:
            logging.error(f"Error saving grant: {str(e)}")
            return False
    
    def get_saved_grants(self, user_id: str = "default") -> List[Dict[str, Any]]:
        """Get all saved grants for a user."""
        saved = self.saved_grants.find({"user_id": user_id})
        grant_ids = [s["grant_id"] for s in saved]
        
        if not grant_ids:
            return []
            
        return list(self.grants.find({"_id": {"$in": grant_ids}}))

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