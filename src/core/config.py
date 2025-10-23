import json
import os
import re
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pathlib import Path
import copy

load_dotenv()

# ✅ ENHANCED: Regex patterns for comprehensive environment variable parsing
ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")
ENV_VAR_DEFAULT_PATTERN = re.compile(r"\$\{(\w+):-([^}]*)\}")
ENV_VAR_PARTIAL_PATTERN = re.compile(r"\$\{(\w+)(?::-([^}]*))?\}")

def _resolve_env_vars(data: Any) -> Any:
    """Recursively resolves environment variable placeholders with default values support."""
    if isinstance(data, dict):
        return {k: _resolve_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_resolve_env_vars(i) for i in data]
    elif isinstance(data, str):
        # Handle partial replacements within strings
        def replace_env_var(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.lastindex >= 2 else ""
            return os.getenv(var_name, default_value)
        
        # Replace all environment variable patterns in the string
        result = ENV_VAR_PARTIAL_PATTERN.sub(replace_env_var, data)
        return result
    return data

def _deep_merge_dicts(base: Dict, override: Dict) -> Dict:
    """
    Recursively merges the override dict into the base dict.
    Returns a new dictionary.
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = _deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result

class ExchangeConfig(BaseModel):
    enabled: bool
    ws_url: str
    futures_ws_url: Optional[str]
    ping_interval_s: int
    max_reconnect_attempts: int
    api_key: Optional[str]
    api_secret: Optional[str]
    testnet: Optional[bool]
    futures_api_url: Optional[str]
    max_leverage: Optional[int]
    default_leverage: Optional[int]
    max_connections: Optional[int]
    max_subscriptions_per_connection: Optional[int]

class NotificationChannelConfig(BaseModel):
    type: str
    enabled: bool
    name: str
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    from_email: Optional[str] = None
    to_emails: Optional[List[str]] = None

class PaperTradingConfig(BaseModel):
    initial_balance_usdt: float
    track_fees: bool
    maker_fee_pct: float
    taker_fee_pct: float
    slippage_pct: float

class PerformanceTrackingConfig(BaseModel):
    enabled: bool
    auto_optimization: bool
    report_frequency: str
    min_trades_for_optimization: int

class TradingConfig(BaseModel):
    enabled: bool
    mode: str
    paper_trading: PaperTradingConfig
    performance_tracking: PerformanceTrackingConfig

class LoggingConfig(BaseModel):
    level: str
    format: str
    file: str
    max_file_size_mb: int
    backup_count: int

class DataCollectionConfig(BaseModel):
    enabled: bool
    output_directory: str
    buffer_size: int
    flush_interval_s: int
    compression: bool
    retention_days: int

# Remove unused DataLoggerConfig - use DataCollectionConfig instead

class BacktestConfig(BaseModel):
    enabled: bool
    data_directory: str
    results_directory: str
    time_scale_factor: int
    parallel_processing: bool
    max_workers: int

# Simplified configuration schema for pump & dump trading
class ReversalDetectionConfig(BaseModel):
    enabled: bool
    min_retracement_pct: float
    retracement_confirmation_seconds: int
    volume_decline_threshold: float
    momentum_shift_required: bool

class FlashPumpDetectionConfig(BaseModel):
    enabled: bool
    min_pump_magnitude: float
    volume_surge_multiplier: float
    price_velocity_threshold: float
    peak_confirmation_window: int
    min_volume_24h_usdt: Optional[float]
    reversal_detection: ReversalDetectionConfig

class SafetyLimitsConfig(BaseModel):
    max_daily_signals: int
    min_cooldown_minutes: int
    max_consecutive_losses: int
    max_drawdown_pct: float
    max_daily_trades: int
    daily_loss_limit_pct: float
    cooldown_after_loss_minutes: int
    cooldown_after_win_minutes: int

class TimeManagementConfig(BaseModel):
    max_position_minutes: int
    emergency_exit_after_minutes: int
    force_close_if_stagnant_minutes: int

class EntryConditionsConfig(BaseModel):
    min_pump_age: int
    max_entry_delay: int
    min_confidence_threshold: float
    max_spread_pct: Optional[float]
    min_liquidity_usdt: Optional[float]
    rsi_max: Optional[float]

class PositionSizingConfig(BaseModel):
    base_risk_pct: float
    max_position_size_usdt: float
    max_leverage: float
    scale_in_enabled: bool

class PositionManagementConfig(BaseModel):
    max_position_duration_minutes: int
    trailing_stop_loss_enabled: bool
    trailing_stop_loss_pct: float

class StopLossConfig(BaseModel):
    trailing_enabled: bool = False
    initial_pct: Optional[float] = None
    trailing_trigger_profit_pct: Optional[float] = None
    trailing_distance_pct: Optional[float] = None
    breakeven_move_after_pct: Optional[float] = None

class TakeProfitConfig(BaseModel):
    primary_target_pct: Optional[float] = None
    scale_out_at_50pct: bool = False
    final_target_pct: Optional[float] = None

class EmergencyConditionsConfig(BaseModel):
    max_spread_pct: float
    min_liquidity_usdt: float
    max_rsi: float
    min_volume_24h_usdt: float
    max_drawdown_pct: float
    spread_blowout_pct: float
    volume_death_threshold_pct: float

class RiskAnalysisWeightsConfig(BaseModel):
    magnitude: float
    volume_surge: float
    reversal_clarity: float
    market_conditions: float

class ScalerConfig(BaseModel):
    min: float
    max: float

class RiskAnalysisScalersConfig(BaseModel):
    magnitude: ScalerConfig
    volume_surge: ScalerConfig
    confidence: ScalerConfig
    spread: ScalerConfig
    liquidity: ScalerConfig

class RiskAnalysisConfig(BaseModel):
    weights: RiskAnalysisWeightsConfig
    scalers: RiskAnalysisScalersConfig

class RiskManagementConfig(BaseModel):
    stop_loss: Optional[StopLossConfig] = None
    take_profit: Optional[TakeProfitConfig] = None
    time_management: Optional[TimeManagementConfig] = None
    emergency_conditions: Optional[EmergencyConditionsConfig] = None
    max_concurrent_positions: Optional[int] = None
    max_daily_trades: Optional[int] = None
    max_position_value_usdt: Optional[float] = None

class MainConfig(BaseModel):
    version: str
    exchanges: Dict[str, ExchangeConfig]
    notifications: Dict[str, NotificationChannelConfig]
    trading: TradingConfig
    logging: LoggingConfig
    data_collection: DataCollectionConfig
    risk_management: Optional[RiskManagementConfig] = None
    position_sizing: Optional[PositionSizingConfig] = None
    position_management: Optional[PositionManagementConfig] = None
    backtest: BacktestConfig
    # Symbol-specific sections, optional in main config
    entry_conditions: Optional[EntryConditionsConfig] = None
    safety_limits: Optional[SafetyLimitsConfig] = None
    risk_analysis: Optional[RiskAnalysisConfig] = None
    flash_pump_detection: Optional[FlashPumpDetectionConfig] = None

class SymbolConfig(BaseModel):
    symbol: str
    exchanges: List[str]
    market_type: str
    enabled: bool
    flash_pump_detection: FlashPumpDetectionConfig
    entry_conditions: EntryConditionsConfig
    position_sizing: PositionSizingConfig
    risk_management: RiskManagementConfig
    notification_channels: List[str]
    safety_limits: Optional[SafetyLimitsConfig] = None
    risk_analysis: Optional[RiskAnalysisConfig] = None

def load_main_config(path: str = "crypto_monitor/config/config.json") -> MainConfig:
    """Loads the main configuration file."""
    with open(path, 'r') as f:
        config_data = json.load(f)
    resolved_data = _resolve_env_vars(config_data)
    return MainConfig(**resolved_data)

def load_symbol_config(symbol: str, config_dir: str = "crypto_monitor/config/symbols") -> SymbolConfig:
    """Loads a symbol-specific configuration file."""
    path = Path(config_dir) / f"{symbol.upper()}.json"
    if not path.exists():
        raise FileNotFoundError(f"Symbol configuration not found for {symbol} at {path}")
    with open(path, 'r') as f:
        config_data = json.load(f)
    return SymbolConfig(**config_data)

def get_available_symbols(config_dir: str = "crypto_monitor/config/symbols") -> List[str]:
    """Returns a list of available symbols based on configuration files."""
    config_path = Path(config_dir)
    if not config_path.exists():
        return []
    
    symbols = []
    for file_path in config_path.glob("*.json"):
        symbol = file_path.stem
        symbols.append(symbol)
    
    return sorted(symbols)

def get_full_config(symbol: str) -> Dict:
    """
    Loads and merges the main and symbol-specific configurations.
    This is a helper for convenience, components should ideally
    receive the specific config objects they need.
    """
    main_config = load_main_config().model_dump()
    # Exclude None values to prevent overwriting main config sections with None
    symbol_config = load_symbol_config(symbol).model_dump(exclude_none=True)
    
    # Deep merge the dictionaries
    return _deep_merge_dicts(main_config, symbol_config)

def validate_config(symbol: str) -> bool:
    """Validates that both main and symbol configurations are valid."""
    try:
        _ = load_main_config()
        _ = load_symbol_config(symbol)
        return True
    except Exception as e:
        try:
            import logging
            logging.getLogger(__name__).error(
                "Configuration validation failed", extra={"symbol": symbol, "error": str(e)}
            )
        except Exception:
            pass
        return False
