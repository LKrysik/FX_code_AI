#!/usr/bin/env python3
"""
VWAP Signal Validation
======================

Validates VWAP-based trading signals with statistical rigor.
Tests if VWAP provides genuine trading edge.
"""

import asyncio
import time
import numpy as np
import statistics
import sys
import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine, IndicatorConfig
from src.core.event_bus import EventBus


@dataclass
class TradeSignal:
    """Represents a trading signal generated from VWAP."""
    timestamp: int
    signal: str  # "BUY" or "SELL"
    vwap: float
    price: float
    index: int


@dataclass
class SignalValidationResult:
    """Results of signal validation analysis."""
    total_signals: int
    signal_accuracy: float
    statistical_significance: Dict[str, any]
    sharpe_ratio: float
    recommendation: str
    returns: List[float]


class VWAPSignalValidator:
    """
    Validate VWAP-based trading signals with statistical rigor.
    """

    def __init__(self, transaction_cost_pct: float = 0.1):
        self.transaction_cost_pct = transaction_cost_pct

    async def validate_signals(self, historical_data: List[Dict], vwap_window_minutes: int = 5) -> SignalValidationResult:
        """
        Generate VWAP signals and validate their effectiveness.
        """
        signals = await self._generate_vwap_signals(historical_data, vwap_window_minutes)
        results = await self._evaluate_signal_performance(signals, historical_data)

        return SignalValidationResult(
            total_signals=len(signals),
            signal_accuracy=results["accuracy"],
            statistical_significance=results["statistical_significance"],
            sharpe_ratio=results["sharpe_ratio"],
            recommendation=self._generate_recommendation(results),
            returns=results["returns"]
        )

    async def _generate_vwap_signals(self, data: List[Dict], window_minutes: int) -> List[TradeSignal]:
        """Generate BUY/SELL signals based on VWAP crossovers."""
        signals = []

        # Use StreamingIndicatorEngine to calculate VWAP
        event_bus = EventBus()
        engine = StreamingIndicatorEngine(event_bus)

        # Register VWAP indicator
        engine.register_vwap_indicator(window_minutes=window_minutes, update_interval_seconds=1.0)

        # Feed historical data and collect VWAP values
        vwap_history = []

        for i, trade in enumerate(data):
            # Send market data to engine
            await engine._handle_market_data(trade)

            # Calculate VWAP for current window
            vwap = await engine.calculate_vwap(window_minutes)
            if vwap is not None:
                vwap_history.append((i, vwap, trade))

        # Generate signals based on price vs VWAP
        for i, vwap, trade in vwap_history:
            current_price = trade["price"]

            # Generate signals based on price relative to VWAP
            if current_price > vwap * 1.001:  # 0.1% above VWAP
                signal = "BUY"
            elif current_price < vwap * 0.999:  # 0.1% below VWAP
                signal = "SELL"
            else:
                continue

            signals.append(TradeSignal(
                timestamp=trade["timestamp"],
                signal=signal,
                vwap=vwap,
                price=current_price,
                index=i
            ))

        return signals

    async def _evaluate_signal_performance(self, signals: List[TradeSignal], data: List[Dict]) -> Dict[str, any]:
        """Evaluate the performance of generated signals."""
        if not signals:
            return {
                "accuracy": 0,
                "statistical_significance": {"significant": False, "p_value": 1.0, "t_statistic": 0},
                "sharpe_ratio": 0,
                "returns": []
            }

        returns = []

        for signal in signals:
            # Simulate holding for 5 minutes (assuming 1s data intervals)
            entry_idx = signal.index
            exit_idx = min(entry_idx + 300, len(data) - 1)  # 5 minutes at 1s intervals

            if exit_idx <= entry_idx:
                continue

            entry_price = data[entry_idx]["price"]
            exit_price = data[exit_idx]["price"]

            # Calculate return (BUY expects price increase, SELL expects decrease)
            if signal.signal == "BUY":
                return_pct = (exit_price - entry_price) / entry_price * 100
            else:  # SELL
                return_pct = (entry_price - exit_price) / entry_price * 100

            # Subtract transaction costs
            return_pct -= self.transaction_cost_pct

            returns.append(return_pct)

        if not returns:
            return {
                "accuracy": 0,
                "statistical_significance": {"significant": False, "p_value": 1.0, "t_statistic": 0},
                "sharpe_ratio": 0,
                "returns": []
            }

        # Calculate metrics
        accuracy = np.mean([r > 0 for r in returns])
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0

        # Simple statistical significance test (basic t-test approximation)
        if len(returns) > 1:
            mean_return = np.mean(returns)
            std_return = np.std(returns, ddof=1)  # Sample standard deviation
            t_stat = mean_return / (std_return / np.sqrt(len(returns))) if std_return > 0 else 0

            # Approximate p-value for t-distribution (simplified)
            # For large samples, t-distribution approaches normal
            p_value = 2 * (1 - 0.5 * (1 + np.sign(t_stat) * np.sqrt(1 - np.exp(-2 * t_stat**2 / np.pi))))
            significant = abs(t_stat) > 2.0  # Rough significance threshold
        else:
            t_stat = 0
            p_value = 1.0
            significant = False

        return {
            "accuracy": accuracy,
            "sharpe_ratio": sharpe_ratio,
            "statistical_significance": {
                "significant": significant,
                "p_value": p_value,
                "t_statistic": t_stat
            },
            "returns": returns
        }

    def _generate_recommendation(self, results: Dict) -> str:
        """Generate recommendation based on validation results."""
        accuracy = results.get("accuracy", 0)
        significant = results["statistical_significance"]["significant"]

        if accuracy > 0.55 and significant:
            return "ACCEPT - VWAP shows statistically significant edge"
        elif accuracy > 0.52:
            return "WEAK ACCEPT - VWAP shows some edge but needs monitoring"
        else:
            return "REJECT - VWAP does not show reliable edge"


