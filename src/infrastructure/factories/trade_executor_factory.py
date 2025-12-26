"""
Trade Executor Factory
======================
Handles conditional logic for creating trade executors.
Isolates trading mode selection logic from Container.

FIXED (2025-12-22): Now properly creates MexcFuturesOrderExecutor for live/paper trading.
Previously raised NotImplementedError for all modes.
"""

from typing import TYPE_CHECKING
from ...domain.interfaces.trading import IOrderExecutor
from ..adapters.mexc_futures_adapter import MexcFuturesAdapter
from ..adapters.mexc_paper_adapter import MexcPaperAdapter
from ..adapters.mexc_futures_order_executor import MexcFuturesOrderExecutor

if TYPE_CHECKING:
    from ...core.event_bus import EventBus
    from ...core.logger import StructuredLogger
    from ...infrastructure.config.settings import AppSettings


class TradeExecutorFactory:
    """Factory for creating trade executors based on settings"""

    def __init__(self, settings: 'AppSettings', event_bus: 'EventBus', logger: 'StructuredLogger'):
        self.settings = settings
        self.event_bus = event_bus
        self.logger = logger

    def create(self) -> IOrderExecutor:
        """
        Create trade executor based on trading mode.

        Modes:
        - live: Uses MexcFuturesAdapter with real API calls
        - paper: Uses MexcPaperAdapter for simulated trading
        - backtest: Uses MexcPaperAdapter (no real orders)

        Returns:
            Configured trade executor implementing IOrderExecutor

        Raises:
            ValueError: If MEXC API credentials not configured for live mode
            RuntimeError: If executor creation fails
        """
        trading_mode = self.settings.trading.mode.value.lower()
        live_trading_enabled = getattr(self.settings.trading, 'live_trading_enabled', False)

        self.logger.info("trade_executor_factory.creating", {
            "mode": trading_mode,
            "live_trading_enabled": live_trading_enabled
        })

        try:
            if live_trading_enabled and trading_mode == "live":
                return self._create_live_executor()
            else:
                return self._create_paper_executor()

        except Exception as e:
            self.logger.error("trade_executor_factory.creation_failed", {
                "mode": trading_mode,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise RuntimeError(f"Failed to create trade executor: {str(e)}") from e

    def _create_live_executor(self) -> IOrderExecutor:
        """
        Create live trading executor with real MEXC API.

        Requires:
        - MEXC API key configured in settings.exchanges.mexc_api_key
        - MEXC API secret configured in settings.exchanges.mexc_api_secret

        Returns:
            MexcFuturesOrderExecutor for live trading

        Raises:
            ValueError: If API credentials not configured
        """
        api_key = getattr(self.settings.exchanges, 'mexc_api_key', '')
        api_secret = getattr(self.settings.exchanges, 'mexc_api_secret', '')

        if not api_key or not api_secret:
            self.logger.error("trade_executor_factory.missing_credentials", {
                "has_api_key": bool(api_key),
                "has_api_secret": bool(api_secret)
            })
            raise ValueError(
                "MEXC API credentials not configured. "
                "Set MEXC_API_KEY and MEXC_API_SECRET in environment or configuration."
            )

        # Get leverage from settings (default: 3x, max: 10x for safety)
        default_leverage = min(
            getattr(self.settings.trading, 'default_leverage', 3),
            10  # Safety cap
        )

        # Create MEXC Futures Adapter
        mexc_adapter = MexcFuturesAdapter(
            api_key=api_key,
            api_secret=api_secret,
            logger=self.logger
        )

        # Create executor wrapper
        executor = MexcFuturesOrderExecutor(
            mexc_adapter=mexc_adapter,
            logger=self.logger,
            default_leverage=default_leverage
        )

        self.logger.info("trade_executor_factory.live_executor_created", {
            "exchange": "MEXC_FUTURES",
            "leverage": default_leverage
        })

        return executor

    def _create_paper_executor(self) -> IOrderExecutor:
        """
        Create paper trading executor with simulated orders.

        Uses MexcPaperAdapter which simulates order execution
        without making real API calls.

        Returns:
            MexcFuturesOrderExecutor with paper adapter
        """
        # Get paper trading settings
        initial_balance = float(getattr(
            self.settings.trading.paper_trading,
            'initial_balance',
            10000.0
        ))

        default_leverage = min(
            getattr(self.settings.trading, 'default_leverage', 3),
            10  # Safety cap
        )

        # Create paper trading adapter
        paper_adapter = MexcPaperAdapter(
            logger=self.logger,
            initial_balance=initial_balance
        )

        # Create executor wrapper (MexcFuturesOrderExecutor works with both adapters)
        executor = MexcFuturesOrderExecutor(
            mexc_adapter=paper_adapter,
            logger=self.logger,
            default_leverage=default_leverage
        )

        self.logger.info("trade_executor_factory.paper_executor_created", {
            "mode": "paper",
            "initial_balance": initial_balance,
            "leverage": default_leverage
        })

        return executor
