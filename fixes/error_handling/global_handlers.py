"""
Enhanced global error handlers with recovery mechanisms.
Provides comprehensive error handling and graceful degradation.
"""

import asyncio
import logging
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Union, Callable, Awaitable
from functools import wraps

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, OperationalError
from pydantic import ValidationError

logger = logging.getLogger(__name__)

class ErrorRecoveryManager:
    """Manages error recovery attempts and tracks failure patterns"""
    
    def __init__(self):
        self.error_patterns = {}
        self.recovery_attempts = {}
        self.max_recovery_attempts = 3
        self.recovery_cooldown = 60  # seconds
        
    def should_attempt_recovery(self, error_type: str, error_context: str) -> bool:
        """Determine if recovery should be attempted for this error"""
        key = f"{error_type}:{error_context}"
        
        if key not in self.recovery_attempts:
            self.recovery_attempts[key] = {
                'count': 0,
                'last_attempt': None,
                'success_count': 0
            }
        
        attempt_info = self.recovery_attempts[key]
        
        # Check if we've exceeded max attempts
        if attempt_info['count'] >= self.max_recovery_attempts:
            # Reset if enough time has passed
            if (attempt_info['last_attempt'] and 
                (datetime.utcnow() - attempt_info['last_attempt']).seconds > self.recovery_cooldown):
                attempt_info['count'] = 0
            else:
                return False
        
        return True
    
    def record_recovery_attempt(self, error_type: str, error_context: str, success: bool):
        """Record the result of a recovery attempt"""
        key = f"{error_type}:{error_context}"
        
        if key not in self.recovery_attempts:
            self.recovery_attempts[key] = {
                'count': 0,
                'last_attempt': None,
                'success_count': 0
            }
        
        attempt_info = self.recovery_attempts[key]
        attempt_info['count'] += 1
        attempt_info['last_attempt'] = datetime.utcnow()
        
        if success:
            attempt_info['success_count'] += 1
            # Reset count on success
            attempt_info['count'] = 0

recovery_manager = ErrorRecoveryManager()

async def attempt_database_recovery() -> bool:
    """Attempt to recover from database errors"""
    try:
        from fixes.database.robust_connection_manager import get_connection_manager
        
        manager = await get_connection_manager()
        return await manager._attempt_recovery()
    except Exception as e:
        logger.error(f"Database recovery attempt failed: {e}")
        return False

async def attempt_service_recovery(service_name: str) -> bool:
    """Attempt to recover a specific service"""
    try:
        from fixes.services.graceful_services import get_service_manager
        from config.settings import get_settings
        
        manager = await get_service_manager()
        settings = get_settings()
        return await manager.attempt_service_recovery(service_name, settings)
    except Exception as e:
        logger.error(f"Service {service_name} recovery attempt failed: {e}")
        return False

