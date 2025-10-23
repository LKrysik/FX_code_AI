"""
Symbol Configuration Manager
===========================
Manages per-symbol configuration with automatic fallback to defaults.
Supports template generation for new symbols.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from decimal import Decimal

from .settings import AppSettings, FlashPumpDetectionSettings, ReversalDetectionSettings, EntryConditionsSettings, PositionSizingSettings, RiskManagementSettings, SafetyLimitsSettings


class SymbolConfig(BaseModel):
    """Symbol-specific configuration model"""
    symbol: str
    exchanges: list[str] = Field(default_factory=list)
    market_type: str = "futures"
    enabled: bool = True
    
    # Detection settings
    flash_pump_detection: FlashPumpDetectionSettings = Field(default_factory=FlashPumpDetectionSettings)
    reversal_detection: ReversalDetectionSettings = Field(default_factory=ReversalDetectionSettings)
    entry_conditions: EntryConditionsSettings = Field(default_factory=EntryConditionsSettings)
    
    # Risk and sizing
    position_sizing: PositionSizingSettings = Field(default_factory=PositionSizingSettings)
    risk_management: RiskManagementSettings = Field(default_factory=RiskManagementSettings)
    safety_limits: SafetyLimitsSettings = Field(default_factory=SafetyLimitsSettings)


class SymbolConfigurationManager:
    """
    Manages symbol-specific configurations with automatic fallback to defaults.
    Provides caching and template generation capabilities.
    """
    
    def __init__(self, config_dir: str, default_settings: AppSettings, logger: logging.Logger):
        """
        Initialize symbol configuration manager.
        
        Args:
            config_dir: Base configuration directory
            default_settings: Default application settings for fallback
            logger: Logger instance
        """
        self.config_dir = Path(config_dir)
        self.symbols_dir = self.config_dir / "symbols"
        self.default_settings = default_settings
        self.logger = logger
        self._cache: Dict[str, SymbolConfig] = {}
        
        # Ensure symbols directory exists
        self.symbols_dir.mkdir(parents=True, exist_ok=True)
        
        # Load default configuration file for enhanced logging
        self._default_config_file = self.symbols_dir / "default.json"
        self._has_default_file = self._default_config_file.exists()
    
    def get_symbol_config(self, symbol: str) -> SymbolConfig:
        """
        Get configuration for a symbol with automatic fallback to defaults.
        Results are cached for performance.
        
        Args:
            symbol: Trading symbol (e.g., "BTC_USDT")
            
        Returns:
            SymbolConfig with symbol-specific or default settings
        """
        # Check cache first
        if symbol in self._cache:
            return self._cache[symbol]
        
        config_file = self.symbols_dir / f"{symbol}.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Create SymbolConfig from file data
                symbol_config = self._create_symbol_config_from_dict(symbol, config_data)
                
                # Enhanced logging with configuration details
                self._log_symbol_config_usage(symbol, "symbol_specific_file", str(config_file), symbol_config)
                
            except Exception as e:
                self.logger.warning("symbol.config_load_error", {
                    "symbol": symbol,
                    "error": str(e),
                    "fallback": "defaults"
                })
                symbol_config = self._create_default_symbol_config(symbol)
                self._log_symbol_config_usage(symbol, "default_fallback_due_to_error", None, symbol_config)
        else:
            symbol_config = self._create_default_symbol_config(symbol)
            config_source = "default_file" if self._has_default_file else "hardcoded_defaults"
            self._log_symbol_config_usage(symbol, config_source, str(self._default_config_file) if self._has_default_file else None, symbol_config)
        
        # Cache the result
        self._cache[symbol] = symbol_config
        return symbol_config
    
    def _create_symbol_config_from_dict(self, symbol: str, config_data: Dict[str, Any]) -> SymbolConfig:
        """Create SymbolConfig from dictionary data with validation"""
        # Merge with defaults for any missing fields
        default_config = self._create_default_symbol_config(symbol)
        
        # Create nested config objects with fallbacks
        flash_pump_data = config_data.get('flash_pump_detection', {})
        reversal_data = config_data.get('reversal_detection', {})
        entry_data = config_data.get('entry_conditions', {})
        sizing_data = config_data.get('position_sizing', {})
        risk_data = config_data.get('risk_management', {})
        safety_data = config_data.get('safety_limits', {})
        
        return SymbolConfig(
            symbol=symbol,
            exchanges=config_data.get('exchanges', default_config.exchanges),
            market_type=config_data.get('market_type', default_config.market_type),
            enabled=config_data.get('enabled', default_config.enabled),
            
            flash_pump_detection=FlashPumpDetectionSettings(**{
                **default_config.flash_pump_detection.model_dump(),
                **flash_pump_data
            }),
            reversal_detection=ReversalDetectionSettings(**{
                **default_config.reversal_detection.model_dump(),
                **reversal_data
            }),
            entry_conditions=EntryConditionsSettings(**{
                **default_config.entry_conditions.model_dump(),
                **entry_data
            }),
            position_sizing=PositionSizingSettings(**{
                **default_config.position_sizing.model_dump(),
                **sizing_data
            }),
            risk_management=RiskManagementSettings(**{
                **default_config.risk_management.model_dump(),
                **self._merge_risk_management(risk_data, default_config.risk_management)
            }),
            safety_limits=SafetyLimitsSettings(**{
                **default_config.safety_limits.model_dump(),
                **safety_data
            })
        )
    
    def _merge_risk_management(self, risk_data: Dict[str, Any], default_risk: RiskManagementSettings) -> Dict[str, Any]:
        """Merge risk management data with proper nested structure"""
        result = default_risk.model_dump()
        
        if 'stop_loss' in risk_data:
            result['stop_loss'].update(risk_data['stop_loss'])
        if 'take_profit' in risk_data:
            result['take_profit'].update(risk_data['take_profit'])
        
        # Update top-level risk management fields
        for key, value in risk_data.items():
            if key not in ['stop_loss', 'take_profit']:
                result[key] = value
        
        return result
    
    def _create_default_symbol_config(self, symbol: str) -> SymbolConfig:
        """Create a SymbolConfig using default settings, with preference for default.json file"""
        # Try to load from default.json file first (but avoid recursion)
        if self._has_default_file and symbol != "DEFAULT":
            try:
                with open(self._default_config_file, 'r') as f:
                    default_data = json.load(f)
                # Create config from default.json with symbol override - using direct creation to avoid recursion
                default_data['symbol'] = symbol
                return self._create_symbol_config_from_dict_direct(symbol, default_data)
            except Exception as e:
                self.logger.warning("symbol.default_file_load_error", {
                    "symbol": symbol,
                    "error": str(e),
                    "fallback": "hardcoded_defaults"
                })
        
        # Fallback to hardcoded defaults from Settings
        return SymbolConfig(
            symbol=symbol,
            exchanges=["mexc"],
            market_type="futures",
            enabled=True,
            flash_pump_detection=self.default_settings.flash_pump_detection,
            reversal_detection=self.default_settings.reversal_detection,
            entry_conditions=self.default_settings.entry_conditions,
            position_sizing=self.default_settings.position_sizing,
            risk_management=self.default_settings.risk_management,
            safety_limits=self.default_settings.safety_limits
        )
    
    def _create_symbol_config_from_dict_direct(self, symbol: str, config_data: Dict[str, Any]) -> SymbolConfig:
        """Create SymbolConfig from dictionary data directly without recursion"""
        # Use hardcoded defaults for merging (avoid recursion)
        default_exchanges = ["mexc"]
        default_market_type = "futures"
        default_enabled = True
        
        # Create nested config objects with fallbacks from settings
        flash_pump_data = config_data.get('flash_pump_detection', {})
        reversal_data = config_data.get('reversal_detection', {})
        entry_data = config_data.get('entry_conditions', {})
        sizing_data = config_data.get('position_sizing', {})
        risk_data = config_data.get('risk_management', {})
        safety_data = config_data.get('safety_limits', {})
        
        return SymbolConfig(
            symbol=symbol,
            exchanges=config_data.get('exchanges', default_exchanges),
            market_type=config_data.get('market_type', default_market_type),
            enabled=config_data.get('enabled', default_enabled),
            
            flash_pump_detection=FlashPumpDetectionSettings(**{
                **self.default_settings.flash_pump_detection.model_dump(),
                **flash_pump_data
            }),
            reversal_detection=ReversalDetectionSettings(**{
                **self.default_settings.reversal_detection.model_dump(),
                **reversal_data
            }),
            entry_conditions=EntryConditionsSettings(**{
                **self.default_settings.entry_conditions.model_dump(),
                **entry_data
            }),
            position_sizing=PositionSizingSettings(**{
                **self.default_settings.position_sizing.model_dump(),
                **sizing_data
            }),
            risk_management=RiskManagementSettings(**{
                **self.default_settings.risk_management.model_dump(),
                **self._merge_risk_management(risk_data, self.default_settings.risk_management)
            }),
            safety_limits=SafetyLimitsSettings(**{
                **self.default_settings.safety_limits.model_dump(),
                **safety_data
            })
        )
    
    def _log_symbol_config_usage(self, symbol: str, config_source: str, config_file: Optional[str], symbol_config: SymbolConfig):
        """
        Log detailed information about which configuration is being used for a symbol.
        
        Args:
            symbol: Trading symbol
            config_source: Source of configuration (symbol_specific_file, default_file, hardcoded_defaults, etc.)
            config_file: Path to config file if applicable
            symbol_config: The loaded configuration
        """
        log_data = {
            "symbol": symbol,
            "config_source": config_source,
            "enabled": symbol_config.enabled,
            "exchanges": symbol_config.exchanges,
            "market_type": symbol_config.market_type,
            "key_parameters": {
                "min_pump_magnitude": float(symbol_config.flash_pump_detection.min_pump_magnitude),
                "volume_surge_multiplier": float(symbol_config.flash_pump_detection.volume_surge_multiplier),
                "max_position_size_usdt": float(symbol_config.position_sizing.max_position_size_usdt),
                "base_risk_pct": float(symbol_config.position_sizing.base_risk_pct),
                "peak_buffer_pct": float(symbol_config.risk_management.stop_loss.peak_buffer_pct),
                "target_retracement_pct": float(symbol_config.risk_management.take_profit.target_retracement_pct),
                "max_daily_trades": symbol_config.safety_limits.max_daily_trades,
                "max_consecutive_losses": symbol_config.safety_limits.max_consecutive_losses
            }
        }
        
        if config_file:
            log_data["config_file"] = config_file
        
        self.logger.info("symbol.configuration_loaded", log_data)
    
    def create_symbol_config_template(self, symbol: str) -> Path:
        """
        Create a configuration template file for a new symbol.
        
        Args:
            symbol: Trading symbol (e.g., "NEW_USDT")
            
        Returns:
            Path to the created template file
        """
        config_file = self.symbols_dir / f"{symbol}.json"
        
        if config_file.exists():
            self.logger.info("symbol.template_exists", {
                "symbol": symbol,
                "config_file": str(config_file)
            })
            return config_file
        
        # Create template with default values
        default_config = self._create_default_symbol_config(symbol)
        template_data = self._symbol_config_to_dict(default_config)
        
        with open(config_file, 'w') as f:
            json.dump(template_data, f, indent=2, default=str)
        
        self.logger.info("symbol.template_created", {
            "symbol": symbol,
            "config_file": str(config_file)
        })
        
        return config_file
    
    def _symbol_config_to_dict(self, config: SymbolConfig) -> Dict[str, Any]:
        """Convert SymbolConfig to dictionary for JSON serialization"""
        return {
            "symbol": config.symbol,
            "exchanges": config.exchanges,
            "market_type": config.market_type,
            "enabled": config.enabled,
            
            "flash_pump_detection": {
                "enabled": config.flash_pump_detection.enabled,
                "min_pump_magnitude": float(config.flash_pump_detection.min_pump_magnitude),
                "volume_surge_multiplier": float(config.flash_pump_detection.volume_surge_multiplier),
                "price_velocity_threshold": float(config.flash_pump_detection.price_velocity_threshold),
                "min_volume_24h_usdt": float(config.flash_pump_detection.min_volume_24h_usdt),
                "peak_confirmation_window": config.flash_pump_detection.peak_confirmation_window
            },
            
            "reversal_detection": {
                "enabled": config.reversal_detection.enabled,
                "min_retracement_pct": float(config.reversal_detection.min_retracement_pct),
                "retracement_confirmation_seconds": config.reversal_detection.retracement_confirmation_seconds,
                "volume_decline_threshold": float(config.reversal_detection.volume_decline_threshold),
                "momentum_shift_required": config.reversal_detection.momentum_shift_required
            },
            
            "entry_conditions": {
                "entry_offset_pct": float(config.entry_conditions.entry_offset_pct),
                "min_pump_age_seconds": config.entry_conditions.min_pump_age_seconds,
                "max_entry_delay_seconds": config.entry_conditions.max_entry_delay_seconds,
                "min_confidence_threshold": float(config.entry_conditions.min_confidence_threshold),
                "max_spread_pct": float(config.entry_conditions.max_spread_pct),
                "min_liquidity_usdt": float(config.entry_conditions.min_liquidity_usdt),
                "rsi_max": float(config.entry_conditions.rsi_max)
            },
            
            "position_sizing": {
                "base_risk_pct": float(config.position_sizing.base_risk_pct),
                "max_position_size_usdt": float(config.position_sizing.max_position_size_usdt),
                "max_leverage": float(config.position_sizing.max_leverage),
                "confidence_scaling_enabled": config.position_sizing.confidence_scaling_enabled,
                "min_size_multiplier": float(config.position_sizing.min_size_multiplier),
                "max_size_multiplier": float(config.position_sizing.max_size_multiplier)
            },
            
            "risk_management": {
                "stop_loss": {
                    "peak_buffer_pct": float(config.risk_management.stop_loss.peak_buffer_pct),
                    "trailing_enabled": config.risk_management.stop_loss.trailing_enabled,
                    "trailing_distance_pct": float(config.risk_management.stop_loss.trailing_distance_pct),
                    "trailing_threshold_pct": float(config.risk_management.stop_loss.trailing_threshold_pct),
                    "trailing_adjustment_pct": float(config.risk_management.stop_loss.trailing_adjustment_pct)
                },
                "take_profit": {
                    "quick_profit_pct": float(config.risk_management.take_profit.quick_profit_pct),
                    "quick_profit_close_pct": float(config.risk_management.take_profit.quick_profit_close_pct),
                    "target_retracement_pct": float(config.risk_management.take_profit.target_retracement_pct),
                    "partial_exit_enabled": config.risk_management.take_profit.partial_exit_enabled,
                    "partial_exit_pct": float(config.risk_management.take_profit.partial_exit_pct)
                },
                "time_limit_minutes": config.risk_management.time_limit_minutes,
                "force_close_minutes": config.risk_management.force_close_minutes,
                "max_drawdown_pct": float(config.risk_management.max_drawdown_pct),
                "spread_blowout_pct": float(config.risk_management.spread_blowout_pct),
                "volume_death_threshold_pct": float(config.risk_management.volume_death_threshold_pct),
                "emergency_min_liquidity": float(config.risk_management.emergency_min_liquidity)
            },
            
            "safety_limits": {
                "max_daily_trades": config.safety_limits.max_daily_trades,
                "max_consecutive_losses": config.safety_limits.max_consecutive_losses,
                "daily_loss_limit_pct": float(config.safety_limits.daily_loss_limit_pct),
                "min_cooldown_minutes": config.safety_limits.min_cooldown_minutes
            }
        }
    
    def clear_cache(self):
        """Clear the configuration cache"""
        self._cache.clear()
        self.logger.debug("symbol.cache_cleared")
    
    def get_cached_symbols(self) -> list[str]:
        """Get list of currently cached symbol configurations"""
        return list(self._cache.keys())
    
    def validate_symbol_config(self, symbol: str) -> Dict[str, Any]:
        """
        Validate that a symbol configuration has all required parameters.
        
        Args:
            symbol: Trading symbol to validate
            
        Returns:
            Validation report with missing/invalid parameters
        """
        config = self.get_symbol_config(symbol)
        validation_report = {
            "symbol": symbol,
            "valid": True,
            "missing_parameters": [],
            "invalid_parameters": [],
            "warnings": []
        }
        
        # Check required top-level parameters
        required_fields = ["symbol", "exchanges", "market_type", "enabled"]
        for field in required_fields:
            if not hasattr(config, field) or getattr(config, field) is None:
                validation_report["missing_parameters"].append(field)
                validation_report["valid"] = False
        
        # Validate detection settings
        if not config.flash_pump_detection.min_pump_magnitude or config.flash_pump_detection.min_pump_magnitude <= 0:
            validation_report["invalid_parameters"].append("flash_pump_detection.min_pump_magnitude must be > 0")
            validation_report["valid"] = False
        
        if not config.flash_pump_detection.volume_surge_multiplier or config.flash_pump_detection.volume_surge_multiplier <= 1:
            validation_report["invalid_parameters"].append("flash_pump_detection.volume_surge_multiplier must be > 1")
            validation_report["valid"] = False
        
        # Validate position sizing
        if not config.position_sizing.max_position_size_usdt or config.position_sizing.max_position_size_usdt <= 0:
            validation_report["invalid_parameters"].append("position_sizing.max_position_size_usdt must be > 0")
            validation_report["valid"] = False
        
        if not config.position_sizing.base_risk_pct or config.position_sizing.base_risk_pct <= 0 or config.position_sizing.base_risk_pct > 100:
            validation_report["invalid_parameters"].append("position_sizing.base_risk_pct must be between 0 and 100")
            validation_report["valid"] = False
        
        # Validate risk management
        if not config.risk_management.stop_loss.peak_buffer_pct or config.risk_management.stop_loss.peak_buffer_pct <= 0:
            validation_report["invalid_parameters"].append("risk_management.stop_loss.peak_buffer_pct must be > 0")
            validation_report["valid"] = False
        
        if not config.risk_management.take_profit.target_retracement_pct or config.risk_management.take_profit.target_retracement_pct <= 0:
            validation_report["invalid_parameters"].append("risk_management.take_profit.target_retracement_pct must be > 0")
            validation_report["valid"] = False
        
        # Validate safety limits
        if not config.safety_limits.max_daily_trades or config.safety_limits.max_daily_trades <= 0:
            validation_report["invalid_parameters"].append("safety_limits.max_daily_trades must be > 0")
            validation_report["valid"] = False
        
        # Add warnings for questionable values
        if config.position_sizing.base_risk_pct > 10:
            validation_report["warnings"].append("base_risk_pct > 10% - bardzo wysokie ryzyko")
        
        if config.flash_pump_detection.min_pump_magnitude < 3:
            validation_report["warnings"].append("min_pump_magnitude < 3% - może generować za dużo sygnałów")
        
        if config.position_sizing.max_leverage > 10:
            validation_report["warnings"].append("max_leverage > 10x - ekstremalnie wysokie ryzyko")
        
        return validation_report
    
    def validate_all_cached_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Validate all currently cached symbol configurations.
        
        Returns:
            Dictionary with validation reports for all cached symbols
        """
        validation_results = {}
        for symbol in self.get_cached_symbols():
            validation_results[symbol] = self.validate_symbol_config(symbol)
        
        return validation_results
