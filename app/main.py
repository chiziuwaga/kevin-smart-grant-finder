from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.router import api_router
from app.services import init_services, services
import logging
from config.logging_config import setup_logging
from datetime import datetime
import os
from typing import List
import time
from fastapi.responses import JSONResponse
from sqlalchemy import text
from database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def get_allowed_origins() -> List[str]:
    """Get allowed origins from environment or use defaults"""
    env_origins = os.getenv('ALLOWED_ORIGINS')
    if env_origins:
        return env_origins.split(',')
    
    # Default origins for different environments
    if os.getenv('ENVIRONMENT') == 'production':
        return [
            'https://smartgrantfinder.vercel.app',
            'https://www.smartgrantfinder.vercel.app'
        ]
    elif os.getenv('ENVIRONMENT') == 'staging':
        return [
            'https://staging.smartgrantfinder.vercel.app',
            'http://localhost:3000'
        ]
    else:
        # Development - allow localhost and production frontend for testing
        return [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://localhost:8000',
            'https://smartgrantfinder.vercel.app'
        ]

# Create FastAPI app
app = FastAPI(
    title="Kevin Smart Grant Finder",
    description="AI-powered grant search and analysis system",
    version="1.0.0",
    docs_url="/api/docs",  # Scoped to /api path
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

@app.get("/health", tags=["Health Check"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint to verify service and database connectivity.
    """
    start_time = time.time()
    try:
        # Check database connection
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        db_status = "error"

    response_time = time.time() - start_time
    
    status_code = 200 if db_status == "ok" else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if db_status == "ok" else "error",
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": {
                "database": db_status
            },
            "response_time": f"{response_time:.4f}s"
        }
    )

# CORS middleware - configured for Vercel frontend
allowed_origins = get_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Length",
        "X-Total-Count", 
        "X-Rate-Limit-Remaining"
    ],
    max_age=600
)

# Initialize services on startup
@app.on_event("startup")
async def startup_event():
    """Initialize services and verify connections on startup"""
    logger.info("Starting service initialization steps...")
    try:
        logger.info("Initializing core services via init_services()...")
        await init_services()
        logger.info("init_services() completed successfully")
        
        # Verify database connectivity using services
        if services.db_sessionmaker:
            async with services.db_sessionmaker() as session:
                await session.execute(text("SELECT 1"))
            logger.info("Database connection verified via services")
        else:
            logger.warning("Database sessionmaker not initialized in services")
            
    except Exception as e:
        logger.error(f"Service initialization failed: {e}", exc_info=True)

    logger.info("Service initialization steps completed")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("Shutting down application...")
    try:
        if services.db_engine:
            await services.db_engine.dispose()
            logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}", exc_info=True)

# Add routes
app.include_router(api_router, prefix="/api")

# Add root route
@app.get("/")
async def read_root():
    """Root endpoint - welcome message"""
    return {"message": "Welcome to Kevin's Smart Grant Finder API"}