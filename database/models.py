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

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False, index=True)
    description = Column(String)
    funding_amount = Column(Float)
    deadline = Column(DateTime, index=True)
    source = Column(String)
    category = Column(String, index=True)
    source_url = Column(String)
    status = Column(Enum(GrantStatus), default=GrantStatus.ACTIVE, index=True)
    eligibility = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    analyses = relationship("Analysis", back_populates="grant", cascade="all, delete-orphan")
    saved_by = relationship("UserSettings", secondary="saved_grants", back_populates="saved_grants")

class Analysis(Base):
    __tablename__ = 'analyses'

    id = Column(Integer, primary_key=True)
    grant_id = Column(Integer, ForeignKey('grants.id', ondelete='CASCADE'))
    score = Column(Float, index=True)
    notes = Column(String)
    analysis_date = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    grant = relationship("Grant", back_populates="analyses")

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