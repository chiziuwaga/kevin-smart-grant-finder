"""
Error recovery strategies for resilient application behavior.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Awaitable, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Available recovery strategies."""
    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAKER = "circuit_breaker"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    CACHE_FALLBACK = "cache_fallback"


@dataclass
class RecoveryConfig:
    """Configuration for recovery strategies."""
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_retry_delay: float = 60.0
    timeout: float = 30.0
    enable_fallback: bool = True
    cache_duration: int = 300  # seconds


class RecoveryHandler(ABC):
    """Abstract base class for recovery handlers."""
    
    @abstractmethod
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Handle error and attempt recovery."""
        pass
    
    @abstractmethod
    def can_handle(self, error: Exception) -> bool:
        """Check if this handler can handle the error."""
        pass


class RetryHandler(RecoveryHandler):
    """Handler that implements retry logic with exponential backoff."""
    
    def __init__(self, config: RecoveryConfig):
        self.config = config
    
    def can_handle(self, error: Exception) -> bool:
        """Check if error is retryable."""
        retryable_errors = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
            OSError
        )
        return isinstance(error, retryable_errors)
    
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Handle error with retry logic."""
        func = context.get('function')
        args = context.get('args', ())
        kwargs = context.get('kwargs', {})
        attempt = context.get('attempt', 0)
        
        if not func or attempt >= self.config.max_retries:
            raise error
        
        # Calculate delay with exponential backoff
        delay = min(
            self.config.retry_delay * (self.config.backoff_multiplier ** attempt),
            self.config.max_retry_delay
        )
        
        logger.warning(f"Retrying after {delay}s (attempt {attempt + 1}/{self.config.max_retries}): {error}")
        await asyncio.sleep(delay)
        
        # Update context for next attempt
        context['attempt'] = attempt + 1
        
        try:
            return await func(*args, **kwargs)
        except Exception as retry_error:
            return await self.handle_error(retry_error, context)


class FallbackHandler(RecoveryHandler):
    """Handler that provides fallback responses."""
    
    def __init__(self, fallback_data: Dict[str, Any]):
        self.fallback_data = fallback_data
    
    def can_handle(self, error: Exception) -> bool:
        """Always can provide fallback."""
        return True
    
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Handle error with fallback data."""
        operation_name = context.get('operation_name', 'unknown')
        
        if operation_name in self.fallback_data:
            fallback_response = self.fallback_data[operation_name]
            logger.warning(f"Using fallback data for {operation_name}: {error}")
            return fallback_response
        
        # Generic fallback
        logger.error(f"No specific fallback for {operation_name}, using generic: {error}")
        return {
            "error": "service_unavailable",
            "message": "Service temporarily unavailable, please try again later",
            "fallback": True,
            "timestamp": datetime.utcnow().isoformat()
        }


class GracefulDegradationHandler(RecoveryHandler):
    """Handler that gracefully degrades service functionality."""
    
    def __init__(self, degradation_map: Dict[str, Callable]):
        self.degradation_map = degradation_map
    
    def can_handle(self, error: Exception) -> bool:
        """Check if degradation is available."""
        return True
    
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Handle error with graceful degradation."""
        operation_name = context.get('operation_name', 'unknown')
        
        if operation_name in self.degradation_map:
            degraded_func = self.degradation_map[operation_name]
            logger.warning(f"Using degraded functionality for {operation_name}: {error}")
            
            try:
                if asyncio.iscoroutinefunction(degraded_func):
                    return await degraded_func(context)
                else:
                    return degraded_func(context)
            except Exception as degraded_error:
                logger.error(f"Degraded function also failed: {degraded_error}")
                raise error
        
        raise error


