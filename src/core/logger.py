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
            # ⚠️ CRITICAL: Log to stderr if file handler creation fails
            # This prevents silent failure where we think we're logging but aren't
            print(f"ERROR: Failed to create file handler for {log_file}: {e}", file=sys.stderr)
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

    def error(self, event_type: str, data: Dict[str, Any] = None, exc_info=False):
        """
        Log an error event.

        Args:
            event_type: Type of error event
            data: Optional error context data
            exc_info: Include exception info (default: False)
        """
        payload = {"event_type": event_type, "data": data or {}}
        self.logger.error(payload, exc_info=exc_info)

    def debug(self, event_type: str, data: Dict[str, Any] = None):
        self._log(logging.DEBUG, event_type, data or {})


def configure_module_logger(
    module_name: str,
    log_file: str,
    level: str = "DEBUG",
    console_enabled: bool = False,
    max_file_size_mb: int = 100,
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure a dedicated file logger for a specific module.

    Use this for critical modules that need separate log files (e.g., EventBus).
    This function configures the Python logging hierarchy directly, avoiding
    StructuredLogger complexity when we just need basic file logging.

    ✅ IDEMPOTENT: Safe to call multiple times - checks for existing handlers
    ✅ THREAD-SAFE: Uses logging module's built-in thread safety

    Args:
        module_name: Module logger name (e.g., "src.core.event_bus")
        log_file: Path to log file (e.g., "logs/event_bus.jsonl")
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        console_enabled: Whether to also log to console
        max_file_size_mb: Max file size before rotation
        backup_count: Number of backup files to keep

    Returns:
        Configured logging.Logger instance

    Example:
        >>> logger = configure_module_logger("src.core.event_bus", "logs/event_bus.jsonl")
        >>> logger.info("EventBus started")
    """
    logger = logging.getLogger(module_name)
    logger.setLevel(getattr(logging, level.upper(), logging.DEBUG))
    logger.propagate = False  # Don't propagate to parent loggers

    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # ✅ DEFENSIVE: Check if file handler already exists (idempotency)
    log_file_normalized = os.path.abspath(log_file)
    file_handler_exists = False
    for existing_handler in logger.handlers:
        if isinstance(existing_handler, RotatingFileHandler):
            if hasattr(existing_handler, 'baseFilename'):
                existing_file = os.path.abspath(existing_handler.baseFilename)
                if existing_file == log_file_normalized:
                    file_handler_exists = True
                    break

    # Add file handler if it doesn't exist
    if not file_handler_exists:
        try:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_file_size_mb * 1024 * 1024,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(JsonFormatter())
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"ERROR: Failed to create file handler for {log_file}: {e}", file=sys.stderr)

    # ✅ DEFENSIVE: Check if console handler already exists (idempotency)
    if console_enabled:
        console_handler_exists = False
        for existing_handler in logger.handlers:
            if isinstance(existing_handler, logging.StreamHandler):
                if hasattr(existing_handler, 'stream') and existing_handler.stream == sys.stdout:
                    console_handler_exists = True
                    break

        if not console_handler_exists:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(JsonFormatter())
            logger.addHandler(console_handler)

    return logger


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
        except Exception as e:
            # ⚠️ CRITICAL: Fallback must return StructuredLogger, not logging.Logger
            # Otherwise we get AttributeError on .info(event_type, data) calls
            print(f"WARNING: Failed to load config for logger '{name}': {e}", file=sys.stderr)
            print(f"WARNING: Using basic StructuredLogger with defaults", file=sys.stderr)

            # Create minimal config for fallback
            class FallbackConfig:
                level = "INFO"
                console_enabled = True
                file_enabled = False
                structured_logging = True
                log_dir = "logs"
                max_file_size_mb = 100
                backup_count = 5

            fallback_logger = StructuredLogger(name, FallbackConfig())
            _logger_cache[name] = fallback_logger
            return fallback_logger