"""
Database models for the application.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, JSON, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
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

    id = Column(Integer, primary_key=True)
    
    # Basic grant information
    title = Column(String, nullable=False, index=True)
    description = Column(String)
    
    # External identifier and additional descriptive fields
    grant_id_external = Column(String, nullable=True, index=True)
    summary_llm = Column(String, nullable=True)
    eligibility_summary_llm = Column(String, nullable=True)
    funder_name = Column(String, nullable=True)
    
    # Funding details
    funding_amount = Column(Float)  # Legacy field
    funding_amount_min = Column(Float, nullable=True)
    funding_amount_max = Column(Float, nullable=True)
    funding_amount_exact = Column(Float, nullable=True)
    funding_amount_display = Column(String, nullable=True)
    
    # Date fields
    deadline = Column(DateTime, index=True)  # Legacy field
    deadline_date = Column(DateTime, nullable=True)
    application_open_date = Column(DateTime, nullable=True)
    
    # Keywords and categories as JSON
    keywords_json = Column(JSON, nullable=True)
    categories_project_json = Column(JSON, nullable=True)
    
    # Source information
    source_name = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    retrieved_at = Column(DateTime, nullable=True)
    
    # Contextual layers
    identified_sector = Column(String, index=True, nullable=True)
    identified_sub_sector = Column(String, index=True, nullable=True)
    geographic_scope = Column(String, nullable=True)
    specific_location_mentions_json = Column(JSON, nullable=True)

    # Scoring systems (individual scores)
    sector_relevance_score = Column(Float, nullable=True)
    geographic_relevance_score = Column(Float, nullable=True)
    operational_alignment_score = Column(Float, nullable=True)
    business_logic_alignment_score = Column(Float, nullable=True)
    feasibility_context_score = Column(Float, nullable=True)
    strategic_synergy_score = Column(Float, nullable=True)
    overall_composite_score = Column(Float, nullable=True, index=True)
    
    # Compliance and feasibility
    compliance_summary_json = Column(JSON, nullable=True)
    feasibility_score = Column(Float, nullable=True)
    risk_assessment_json = Column(JSON, nullable=True)

    # Additional metadata
    raw_source_data_json = Column(JSON, nullable=True)
    enrichment_log_json = Column(JSON, nullable=True)
    last_enriched_at = Column(DateTime, nullable=True)
    
    # Grant lifecycle tracking
    record_status = Column(String, nullable=True, default="ACTIVE")

    # Timestamps
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

class SearchRunType(str, PyEnum):
    AUTOMATED = "automated"
    MANUAL = "manual"
    SCHEDULED = "scheduled"

class SearchRunStatus(str, PyEnum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    IN_PROGRESS = "in_progress"

class SearchRun(Base):
    __tablename__ = 'search_runs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, server_default=func.now())
    grants_found = Column(Integer, default=0)
    high_priority = Column(Integer, default=0)
    search_filters = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    
    # Enhanced fields for better tracking
    run_type = Column(Enum(SearchRunType), default=SearchRunType.MANUAL)
    status = Column(Enum(SearchRunStatus), default=SearchRunStatus.SUCCESS)
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    search_query = Column(String, nullable=True)
    user_triggered = Column(Boolean, default=False)
    
    # Performance metrics
    sources_searched = Column(Integer, default=0)
    api_calls_made = Column(Integer, default=0)
    processing_time_ms = Column(Integer, nullable=True)