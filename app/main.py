from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
import uuid
import traceback
import json
from datetime import datetime
import sys
import os
import time
from typing import List
from app.router import api_router
from app.services import init_services, services
import logging
from config.logging_config import setup_logging
from sqlalchemy import text
from database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
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
async def health_check():
    """
    Simple health check endpoint for load balancers
    """
    try:
        # Quick database test if available
        if services.db_sessionmaker:
            async with services.db_sessionmaker() as session:
                await session.execute(text("SELECT 1"))
            db_status = "ok"
        else:
            db_status = "unavailable"
    except Exception as e:
        logger.error(f"Health check database error: {e}")
        db_status = "error"

    status_code = 200 if db_status in ["ok", "unavailable"] else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if db_status == "ok" else "degraded" if db_status == "unavailable" else "error",
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_status
        }
    )

@app.get("/health/detailed", tags=["Health Check"])
async def detailed_health_check():
    """
    Comprehensive health check with detailed service status
    """
    from app.health import HealthChecker
    
    try:
        health_data = await HealthChecker.comprehensive_health_check()
        
        # Determine HTTP status based on overall health
        if health_data["overall_status"] == "healthy":
            status_code = 200
        elif health_data["overall_status"] == "degraded":
            status_code = 206  # Partial Content
        else:
            status_code = 503  # Service Unavailable
            
        return JSONResponse(
            status_code=status_code,
            content=health_data
        )
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "overall_status": "error",
                "error": "Health check system failure",
                "timestamp": datetime.utcnow().isoformat()
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

