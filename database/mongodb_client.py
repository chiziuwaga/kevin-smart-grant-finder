import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
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
    def __init__(self):
        """Initialize MongoDB client with connection to grant database using component variables."""
        # self.use_mock = use_mock # Commented out
        # if use_mock: # Commented out
        # ... mock initialization logic ...
        #     return # Commented out

        # Real connection logic starts here
        # Get connection components from environment variables
        mongodb_user = os.getenv("MONGODB_USER")
        mongodb_password = os.getenv("MONGODB_PASSWORD")
        mongodb_host = os.getenv("MONGODB_HOST")
        mongodb_dbname = os.getenv("MONGODB_DBNAME", "grant_finder") # Default db name
        mongodb_authsource = os.getenv("MONGODB_AUTHSOURCE", "admin")
        mongodb_replicaset = os.getenv("MONGODB_REPLICASET")
        mongodb_ssl_str = os.getenv("MONGODB_SSL", "true").lower()

        # Basic validation
        if not all([mongodb_user, mongodb_password, mongodb_host]):
            logger.error("Missing required MongoDB connection components (User, Password, Host) in environment variables.")
            raise ConfigurationError("Missing required MongoDB connection components.")

        # Construct connection options
        options = {
            "username": mongodb_user,
            "password": mongodb_password,
            "authSource": mongodb_authsource,
            "ssl": mongodb_ssl_str == "true",
            "retryWrites": True, # Recommended for Atlas
            "w": "majority"     # Recommended for Atlas
        }
        if mongodb_replicaset:
            options["replicaSet"] = mongodb_replicaset

        # Construct the host string (usually includes port if not default)
        # For Atlas SRV records, the host usually handles ports/replicas, check Atlas instructions
        # If not using SRV, host might be like "host1:port1,host2:port2"
        host = mongodb_host

        try:
            # Connect to MongoDB
            # Use appropriate connection method based on host type (SRV or standard)
            # Assuming Atlas SRV record format for host, which pymongo handles directly
            connection_string = f"mongodb+srv://{mongodb_user}:{mongodb_password}@{mongodb_host}/?retryWrites=true&w=majority"
            if mongodb_replicaset:
                connection_string += f"&replicaSet={mongodb_replicaset}"
            if mongodb_authsource:
                connection_string += f"&authSource={mongodb_authsource}"

            # Alternative if *not* using SRV (less common for Atlas)
            # self.client = pymongo.MongoClient(host, **options, serverSelectionTimeoutMS=5000)

            self.client = pymongo.MongoClient(connection_string, serverSelectionTimeoutMS=5000)

            # Verify connection
            self.client.server_info() # Raise exception if connection fails
            self.db = self.client[mongodb_dbname]

            # Collections
            self.grants_collection = self.db["grants"]
            self.priorities_collection = self.db["priorities"]
            self.search_history_collection = self.db["search_history"]
            self.source_collection = self.db["sources"]
            self.user_settings_collection = self.db["user_settings"]
            self.alert_history_collection = self.db["alert_history"] # New collection

            # Create indexes for faster queries
            self._create_indexes()

            logger.info("MongoDB client initialized successfully using component variables.")
        except ConfigurationError as e:
             logger.error(f"MongoDB configuration error: {e}")
             raise
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error initializing MongoDB client: {e}")
            raise

    def _create_indexes(self):
        """Create database indexes for optimized queries."""
        # if self.use_mock: return # Commented out
        try:
            # Grant collection indexes (ensure no conflicts with existing)
            self.grants_collection.create_index([("relevance_score", pymongo.DESCENDING)], background=True)
            self.grants_collection.create_index([("deadline", pymongo.ASCENDING)], background=True)
            self.grants_collection.create_index([("category", pymongo.ASCENDING)], background=True)
            self.grants_collection.create_index([("source_name", pymongo.ASCENDING)], background=True)
            try:
                 self.grants_collection.create_index([("source_url", pymongo.ASCENDING)], unique=True, background=True)
            except OperationFailure as e:
                 logger.warning(f"Could not create unique index on source_url (might already exist non-uniquely or operation failed): {e}")

            # Search history indexes
            self.search_history_collection.create_index([("search_date", pymongo.DESCENDING)], background=True)
            self.search_history_collection.create_index([("category", pymongo.ASCENDING)], background=True)

            # Source collection indexes
            self.source_collection.create_index([("domain", pymongo.ASCENDING)], background=True)
            try:
                self.source_collection.create_index([("name", pymongo.ASCENDING)], unique=True, background=True)
            except OperationFailure as e:
                 logger.warning(f"Could not create unique index on source name: {e}")

            # User Settings index
            try:
                self.user_settings_collection.create_index([("user_id", pymongo.ASCENDING)], unique=True, background=True)
            except OperationFailure as e:
                 logger.warning(f"Could not create unique index on user_id: {e}")

            # Alert History indexes (New)
            self.alert_history_collection.create_index([("user_id", pymongo.ASCENDING)], background=True)
            self.alert_history_collection.create_index([("grant_id", pymongo.ASCENDING)], background=True)
            self.alert_history_collection.create_index([("alert_sent_at", pymongo.DESCENDING)], background=True)
            self.alert_history_collection.create_index([("user_id", pymongo.ASCENDING), ("grant_id", pymongo.ASCENDING)], background=True)

            logger.info("Database indexes checked/created.")
        except Exception as e:
             logger.error(f"Error creating database indexes: {e}")

    def store_grant(self, grant_data: Dict) -> Optional[str]:
        """Store a single grant in the database."""
        # if self.use_mock: # Commented out
        #     # ... mock store logic ...
        #     return grant_data["_id"] # Commented out
        
        # Real store logic starts here
        try:
            # Add timestamps
            now = datetime.utcnow()
            grant_data["last_updated"] = now

            # Upsert based on source_url
            result = self.grants_collection.update_one(
                {"source_url": grant_data["source_url"]},
                {
                    "$set": grant_data,
                    "$setOnInsert": {"first_found_at": now} # Set only on insert
                },
                upsert=True
            )

            if result.upserted_id:
                logger.debug(f"Inserted new grant: {grant_data.get('title', 'N/A')} ID: {result.upserted_id}")
                return str(result.upserted_id)
            elif result.matched_count > 0:
                # If matched, need to find the _id to return it
                existing = self.grants_collection.find_one({"source_url": grant_data["source_url"]}, {"_id": 1})
                if existing:
                    logger.debug(f"Updated existing grant: {grant_data.get('title', 'N/A')} ID: {existing['_id']}")
                    return str(existing['_id'])
            else:
                logger.warning(f"Upsert operation neither inserted nor matched for grant: {grant_data.get('title')}")
                return None
        except OperationFailure as e:
            # Handle potential duplicate key errors if unique index fails sometimes
            logger.error(f"Database operation failure storing grant {grant_data.get('title')}: {e}")
            # Try to find existing if it was a duplicate error
            if "duplicate key" in str(e).lower():
                existing = self.grants_collection.find_one({"source_url": grant_data["source_url"]}, {"_id": 1})
                if existing: return str(existing['_id'])
            return None
        except Exception as e:
            logger.error(f"Error storing grant {grant_data.get('title', 'N/A')}: {e}")
            return None

    def store_grants(self, grants_list: List[Dict]) -> int:
        """Store multiple grants efficiently."""
        # if self.use_mock: # Commented out
        #     # ... mock bulk store logic ...
        #     return count # Commented out
        
        # Real bulk store logic starts here
        if not grants_list:
            return 0
        
        # Use bulk operations for efficiency
        from pymongo import UpdateOne
        operations = []
        now = datetime.utcnow()
        stored_count = 0

        for grant in grants_list:
            grant["last_updated"] = now
            operations.append(
                UpdateOne(
                    {"source_url": grant["source_url"]},
                    {
                        "$set": grant,
                        "$setOnInsert": {"first_found_at": now}
                    },
                    upsert=True
                )
            )
        
        try:
            result = self.grants_collection.bulk_write(operations, ordered=False)
            stored_count = result.upserted_count + result.modified_count
            logger.info(f"Bulk stored/updated {stored_count} grants (Upserted: {result.upserted_count}, Modified: {result.modified_count}).")
            # Note: modified_count includes updates where data might not have changed
            return stored_count
        except pymongo.errors.BulkWriteError as bwe:
            logger.error(f"Error during bulk grant storage: {bwe.details}")
            # Still return potentially successful operations count
            return bwe.details.get('nUpserted', 0) + bwe.details.get('nModified', 0)
        except Exception as e:
            logger.error(f"Unexpected error during bulk grant storage: {e}")
            return 0

    def get_grants(self, min_score: Optional[float] = None, days_to_deadline: Optional[int] = None, category: Optional[Union[str, List[str]]] = None, search_text: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Retrieve grants based on filtering criteria."""
        # if self.use_mock: # Commented out
        #     # ... mock get grants logic ...
        #     return filtered_grants[:limit] # Commented out
        
        # Real get grants logic starts here
        try:
            query = {}
            now = datetime.utcnow()

            # Apply filters
            if min_score is not None:
                query["relevance_score"] = {"$gte": float(min_score)}
            if days_to_deadline is not None:
                deadline_threshold = now + timedelta(days=days_to_deadline)
                query["deadline"] = {"$lte": deadline_threshold, "$gte": now} # Only future deadlines
            if category and category != "All":
                if isinstance(category, list):
                    query["category"] = {"$in": category}
                else:
                    query["category"] = category
            # Add text search if implemented with text index
            # if search_text:
            #     query["$text"] = {"$search": search_text}

            cursor = self.grants_collection.find(query).sort("relevance_score", pymongo.DESCENDING).limit(limit)
            grants = []
            for grant in cursor:
                grant["_id"] = str(grant["_id"])
                grants.append(grant)
            logger.debug(f"Retrieved {len(grants)} grants matching query: {query}")
            return grants
        except Exception as e:
            logger.error(f"Error retrieving grants: {e}")
            return []
            
    def store_priorities(self, priorities_data: Dict) -> bool:
        """Store or update priority settings."""
        # if self.use_mock: # Commented out
        #     # ... mock store priorities logic ...
        #     return True # Commented out
        
        # Real store priorities logic starts here
        try:
            priorities_data["updated_at"] = datetime.utcnow()
            result = self.priorities_collection.replace_one(
                {"type": "grant_priorities"}, # Assuming a single doc for priorities
                priorities_data,
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            logger.error(f"Error storing priorities: {e}")
            return False

    def get_priorities(self) -> Dict:
        """Retrieve current priority settings."""
        # if self.use_mock: # Commented out
        #     # ... mock get priorities logic ...
        #     return self.mock_priorities # Commented out
        
        # Real get priorities logic starts here
        try:
            priorities = self.priorities_collection.find_one({"type": "grant_priorities"})
            if priorities:
                 priorities["_id"] = str(priorities["_id"])
            return priorities if priorities else {}
        except Exception as e:
            logger.error(f"Error retrieving priorities: {e}")
            return {}
            
    def store_source(self, source_data):
        """Store grant source information."""
        # if self.use_mock: # Commented out
        #     # ... mock store source logic ...
        #     return True # Commented out
        
        # Real store source logic starts here
        try:
            now = datetime.utcnow()
            result = self.source_collection.update_one(
                 {"name": source_data["name"]},
                 {"$set": {"last_checked": now, **source_data}, "$setOnInsert": {"added_at": now}},
                 upsert=True
             )
            if result.upserted_id:
                return str(result.upserted_id)
            elif result.matched_count:
                 existing = self.source_collection.find_one({"name": source_data["name"]})
                 return str(existing["_id"]) if existing else None
            return None
        except Exception as e:
            logger.error(f"Error storing source {source_data.get('name', 'Unknown')}: {str(e)}")
            return None

    def get_sources_by_domain(self, domain: Optional[str] = None) -> List[Dict]:
        """Retrieve sources, optionally filtered by domain."""
        # if self.use_mock: # Commented out
        #     # ... mock get sources logic ...
        #     return mock_data # Commented out
        
        # Real get sources logic starts here
        try:
            query = {} if domain is None else {"domain": domain}
            cursor = self.source_collection.find(query).sort("name", pymongo.ASCENDING)
            sources = []
            for source in cursor:
                source["_id"] = str(source["_id"])
                sources.append(source)
            return sources
        except Exception as e:
            logger.error(f"Error retrieving sources for domain {domain}: {str(e)}")
            return []
            
    def get_search_history(self, limit: int = 5) -> List[Dict]:
        """Retrieve recent search history."""
        # if self.use_mock: # Commented out
        #     # ... mock get history logic ...
        #     return [...] # Commented out
        
        # Real get history logic starts here
        try:
            cursor = self.search_history_collection.find().sort("search_date", pymongo.DESCENDING).limit(limit)
            history = []
            for entry in cursor:
                entry["_id"] = str(entry["_id"])
                history.append(entry)
            return history
        except Exception as e:
            logger.error(f"Error retrieving search history: {str(e)}")
            return []

    def save_user_settings(self, settings: Dict, user_id: str = "default_user") -> bool:
        """Save user settings."""
        # if self.use_mock: # Commented out
        #     pass # Commented out
        
        # Real save settings logic starts here
        try:
            settings["updated_at"] = datetime.utcnow()
            result = self.user_settings_collection.update_one(
                {"user_id": user_id},
                {"$set": settings},
                upsert=True
            )
            logger.info(f"User settings saved/updated for user: {user_id}")
            return result.acknowledged
        except Exception as e:
            logger.error(f"Error saving user settings for {user_id}: {str(e)}")
            return False

    def get_user_settings(self, user_id: str = "default_user") -> Dict:
        """Retrieve user settings."""
        # if self.use_mock: # Commented out
        #     # ... mock get settings logic ...
        #     return {...} # Commented out
        
        # Real get settings logic starts here
        try:
            settings = self.user_settings_collection.find_one({"user_id": user_id})
            if settings:
                settings["_id"] = str(settings["_id"])
                return settings
            else:
                logger.info(f"No settings found for user {user_id}, returning defaults.")
                # Return consistent default structure
                return {
                    "user_id": user_id,
                    "notifications": {"sms_enabled": False, "telegram_enabled": False, "sms_number": "", "telegram_username": ""},
                    "relevance_threshold": 85,
                    "deadline_threshold": 30,
                    "schedule_frequency": "Twice Weekly",
                    "schedule_days": ["Monday", "Thursday"],
                    "schedule_time": "10:00"
                }
        except Exception as e:
            logger.error(f"Error retrieving user settings for {user_id}: {str(e)}")
            return {} # Return empty dict on error

    def record_alert_sent(self, user_id: str, grant_id: str) -> bool:
        """Records that an alert was sent for a specific grant to a user."""
        # if self.use_mock: return True # Commented out
        
        # Real record alert logic starts here
        try:
            if not isinstance(grant_id, ObjectId):
                grant_id = ObjectId(grant_id)
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
        # if self.use_mock: return False # Commented out
        
        # Real check alert logic starts here
        try:
            if not isinstance(grant_id, ObjectId):
                grant_id = ObjectId(grant_id)
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