import logging
import logging.handlers
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class StructuredLogger:
    """Structured logging utility with JSON formatting and rotation"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(name)
        self.config = config or {}
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with handlers and formatting"""
        # Clear existing handlers
        self.logger.handlers.clear()
        
        level = getattr(logging, self.config.get('level', 'INFO').upper())
        self.logger.setLevel(level)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self._get_console_formatter())
        self.logger.addHandler(console_handler)
        
        # File handler with rotation
        log_file = self.config.get('file', 'logs/cross_listing.log')
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self._parse_size(self.config.get('max_file_size', '10MB')),
                backupCount=self.config.get('backup_count', 5)
            )
            file_handler.setFormatter(self._get_file_formatter())
            self.logger.addHandler(file_handler)
    
    def _get_console_formatter(self):
        """Get console formatter"""
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def _get_file_formatter(self):
        """Get file formatter with JSON structure"""
        return JsonFormatter()
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '10MB' to bytes"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def log_api_call(self, platform: str, method: str, url: str, 
                     duration: float, success: bool, 
                     status_code: Optional[int] = None, 
                     error: Optional[str] = None):
        """Log API call with structured data"""
        log_data = {
            "event_type": "api_call",
            "platform": platform,
            "method": method,
            "url": self._sanitize_url(url),
            "duration": round(duration, 3),
            "success": success,
            "status_code": status_code,
            "timestamp": datetime.now().isoformat()
        }
        
        if error:
            log_data["error"] = str(error)
        
        message = f"API call to {platform} {method} - {'SUCCESS' if success else 'FAILED'}"
        
        if success:
            self.logger.info(message, extra={"structured_data": log_data})
        else:
            self.logger.error(message, extra={"structured_data": log_data})
    
    def log_listing_operation(self, operation: str, platform: str, 
                              item_id: str, listing_id: Optional[str] = None,
                              success: bool = True, error: Optional[str] = None):
        """Log listing operations"""
        log_data = {
            "event_type": "listing_operation",
            "operation": operation,
            "platform": platform,
            "item_id": item_id,
            "listing_id": listing_id,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        if error:
            log_data["error"] = str(error)
        
        message = f"Listing {operation} for {item_id} on {platform} - {'SUCCESS' if success else 'FAILED'}"
        
        if success:
            self.logger.info(message, extra={"structured_data": log_data})
        else:
            self.logger.error(message, extra={"structured_data": log_data})
    
    def log_sync_operation(self, operation: str, platform: str, 
                           items_processed: int, items_failed: int = 0,
                           duration: Optional[float] = None):
        """Log synchronization operations"""
        log_data = {
            "event_type": "sync_operation",
            "operation": operation,
            "platform": platform,
            "items_processed": items_processed,
            "items_failed": items_failed,
            "success_rate": (items_processed - items_failed) / items_processed if items_processed > 0 else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        if duration:
            log_data["duration"] = round(duration, 3)
        
        message = f"Sync {operation} for {platform} - {items_processed} items processed, {items_failed} failed"
        
        if items_failed == 0:
            self.logger.info(message, extra={"structured_data": log_data})
        else:
            self.logger.warning(message, extra={"structured_data": log_data})
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log error with context"""
        log_data = {
            "event_type": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat()
        }
        
        if context:
            log_data["context"] = context
        
        self.logger.error(f"Error: {error}", extra={"structured_data": log_data})
    
    def log_performance(self, operation: str, duration: float, 
                        items_count: Optional[int] = None,
                        platform: Optional[str] = None):
        """Log performance metrics"""
        log_data = {
            "event_type": "performance",
            "operation": operation,
            "duration": round(duration, 3),
            "timestamp": datetime.now().isoformat()
        }
        
        if items_count:
            log_data["items_count"] = items_count
            log_data["items_per_second"] = round(items_count / duration, 2) if duration > 0 else 0
        
        if platform:
            log_data["platform"] = platform
        
        message = f"Performance: {operation} took {duration:.3f}s"
        if items_count:
            message += f" for {items_count} items"
        
        self.logger.info(message, extra={"structured_data": log_data})
    
    def _sanitize_url(self, url: str) -> str:
        """Remove sensitive information from URLs"""
        import re
        # Remove API keys, tokens, and other sensitive query parameters
        sensitive_params = ['api_key', 'token', 'access_token', 'secret', 'password']
        
        for param in sensitive_params:
            pattern = f'({param}=)[^&]*'
            url = re.sub(pattern, r'\1***', url, flags=re.IGNORECASE)
        
        return url


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add structured data if available
        if hasattr(record, 'structured_data'):
            log_entry.update(record.structured_data)
        
        # Add exception info if available
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


def setup_logging(config: Dict[str, Any] = None) -> StructuredLogger:
    """Setup global logging configuration"""
    if config is None:
        config = {
            'level': 'INFO',
            'file': 'logs/cross_listing.log',
            'max_file_size': '10MB',
            'backup_count': 5
        }
    
    return StructuredLogger("cross_listing", config)


def get_logger(name: str) -> StructuredLogger:
    """Get a logger instance"""
    return StructuredLogger(name)