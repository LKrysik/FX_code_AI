"""
Signal Adapter
==============

Adapts strategy signals from StrategyEvaluator to PaperTradingEngine format.
Handles signal filtering, transformation, and routing for paper trading.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..core.logger import StructuredLogger
from ..core.event_bus import EventBus
from .paper_trading_engine import PaperTradingEngine, TradingSignal, TradingSignalType


class SignalFilter(Enum):
    """Signal filtering options."""
    ALL = "all"
    HIGH_CONFIDENCE = "high_confidence"
    STRATEGY_SPECIFIC = "strategy_specific"
    SYMBOL_SPECIFIC = "symbol_specific"


@dataclass
class SignalFilterConfig:
    """Configuration for signal filtering."""
    filter_type: SignalFilter
    min_confidence: float = 0.0
    allowed_strategies: Optional[List[str]] = None
    allowed_symbols: Optional[List[str]] = None
    max_signals_per_minute: int = 10


class SignalAdapter:
    """
    Adapts and routes strategy signals to paper trading engine.

    Subscribes to strategy signals from EventBus, filters and transforms them,
    then forwards to PaperTradingEngine for execution.
    """

    def __init__(self,
                 event_bus: EventBus,
                 paper_trading_engine: PaperTradingEngine,
                 logger: StructuredLogger,
                 filter_config: Optional[SignalFilterConfig] = None):

        self.event_bus = event_bus
        self.paper_trading_engine = paper_trading_engine
        self.logger = logger

        # Default filter config
        self.filter_config = filter_config or SignalFilterConfig(
            filter_type=SignalFilter.ALL,
            min_confidence=0.5  # Only high confidence signals by default
        )

        # Signal rate limiting
        self.signal_timestamps: List[datetime] = []
        self.rate_limit_window_seconds = 60  # 1 minute window

        # Signal processing stats
        self.stats = {
            'signals_received': 0,
            'signals_filtered': 0,
            'signals_processed': 0,
            'signals_executed': 0,
            'signals_rejected': 0
        }

        self.logger.info("signal_adapter.initialized", {
            "filter_type": self.filter_config.filter_type.value,
            "min_confidence": self.filter_config.min_confidence,
            "rate_limit": self.filter_config.max_signals_per_minute
        })

    async def start(self) -> None:
        """Start the signal adapter and subscribe to strategy signals."""
        await self.event_bus.subscribe("strategy.signal", self._handle_strategy_signal)

        self.logger.info("signal_adapter.started")

    async def stop(self) -> None:
        """Stop the signal adapter."""
        # Note: EventBus unsubscribe would be implemented here if available
        self.logger.info("signal_adapter.stopped")

    async def _handle_strategy_signal(self, signal_data: Dict[str, Any]) -> None:
        """Handle incoming strategy signals from EventBus."""
        try:
            self.stats['signals_received'] += 1

            # Validate signal data
            if not self._validate_signal_data(signal_data):
                self.stats['signals_filtered'] += 1
                return

            # Apply filtering
            if not self._should_process_signal(signal_data):
                self.stats['signals_filtered'] += 1
                self.logger.debug("signal_adapter.signal_filtered", {
                    "strategy": signal_data.get("strategy_name"),
                    "symbol": signal_data.get("symbol"),
                    "confidence": signal_data.get("confidence")
                })
                return

            # Check rate limiting
            if not self._check_rate_limit():
                self.stats['signals_filtered'] += 1
                self.logger.debug("signal_adapter.signal_rate_limited", {
                    "strategy": signal_data.get("strategy_name"),
                    "symbol": signal_data.get("symbol")
                })
                return

            # Transform and process signal
            trading_signal = self._transform_signal(signal_data)
            if trading_signal:
                self.stats['signals_processed'] += 1
                await self._process_trading_signal(trading_signal)

        except Exception as e:
            self.logger.error("signal_adapter.signal_processing_error", {
                "error": str(e),
                "signal_data": signal_data
            })

    def _validate_signal_data(self, signal_data: Dict[str, Any]) -> bool:
        """Validate that signal data contains required fields."""
        required_fields = [
            "strategy_name", "symbol", "signal_type",
            "confidence", "position_size", "timestamp"
        ]

        return all(field in signal_data for field in required_fields)

    def _should_process_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Apply filtering rules to determine if signal should be processed."""
        config = self.filter_config

        # Confidence filter
        confidence = signal_data.get("confidence", 0.0)
        if confidence < config.min_confidence:
            return False

        # Strategy filter
        if config.allowed_strategies:
            strategy_name = signal_data.get("strategy_name")
            if strategy_name not in config.allowed_strategies:
                return False

        # Symbol filter
        if config.allowed_symbols:
            symbol = signal_data.get("symbol")
            if symbol not in config.allowed_symbols:
                return False

        # Signal type filter
        signal_type = signal_data.get("signal_type")
        if signal_type not in ["BUY", "SELL"]:
            return False  # Only process buy/sell signals

        return True

    def _check_rate_limit(self) -> bool:
        """Check if signal rate limit has been exceeded."""
        now = datetime.now()
        window_start = now

        # Remove old timestamps outside the window
        self.signal_timestamps = [
            ts for ts in self.signal_timestamps
            if (now - ts).total_seconds() <= self.rate_limit_window_seconds
        ]

        # Check if we're within limits
        if len(self.signal_timestamps) >= self.filter_config.max_signals_per_minute:
            return False

        # Add current timestamp
        self.signal_timestamps.append(now)
        return True

    def _transform_signal(self, signal_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Transform EventBus signal data to TradingSignal format."""
        try:
            # Map signal type
            signal_type_str = signal_data.get("signal_type", "")
            if signal_type_str == "BUY":
                action = TradingSignalType.BUY
            elif signal_type_str == "SELL":
                action = TradingSignalType.SELL
            elif signal_type_str == "EMERGENCY_EXIT":
                action = TradingSignalType.EMERGENCY_EXIT
            else:
                return None

            # Extract quantity from position_size (assuming USD amount)
            position_size_usd = signal_data.get("position_size", 0.0)

            # For emergency exit, we need to determine quantity from current position
            # This will be handled by the paper trading engine
            quantity = 0.0 if action == TradingSignalType.EMERGENCY_EXIT else position_size_usd

            # Create trading signal
            signal = TradingSignal(
                symbol=signal_data.get("symbol", ""),
                action=action,
                quantity=quantity,
                strategy_name=signal_data.get("strategy_name", ""),
                confidence=signal_data.get("confidence", 0.0),
                price=self._extract_price_from_signal(signal_data),
                timestamp=self._parse_timestamp(signal_data.get("timestamp"))
            )

            return signal

        except Exception as e:
            self.logger.error("signal_adapter.signal_transformation_error", {
                "error": str(e),
                "signal_data": signal_data
            })
            return None

    def _extract_price_from_signal(self, signal_data: Dict[str, Any]) -> Optional[float]:
        """Extract price information from signal data."""
        # Try different price fields that might be present
        price_fields = ["price", "current_price", "market_price", "last_price"]

        for field in price_fields:
            if field in signal_data and signal_data[field]:
                return float(signal_data[field])

        # If no price found, return None (engine will use default)
        return None

    def _parse_timestamp(self, timestamp: Any) -> datetime:
        """Parse timestamp from various formats."""
        if isinstance(timestamp, (int, float)):
            # Assume milliseconds since epoch
            import time
            return datetime.fromtimestamp(timestamp / 1000)
        elif isinstance(timestamp, str):
            # Try ISO format
            try:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                pass
        # Fallback to current time
        return datetime.now()

    async def _process_trading_signal(self, signal: TradingSignal) -> None:
        """Process the transformed trading signal."""
        try:
            # Send to paper trading engine
            order_id = await self.paper_trading_engine.process_signal(signal)

            if order_id:
                self.stats['signals_executed'] += 1
                self.logger.info("signal_adapter.signal_executed", {
                    "order_id": order_id,
                    "symbol": signal.symbol,
                    "action": signal.action.value,
                    "strategy": signal.strategy_name,
                    "confidence": signal.confidence
                })
            else:
                self.stats['signals_rejected'] += 1
                self.logger.debug("signal_adapter.signal_rejected", {
                    "symbol": signal.symbol,
                    "action": signal.action.value,
                    "strategy": signal.strategy_name,
                    "reason": "engine_rejection"
                })

        except Exception as e:
            self.logger.error("signal_adapter.signal_execution_error", {
                "error": str(e),
                "symbol": signal.symbol,
                "action": signal.action.value
            })

    def get_stats(self) -> Dict[str, Any]:
        """Get signal processing statistics."""
        return {
            **self.stats,
            'processing_rate': self._calculate_processing_rate(),
            'filter_efficiency': self._calculate_filter_efficiency(),
            'last_update': datetime.now().isoformat()
        }

    def _calculate_processing_rate(self) -> float:
        """Calculate signal processing rate (signals per minute)."""
        if not self.signal_timestamps:
            return 0.0

        # Use last 5 minutes for rate calculation
        now = datetime.now()
        recent_signals = [
            ts for ts in self.signal_timestamps
            if (now - ts).total_seconds() <= 300  # 5 minutes
        ]

        if len(recent_signals) < 2:
            return 0.0

        time_span = (recent_signals[-1] - recent_signals[0]).total_seconds() / 60  # minutes
        if time_span == 0:
            return 0.0

        return len(recent_signals) / time_span

    def _calculate_filter_efficiency(self) -> float:
        """Calculate filtering efficiency (percentage of signals that pass filters)."""
        total_signals = self.stats['signals_received']
        if total_signals == 0:
            return 0.0

        processed_signals = self.stats['signals_processed']
        return (processed_signals / total_signals) * 100

    def update_filter_config(self, new_config: SignalFilterConfig) -> None:
        """Update signal filtering configuration."""
        self.filter_config = new_config
        self.logger.info("signal_adapter.filter_config_updated", {
            "filter_type": new_config.filter_type.value,
            "min_confidence": new_config.min_confidence,
            "allowed_strategies": new_config.allowed_strategies,
            "allowed_symbols": new_config.allowed_symbols
        })

    async def emergency_stop(self) -> None:
        """Emergency stop - reject all incoming signals."""
        # Create a filter that rejects everything
        emergency_config = SignalFilterConfig(
            filter_type=SignalFilter.ALL,
            min_confidence=999.0  # Impossible to reach
        )
        self.update_filter_config(emergency_config)

        self.logger.warning("signal_adapter.emergency_stop_activated")