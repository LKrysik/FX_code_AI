#!/usr/bin/env python3
"""
Strategy Evaluator
==================

Real-time strategy evaluation engine that processes indicator data into trading signals.
Implements pump detection logic using Sprint 2 validated weights and thresholds.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

from src.core.event_bus import EventBus


class SignalType(Enum):
    """Trading signal types."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    EMERGENCY_EXIT = "EMERGENCY_EXIT"


class RiskLevel(Enum):
    """Risk assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class PumpSignal:
    """Pump detection signal with confidence and sizing."""
    symbol: str
    signal_type: SignalType
    confidence: float  # 0.0 to 1.0
    position_size: float  # USD amount
    risk_level: RiskLevel
    indicators: Dict[str, float]
    timestamp: int
    reason: str


@dataclass
class StrategyConfig:
    """Strategy configuration loaded from YAML."""
    name: str
    version: str
    indicators: Dict[str, Any]
    weights: Dict[str, float]
    thresholds: Dict[str, float]
    risk_limits: Dict[str, Any]
    emergency_stops: Dict[str, Any]


class StrategyEvaluator:
    """
    Real-time strategy evaluation engine.

    Processes indicator updates into trading signals using validated pump detection logic.
    Integrates with EventBus for indicator consumption and signal publishing.
    """

    def __init__(self, event_bus: EventBus, config: StrategyConfig):
        self.event_bus = event_bus
        self.config = config
        self.running = False
        self.tasks: List[asyncio.Task] = []

        # Indicator state storage (latest values per symbol)
        self.indicator_state: Dict[str, Dict[str, Any]] = {}

        # Sprint 2 validated weights and baseline
        self.PUMP_SCORE_BASELINE = 48.67
        self.WEIGHTS = {
            "volume_surge_ratio": 0.30,
            "price_velocity": 0.50,
            "bid_ask_imbalance": 0.20
        }

        # Scaling factor for price velocity (from Sprint 2 analysis)
        self.PRICE_VELOCITY_SCALE = 1000.0

    async def start(self) -> None:
        """Start the strategy evaluator and subscribe to indicator events."""
        if self.running:
            return

        self.running = True

        # Subscribe to indicator updates
        await self.event_bus.subscribe("indicator.updated", self._handle_indicator_update)

        print(f"StrategyEvaluator started for strategy: {self.config.name}")

    async def stop(self) -> None:
        """Stop the strategy evaluator and cancel all tasks."""
        if not self.running:
            return

        self.running = False

        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        try:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass

        self.tasks = []
        print("StrategyEvaluator stopped")

    async def _handle_indicator_update(self, data: Dict[str, Any]) -> None:
        """Handle incoming indicator updates from EventBus."""
        if not isinstance(data, dict) or not self.running:
            return

        # Validate required fields
        required_fields = ["indicator", "value", "timestamp"]
        if not all(field in data for field in required_fields):
            return

        # Extract indicator data
        indicator_name = data["indicator"]
        value = data["value"]
        timestamp = data["timestamp"]

        # For now, assume symbol is embedded in indicator name or use default
        # In production, this should be extracted from the data
        symbol = self._extract_symbol_from_indicator(indicator_name)

        # Update indicator state
        if symbol not in self.indicator_state:
            self.indicator_state[symbol] = {}

        self.indicator_state[symbol][indicator_name] = {
            "value": value,
            "timestamp": timestamp
        }

        # Evaluate strategy for this symbol
        await self._evaluate_strategy_for_symbol(symbol)

    def _extract_symbol_from_indicator(self, indicator_name: str) -> str:
        """Extract symbol from indicator name (temporary implementation)."""
        # This is a simplified implementation
        # In production, symbols should be explicitly passed in indicator data
        return "BTC_USDT"  # Default for now

    async def _evaluate_strategy_for_symbol(self, symbol: str) -> None:
        """Evaluate strategy conditions for a specific symbol."""
        if symbol not in self.indicator_state:
            return

        indicator_data = self.indicator_state[symbol]

        # Check if we have all required indicators
        required_indicators = ["volume_surge_ratio", "price_velocity", "bid_ask_imbalance"]
        if not all(indicator in indicator_data for indicator in required_indicators):
            return

        # Extract indicator values
        vsr = indicator_data["volume_surge_ratio"]["value"]
        pv = indicator_data["price_velocity"]["value"]
        bai = indicator_data["bid_ask_imbalance"]["value"]

        # Calculate pump score using Sprint 2 validated formula
        pump_score = self._calculate_pump_score(vsr, pv, bai)

        # Determine signal type and confidence
        signal_type, confidence = self._determine_signal(pump_score)

        # Check risk limits
        if not self._check_risk_limits(symbol, confidence):
            signal_type = SignalType.HOLD
            confidence = 0.0

        # Calculate position size
        position_size = self._calculate_position_size(confidence)

        # Assess risk level
        risk_level = self._assess_risk_level(confidence, pump_score)

        # Create signal
        signal = PumpSignal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            position_size=position_size,
            risk_level=risk_level,
            indicators={
                "volume_surge_ratio": vsr,
                "price_velocity": pv,
                "bid_ask_imbalance": bai,
                "pump_score": pump_score
            },
            timestamp=int(time.time() * 1000),
            reason=self._generate_signal_reason(signal_type, pump_score, confidence)
        )

        # Publish signal
        await self._publish_signal(signal)

    def _calculate_pump_score(self, vsr: float, pv: float, bai: float) -> float:
        """Calculate pump score using Sprint 2 validated weights."""
        # Sprint 2 formula: score = (vsr * 0.30) + (pv * 1000 * 0.50) + (bai * 0.20)
        score = (
            vsr * self.WEIGHTS["volume_surge_ratio"] +
            (pv * self.PRICE_VELOCITY_SCALE) * self.WEIGHTS["price_velocity"] +
            bai * self.WEIGHTS["bid_ask_imbalance"]
        )
        return score

    def _determine_signal(self, pump_score: float) -> tuple[SignalType, float]:
        """Determine signal type and confidence from pump score."""
        # Normalize confidence against Sprint 2 baseline
        confidence = min(1.0, pump_score / self.PUMP_SCORE_BASELINE)

        if confidence >= 0.5:
            return SignalType.BUY, confidence
        elif confidence >= 0.3:
            return SignalType.HOLD, confidence
        else:
            return SignalType.HOLD, confidence

    def _check_risk_limits(self, symbol: str, confidence: float) -> bool:
        """Check if signal passes risk limits."""
        # Simplified risk checking - in production would check:
        # - Max concurrent positions
        # - Daily loss limits
        # - Position size limits
        # - Emergency stop conditions

        risk_limits = self.config.risk_limits

        # Check confidence threshold
        min_confidence = risk_limits.get("min_confidence", 0.5)
        if confidence < min_confidence:
            return False

        # Check max position size
        max_position_size = risk_limits.get("max_position_size", 1000.0)
        position_size = self._calculate_position_size(confidence)
        if position_size > max_position_size:
            return False

        return True

    def _calculate_position_size(self, confidence: float) -> float:
        """Calculate position size based on confidence."""
        # Simple linear scaling: higher confidence = larger position
        base_size = self.config.risk_limits.get("base_position_size", 100.0)
        max_size = self.config.risk_limits.get("max_position_size", 1000.0)

        # Scale position size with confidence
        position_size = base_size + (max_size - base_size) * confidence

        return min(position_size, max_size)

    def _assess_risk_level(self, confidence: float, pump_score: float) -> RiskLevel:
        """Assess risk level based on confidence and pump score."""
        if confidence >= 0.8 and pump_score > self.PUMP_SCORE_BASELINE:
            return RiskLevel.EXTREME
        elif confidence >= 0.6:
            return RiskLevel.HIGH
        elif confidence >= 0.4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _generate_signal_reason(self, signal_type: SignalType, pump_score: float, confidence: float) -> str:
        """Generate human-readable reason for the signal."""
        if signal_type == SignalType.BUY:
            return ".2f"
        elif signal_type == SignalType.SELL:
            return ".2f"
        else:
            return ".2f"

    async def _publish_signal(self, signal: PumpSignal) -> None:
        """Publish trading signal via EventBus."""
        signal_data = {
            "type": "strategy_signal",
            "strategy_name": self.config.name,
            "symbol": signal.symbol,
            "signal_type": signal.signal_type.value,
            "confidence": signal.confidence,
            "position_size": signal.position_size,
            "risk_level": signal.risk_level.value,
            "indicators": signal.indicators,
            "timestamp": signal.timestamp,
            "reason": signal.reason,
            # OrderManager required fields
            "side": "buy" if signal.signal_type.value == "BUY" else "sell",
            "quantity": signal.position_size,
            "price": signal.indicators.get("price", 0.0),
            # TradingPersistenceService fields
            "signal_id": f"signal_{self.config.name}_{signal.symbol}_{int(signal.timestamp * 1000)}",
            "strategy_id": self.config.name,
            "action": signal.signal_type.value,
            "triggered": True,
            "conditions_met": {"confidence": signal.confidence, "risk_level": signal.risk_level.value},
            "indicator_values": signal.indicators,
            "metadata": {"reason": signal.reason}
        }

        await self.event_bus.publish("signal_generated", signal_data)

    def get_strategy_status(self) -> Dict[str, Any]:
        """Get current strategy evaluation status."""
        return {
            "strategy_name": self.config.name,
            "version": self.config.version,
            "active_symbols": list(self.indicator_state.keys()),
            "indicator_counts": {symbol: len(data) for symbol, data in self.indicator_state.items()},
            "last_evaluation": int(time.time() * 1000)
        }

    def get_latest_signal(self, symbol: str) -> Optional[PumpSignal]:
        """Get the latest signal for a symbol (not implemented - would need signal history)."""
        # This would require maintaining signal history
        return None