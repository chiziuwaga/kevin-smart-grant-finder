"""
Circuit breaker pattern implementation for service reliability.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5      # Number of failures before opening
    recovery_timeout: int = 60      # Seconds before trying half-open
    success_threshold: int = 3      # Successes needed to close from half-open
    timeout: int = 30              # Request timeout in seconds


class CircuitBreaker:
    """Circuit breaker implementation for service resilience."""
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.half_open_start_time = None
        
    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._move_to_half_open()
            else:
                raise CircuitBreakerOpenException(f"Circuit breaker {self.name} is open")
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs), 
                timeout=self.config.timeout
            )
            await self._on_success()
            return result
            
        except asyncio.TimeoutError:
            await self._on_failure("timeout")
            raise
        except Exception as e:
            await self._on_failure(str(e))
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset from open state."""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout
    
    def _move_to_half_open(self):
        """Move circuit breaker to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.half_open_start_time = datetime.utcnow()
        self.success_count = 0
        logger.info(f"Circuit breaker {self.name} moved to HALF_OPEN state")
    
    async def _on_success(self):
        """Handle successful execution."""
        self.last_success_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._move_to_closed()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0  # Reset failure count on success
    
    async def _on_failure(self, error: str):
        """Handle failed execution."""
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.config.failure_threshold:
                self._move_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            self._move_to_open()
        
        logger.warning(f"Circuit breaker {self.name} failure: {error}")
    
    def _move_to_open(self):
        """Move circuit breaker to open state."""
        self.state = CircuitState.OPEN
        self.failure_count = 0
        self.success_count = 0
        logger.error(f"Circuit breaker {self.name} moved to OPEN state")
    
    def _move_to_closed(self):
        """Move circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        logger.info(f"Circuit breaker {self.name} moved to CLOSED state")
    
    def get_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self.state
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout
            }
        }
    
    def reset(self):
        """Reset circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.half_open_start_time = None
        logger.info(f"Circuit breaker {self.name} reset to CLOSED state")


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def get_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        return self.circuit_breakers[name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {
            name: cb.get_stats() 
            for name, cb in self.circuit_breakers.items()
        }
    
    def reset_all(self):
        """Reset all circuit breakers."""
        for cb in self.circuit_breakers.values():
            cb.reset()
        logger.info("All circuit breakers reset")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all circuit breakers."""
        stats = self.get_all_stats()
        
        total_count = len(stats)
        open_count = sum(1 for s in stats.values() if s["state"] == "open")
        half_open_count = sum(1 for s in stats.values() if s["state"] == "half_open")
        closed_count = sum(1 for s in stats.values() if s["state"] == "closed")
        
        return {
            "total_circuit_breakers": total_count,
            "open": open_count,
            "half_open": half_open_count,
            "closed": closed_count,
            "health_ratio": closed_count / total_count if total_count > 0 else 1.0,
            "circuit_breakers": stats
        }


# Global circuit breaker manager
_circuit_manager = None


def get_circuit_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager."""
    global _circuit_manager
    if _circuit_manager is None:
        _circuit_manager = CircuitBreakerManager()
    return _circuit_manager


def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator for applying circuit breaker to functions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            manager = get_circuit_manager()
            cb = manager.get_circuit_breaker(name, config)
            return await cb.call(func, *args, **kwargs)
        return wrapper
    return decorator


# Predefined circuit breaker configurations
CIRCUIT_BREAKER_CONFIGS = {
    "database": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=30,
        success_threshold=2,
        timeout=10
    ),
    "pinecone": CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60,
        success_threshold=3,
        timeout=30
    ),
    "perplexity": CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60,
        success_threshold=3,
        timeout=45
    ),
    "notification": CircuitBreakerConfig(
        failure_threshold=10,
        recovery_timeout=120,
        success_threshold=5,
        timeout=30
    )
}
