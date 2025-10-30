import json
import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from typing import Dict, Any, Union, TYPE_CHECKING
from pathlib import Path
from decimal import Decimal

if TYPE_CHECKING:
    from .config import LoggingConfig
    from ..infrastructure.config.settings import LoggingSettings

# ✅ FIX #1: Logger cache to prevent handler duplication
# Thread-safe singleton cache for StructuredLogger instances
_logger_cache: Dict[str, 'StructuredLogger'] = {}
_cache_lock = threading.RLock()


# --- Custom JSON Formatter ---

class CustomJsonEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle non-serializable types like Decimal, Enum, and datetime."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        if hasattr(obj, 'name') and hasattr(obj, 'value'): # Check for Enum-like objects
            return obj.name # Return the name of the enum member
        if isinstance(obj, type): # Handle class types if they end up here
            return obj.__name__
        return super().default(obj)


class JsonFormatter(logging.Formatter):
    """Formats log records into a JSON string."""

    def _sanitize_dict(self, d: dict) -> dict:
        """Recursively sanitize dictionary keys and values."""
        sanitized = {}
        for k, v in d.items():
            # Ensure key is a string
            str_key = str(k)
            if isinstance(v, dict):
                sanitized[str_key] = self._sanitize_dict(v)
            elif isinstance(v, (list, tuple)):
                sanitized[str_key] = [self._sanitize_dict(item) if isinstance(item, dict) else item for item in v]
            else:
                sanitized[str_key] = v
        return sanitized

    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, dict):
            message_dict = self._sanitize_dict(record.msg)
        else:
            message_dict = {"message": record.getMessage()}

        log_object = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
            **message_dict,
        }
        
        return json.dumps(log_object, cls=CustomJsonEncoder)


class StructuredLogger:
    def __init__(self, name: str, config: Any, filename: str = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))
        self.logger.propagate = False

        # Always setup handlers for this logger instance
        # Unified config extraction with defaults
        console_enabled = getattr(config, 'console_enabled', True)
        file_enabled = getattr(config, 'file_enabled', bool(getattr(config, 'file', None)))
        structured_logging = getattr(config, 'structured_logging', True)
        max_file_size_mb = getattr(config, 'max_file_size_mb', 100)
        backup_count = getattr(config, 'backup_count', 5)

        # Determine log file path
        if filename:
            # Explicit filename provided
            log_dir = getattr(config, 'log_dir', 'logs')
            log_file = str(Path(log_dir) / filename)
        elif hasattr(config, 'file') and config.file:
            # Legacy: direct file path
            log_file = config.file
        elif file_enabled:
            # New: computed from log_dir
            log_dir = getattr(config, 'log_dir', 'logs')
            log_file = str(Path(log_dir) / f"{name}.jsonl")
        else:
            log_file = None

        # Setup handlers
        self._setup_console_handler(console_enabled, structured_logging)
        self._setup_file_handler(file_enabled, log_file, max_file_size_mb, backup_count, structured_logging)
    
    def _setup_console_handler(self, enabled: bool, structured: bool):
        """
        Setup console handler with appropriate formatter.

        ✅ FIX #2: Defensive check prevents duplicate handlers (idempotency).

        Checks if console handler (StreamHandler to stdout) already exists
        before adding a new one. This makes the function idempotent - safe
        to call multiple times without side effects.
        """
        if not enabled:
            return

        # ✅ DEFENSIVE: Check if console handler already exists
        # Prevents duplicate handlers if get_logger() is called multiple times
        # (though cache should prevent this, this is fail-safe)
        for existing_handler in self.logger.handlers:
            if isinstance(existing_handler, logging.StreamHandler):
                # Check if it's stdout handler (console handler)
                if hasattr(existing_handler, 'stream') and existing_handler.stream == sys.stdout:
                    # Console handler already exists, skip adding
                    return

        handler = logging.StreamHandler(sys.stdout)
        formatter = JsonFormatter() if structured else logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def _setup_file_handler(self, enabled: bool, log_file: str, max_size_mb: int, backup_count: int, structured: bool):
        """
        Setup file handler with appropriate formatter.

        ✅ FIX #2: Defensive check prevents duplicate file handlers (idempotency).

        Checks if RotatingFileHandler for the same file already exists before
        adding a new one. This prevents duplicate writes to the same log file.
        """
        if not enabled or not log_file:
            return

        # ✅ DEFENSIVE: Check if file handler for this file already exists
        # Prevents duplicate file handlers if get_logger() is called multiple times
        # (though cache should prevent this, this is fail-safe)
        log_file_normalized = os.path.abspath(log_file)  # Normalize path for comparison
        for existing_handler in self.logger.handlers:
            if isinstance(existing_handler, RotatingFileHandler):
                # Check if it's the same file
                if hasattr(existing_handler, 'baseFilename'):
                    existing_file = os.path.abspath(existing_handler.baseFilename)
                    if existing_file == log_file_normalized:
                        # File handler for this file already exists, skip adding
                        return

        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        try:
            handler = RotatingFileHandler(
                log_file,
                maxBytes=max_size_mb * 1024 * 1024,
                backupCount=backup_count,
                encoding='utf-8'
            )
        except Exception as e:
            # In a real system, this error should be logged to a fallback or stderr
            # For now, we'll just let it fail silently if file handler can't be created
            return

        formatter = JsonFormatter() if structured else logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _log(self, level: int, event_type: str, data: Dict[str, Any]):
        """Helper to log structured data."""
        payload = {"event_type": event_type, "data": data}
        self.logger.log(level, payload)

    def info(self, event_type: str, data: Dict[str, Any] = None):
        self._log(logging.INFO, event_type, data or {})

    def warning(self, event_type: str, data: Dict[str, Any] = None):
        self._log(logging.WARNING, event_type, data or {})

    def error(self, event_type: str, data: Dict[str, Any], exc_info=False):
        payload = {"event_type": event_type, "data": data}
        self.logger.error(payload, exc_info=exc_info)

    def debug(self, event_type: str, data: Dict[str, Any] = None):
        self._log(logging.DEBUG, event_type, data or {})


def get_logger(name: str) -> StructuredLogger:
    """
    Get a cached structured logger instance for the given name.

    ✅ FIX #1: Thread-safe singleton cache prevents handler duplication.

    Problem solved:
    - Before: Every get_logger(__name__) created NEW StructuredLogger
    - Handlers accumulated in singleton logging.getLogger(name)
    - Result: 30x log duplication in indicators_routes.py

    Solution:
    - Cache StructuredLogger instances by name (thread-safe)
    - Second call returns cached instance (no new handlers)
    - Double-check locking for thread safety

    This is a convenience function that creates a StructuredLogger
    with default settings from the working directory configuration.

    Args:
        name: Logger name (typically __name__ of calling module)

    Returns:
        Cached StructuredLogger instance (singleton per name)
    """
    # Fast path: check cache without lock (thread-safe read)
    if name in _logger_cache:
        return _logger_cache[name]

    # Slow path: acquire lock and create logger
    with _cache_lock:
        # Double-check locking: another thread might have created it
        if name in _logger_cache:
            return _logger_cache[name]

        # Create new logger and cache it
        from ..infrastructure.config.config_loader import get_settings_from_working_directory
        try:
            settings = get_settings_from_working_directory()
            logger = StructuredLogger(name, settings.logging)
            _logger_cache[name] = logger
            return logger
        except Exception:
            # Fallback to basic logging if config loading fails
            import logging
            return logging.getLogger(name)