class CacheFallbackHandler(RecoveryHandler):
    """Handler that uses cached responses as fallback."""
    
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
    
    def can_handle(self, error: Exception) -> bool:
        """Check if cached data is available."""
        return self.cache_manager is not None
    
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Handle error with cached fallback."""
        cache_key = context.get('cache_key')
        
        if cache_key:
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                logger.warning(f"Using cached data for {cache_key}: {error}")
                return cached_data
        
        raise error


class RecoveryManager:
    """Manages error recovery strategies."""
    
    def __init__(self, config: Optional[RecoveryConfig] = None):
        self.config = config or RecoveryConfig()
        self.handlers: List[RecoveryHandler] = []
        self.recovery_stats = {
            'total_errors': 0,
            'recovered_errors': 0,
            'failed_recoveries': 0,
            'recovery_methods': {}
        }
    
    def add_handler(self, handler: RecoveryHandler):
        """Add a recovery handler."""
        self.handlers.append(handler)
    
    def setup_default_handlers(self):
        """Setup default recovery handlers."""
        # Retry handler
        retry_handler = RetryHandler(self.config)
        self.add_handler(retry_handler)
        
        # Fallback handler with common fallback responses
        fallback_data = {
            'search_grants': {
                'grants': [],
                'total': 0,
                'message': 'Search service temporarily unavailable',
                'fallback': True
            },
            'analyze_grant': {
                'analysis': {
                    'research_context_scores': {},
                    'compliance_scores': {},
                    'overall_score': 0.0
                },
                'message': 'Analysis service temporarily unavailable',
                'fallback': True
            },
            'get_grants': {
                'grants': [],
                'total': 0,
                'message': 'Database temporarily unavailable',
                'fallback': True
            }
        }
        
        fallback_handler = FallbackHandler(fallback_data)
        self.add_handler(fallback_handler)
    
    async def recover_from_error(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Attempt to recover from error using registered handlers."""
        self.recovery_stats['total_errors'] += 1
        
        for handler in self.handlers:
            if handler.can_handle(error):
                try:
                    result = await handler.handle_error(error, context)
                    self.recovery_stats['recovered_errors'] += 1
                    
                    # Track recovery method
                    handler_name = handler.__class__.__name__
                    self.recovery_stats['recovery_methods'][handler_name] = \
                        self.recovery_stats['recovery_methods'].get(handler_name, 0) + 1
                    
                    return result
                except Exception as recovery_error:
                    logger.error(f"Recovery handler {handler.__class__.__name__} failed: {recovery_error}")
                    continue
        
        # No handler could recover
        self.recovery_stats['failed_recoveries'] += 1
        raise error
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        total = self.recovery_stats['total_errors']
        recovered = self.recovery_stats['recovered_errors']
        
        return {
            'total_errors': total,
            'recovered_errors': recovered,
            'failed_recoveries': self.recovery_stats['failed_recoveries'],
            'recovery_rate': recovered / total if total > 0 else 0.0,
            'recovery_methods': self.recovery_stats['recovery_methods']
        }


def with_recovery(operation_name: str, config: Optional[RecoveryConfig] = None,
                 recovery_manager: Optional[RecoveryManager] = None):
    """Decorator for adding recovery to functions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not recovery_manager:
                manager = RecoveryManager(config)
                manager.setup_default_handlers()
            else:
                manager = recovery_manager
            
            context = {
                'function': func,
                'args': args,
                'kwargs': kwargs,
                'operation_name': operation_name,
                'attempt': 0,
                'cache_key': f"{operation_name}_{hash(str(args) + str(kwargs))}"
            }
            
            try:
                return await func(*args, **kwargs)
            except Exception as error:
                return await manager.recover_from_error(error, context)
        
        return wrapper
    return decorator


# Database recovery strategies
async def database_recovery_strategy(context: Dict[str, Any]) -> Dict[str, Any]:
    """Recovery strategy for database operations."""
    operation = context.get('operation_name', 'unknown')
    
    if operation == 'get_grants':
        return {
            'grants': [],
            'total': 0,
            'message': 'Database temporarily unavailable. Please try again in a few minutes.',
            'fallback': True
        }
    elif operation == 'create_grant':
        return {
            'id': None,
            'message': 'Grant creation temporarily unavailable. Please try again later.',
            'fallback': True
        }
    elif operation == 'update_grant':
        return {
            'success': False,
            'message': 'Grant update temporarily unavailable. Please try again later.',
            'fallback': True
        }
    else:
        return {
            'error': 'database_unavailable',
            'message': 'Database service temporarily unavailable',
            'fallback': True
        }


# Service recovery strategies
async def service_recovery_strategy(context: Dict[str, Any]) -> Dict[str, Any]:
    """Recovery strategy for external service operations."""
    operation = context.get('operation_name', 'unknown')
    
    if operation == 'search_grants':
        return {
            'grants': [],
            'total': 0,
            'message': 'Search service temporarily unavailable. Using local data.',
            'fallback': True
        }
    elif operation == 'analyze_grant':
        return {
            'analysis': {
                'research_context_scores': {
                    'funding_alignment': 0.5,
                    'technical_feasibility': 0.5,
                    'competitive_advantage': 0.5
                },
                'compliance_scores': {
                    'eligibility_match': 0.5,
                    'requirement_coverage': 0.5,
                    'deadline_feasibility': 0.5
                },
                'overall_score': 0.5
            },
            'message': 'Analysis service temporarily unavailable. Using default analysis.',
            'fallback': True
        }
    else:
        return {
            'error': 'service_unavailable',
            'message': 'External service temporarily unavailable',
            'fallback': True
        }


# Global recovery manager
_global_recovery_manager = None


def get_recovery_manager() -> RecoveryManager:
    """Get global recovery manager."""
    global _global_recovery_manager
    if _global_recovery_manager is None:
        _global_recovery_manager = RecoveryManager()
        _global_recovery_manager.setup_default_handlers()
    return _global_recovery_manager
