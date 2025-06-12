from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from utils.pinecone_client import PineconeClient
from utils.perplexity_client import PerplexityClient
from utils.notification_manager import NotificationManager
from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from app.services import services

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    if not services.db_sessionmaker:
        raise RuntimeError("Database sessionmaker not initialized in services.")
    
    async with services.db_sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

def get_pinecone() -> PineconeClient:
    return services.pinecone_client

def get_perplexity() -> PerplexityClient:
    return services.perplexity_client

def get_notifier() -> NotificationManager:
    return services.notifier

def get_db_sessionmaker():
    """Get the database sessionmaker from services"""
    if not services.db_sessionmaker:
        raise RuntimeError("Database sessionmaker not initialized in services.")
    return services.db_sessionmaker

def get_research_agent(
    perplexity: PerplexityClient = Depends(get_perplexity),
    pinecone: PineconeClient = Depends(get_pinecone)
) -> ResearchAgent:
    if not services.db_sessionmaker:
        raise RuntimeError("Database sessionmaker not initialized in services.")
    return ResearchAgent(
        perplexity_client=perplexity,
        db_session_maker=services.db_sessionmaker
    )

def get_analysis_agent(
    pinecone: PineconeClient = Depends(get_pinecone)
) -> AnalysisAgent:
    if not services.db_sessionmaker:
        raise RuntimeError("Database sessionmaker not initialized in services.")
    return AnalysisAgent(
        db_sessionmaker=services.db_sessionmaker,  # Corrected: Pass the sessionmaker
        pinecone_client=pinecone
    )