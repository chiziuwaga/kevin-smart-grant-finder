import logging
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.analysis_agent import AnalysisAgent
from agents.research_agent import ResearchAgent
# Import API router (after we have a placeholder services dict)
from app.router import \
    api_router as api_router  # Corrected import
from config.logging_config import setup_logging
from config.settings import get_settings # Added import
# Import your API routers and database clients
from utils.pinecone_client import PineconeClient # Corrected import path
# Shared services dictionary
from app.services import services # Corrected import path
# from utils.agentql_client import AgentQLClient # Commented out missing client
from utils.notification_manager import NotificationManager
from utils.perplexity_client import PerplexityClient
from fastapi.responses import JSONResponse
from sqlalchemy import text # Added for health check

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
    global services, init_status # services is now the dataclass instance
    logger.info("Initializing global services...")
    current_settings = get_settings() # Ensure settings are loaded here

    init_status['mongo'] = False 
    pinecone_instance, pinecone_status_from_retry = initialize_service_with_retry(
        "Pinecone client",
        lambda: PineconeClient()
    )
    if pinecone_status_from_retry and pinecone_instance and not pinecone_instance.use_mock:
        services.pinecone_client = pinecone_instance
        init_status['pinecone'] = True
        logging.info("Pinecone client initialized successfully (REAL).")
    else:
        services.pinecone_client = pinecone_instance # Store even if mock, for consistent access patterns
        init_status['pinecone'] = False # Mark as failed for real operations
        if pinecone_instance and pinecone_instance.use_mock:
            logging.warning("Pinecone client initialized in MOCK mode.")
        else:
            logging.error("Pinecone client failed to initialize from retry logic.")

    init_status['agentql'] = False 

    perplexity_instance, perplexity_status = initialize_service_with_retry(
        "Perplexity client",
        lambda: PerplexityClient()
    )
    if perplexity_status:
        services.perplexity_client = perplexity_instance
    init_status['perplexity'] = perplexity_status
    
    notification_instance, notification_status = initialize_service_with_retry(
        "Notification manager",
        lambda: NotificationManager(
            telegram_token=current_settings.telegram_token,
            telegram_chat_id=current_settings.telegram_chat_id
        )
    )
    if notification_status:
        services.notifier = notification_instance 
    init_status['notifier'] = notification_status

    try:
        logger.info("Initializing Database session manager...")
        from database.session import AsyncSessionLocal, engine 
        services.db_engine = engine 
        services.db_sessionmaker = AsyncSessionLocal 
        logger.info("Database session manager configured.")
        init_status['db'] = True
    except Exception as e:
        logger.critical(f"Failed to initialize Database session manager: {e}", exc_info=True)
        init_status['db'] = False

    if init_status['perplexity'] and init_status['pinecone'] and init_status['db']:
        research_agent_instance, research_agent_status = initialize_service_with_retry(
            "Research Agent",
            lambda: ResearchAgent(
                perplexity_client=services.perplexity_client,
                db_sessionmaker=services.db_sessionmaker,  # Pass sessionmaker
                pinecone_client=services.pinecone_client
            )
        )
        init_status['research_agent'] = research_agent_status
    else:
        logger.error(f"Cannot initialize Research Agent due to missing dependencies. Status - Perplexity: {init_status.get('perplexity')}, Pinecone: {init_status.get('pinecone')}, DB: {init_status.get('db')}.")
        init_status['research_agent'] = False

    if init_status['pinecone'] and init_status['db']:
        analysis_agent_instance, analysis_agent_status = initialize_service_with_retry(
            "Analysis Agent",
            lambda: AnalysisAgent(
                db_sessionmaker=services.db_sessionmaker, # Pass sessionmaker
                pinecone_client=services.pinecone_client
            )
        )
        init_status['analysis_agent'] = analysis_agent_status
    else:
        logger.error(f"Cannot initialize Analysis Agent due to missing dependencies. Status - Pinecone: {init_status.get('pinecone')}, DB: {init_status.get('db')}.")
        init_status['analysis_agent'] = False
    
    # Replace special characters for logging if needed, or ensure console supports UTF-8
    summary_items = []
    for svc, status in init_status.items():
        summary_items.append(f"{svc}: {'✓' if status else '✗'}") # Using ✓ and ✗ for clarity
    init_summary = ", ".join(summary_items)
    try:
        logger.info(f"Global service initialization summary: {init_summary}")
    except UnicodeEncodeError:
        safe_init_summary = init_summary.replace('✓', 'OK').replace('✗', 'FAIL')
        logger.info(f"Global service initialization summary (ASCII): {safe_init_summary}")

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

# @main_app.exception_handler(Exception) # Commented out for now to see specific errors if they occur
# async def global_exception_handler(request, exc: Exception):
#     logger.error(f"Unhandled exception: {exc}", exc_info=True)
#     return JSONResponse(
#         status_code=500,
#         content={"status": "error", "detail": "Internal server error"}
#     )

@main_app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify database connection."""
    if not services.db_sessionmaker:
        logger.error("Database sessionmaker not initialized for health check.")
        return JSONResponse(status_code=503, content={"status": "error", "detail": "Database service not configured"})
    try:
        async with services.db_sessionmaker() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Database health check successful.")
        return {"status": "ok", "detail": "Database connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}", exc_info=True)
        return JSONResponse(status_code=503, content={"status": "error", "detail": f"Database connection failed: {str(e)}"})

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