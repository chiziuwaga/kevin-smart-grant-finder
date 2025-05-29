import logging
import os
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Dict, Any

class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs JSON structured logs"""
    def format(self, record: logging.LogRecord) -> str:
        # Basic log entry
        log_entry: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
            
        # Add metrics if present
        if hasattr(record, "metrics"):
            log_entry["metrics"] = record.metrics
            
        return json.dumps(log_entry)

def setup_logging():
    """Configure logging for the application."""
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set up rotating file handlers for different log types
    handlers = {
        "app": RotatingFileHandler(
            os.path.join(log_dir, "grant_finder.log"),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5
        ),
        "metrics": RotatingFileHandler(
            os.path.join(log_dir, "metrics.log"),
            maxBytes=5*1024*1024,
            backupCount=5
        ),
        "audit": RotatingFileHandler(
            os.path.join(log_dir, "audit.log"),
            maxBytes=5*1024*1024,
            backupCount=5
        )
    }
    
    # Configure formatters
    json_formatter = StructuredFormatter()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    
    # Configure handlers
    for handler in handlers.values():
        handler.setFormatter(json_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(handlers["app"])
    
    # Configure specific loggers
    metrics_logger = logging.getLogger("metrics")
    metrics_logger.addHandler(handlers["metrics"])
    metrics_logger.propagate = False
    
    audit_logger = logging.getLogger("audit")
    audit_logger.addHandler(handlers["audit"])
    audit_logger.propagate = False
    
    # Set specific levels for noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Log startup
    logging.info("Logging initialized", extra={
        "extra_fields": {
            "startup_time": datetime.now().isoformat(),
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    })