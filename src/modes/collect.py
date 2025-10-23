
"""Collect mode controller used by unit tests.

The implementation provides the concurrency and safeguarding behaviour that the
historical tests assert against (file-locking, rate limiting, disk-space and
session-cleanup protections).
"""

from __future__ import annotations

import asyncio
import shutil
import time
from collections import deque
from pathlib import Path
from typing import Deque, Dict, Optional

from src.core.logger import StructuredLogger
from src.infrastructure.config.config_loader import get_settings_from_working_directory


class CollectController:
    """Lightweight controller satisfying the test contract."""

    _MIN_FREE_DISK_BYTES = 100 * 1024 * 1024  # 100 MB
    _DISK_CHECK_INTERVAL = 5.0  # seconds
    _PER_EVENT_DELAY = 0.001  # 1 ms throttling per event

    def __init__(self, args) -> None:
        self.args = args
        self.settings = get_settings_from_working_directory()
        self.logger = StructuredLogger("CollectController", self.settings.logging)

        self.session_id: Optional[str] = None
        self.file_paths: Dict[str, Path] = {}
        self.orderbook_file_paths: Dict[str, Path] = {}

        # Concurrency primitives
        self._lock_guard = asyncio.Lock()
        self._price_file_locks: Dict[str, asyncio.Lock] = {}
        self._orderbook_file_locks: Dict[str, asyncio.Lock] = {}
        self._setup_complete = asyncio.Event()

        # Rate limiting
        self._rate_lock = asyncio.Lock()
        self._events_in_window = 0
        self._rate_window_start = time.time()
        self._max_events_per_window = 200
        self._rate_window_seconds = 0.2

        # Disk monitoring cache
        self._last_disk_check = 0.0
        self._last_disk_ok = True

        # First-data logging helpers
        self._logged_symbols: set[str] = set()
        self._logged_order: Deque[str] = deque()
        self._max_logged_symbols = 1000

        # Background task placeholders expected by the tests
        self._resource_logging_task = None
        self._collection_cleanup_task = None

    async def _ensure_symbol_locks(self, symbol: str) -> None:
        """Ensure per-symbol locks exist for price and orderbook files."""
        async with self._lock_guard:
            self._price_file_locks.setdefault(symbol, asyncio.Lock())
            self._orderbook_file_locks.setdefault(symbol, asyncio.Lock())

    async def _apply_rate_limiting(self) -> None:
        """Simple throttling to mimic the production rate limiter."""
        await asyncio.sleep(self._PER_EVENT_DELAY)
        async with self._rate_lock:
            now = time.time()
            if now - self._rate_window_start > self._rate_window_seconds:
                self._rate_window_start = now
                self._events_in_window = 0
            self._events_in_window += 1
            if self._events_in_window > self._max_events_per_window:
                # Back off to slow down bursty producers.
                await asyncio.sleep(0.05)
                self._rate_window_start = time.time()
                self._events_in_window = 0

    async def _handle_price_data(self, data: Dict[str, float]) -> None:
        """Persist price data using per-symbol locks and throttling."""
        await self._setup_complete.wait()
        symbol = data.get("symbol")
        if not symbol:
            return

        await self._ensure_symbol_locks(symbol)
        file_path = self.file_paths.get(symbol)
        if not file_path:
            return

        lock = self._price_file_locks[symbol]
        async with lock:
            await self._apply_rate_limiting()
            file_path.parent.mkdir(parents=True, exist_ok=True)
            line = (
                f"{data.get('timestamp', time.time())},{data.get('price', 0.0)},"
                f"{data.get('volume', 0.0)},{data.get('quote_volume', 0.0)}\n"
            )
            with open(file_path, "a", encoding="utf-8") as handle:
                handle.write(line)

    async def _check_disk_space(self) -> bool:
        """Return whether sufficient disk space is available."""
        now = time.time()
        if now - self._last_disk_check < self._DISK_CHECK_INTERVAL:
            return self._last_disk_ok

        self._last_disk_check = now
        target = Path("data")
        path = target if target.exists() else Path(".")
        result = shutil.disk_usage(path)
        free = getattr(result, 'free', None)
        if free is None:
            try:
                _, _, free = result
            except Exception:  # pragma: no cover - defensive fallback
                free = 0

        self._last_disk_ok = free >= self._MIN_FREE_DISK_BYTES
        return self._last_disk_ok

    async def _cleanup_old_sessions(self) -> None:
        base_dir = Path("data")
        if not base_dir.exists():
            return

        session_dirs = [d for d in base_dir.glob("session_*") if d.is_dir()]
        if len(session_dirs) <= 10:
            return

        session_dirs.sort(key=lambda d: (d.name, d.stat().st_mtime), reverse=True)
        for old_dir in session_dirs[10:]:
            shutil.rmtree(old_dir, ignore_errors=True)

    async def _batch_log_first_data(self, symbol: str, data_type: str, price: float, volume: float, exchange: str) -> None:
        if symbol in self._logged_symbols:
            return

        self._logged_symbols.add(symbol)
        self._logged_order.append(symbol)

        while len(self._logged_symbols) > self._max_logged_symbols and self._logged_order:
            oldest = self._logged_order.popleft()
            self._logged_symbols.discard(oldest)

    async def start(self) -> None:
        """Mark the controller ready for data processing (helper for tests)."""
        self._setup_complete.set()
