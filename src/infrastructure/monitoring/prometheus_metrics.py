"""
Prometheus Metrics for Live Trading System
==========================================

Production-grade Prometheus metrics collection for live trading monitoring.

Features:
- Order metrics (submitted, filled, failed, latency)
- Position metrics (open positions, unrealized PnL, margin ratio)
- Risk metrics (alerts, daily loss)
- System metrics (EventBus messages, circuit breaker state)
- EventBus integration for real-time metric collection
- Non-blocking metric collection

Critical Requirements:
- ✅ Subscribe to EventBus (from Agent 1)
- ✅ NO blocking calls in metric collection
- ✅ Prometheus format compliance
"""

import logging
import time
from typing import Dict, Any, Optional, ClassVar
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry

from ...core.event_bus import EventBus

logger = logging.getLogger(__name__)


# ==================== MODULE-LEVEL METRICS (Singleton Pattern) ====================
# Metrics are created once at module level to avoid duplicate registration

# Order Metrics
orders_submitted_total = Counter(
    'orders_submitted_total',
    'Total orders submitted to exchange',
    ['symbol', 'side', 'order_type']
)

orders_filled_total = Counter(
    'orders_filled_total',
    'Total orders filled by exchange',
    ['symbol', 'side']
)

orders_failed_total = Counter(
    'orders_failed_total',
    'Total orders failed',
    ['symbol', 'reason']
)

order_submission_latency = Histogram(
    'order_submission_latency_seconds',
    'Order submission latency in seconds',
    ['symbol'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Position Metrics
positions_open_total = Gauge(
    'positions_open_total',
    'Total number of open positions',
    ['symbol']
)

unrealized_pnl_usd = Gauge(
    'unrealized_pnl_usd',
    'Unrealized profit and loss in USD',
    ['symbol']
)

margin_ratio_percent = Gauge(
    'margin_ratio_percent',
    'Margin ratio as percentage (equity / maintenance_margin * 100)',
    ['symbol']
)

# Risk Metrics
risk_alerts_total = Counter(
    'risk_alerts_total',
    'Total risk alerts triggered',
    ['severity', 'alert_type']
)

daily_loss_percent = Gauge(
    'daily_loss_percent',
    'Daily loss as percentage of capital'
)

# System Metrics
event_bus_messages_total = Counter(
    'event_bus_messages_total',
    'Total EventBus messages published',
    ['topic']
)

circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=CLOSED, 1=HALF_OPEN, 2=OPEN)',
    ['service']
)


