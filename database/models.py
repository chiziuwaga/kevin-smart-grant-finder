"""
Database models for the application.
Multi-user support with Auth0 authentication, Stripe subscriptions, and AI application generation.
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

class SubscriptionStatus(str, PyEnum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    UNPAID = "unpaid"

class ApplicationGenerationStatus(str, PyEnum):
    DRAFT = "draft"
    GENERATED = "generated"
    EDITED = "edited"
    SUBMITTED = "submitted"
    AWARDED = "awarded"
    REJECTED = "rejected"


# ============================================================================
# USER & AUTHENTICATION MODELS
# ============================================================================

class User(Base):
    """User account with email/password JWT authentication and subscription management."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    auth0_id = Column(String, unique=True, nullable=True, index=True)  # Legacy compat
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    company_name = Column(String, nullable=True)

    # Subscription tier and status
    subscription_tier = Column(String, default="free")  # free, basic, pro
    subscription_status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.INCOMPLETE)

    # Usage tracking (monthly counters)
    searches_used = Column(Integer, default=0)
    applications_used = Column(Integer, default=0)
    searches_limit = Column(Integer, default=50)
    applications_limit = Column(Integer, default=20)

    # Usage period tracking
    usage_period_start = Column(DateTime, default=func.now())
    usage_period_end = Column(DateTime, nullable=True)

    # Account status
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    # Cost tracking
    monthly_ai_cost_cents = Column(Integer, default=0)  # Track AI costs in cents
    last_cost_reset = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)

    # Relationships
    business_profile = relationship("BusinessProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    grants = relationship("Grant", back_populates="user", cascade="all, delete-orphan")
    generated_applications = relationship("GeneratedApplication", back_populates="user", cascade="all, delete-orphan")
    search_runs = relationship("SearchRun", back_populates="user", cascade="all, delete-orphan")
    user_settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        """Convert User model to dictionary for API responses."""
        return {
            "id": self.id,
            "email": self.email,
            "fullName": self.full_name,
            "companyName": self.company_name,
            "subscriptionTier": self.subscription_tier,
            "subscriptionStatus": self.subscription_status.value if self.subscription_status is not None else None,
            "searchesUsed": self.searches_used,
            "applicationsUsed": self.applications_used,
            "searchesLimit": self.searches_limit,
            "applicationsLimit": self.applications_limit,
            "isActive": self.is_active,
            "createdAt": self.created_at.isoformat() if self.created_at is not None else None,
            "lastLogin": self.last_login.isoformat() if self.last_login else None,
        }


class BusinessProfile(Base):
    """User's business profile for RAG-based grant application generation."""
    __tablename__ = 'business_profiles'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)

    # Basic business information
    business_name = Column(String, nullable=False)
    mission_statement = Column(Text, nullable=True)
    service_description = Column(Text, nullable=True)
    website_url = Column(String, nullable=True)  # Business website URL

    # Business details
    target_sectors = Column(JSON, nullable=True)  # List of sectors
    revenue_range = Column(String, nullable=True)  # e.g., "100k-500k"
    years_in_operation = Column(Integer, nullable=True)
    geographic_focus = Column(String, nullable=True)
    team_size = Column(Integer, nullable=True)

    # Long-form narrative for RAG (2000 char limit enforced in application)
    narrative_text = Column(Text, nullable=True)  # Comprehensive business description

    # Document uploads (supporting documents for grant applications)
    uploaded_documents = Column(JSON, nullable=True)  # Array of {filename, url, size, uploaded_at}
    documents_total_size_bytes = Column(Integer, default=0)  # Track total size (10MB limit)

    # Vector embeddings reference
    vector_embeddings_id = Column(String, nullable=True)  # Pinecone namespace/ID
    embeddings_generated_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="business_profile")

    def to_dict(self):
        """Convert BusinessProfile to dictionary."""
        return {
            "id": self.id,
            "businessName": self.business_name,
            "missionStatement": self.mission_statement,
            "serviceDescription": self.service_description,
            "websiteUrl": self.website_url,
            "targetSectors": self.target_sectors if self.target_sectors is not None else [],
            "revenueRange": self.revenue_range,
            "yearsInOperation": self.years_in_operation,
            "geographicFocus": self.geographic_focus,
            "teamSize": self.team_size,
            "narrativeText": self.narrative_text,
            "uploadedDocuments": self.uploaded_documents if self.uploaded_documents is not None else [],
            "documentsTotalSize": self.documents_total_size_bytes or 0,
            "embeddingsGenerated": self.embeddings_generated_at is not None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at is not None else None,
        }


