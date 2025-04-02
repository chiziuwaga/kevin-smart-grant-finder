import os
import logging
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson.objectid import ObjectId

class MongoDBClient:
    def __init__(self):
        try:
            username = os.getenv('MONGODB_USERNAME')
            password = os.getenv('MONGODB_PASSWORD')
            host = os.getenv('MONGODB_HOST')
            port = os.getenv('MONGODB_PORT')
            auth_source = os.getenv('MONGODB_AUTH_SOURCE', 'admin')
            
            connection_string = f'mongodb+srv://{username}:{password}@{host}/?authSource={auth_source}&ssl=true'
            self.client = MongoClient(connection_string)
            self.db = self.client.grant_finder
            
            # Initialize collections
            self.grants = self.db.grants
            self.priorities = self.db.priorities
            self.search_history = self.db.search_history
            self.sources = self.db.sources
            self.user_settings = self.db.user_settings
            self.alert_history = self.db.alert_history
            self.saved_grants = self.db.saved_grants
            
            self._create_indexes()
            logging.info('MongoDB client initialized successfully')
            
        except Exception as e:
            logging.error(f'Failed to initialize MongoDB client: {str(e)}')
            raise
    
    def _create_indexes(self):
        try:
            # Create indexes in background
            self.grants.create_index([('title', ASCENDING)], background=True)
            self.grants.create_index([('source', ASCENDING)], background=True)
            self.grants.create_index([('deadline', ASCENDING)], background=True)
            
            self.priorities.create_index([('user_id', ASCENDING)], background=True)
            self.search_history.create_index([('user_id', ASCENDING)], background=True)
            self.search_history.create_index([('timestamp', DESCENDING)], background=True)
            
            self.user_settings.create_index([('user_id', ASCENDING)], unique=True, background=True)
            self.alert_history.create_index([('user_id', ASCENDING)], background=True)
            self.alert_history.create_index([('grant_id', ASCENDING)], background=True)
            self.alert_history.create_index([('timestamp', DESCENDING)], background=True)
            
            self.saved_grants.create_index([('user_id', ASCENDING)], background=True)
            self.saved_grants.create_index([('grant_id', ASCENDING)], background=True)
            
        except Exception as e:
            logging.error(f'Failed to create indexes: {str(e)}')
            raise
    
    def store_grant(self, grant_data):
        try:
            result = self.grants.insert_one(grant_data)
            return str(result.inserted_id)
        except Exception as e:
            logging.error(f'Failed to store grant: {str(e)}')
            return None
    
    def store_grants(self, grants_data):
        try:
            if not grants_data:
                return []
            result = self.grants.insert_many(grants_data)
            return [str(id) for id in result.inserted_ids]
        except Exception as e:
            logging.error(f'Failed to store grants: {str(e)}')
            return []
    
    def get_grants(self, filters=None, sort_by=None, limit=None):
        try:
            query = filters if filters else {}
            cursor = self.grants.find(query)
            
            if sort_by:
                cursor = cursor.sort(sort_by)
            if limit:
                cursor = cursor.limit(limit)
                
            return list(cursor)
        except Exception as e:
            logging.error(f'Failed to get grants: {str(e)}')
            return []
    
    def store_priorities(self, user_id, priorities):
        try:
            result = self.priorities.update_one(
                {'user_id': user_id},
                {'$set': {'priorities': priorities, 'updated_at': datetime.utcnow()}},
                upsert=True
            )
            return True
        except Exception as e:
            logging.error(f'Failed to store priorities: {str(e)}')
            return False
    
    def get_priorities(self, user_id):
        try:
            doc = self.priorities.find_one({'user_id': user_id})
            return doc.get('priorities', []) if doc else []
        except Exception as e:
            logging.error(f'Failed to get priorities: {str(e)}')
            return []
    
    def store_source(self, source_data):
        try:
            result = self.sources.insert_one(source_data)
            return str(result.inserted_id)
        except Exception as e:
            logging.error(f'Failed to store source: {str(e)}')
            return None
    
    def get_sources_by_domain(self, domain=None):
        try:
            query = {'domain': domain} if domain else {}
            return list(self.sources.find(query))
        except Exception as e:
            logging.error(f'Failed to get sources: {str(e)}')
            return []
    
    def get_search_history(self, user_id, limit=10):
        try:
            return list(self.search_history.find(
                {'user_id': user_id}
            ).sort('timestamp', DESCENDING).limit(limit))
        except Exception as e:
            logging.error(f'Failed to get search history: {str(e)}')
            return []
    
    def save_user_settings(self, user_id, settings):
        try:
            settings['updated_at'] = datetime.utcnow()
            result = self.user_settings.update_one(
                {'user_id': user_id},
                {'$set': settings},
                upsert=True
            )
            return True
        except Exception as e:
            logging.error(f'Failed to save user settings: {str(e)}')
            return False
    
    def get_user_settings(self, user_id):
        try:
            settings = self.user_settings.find_one({'user_id': user_id})
            if not settings:
                return {
                    'user_id': user_id,
                    'email_notifications': True,
                    'sms_notifications': False,
                    'telegram_notifications': False,
                    'alert_threshold': 0.8,
                    'search_schedule': 'weekly'
                }
            return settings
        except Exception as e:
            logging.error(f'Failed to get user settings: {str(e)}')
            return None
    
    def record_alert_sent(self, user_id, grant_id, channel):
        try:
            alert_data = {
                'user_id': user_id,
                'grant_id': grant_id,
                'channel': channel,
                'timestamp': datetime.utcnow()
            }
            self.alert_history.insert_one(alert_data)
            return True
        except Exception as e:
            logging.error(f'Failed to record alert: {str(e)}')
            return False
    
    def check_alert_sent(self, user_id, grant_id):
        try:
            return self.alert_history.find_one({
                'user_id': user_id,
                'grant_id': grant_id
            }) is not None
        except Exception as e:
            logging.error(f'Failed to check alert: {str(e)}')
            return False
    
    def get_alert_history_for_user(self, user_id, limit=50):
        try:
            pipeline = [
                {'$match': {'user_id': user_id}},
                {'$lookup': {
                    'from': 'grants',
                    'localField': 'grant_id',
                    'foreignField': '_id',
                    'as': 'grant_details'
                }},
                {'$unwind': '$grant_details'},
                {'$sort': {'timestamp': -1}},
                {'$limit': limit}
            ]
            return list(self.alert_history.aggregate(pipeline))
        except Exception as e:
            logging.error(f'Failed to get alert history: {str(e)}')
            return []
    
    def save_grant_for_user(self, user_id, grant_id):
        try:
            saved_grant = {
                'user_id': user_id,
                'grant_id': ObjectId(grant_id),
                'saved_at': datetime.utcnow()
            }
            result = self.saved_grants.update_one(
                {'user_id': user_id, 'grant_id': ObjectId(grant_id)},
                {'$set': saved_grant},
                upsert=True
            )
            return True
        except Exception as e:
            logging.error(f'Failed to save grant: {str(e)}')
            return False
    
    def remove_saved_grant(self, user_id, grant_id):
        try:
            result = self.saved_grants.delete_one({
                'user_id': user_id,
                'grant_id': ObjectId(grant_id)
            })
            return result.deleted_count > 0
        except Exception as e:
            logging.error(f'Failed to remove saved grant: {str(e)}')
            return False
    
    def get_saved_grants(self, user_id):
        try:
            pipeline = [
                {'$match': {'user_id': user_id}},
                {'$lookup': {
                    'from': 'grants',
                    'localField': 'grant_id',
                    'foreignField': '_id',
                    'as': 'grant_details'
                }},
                {'$unwind': '$grant_details'},
                {'$sort': {'saved_at': -1}}
            ]
            return list(self.saved_grants.aggregate(pipeline))
        except Exception as e:
            logging.error(f'Failed to get saved grants: {str(e)}')
            return []
