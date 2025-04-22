"""
API routes for the Grant Finder.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, Query, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import necessary database models and clients
from database.mongodb_client import MongoDBClient
from service_registry import services  # Avoid circular import

# Setup logging
logger = logging.getLogger(__name__)

# FastAPI app instance (if defining routes in a separate module, use APIRouter)
# from fastapi import APIRouter
# api_router = APIRouter()
# Using the existing 'api' instance defined in api/__init__.py or routes.py
# Assuming api = FastAPI() or APIRouter() is defined elsewhere and imported
# For this example, let's assume 'api' is an APIRouter instance.
from fastapi import APIRouter
api = APIRouter()

# --- Pydantic Models --- 
class GrantBase(BaseModel):
    title: str
    source: str
    category: str
    deadline: datetime
    relevance_score: float
    funding_amount: Optional[str] = None
    description: Optional[str] = None
    source_url: str

class GrantOut(GrantBase):
    id: str

class UserSettings(BaseModel):
    notifications: Dict[str, Any]
    relevance_threshold: float
    deadline_threshold: int
    schedule_frequency: str
    schedule_days: List[str]
    schedule_time: str
    saved_grant_ids: Optional[List[str]] = []

# --- Dependency Injection --- 
def get_db() -> MongoDBClient:
    """Dependency function to get the MongoDB client instance."""
    db_client = services.get("mongodb_client")
    if db_client is None:
        logger.error("MongoDB client not initialized or unavailable.")
        raise HTTPException(status_code=503, detail="Database service unavailable")
    return db_client

# Add dependencies for other services if needed
# def get_research_agent(): ...
# def get_analysis_agent(): ...

# --- API Endpoints --- 

@api.get("/grants", response_model=List[GrantOut], tags=["Grants"])
async def get_grants(
    min_score: Optional[float] = None,
    days_to_deadline: Optional[int] = None,
    category: Optional[str] = None,
    search_text: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: MongoDBClient = Depends(get_db)
):
    """Get grants based on filtering criteria."""
    try:
        # Ensure category is handled correctly (e.g., list or string)
        cat_filter = category.split(',') if category else None
        grants = db.get_grants(min_score, days_to_deadline, cat_filter, search_text, limit)
        return grants
    except Exception as e:
        logger.error(f"Error fetching grants: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error fetching grants")

@api.get("/grants/{grant_id}", response_model=GrantOut, tags=["Grants"])
async def get_grant_by_id(grant_id: str, db: MongoDBClient = Depends(get_db)):
    """Get a specific grant by ID."""
    try:
        # TODO: Ensure get_grant_by_id is implemented in MongoDBClient
        grant = db.get_grant_by_id(grant_id) 
        if not grant:
            raise HTTPException(status_code=404, detail="Grant not found")
        return grant
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching grant {grant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error fetching grant")

@api.get("/grants/search", response_model=List[GrantOut], tags=["Grants"])
async def search_grants(
    query: str,
    limit: int = Query(20, ge=1, le=100),
    db: MongoDBClient = Depends(get_db)
):
    """Search grants by query text."""
    try:
        # TODO: Ensure search_grants is implemented in MongoDBClient and handles text search
        grants = db.search_grants(query, limit)
        return grants
    except NotImplementedError:
         raise HTTPException(status_code=501, detail="Text search not implemented")
    except Exception as e:
        logger.error(f"Error searching grants for query '{query}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during search")

@api.get("/user/settings", response_model=UserSettings, tags=["User Settings"])
async def get_user_settings(user_id: str = "default_user", db: MongoDBClient = Depends(get_db)):
    """Get user settings."""
    try:
        settings = db.get_user_settings(user_id)
        if not settings:
             # Return default settings if none found? Or 404?
             # Let's assume get_user_settings returns defaults
             logger.warning(f"No settings found for user {user_id}, returning defaults.")
             # settings = create_default_settings(user_id) # Need default logic
        return settings
    except Exception as e:
        logger.error(f"Error fetching user settings for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error fetching settings")

@api.put("/user/settings", response_model=UserSettings, tags=["User Settings"])
async def update_user_settings(
    settings: UserSettings,
    user_id: str = "default_user",
    db: MongoDBClient = Depends(get_db)
):
    """Update user settings."""
    try:
        # Pydantic automatically validates the input `settings` against the UserSettings model
        success = db.save_user_settings(settings.dict(), user_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save settings")
        # Fetch the updated settings to return them
        updated_settings = db.get_user_settings(user_id)
        return updated_settings
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user settings for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error updating settings")

@api.get("/user/saved-grants", response_model=List[GrantOut], tags=["Saved Grants"])
async def get_saved_grants(user_id: str = "default_user", db: MongoDBClient = Depends(get_db)):
    """Get grants saved by the user."""
    try:
        grants = db.get_saved_grants_for_user(user_id)
        return grants
    except Exception as e:
        logger.error(f"Error fetching saved grants for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error fetching saved grants")

@api.post("/user/saved-grants/{grant_id}", status_code=201, tags=["Saved Grants"])
async def save_grant(
    grant_id: str,
    user_id: str = "default_user",
    db: MongoDBClient = Depends(get_db)
):
    """Save a grant for the user."""
    try:
        success = db.save_grant_for_user(user_id, grant_id)
        if not success:
            # Might be duplicate or DB error
            # Check if already saved? Client should ideally handle this state.
             logger.warning(f"Failed to save grant {grant_id} for user {user_id}. Might already exist or DB error.")
             raise HTTPException(status_code=400, detail="Failed to save grant. It might already be saved.")
        return {"message": "Grant saved successfully"}
    except HTTPException: # Re-raise specific HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error saving grant {grant_id} for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error saving grant")

@api.delete("/user/saved-grants/{grant_id}", status_code=200, tags=["Saved Grants"])
async def unsave_grant(
    grant_id: str,
    user_id: str = "default_user",
    db: MongoDBClient = Depends(get_db)
):
    """Remove a grant from user's saved list."""
    try:
        success = db.remove_saved_grant_for_user(user_id, grant_id)
        if not success:
             # Check if it actually existed
             logger.warning(f"Failed to remove grant {grant_id} for user {user_id}. Might not exist or DB error.")
             # Returning 200 anyway as the state is achieved (grant is not saved)
             # Alternatively, return 404 if strict about existence.
        return {"message": "Grant removed from saved list (or was not saved)"}
    except Exception as e:
        logger.error(f"Error removing saved grant {grant_id} for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error removing grant")

