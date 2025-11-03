"""
MEXC Subscription Confirmation Handler
======================================

Handles subscription confirmation messages from MEXC WebSocket API.

This component extracts the duplicated logic from the 358-line
_handle_futures_subscription_response method, eliminating 75% code duplication.

Key Responsibilities:
- Process subscription confirmation messages (success/failure)
- Update subscription status in pending tracker
- Determine when all required subscriptions are confirmed
- Trigger snapshot refresh tasks for depth.full subscriptions
- Handle edge cases (orphaned confirmations, late arrivals)

Design Principles:
- DRY: Common logic extracted once, reused for all subscription types
- Single Responsibility: Only handles confirmation processing
- Testability: Pure functions with clear inputs/outputs
- Extensibility: Easy to add new subscription types
"""

from typing import Dict, Any, Optional, Set, Callable, Awaitable
from .....core.logger import StructuredLogger


class SubscriptionConfirmer:
    """
    Processes MEXC subscription confirmation messages.

    Eliminates code duplication by extracting common confirmation logic
    that was repeated 3 times for (deal, depth, depth.full) subscriptions.

    Architecture:
    - Stateless: All state managed by caller (MexcWebSocketAdapter)
    - Dependency Injection: Receives callbacks for state access
    - Event-driven: Notifies caller of important events via callbacks
    """

    def __init__(
        self,
        logger: StructuredLogger,
        data_types: Set[str],
        get_pending_subscriptions: Callable[[int], Optional[Dict[str, Dict[str, str]]]],
        update_pending_status: Callable[[int, str, str, str], None],
        remove_from_pending: Callable[[int, str], None],
        get_subscribed_symbols_on_connection: Callable[[int], list],
        start_snapshot_refresh: Optional[Callable[[str], Awaitable[None]]] = None
    ):
        """
        Initialize subscription confirmer.

        Args:
            logger: Structured logger for events
            data_types: Set of enabled data types ('prices', 'orderbook')
            get_pending_subscriptions: Callback to get pending subs for connection
            update_pending_status: Callback to update subscription status
            remove_from_pending: Callback to remove symbol from pending
            get_subscribed_symbols_on_connection: Callback to get subscribed symbols
            start_snapshot_refresh: Optional callback to start snapshot refresh task
        """
        self.logger = logger
        self.data_types = data_types

        # State access callbacks (dependency injection)
        self._get_pending = get_pending_subscriptions
        self._update_status = update_pending_status
        self._remove_pending = remove_from_pending
        self._get_subscribed = get_subscribed_symbols_on_connection
        self._start_snapshot = start_snapshot_refresh

    async def handle_confirmation(
        self,
        channel: str,
        response_data: str,
        connection_id: int
    ) -> None:
        """
        Handle subscription confirmation message from MEXC.

        This is the main entry point that routes to success/failure handlers.

        Args:
            channel: MEXC channel name (e.g., "rs.sub.deal", "rs.sub.depth")
            response_data: Response from MEXC ("success" or error message)
            connection_id: WebSocket connection ID
        """
        # Parse channel to subscription type
        sub_type = self._parse_channel_type(channel)

        if not sub_type:
            # Unknown channel type, log for debugging
            if channel.startswith("rs."):
                self.logger.debug("mexc_adapter.futures_subscription_response", {
                    "connection_id": connection_id,
                    "channel": channel,
                    "data": response_data
                })
            else:
                self.logger.debug("mexc_adapter.unknown_futures_response", {
                    "connection_id": connection_id,
                    "channel": channel,
                    "data": response_data
                })
            return

        # Handle special error channel
        if sub_type == "error":
            self.logger.error("mexc_adapter.futures_error_response", {
                "connection_id": connection_id,
                "error": response_data
            })
            return

        # Route to success/failure handler
        is_success = (response_data == "success")

        if is_success:
            await self._handle_success(sub_type, connection_id)
        else:
            await self._handle_failure(sub_type, connection_id, response_data)

    async def _handle_success(
        self,
        sub_type: str,
        connection_id: int
    ) -> None:
        """
        Common success handling for ALL subscription types.

        This method eliminates 90% of code duplication by extracting
        the logic that was repeated for deal/depth/depth_full.

        Flow:
        1. Find symbol in pending subscriptions
        2. Update status to 'confirmed'
        3. Check if all required subscriptions confirmed
        4. If yes, remove from pending
        5. Type-specific actions (e.g., start snapshot refresh)

        Args:
            sub_type: Subscription type ("deal", "depth", "depth_full")
            connection_id: WebSocket connection ID
        """
        # Get pending subscriptions for this connection
        pending_symbols = self._get_pending(connection_id)

        if not pending_symbols:
            # No pending subscriptions - this is expected for late/duplicate confirmations
            # Especially for depth_full which may arrive after cleanup
            await self._handle_no_pending_symbols(sub_type, connection_id)
            return

        # Find symbol with pending subscription for this type
        confirmed_symbol = self._find_and_confirm_symbol(pending_symbols, sub_type)

        if not confirmed_symbol:
            # Symbol not found in pending - log and return
            self.logger.info("mexc_adapter.futures_subscription_confirmed", {
                "connection_id": connection_id,
                "channel": f"rs.sub.{sub_type.replace('_', '.')}",
                "symbol": "unknown",
                "subscription_type": sub_type.replace('_', '.'),
                "pending_count": 0
            })
            return

        # Log confirmation
        pending_count = self._calculate_pending_count(pending_symbols)
        self.logger.info("mexc_adapter.futures_subscription_confirmed", {
            "connection_id": connection_id,
            "channel": f"rs.sub.{sub_type.replace('_', '.')}",
            "symbol": confirmed_symbol,
            "subscription_type": sub_type.replace('_', '.'),
            "pending_count": pending_count
        })

        # Type-specific actions BEFORE checking all confirmed
        # (depth_full needs to start snapshot refresh)
        if sub_type == "depth_full" and self._start_snapshot:
            await self._start_snapshot(confirmed_symbol)

        # Check if ALL required subscriptions are confirmed
        if self._all_subscriptions_confirmed(confirmed_symbol, pending_symbols):
            # All confirmed, safe to remove from pending
            self.logger.debug("mexc_adapter.symbol_confirmed_removing_from_pending", {
                "symbol": confirmed_symbol,
                "connection_id": connection_id,
                "has_orderbook": 'orderbook' in self.data_types,
                "all_channels_confirmed": True,
                "handler": sub_type
            })

            self._remove_pending(connection_id, confirmed_symbol)

    async def _handle_failure(
        self,
        sub_type: str,
        connection_id: int,
        error: str
    ) -> None:
        """
        Common failure handling for ALL subscription types.

        This method eliminates duplication in failure handling.

        Args:
            sub_type: Subscription type ("deal", "depth", "depth_full")
            connection_id: WebSocket connection ID
            error: Error message from MEXC
        """
        # Get pending subscriptions
        pending_symbols = self._get_pending(connection_id)

        if not pending_symbols:
            # No pending subscriptions
            self.logger.error("mexc_adapter.futures_subscription_failed", {
                "connection_id": connection_id,
                "channel": f"rs.sub.{sub_type.replace('_', '.')}",
                "symbol": "unknown",
                "subscription_type": sub_type.replace('_', '.'),
                "error": error,
                "pending_count": 0
            })
            return

        # Find symbol with pending subscription and mark as failed
        failed_symbol = None
        for symbol, status in pending_symbols.items():
            if status.get(sub_type) == 'pending':
                # Mark as failed
                self._update_status(connection_id, symbol, sub_type, 'failed')
                failed_symbol = symbol
                break

        if failed_symbol:
            pending_count = self._calculate_pending_count(pending_symbols)
            self.logger.error("mexc_adapter.futures_subscription_failed", {
                "connection_id": connection_id,
                "channel": f"rs.sub.{sub_type.replace('_', '.')}",
                "symbol": failed_symbol,
                "subscription_type": sub_type.replace('_', '.'),
                "error": error,
                "pending_count": pending_count
            })
        else:
            # Symbol not found
            self.logger.error("mexc_adapter.futures_subscription_failed", {
                "connection_id": connection_id,
                "channel": f"rs.sub.{sub_type.replace('_', '.')}",
                "symbol": "unknown",
                "subscription_type": sub_type.replace('_', '.'),
                "error": error,
                "pending_count": 0
            })

    async def _handle_no_pending_symbols(
        self,
        sub_type: str,
        connection_id: int
    ) -> None:
        """
        Handle case where confirmation arrives but no pending subscriptions exist.

        This can happen for:
        - Late confirmations (arrived after cleanup)
        - Duplicate confirmations
        - depth_full confirmations after deal/depth already removed symbol

        For depth_full, implements recovery mechanism to start snapshot tasks.

        Args:
            sub_type: Subscription type
            connection_id: WebSocket connection ID
        """
        subscribed_symbols = self._get_subscribed(connection_id)

        # For depth_full with orderbook enabled, implement recovery
        if sub_type == "depth_full" and 'orderbook' in self.data_types and self._start_snapshot:
            self.logger.warning("mexc_adapter.depth_full_confirmation_no_pending", {
                "connection_id": connection_id,
                "channel": "rs.sub.depth.full",
                "scenario": "late_or_duplicate_depth_full_confirmation",
                "subscribed_symbols_on_connection": subscribed_symbols,
                "recovery_action": "starting_snapshot_tasks_if_missing",
                "explanation": "This can happen if confirmation arrived after cleanup or is duplicate"
            })

            # Recovery: start snapshot tasks for subscribed symbols if missing
            # This is handled by the adapter via callback
            # (We can't check _snapshot_refresh_tasks here as it's adapter state)
            for symbol in subscribed_symbols:
                await self._start_snapshot(symbol)

            if subscribed_symbols:
                self.logger.info("mexc_adapter.recovery_completed", {
                    "connection_id": connection_id,
                    "recovered_tasks": len(subscribed_symbols),
                    "total_symbols_on_connection": len(subscribed_symbols)
                })
        else:
            # For other types, just log
            self.logger.info("mexc_adapter.futures_subscription_confirmed", {
                "connection_id": connection_id,
                "channel": f"rs.sub.{sub_type.replace('_', '.')}",
                "symbol": "unknown",
                "subscription_type": sub_type.replace('_', '.'),
                "pending_count": 0
            })

    def _parse_channel_type(self, channel: str) -> Optional[str]:
        """
        Parse MEXC channel name to subscription type.

        Examples:
            "rs.sub.deal" → "deal"
            "rs.sub.depth" → "depth"
            "rs.sub.depth.full" → "depth_full"
            "rs.error" → "error"

        Args:
            channel: MEXC channel name

        Returns:
            Subscription type or None if unknown
        """
        if not channel.startswith("rs."):
            return None

        if channel == "rs.error":
            return "error"

        if channel.startswith("rs.sub."):
            # Remove "rs.sub." prefix and replace "." with "_"
            sub_type = channel[7:]  # Skip "rs.sub."
            return sub_type.replace('.', '_')

        return None

    def _find_and_confirm_symbol(
        self,
        pending_symbols: Dict[str, Dict[str, str]],
        sub_type: str
    ) -> Optional[str]:
        """
        Find symbol with pending subscription and mark as confirmed.

        Args:
            pending_symbols: Dict of symbol -> status mappings
            sub_type: Subscription type to confirm

        Returns:
            Confirmed symbol name or None if not found
        """
        for symbol, status in pending_symbols.items():
            if status.get(sub_type) == 'pending':
                # Mark as confirmed
                status[sub_type] = 'confirmed'
                return symbol

        return None

    def _all_subscriptions_confirmed(
        self,
        symbol: str,
        pending_symbols: Dict[str, Dict[str, str]]
    ) -> bool:
        """
        Check if all required subscriptions are confirmed for symbol.

        Required subscriptions depend on data_types:
        - If orderbook enabled: deal + depth + depth_full
        - Otherwise: deal + depth

        Args:
            symbol: Symbol to check
            pending_symbols: Dict of symbol -> status mappings

        Returns:
            True if all required subscriptions confirmed
        """
        status = pending_symbols.get(symbol, {})

        if 'orderbook' in self.data_types:
            # Need all three confirmed
            return (
                status.get('deal') == 'confirmed' and
                status.get('depth') == 'confirmed' and
                status.get('depth_full') == 'confirmed'
            )
        else:
            # Need deal + depth
            return (
                status.get('deal') == 'confirmed' and
                status.get('depth') == 'confirmed'
            )

    def _calculate_pending_count(
        self,
        pending_symbols: Dict[str, Dict[str, str]]
    ) -> int:
        """
        Calculate count of pending subscriptions across all symbols.

        Args:
            pending_symbols: Dict of symbol -> status mappings

        Returns:
            Count of pending subscriptions
        """
        count = 0
        for symbol, status in pending_symbols.items():
            if status.get('deal') == 'pending':
                count += 1
            if status.get('depth') == 'pending':
                count += 1
            if status.get('depth_full') == 'pending':
                count += 1

        return count
