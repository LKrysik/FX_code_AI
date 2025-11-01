"""
Diagnostic Script: MEXC Snapshot Connection Issue
==================================================

This script diagnoses the "no_connection_for_snapshot" issue by:
1. Monitoring pending subscriptions state during subscription phase
2. Tracking confirmation order and timing
3. Verifying snapshot refresh task creation
4. Detecting race conditions in subscription confirmation

Usage:
    python scripts/diagnostic_snapshot_issue.py

Requirements:
    - Backend must be running
    - Start data collection and observe the diagnostic output
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, List, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.event_bus import EventBus
from core.logger import StructuredLogger


class SnapshotIssueDiagnostic:
    """Diagnostic tool for tracking subscription and snapshot task creation"""

    def __init__(self):
        self.logger = StructuredLogger()
        self.event_bus = EventBus()

        # Tracking structures
        self.subscription_timeline: List[Dict[str, Any]] = []
        self.pending_state: Dict[int, Dict[str, Dict[str, str]]] = {}
        self.snapshot_tasks_started: Set[str] = set()
        self.confirmation_order: List[Dict[str, Any]] = []
        self.symbols_subscribed: Set[str] = set()
        self.symbol_to_connection: Dict[str, int] = {}

        # Issue detection
        self.race_conditions_detected: List[Dict[str, Any]] = []
        self.missing_snapshot_tasks: Set[str] = set()

        # Subscribe to relevant events
        self.event_bus.subscribe("mexc_adapter.*", self._handle_mexc_event)

    async def _handle_mexc_event(self, event_type: str, data: Dict[str, Any]):
        """Process MEXC adapter events"""
        timestamp = datetime.now().isoformat()

        # Log all events
        self.subscription_timeline.append({
            "timestamp": timestamp,
            "event_type": event_type,
            "data": data.copy()
        })

        # Track specific event types
        if event_type == "mexc_adapter.subscribing":
            symbol = data.get("symbol")
            connection_id = data.get("connection_id")

            self.symbols_subscribed.add(symbol)
            self.symbol_to_connection[symbol] = connection_id

            print(f"[{timestamp}] 📝 SUBSCRIBING: {symbol} on connection {connection_id}")

        elif event_type == "mexc_adapter.futures_subscription_confirmed":
            connection_id = data.get("connection_id")
            symbol = data.get("symbol", "unknown")
            channel = data.get("channel")
            subscription_type = data.get("subscription_type")

            self.confirmation_order.append({
                "timestamp": timestamp,
                "connection_id": connection_id,
                "symbol": symbol,
                "channel": channel,
                "subscription_type": subscription_type
            })

            if symbol == "unknown":
                print(f"[{timestamp}] ⚠️  UNKNOWN SYMBOL CONFIRMATION: {subscription_type} on connection {connection_id}")
                print(f"    Channel: {channel}")
                print(f"    This indicates a race condition!")

                # Try to identify which symbol this might be
                self._detect_race_condition(connection_id, subscription_type, timestamp)
            else:
                print(f"[{timestamp}] ✅ CONFIRMED: {symbol} - {subscription_type}")

        elif event_type == "mexc_adapter.snapshot_refresh_task_started":
            symbol = data.get("symbol")
            self.snapshot_tasks_started.add(symbol)
            print(f"[{timestamp}] 🔄 SNAPSHOT TASK STARTED: {symbol}")

        elif event_type == "mexc_adapter.no_connection_for_snapshot":
            symbol = data.get("symbol")
            print(f"[{timestamp}] ❌ NO CONNECTION FOR SNAPSHOT: {symbol}")

            if symbol not in self.snapshot_tasks_started:
                self.missing_snapshot_tasks.add(symbol)
                print(f"    ⚠️  Snapshot task was NEVER started for {symbol}!")

    def _detect_race_condition(self, connection_id: int, subscription_type: str, timestamp: str):
        """Detect which symbol had a race condition"""
        # Find recently subscribed symbols on this connection
        recent_symbols = [
            s for s, c in self.symbol_to_connection.items()
            if c == connection_id and s not in [conf["symbol"] for conf in self.confirmation_order if conf["symbol"] != "unknown"]
        ]

        if recent_symbols:
            print(f"    Likely affected symbols: {', '.join(recent_symbols)}")
            self.race_conditions_detected.append({
                "timestamp": timestamp,
                "connection_id": connection_id,
                "subscription_type": subscription_type,
                "likely_symbols": recent_symbols
            })

    async def run_continuous_monitoring(self, duration: int = 600):
        """Run monitoring for specified duration (default 10 minutes)"""
        print("=" * 80)
        print("MEXC Snapshot Issue Diagnostic Tool")
        print("=" * 80)
        print(f"Monitoring for {duration} seconds...")
        print("Start data collection now and watch for issues.\n")

        await asyncio.sleep(duration)

        print("\n" + "=" * 80)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 80)

        self._print_summary()

    def _print_summary(self):
        """Print diagnostic summary"""
        print(f"\n📊 STATISTICS:")
        print(f"   Total symbols subscribed: {len(self.symbols_subscribed)}")
        print(f"   Snapshot tasks started: {len(self.snapshot_tasks_started)}")
        print(f"   Missing snapshot tasks: {len(self.missing_snapshot_tasks)}")
        print(f"   Race conditions detected: {len(self.race_conditions_detected)}")

        if self.missing_snapshot_tasks:
            print(f"\n⚠️  SYMBOLS WITHOUT SNAPSHOT TASKS:")
            for symbol in sorted(self.missing_snapshot_tasks):
                print(f"   - {symbol}")

        if self.race_conditions_detected:
            print(f"\n🔍 RACE CONDITIONS DETECTED:")
            for rc in self.race_conditions_detected:
                print(f"   - Connection {rc['connection_id']}: {rc['subscription_type']}")
                print(f"     Timestamp: {rc['timestamp']}")
                print(f"     Likely symbols: {', '.join(rc['likely_symbols'])}")

        print(f"\n📝 CONFIRMATION ORDER ANALYSIS:")
        # Group by symbol
        by_symbol: Dict[str, List[str]] = {}
        for conf in self.confirmation_order:
            symbol = conf['symbol']
            if symbol not in by_symbol:
                by_symbol[symbol] = []
            by_symbol[symbol].append(conf['subscription_type'])

        for symbol in sorted(by_symbol.keys()):
            types = by_symbol[symbol]
            print(f"   {symbol}: {' → '.join(types)}")

            # Check for depth_full arriving after deal+depth
            if 'deals' in types and 'depth' in types and 'depth.full' in types:
                deal_idx = types.index('deals')
                depth_idx = types.index('depth')
                depth_full_idx = types.index('depth.full')

                if depth_full_idx > max(deal_idx, depth_idx):
                    print(f"      ⚠️  depth.full arrived AFTER deal+depth (race condition risk)")

        # Save detailed log
        log_file = Path(__file__).parent.parent / "diagnostic_output.json"
        with open(log_file, 'w') as f:
            json.dump({
                "symbols_subscribed": list(self.symbols_subscribed),
                "snapshot_tasks_started": list(self.snapshot_tasks_started),
                "missing_snapshot_tasks": list(self.missing_snapshot_tasks),
                "race_conditions": self.race_conditions_detected,
                "confirmation_order": self.confirmation_order,
                "timeline": self.subscription_timeline
            }, f, indent=2)

        print(f"\n💾 Detailed log saved to: {log_file}")


async def main():
    """Main entry point"""
    diagnostic = SnapshotIssueDiagnostic()

    try:
        await diagnostic.run_continuous_monitoring(duration=600)  # 10 minutes
    except KeyboardInterrupt:
        print("\n\nMonitoring interrupted by user.")
        diagnostic._print_summary()


if __name__ == "__main__":
    asyncio.run(main())