class Subscription(Base):
    """Stripe subscription management."""
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)

    # Stripe identifiers
    stripe_customer_id = Column(String, unique=True, nullable=True)
    stripe_subscription_id = Column(String, unique=True, nullable=True)

    # Plan details
    plan_name = Column(String, default="basic")  # basic, pro
    amount = Column(Integer, default=3500)  # Amount in cents ($35.00)
    currency = Column(String, default="usd")

    # Subscription status
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.INCOMPLETE)

    # Billing period
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)

    # Usage limits for this subscription
    searches_remaining = Column(Integer, default=50)
    applications_remaining = Column(Integer, default=20)

    # Subscription management
    auto_renew = Column(Boolean, default=True)
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="subscription")

    def to_dict(self):
        """Convert Subscription to dictionary."""
        return {
            "id": self.id,
            "planName": self.plan_name,
            "amount": self.amount / 100,  # Convert to dollars
            "currency": self.currency,
            "status": self.status.value if self.status is not None else None,
            "currentPeriodStart": self.current_period_start.isoformat() if self.current_period_start is not None else None,
            "currentPeriodEnd": self.current_period_end.isoformat() if self.current_period_end is not None else None,
            "searchesRemaining": self.searches_remaining,
            "applicationsRemaining": self.applications_remaining,
            "autoRenew": self.auto_renew,
            "cancelAtPeriodEnd": self.cancel_at_period_end,
        }


class GeneratedApplication(Base):
    """AI-generated grant applications using RAG."""
    __tablename__ = 'generated_applications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    grant_id = Column(Integer, ForeignKey('grants.id', ondelete='CASCADE'), nullable=False, index=True)

    # Application content
    generated_content = Column(Text, nullable=True)  # Full application text

    # Structured sections (JSON)
    sections = Column(JSON, nullable=True)  # {executive_summary, needs_statement, etc.}

    # Application metadata
    generation_date = Column(DateTime, server_default=func.now())
    last_edited = Column(DateTime, nullable=True)
    status = Column(Enum(ApplicationGenerationStatus), default=ApplicationGenerationStatus.DRAFT)

    # User feedback and notes
    feedback_notes = Column(Text, nullable=True)
    user_edits = Column(JSON, nullable=True)  # Track which sections were edited

    # Generation metadata
    model_used = Column(String, default="deepseek")  # AI model used
    generation_time_seconds = Column(Float, nullable=True)
    tokens_used = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="generated_applications")
    grant = relationship("Grant", back_populates="generated_applications")

    def to_dict(self):
        """Convert GeneratedApplication to dictionary."""
        return {
            "id": self.id,
            "grantId": self.grant_id,
            "generatedContent": self.generated_content,
            "sections": self.sections if self.sections is not None else {},
            "generationDate": self.generation_date.isoformat() if self.generation_date is not None else None,
            "lastEdited": self.last_edited.isoformat() if self.last_edited is not None else None,
            "status": self.status.value if self.status is not None else None,
            "feedbackNotes": self.feedback_notes,
            "modelUsed": self.model_used,
            "generationTime": self.generation_time_seconds,
        }


# ============================================================================
# GRANT MODELS (Updated for multi-user)
# ============================================================================

class Grant(Base):
    __tablename__ = 'grants'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)  # NULL for legacy grants

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

    # Relationships
    user = relationship("User", back_populates="grants")
    analyses = relationship("Analysis", back_populates="grant", cascade="all, delete-orphan")
    saved_by = relationship("UserSettings", secondary="saved_grants", back_populates="saved_grants")
    application_history = relationship("ApplicationHistory", back_populates="grant", cascade="all, delete-orphan")
    generated_applications = relationship("GeneratedApplication", back_populates="grant", cascade="all, delete-orphan")


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
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)  # Now FK to users table
    
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
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)

    # Notification preferences (Telegram removed, email added)
    email_notifications = Column(Boolean, default=True)
    deadline_reminders = Column(Boolean, default=True)

    minimum_score = Column(Float, default=0.7)
    notify_categories = Column(JSON, default=list)
    schedule_frequency = Column(Enum(SearchFrequency), default=SearchFrequency.WEEKLY)
    schedule_days = Column(JSON, default=list)  # List of days for scheduling
    schedule_time = Column(String, default="10:00")  # Time in HH:MM format
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="user_settings")
    saved_grants = relationship("Grant", secondary="saved_grants", back_populates="saved_by")

    def to_dict(self):
        """Convert UserSettings model to dictionary format for API responses"""
        return {
            "emailNotifications": self.email_notifications,
            "deadlineReminders": self.deadline_reminders,
            "searchFrequency": self.schedule_frequency.value if self.schedule_frequency is not None else "weekly",
            "categories": self.notify_categories if self.notify_categories is not None else [],
            "minimumScore": self.minimum_score if self.minimum_score is not None else 0.7
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
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)  # NULL for legacy searches

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

    # Relationships
    user = relationship("User", back_populates="search_runs")