async def generate_synthetic_market_data(num_trades: int = 3600) -> List[Dict]:
    """Generate synthetic market data with some VWAP-responsive patterns."""
    np.random.seed(42)  # For reproducible results

    data = []
    base_time = int(time.time() * 1000)
    base_price = 50000.0

    for i in range(num_trades):
        # Add some trend that VWAP should capture
        trend = (i / num_trades) * 200  # Gradual trend over the period
        noise = np.random.normal(0, 50)  # Random noise
        volume = 1.0 + np.random.exponential(2)  # Variable volume

        price = base_price + trend + noise

        data.append({
            "price": price,
            "volume": volume,
            "timestamp": base_time + i * 1000  # 1 second intervals
        })

    return data


async def main():
    """Run VWAP signal validation."""
    print("VWAP Signal Validation")
    print("=" * 50)

    # Generate synthetic market data
    print("Generating synthetic market data...")
    historical_data = await generate_synthetic_market_data(3600)  # 1 hour of data
    print(f"Generated {len(historical_data)} trades")

    # Validate VWAP signals
    print("\nValidating VWAP signals...")
    validator = VWAPSignalValidator(transaction_cost_pct=0.1)
    results = await validator.validate_signals(historical_data, vwap_window_minutes=5)

    # Print results
    print("\nVWAP Signal Validation Results:")
    print(f"  Total signals: {results.total_signals}")
    print(".1%")
    print(".3f")
    print(f"  Statistical significance: {results.statistical_significance['significant']}")
    print(".3f")
    print(".3f")
    print(f"  Recommendation: {results.recommendation}")

    # Additional analysis
    if results.returns:
        print("\nSignal Performance Analysis:")
        print(".2f")
        print(".2f")
        print(".2f")
        print(f"  Best trade: {max(results.returns):.2f}%")
        print(f"  Worst trade: {min(results.returns):.2f}%")

        # Distribution analysis
        positive_trades = len([r for r in results.returns if r > 0])
        negative_trades = len([r for r in results.returns if r < 0])
        print(f"  Positive trades: {positive_trades}")
        print(f"  Negative trades: {negative_trades}")

    print("\n" + "=" * 50)

    # Return success based on recommendation
    return "ACCEPT" in results.recommendation


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)