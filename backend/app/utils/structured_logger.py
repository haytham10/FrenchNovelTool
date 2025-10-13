"""
Structured logging utility for Project Battleship.

Provides centralized, JSON-formatted logging with context management for:
- Error tracking with full context (job_id, chunk_id, user_id)
- Fragment rate monitoring per job
- GeminiAPIError tracking with stack traces
- Performance metrics aggregation
- Railway/Sentry integration support
"""
import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Union, List

try:
    from flask import request, has_request_context, g
except ImportError:
    # Handle case where Flask is not available (e.g., in Celery workers)
    def has_request_context():
        return False
    
    class MockG:
        pass
    
    g = MockG()
    request = None


class StructuredLogger:
    """
    JSON-formatted logger with automatic context injection.
    
    Features:
    - Automatic job_id, user_id, chunk_id context from Flask g
    - Structured error tracking with stack traces
    - Fragment rate monitoring
    - Performance metrics
    - Integration with Railway logs and optional Sentry
    """
    
    def __init__(self, name: str, level: str = "INFO"):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name (typically __name__)
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Create structured formatter if not already set
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = StructuredFormatter()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _build_context(self, extra_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build logging context from Flask g and request context.
        
        Args:
            extra_context: Additional context to include
            
        Returns:
            Dict with structured context
        """
        context = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": "french-novel-tool",
            "component": self.logger.name,
        }
        
        # Add Flask request context if available
        if has_request_context():
            context.update({
                "request_id": getattr(request, "id", None),
                "endpoint": request.endpoint,
                "method": request.method,
                "url": request.url,
                "user_agent": request.headers.get("User-Agent"),
                "remote_addr": request.remote_addr,
            })
        
        # Add Flask g context (job processing context)
        if has_request_context() and hasattr(g, "job_id"):
            context["job_id"] = g.job_id
        if has_request_context() and hasattr(g, "user_id"):
            context["user_id"] = g.user_id
        if has_request_context() and hasattr(g, "chunk_id"):
            context["chunk_id"] = g.chunk_id
        
        # Add extra context
        if extra_context:
            context.update(extra_context)
            
        return context
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured context."""
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with structured context."""
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured context."""
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """
        Log error message with structured context and optional exception.
        
        Args:
            message: Error message
            exception: Exception instance (will include stack trace)
            **kwargs: Additional context
        """
        context = kwargs.copy()
        
        if exception:
            context.update({
                "exception_type": exception.__class__.__name__,
                "exception_message": str(exception),
                "stack_trace": traceback.format_exc(),
            })
            
            # Special handling for GeminiAPIError
            if hasattr(exception, "raw_response"):
                context["gemini_raw_response"] = exception.raw_response
        
        self._log("ERROR", message, **context)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log critical message with structured context and optional exception."""
        context = kwargs.copy()
        
        if exception:
            context.update({
                "exception_type": exception.__class__.__name__,
                "exception_message": str(exception),
                "stack_trace": traceback.format_exc(),
            })
        
        self._log("CRITICAL", message, **context)
    
    def gemini_error(
        self,
        message: str,
        exception: Exception,
        chunk_info: Optional[Dict[str, Any]] = None,
        processing_settings: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Specialized logging for Gemini API errors with full context.
        
        Args:
            message: Error description
            exception: GeminiAPIError or related exception
            chunk_info: Information about the chunk being processed
            processing_settings: User settings that may have affected the error
            **kwargs: Additional context
        """
        context = {
            "error_category": "gemini_api",
            "model_name": getattr(processing_settings, "get", lambda x, y: None)("model", "unknown"),
            "chunk_size": len(chunk_info.get("text", "")) if chunk_info else 0,
            "processing_settings": processing_settings,
            **kwargs
        }
        
        if chunk_info:
            context.update({
                "chunk_id": chunk_info.get("chunk_id"),
                "page_range": f"{chunk_info.get('start_page', '?')}-{chunk_info.get('end_page', '?')}",
                "pdf_filename": chunk_info.get("filename"),
            })
        
        self.error(message, exception=exception, **context)
    
    def fragment_rate_warning(
        self,
        fragment_rate: float,
        fragment_count: int,
        total_sentences: int,
        fragments: List[str],
        job_id: Optional[int] = None,
        **kwargs
    ):
        """
        Log fragment rate warning with detailed fragment information.
        
        Args:
            fragment_rate: Percentage of fragments (0.0-100.0)
            fragment_count: Number of fragment sentences
            total_sentences: Total number of sentences processed
            fragments: List of actual fragment strings
            job_id: Job ID if available
            **kwargs: Additional context
        """
        context = {
            "metric_type": "fragment_rate",
            "fragment_rate_percent": fragment_rate,
            "fragment_count": fragment_count,
            "total_sentences": total_sentences,
            "fragments_sample": fragments[:5],  # First 5 fragments for debugging
            "all_fragments": fragments,  # Full list for analysis
            **kwargs
        }
        
        if job_id:
            context["job_id"] = job_id
        
        level = "ERROR" if fragment_rate > 3.0 else "WARNING"
        message = f"High fragment rate detected: {fragment_rate:.2f}% ({fragment_count}/{total_sentences})"
        
        self._log(level, message, **context)
    
    def performance_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        unit: str,
        **kwargs
    ):
        """
        Log performance metric for monitoring.
        
        Args:
            metric_name: Name of the metric (e.g., "gemini_api_latency")
            value: Metric value
            unit: Unit of measurement (e.g., "ms", "seconds", "bytes")
            **kwargs: Additional context
        """
        context = {
            "metric_type": "performance",
            "metric_name": metric_name,
            "metric_value": value,
            "metric_unit": unit,
            **kwargs
        }
        
        self.info(f"Performance metric: {metric_name} = {value} {unit}", **context)
    
    def quality_gate_rejection(
        self,
        sentence: str,
        rejection_reason: str,
        job_id: Optional[int] = None,
        chunk_id: Optional[str] = None,
        **kwargs
    ):
        """
        Log Quality Gate sentence rejection.
        
        Args:
            sentence: The rejected sentence
            rejection_reason: Why it was rejected
            job_id: Job ID if available
            chunk_id: Chunk ID if available
            **kwargs: Additional context
        """
        context = {
            "metric_type": "quality_gate_rejection",
            "rejected_sentence": sentence,
            "rejection_reason": rejection_reason,
            "sentence_length": len(sentence.split()),
            **kwargs
        }
        
        if job_id:
            context["job_id"] = job_id
        if chunk_id:
            context["chunk_id"] = chunk_id
            
        self.warning(f"Quality Gate rejected sentence: {rejection_reason}", **context)
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal logging method with context building."""
        context = self._build_context(kwargs)
        
        # Use the logger's built-in level methods with extra context
        log_method = getattr(self.logger, level.lower())
        log_method(message, extra={"structured_context": context})


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Python logging record
            
        Returns:
            JSON-formatted log string
        """
        # Base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add structured context if present
        if hasattr(record, "structured_context"):
            log_entry.update(record.structured_context)
        
        return json.dumps(log_entry, default=str, separators=(',', ':'))


# Convenience factory functions
def get_logger(name: str, level: str = "INFO") -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        level: Log level
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name, level)


def set_job_context(job_id: Optional[int] = None, user_id: Optional[int] = None, chunk_id: Optional[str] = None):
    """
    Set job processing context in Flask g for automatic logging context.
    
    Args:
        job_id: Current job ID
        user_id: Current user ID
        chunk_id: Current chunk ID
    """
    if has_request_context():
        if job_id is not None:
            g.job_id = job_id
        if user_id is not None:
            g.user_id = user_id
        if chunk_id is not None:
            g.chunk_id = chunk_id


def clear_job_context():
    """Clear job context from Flask g."""
    if has_request_context():
        for attr in ["job_id", "user_id", "chunk_id"]:
            if hasattr(g, attr):
                delattr(g, attr)


# Global logger instances for common use
logger = get_logger("battleship")
gemini_logger = get_logger("battleship.gemini")
task_logger = get_logger("battleship.tasks")
quality_gate_logger = get_logger("battleship.quality_gate")