"""
Resilient Strategy Storage - Fallback wrapper for strategy persistence
======================================================================
Provides graceful degradation: tries QuestDB first, falls back to file-based storage.

Design:
- Primary: QuestDB (preferred for multi-instance deployments)
- Fallback: File-based JSON storage (config/strategies/*.json)
- Transparent switching on connection failures
- Single source of truth maintained per environment

Architecture:
- Implements same interface as QuestDBStrategyStorage
- Delegates to appropriate storage backend
- Caches backend availability to avoid repeated connection attempts
- Logs all fallback events for monitoring
"""

import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from src.domain.services.strategy_storage_questdb import (
    QuestDBStrategyStorage,
    StrategyStorageError,
    StrategyNotFoundError,
    StrategyValidationError
)
from src.domain.services.strategy_storage import StrategyStorage


class ResilientStrategyStorage:
    """
    Resilient strategy storage with automatic fallback.

    Attempts to use QuestDB first, falls back to file-based storage
    if QuestDB is unavailable. This ensures the application remains
    functional even when the database is down.

    Usage:
        storage = ResilientStrategyStorage(logger=logger)
        await storage.initialize()
        strategies = await storage.list_strategies()
    """

    def __init__(self,
                 questdb_host: str = "127.0.0.1",
                 questdb_port: int = 8812,
                 questdb_user: str = "admin",
                 questdb_password: str = "quest",
                 questdb_database: str = "qdb",
                 file_storage_path: Optional[Path] = None,
                 logger = None):
        """
        Initialize resilient strategy storage.

        Args:
            questdb_host: QuestDB host
            questdb_port: QuestDB PostgreSQL protocol port
            questdb_user: QuestDB user
            questdb_password: QuestDB password
            questdb_database: QuestDB database name
            file_storage_path: Path to JSON strategy files (default: config/strategies)
            logger: Optional logger for diagnostics
        """
        self.logger = logger
        self._primary_available = None  # None = unknown, True/False = cached state
        self._last_check_time = None
        self._check_interval = 30.0  # Seconds between availability checks

        # Initialize both storage backends
        self._primary = QuestDBStrategyStorage(
            host=questdb_host,
            port=questdb_port,
            user=questdb_user,
            password=questdb_password,
            database=questdb_database
        )

        if file_storage_path is None:
            file_storage_path = Path("config/strategies")

        self._fallback = StrategyStorage(storage_path=file_storage_path)

        self._log_info("resilient_storage.initialized", {
            "primary": "QuestDB",
            "fallback": "file-based",
            "file_path": str(file_storage_path)
        })

    def _log_info(self, event: str, data: Dict[str, Any]) -> None:
        """Log info event if logger available."""
        if self.logger:
            try:
                self.logger.info(event, data)
            except Exception:
                pass

    def _log_warning(self, event: str, data: Dict[str, Any]) -> None:
        """Log warning event if logger available."""
        if self.logger:
            try:
                self.logger.warning(event, data)
            except Exception:
                pass

    def _log_error(self, event: str, data: Dict[str, Any]) -> None:
        """Log error event if logger available."""
        if self.logger:
            try:
                self.logger.error(event, data)
            except Exception:
                pass

    async def initialize(self) -> None:
        """
        Initialize storage backends.

        Attempts to initialize QuestDB first. If it fails, marks primary
        as unavailable and relies on file-based fallback.
        """
        # Try to initialize primary storage
        try:
            await self._primary.initialize()
            self._primary_available = True
            self._last_check_time = datetime.utcnow()
            self._log_info("resilient_storage.primary_available", {
                "backend": "QuestDB",
                "status": "connected"
            })
        except Exception as e:
            self._primary_available = False
            self._last_check_time = datetime.utcnow()
            self._log_warning("resilient_storage.primary_unavailable", {
                "backend": "QuestDB",
                "error": str(e),
                "fallback": "file-based"
            })

        # Fallback is always available (file-based, no initialization needed)
        # StrategyStorage.__init__ already creates the directory
        # No async initialization required for file-based storage

    async def close(self) -> None:
        """Close all storage backends."""
        if self._primary_available:
            try:
                await self._primary.close()
            except Exception as e:
                self._log_warning("resilient_storage.primary_close_failed", {
                    "error": str(e)
                })

    async def _check_primary_availability(self) -> bool:
        """
        Check if primary storage is available.

        Uses cached result if check was recent, otherwise performs fresh check.

        Returns:
            True if primary is available, False otherwise
        """
        now = datetime.utcnow()

        # Use cached result if recent
        if (self._primary_available is not None and
            self._last_check_time is not None and
            (now - self._last_check_time).total_seconds() < self._check_interval):
            return self._primary_available

        # Perform fresh check
        try:
            # Simple availability test: try to list strategies with timeout
            await asyncio.wait_for(self._primary.list_strategies(), timeout=2.0)

            # If we get here, primary is available
            if not self._primary_available:
                self._log_info("resilient_storage.primary_recovered", {
                    "backend": "QuestDB",
                    "status": "reconnected"
                })

            self._primary_available = True
            self._last_check_time = now
            return True

        except Exception as e:
            # Primary is unavailable
            if self._primary_available:
                self._log_warning("resilient_storage.primary_failed", {
                    "backend": "QuestDB",
                    "error": str(e),
                    "switching_to": "file-based"
                })

            self._primary_available = False
            self._last_check_time = now
            return False

    async def _execute_with_fallback(self, operation: str, primary_fn, fallback_fn):
        """
        Execute operation with automatic fallback.

        Args:
            operation: Operation name for logging
            primary_fn: Async callable for primary storage
            fallback_fn: Async callable for fallback storage

        Returns:
            Result from primary or fallback

        Raises:
            StrategyStorageError: If both backends fail
        """
        # Check if primary is available
        primary_available = await self._check_primary_availability()

        if primary_available:
            try:
                return await primary_fn()
            except Exception as e:
                self._log_warning("resilient_storage.primary_operation_failed", {
                    "operation": operation,
                    "backend": "QuestDB",
                    "error": str(e),
                    "attempting_fallback": True
                })
                # Mark primary as unavailable and try fallback
                self._primary_available = False

        # Use fallback
        try:
            self._log_info("resilient_storage.using_fallback", {
                "operation": operation,
                "backend": "file-based"
            })
            return await fallback_fn()
        except Exception as e:
            self._log_error("resilient_storage.fallback_failed", {
                "operation": operation,
                "error": str(e)
            })
            raise

    async def create_strategy(self, strategy_data: Dict[str, Any]) -> str:
        """Create a new strategy."""
        return await self._execute_with_fallback(
            "create_strategy",
            lambda: self._primary.create_strategy(strategy_data),
            lambda: self._fallback.create_strategy(strategy_data)
        )

    async def read_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """Read strategy by ID."""
        return await self._execute_with_fallback(
            "read_strategy",
            lambda: self._primary.read_strategy(strategy_id),
            lambda: self._fallback.read_strategy(strategy_id)
        )

    async def update_strategy(self, strategy_id: str, strategy_data: Dict[str, Any]) -> None:
        """Update existing strategy."""
        return await self._execute_with_fallback(
            "update_strategy",
            lambda: self._primary.update_strategy(strategy_id, strategy_data),
            lambda: self._fallback.update_strategy(strategy_id, strategy_data)
        )

    async def delete_strategy(self, strategy_id: str) -> None:
        """Delete strategy by ID."""
        return await self._execute_with_fallback(
            "delete_strategy",
            lambda: self._primary.delete_strategy(strategy_id),
            lambda: self._fallback.delete_strategy(strategy_id)
        )

    async def list_strategies(self) -> List[Dict[str, Any]]:
        """List all strategies."""
        return await self._execute_with_fallback(
            "list_strategies",
            lambda: self._primary.list_strategies(),
            lambda: self._fallback.list_strategies()
        )

    def get_backend_status(self) -> Dict[str, Any]:
        """
        Get current backend status for monitoring.

        Returns:
            Dict with backend availability and last check time
        """
        return {
            "primary_backend": "QuestDB",
            "fallback_backend": "file-based",
            "primary_available": self._primary_available,
            "last_check": self._last_check_time.isoformat() if self._last_check_time else None,
            "current_backend": "QuestDB" if self._primary_available else "file-based"
        }
