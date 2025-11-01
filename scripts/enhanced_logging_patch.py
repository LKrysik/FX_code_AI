"""
Enhanced Logging Patch for MEXC WebSocket Adapter
==================================================

This script adds detailed logging to track the subscription confirmation
race condition without modifying the core behavior.

Apply this by importing and monkey-patching the adapter, OR manually
add the logging statements to the adapter code.

Key additions:
1. Log pending subscription state before/after each confirmation
2. Log when symbols are removed from pending
3. Log when snapshot tasks should start but don't
4. Track timing between confirmations
"""

from typing import Dict, Any
import time


class EnhancedLoggingMixin:
    """Mixin to add enhanced logging to MexcWebSocketAdapter"""

    def _log_pending_state(self, operation: str, connection_id: int):
        """Log current pending subscriptions state"""
        if not hasattr(self, '_pending_subscriptions'):
            return

        pending = self._pending_subscriptions.get(connection_id, {})
        if pending:
            symbols_status = {}
            for symbol, status in pending.items():
                symbols_status[symbol] = {
                    k: v for k, v in status.items() if k != 'added_time'
                }

            self.logger.debug("mexc_adapter.pending_state", {
                "operation": operation,
                "connection_id": connection_id,
                "pending_symbols": symbols_status,
                "total_pending": len(pending)
            })

    def _log_symbol_removal(self, symbol: str, connection_id: int, reason: str):
        """Log when a symbol is removed from pending subscriptions"""
        self.logger.info("mexc_adapter.symbol_removed_from_pending", {
            "symbol": symbol,
            "connection_id": connection_id,
            "reason": reason,
            "remaining_pending": len(self._pending_subscriptions.get(connection_id, {}))
        })

    def _log_snapshot_task_check(self, symbol: str, connection_id: int, should_start: bool, started: bool):
        """Log snapshot task creation attempts"""
        if should_start and not started:
            self.logger.error("mexc_adapter.snapshot_task_not_started", {
                "symbol": symbol,
                "connection_id": connection_id,
                "reason": "symbol_not_in_pending",
                "subscribed_symbols_count": len(self._subscribed_symbols),
                "is_symbol_subscribed": symbol in self._subscribed_symbols,
                "has_connection_mapping": symbol in self._symbol_to_connection
            })

    def _log_confirmation_timing(self, symbol: str, subscription_type: str, connection_id: int):
        """Track timing between confirmations"""
        if not hasattr(self, '_confirmation_times'):
            self._confirmation_times = {}

        key = f"{connection_id}_{symbol}"
        if key not in self._confirmation_times:
            self._confirmation_times[key] = {}

        self._confirmation_times[key][subscription_type] = time.time()

        # Check if we have all three
        times = self._confirmation_times[key]
        if 'deals' in times and 'depth' in times and 'depth.full' in times:
            # Calculate order
            sorted_types = sorted(times.items(), key=lambda x: x[1])
            order = [t[0] for t in sorted_types]

            # Calculate time differences
            diffs = []
            for i in range(1, len(sorted_types)):
                diff_ms = (sorted_types[i][1] - sorted_types[i-1][1]) * 1000
                diffs.append(f"{sorted_types[i-1][0]}→{sorted_types[i][0]}: {diff_ms:.1f}ms")

            self.logger.info("mexc_adapter.confirmation_timing", {
                "symbol": symbol,
                "connection_id": connection_id,
                "order": " → ".join(order),
                "timing": ", ".join(diffs),
                "total_ms": (sorted_types[-1][1] - sorted_types[0][1]) * 1000
            })

            # Clean up
            del self._confirmation_times[key]


# Example usage instructions
USAGE_INSTRUCTIONS = """
USAGE INSTRUCTIONS
==================

To apply enhanced logging to your MEXC adapter, add the following
logging calls at key points in mexc_websocket_adapter.py:

1. In _handle_subscribe_confirmation_response(), ADD at the start of each channel handler:

   # Before processing confirmation
   self._log_pending_state(f"before_{channel}", connection_id)

2. AFTER marking a channel as confirmed, ADD:

   self._log_confirmation_timing(confirmed_symbol, subscription_type, connection_id)

3. When REMOVING a symbol from pending (lines 1328, 1401), ADD before del:

   self._log_symbol_removal(confirmed_symbol, connection_id, "deal_and_depth_confirmed")

4. In depth_full confirmation handler (line 1479), ADD after snapshot task start:

   self._log_snapshot_task_check(confirmed_symbol, connection_id,
                                  should_start=True, started=True)

5. When confirmed_symbol is None (symbol="unknown"), ADD:

   self._log_snapshot_task_check("unknown", connection_id,
                                  should_start=True, started=False)

6. At the end of each confirmation handler, ADD:

   self._log_pending_state(f"after_{channel}", connection_id)

ALTERNATIVE: Import this module and use monkey patching (not recommended for production).
"""


