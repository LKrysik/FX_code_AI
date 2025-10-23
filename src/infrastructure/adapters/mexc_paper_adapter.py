"""
Paper Mexc Adapter
==================
Lightweight in-memory adapter used when real MEXC credentials are missing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any


class MexcPaperAdapter:
    """Minimal adapter that mimics the balance endpoint for local development."""

    def __init__(self, logger, initial_balances: Dict[str, Any] | None = None) -> None:
        self._logger = logger
        default_assets = {
            "USDT": {"free": "10000.0", "locked": "0.0"},
            "BTC": {"free": "0.5", "locked": "0.0"},
        }
        self._assets = dict(initial_balances or default_assets)

    def get_balances(self) -> Dict[str, Any]:
        """Return static balances for development scenarios."""
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "assets": self._assets,
            "source": "paper_wallet",
        }
        if self._logger:
            self._logger.debug("mexc_paper_adapter.get_balances", snapshot)
        return snapshot
