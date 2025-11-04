"""
Unified Configuration Settings - Single Source of Truth
=======================
All application configuration using Pydantic Settings.
Replaces all existing config managers and config utilities.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, model_validator
from typing import Dict, List, Optional
from decimal import Decimal
from enum import Enum
import os
from pathlib import Path


class TradingMode(str, Enum):
    """Trading modes"""
    LIVE = "live"
    BACKTEST = "backtest"
    COLLECT = "collect"


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# === TRADING CONFIGURATION ===

class PaperTradingSettings(BaseSettings):
    """Paper trading configuration"""
    enabled: bool = Field(default=True, description="Enable paper trading")
    initial_balance_usdt: Decimal = Field(default=Decimal('10000'), description="Initial balance")
    
    class Config:
        env_prefix = "PAPER_"


class TradingSettings(BaseSettings):
    """Core trading configuration"""
    mode: TradingMode = Field(default=TradingMode.BACKTEST, description="Trading mode")
    paper_trading: PaperTradingSettings = Field(default_factory=PaperTradingSettings)

    # Live trading (TIER 1.1)
    live_trading_enabled: bool = Field(
        default=False,
        description="Enable LIVE trading with real exchange orders (DANGEROUS! Only enable with proper risk management)"
    )

    # Symbol configuration
    default_symbols: List[str] = Field(default_factory=lambda: ['BTC_USDT', 'ETH_USDT'], description="Trading symbols (must be configured)")
    
    # Execution settings
    execution_delay_seconds: Decimal = Field(default=Decimal('1.0'))
    max_slippage_pct: Decimal = Field(default=Decimal('0.1'))
    execution_timeout_seconds: int = Field(default=30)
    
    # Position limits
    max_open_positions: int = Field(default=3)
    max_position_size_usdt: Decimal = Field(default=Decimal('1000'))
    
    @field_validator('default_symbols')
    @classmethod
    def validate_symbol_formats(cls, v):
        """Validate symbol formatting; emptiness handled after model creation."""
        if not v:
            return []
        for symbol in v:
            if not isinstance(symbol, str) or len(symbol) < 3 or '_' not in symbol:
                raise ValueError(f"Invalid symbol format: '{symbol}'. Expected format: 'BASE_QUOTE' (e.g., 'BTC_USDT')")
        return v

    @model_validator(mode='after')
    def validate_symbols_for_mode(self):
        if not self.default_symbols and self.mode != TradingMode.COLLECT:
            raise ValueError(f"Trading mode '{self.mode}' requires at least one symbol to be configured")
        return self

    class Config:
        env_prefix = "TRADING_"


# === EXCHANGE CONFIGURATION ===

class ExchangeSettings(BaseSettings):
    """Exchange configuration"""
    # MEXC
    mexc_enabled: bool = Field(default=True)
    mexc_api_key: str = Field(default="", description="MEXC API Key")
    mexc_api_secret: str = Field(default="", description="MEXC API Secret")
    mexc_paper_trading: bool = Field(default=True)
    mexc_ws_url: str = Field(default="wss://contract.mexc.com/edge", description="MEXC Futures WebSocket URL")
    mexc_futures_ws_url: str = Field(default="wss://contract.mexc.com/edge", description="MEXC Futures WebSocket URL")
    mexc_max_subscriptions_per_connection: int = Field(default=30, description="Max subscriptions per WebSocket connection")
    mexc_max_connections: int = Field(default=5, description="Maximum WebSocket connections")
    mexc_max_reconnect_attempts: int = Field(default=5, description="Maximum reconnection attempts")
    
    # Bybit (for future use)
    bybit_enabled: bool = Field(default=False)
    bybit_api_key: str = Field(default="")
    bybit_api_secret: str = Field(default="")
    bybit_paper_trading: bool = Field(default=True)
    
    class Config:
        env_prefix = "EXCHANGE_"
    
    def get(self, exchange_name: str) -> dict:
        """DEPRECATED: Legacy compatibility method. Use direct attribute access instead.
        
        This method exposes credentials in plain dict format which poses security risks.
        Migrate to direct attribute access: settings.exchanges.mexc_api_key
        """
        import warnings
        warnings.warn(
            "ExchangeSettings.get() is deprecated and poses security risks. "
            "Use direct attribute access instead (e.g., settings.exchanges.mexc_api_key)",
            DeprecationWarning,
            stacklevel=2
        )
        
        if exchange_name.lower() == "mexc":
            # Return sanitized version without sensitive credentials
            return {
                "enabled": self.mexc_enabled,
                "api_key": "***" if self.mexc_api_key else "",  # Mask credentials
                "api_secret": "***" if self.mexc_api_secret else "",  # Mask credentials
                "paper_trading": self.mexc_paper_trading,
                "ws_url": self.mexc_ws_url,
                "futures_ws_url": self.mexc_futures_ws_url,
                "max_subscriptions_per_connection": self.mexc_max_subscriptions_per_connection,
                "max_connections": self.mexc_max_connections,
                "max_reconnect_attempts": self.mexc_max_reconnect_attempts
            }
        elif exchange_name.lower() == "bybit":
            return {
                "enabled": self.bybit_enabled,
                "api_key": "***" if self.bybit_api_key else "",  # Mask credentials
                "api_secret": "***" if self.bybit_api_secret else "",  # Mask credentials
                "paper_trading": self.bybit_paper_trading
            }
        return {}


# === DETECTION CONFIGURATION ===

class FlashPumpDetectionSettings(BaseSettings):
    """Flash pump detection configuration"""
    enabled: bool = Field(default=True)
    min_pump_magnitude: Decimal = Field(default=Decimal('7.0'), description="Minimum pump magnitude %")
    volume_surge_multiplier: Decimal = Field(default=Decimal('3.5'), description="Volume surge multiplier")
    price_velocity_threshold: Decimal = Field(default=Decimal('0.5'), description="Price velocity threshold")
    min_volume_24h_usdt: Decimal = Field(default=Decimal('100000'), description="Minimum 24h volume")
    peak_confirmation_window: int = Field(default=30, description="Peak confirmation window seconds")
    
    class Config:
        env_prefix = "PUMP_"


class ReversalDetectionSettings(BaseSettings):
    """Reversal detection configuration"""
    enabled: bool = Field(default=True)
    min_retracement_pct: Decimal = Field(default=Decimal('2.0'))
    retracement_confirmation_seconds: int = Field(default=10)
    volume_decline_threshold: Decimal = Field(default=Decimal('0.4'))
    momentum_shift_required: bool = Field(default=True)
    
    class Config:
        env_prefix = "REVERSAL_"


class EntryConditionsSettings(BaseSettings):
    """Entry conditions configuration"""
    entry_offset_pct: Decimal = Field(default=Decimal('0.5'), description="Offset from peak price for entry")
    min_pump_age_seconds: int = Field(default=5)
    max_entry_delay_seconds: int = Field(default=45)
    min_confidence_threshold: Decimal = Field(default=Decimal('60'))
    max_spread_pct: Decimal = Field(default=Decimal('2.0'))
    min_liquidity_usdt: Decimal = Field(default=Decimal('1000'))
    rsi_max: Decimal = Field(default=Decimal('70'))
    
    class Config:
        env_prefix = "ENTRY_"


# === RISK MANAGEMENT CONFIGURATION ===

class StopLossSettings(BaseSettings):
    """Stop loss configuration"""
    peak_buffer_pct: Decimal = Field(default=Decimal('8.0'))
    trailing_enabled: bool = Field(default=False)
    trailing_distance_pct: Decimal = Field(default=Decimal('3.0'))
    trailing_threshold_pct: Decimal = Field(default=Decimal('5.0'), description="Threshold to start trailing")
    trailing_adjustment_pct: Decimal = Field(default=Decimal('2.0'), description="Adjustment percentage for trailing stop")
    
    class Config:
        env_prefix = "STOP_"


class TakeProfitSettings(BaseSettings):
    """Take profit configuration"""
    quick_profit_pct: Decimal = Field(default=Decimal('3.0'))
    quick_profit_close_pct: Decimal = Field(default=Decimal('50.0'))
    levels: List[Dict[str, Decimal]] = Field(default_factory=lambda: [
        {'retracement_pct': Decimal('30'), 'close_pct': Decimal('30')},
        {'retracement_pct': Decimal('50'), 'close_pct': Decimal('40')},
        {'retracement_pct': Decimal('70'), 'close_pct': Decimal('30')}
    ])
    target_retracement_pct: Decimal = Field(default=Decimal('50.0'))
    partial_exit_enabled: bool = Field(default=False)
    partial_exit_pct: Decimal = Field(default=Decimal('50.0'))
    
    class Config:
        env_prefix = "PROFIT_"


class RiskManagementSettings(BaseSettings):
    """Risk management configuration"""
    stop_loss: StopLossSettings = Field(default_factory=StopLossSettings)
    take_profit: TakeProfitSettings = Field(default_factory=TakeProfitSettings)
    
    # Time limits
    time_limit_minutes: int = Field(default=15)
    force_close_minutes: int = Field(default=30)
    
    # Emergency conditions
    max_drawdown_pct: Decimal = Field(default=Decimal('6.0'))
    spread_blowout_pct: Decimal = Field(default=Decimal('5.0'))
    volume_death_threshold_pct: Decimal = Field(default=Decimal('80'))
    emergency_min_liquidity: Decimal = Field(default=Decimal('100'))
    
    class Config:
        env_prefix = "RISK_"


class SafetyLimitsSettings(BaseSettings):
    """Safety limits configuration"""
    max_daily_trades: int = Field(default=3)
    max_consecutive_losses: int = Field(default=2)
    daily_loss_limit_pct: Decimal = Field(default=Decimal('2.0'))
    min_cooldown_minutes: int = Field(default=30)
    
    class Config:
        env_prefix = "SAFETY_"


# === POSITION SIZING CONFIGURATION ===

class PositionSizingSettings(BaseSettings):
    """Position sizing configuration"""
    base_risk_pct: Decimal = Field(default=Decimal('2.0'))
    max_position_size_usdt: Decimal = Field(default=Decimal('1000'))
    max_leverage: Decimal = Field(default=Decimal('5'))
    
    # Dynamic sizing
    confidence_scaling_enabled: bool = Field(default=True)
    min_size_multiplier: Decimal = Field(default=Decimal('0.3'))
    max_size_multiplier: Decimal = Field(default=Decimal('1.0'))
    
    class Config:
        env_prefix = "SIZING_"


# === LOGGING CONFIGURATION ===

class LoggingSettings(BaseSettings):
    """Logging configuration"""
    level: LogLevel = Field(default=LogLevel.INFO)
    file_enabled: bool = Field(default=True)
    console_enabled: bool = Field(default=True)
    structured_logging: bool = Field(default=True)
    log_dir: str = Field(default="logs")
    max_file_size_mb: int = Field(default=100)
    backup_count: int = Field(default=5)
    
    class Config:
        env_prefix = "LOG_"


# === PERFORMANCE TRACKING CONFIGURATION ===

class PerformanceSettings(BaseSettings):
    """Performance tracking configuration"""
    enabled: bool = Field(default=True)
    auto_optimization: bool = Field(default=False)
    report_frequency: str = Field(default="daily")  # daily, hourly
    analysis_interval_seconds: int = Field(default=300)
    
    class Config:
        env_prefix = "PERF_"


# === BACKTEST CONFIGURATION ===

class BacktestSettings(BaseSettings):
    """Backtest configuration"""
    enabled: bool = Field(default=True, description="Enable backtest mode")
    data_directory: str = Field(default="data", description="Backtest data directory")
    results_directory: str = Field(default="backtest_results", description="Results output directory")
    time_scale_factor: float = Field(default=10.0, description="Time acceleration factor")
    parallel_processing: bool = Field(default=True, description="Enable parallel processing")
    max_workers: int = Field(default=4, description="Maximum worker threads")

    class Config:
        env_prefix = "BACKTEST_"


# === PERFORMANCE MONITORING CONFIGURATION ===

class PerformanceMonitoringSettings(BaseSettings):
    """Performance monitoring configuration"""
    latency_threshold_ms: int = Field(default=100, description="Latency threshold for warnings")
    cleanup_interval_seconds: int = Field(default=300, description="Cleanup interval in seconds")
    session_ttl_hours: int = Field(default=24, description="Session time-to-live in hours")
    max_latency_measurements: int = Field(default=1000, description="Maximum latency measurements to keep")

    class Config:
        env_prefix = "PERF_MONITOR_"


# === WEBSOCKET CONFIGURATION ===

class RateLimiterSettings(BaseSettings):
    """Rate limiter configuration"""
    max_connections_per_minute: int = Field(default=10, description="Maximum connections per minute")
    max_messages_per_minute: int = Field(default=60, description="Maximum messages per minute")
    block_duration_minutes: int = Field(default=5, description="Block duration in minutes")
    cleanup_interval_seconds: int = Field(default=300, description="Cleanup interval in seconds")

    class Config:
        env_prefix = "RATE_LIMIT_"


class WebSocketSettings(BaseSettings):
    """WebSocket configuration"""
    progress_update_interval_seconds: float = Field(default=1.0, description="Progress update interval")
    max_broadcast_queue_size: int = Field(default=5000, description="Maximum broadcast queue size")
    batch_flush_interval_seconds: float = Field(default=0.1, description="Batch flush interval")
    max_batch_size: int = Field(default=50, description="Maximum batch size")
    health_broadcast_interval_seconds: int = Field(default=5, description="Health broadcast interval")

    class Config:
        env_prefix = "WEBSOCKET_"


# === REDIS CONFIGURATION ===

class RedisSettings(BaseSettings):
    """Redis configuration for state persistence and caching"""
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=0, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")
    socket_timeout: int = Field(default=5, description="Socket timeout in seconds")
    socket_connect_timeout: int = Field(default=5, description="Socket connect timeout in seconds")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    max_connections: int = Field(default=20, description="Maximum connections in pool")
    decode_responses: bool = Field(default=True, description="Decode responses as strings")

    @property
    def url(self) -> str:
        """Generate Redis URL from settings"""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"

    class Config:
        env_prefix = "REDIS_"


# === MAIN APPLICATION SETTINGS ===

class AppSettings(BaseSettings):
    """Main application settings - Single Source of Truth"""
    
    # Core settings
    app_name: str = Field(default="Crypto Monitor")
    version: str = Field(default="2.0.0")
    debug: bool = Field(default=False)
    
    # Configuration sections
    trading: TradingSettings = Field(default_factory=TradingSettings)
    exchanges: ExchangeSettings = Field(default_factory=ExchangeSettings)
    
    # Detection settings
    flash_pump_detection: FlashPumpDetectionSettings = Field(default_factory=FlashPumpDetectionSettings)
    reversal_detection: ReversalDetectionSettings = Field(default_factory=ReversalDetectionSettings)
    entry_conditions: EntryConditionsSettings = Field(default_factory=EntryConditionsSettings)
    
    # Risk management
    risk_management: RiskManagementSettings = Field(default_factory=RiskManagementSettings)
    safety_limits: SafetyLimitsSettings = Field(default_factory=SafetyLimitsSettings)
    position_sizing: PositionSizingSettings = Field(default_factory=PositionSizingSettings)
    
    # System settings
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings)
    backtest: BacktestSettings = Field(default_factory=BacktestSettings)

    # Performance monitoring and WebSocket settings
    performance_monitoring: PerformanceMonitoringSettings = Field(default_factory=PerformanceMonitoringSettings)
    websocket: WebSocketSettings = Field(default_factory=WebSocketSettings)
    rate_limiter: RateLimiterSettings = Field(default_factory=RateLimiterSettings)

    # Redis settings for state persistence
    redis: RedisSettings = Field(default_factory=RedisSettings)
    
    # File paths
    config_dir: str = Field(default="config")
    data_dir: str = Field(default="data")
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"  # Allows TRADING__MODE=live
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from environment variables
        
        # JSON schema for validation
        json_schema_extra = {
            "example": {
                "trading": {
                    "mode": "backtest",
                    "paper_trading": {
                        "enabled": True,
                        "initial_balance_usdt": 10000
                    }
                },
                "flash_pump_detection": {
                    "enabled": True,
                    "min_pump_magnitude": 7.0
                }
            }
        }
    
    @field_validator('config_dir', 'data_dir')
    @classmethod
    def validate_directories(cls, v):
        """Ensure directories exist"""
        Path(v).mkdir(parents=True, exist_ok=True)
        return v


# === SETTINGS FACTORY FUNCTIONS ===
# Note: These functions create new instances - no singleton pattern
# Settings should be created once in main.py and passed through dependency injection
