#!/usr/bin/env python3
"""
Strategy Monitor - Console Dashboard
===================================

Real-time console dashboard for monitoring strategy evaluation and signals.
Provides live view of indicator values, confidence scores, and trading signals.
"""

import asyncio
import time
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import curses
import threading

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.event_bus import EventBus
from src.core.logger import StructuredLogger
from src.infrastructure.config.config_loader import get_settings_from_working_directory
from src.engine.strategy_evaluator import StrategyEvaluator, StrategyConfig
from src.config.strategy_config import StrategyConfigLoader


class ConsoleDashboard:
    """
    Real-time console dashboard for strategy monitoring.

    Displays live indicator values, confidence scores, signals, and system status.
    """

    def __init__(self, event_bus: EventBus, strategy_evaluator: StrategyEvaluator):
        self.event_bus = event_bus
        self.strategy_evaluator = strategy_evaluator
        self.running = False

        # Data storage
        self.latest_indicators: Dict[str, Dict[str, Any]] = {}
        self.latest_signals: Dict[str, Dict[str, Any]] = {}
        self.system_status: Dict[str, Any] = {}

        # Display settings
        self.refresh_rate = 1.0  # seconds
        self.max_signal_history = 10

    async def start(self):
        """Start the console dashboard."""
        if self.running:
            return

        self.running = True

        # Subscribe to events
        await self.event_bus.subscribe("indicator.updated", self._handle_indicator_update)
        await self.event_bus.subscribe("strategy.signal", self._handle_strategy_signal)

        # Start display loop
        display_task = asyncio.create_task(self._display_loop())
        self.tasks = [display_task]

        print("Strategy Monitor started. Press Ctrl+C to exit.")
        print("=" * 80)

    async def stop(self):
        """Stop the console dashboard."""
        if not self.running:
            return

        self.running = False

        # Cancel tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

        try:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass

    async def _handle_indicator_update(self, data: Dict[str, Any]):
        """Handle indicator update events."""
        if not isinstance(data, dict):
            return

        indicator_name = data.get("indicator", "unknown")
        symbol = "BTC_USDT"  # Simplified - should extract from data

        if symbol not in self.latest_indicators:
            self.latest_indicators[symbol] = {}

        self.latest_indicators[symbol][indicator_name] = {
            "value": data.get("value"),
            "timestamp": data.get("timestamp"),
            "status": data.get("status", "unknown")
        }

    async def _handle_strategy_signal(self, data: Dict[str, Any]):
        """Handle strategy signal events."""
        if not isinstance(data, dict):
            return

        symbol = data.get("symbol", "unknown")
        signal_type = data.get("signal_type", "unknown")

        signal_entry = {
            "type": signal_type,
            "confidence": data.get("confidence", 0.0),
            "position_size": data.get("position_size", 0.0),
            "risk_level": data.get("risk_level", "unknown"),
            "timestamp": data.get("timestamp"),
            "reason": data.get("reason", ""),
            "indicators": data.get("indicators", {})
        }

        # Keep only recent signals
        if symbol not in self.latest_signals:
            self.latest_signals[symbol] = []

        self.latest_signals[symbol].append(signal_entry)
        self.latest_signals[symbol] = self.latest_signals[symbol][-self.max_signal_history:]

    async def _display_loop(self):
        """Main display loop for the console dashboard."""
        while self.running:
            try:
                self._clear_screen()
                self._display_header()
                self._display_indicators()
                self._display_signals()
                self._display_system_status()

                await asyncio.sleep(self.refresh_rate)

            except Exception as e:
                print(f"Display error: {e}")
                await asyncio.sleep(1.0)

    def _clear_screen(self):
        """Clear the console screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def _display_header(self):
        """Display dashboard header."""
        print("🚀 STRATEGY MONITOR DASHBOARD")
        print("=" * 80)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Time: {timestamp} | Strategy: {self.strategy_evaluator.config.name}")
        print("-" * 80)

    def _display_indicators(self):
        """Display current indicator values."""
        print("📊 LIVE INDICATORS")
        print("-" * 40)

        if not self.latest_indicators:
            print("No indicator data received yet...")
            print()
            return

        for symbol, indicators in self.latest_indicators.items():
            print(f"Symbol: {symbol}")
            for indicator_name, data in indicators.items():
                value = data.get("value", "N/A")
                timestamp = data.get("timestamp", 0)
                age_seconds = (time.time() * 1000 - timestamp) / 1000 if timestamp else float('inf')

                # Format value
                if isinstance(value, float):
                    formatted_value = ".4f"
                else:
                    formatted_value = str(value)

                # Color code based on age
                if age_seconds < 5:
                    status = "🟢"
                elif age_seconds < 30:
                    status = "🟡"
                else:
                    status = "🔴"

                print(f"  {indicator_name}: {formatted_value} {status} ({age_seconds:.1f}s ago)")

        print()

    def _display_signals(self):
        """Display recent trading signals."""
        print("🎯 RECENT SIGNALS")
        print("-" * 40)

        if not self.latest_signals:
            print("No signals generated yet...")
            print()
            return

        for symbol, signals in self.latest_signals.items():
            print(f"Symbol: {symbol}")
            for signal in signals[-3:]:  # Show last 3 signals
                signal_type = signal.get("type", "UNKNOWN")
                confidence = signal.get("confidence", 0.0)
                position_size = signal.get("position_size", 0.0)
                risk_level = signal.get("risk_level", "unknown")
                timestamp = signal.get("timestamp", 0)

                # Format timestamp
                if timestamp:
                    dt = datetime.fromtimestamp(timestamp / 1000)
                    time_str = dt.strftime("%H:%M:%S")
                else:
                    time_str = "N/A"

                # Signal emoji
                if signal_type == "BUY":
                    emoji = "🟢"
                elif signal_type == "SELL":
                    emoji = "🔴"
                elif signal_type == "HOLD":
                    emoji = "🟡"
                else:
                    emoji = "⚪"

                print(f"  {emoji} {signal_type} | Conf: {confidence:.2f} | Size: ${position_size:.0f} | Risk: {risk_level} | {time_str}")

        print()

    def _display_system_status(self):
        """Display system status information."""
        print("⚙️ SYSTEM STATUS")
        print("-" * 40)

        # Strategy status
        strategy_status = self.strategy_evaluator.get_strategy_status()
        print(f"Active Symbols: {len(strategy_status.get('active_symbols', []))}")
        print(f"Total Indicators: {sum(strategy_status.get('indicator_counts', {}).values())}")

        # System health (simplified)
        print("EventBus: Active"        print("Indicator Engine: Active"        print("Strategy Evaluator: Active"
        print("-" * 80)
        print("Press Ctrl+C to exit")


async def main():
    """Main entry point for the strategy monitor."""
    try:
        # Initialize components
        settings = get_settings_from_working_directory()
        logger = StructuredLogger("StrategyMonitor", settings.logging)
        event_bus = EventBus()

        # Load strategy configuration
        config_loader = StrategyConfigLoader()
        try:
            strategy_config = config_loader.load_strategy("pump_detection")
        except FileNotFoundError:
            print("Creating default pump detection strategy...")
            strategy_config = config_loader.create_default_pump_strategy()

        # Create strategy evaluator
        strategy_evaluator = StrategyEvaluator(event_bus, strategy_config)

        # Create console dashboard
        dashboard = ConsoleDashboard(event_bus, strategy_evaluator)

        # Start components
        await strategy_evaluator.start()
        await dashboard.start()

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1.0)

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        try:
            await dashboard.stop()
            await strategy_evaluator.stop()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())