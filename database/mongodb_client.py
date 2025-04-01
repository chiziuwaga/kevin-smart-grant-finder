import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError, OperationFailure
import pymongo
from dotenv import load_dotenv
from bson.objectid import ObjectId

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

class MongoDBClient:
    def __init__(self, use_mock: bool = True):
        """Initialize MongoDB client with connection to the grant database."""
        self.use_mock = use_mock
        
        if not use_mock:
            mongodb_uri = os.getenv("MONGODB_URI")
            if not mongodb_uri:
                raise ValueError("MongoDB URI not found in environment variables")
            
            # Connect to MongoDB
            self.client = pymongo.MongoClient(mongodb_uri)
            self.db = self.client[os.getenv("MONGODB_DATABASE", "grant_finder")]
            
            # Collections
            self.grants_collection = self.db["grants"]
            self.priorities = self.db["priorities"]
            self.search_history = self.db["search_history"]
            self.saved_grants = self.db["saved_grants"]
            
            # Create indexes for faster queries
            self._create_indexes()
            
            logging.info("MongoDB client initialized")
        else:
            logging.info("Using mock data for development")
            # Mock data for development
            self.mock_grants = [
                {
                    "_id": "1",
                    "title": "Rural Telecommunications Infrastructure Grant",
                    "description": "Funding for rural telecom infrastructure development",
                    "amount": 500000,
                    "deadline": datetime.utcnow() + timedelta(days=30),
                    "category": "telecom",
                    "relevance_score": 95,
                    "source_url": "https://example.com/grant1"
                },
                {
                    "_id": "2",
                    "title": "Nonprofit Digital Transformation Grant",
                    "description": "Support for nonprofits adopting digital solutions",
                    "amount": 250000,
                    "deadline": datetime.utcnow() + timedelta(days=15),
                    "category": "nonprofit",
                    "relevance_score": 88,
                    "source_url": "https://example.com/grant2"
                },
                {
                    "_id": "3",
                    "title": "Community Broadband Initiative",
                    "description": "Funding for community broadband projects",
                    "amount": 750000,
                    "deadline": datetime.utcnow() + timedelta(days=45),
                    "category": "telecom",
                    "relevance_score": 92,
                    "source_url": "https://example.com/grant3"
                }
            ]
            self.mock_saved_grants = []
            self.mock_priorities = {
                "type": "grant_priorities",
                "categories": ["telecom", "nonprofit"],
                "keywords": ["rural", "digital", "infrastructure"],
                "weights": {"relevance": 0.6, "deadline": 0.4}
            }

    def _create_indexes(self):
        """Create database indexes for optimized queries."""
        # Grants collection indexes
        self.grants_collection.create_index([("relevance_score", pymongo.DESCENDING)])
        self.grants_collection.create_index([("deadline", pymongo.ASCENDING)])
        self.grants_collection.create_index([("category", pymongo.ASCENDING)])
        self.grants_collection.create_index([("source_url", pymongo.ASCENDING)], unique=True)
        
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
        
        if self.use_mock:
            # Mock implementation
            grant_data["_id"] = str(len(self.mock_grants) + 1)
            self.mock_grants.append(grant_data)
            return grant_data["_id"]
        
        # Check if grant already exists (using URL as unique identifier)
        existing_grant = self.grants_collection.find_one({"source_url": grant_data["source_url"]})
        
        if existing_grant:
            # Update existing grant
            grant_data["first_found_at"] = existing_grant["first_found_at"]
            grant_data["last_updated"] = datetime.utcnow()
            
            # Update document
            self.grants_collection.update_one(
                {"_id": existing_grant["_id"]},
                {"$set": grant_data}
            )
            return str(existing_grant["_id"])
        else:
            # Insert new grant
            result = self.grants_collection.insert_one(grant_data)
            return str(result.inserted_id)
    
    def get_grants(self, 
                  min_score: Optional[float] = None, 
                  days_to_deadline: Optional[int] = None, 
                  category: Optional[str] = None,
                  search_text: Optional[str] = None,
                  limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve grants based on filtering criteria."""
        if self.use_mock:
            filtered_grants = self.mock_grants.copy()
            
            # Apply filters
            if min_score is not None:
                filtered_grants = [g for g in filtered_grants if g["relevance_score"] >= min_score]
                
            if days_to_deadline is not None:
                deadline_threshold = datetime.utcnow() + timedelta(days=days_to_deadline)
                filtered_grants = [g for g in filtered_grants if g["deadline"] <= deadline_threshold]
                
            if category and category != "All":
                filtered_grants = [g for g in filtered_grants if g["category"] == category]
                
            if search_text:
                filtered_grants = [g for g in filtered_grants 
                                 if search_text.lower() in g["title"].lower() 
                                 or search_text.lower() in g["description"].lower()]
            
            return filtered_grants[:limit]
        else:
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
            cursor = self.grants_collection.find(query).sort("relevance_score", pymongo.DESCENDING).limit(limit)
            
            # Convert cursor to list
            grants = list(cursor)
            
            return grants
    
    def save_grant_for_user(self, grant_id: str, user_id: str = "default") -> bool:
        """Save a grant for a specific user."""
        if self.use_mock:
            try:
                self.mock_saved_grants.append({
                    "user_id": user_id,
                    "grant_id": grant_id,
                    "saved_at": datetime.utcnow()
                })
                return True
            except Exception as e:
                logging.error(f"Error saving mock grant: {str(e)}")
                return False
        else:
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
        if self.use_mock:
            saved = [s for s in self.mock_saved_grants if s["user_id"] == user_id]
            grant_ids = [s["grant_id"] for s in saved]
            return [g for g in self.mock_grants if g["_id"] in grant_ids]
        else:
            saved = self.saved_grants.find({"user_id": user_id})
            grant_ids = [s["grant_id"] for s in saved]
            
            if not grant_ids:
                return []
                
            return list(self.grants_collection.find({"_id": {"$in": grant_ids}}))

    def store_priorities(self, priorities_data: Dict) -> bool:
        """Store or update priority settings."""
        if self.use_mock:
            try:
                priorities_data["updated_at"] = datetime.utcnow()
                self.mock_priorities = priorities_data
                return True
            except Exception as e:
                logging.error(f"Error storing mock priorities: {e}")
                return False
        else:
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
        """Retrieve current priority settings."""
        if self.use_mock:
            try:
                return self.mock_priorities
            except Exception as e:
                logging.error(f"Error retrieving mock priorities: {e}")
                return {}
        else:
            try:
                priorities = self.priorities.find_one({"type": "grant_priorities"})
                return priorities if priorities else {}
            except Exception as e:
                logging.error(f"Error retrieving priorities: {e}")
                return {}

    def store_source(self, source_data):
        """Store grant source information."""
        if self.use_mock:
            # Mock implementation for storing sources if needed
            if not hasattr(self, 'mock_sources'):
                self.mock_sources = []
            source_data["added_at"] = datetime.utcnow()
            source_data["last_checked"] = datetime.utcnow()
            self.mock_sources.append(source_data)
            logging.debug(f"Stored mock source: {source_data.get('name')}")
            return True

        # Non-mock implementation
        try:
            # Add timestamps
            source_data["added_at"] = datetime.utcnow()
            source_data["last_checked"] = datetime.utcnow()

            # Ensure the source collection exists (if not created elsewhere)
            if "sources" not in self.db.list_collection_names():
                 self.source_collection = self.db["sources"]
                 self.source_collection.create_index([("domain", pymongo.ASCENDING)])
                 self.source_collection.create_index([("name", pymongo.ASCENDING)], unique=True)
            elif not hasattr(self, 'source_collection'): # Assign if exists but not assigned
                 self.source_collection = self.db["sources"]


            # Check if source already exists by name
            existing_source = self.source_collection.find_one({"name": source_data["name"]})

            if existing_source:
                # Update existing source
                result = self.source_collection.update_one(
                    {"_id": existing_source["_id"]},
                    {"$set": {"last_checked": datetime.utcnow()}}
                )
                logging.debug(f"Updated source last_checked: {source_data.get('name')}")
                return existing_source["_id"]
            else:
                # Insert new source
                result = self.source_collection.insert_one(source_data)
                logging.debug(f"Inserted new source: {source_data.get('name')}")
                return result.inserted_id

        except Exception as e:
            logging.error(f"Error storing source {source_data.get('name', 'Unknown')}: {str(e)}")
            return None

    def get_sources_by_domain(self, domain: str = None) -> List[Dict]:
        """Retrieve sources, optionally filtered by domain."""
        if self.use_mock:
            # Mock implementation for getting sources
            mock_data = [
                {"name": "Grants.gov", "domain": "federal", "url": "https://www.grants.gov"},
                {"name": "USDA", "domain": "telecom", "url": "https://www.rd.usda.gov"},
                {"name": "FCC", "domain": "telecom", "url": "https://www.fcc.gov"},
                {"name": "IFundWomen", "domain": "nonprofit", "url": "https://www.ifundwomen.com"},
                {"name": "Amber Grant Foundation", "domain": "nonprofit", "url": "https://ambergrantsforwomen.com"},
                {"name": "Louisiana Grants", "domain": "state", "url": "https://www.opportunitylouisiana.gov/business-incentives/grants"}
            ]
            if domain:
                return [s for s in mock_data if s.get('domain') == domain]
            return mock_data

        # Non-mock implementation
        try:
            if "sources" not in self.db.list_collection_names():
                 logging.warning("'sources' collection does not exist.")
                 return []
            elif not hasattr(self, 'source_collection'):
                 self.source_collection = self.db["sources"]

            query = {}
            if domain:
                query = {"domain": domain}

            cursor = self.source_collection.find(query).sort("name", pymongo.ASCENDING)

            # Convert cursor to list and process ObjectId
            sources = []
            for source in cursor:
                source["_id"] = str(source["_id"])
                sources.append(source)

            return sources
        except Exception as e:
            logging.error(f"Error retrieving sources for domain {domain}: {str(e)}")
            return []

    # Add other methods like get_search_history, get_user_settings etc. if they are missing
    def get_search_history(self, limit: int = 5) -> List[Dict]:
        """Retrieve recent search history."""
        if self.use_mock:
            # Return mock search history
            return [
                {"search_date": datetime.now() - timedelta(hours=1), "parameters": {"category": "telecom"}, "results_count": 5},
                {"search_date": datetime.now() - timedelta(days=1), "parameters": {"category": "nonprofit"}, "results_count": 3}
            ]
        try:
            if "search_history" not in self.db.list_collection_names():
                 logging.warning("'search_history' collection does not exist.")
                 return []
            elif not hasattr(self, 'search_history'):
                 self.search_history = self.db["search_history"]

            cursor = self.search_history.find().sort("search_date", pymongo.DESCENDING).limit(limit)
            history = []
            for entry in cursor:
                entry["_id"] = str(entry["_id"])
                history.append(entry)
            return history
        except Exception as e:
            logging.error(f"Error retrieving search history: {str(e)}")
            return []

    def save_user_settings(self, settings: Dict, user_id: str = "default") -> bool:
        """Save user settings."""
        if self.use_mock:
            logging.info("Mock saving user settings.")
            return True
        
        # Non-mock implementation
        try:
            if not hasattr(self, 'user_settings_collection'):
                self.user_settings_collection = self.db["user_settings"]
                # Optional: Add index if needed, e.g., on user_id if supporting multiple users
                # self.user_settings_collection.create_index([("user_id", pymongo.ASCENDING)], unique=True)
            
            settings["updated_at"] = datetime.utcnow()
            result = self.user_settings_collection.update_one(
                {"user_id": user_id}, # Filter to find the specific user's settings
                {"$set": settings},     # Use $set to update fields
                upsert=True             # Create the document if it doesn't exist
            )
            logging.info(f"User settings saved/updated for user: {user_id}")
            return result.acknowledged
        except Exception as e:
            logging.error(f"Error saving user settings for {user_id}: {str(e)}")
            return False
    
    def get_user_settings(self, user_id: str = "default") -> Dict:
        """Retrieve user settings."""
        if self.use_mock:
            return {
                "notifications": {"sms_enabled": True, "telegram_enabled": True, "sms_number": "+1234567890", "telegram_username": "@testuser"},
                "relevance_threshold": 85,
                "deadline_threshold": 30,
                "schedule_frequency": "Twice Weekly",
                "schedule_days": ["Monday", "Thursday"],
                "schedule_time": "10:00"
            }
        
        # Non-mock implementation
        try:
            if not hasattr(self, 'user_settings_collection'):
                self.user_settings_collection = self.db["user_settings"]

            settings = self.user_settings_collection.find_one({"user_id": user_id})
            
            if settings:
                settings["_id"] = str(settings["_id"]) # Convert ObjectId
                return settings
            else:
                # Return default settings if none found for the user
                logging.info(f"No settings found for user {user_id}, returning defaults.")
                return {
                    "user_id": user_id, # Include user_id in default return
                    "notifications": {"sms_enabled": False, "telegram_enabled": False},
                    "relevance_threshold": 85,
                    "deadline_threshold": 30,
                    "schedule_frequency": "Twice Weekly",
                    # Add other defaults as needed
                }
        except Exception as e:
            logging.error(f"Error retrieving user settings for {user_id}: {str(e)}")
            return {} # Return empty dict on error

    # --- Alert History Methods (New) ---

    def record_alert_sent(self, user_id: str, grant_id: str) -> bool:
        """Records that an alert was sent for a specific grant to a user."""
        if self.use_mock: return True # Simulate success in mock mode
        try:
            if not isinstance(grant_id, ObjectId):
                grant_id = ObjectId(grant_id) # Ensure grant_id is ObjectId

            entry = {
                "user_id": user_id,
                "grant_id": grant_id,
                "alert_sent_at": datetime.utcnow()
            }
            self.alert_history_collection.insert_one(entry)
            logger.debug(f"Recorded alert sent for grant {grant_id} to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error recording alert sent for grant {grant_id} to user {user_id}: {e}")
            return False

    def check_alert_sent(self, user_id: str, grant_id: str, days_since: int) -> bool:
        """Checks if an alert for a specific grant was sent to a user within the last N days."""
        if self.use_mock: return False # Simulate not sent in mock mode
        try:
            if not isinstance(grant_id, ObjectId):
                grant_id = ObjectId(grant_id) # Ensure grant_id is ObjectId

            threshold_date = datetime.utcnow() - timedelta(days=days_since)
            query = {
                "user_id": user_id,
                "grant_id": grant_id,
                "alert_sent_at": {"$gte": threshold_date}
            }
            count = self.alert_history_collection.count_documents(query)
            was_sent = count > 0
            logger.debug(f"Checked alert status for grant {grant_id}, user {user_id} (within {days_since} days): Sent = {was_sent}")
            return was_sent
        except Exception as e:
            logger.error(f"Error checking alert status for grant {grant_id}, user {user_id}: {e}")
            return False # Assume not sent if error occurs