"""
Enhanced error handling and response utilities for API endpoints.
"""
import logging
from typing import Any, Dict, Optional, List
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class APIErrorHandler:
    """Centralized error handling for API endpoints"""
    
    @staticmethod
    def create_error_response(
        status_code: int,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        error_id: Optional[str] = None
    ) -> JSONResponse:
        """Create standardized error response"""
        
        if not error_id:
            error_id = str(uuid.uuid4())
        
        response_data: Dict[str, Any] = {
            "status": "error",
            "error_type": error_type,
            "error_id": error_id,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if details:
            response_data["details"] = details
            
        if suggestions:
            response_data["suggestions"] = suggestions
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
    
    @staticmethod
    def handle_database_error(e: Exception, operation: str = "database operation") -> JSONResponse:
        """Handle database-related errors"""
        error_id = str(uuid.uuid4())
        logger.error(f"Database error {error_id} during {operation}: {e}", exc_info=True)
        
        return APIErrorHandler.create_error_response(
            status_code=500,
            error_type="database_error",
            message=f"Database error occurred during {operation}",
            details={"operation": operation},
            suggestions=["Please try again later", "Contact support if the problem persists"],
            error_id=error_id
        )
    
    @staticmethod
    def handle_service_unavailable_error(service_name: str, operation: str = "") -> JSONResponse:
        """Handle service unavailable errors"""
        error_id = str(uuid.uuid4())
        logger.warning(f"Service unavailable {error_id}: {service_name} for {operation}")
        
        return APIErrorHandler.create_error_response(
            status_code=503,
            error_type="service_unavailable",
            message=f"{service_name} service is temporarily unavailable",
            details={
                "service": service_name,
                "operation": operation
            },
            suggestions=[
                "The service may be starting up or experiencing temporary issues",
                "Please try again in a few moments",
                "Core functionality may still be available"
            ],
            error_id=error_id
        )
    
    @staticmethod
    def handle_validation_error(errors: List[Dict], operation: str = "") -> JSONResponse:
        """Handle validation errors"""
        error_id = str(uuid.uuid4())
        logger.warning(f"Validation error {error_id} during {operation}: {len(errors)} errors")
        
        # Extract suggestions from validation errors
        suggestions = []
        for error in errors:
            if "missing" in error.get("type", ""):
                suggestions.append(f"Field '{error.get('field', 'unknown')}' is required")
            elif "type_error" in error.get("type", ""):
                suggestions.append(f"Field '{error.get('field', 'unknown')}' has incorrect data type")
            elif "value_error" in error.get("type", ""):
                suggestions.append(f"Field '{error.get('field', 'unknown')}' has invalid value")
        
        return APIErrorHandler.create_error_response(
            status_code=422,
            error_type="validation_error",
            message="Request validation failed",
            details={
                "validation_errors": errors,
                "error_count": len(errors)
            },
            suggestions=suggestions if suggestions else ["Please check all required fields and data types"],
            error_id=error_id
        )
    
    @staticmethod
    def handle_not_found_error(resource: str, identifier: str = "") -> JSONResponse:
        """Handle resource not found errors"""
        error_id = str(uuid.uuid4())
        logger.info(f"Resource not found {error_id}: {resource} {identifier}")
        
        return APIErrorHandler.create_error_response(
            status_code=404,
            error_type="not_found",
            message=f"{resource} not found",
            details={
                "resource": resource,
                "identifier": identifier
            },
            suggestions=[
                "Check the resource identifier",
                "Ensure the resource exists",
                "Verify your request parameters"
            ],
            error_id=error_id
        )

class APIResponseBuilder:
    """Utilities for building standardized API responses"""
    
    @staticmethod
    def success_response(
        data: Any,
        message: str = "Success",
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build standardized success response"""
        response = {
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if meta:
            response["meta"] = meta
            
        return response
    
    @staticmethod
    def paginated_response(
        data: List[Any],
        total: int,
        page: int,
        page_size: int,
        message: str = "Success"
    ) -> Dict[str, Any]:
        """Build paginated response"""
        total_pages = (total + page_size - 1) // page_size
        
        return APIResponseBuilder.success_response(
            data=data,
            message=message,
            meta={
                "pagination": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        )

def handle_api_exceptions(func):
    """Decorator for consistent API exception handling"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            # Convert unexpected exceptions to HTTP 500
            error_id = str(uuid.uuid4())
            logger.error(f"Unexpected error {error_id} in {func.__name__}: {e}", exc_info=True)
            
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal server error",
                    "error_id": error_id,
                    "message": "An unexpected error occurred",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    return wrapper
