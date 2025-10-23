"""
Event Constants - Centralized Event Type Definitions
===================================================
Single source of truth for all event type names used across the system.
Prevents typos and ensures consistency in event-driven communication.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from enum import Enum


class EventType:
    """
    Centralized event type constants.
    All event names should be defined here to ensure consistency.
    """
    
    # Market Data Events
    MARKET_PRICE_UPDATE = "market.price_update"
    MARKET_ORDERBOOK_UPDATE = "market.orderbook_update"
    MARKET_VOLUME_UPDATE = "market.volume_update"
    MARKET_TICKER_UPDATE = "market.ticker_update"
    
    # Signal Detection Events
    PUMP_DETECTED = "pump.detected"
    DUMP_DETECTED = "dump.detected"
    REVERSAL_DETECTED = "reversal.detected"
    SIGNAL_DETECTED = "signal.detected"
    
    # Trading Events
    ORDER_PLACED = "order.placed"
    ORDER_FILLED = "order.filled"
    ORDER_REJECTED = "order.rejected"
    ORDER_CANCELLED = "order.cancelled"
    ORDER_EXPIRED = "order.expired"
    
    # Position Events
    POSITION_OPENING = "position.opening"
    POSITION_OPENED = "position.opened"
    POSITION_CLOSING = "position.closing"
    POSITION_CLOSED = "position.closed"
    POSITION_UPDATED = "position.updated"
    
    # Risk Management Events
    STOP_LOSS_TRIGGERED = "risk.stop_loss_triggered"
    TAKE_PROFIT_TRIGGERED = "risk.take_profit_triggered"
    EMERGENCY_CONDITION_DETECTED = "risk.emergency_condition_detected"
    RISK_LIMIT_EXCEEDED = "risk.limit_exceeded"
    
    # Entry System Events
    ENTRY_CONDITIONS_PASSED = "entry.conditions_passed"
    ENTRY_CONDITIONS_FAILED = "entry.conditions_failed"
    ENTRY_SIGNAL_GENERATED = "entry.signal_generated"
    
    # System Events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_HEALTH_CHECK = "system.health_check"
    
    # Exchange Events
    EXCHANGE_CONNECTED = "exchange.connected"
    EXCHANGE_DISCONNECTED = "exchange.disconnected"
    EXCHANGE_ERROR = "exchange.error"
    EXCHANGE_RECONNECTING = "exchange.reconnecting"
    
    # Configuration Events
    CONFIG_LOADED = "config.loaded"
    CONFIG_UPDATED = "config.updated"
    CONFIG_ERROR = "config.error"


@dataclass
class PriceEvent:
    """Standard price update event data structure"""
    symbol: str
    exchange: str
    price: float
    volume: float
    timestamp: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None


@dataclass
class SignalEvent:
    """Standard signal detection event data structure"""
    signal_type: str
    symbol: str
    exchange: str
    confidence: float
    magnitude: float
    timestamp: float
    metadata: Dict[str, Any]


@dataclass
class OrderEvent:
    """Standard order event data structure"""
    order_id: str
    symbol: str
    exchange: str
    side: str
    size: float
    price: Optional[float]
    order_type: str
    status: str
    timestamp: float
    filled_price: Optional[float] = None
    filled_size: Optional[float] = None
    fee: Optional[float] = None


@dataclass
class PositionEvent:
    """Standard position event data structure"""
    position_id: str
    symbol: str
    exchange: str
    side: str
    size: float
    entry_price: float
    current_price: Optional[float]
    unrealized_pnl: Optional[float]
    status: str
    timestamp: float


class EventValidator:
    """
    Validates event data structures to ensure consistency.
    """
    
    @staticmethod
    def validate_price_event(data: Dict[str, Any]) -> bool:
        """Validate price event data structure"""
        required_fields = ['symbol', 'exchange', 'price', 'volume', 'timestamp']
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_signal_event(data: Dict[str, Any]) -> bool:
        """Validate signal event data structure"""
        required_fields = ['signal_type', 'symbol', 'exchange', 'confidence', 'timestamp']
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_order_event(data: Dict[str, Any]) -> bool:
        """Validate order event data structure"""
        required_fields = ['order_id', 'symbol', 'exchange', 'side', 'size', 'order_type', 'status', 'timestamp']
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_position_event(data: Dict[str, Any]) -> bool:
        """Validate position event data structure"""
        required_fields = ['position_id', 'symbol', 'exchange', 'side', 'size', 'entry_price', 'status', 'timestamp']
        return all(field in data for field in required_fields)


# Event type validation mapping
EVENT_VALIDATORS = {
    EventType.MARKET_PRICE_UPDATE: EventValidator.validate_price_event,
    EventType.PUMP_DETECTED: EventValidator.validate_signal_event,
    EventType.DUMP_DETECTED: EventValidator.validate_signal_event,
    EventType.REVERSAL_DETECTED: EventValidator.validate_signal_event,
    EventType.SIGNAL_DETECTED: EventValidator.validate_signal_event,
    EventType.ORDER_PLACED: EventValidator.validate_order_event,
    EventType.ORDER_FILLED: EventValidator.validate_order_event,
    EventType.ORDER_REJECTED: EventValidator.validate_order_event,
    EventType.ORDER_CANCELLED: EventValidator.validate_order_event,
    EventType.POSITION_OPENING: EventValidator.validate_position_event,
    EventType.POSITION_OPENED: EventValidator.validate_position_event,
    EventType.POSITION_CLOSED: EventValidator.validate_position_event,
}


def validate_event(event_type: str, data: Dict[str, Any]) -> bool:
    """
    Validate event data against its expected structure.
    
    Args:
        event_type: The event type constant
        data: Event data dictionary
        
    Returns:
        True if valid, False otherwise
    """
    validator = EVENT_VALIDATORS.get(event_type)
    if validator:
        return validator(data)
    return True  # No validation defined, assume valid


def create_standard_event_data(source: str, **kwargs) -> Dict[str, Any]:
    """
    Create standard event data structure with common fields.
    
    Args:
        source: Source component name
        **kwargs: Additional event-specific data
        
    Returns:
        Event data dictionary with standard structure
    """
    import time
    
    return {
        'timestamp': time.time(),
        'source': source,
        **kwargs
    }