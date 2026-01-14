from typing import AsyncGenerator
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from utils.pinecone_client import PineconeClient
from services.deepseek_client import DeepSeekClient
from services.resend_client import ResendEmailClient
from agents.integrated_research_agent import IntegratedResearchAgent
from agents.analysis_agent import AnalysisAgent
from app.services import services

logger = logging.getLogger(__name__)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Enhanced database session dependency with graceful error handling"""
    if not services.db_sessionmaker:
        logger.error("Database sessionmaker not initialized")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Database service unavailable",
                "message": "The database service is temporarily unavailable. Please try again later.",
                "service": "database"
            }
        )
    
    session = None
    try:
        session = services.db_sessionmaker()
        yield session
        await session.commit()
    except Exception as e:
        logger.error(f"Database session error: {e}", exc_info=True)
        if session:
            await session.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database operation failed",
                "message": "A database error occurred. Please try again.",
                "service": "database"
            }
        )
    finally:
        if session:
            await session.close()

def get_pinecone():
    """Get Pinecone client with fallback handling"""
    if not services.pinecone_client:
        logger.warning("Pinecone client not available, using mock")
        from app.services import MockPineconeClient
        return MockPineconeClient()
    return services.pinecone_client

def get_deepseek():
    """Get DeepSeek client with fallback handling"""
    if not services.deepseek_client:
        logger.warning("DeepSeek client not available, creating new instance")
        return DeepSeekClient()
    return services.deepseek_client

def get_notifier():
    """Get email notification client with fallback handling"""
    if not services.notifier:
        logger.warning("Notifier not available, creating new Resend client")
        return ResendEmailClient()
    return services.notifier

def get_db_sessionmaker():
    """Get the database sessionmaker from services with error handling"""
    if not services.db_sessionmaker:
        logger.error("Database sessionmaker not initialized")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Database service unavailable",
                "message": "The database service is temporarily unavailable.",
                "service": "database"
            }
        )
    return services.db_sessionmaker

def get_research_agent(
    deepseek = Depends(get_deepseek),
    pinecone = Depends(get_pinecone)
) -> IntegratedResearchAgent:
    """Get research agent with fallback handling"""
    if not services.db_sessionmaker:
        logger.error("Cannot create research agent: Database not available")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Research service unavailable",
                "message": "The research service requires database access.",
                "service": "research_agent"
            }
        )
    
    try:
        return IntegratedResearchAgent(
            db_session_maker=services.db_sessionmaker
        )
    except Exception as e:
        logger.error(f"Failed to create research agent: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Research agent initialization failed",
                "message": "Unable to initialize research capabilities.",
                "service": "research_agent"
            }
        )

def get_analysis_agent(
    pinecone = Depends(get_pinecone)
) -> AnalysisAgent:
    """Get analysis agent with fallback handling"""
    if not services.db_sessionmaker:
        logger.error("Cannot create analysis agent: Database not available")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Analysis service unavailable",
                "message": "The analysis service requires database access.",
                "service": "analysis_agent"
            }
        )
    
    try:
        return AnalysisAgent(
            db_sessionmaker=services.db_sessionmaker,
            pinecone_client=pinecone
        )
    except Exception as e:
        logger.error(f"Failed to create analysis agent: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Analysis agent initialization failed",
                "message": "Unable to initialize analysis capabilities.",
                "service": "analysis_agent"
            }
        )