@api.get("/dashboard/stats", tags=["Dashboard"])
async def get_dashboard_stats(db: MongoDBClient = Depends(get_db)):
    """Get statistics for the dashboard."""
    try:
        # TODO: Implement calculation methods properly in MongoDBClient
        total_grants = db.count_documents() # Example: Use count_documents for total
        high_priority = db.count_documents({"relevance_score": {"$gte": 85}})
        deadline_soon_date = datetime.now() + timedelta(days=7)
        deadline_soon = db.count_documents({"deadline": {"$lte": deadline_soon_date, "$gte": datetime.now()}})
        
        # TODO: Implement these methods in MongoDBClient
        total_funding = db.calculate_total_funding() if hasattr(db, 'calculate_total_funding') else "N/A" 
        avg_score = db.calculate_average_score() if hasattr(db, 'calculate_average_score') else 0.0
        
        saved_grants = 0 # Requires user context, maybe fetch settings?
        user_settings = db.get_user_settings("default_user") # Example fetch
        if user_settings:
             saved_grants = len(user_settings.get('saved_grant_ids', []))
        
        return {
            "totalGrants": total_grants,
            "highPriorityCount": high_priority,
            "deadlineSoonCount": deadline_soon,
            "savedGrantsCount": saved_grants, 
            "totalFunding": total_funding,
            "averageRelevanceScore": round(avg_score, 1)
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error fetching dashboard stats")

@api.get("/system/status", tags=["System"])
async def get_system_status():
    """Get the status of system services."""
    # Access globally initialized status
    from Home import init_status 
    
    service_status = {
        "mongodb": init_status.get('mongo', False),
        "pinecone": init_status.get('pinecone', False),
        "agentql": init_status.get('agentql', False),
        "perplexity": init_status.get('perplexity', False),
        # Add other relevant services if needed
    }
    
    overall_status = "healthy" if all(service_status.values()) else "degraded"
    if not service_status["mongodb"]:
        overall_status = "unavailable"
        
    return {
        "services": service_status,
        "status": overall_status,
        "version": "1.0.0" # Consider reading from a config file or env var
    }

@api.post("/notifications/test", tags=["Notifications"])
async def test_notification(
    payload: Dict[str, str] = Body(...), # Expect {"channel": "telegram" or "sms"}
    db: MongoDBClient = Depends(get_db)
):
    """Send a test notification to the specified channel."""
    channel = payload.get("channel")
    user_id = "default_user" # Hardcoded for now
    if not channel or channel not in ["telegram", "sms"]:
        raise HTTPException(status_code=400, detail="Invalid or missing 'channel' in request body. Use 'telegram' or 'sms'.")
        
    notifier = services.get("notification_manager")
    if not notifier:
         raise HTTPException(status_code=503, detail="Notification service unavailable")
         
    try:
        settings = db.get_user_settings(user_id)
        test_message = f"This is a test notification from Smart Grant Finder via {channel.upper()}."
 
        # Check if channel enabled in settings (add this logic to get_user_settings or here)
        # if channel == "telegram" and not settings...:
        #     raise HTTPException(status_code=400, ...)
        
        success = False
        if channel == "telegram":
            success = notifier.send_telegram_sync(test_message)
        elif channel == "sms":
            # Ensure user phone number is available in settings
            # phone_number = settings.get('notifications', {}).get('sms_number')
            # if not phone_number: raise HTTPException(...) 
            success = notifier.send_sms(test_message) # Assumes send_sms uses configured default number
            
        if not success:
             raise HTTPException(status_code=500, detail=f"Failed to send test notification via {channel}")
             
        return {"message": f"Test notification sent successfully via {channel}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test notification via {channel}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error sending test notification")