"""
WalletService - Real MEXC API Integration
=========================================
Wallet service for real MEXC API balance management.
"""

from typing import Dict, Any
from datetime import datetime


class WalletService:
    def __init__(self, adapter: Any):
        # Allow None adapter for two-phase initialization
        self._adapter = adapter
        self._is_initialized = adapter is not None

    def validate_dependencies(self) -> None:
        """Validate that all required dependencies are properly set"""
        if self._adapter is None:
            raise RuntimeError("WalletService dependency validation failed: adapter not set")
        if not self._is_initialized:
            raise RuntimeError("WalletService dependency validation failed: service not initialized")

    def get_balance(self) -> Dict[str, Any]:
        """Get real balance from MEXC API"""
        if not self._is_initialized or self._adapter is None:
            raise RuntimeError("WalletService not initialized - adapter not set")

        try:
            data = self._adapter.get_balances()
            assets = data.get("assets", {})
            total_usd = float(assets.get("USDT", {}).get("free", 0)) + float(assets.get("USDT", {}).get("locked", 0))
            return {
                "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
                "assets": assets,
                "total_usd_estimate": total_usd,
                "source": "mexc_api"
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get balance from MEXC API: {str(e)}")
