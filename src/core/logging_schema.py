"""
Logging Schema - Standardized Event Names and Data Structures
============================================================
Defines consistent logging event names and required fields for all components.
Ensures log correlation and analysis capabilities.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class LogLevel(Enum):
    """Standard log levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class LogEvent:
    """Standard log event structure"""
    event_name: str
    level: LogLevel
    required_fields: List[str]
    optional_fields: List[str]
    description: str


class LoggingSchema:
    """
    Centralized logging schema with standardized event names and structures.
    All components should use these event names for consistency.
    """
    
    # Core system events
    SYSTEM_STARTUP = LogEvent(
        event_name="system.startup",
        level=LogLevel.INFO,
        required_fields=["component", "version"],
        optional_fields=["config_loaded", "dependencies"],
        description="System component startup"
    )
    
    SYSTEM_SHUTDOWN = LogEvent(
        event_name="system.shutdown",
        level=LogLevel.INFO,
        required_fields=["component"],
        optional_fields=["cleanup_actions", "duration_seconds"],
        description="System component shutdown"
    )
    
    # Configuration events
    CONFIG_LOADED = LogEvent(
        event_name="config.loaded",
        level=LogLevel.INFO,
        required_fields=["config_type", "source"],
        optional_fields=["sections", "file_path"],
        description="Configuration loaded successfully"
    )
    
    CONFIG_ERROR = LogEvent(
        event_name="config.error",
        level=LogLevel.ERROR,
        required_fields=["config_type", "error"],
        optional_fields=["file_path", "fallback_used"],
        description="Configuration loading error"
    )
    
    # Signal detection events
    SIGNAL_DETECTED = LogEvent(
        event_name="signal.detected",
        level=LogLevel.INFO,
        required_fields=["symbol", "exchange", "signal_type", "confidence"],
        optional_fields=["magnitude", "volume_surge", "price_velocity", "metadata"],
        description="Trading signal detected"
    )

    # Pump/dump specific detection events
    PUMP_DETECTED = LogEvent(
        event_name="pump.detected",
        level=LogLevel.INFO,
        required_fields=["symbol", "exchange", "magnitude", "volume_surge", "velocity"],
        optional_fields=["baseline_price", "current_price", "conditions_met"],
        description="Flash pump conditions met"
    )

    REVERSAL_DETECTED = LogEvent(
        event_name="reversal.detected",
        level=LogLevel.INFO,
        required_fields=["symbol", "exchange", "retracement_pct", "volume_decline"],
        optional_fields=["confidence", "momentum_shift", "spread"],
        description="Flash pump reversal detected"
    )

    # Entry conditions
    ENTRY_CONDITIONS_PASSED = LogEvent(
        event_name="entry.conditions_passed",
        level=LogLevel.INFO,
        required_fields=["symbol", "confidence", "pump_age"],
        optional_fields=["spread", "liquidity", "rsi"],
        description="Entry conditions satisfied for pump signal"
    )

    ENTRY_CONDITIONS_REJECTED = LogEvent(
        event_name="entry.conditions_rejected",
        level=LogLevel.INFO,
        required_fields=["symbol", "confidence", "pump_age"],
        optional_fields=["rejection_details"],
        description="Entry conditions rejected for pump signal"
    )
    
    SIGNAL_ANALYZED = LogEvent(
        event_name="signal.analyzed",
        level=LogLevel.INFO,
        required_fields=["symbol", "exchange", "opportunity_score", "risk_level"],
        optional_fields=["recommendation", "entry_price", "stop_loss", "take_profit"],
        description="Signal analysis completed"
    )
    
    SIGNAL_REJECTED = LogEvent(
        event_name="signal.rejected",
        level=LogLevel.DEBUG,
        required_fields=["symbol", "exchange", "reason"],
        optional_fields=["confidence", "magnitude", "criteria_failed"],
        description="Signal rejected due to criteria"
    )
    
    # Position events
    POSITION_OPENING = LogEvent(
        event_name="position.opening",
        level=LogLevel.INFO,
        required_fields=["symbol", "exchange", "position_id", "side", "size"],
        optional_fields=["leverage", "entry_price", "stop_loss", "take_profit"],
        description="Position opening initiated"
    )
    
    POSITION_OPENED = LogEvent(
        event_name="position.opened",
        level=LogLevel.INFO,
        required_fields=["symbol", "exchange", "position_id", "entry_price", "size"],
        optional_fields=["leverage", "stop_loss", "take_profit", "fill_time"],
        description="Position successfully opened"
    )
    
    POSITION_UPDATED = LogEvent(
        event_name="position.updated",
        level=LogLevel.DEBUG,
        required_fields=["symbol", "exchange", "position_id", "current_price", "unrealized_pnl"],
        optional_fields=["pnl_pct", "duration_minutes", "risk_level"],
        description="Position price update"
    )
    
    POSITION_CLOSING = LogEvent(
        event_name="position.closing",
        level=LogLevel.INFO,
        required_fields=["symbol", "exchange", "position_id", "reason"],
        optional_fields=["close_type", "size_to_close", "current_price"],
        description="Position closing initiated"
    )
    
    POSITION_CLOSED = LogEvent(
        event_name="position.closed",
        level=LogLevel.INFO,
        required_fields=["symbol", "exchange", "position_id", "realized_pnl", "duration_minutes"],
        optional_fields=["close_price", "close_reason", "partial_closes"],
        description="Position successfully closed"
    )
    
    # Order events
    ORDER_PLACED = LogEvent(
        event_name="order.placed",
        level=LogLevel.INFO,
        required_fields=["order_id", "symbol", "exchange", "side", "size", "order_type"],
        optional_fields=["price", "leverage", "position_id"],
        description="Order placed successfully"
    )
    
    ORDER_FILLED = LogEvent(
        event_name="order.filled",
        level=LogLevel.INFO,
        required_fields=["order_id", "symbol", "exchange", "filled_price", "filled_size"],
        optional_fields=["fee", "execution_time", "position_id"],
        description="Order filled successfully"
    )
    
    ORDER_REJECTED = LogEvent(
        event_name="order.rejected",
        level=LogLevel.ERROR,
        required_fields=["order_id", "symbol", "exchange", "reason"],
        optional_fields=["order_type", "size", "price"],
        description="Order rejected by exchange"
    )
    
    # Risk management events
    RISK_CHECK = LogEvent(
        event_name="risk.check",
        level=LogLevel.DEBUG,
        required_fields=["symbol", "exchange", "check_type", "result"],
        optional_fields=["risk_level", "exposure", "limits"],
        description="Risk management check performed"
    )

    EMERGENCY_CONDITION_DETECTED = LogEvent(
        event_name="emergency_condition.detected",
        level=LogLevel.WARNING,
        required_fields=["symbol", "reasons"],
        optional_fields=["exchange", "details"],
        description="Emergency condition detected (e.g., extreme spread, magnitude)"
    )

    RISK_LIMIT_EXCEEDED = LogEvent(
        event_name="risk.limit_exceeded",
        level=LogLevel.WARNING,
        required_fields=["symbol", "exchange", "limit_type", "current_value", "limit_value"],
        optional_fields=["action_taken", "position_id"],
        description="Risk limit exceeded"
    )
    
    STOP_LOSS_TRIGGERED = LogEvent(
        event_name="risk.stop_loss_triggered",
        level=LogLevel.WARNING,
        required_fields=["symbol", "exchange", "position_id", "trigger_price", "stop_price"],
        optional_fields=["loss_amount", "loss_pct"],
        description="Stop loss triggered"
    )
    
    TAKE_PROFIT_TRIGGERED = LogEvent(
        event_name="risk.take_profit_triggered",
        level=LogLevel.INFO,
        required_fields=["symbol", "exchange", "position_id", "trigger_price", "target_price"],
        optional_fields=["profit_amount", "profit_pct", "level"],
        description="Take profit triggered"
    )
    
    # Market data events
    PRICE_UPDATE = LogEvent(
        event_name="market.price_update",
        level=LogLevel.DEBUG,
        required_fields=["symbol", "exchange", "price", "volume"],
        optional_fields=["timestamp", "bid", "ask", "change_pct"],
        description="Market price update received"
    )
    
    MARKET_DATA_ERROR = LogEvent(
        event_name="market.data_error",
        level=LogLevel.ERROR,
        required_fields=["symbol", "exchange", "error"],
        optional_fields=["error_code", "retry_count"],
        description="Market data feed error"
    )
    
    # Performance and monitoring events
    PERFORMANCE_METRICS = LogEvent(
        event_name="performance.metrics",
        level=LogLevel.INFO,
        required_fields=["component", "metric_type"],
        optional_fields=["value", "unit", "timestamp", "metadata"],
        description="Performance metrics update"
    )
    
    HEALTH_CHECK = LogEvent(
        event_name="system.health_check",
        level=LogLevel.DEBUG,
        required_fields=["component", "status"],
        optional_fields=["checks_passed", "checks_failed", "response_time"],
        description="System health check result"
    )
    
    @classmethod
    def get_all_events(cls) -> Dict[str, LogEvent]:
        """Get all defined log events"""
        events = {}
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if isinstance(attr, LogEvent):
                events[attr.event_name] = attr
        return events
    
    @classmethod
    def validate_log_data(cls, event_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate log data against schema and return validation result.
        
        Returns:
            Dict with 'valid', 'missing_fields', 'extra_fields' keys
        """
        events = cls.get_all_events()
        
        if event_name not in events:
            return {
                'valid': False,
                'error': f'Unknown event name: {event_name}',
                'missing_fields': [],
                'extra_fields': list(data.keys())
            }
        
        event = events[event_name]
        data_keys = set(data.keys())
        required_keys = set(event.required_fields)
        optional_keys = set(event.optional_fields)
        allowed_keys = required_keys | optional_keys
        
        missing_fields = required_keys - data_keys
        extra_fields = data_keys - allowed_keys
        
        return {
            'valid': len(missing_fields) == 0,
            'missing_fields': list(missing_fields),
            'extra_fields': list(extra_fields),
            'event': event
        }
    
    @classmethod
    def create_standard_log_data(cls, event_name: str, **kwargs) -> Dict[str, Any]:
        """
        Create standardized log data for an event.
        Ensures all required fields are present and adds common fields.
        """
        events = cls.get_all_events()
        
        if event_name not in events:
            raise ValueError(f"Unknown event name: {event_name}")
        
        event = events[event_name]
        
        # Start with provided data
        log_data = dict(kwargs)
        
        # Add common fields if not present
        if 'timestamp' not in log_data:
            import time
            log_data['timestamp'] = time.time()
        
        # Validate required fields
        validation = cls.validate_log_data(event_name, log_data)
        if not validation['valid']:
            missing = ', '.join(validation['missing_fields'])
            raise ValueError(f"Missing required fields for {event_name}: {missing}")
        
        return log_data


class StandardizedLogger:
    """
    Wrapper around StructuredLogger that enforces schema compliance.
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.schema = LoggingSchema()
    
    def log_event(self, event_name: str, level: Optional[LogLevel] = None, **kwargs):
        """Log an event using standardized schema"""
        try:
            log_data = self.schema.create_standard_log_data(event_name, **kwargs)
            
            # Use provided level or default from schema
            if level is None:
                events = self.schema.get_all_events()
                if event_name in events:
                    level = events[event_name].level
                else:
                    level = LogLevel.INFO
            
            # Log using appropriate level
            if level == LogLevel.DEBUG:
                self.logger.debug(event_name, log_data)
            elif level == LogLevel.INFO:
                self.logger.info(event_name, log_data)
            elif level == LogLevel.WARNING:
                self.logger.warning(event_name, log_data)
            elif level == LogLevel.ERROR:
                self.logger.error(event_name, log_data)
                
        except Exception as e:
            # Fallback logging if schema validation fails
            self.logger.error("logging.schema_error", {
                "event_name": event_name,
                "error": str(e),
                "data": kwargs
            })
    
    def signal_detected(self, symbol: str, exchange: str, signal_type: str, confidence: float, **kwargs):
        """Convenience method for signal detection events"""
        self.log_event("signal.detected", 
                      symbol=symbol, exchange=exchange, 
                      signal_type=signal_type, confidence=confidence, **kwargs)
    
    def position_opened(self, symbol: str, exchange: str, position_id: str, 
                       entry_price: float, size: float, **kwargs):
        """Convenience method for position opened events"""
        self.log_event("position.opened",
                      symbol=symbol, exchange=exchange, position_id=position_id,
                      entry_price=entry_price, size=size, **kwargs)
    
    def order_filled(self, order_id: str, symbol: str, exchange: str, 
                    filled_price: float, filled_size: float, **kwargs):
        """Convenience method for order filled events"""
        self.log_event("order.filled",
                      order_id=order_id, symbol=symbol, exchange=exchange,
                      filled_price=filled_price, filled_size=filled_size, **kwargs)
    
    # Delegate other methods to underlying logger
    def __getattr__(self, name):
        return getattr(self.logger, name)
