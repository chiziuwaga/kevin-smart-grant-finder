import logging
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.analysis_agent import GrantAnalysisAgent
from agents.research_agent import ResearchAgent
# Import API router (after we have a placeholder services dict)
from api.routes import \
    api as api_router  # Rename imported 'api' to avoid conflict
from config.logging_config import setup_logging
# Import your API routers and database clients
from database.mongodb_client import MongoDBClient
from database.pinecone_client import PineconeClient
# Shared services dictionary
from service_registry import services
from utils.agentql_client import AgentQLClient
from utils.notification_manager import NotificationManager
from utils.perplexity_client import PerplexityClient

# Set up logging
setup_logging()
logger = logging.getLogger("grant_finder")

# Load environment variables
load_dotenv()

# Initialize FastAPI app
main_app = FastAPI(title="Kevin's Smart Grant Finder API", version="1.0.0")

# Configure CORS
main_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Update with specific Vercel URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Service Initialization --- 
# This section initializes necessary services that the API might need access to.
# In a production setup, consider dependency injection (e.g., using FastAPI's Depends)
# or a global state management approach if services need to be shared across requests.

init_status = {}

def initialize_service_with_retry(service_name, init_func, max_retries=3, retry_delay=2):
    """Initialize a service with retry logic and proper error handling."""
    for attempt in range(max_retries):
        try:
            logger.info(f"Initializing {service_name} (attempt {attempt+1}/{max_retries})...")
            service = init_func()
            logger.info(f"Successfully initialized {service_name}")
            return service, True
        except Exception as e:
            logger.error(f"Error initializing {service_name} (attempt {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying {service_name} initialization in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)
            else:
                logger.critical(f"Failed to initialize {service_name} after {max_retries} attempts")
                return None, False
    return None, False

def initialize_global_services():
    """Initialize all required services at startup."""
    global services, init_status
    logger.info("Initializing global services...")

    services["mongodb_client"], init_status['mongo'] = initialize_service_with_retry(
        "MongoDB client", 
        lambda: MongoDBClient()
    )
    services["pinecone_client"], init_status['pinecone'] = initialize_service_with_retry(
        "Pinecone client",
        lambda: PineconeClient()
    )
    services["agentql_client"], init_status['agentql'] = initialize_service_with_retry(
        "AgentQL client",
        lambda: AgentQLClient()
    )
    services["perplexity_client"], init_status['perplexity'] = initialize_service_with_retry(
        "Perplexity client",
        lambda: PerplexityClient()
    )
    services["notification_manager"], init_status['notifier'] = initialize_service_with_retry(
        "Notification manager",
        lambda: NotificationManager()
    )

    # Initialize Agents - they depend on other clients
    if init_status['mongo'] and init_status['agentql'] and init_status['perplexity']:
        services["research_agent"], init_status['research_agent'] = initialize_service_with_retry(
            "Research Agent",
            lambda: ResearchAgent(
                services["agentql_client"],
                services["perplexity_client"],
                services["mongodb_client"]
            )
        )
    else:
        logger.error("Cannot initialize Research Agent due to missing dependencies.")
        init_status['research_agent'] = False

    if init_status['mongo'] and init_status['pinecone']:
        services["analysis_agent"], init_status['analysis_agent'] = initialize_service_with_retry(
            "Analysis Agent",
            lambda: GrantAnalysisAgent(
                services["pinecone_client"],
                services["mongodb_client"]
            )
        )
    else:
        logger.error("Cannot initialize Analysis Agent due to missing dependencies.")
        init_status['analysis_agent'] = False

    init_summary = ", ".join([f"{svc}: {'✓' if status else '✗'}" for svc, status in init_status.items()])
    logger.info(f"Global service initialization summary: {init_summary}")

# Run service initialization at startup
initialize_global_services()

# --- Mount API Router --- 
# Make services available to the API routes (e.g., via dependency injection)
# For simplicity here, we might pass them directly if needed, but Depends is cleaner.

# Example: Update get_db in api/routes.py to use the global services dict
# This avoids re-initializing the client on every request.
# In api/routes.py:
# 
# from Home import services # Assuming services is accessible
# 
# def get_db():
#     if "mongodb_client" in services and services["mongodb_client"]:
#         return services["mongodb_client"]
#     else:
#         logger.error("MongoDB client not initialized globally.")
#         raise HTTPException(status_code=503, detail="Database service unavailable")

main_app.include_router(api_router, prefix="/api")

# --- Root Endpoint (Optional) --- 
@main_app.get("/")
async def read_root():
    return {"message": "Welcome to Kevin's Smart Grant Finder API"}

# --- Application Startup Event (Optional) --- 
# @main_app.on_event("startup")
# async def startup_event():
#     logger.info("API Application startup complete.")

# --- Application Shutdown Event (Optional) --- 
# @main_app.on_event("shutdown")
# async def shutdown_event():
#     # Clean up resources if needed
#     logger.info("API Application shutting down.")

# Note: When running with uvicorn like `uvicorn Home:main_app --reload`,
# this file (Home.py) becomes the entry point for the ASGI server. 