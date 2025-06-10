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
    category: Optional[str] = None # This might be refined or replaced by sector/sub-sector
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    # score: Optional[float] = None # This will be part of Analysis or a more complex scoring object

# Research and scoring models
class ResearchContextScores(BaseModel):
    """Scores from research analysis"""
    sector_relevance: Optional[float] = None
    geographic_relevance: Optional[float] = None
    operational_alignment: Optional[float] = None

class ComplianceScores(BaseModel):
    """Scores from compliance analysis"""
    business_logic_alignment: Optional[float] = None
    feasibility_score: Optional[float] = None
    strategic_synergy: Optional[float] = None
    final_weighted_score: Optional[float] = None # Added field

class GrantSourceDetails(BaseModel):
    """Source information for grants"""
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    retrieved_at: Optional[datetime] = None

# New EnrichedGrant Model
class EnrichedGrant(Grant):
    """
    Extends the basic Grant model with enriched information from various analysis phases.
    """
    # External identifier and additional descriptive fields
    grant_id_external: Optional[str] = None
    summary_llm: Optional[str] = None
    eligibility_summary_llm: Optional[str] = None
    funder_name: Optional[str] = None
    
    # Funding details
    funding_amount_min: Optional[float] = None
    funding_amount_max: Optional[float] = None
    funding_amount_exact: Optional[float] = None
    funding_amount_display: Optional[str] = None
    
    # Date fields
    deadline_date: Optional[datetime] = None
    application_open_date: Optional[datetime] = None
    
    # Keywords and categories
    keywords: List[str] = Field(default_factory=list)
    categories_project: List[str] = Field(default_factory=list)
    
    # Source details
    source_details: Optional[GrantSourceDetails] = None
    
    # Contextual Layers
    identified_sector: Optional[str] = None
    identified_sub_sector: Optional[str] = None
    geographic_scope: Optional[str] = None # e.g., "National, USA", "State, CA", "City, Anytown"
    specific_location_mentions: List[str] = Field(default_factory=list)

    # Scoring systems
    research_scores: Optional[ResearchContextScores] = None
    compliance_scores: Optional[ComplianceScores] = None
    overall_composite_score: Optional[float] = None
    
    # Compliance and Feasibility
    compliance_summary: Optional[Dict[str, Any]] = None # Store results from ComplianceAnalysisAgent
    feasibility_score: Optional[float] = None # 0.0 to 1.0
    risk_assessment: Optional[Dict[str, Any]] = None # e.g., {"financial": "Low", "legal": "Medium"}

    # Additional metadata
    raw_source_data: Optional[Dict[str, Any]] = None # Original data from Perplexity or other sources
    enrichment_log: List[str] = Field(default_factory=list) # Log of enrichment steps
    last_enriched_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Grant lifecycle tracking
    record_status: Optional[str] = None # Maps to grants.status column (ACTIVE, EXPIRED, DRAFT, ARCHIVED)
      # For linking with ApplicationHistory
    application_status: Optional[str] = None # e.g., "Not Applied", "Applied", "Successful", "Rejected"
    application_history_id: Optional[int] = None # Foreign key to ApplicationHistory table

    class Config:
        from_attributes = True # For SQLAlchemy compatibility if needed directly
        # Ensure Pydantic V2 features like Field are used if on V2, otherwise adjust for V1.
        # If using Pydantic V1, `default_factory` is correct. For V2, just `default=[]` for lists.

# User Profile model (as used by ResearchAgent)
class UserProfile(BaseModel):
    user_id: str
    focus_areas: List[str] = Field(default_factory=list)
    expertise: List[str] = Field(default_factory=list)
    # Add other fields that might be relevant from kevin_profile_config or user interactions
    # For example:
    # project_constraints: Optional[Dict[str, Any]] = None
    # strategic_goals: List[str] = Field(default_factory=list)

# Configuration Models (as used by ResearchAgent)
class GrantSource(BaseModel):
    source_id: str
    name: str
    base_url: str
    description: Optional[str] = None
    trust_level: int = Field(default=0, ge=0, le=5) # 0-5 scale for trust
    search_parameters: Optional[Dict[str, Any]] = None # e.g., API keys, specific query params
    is_active: bool = True

class KeywordConfig(BaseModel):
    keyword: str
    priority: Optional[str] = None # e.g., High, Medium, Low
    weight: float = Field(default=1.0)

class SectorConfig(BaseModel):
    priority_keywords: List[KeywordConfig] = Field(default_factory=list)
    secondary_keywords: List[KeywordConfig] = Field(default_factory=list)
    exclusion_keywords: List[str] = Field(default_factory=list)
    priority_weight: float = Field(default=0.7, ge=0, le=1) # Weight for priority vs secondary
    default_relevance_score: float = Field(default=0.1, ge=0, le=1)
    # llm_assessment_enabled: bool = False # Future: toggle for LLM-based scoring

class GeographicConfig(BaseModel):
    priority_keywords: List[KeywordConfig] = Field(default_factory=list)
    secondary_keywords: List[KeywordConfig] = Field(default_factory=list)
    exclusion_keywords: List[str] = Field(default_factory=list) # e.g., "international" if focus is local
    priority_weight: float = Field(default=0.6, ge=0, le=1)
    national_scope_boost: float = Field(default=0.1, ge=0, le=0.5) # Bonus for "national" scope grants
    default_relevance_score: float = Field(default=0.1, ge=0, le=1)

class ProjectConstraints(BaseModel):
    min_funding: Optional[float] = None
    max_funding: Optional[float] = None
    exclude_sectors: List[str] = Field(default_factory=list)
    required_keywords_in_grant: List[str] = Field(default_factory=list)
    negative_keywords_in_grant: List[str] = Field(default_factory=list) # Penalize if these appear

class KevinProfileConfig(BaseModel): # Represents the user\'s (Kevin\'s) preferences
    focus_areas_keywords: List[str] = Field(default_factory=list)
    expertise_keywords: List[str] = Field(default_factory=list)
    strategic_goals_keywords: List[str] = Field(default_factory=list)
    project_constraints: Optional[ProjectConstraints] = None
    default_alignment_score: float = Field(default=0.05, ge=0, le=1)
    # Weights for different alignment aspects could be added here
    # e.g., focus_area_weight: float = 0.4

class GrantSearchFilters(BaseModel):
    min_score: Optional[float] = Field(None, alias="minScore") # Existing field for min_overall_score
    max_score: Optional[float] = Field(None, alias="maxScore") # New field for max_overall_score
    category: Optional[str] = None
    deadline_before: Optional[str] = Field(None, alias="deadlineBefore")
    search_text: Optional[str] = Field(None, alias="searchText")
    # Frontend sends min_overall_score and max_overall_score, ensure aliases match if needed
    # Or adjust frontend to send minScore and maxScore if that's preferred for backend consistency.
    # For now, adding max_score and assuming backend crud will handle mapping if frontend sends max_overall_score

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

# Specific response models using EnrichedGrant for clarity in API contracts
class SingleEnrichedGrantResponse(APIResponse[EnrichedGrant]):
    pass

class PaginatedEnrichedGrantResponse(PaginatedResponse[EnrichedGrant]):
    pass

# Schema for creating/updating ApplicationHistory
class ApplicationHistoryBase(BaseModel):
    grant_id: int
    submission_date: Optional[datetime] = None
    status: str # Corresponds to ApplicationStatus enum in models.py
    outcome_notes: Optional[str] = None
    feedback_for_profile_update: Optional[str] = None

class ApplicationHistoryCreate(ApplicationHistoryBase):
    pass

class ApplicationHistoryResponse(ApplicationHistoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
