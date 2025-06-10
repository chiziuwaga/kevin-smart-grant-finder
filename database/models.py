"""
Database models for the application.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import List

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class GrantStatus(str, PyEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DRAFT = "draft"
    ARCHIVED = "archived"

class SearchFrequency(str, PyEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    TWICE_WEEKLY = "twice_weekly"
    MONTHLY = "monthly"

class Grant(Base):
    __tablename__ = 'grants'

    id = Column(Integer, primary_key=True) # Keep as Integer for now, consider UUID later if needed
    title = Column(String, nullable=False, index=True)
    description = Column(String) # Consider TEXT type for longer descriptions if DB supports easily
    funding_amount = Column(Float)
    deadline = Column(DateTime, index=True)
    # source = Column(String) # Replaced by source_name and source_url
    source_name = Column(String) # e.g., "Grants.gov", "Ford Foundation"
    source_url = Column(String) # Direct link to the grant page
    # category = Column(String, index=True) # To be replaced by more granular sector/sub-sector if used
    
    # New fields for enriched data - these align with EnrichedGrant Pydantic model
    identified_sector = Column(String, index=True, nullable=True)
    identified_sub_sector = Column(String, index=True, nullable=True)
    geographic_scope = Column(String, nullable=True) # e.g., "National, USA", "State, CA"
    specific_location_mentions = Column(JSON, nullable=True) # List of strings    # Raw source data from Perplexity or other APIs
    raw_source_data = Column(JSON, nullable=True)
    enrichment_log = Column(JSON, nullable=True) # List of strings logging enrichment steps
    last_enriched_at = Column(DateTime, nullable=True)

    # Overall composite score for this grant (calculated from analysis)
    overall_composite_score = Column(Float, nullable=True, index=True)

    # status = Column(Enum(GrantStatus), default=GrantStatus.ACTIVE, index=True) # Retain or revise based on new workflow
    # eligibility = Column(JSON) # Replaced by more structured compliance/feasibility in Analysis

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    analyses = relationship("Analysis", back_populates="grant", cascade="all, delete-orphan")
    saved_by = relationship("UserSettings", secondary="saved_grants", back_populates="saved_grants")
    # Relationship to ApplicationHistory
    application_history = relationship("ApplicationHistory", back_populates="grant", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = 'analyses'

    id = Column(Integer, primary_key=True)
    grant_id = Column(Integer, ForeignKey('grants.id', ondelete='CASCADE'), nullable=False)
    
    # Original score might be the final_score from AnalysisAgent
    final_score = Column(Float, index=True, nullable=True) # Renamed from 'score' for clarity
    
    # Detailed scores from different agents/dimensions
    relevance_score = Column(Float, nullable=True) # From ResearchAgent or initial assessment
    compliance_score = Column(Float, nullable=True) # From ComplianceAnalysisAgent
    feasibility_score = Column(Float, nullable=True) # From combined analysis
    # Add other specific score dimensions as needed, e.g., strategic_alignment_score

    # Store detailed analysis components as JSON
    # This allows flexibility without altering schema for every new analysis detail
    relevance_details = Column(JSON, nullable=True) # e.g., keyword matches, sector alignment
    compliance_details = Column(JSON, nullable=True) # e.g., list of met/unmet compliance rules, risk assessment
    feasibility_details = Column(JSON, nullable=True) # e.g., notes on operational capacity, budget fit

    # notes = Column(String) # Can be part of feasibility_details or a general summary
    overall_summary = Column(String, nullable=True) # A human-readable summary of the analysis

    analysis_date = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    grant = relationship("Grant", back_populates="analyses")

# New ApplicationHistory Table
class ApplicationStatus(str, PyEnum):
    NOT_APPLIED = "Not Applied"
    DRAFTING = "Drafting"
    APPLIED = "Applied"
    UNDER_REVIEW = "Under Review"
    AWARDED = "Awarded"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"

class ApplicationHistory(Base):
    __tablename__ = 'application_history'

    id = Column(Integer, primary_key=True)
    grant_id = Column(Integer, ForeignKey('grants.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String, index=True, nullable=False) # Link to Kevin's profile (e.g., "kevin_default")
    
    application_date = Column(DateTime, nullable=True)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.NOT_APPLIED, nullable=False)
    status_reason = Column(String, nullable=True) # e.g., reason for rejection or withdrawal
    award_amount = Column(Float, nullable=True)
    feedback_notes = Column(String, nullable=True) # Feedback received from funder or internal notes
    
    # For recursive correction mechanism
    is_successful_outcome = Column(Boolean, nullable=True) # True if Awarded, False if Rejected, Null otherwise

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    grant = relationship("Grant", back_populates="application_history")


class UserSettings(Base):
    __tablename__ = 'user_settings'

    id = Column(Integer, primary_key=True)
    telegram_enabled = Column(Boolean, default=True)
    minimum_score = Column(Float, default=0.7)
    notify_categories = Column(JSON, default=list)
    schedule_frequency = Column(Enum(SearchFrequency), default=SearchFrequency.WEEKLY)
    schedule_days = Column(JSON, default=list)  # List of days for scheduling
    schedule_time = Column(String, default="10:00")  # Time in HH:MM format
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    saved_grants = relationship("Grant", secondary="saved_grants", back_populates="saved_by")

    def to_dict(self):
        """Convert UserSettings model to dictionary format for API responses"""
        return {
            "telegramEnabled": self.telegram_enabled,
            "emailNotifications": True,  # Default value since not in DB model
            "deadlineReminders": True,   # Default value since not in DB model
            "searchFrequency": self.schedule_frequency.value if self.schedule_frequency else "weekly",
            "categories": self.notify_categories or [],
            "minimumScore": self.minimum_score or 0.7
        }

class SavedGrants(Base):
    __tablename__ = 'saved_grants'

    user_settings_id = Column(Integer, ForeignKey('user_settings.id', ondelete='CASCADE'), primary_key=True)
    grant_id = Column(Integer, ForeignKey('grants.id', ondelete='CASCADE'), primary_key=True)
    saved_at = Column(DateTime, server_default=func.now())

class SearchRun(Base):
    __tablename__ = 'search_runs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, server_default=func.now())
    grants_found = Column(Integer)
    high_priority = Column(Integer)
    search_filters = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())