from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, logging
from pymongo import MongoClient
import pinecone
from agents.research_agent import ResearchAgent
from agents.grant_analysis_agent import GrantAnalysisAgent
from datetime import datetime

# Load environment variables
MONGODB_URI = os.getenv("MONGODB_URI")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
AGENTQL_API_KEY = os.getenv("AGENTQL_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# Initialize FastAPI app
app = FastAPI(title="Grant Finder API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    global mongodb_client, agentql_client, perplexity_client, pinecone_index
    global research_agent, analysis_agent

    # MongoDB client
    mongodb_client = MongoClient(MONGODB_URI)

    # Pinecone initialization
    pinecone.init(api_key=PINECONE_API_KEY)
    pinecone_index = pinecone.Index(os.getenv("PINECONE_INDEX_NAME", "grant-index"))

    # AgentQL client (replace with your import path)
    from agentql_client import AgentQLClient
    agentql_client = AgentQLClient(api_key=AGENTQL_API_KEY)

    # Perplexity client (replace with your import path)
    from perplexity_client import PerplexityClient
    perplexity_client = PerplexityClient(api_key=PERPLEXITY_API_KEY)

    # Initialize agents
    research_agent = ResearchAgent(perplexity_client, agentql_client, mongodb_client)
    analysis_agent = GrantAnalysisAgent(perplexity_client, agentql_client, mongodb_client)

@app.get("/api/search")
def search_grants(category: str):
    """Endpoint to search grants by category"""
    try:
        params = {"category": category}
        results = research_agent.search_grants(params)
        return {"results": results}
    except Exception as e:
        logging.error("Grant search failed", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics")
def get_metrics():
    """Endpoint to retrieve application metrics"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()} 