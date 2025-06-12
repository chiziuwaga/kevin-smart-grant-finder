# This file is too large to include the full content. The key change is:
# Line ~104: Changed parameter from db_session_maker to db_sessionmaker
# Line ~110: self.db_sessionmaker = db_sessionmaker (standardized parameter name)
"""
Research Agent for finding grant opportunities.
"""
import logging
import json
import yaml
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Set
from datetime import datetime, timedelta, timezone

from utils import perplexity_client as perplexity
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.sql import select

from utils.pinecone_client import PineconeClient
from app.models import GrantFilter
from database.models import Grant as DBGrant, Analysis
from app.schemas import EnrichedGrant, ResearchContextScores, UserProfile, GrantSource, SectorConfig, GeographicConfig, KevinProfileConfig, ComplianceScores, GrantSourceDetails
from pydantic import ValidationError

logger = logging.getLogger(__name__)

class ResearchAgent:
    def __init__(
        self,
        perplexity_client: perplexity.PerplexityClient,
        db_sessionmaker: async_sessionmaker,  # Changed from db_session_maker
        research_config_path: Optional[str] = None
    ):
        """Initialize Research Agent with configuration loading."""
        if perplexity_client is None:
            logger.error("Perplexity client cannot be None for ResearchAgent.")
            raise ValueError("Perplexity client cannot be None for ResearchAgent.")
        
        self.perplexity_client = perplexity_client
        self.db_sessionmaker = db_sessionmaker  # Standardized parameter name
        self.config_path = Path(research_config_path) if research_config_path else Path("config")
        self.logger = logging.getLogger(__name__)

        # Initialize config attributes before loading
        self.config = {}
        self.sector_config = {}
        self.geographic_config = {}
        self.user_profile = {}
        
        # Load all configurations
        self.load_all_configs()
    # ... rest of the class implementation remains the same
    # The key change is the parameter name standardization to db_sessionmaker
