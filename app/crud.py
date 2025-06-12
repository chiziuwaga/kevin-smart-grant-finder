# Key change: Line ~251: Ensured consistency comment for db_sessionmaker parameter
# The ResearchAgent instantiation already uses db_sessionmaker correctly

import logging
import time
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from database.models import Grant as DBGrant, Analysis, SearchRun, UserSettings, ApplicationHistory
from utils.pinecone_client import PineconeClient
from app.schemas import EnrichedGrant, ResearchContextScores, ComplianceScores, GrantSourceDetails, ApplicationHistoryCreate
from database import models
from app import schemas

from agents.research_agent import ResearchAgent
from agents.compliance_agent import ComplianceAnalysisAgent
from utils.perplexity_client import PerplexityClient
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

async def run_full_search_cycle(
    db_sessionmaker: async_sessionmaker, 
    perplexity_client: PerplexityClient, 
    pinecone_client: PineconeClient 
) -> List[EnrichedGrant]:
    """Run a complete grant search cycle, including research and compliance analysis."""
    logger.info("Starting full search cycle...")
    start_time_cycle = time.time()
    research_agent_instance = None
    try:
        research_agent_instance = ResearchAgent(
            perplexity_client=perplexity_client,
            db_sessionmaker=db_sessionmaker,  # Ensured consistency
            config_path=settings.CONFIG_DIR
        )
    except Exception as e:
        logger.error(f"Failed to initialize ResearchAgent: {e}", exc_info=True)
        # ... rest of error handling
    # ... rest of the function implementation
