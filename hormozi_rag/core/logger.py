"""
Structured logging configuration for the Hormozi RAG system.

This module provides a centralized logging setup with structured output
for better observability and debugging in production environments.
"""

import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import structlog
from structlog.processors import TimeStamper, add_log_level, format_exc_info
from structlog.dev import ConsoleRenderer
from structlog.processors import JSONRenderer

from ..config.settings import settings, DATA_DIR


class StructuredLogger:
    """Structured logging wrapper for consistent logging across the application."""
    
    def __init__(self, name: str):
        """Initialize structured logger with given name.
        
        Args:
            name: Logger name (typically __name__ of the module)
        """
        self.logger = structlog.get_logger(name)
        self._context: Dict[str, Any] = {}
    
    def bind(self, **kwargs) -> "StructuredLogger":
        """Bind contextual information to all future log messages.
        
        Args:
            **kwargs: Key-value pairs to bind to the logger context
            
        Returns:
            Self for method chaining
        """
        self._context.update(kwargs)
        self.logger = self.logger.bind(**self._context)
        return self
    
    def unbind(self, *keys) -> "StructuredLogger":
        """Remove keys from the logger context.
        
        Args:
            *keys: Keys to remove from context
            
        Returns:
            Self for method chaining
        """
        for key in keys:
            self._context.pop(key, None)
        self.logger = self.logger.unbind(*keys)
        return self
    
    def debug(self, message: str, **kwargs):
        """Log debug message with optional structured data."""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with optional structured data."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with optional structured data."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message with optional exception and structured data."""
        if exception:
            kwargs["exception"] = str(exception)
            kwargs["exception_type"] = type(exception).__name__
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log critical message with optional exception and structured data."""
        if exception:
            kwargs["exception"] = str(exception)
            kwargs["exception_type"] = type(exception).__name__
        self.logger.critical(message, **kwargs)
    
    def log_performance(self, operation: str, duration_ms: float, **kwargs):
        """Log performance metrics for operations.
        
        Args:
            operation: Name of the operation being measured
            duration_ms: Duration in milliseconds
            **kwargs: Additional metrics to log
        """
        self.info(
            f"Performance: {operation}",
            operation=operation,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def log_retrieval(self, query: str, results_count: int, 
                     relevance_scores: Optional[list] = None, **kwargs):
        """Log retrieval operations with metrics.
        
        Args:
            query: The search query
            results_count: Number of results retrieved
            relevance_scores: Optional list of relevance scores
            **kwargs: Additional retrieval metrics
        """
        log_data = {
            "query": query,
            "results_count": results_count,
            "event_type": "retrieval"
        }
        
        if relevance_scores:
            log_data["avg_relevance"] = sum(relevance_scores) / len(relevance_scores)
            log_data["max_relevance"] = max(relevance_scores)
            log_data["min_relevance"] = min(relevance_scores)
        
        log_data.update(kwargs)
        self.info("Retrieval operation completed", **log_data)


def setup_logging():
    """Configure structured logging for the entire application."""
    
    # Configure structlog
    timestamper = TimeStamper(fmt="iso")
    
    # Choose renderer based on environment
    if settings.ENVIRONMENT == "production":
        renderer = JSONRenderer()
    else:
        renderer = ConsoleRenderer()
    
    # Base processors
    processors = [
        timestamper,
        add_log_level,
        format_exc_info,
    ]
    
    # Add custom processors
    def add_environment(logger, method_name, event_dict):
        """Add environment to all log messages."""
        event_dict["environment"] = settings.ENVIRONMENT
        return event_dict
    
    processors.append(add_environment)
    processors.append(renderer)
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )
    
    # Add file handler if configured (simplified for new architecture)
    log_file = DATA_DIR / "logs" / "hormozi_rag.log"
    if log_file.parent.exists():
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        logging.getLogger().addHandler(file_handler)
    
    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance for the given module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)


# Initialize logging on module import
setup_logging()