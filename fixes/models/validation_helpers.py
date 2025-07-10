"""
Validation helpers for safe data handling and schema validation.
"""

import logging
from typing import Any, Dict, List, Optional, Union, Type, get_type_hints
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, ValidationError
import json

logger = logging.getLogger(__name__)


def safe_get_attribute(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute from object with default fallback."""
    if obj is None:
        return default
    return getattr(obj, attr, default)


def safe_get_nested_attribute(obj: Any, attr_path: str, default: Any = None) -> Any:
    """Safely get nested attribute using dot notation."""
    if obj is None:
        return default
    
    try:
        attrs = attr_path.split('.')
        current = obj
        for attr in attrs:
            if current is None:
                return default
            current = getattr(current, attr, None)
        return current if current is not None else default
    except (AttributeError, TypeError):
        return default


def safe_parse_json(json_str: Union[str, dict, list, None], default: Any = None) -> Any:
    """Safely parse JSON string with fallback to default."""
    if json_str is None:
        return default
    
    if isinstance(json_str, (dict, list)):
        return json_str
    
    if not isinstance(json_str, str):
        return default
    
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Failed to parse JSON: {json_str}")
        return default


def safe_convert_to_dict(obj: Any, default: Optional[Dict] = None) -> Dict[str, Any]:
    """Safely convert object to dictionary."""
    if default is None:
        default = {}
    
    if obj is None:
        return default
    
    if isinstance(obj, dict):
        return obj
    
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    
    if hasattr(obj, 'dict') and callable(obj.dict):
        try:
            result = obj.dict()
            return result if isinstance(result, dict) else default
        except Exception:
            pass
    
    return default


def safe_convert_datetime(value: Any, default: Optional[datetime] = None) -> Optional[datetime]:
    """Safely convert various datetime formats."""
    if value is None:
        return default
    
    if isinstance(value, datetime):
        return value
    
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    
    if isinstance(value, str):
        try:
            # Try ISO format first
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            try:
                # Try parsing common formats
                from dateutil.parser import parse
                return parse(value)
            except (ValueError, ImportError):
                logger.warning(f"Failed to parse datetime: {value}")
                return default
    
    return default


def safe_convert_number(value: Any, number_type: Type = int, default: Any = 0) -> Union[int, float, Decimal]:
    """Safely convert value to number type."""
    if value is None:
        return default
    
    if isinstance(value, number_type):
        return value
    
    try:
        if number_type == int:
            if isinstance(value, str):
                # Handle float strings
                return int(float(value))
            return int(value)
        elif number_type == float:
            return float(value)
        elif number_type == Decimal:
            return Decimal(str(value))
        else:
            return number_type(value)
    except (ValueError, TypeError, OverflowError):
        logger.warning(f"Failed to convert {value} to {number_type.__name__}")
        return default


def safe_convert_bool(value: Any, default: bool = False) -> bool:
    """Safely convert value to boolean."""
    if value is None:
        return default
    
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    if isinstance(value, (int, float)):
        return bool(value)
    
    return default


def safe_convert_list(value: Any, default: Optional[List] = None) -> List[Any]:
    """Safely convert value to list."""
    if default is None:
        default = []
    
    if value is None:
        return default
    
    if isinstance(value, list):
        return value
    
    if isinstance(value, (tuple, set)):
        return list(value)
    
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    
    return default


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """Validate that required fields are present and not None."""
    errors = {}
    
    for field in required_fields:
        if field not in data:
            errors[field] = "Field is required"
        elif data[field] is None:
            errors[field] = "Field cannot be None"
    
    return errors


def validate_email(email: str) -> bool:
    """Basic email validation."""
    if not email or not isinstance(email, str):
        return False
    
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_url(url: str) -> bool:
    """Basic URL validation."""
    if not url or not isinstance(url, str):
        return False
    
    import re
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return re.match(pattern, url) is not None


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """Sanitize string input."""
    if not isinstance(value, str):
        return str(value) if value is not None else ""
    
    # Remove control characters
    sanitized = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
    
    # Truncate if needed
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()


def safe_pydantic_conversion(data: Dict[str, Any], model_class: Type[BaseModel], 
                           strict: bool = False) -> Optional[BaseModel]:
    """Safely convert dictionary to Pydantic model."""
    if not data:
        return None
    
    try:
        # Try direct conversion first
        return model_class(**data)
    except ValidationError as e:
        if strict:
            logger.error(f"Pydantic validation failed for {model_class.__name__}: {e}")
            raise
        
        # Try to fix common issues
        cleaned_data = {}
        model_fields = get_type_hints(model_class)
        
        for field_name, field_value in data.items():
            if field_name in model_fields:
                field_type = model_fields[field_name]
                
                # Handle Optional types
                if hasattr(field_type, '__origin__') and field_type.__origin__ is Union:
                    args = field_type.__args__
                    if len(args) == 2 and type(None) in args:
                        # This is Optional[T]
                        field_type = args[0] if args[1] is type(None) else args[1]
                
                # Apply safe conversions based on type
                if field_type == str:
                    cleaned_data[field_name] = sanitize_string(field_value) if field_value else None
                elif field_type == int:
                    cleaned_data[field_name] = safe_convert_number(field_value, int)
                elif field_type == float:
                    cleaned_data[field_name] = safe_convert_number(field_value, float)
                elif field_type == bool:
                    cleaned_data[field_name] = safe_convert_bool(field_value)
                elif field_type == datetime:
                    cleaned_data[field_name] = safe_convert_datetime(field_value)
                elif field_type == list:
                    cleaned_data[field_name] = safe_convert_list(field_value)
                elif field_type == dict:
                    cleaned_data[field_name] = safe_convert_to_dict(field_value)
                else:
                    cleaned_data[field_name] = field_value
            else:
                # Include extra fields as-is
                cleaned_data[field_name] = field_value
        
        try:
            return model_class(**cleaned_data)
        except ValidationError as e:
            logger.error(f"Pydantic validation failed after cleaning for {model_class.__name__}: {e}")
            return None
    except Exception as e:
        logger.error(f"Unexpected error in Pydantic conversion: {e}")
        return None


def create_error_response(message: str, error_code: str = "validation_error", 
                         details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create standardized error response."""
    return {
        "error": error_code,
        "message": message,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat()
    }


def validate_pagination_params(page: int, page_size: int) -> Dict[str, Any]:
    """Validate pagination parameters."""
    errors = {}
    
    if page < 1:
        errors["page"] = "Page number must be greater than 0"
    
    if page_size < 1:
        errors["page_size"] = "Page size must be greater than 0"
    elif page_size > 100:
        errors["page_size"] = "Page size cannot exceed 100"
    
    return errors


def safe_extract_enum_value(value: Any, enum_class: Type, default: Any = None) -> Any:
    """Safely extract enum value."""
    if value is None:
        return default
    
    if isinstance(value, enum_class):
        return value
    
    try:
        # Try by value
        return enum_class(value)
    except (ValueError, TypeError):
        try:
            # Try by name
            if hasattr(enum_class, '__members__'):
                return enum_class.__members__[str(value).upper()]
            return getattr(enum_class, str(value).upper())
        except (KeyError, AttributeError):
            logger.warning(f"Failed to convert {value} to {enum_class.__name__}")
            return default


class ValidationResult:
    """Result of validation operation."""
    
    def __init__(self, is_valid: bool, errors: Optional[Dict[str, Any]] = None, 
                 warnings: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors = errors or {}
        self.warnings = warnings or []
    
    def add_error(self, field: str, message: str):
        """Add validation error."""
        self.errors[field] = message
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add validation warning."""
        self.warnings.append(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings
        }
