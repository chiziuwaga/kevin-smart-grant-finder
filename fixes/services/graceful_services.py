"""
Graceful service initialization and management with fallback capabilities.
Ensures the application can start and function even when some services fail.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Union, Type
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from fixes.services.fallback_clients import (
    FallbackPineconeClient,
    FallbackDeepSeekClient,
    FallbackNotificationManager,
    FallbackResearchAgent,
    FallbackAnalysisAgent,
    FallbackConfig
)

# Import actual service classes
try:
    from utils.pgvector_client import PgVectorClient as PineconeClient  # Compat alias
    from services.deepseek_client import DeepSeekClient
    from services.resend_client import ResendEmailClient
    from agents.integrated_research_agent import IntegratedResearchAgent
    from agents.analysis_agent import AnalysisAgent
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import service classes: {e}")

logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    """Service status enumeration"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    FALLBACK = "fallback"

@dataclass
class ServiceHealth:
    """Track service health and status"""
    status: ServiceStatus = ServiceStatus.UNINITIALIZED
    last_check: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None
    initialization_attempts: int = 0
    fallback_active: bool = False
    response_times: list = field(default_factory=list)
    is_fallback: bool = False
    uptime_seconds: int = 0
    
    def add_response_time(self, response_time: float):
        """Add response time measurement"""
        self.response_times.append(response_time)
        if len(self.response_times) > 50:  # Keep last 50 measurements
            self.response_times.pop(0)
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time"""
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0.0

@dataclass
class ServiceConfig:
    """Configuration for service initialization"""
    max_retry_attempts: int = 3
    retry_delay: float = 2.0
    timeout: float = 30.0
    enable_fallback: bool = True
    required_for_startup: bool = False
    health_check_interval: float = 300.0  # 5 minutes

class GracefulServiceManager:
    """
    Manages service initialization with graceful degradation.
    Allows the application to start even when some services fail.
    """
    
    def __init__(self, fallback_config: Optional[FallbackConfig] = None):
        self.fallback_config = fallback_config or FallbackConfig()
        self.services: Dict[str, Any] = {}
        self.service_health: Dict[str, ServiceHealth] = {}
        self.service_configs: Dict[str, ServiceConfig] = {}
        self.initialization_complete = False
        self.startup_time = None
        
        # Define service configurations
        self._setup_service_configs()
        
    def _setup_service_configs(self):
        """Setup configurations for different services"""
        self.service_configs = {
            "database": ServiceConfig(
                max_retry_attempts=5,
                retry_delay=1.0,
                timeout=30.0,
                enable_fallback=False,  # Database is critical
                required_for_startup=True,
                health_check_interval=60.0
            ),
            "pinecone": ServiceConfig(
                max_retry_attempts=3,
                retry_delay=2.0,
                timeout=30.0,
                enable_fallback=True,
                required_for_startup=False,
                health_check_interval=300.0
            ),
            "perplexity": ServiceConfig(
                max_retry_attempts=3,
                retry_delay=2.0,
                timeout=30.0,
                enable_fallback=True,
                required_for_startup=False,
                health_check_interval=300.0
            ),
            "notification": ServiceConfig(
                max_retry_attempts=2,
                retry_delay=1.0,
                timeout=10.0,
                enable_fallback=True,
                required_for_startup=False,
                health_check_interval=600.0
            ),
            "research_agent": ServiceConfig(
                max_retry_attempts=3,
                retry_delay=2.0,
                timeout=30.0,
                enable_fallback=True,
                required_for_startup=False,
                health_check_interval=300.0
            ),
            "analysis_agent": ServiceConfig(
                max_retry_attempts=3,
                retry_delay=2.0,
                timeout=30.0,
                enable_fallback=True,
                required_for_startup=False,
                health_check_interval=300.0
            )
        }
        
        # Initialize health tracking
        for service_name in self.service_configs:
            self.service_health[service_name] = ServiceHealth()
    
    async def initialize_all_services(self, settings) -> Dict[str, bool]:
        """
        Initialize all services with graceful degradation.
        Returns dict of service_name -> success status.
        """
        logger.info("Starting graceful service initialization...")
        self.startup_time = time.time()
        
        # Import database manager
        from fixes.database.robust_connection_manager import get_connection_manager
        
        initialization_results = {}
        critical_failures = []
        
        # Initialize database first (critical service)
        try:
            db_manager = await get_connection_manager()
            if db_manager.is_initialized:
                self.services["database"] = db_manager
                self.service_health["database"].status = ServiceStatus.HEALTHY
                initialization_results["database"] = True
                logger.info("Database initialized successfully")
            else:
                raise RuntimeError("Database initialization failed")
        except Exception as e:
            logger.error(f"Critical database initialization failed: {e}")
            self.service_health["database"].status = ServiceStatus.FAILED
            self.service_health["database"].last_error = str(e)
            initialization_results["database"] = False
            critical_failures.append("database")
        
        # Initialize other services concurrently
        service_tasks = []
        non_critical_services = ["pinecone", "perplexity", "notification", "research_agent", "analysis_agent"]
        
        for service_name in non_critical_services:
            task = asyncio.create_task(
                self._initialize_service(service_name, settings),
                name=f"init_{service_name}"
            )
            service_tasks.append((service_name, task))
        
        # Wait for all service initialization attempts
        for service_name, task in service_tasks:
            try:
                success = await task
                initialization_results[service_name] = success
                if success:
                    logger.info(f"Service {service_name} initialized successfully")
                else:
                    logger.warning(f"Service {service_name} failed to initialize, using fallback")
            except Exception as e:
                logger.error(f"Unexpected error initializing {service_name}: {e}")
                initialization_results[service_name] = False
        
        # Check if we can proceed with startup
        if critical_failures:
            logger.critical(f"Critical services failed: {critical_failures}")
            raise RuntimeError(f"Cannot start application - critical services failed: {critical_failures}")
        
        # Log final initialization status
        successful_services = [k for k, v in initialization_results.items() if v]
        failed_services = [k for k, v in initialization_results.items() if not v]
        
        logger.info(f"Service initialization complete - Success: {len(successful_services)}, Failed: {len(failed_services)}")
        if failed_services:
            logger.warning(f"Services using fallback: {failed_services}")
        
        self.initialization_complete = True
        return initialization_results
    
    async def _initialize_service(self, service_name: str, settings) -> bool:
        """Initialize a single service with retry logic"""
        config = self.service_configs[service_name]
        health = self.service_health[service_name]
        
        health.status = ServiceStatus.INITIALIZING
        
        for attempt in range(1, config.max_retry_attempts + 1):
            health.initialization_attempts += 1
            
            try:
                logger.info(f"Initializing {service_name} (attempt {attempt}/{config.max_retry_attempts})")
                
                # Try to initialize the actual service
                service_instance = await self._create_service_instance(service_name, settings)
                
                if service_instance:
                    self.services[service_name] = service_instance
                    health.status = ServiceStatus.HEALTHY
                    health.last_check = datetime.utcnow()
                    logger.info(f"Service {service_name} initialized successfully")
                    return True
                else:
                    raise RuntimeError(f"Failed to create {service_name} instance")
                    
            except Exception as e:
                health.error_count += 1
                health.last_error = str(e)
                logger.error(f"Service {service_name} initialization attempt {attempt} failed: {e}")
                
                if attempt < config.max_retry_attempts:
                    delay = config.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"Retrying {service_name} initialization in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {service_name} initialization attempts failed")
        
        # If we get here, initialization failed - try fallback
        if config.enable_fallback:
            try:
                fallback_service = await self._create_fallback_service(service_name)
                self.services[service_name] = fallback_service
                health.status = ServiceStatus.FALLBACK
                health.fallback_active = True
                health.last_check = datetime.utcnow()
                logger.info(f"Service {service_name} using fallback implementation")
                return True
            except Exception as e:
                logger.error(f"Failed to create fallback for {service_name}: {e}")
        
        # Complete failure
        health.status = ServiceStatus.FAILED
        return False
    
    async def _create_service_instance(self, service_name: str, settings) -> Optional[Any]:
        """Create actual service instance"""
        try:
            if service_name == "pinecone":
                return PineconeClient()
            elif service_name == "deepseek":
                from services.deepseek_client import DeepSeekClient
                return DeepSeekClient()
            elif service_name == "notification":
                from services.resend_client import ResendEmailClient
                return ResendEmailClient()
            elif service_name == "research_agent":
                # Create research agent with proper dependencies
                if "pinecone" in self.services and "deepseek" in self.services:
                    return IntegratedResearchAgent(
                        db_session_maker=self.services["database"].sessionmaker
                    )
                else:
                    logger.warning("Dependencies not available for ResearchAgent")
                    return None
            elif service_name == "analysis_agent":
                if "pinecone" in self.services:
                    return AnalysisAgent(
                        db_sessionmaker=self.services["database"].sessionmaker,
                        pinecone_client=self.services["pinecone"]
                    )
                else:
                    logger.warning("Dependencies not available for AnalysisAgent")
                    return None
            else:
                logger.error(f"Unknown service name: {service_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating {service_name} instance: {e}")
            return None
    
    async def _create_fallback_service(self, service_name: str) -> Any:
        """Create fallback service instance"""
        if service_name == "pinecone":
            return FallbackPineconeClient(self.fallback_config)
        elif service_name == "deepseek":
            return FallbackDeepSeekClient(self.fallback_config)
        elif service_name == "notification":
            return FallbackNotificationManager(self.fallback_config)
        elif service_name == "research_agent":
            return FallbackResearchAgent(self.fallback_config)
        elif service_name == "analysis_agent":
            return FallbackAnalysisAgent(self.fallback_config)
        else:
            raise ValueError(f"No fallback available for service: {service_name}")
    
    async def get_service_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all services"""
        statuses = {}
        
        for service_name, health in self.service_health.items():
            service_info = {
                "status": health.status.value,
                "last_check": health.last_check.isoformat() if health.last_check else None,
                "error_count": health.error_count,
                "last_error": health.last_error,
                "is_fallback": health.is_fallback,
                "uptime": health.uptime_seconds
            }
            
            # Add service-specific info
            if service_name in self.services:
                service = self.services[service_name]
                if hasattr(service, 'is_mock') and service.is_mock:
                    service_info["mode"] = "mock"
                elif hasattr(service, 'is_fallback') and service.is_fallback:
                    service_info["mode"] = "fallback"
                else:
                    service_info["mode"] = "normal"
            
            statuses[service_name] = service_info
        
        return statuses
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """Get service instance"""
        return self.services.get(service_name)
    
    async def restart_services(self) -> Dict[str, bool]:
        """Restart all services"""
        results = {}
        
        for service_name in self.services:
            try:
                logger.info(f"Restarting service: {service_name}")
                
                # Clean up existing service
                if service_name in self.services:
                    old_service = self.services[service_name]
                    if hasattr(old_service, 'cleanup'):
                        await old_service.cleanup()
                
                # Re-initialize service
                success = await self._initialize_service(service_name, self.fallback_config)
                results[service_name] = success
                
                if success:
                    logger.info(f"Service {service_name} restarted successfully")
                else:
                    logger.warning(f"Service {service_name} restart failed")
                    
            except Exception as e:
                logger.error(f"Error restarting service {service_name}: {e}")
                results[service_name] = False
        
        return results
    
    def is_initialized(self) -> bool:
        """Check if service manager initialization is complete"""
        return self.initialization_complete
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""
        statuses = await self.get_service_statuses()
        
        total_services = len(statuses)
        healthy_count = sum(1 for s in statuses.values() if s["status"] == "healthy")
        degraded_count = sum(1 for s in statuses.values() if s["status"] == "degraded")
        failed_count = sum(1 for s in statuses.values() if s["status"] == "failed")
        fallback_count = sum(1 for s in statuses.values() if s["status"] == "fallback")
        
        return {
            "total_services": total_services,
            "healthy": healthy_count,
            "degraded": degraded_count,
            "failed": failed_count,
            "fallback": fallback_count,
            "health_ratio": healthy_count / total_services if total_services > 0 else 0.0,
            "initialization_complete": self.initialization_complete,
            "startup_time": datetime.fromtimestamp(self.startup_time).isoformat() if self.startup_time else None,
            "services": statuses
        }
    
    async def cleanup_services(self):
        """Clean up all services"""
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'cleanup'):
                    await service.cleanup()
                logger.info(f"Cleaned up service: {service_name}")
            except Exception as e:
                logger.error(f"Error cleaning up service {service_name}: {e}")
        
        self.services.clear()
        self.initialization_complete = False
        logger.info("All services cleaned up")
        
    # ...existing methods...

# Global service manager instance
_service_manager: Optional[GracefulServiceManager] = None

async def get_service_manager() -> GracefulServiceManager:
    """Get or create global service manager"""
    global _service_manager
    
    if _service_manager is None:
        _service_manager = GracefulServiceManager()
    
    return _service_manager

async def initialize_services(settings) -> Dict[str, bool]:
    """Initialize all services with graceful degradation"""
    manager = await get_service_manager()
    return await manager.initialize_all_services(settings)

def get_service(service_name: str) -> Optional[Any]:
    """Get service instance (synchronous)"""
    global _service_manager
    
    if _service_manager is None:
        logger.warning(f"Service manager not initialized, cannot get {service_name}")
        return None
    
    return _service_manager.get_service(service_name)

async def cleanup_all_services():
    """Clean up all services"""
    global _service_manager
    
    if _service_manager:
        await _service_manager.cleanup_services()
        _service_manager = None
