from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import AsyncSessionLocal
from utils.pinecone_client import PineconeClient
from utils.perplexity_client import PerplexityClient
from utils.notification_manager import NotificationManager
from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from app.services import services

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
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

def get_research_agent(
    db: AsyncSession = Depends(get_db_session),
    perplexity: PerplexityClient = Depends(get_perplexity),
    pinecone: PineconeClient = Depends(get_pinecone)
) -> ResearchAgent:
    return ResearchAgent(
        perplexity_client=perplexity,
        db_session=db,
        pinecone_client=pinecone
    )

def get_analysis_agent(
    db: AsyncSession = Depends(get_db_session),
    pinecone: PineconeClient = Depends(get_pinecone)
) -> AnalysisAgent:
    return AnalysisAgent(
        db_session=db,
        pinecone_client=pinecone
    )