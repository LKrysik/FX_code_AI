#!/usr/bin/env python3
"""
Strategy Configuration Loader
============================

Loads and validates YAML-based strategy configurations for the StrategyEvaluator.
Provides schema validation and configuration management.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StrategyConfig:
    """Strategy configuration loaded from YAML."""
    name: str
    version: str
    description: str
    indicators: Dict[str, Any]
    weights: Dict[str, float]
    thresholds: Dict[str, float]
    risk_limits: Dict[str, Any]
    emergency_stops: Dict[str, Any]
    metadata: Dict[str, Any]

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_config()

    def _validate_config(self):
        """Validate the strategy configuration."""
        required_fields = ["name", "version", "weights", "thresholds", "risk_limits"]
        for field in required_fields:
            if not hasattr(self, field) or getattr(self, field) is None:
                raise ValueError(f"Missing required field: {field}")

        # Validate weights sum to 1.0
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.01:  # Allow small floating point errors
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")

        # Validate required indicators
        required_indicators = ["volume_surge_ratio", "price_velocity", "bid_ask_imbalance"]
        for indicator in required_indicators:
            if indicator not in self.weights:
                raise ValueError(f"Missing weight for required indicator: {indicator}")


class StrategyConfigLoader:
    """
    Loads and manages strategy configurations from YAML files.

    Provides validation, caching, and hot-reload capabilities for strategy configurations.
    """

    def __init__(self, config_dir: str = "configs/strategies"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._config_cache: Dict[str, StrategyConfig] = {}
        self._config_timestamps: Dict[str, float] = {}

    def load_strategy(self, strategy_name: str) -> StrategyConfig:
        """
        Load a strategy configuration by name.

        Args:
            strategy_name: Name of the strategy (without .yaml extension)

        Returns:
            StrategyConfig: Validated strategy configuration

        Raises:
            FileNotFoundError: If strategy file doesn't exist
            ValueError: If configuration is invalid
        """
        config_path = self.config_dir / f"{strategy_name}.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Strategy configuration not found: {config_path}")

        # Check if file has been modified
        current_mtime = config_path.stat().st_mtime
        if strategy_name in self._config_timestamps:
            cached_mtime = self._config_timestamps[strategy_name]
            if current_mtime <= cached_mtime:
                # Return cached version
                return self._config_cache[strategy_name]

        # Load and parse YAML
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {config_path}: {e}")

        # Validate required top-level structure
        if not isinstance(config_data, dict):
            raise ValueError(f"Strategy configuration must be a dictionary: {config_path}")

        # Create StrategyConfig object
        try:
            config = StrategyConfig(
                name=config_data.get("name", strategy_name),
                version=config_data.get("version", "1.0.0"),
                description=config_data.get("description", ""),
                indicators=config_data.get("indicators", {}),
                weights=config_data.get("weights", {}),
                thresholds=config_data.get("thresholds", {}),
                risk_limits=config_data.get("risk_limits", {}),
                emergency_stops=config_data.get("emergency_stops", {}),
                metadata=config_data.get("metadata", {})
            )
        except Exception as e:
            raise ValueError(f"Invalid strategy configuration in {config_path}: {e}")

        # Cache the configuration
        self._config_cache[strategy_name] = config
        self._config_timestamps[strategy_name] = current_mtime

        return config

    def list_available_strategies(self) -> list[str]:
        """List all available strategy configuration files."""
        if not self.config_dir.exists():
            return []

        strategy_files = self.config_dir.glob("*.yaml")
        return [f.stem for f in strategy_files]

    def create_default_pump_strategy(self, strategy_name: str = "pump_detection") -> StrategyConfig:
        """
        Create a default pump detection strategy configuration.

        This creates the baseline configuration using Sprint 2 validated parameters.
        """
        default_config = {
            "name": strategy_name,
            "version": "1.0.0",
            "description": "Sprint 2 validated pump detection strategy",
            "indicators": {
                "volume_surge_ratio": {
                    "type": "volume_surge_ratio",
                    "current_window_seconds": 30,
                    "baseline_window_seconds": 1800
                },
                "price_velocity": {
                    "type": "price_velocity",
                    "window_seconds": 60
                },
                "bid_ask_imbalance": {
                    "type": "bid_ask_imbalance",
                    "window_seconds": 30
                }
            },
            "weights": {
                "volume_surge_ratio": 0.30,
                "price_velocity": 0.50,
                "bid_ask_imbalance": 0.20
            },
            "thresholds": {
                "min_confidence": 0.5,
                "pump_score_baseline": 48.67,
                "price_velocity_scale": 1000.0
            },
            "risk_limits": {
                "base_position_size": 100.0,
                "max_position_size": 1000.0,
                "max_concurrent_positions": 3,
                "daily_loss_limit_pct": 3.0,
                "max_daily_trades": 5
            },
            "emergency_stops": {
                "max_consecutive_losses": 3,
                "max_daily_drawdown_pct": 4.0,
                "indicator_malfunction_sigma": 4,
                "data_feed_loss_timeout_sec": 90
            },
            "metadata": {
                "based_on_sprint": 2,
                "validation_results": {
                    "accuracy": 0.91,
                    "sharpe": 2.1,
                    "tested_period": "2025-09-25 to 2025-09-27"
                },
                "created_at": datetime.now().isoformat(),
                "author": "Sprint 3 Implementation"
            }
        }

        # Save to file
        config_path = self.config_dir / f"{strategy_name}.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

        # Load and return the configuration
        return self.load_strategy(strategy_name)

    def validate_strategy_config(self, config_data: Dict[str, Any]) -> list[str]:
        """
        Validate strategy configuration data.

        Args:
            config_data: Raw configuration dictionary

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check required fields
        required_fields = ["name", "weights", "thresholds", "risk_limits"]
        for field in required_fields:
            if field not in config_data:
                errors.append(f"Missing required field: {field}")

        # Validate weights
        if "weights" in config_data:
            weights = config_data["weights"]
            if not isinstance(weights, dict):
                errors.append("weights must be a dictionary")
            else:
                total_weight = sum(weights.values())
                if abs(total_weight - 1.0) > 0.01:
                    errors.append(f"Weights must sum to 1.0, got {total_weight}")

                # Check required indicators
                required_indicators = ["volume_surge_ratio", "price_velocity", "bid_ask_imbalance"]
                for indicator in required_indicators:
                    if indicator not in weights:
                        errors.append(f"Missing weight for required indicator: {indicator}")

        # Validate risk limits
        if "risk_limits" in config_data:
            risk_limits = config_data["risk_limits"]
            if not isinstance(risk_limits, dict):
                errors.append("risk_limits must be a dictionary")
            else:
                required_limits = ["base_position_size", "max_position_size"]
                for limit in required_limits:
                    if limit not in risk_limits:
                        errors.append(f"Missing required risk limit: {limit}")

        return errors

    def reload_strategy(self, strategy_name: str) -> StrategyConfig:
        """Force reload a strategy configuration from disk."""
        if strategy_name in self._config_timestamps:
            del self._config_timestamps[strategy_name]
        if strategy_name in self._config_cache:
            del self._config_cache[strategy_name]

        return self.load_strategy(strategy_name)