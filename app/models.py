from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class GrantFilter(BaseModel):
    """Model for grant search filters"""
    min_score: float = Field(0.0, description="Minimum relevance score")
    categories: List[str] = Field(default_factory=list, description="List of grant categories")
    keywords: str = Field("", description="Search keywords")
    deadline_before: Optional[datetime] = Field(None, description="Filter by deadline before this date")
    deadline_after: Optional[datetime] = Field(None, description="Filter by deadline after this date")
    min_funding: Optional[float] = Field(None, description="Minimum funding amount")
    max_funding: Optional[float] = Field(None, description="Maximum funding amount")
    geographic_focus: Optional[str] = Field(None, description="Geographic focus for the grant")
    sites_to_focus: Optional[List[str]] = Field(None, description="List of sites to focus on")

class Grant(BaseModel):
    """Model for grant data"""
    id: str = Field(..., description="Unique identifier")
    title: str = Field(..., description="Grant title")
    description: str = Field(..., description="Grant description")
    category: str = Field(..., description="Grant category")
    funding_amount: Optional[str] = Field(None, description="Available funding")
    deadline: Optional[datetime] = Field(None, description="Application deadline")
    score: float = Field(0.0, description="Relevance score")
    source_url: Optional[str] = Field(None, description="Source URL")
    eligibility: Optional[Dict[str, Any]] = Field(None, description="Eligibility requirements")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class SearchRun(BaseModel):
    """Model for search execution metadata"""
    timestamp: datetime = Field(default_factory=datetime.now)
    grants_found: int = Field(..., description="Total grants found")
    high_priority: int = Field(..., description="Number of high-priority grants")
    filters_used: Optional[GrantFilter] = Field(None, description="Search filters used")

class UserSettings(BaseModel):
    """Model for user notification and search settings"""
    email_notifications: bool = Field(True, description="Whether email notifications are enabled")
    minimum_score: float = Field(0.7, description="Minimum score for notifications")
    notify_categories: List[str] = Field(default_factory=list, description="Categories to notify about")
    schedule_cron: str = Field("0 10 * * 1,4", description="Cron schedule for searches")