def generate_logging_additions():
    """Generate the exact code to add to mexc_websocket_adapter.py"""
    additions = []

    # Addition 1: In __init__
    additions.append({
        "location": "__init__ method, after line 200",
        "code": """
        # Enhanced diagnostic logging
        self._confirmation_times: Dict[str, Dict[str, float]] = {}  # Track confirmation timing
"""
    })

    # Addition 2: Deal confirmation handler
    additions.append({
        "location": "Deal confirmation handler, after line 1320",
        "code": """
                    if confirmed_symbol:
                        # ✅ DIAGNOSTIC: Log confirmation timing
                        self.logger.debug("mexc_adapter.confirmation_received", {
                            "symbol": confirmed_symbol,
                            "connection_id": connection_id,
                            "subscription_type": "deals",
                            "pending_before": {k: v for k, v in pending_symbols[confirmed_symbol].items() if k != 'added_time'}
                        })
"""
    })

    # Addition 3: Before symbol removal in deal handler
    additions.append({
        "location": "Deal confirmation handler, BEFORE line 1328 (del pending_symbols)",
        "code": """
                        # ✅ DIAGNOSTIC: Log symbol removal
                        self.logger.warning("mexc_adapter.symbol_removed_from_pending_early", {
                            "symbol": confirmed_symbol,
                            "connection_id": connection_id,
                            "reason": "deal_and_depth_confirmed",
                            "depth_full_status": pending_symbols[confirmed_symbol].get('depth_full', 'not_tracked'),
                            "this_is_the_bug": "depth_full confirmation will find 'unknown' symbol!"
                        })
"""
    })

    # Addition 4: In depth_full confirmation when symbol not found
    additions.append({
        "location": "depth_full confirmation handler, in else block at line 1481",
        "code": """
                    else:
                        # ✅ DIAGNOSTIC: Symbol not found - this is the bug!
                        # Try to find which symbol this confirmation belongs to
                        subscribed_on_conn = [s for s, c in self._symbol_to_connection.items() if c == connection_id]

                        self.logger.error("mexc_adapter.depth_full_confirmation_orphaned", {
                            "connection_id": connection_id,
                            "channel": channel,
                            "problem": "Symbol already removed from pending by deal/depth handlers",
                            "subscribed_symbols_on_connection": subscribed_on_conn,
                            "snapshot_refresh_task_NOT_started": "This is why no_connection_for_snapshot occurs",
                            "bug_location": "Lines 1328 and 1401 remove symbol before depth_full confirmation"
                        })
"""
    })

    # Addition 5: In _start_snapshot_refresh_task
    additions.append({
        "location": "_start_snapshot_refresh_task, at line 3167",
        "code": """
        if symbol in self._snapshot_refresh_tasks:
            # ✅ DIAGNOSTIC: Task already exists
            self.logger.debug("mexc_adapter.snapshot_task_already_exists", {
                "symbol": symbol
            })
            return

        # ✅ DIAGNOSTIC: Starting new task
        self.logger.info("mexc_adapter.starting_snapshot_refresh_task", {
            "symbol": symbol,
            "has_connection": symbol in self._symbol_to_connection,
            "connection_id": self._symbol_to_connection.get(symbol, "none"),
            "is_subscribed": symbol in self._subscribed_symbols
        })
"""
    })

    return additions


if __name__ == "__main__":
    print(USAGE_INSTRUCTIONS)
    print("\n" + "=" * 80)
    print("CODE ADDITIONS TO MAKE")
    print("=" * 80 + "\n")

    additions = generate_logging_additions()
    for i, addition in enumerate(additions, 1):
        print(f"{i}. {addition['location']}")
        print("-" * 80)
        print(addition['code'])
        print()
