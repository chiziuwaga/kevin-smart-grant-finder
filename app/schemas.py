from typing import Dict, List, Optional, Union, Any, Generic, TypeVar
from typing_extensions import TypedDict
from datetime import datetime
from pydantic import BaseModel, Field

T = TypeVar('T')

# TypedDicts for distribution items
class CategoryDistributionItem(TypedDict):
    name: str
    value: int

class DeadlineDistributionItem(TypedDict):
    name: str # e.g., "2023-01" (Year-Month) or a specific date string
    count: int

class ScoreDistributionItem(TypedDict):
    name: str # e.g., "70-80"
    count: int

# Grant models
class Grant(BaseModel):
    id: str
    title: str
    description: str
    funding_amount: Optional[float] = None
    deadline: Optional[datetime] = None
    eligibility_criteria: Optional[str] = None
    category: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    score: Optional[float] = None

class GrantSearchFilters(BaseModel):
    min_score: Optional[float] = Field(None, alias="minScore")
    category: Optional[str] = None
    deadline_before: Optional[str] = Field(None, alias="deadlineBefore")
    search_text: Optional[str] = Field(None, alias="searchText")

    class Config:
        populate_by_name = True

# Dashboard models
class DashboardStats(BaseModel):
    total_grants: int = Field(..., alias="totalGrants")
    average_score: float = Field(..., alias="averageScore")
    grants_this_month: int = Field(..., alias="grantsThisMonth")
    upcoming_deadlines: int = Field(..., alias="upcomingDeadlines")

    class Config:
        populate_by_name = True

class DistributionData(BaseModel):
    categories: List[CategoryDistributionItem]
    deadlines: List[DeadlineDistributionItem]
    scores: List[ScoreDistributionItem]

# User settings models
class UserSettings(BaseModel):
    telegram_enabled: bool = Field(..., alias="telegramEnabled")
    email_notifications: bool = Field(..., alias="emailNotifications")
    deadline_reminders: bool = Field(..., alias="deadlineReminders")
    search_frequency: str = Field(..., alias="searchFrequency")
    categories: List[str]
    minimum_score: float = Field(..., alias="minimumScore")

    class Config:
        populate_by_name = True

# API response models
class APIResponse(BaseModel, Generic[T]):
    status: str = "success"
    message: Optional[str] = None
    data: Optional[T] = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")

    class Config:
        populate_by_name = True