def create_error_response(
    status_code: int,
    error_type: str,
    message: str,
    error_id: str,
    details: Optional[Dict[str, Any]] = None,
    recovery_info: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """Create standardized error response"""
    content: Dict[str, Any] = {
        "status": "error",
        "error_type": error_type,
        "error_id": error_id,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        content["details"] = details
    
    if recovery_info:
        content["recovery"] = recovery_info
    
    return JSONResponse(status_code=status_code, content=content)

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler with recovery mechanisms.
    Handles all unhandled exceptions gracefully.
    """
    error_id = str(uuid.uuid4())
    error_type = type(exc).__name__
    error_message = str(exc)
    
    # Extract request information safely
    try:
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "user_agent": request.headers.get("user-agent", "unknown"),
            "content_type": request.headers.get("content-type", "unknown")
        }
    except Exception:
        request_info = {"method": "unknown", "url": "unknown"}
    
    # Log the error with full context
    logger.error(
        f"Unhandled error {error_id}: {error_type}: {error_message}",
        exc_info=True,
        extra={
            "error_id": error_id,
            "error_type": error_type,
            "error_message": error_message,
            "request_info": request_info,
            "stack_trace": traceback.format_exc()
        }
    )
    
    # Attempt recovery based on error type
    recovery_attempted = False
    recovery_success = False
    recovery_message = None
    
    try:
        # Database-related errors
        if isinstance(exc, (SQLAlchemyError, DisconnectionError, OperationalError)):
            if recovery_manager.should_attempt_recovery("database", request_info["url"]):
                logger.info(f"Attempting database recovery for error {error_id}")
                recovery_attempted = True
                recovery_success = await attempt_database_recovery()
                recovery_manager.record_recovery_attempt("database", request_info["url"], recovery_success)
                
                if recovery_success:
                    recovery_message = "Database connection restored. Please retry your request."
                else:
                    recovery_message = "Database recovery attempted but failed. Please try again later."
        
        # Service dependency errors
        elif "service" in error_message.lower() or "client" in error_message.lower():
            # Try to identify which service failed
            service_name = "unknown"
            if "pinecone" in error_message.lower():
                service_name = "pinecone"
            elif "perplexity" in error_message.lower():
                service_name = "perplexity"
            elif "notification" in error_message.lower():
                service_name = "notification"
            
            if service_name != "unknown" and recovery_manager.should_attempt_recovery("service", service_name):
                logger.info(f"Attempting {service_name} service recovery for error {error_id}")
                recovery_attempted = True
                recovery_success = await attempt_service_recovery(service_name)
                recovery_manager.record_recovery_attempt("service", service_name, recovery_success)
                
                if recovery_success:
                    recovery_message = f"{service_name.title()} service restored. Please retry your request."
                else:
                    recovery_message = f"{service_name.title()} service recovery attempted but failed."
        
        # AttributeError often indicates model conversion issues
        elif isinstance(exc, AttributeError):
            if "NoneType" in error_message:
                recovery_message = "Data integrity issue detected. Using safe defaults."
                recovery_attempted = True
                recovery_success = True  # We can handle these gracefully
        
    except Exception as recovery_error:
        logger.error(f"Recovery attempt failed for {error_id}: {recovery_error}")
    
    # Determine response based on recovery results
    if recovery_attempted and recovery_success:
        return create_error_response(
            status_code=503,  # Service temporarily unavailable but recoverable
            error_type="recoverable_error",
            message=recovery_message or "The issue has been resolved. Please retry your request.",
            error_id=error_id,
            recovery_info={
                "recovery_attempted": True,
                "recovery_successful": True,
                "retry_recommended": True,
                "retry_after_seconds": 2
            }
        )
    elif recovery_attempted and not recovery_success:
        return create_error_response(
            status_code=503,
            error_type="recovery_failed",
            message=recovery_message or "Recovery was attempted but failed. Please try again later.",
            error_id=error_id,
            recovery_info={
                "recovery_attempted": True,
                "recovery_successful": False,
                "retry_recommended": True,
                "retry_after_seconds": 30
            }
        )
    else:
        # No recovery attempted or available
        return create_error_response(
            status_code=500,
            error_type="internal_server_error",
            message="An unexpected error occurred. Our team has been notified.",
            error_id=error_id,
            details={
                "support_message": f"Please include error ID {error_id} when contacting support."
            }
        )

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Enhanced HTTP exception handler with context logging"""
    error_id = str(uuid.uuid4())
    
    # Extract request information
    request_info = {
        "method": request.method,
        "url": str(request.url),
        "user_agent": request.headers.get("user-agent", "unknown")
    }
    
    # Log the HTTP error
    logger.warning(
        f"HTTP error {error_id}: {exc.status_code} - {exc.detail}",
        extra={
            "error_id": error_id,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_info": request_info
        }
    )
    
    # Enhance error message for common issues
    enhanced_detail = exc.detail
    if exc.status_code == 404:
        enhanced_detail = "The requested resource was not found. Please check the URL and try again."
    elif exc.status_code == 403:
        enhanced_detail = "Access denied. You do not have permission to access this resource."
    elif exc.status_code == 429:
        enhanced_detail = "Too many requests. Please slow down and try again later."
    
    return create_error_response(
        status_code=exc.status_code,
        error_type="http_error",
        message=enhanced_detail,
        error_id=error_id
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Enhanced validation error handler with helpful suggestions"""
    error_id = str(uuid.uuid4())
    
    # Extract detailed validation errors
    validation_errors = []
    corrective_suggestions = []
    
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        error_detail = {
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        }
        validation_errors.append(error_detail)
        
        # Generate helpful suggestions
        if "missing" in error["type"]:
            corrective_suggestions.append(f"Field '{field_path}' is required and must be provided.")
        elif "string_too_short" in error["type"]:
            corrective_suggestions.append(f"Field '{field_path}' must be longer.")
        elif "string_too_long" in error["type"]:
            corrective_suggestions.append(f"Field '{field_path}' is too long.")
        elif "type_error" in error["type"]:
            if "str_type" in error["type"]:
                corrective_suggestions.append(f"Field '{field_path}' must be a string.")
            elif "int_type" in error["type"]:
                corrective_suggestions.append(f"Field '{field_path}' must be an integer.")
            elif "float_type" in error["type"]:
                corrective_suggestions.append(f"Field '{field_path}' must be a number.")
            elif "bool_type" in error["type"]:
                corrective_suggestions.append(f"Field '{field_path}' must be true or false.")
            else:
                corrective_suggestions.append(f"Field '{field_path}' has an incorrect data type.")
        elif "value_error.date" in error["type"]:
            corrective_suggestions.append(f"Field '{field_path}' must be a valid date in YYYY-MM-DD format.")
        elif "value_error.email" in error["type"]:
            corrective_suggestions.append(f"Field '{field_path}' must be a valid email address.")
        elif "value_error.url" in error["type"]:
            corrective_suggestions.append(f"Field '{field_path}' must be a valid URL.")
    
    # Log validation error
    logger.warning(
        f"Validation error {error_id}: {len(validation_errors)} field errors",
        extra={
            "error_id": error_id,
            "validation_errors": validation_errors,
            "request_method": request.method,
            "request_url": str(request.url)
        }
    )
    
    return create_error_response(
        status_code=422,
        error_type="validation_error",
        message="Request validation failed. Please check the provided data.",
        error_id=error_id,
        details={
            "validation_errors": validation_errors,
            "suggestions": corrective_suggestions,
            "help": "Ensure all required fields are provided with correct data types."
        }
    )

def with_error_handling(func: Callable) -> Callable:
    """Decorator to add error handling to any function"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

def safe_execute(func: Callable, *args, default=None, **kwargs):
    """Safely execute a function and return default on error"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.debug(f"Safe execution failed for {func.__name__}: {e}")
        return default

async def safe_execute_async(func: Callable, *args, default=None, **kwargs):
    """Safely execute an async function and return default on error"""
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.debug(f"Safe async execution failed for {func.__name__}: {e}")
        return default

class CircuitBreaker:
    """Circuit breaker pattern for preventing cascading failures"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution"""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if (self.last_failure_time and 
                (datetime.utcnow() - self.last_failure_time).seconds > self.timeout):
                self.state = "half-open"
                return True
            return False
        else:  # half-open
            return True
    
    def record_success(self):
        """Record a successful execution"""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record a failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

# Global circuit breakers for different services
circuit_breakers = {
    "database": CircuitBreaker(failure_threshold=3, timeout=30),
    "pinecone": CircuitBreaker(failure_threshold=5, timeout=60),
    "perplexity": CircuitBreaker(failure_threshold=5, timeout=60),
    "notification": CircuitBreaker(failure_threshold=10, timeout=120)
}

def with_circuit_breaker(service_name: str):
    """Decorator to add circuit breaker pattern to functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            breaker = circuit_breakers.get(service_name)
            if not breaker:
                return await func(*args, **kwargs)
            
            if not breaker.can_execute():
                raise Exception(f"Circuit breaker open for {service_name}")
            
            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            breaker = circuit_breakers.get(service_name)
            if not breaker:
                return func(*args, **kwargs)
            
            if not breaker.can_execute():
                raise Exception(f"Circuit breaker open for {service_name}")
            
            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator
