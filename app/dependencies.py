# Key change: Line ~50: Ensured consistency comment for db_sessionmaker parameter

from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from utils.pinecone_client import PineconeClient
from utils.perplexity_client import PerplexityClient
from utils.notification_manager import NotificationManager
from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from app.services import services

def get_research_agent(
    perplexity: PerplexityClient = Depends(get_perplexity),
    pinecone: PineconeClient = Depends(get_pinecone)
) -> ResearchAgent:
    if not services.db_sessionmaker:
        raise RuntimeError("Database sessionmaker not initialized in services.")
    return ResearchAgent(
        perplexity_client=perplexity,
        db_sessionmaker=services.db_sessionmaker,  # Ensured consistency
        pinecone_client=pinecone
    )

# ... rest of the dependencies implementation
