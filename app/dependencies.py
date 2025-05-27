from fastapi import Depends
from typing import Any
from utils.mongodb_client import MongoDBClient
from utils.pinecone_client import PineconeClient
from utils.perplexity_client import PerplexityClient
from utils.notification_manager import NotificationManager
from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from app.services import services

def get_mongo() -> MongoDBClient:
    return services.mongodb_client

def get_pinecone() -> PineconeClient:
    return services.pinecone_client

def get_perplexity() -> PerplexityClient:
    return services.perplexity_client

def get_notifier() -> NotificationManager:
    return services.notifier

def get_research_agent() -> ResearchAgent:
    return ResearchAgent(
        perplexity_client=get_perplexity(),
        mongodb_client=get_mongo(),
        pinecone_client=get_pinecone()
    )

def get_analysis_agent() -> AnalysisAgent:
    return AnalysisAgent(
        mongodb_client=get_mongo(),
        pinecone_client=get_pinecone()
    )