class PrometheusMetrics:
    """
    Prometheus metrics collector for live trading system.

    Subscribes to EventBus topics to collect metrics in real-time.
    All metric collection is non-blocking and asynchronous.

    Note: Metrics are defined at module level (singleton pattern) to avoid
    duplicate registration errors in Prometheus registry.
    """

    def __init__(self, event_bus: EventBus):
        """
        Initialize Prometheus metrics collector.

        Args:
            event_bus: EventBus instance for subscribing to events
        """
        self.event_bus = event_bus
        self._subscribed = False

        # Reference module-level metrics
        self.orders_submitted_total = orders_submitted_total
        self.orders_filled_total = orders_filled_total
        self.orders_failed_total = orders_failed_total
        self.order_submission_latency = order_submission_latency
        self.positions_open_total = positions_open_total
        self.unrealized_pnl_usd = unrealized_pnl_usd
        self.margin_ratio_percent = margin_ratio_percent
        self.risk_alerts_total = risk_alerts_total
        self.daily_loss_percent = daily_loss_percent
        self.event_bus_messages_total = event_bus_messages_total
        self.circuit_breaker_state = circuit_breaker_state

        logger.info("PrometheusMetrics initialized (EventBus integration ready)")

    def subscribe_to_events(self) -> None:
        """
        Subscribe to EventBus topics for metric collection.

        This method is idempotent - safe to call multiple times.
        """
        if self._subscribed:
            logger.warning("PrometheusMetrics already subscribed to EventBus")
            return

        # Subscribe to all relevant EventBus topics
        self.event_bus.subscribe("order_created", self._handle_order_created)
        self.event_bus.subscribe("order_filled", self._handle_order_filled)
        self.event_bus.subscribe("order_failed", self._handle_order_failed)
        self.event_bus.subscribe("position_updated", self._handle_position_updated)
        self.event_bus.subscribe("risk_alert", self._handle_risk_alert)

        # Subscribe to ALL EventBus topics for message counting
        # Note: This is a wildcard subscription for system metrics
        self.event_bus.subscribe("market_data", self._handle_eventbus_message)
        self.event_bus.subscribe("indicator_updated", self._handle_eventbus_message)
        self.event_bus.subscribe("signal_generated", self._handle_eventbus_message)
        self.event_bus.subscribe("order_created", self._handle_eventbus_message)
        self.event_bus.subscribe("order_filled", self._handle_eventbus_message)
        self.event_bus.subscribe("position_updated", self._handle_eventbus_message)
        self.event_bus.subscribe("risk_alert", self._handle_eventbus_message)

        self._subscribed = True
        logger.info("PrometheusMetrics subscribed to EventBus topics")

    def unsubscribe_from_events(self) -> None:
        """
        Unsubscribe from EventBus topics.

        Called during shutdown to clean up subscriptions.
        """
        if not self._subscribed:
            return

        # Unsubscribe from all topics
        self.event_bus.unsubscribe("order_created", self._handle_order_created)
        self.event_bus.unsubscribe("order_filled", self._handle_order_filled)
        self.event_bus.unsubscribe("order_failed", self._handle_order_failed)
        self.event_bus.unsubscribe("position_updated", self._handle_position_updated)
        self.event_bus.unsubscribe("risk_alert", self._handle_risk_alert)

        self.event_bus.unsubscribe("market_data", self._handle_eventbus_message)
        self.event_bus.unsubscribe("indicator_updated", self._handle_eventbus_message)
        self.event_bus.unsubscribe("signal_generated", self._handle_eventbus_message)
        self.event_bus.unsubscribe("order_created", self._handle_eventbus_message)
        self.event_bus.unsubscribe("order_filled", self._handle_eventbus_message)
        self.event_bus.unsubscribe("position_updated", self._handle_eventbus_message)
        self.event_bus.unsubscribe("risk_alert", self._handle_eventbus_message)

        self._subscribed = False
        logger.info("PrometheusMetrics unsubscribed from EventBus topics")

    # ==================== EVENT HANDLERS ====================

    async def _handle_order_created(self, data: Dict[str, Any]) -> None:
        """
        Handle order_created event from EventBus.

        Expected data structure:
        {
            "order_id": str,
            "symbol": str,
            "side": str (BUY/SELL),
            "quantity": float,
            "price": float (optional),
            "order_type": str (MARKET/LIMIT),
            "status": str,
            "exchange_order_id": str (optional),
            "timestamp": int (epoch ms),
            "submission_latency": float (optional, seconds)
        }
        """
        try:
            symbol = data.get("symbol", "UNKNOWN")
            side = data.get("side", "UNKNOWN")
            order_type = data.get("order_type", "MARKET")

            # Increment order submitted counter
            self.orders_submitted_total.labels(
                symbol=symbol,
                side=side,
                order_type=order_type
            ).inc()

            # Record submission latency if available
            if "submission_latency" in data:
                self.order_submission_latency.labels(symbol=symbol).observe(
                    data["submission_latency"]
                )

            logger.debug(f"Metric recorded: order_created (symbol={symbol}, side={side})")

        except Exception as e:
            logger.error(f"Error handling order_created metric: {e}", exc_info=True)

    async def _handle_order_filled(self, data: Dict[str, Any]) -> None:
        """
        Handle order_filled event from EventBus.

        Expected data structure:
        {
            "order_id": str,
            "symbol": str,
            "side": str,
            "exchange_order_id": str,
            "filled_price": float,
            "filled_quantity": float,
            "slippage": float,
            "timestamp": int (epoch ms)
        }
        """
        try:
            symbol = data.get("symbol", "UNKNOWN")
            side = data.get("side", "UNKNOWN")

            # Increment order filled counter
            self.orders_filled_total.labels(
                symbol=symbol,
                side=side
            ).inc()

            logger.debug(f"Metric recorded: order_filled (symbol={symbol}, side={side})")

        except Exception as e:
            logger.error(f"Error handling order_filled metric: {e}", exc_info=True)

    async def _handle_order_failed(self, data: Dict[str, Any]) -> None:
        """
        Handle order_failed event from EventBus.

        Expected data structure:
        {
            "order_id": str,
            "symbol": str,
            "reason": str,
            "error_message": str,
            "timestamp": int (epoch ms)
        }
        """
        try:
            symbol = data.get("symbol", "UNKNOWN")
            reason = data.get("reason", "unknown")

            # Increment order failed counter
            self.orders_failed_total.labels(
                symbol=symbol,
                reason=reason
            ).inc()

            logger.debug(f"Metric recorded: order_failed (symbol={symbol}, reason={reason})")

        except Exception as e:
            logger.error(f"Error handling order_failed metric: {e}", exc_info=True)

    async def _handle_position_updated(self, data: Dict[str, Any]) -> None:
        """
        Handle position_updated event from EventBus.

        Expected data structure:
        {
            "position_id": str,
            "symbol": str,
            "current_price": float,
            "entry_price": float,
            "quantity": float,
            "unrealized_pnl": float,
            "margin_ratio": float,
            "liquidation_price": float,
            "timestamp": int (epoch ms)
        }
        """
        try:
            symbol = data.get("symbol", "UNKNOWN")
            quantity = data.get("quantity", 0.0)
            unrealized_pnl = data.get("unrealized_pnl", 0.0)
            margin_ratio = data.get("margin_ratio", 0.0)

            # Update position metrics
            if quantity > 0:
                self.positions_open_total.labels(symbol=symbol).set(1)
            else:
                self.positions_open_total.labels(symbol=symbol).set(0)

            self.unrealized_pnl_usd.labels(symbol=symbol).set(unrealized_pnl)
            self.margin_ratio_percent.labels(symbol=symbol).set(margin_ratio * 100)

            logger.debug(f"Metric recorded: position_updated (symbol={symbol}, pnl={unrealized_pnl})")

        except Exception as e:
            logger.error(f"Error handling position_updated metric: {e}", exc_info=True)

    async def _handle_risk_alert(self, data: Dict[str, Any]) -> None:
        """
        Handle risk_alert event from EventBus.

        Expected data structure:
        {
            "severity": str (CRITICAL/WARNING/INFO),
            "alert_type": str,
            "message": str,
            "details": dict,
            "timestamp": int (epoch ms)
        }
        """
        try:
            severity = data.get("severity", "INFO")
            alert_type = data.get("alert_type", "unknown")

            # Increment risk alert counter
            self.risk_alerts_total.labels(
                severity=severity,
                alert_type=alert_type
            ).inc()

            logger.debug(f"Metric recorded: risk_alert (severity={severity}, type={alert_type})")

        except Exception as e:
            logger.error(f"Error handling risk_alert metric: {e}", exc_info=True)

    async def _handle_eventbus_message(self, data: Dict[str, Any]) -> None:
        """
        Handle all EventBus messages for system metrics.

        This is called for EVERY EventBus message to count total throughput.
        """
        try:
            # Determine topic from call stack or use a marker in data
            # For now, we'll use a simple approach: extract topic from data if available
            topic = data.get("_topic", "unknown")

            # Increment EventBus message counter
            self.event_bus_messages_total.labels(topic=topic).inc()

        except Exception as e:
            # Don't log for every message - too noisy
            pass

    # ==================== MANUAL METRIC UPDATES ====================

    def update_circuit_breaker_state(self, service: str, state: str) -> None:
        """
        Manually update circuit breaker state metric.

        Args:
            service: Service name (e.g., "mexc_adapter", "order_manager")
            state: Circuit breaker state (CLOSED, HALF_OPEN, OPEN)
        """
        state_map = {
            "CLOSED": 0,
            "HALF_OPEN": 1,
            "OPEN": 2
        }

        state_value = state_map.get(state, 0)
        self.circuit_breaker_state.labels(service=service).set(state_value)

        logger.debug(f"Metric updated: circuit_breaker_state (service={service}, state={state})")

    def update_daily_loss_percent(self, loss_percent: float) -> None:
        """
        Manually update daily loss percentage metric.

        Args:
            loss_percent: Daily loss as percentage (e.g., 5.0 for 5%)
        """
        self.daily_loss_percent.set(loss_percent)

        logger.debug(f"Metric updated: daily_loss_percent ({loss_percent}%)")

    # ==================== METRICS EXPORT ====================

    def get_metrics(self) -> bytes:
        """
        Get metrics in Prometheus exposition format.

        Returns:
            Metrics as bytes in Prometheus format
        """
        return generate_latest()

    def get_metrics_content_type(self) -> str:
        """
        Get the content type for Prometheus metrics.

        Returns:
            Content type string
        """
        return CONTENT_TYPE_LATEST

    # ==================== HEALTH CHECK ====================

    def get_health(self) -> Dict[str, Any]:
        """
        Get health status of metrics collector.

        Returns:
            Health status dict
        """
        return {
            "status": "healthy" if self._subscribed else "not_subscribed",
            "subscribed_to_eventbus": self._subscribed,
            "metrics_available": [
                "orders_submitted_total",
                "orders_filled_total",
                "orders_failed_total",
                "order_submission_latency",
                "positions_open_total",
                "unrealized_pnl_usd",
                "margin_ratio_percent",
                "risk_alerts_total",
                "daily_loss_percent",
                "event_bus_messages_total",
                "circuit_breaker_state"
            ]
        }


# Global singleton instance (initialized in container.py)
_metrics_instance: Optional[PrometheusMetrics] = None


def get_metrics_instance() -> Optional[PrometheusMetrics]:
    """
    Get the global metrics instance.

    Returns:
        PrometheusMetrics instance or None if not initialized
    """
    return _metrics_instance


def set_metrics_instance(instance: PrometheusMetrics) -> None:
    """
    Set the global metrics instance.

    This should only be called from container.py during initialization.

    Args:
        instance: PrometheusMetrics instance
    """
    global _metrics_instance
    _metrics_instance = instance
    logger.info("Global PrometheusMetrics instance set")