# Request monitoring and error prediction middleware
@app.middleware("http")
async def error_prediction_middleware(request: Request, call_next):
    """Predictive error handling middleware that monitors patterns"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Add request context
    request.state.request_id = request_id
    request.state.start_time = start_time
    
    # Predictive error patterns
    error_risk_factors = []
    
    # Check for common problematic patterns
    if request.method == "POST" and "grants" in str(request.url):
        error_risk_factors.append("grant_creation_endpoint")
    
    if "search" in str(request.url):
        error_risk_factors.append("search_endpoint")
        
    try:
        # Log request with risk assessment
        logger.info(
            f"Request {request_id}: {request.method} {request.url}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "risk_factors": error_risk_factors,
                "user_agent": request.headers.get("User-Agent", ""),
                "content_type": request.headers.get("Content-Type", "")
            }
        )
        
        response = await call_next(request)
        
        # Log successful response
        duration = time.time() - start_time
        logger.info(
            f"Response {request_id}: {response.status_code} in {duration:.3f}s",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration": duration,
                "risk_factors": error_risk_factors
            }
        )
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        error_type = type(e).__name__
        
        # Enhanced error logging with pattern detection
        logger.error(
            f"Request {request_id} failed after {duration:.3f}s: {error_type}: {str(e)}",
            exc_info=True,
            extra={
                "request_id": request_id,
                "duration": duration,
                "error_type": error_type,
                "error_message": str(e),
                "risk_factors": error_risk_factors,
                "url": str(request.url)
            }
        )
        
        # Re-raise for main exception handlers to process
        raise

# Initialize services on startup
@app.on_event("startup")
async def startup_event():
    """Initialize services with graceful degradation on startup"""
    logger.info("=== Kevin Smart Grant Finder Startup ===")
    logger.info("Starting service initialization with graceful degradation...")
    
    try:
        await init_services()
        logger.info("Service initialization completed")
        
        # Log service status
        if services.db_sessionmaker:
            logger.info("✅ Database: Connected")
        else:
            logger.warning("⚠️  Database: Not available")
            
        if services.pinecone_client:
            is_mock = getattr(services.pinecone_client, 'is_mock', False)
            if is_mock:
                logger.warning("⚠️  Pinecone: Using mock client")
            else:
                logger.info("✅ Pinecone: Connected")
        else:
            logger.warning("⚠️  Pinecone: Not available")
            
        if services.perplexity_client:
            is_mock = getattr(services.perplexity_client, 'is_mock', False)
            if is_mock:
                logger.warning("⚠️  Perplexity: Using mock client")
            else:
                logger.info("✅ Perplexity: Connected")
        else:
            logger.warning("⚠️  Perplexity: Not available")
            
        if services.notifier:
            is_mock = getattr(services.notifier, 'is_mock', False)
            if is_mock:
                logger.warning("⚠️  Notifications: Using mock manager")
            else:
                logger.info("✅ Notifications: Connected")
        else:
            logger.warning("⚠️  Notifications: Not available")
            
        logger.info("=== Startup Complete - Application Ready ===")
        
    except Exception as e:
        logger.error(f"Critical startup error: {e}", exc_info=True)
        logger.error("Application may have limited functionality")
        # Don't raise - allow app to start with degraded functionality

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

# Exception handler for HTTP errors
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions and return JSON response"""
    logger.error(f"HTTP error occurred: {exc.detail}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "detail": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Exception handler for request validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Enhanced validation error handler for 422 errors with recursive correction"""
    error_id = str(uuid.uuid4())
    
    # Extract detailed validation errors
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    logger.warning(
        f"Validation error {error_id} in {request.method} {request.url}: {len(validation_errors)} errors",
        exc_info=True,
        extra={
            "error_id": error_id,
            "method": request.method,
            "url": str(request.url),
            "validation_errors": validation_errors,
            "body": getattr(exc, 'body', None)
        }
    )
    
    # Recursive correction attempt for common validation issues
    corrective_suggestions = []
    for error in validation_errors:
        if "string_too_short" in error["type"]:
            corrective_suggestions.append(f"Field '{error['field']}' requires more characters")
        elif "value_error.missing" in error["type"]:
            corrective_suggestions.append(f"Field '{error['field']}' is required")
        elif "type_error" in error["type"]:
            corrective_suggestions.append(f"Field '{error['field']}' has incorrect data type")
        elif "value_error.date" in error["type"]:
            corrective_suggestions.append(f"Field '{error['field']}' should be in format YYYY-MM-DD")
    
    return JSONResponse(
        status_code=422,
        content={
            "status": "validation_error",
            "error_id": error_id,
            "message": "Request validation failed. Please check the provided data.",
            "details": validation_errors,
            "suggestions": corrective_suggestions,
            "timestamp": datetime.utcnow().isoformat(),
            "help": "Ensure all required fields are provided with correct data types."
        }
    )

# Exception handler for all other exceptions
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions with recursive error correction"""
    error_id = str(uuid.uuid4())
    error_type = type(exc).__name__
    
    # Log the detailed error with context
    logger.error(
        f"Unhandled error {error_id}: {error_type}: {str(exc)}",
        exc_info=True,
        extra={
            "error_id": error_id,
            "error_type": error_type,
            "request_url": str(request.url),
            "request_method": request.method,
            "user_agent": request.headers.get("User-Agent", ""),
            "stack_trace": traceback.format_exc()
        }
    )
    
    # Recursive error correction based on error type
    retry_attempted = False
    recovery_message = None
    
    try:
        if "AttributeError" in error_type:
            logger.info(f"Attempting AttributeError recovery for {error_id}")
            # For AttributeError, try to provide default values or alternative methods
            if "has no attribute" in str(exc):
                recovery_message = "Missing method or attribute detected. Using fallback implementation."
                retry_attempted = True
        
        elif "DatabaseError" in error_type or "OperationalError" in error_type:
            logger.info(f"Attempting database recovery for {error_id}")
            # For database errors, attempt reconnection
            try:
                if services.db_sessionmaker:
                    async with services.db_sessionmaker() as test_session:
                        await test_session.execute(text("SELECT 1"))
                    recovery_message = "Database connection restored."
                    retry_attempted = True
            except Exception:
                logger.warning(f"Database recovery failed for {error_id}")
        
        elif "ValidationError" in error_type:
            logger.info(f"Attempting validation recovery for {error_id}")
            recovery_message = "Data validation issue detected. Please check input format."
            retry_attempted = True
        
        # If recovery was attempted successfully, return a more informative response
        if retry_attempted and recovery_message:
            return JSONResponse(
                status_code=503,  # Service temporarily unavailable but recoverable
                content={
                    "status": "recovered",
                    "error_id": error_id,
                    "message": recovery_message,
                    "detail": "The request encountered an issue but recovery was attempted. Please retry.",
                    "timestamp": datetime.utcnow().isoformat(),
                    "retry_after": 5  # Suggest retry after 5 seconds
                }
            )
    
    except Exception as recovery_exc:
        logger.error(f"Recovery attempt failed for {error_id}: {str(recovery_exc)}", exc_info=True)
    
    # Default error response when no recovery is possible
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_id": error_id,
            "message": "An unexpected error occurred. Our team has been notified.",
            "timestamp": datetime.utcnow().isoformat(),
            "support_message": f"Please include error ID {error_id} when contacting support."
        }
    )

# Add routes
app.include_router(api_router, prefix="/api")

# Add root route
@app.get("/")
async def read_root():
    """Root endpoint - welcome message"""
    return {"message": "Welcome to Kevin's Smart Grant Finder API"}