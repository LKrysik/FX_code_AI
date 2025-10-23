"""
Configuration Loader - Bridge Between JSON Config and AppSettings
================================================================
Loads configuration from JSON file and maps to new AppSettings structure.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

from .settings import AppSettings, LoggingSettings, LogLevel


def load_app_settings_from_json(config_path: str = "config/config.json") -> AppSettings:
    """
    Load AppSettings from JSON configuration file.
    
    Args:
        config_path: Path to config.json file (relative to main.py)
        
    Returns:
        Configured AppSettings instance
    """
    try:
        # Resolve environment variables in JSON
        def resolve_env_vars(data):
            if isinstance(data, dict):
                return {k: resolve_env_vars(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [resolve_env_vars(i) for i in data]
            elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
                var_name = data[2:-1]
                return os.getenv(var_name, "")
            return data
        
        # Load and parse JSON config
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        resolved_data = resolve_env_vars(config_data)
        
        # Create AppSettings with explicit JSON values
        settings = AppSettings()
        
        # Map logging configuration
        if 'logging' in resolved_data:
            logging_config = resolved_data['logging']
            
            # Map JSON logging level to LogLevel enum
            json_level = logging_config.get('level', 'INFO').upper()
            if json_level in LogLevel.__members__:
                settings.logging.level = LogLevel[json_level]
            
            # Map other logging settings
            settings.logging.file_enabled = True
            settings.logging.console_enabled = True
            settings.logging.structured_logging = True
            
            # Use JSON file path if specified
            if 'file' in logging_config:
                # Extract directory from file path
                log_path = Path(logging_config['file'])
                settings.logging.log_dir = str(log_path.parent)
        
        # Map trading configuration
        if 'trading' in resolved_data:
            trading_config = resolved_data['trading']

            # Map trading mode
            if 'mode' in trading_config:
                from .settings import TradingMode
                mode_str = trading_config['mode'].upper()
                if mode_str in TradingMode.__members__:
                    settings.trading.mode = TradingMode[mode_str]

            if 'default_symbols' in trading_config:
                settings.trading.default_symbols = trading_config['default_symbols']
        
        # Map exchanges configuration
        if 'exchanges' in resolved_data:
            exchanges_config = resolved_data['exchanges']

            # Map MEXC configuration
            if 'mexc' in exchanges_config:
                mexc_config = exchanges_config['mexc']
                settings.exchanges.mexc_enabled = mexc_config.get('enabled', True)
                settings.exchanges.mexc_ws_url = mexc_config.get('ws_url', 'wss://wbs.mexc.com/ws')
                settings.exchanges.mexc_futures_ws_url = mexc_config.get('futures_ws_url', 'wss://contract.mexc.com/ws')
                # Only set API credentials if they are not already set by environment variables
                if not settings.exchanges.mexc_api_key:
                    settings.exchanges.mexc_api_key = mexc_config.get('api_key', '')
                if not settings.exchanges.mexc_api_secret:
                    settings.exchanges.mexc_api_secret = mexc_config.get('api_secret', '')
                settings.exchanges.mexc_paper_trading = mexc_config.get('testnet', False)

            # Map Bybit configuration
            if 'bybit' in exchanges_config:
                bybit_config = exchanges_config['bybit']
                settings.exchanges.bybit_enabled = bybit_config.get('enabled', False)
                # Only set API credentials if they are not already set by environment variables
                if not settings.exchanges.bybit_api_key:
                    settings.exchanges.bybit_api_key = bybit_config.get('api_key', '')
                if not settings.exchanges.bybit_api_secret:
                    settings.exchanges.bybit_api_secret = bybit_config.get('api_secret', '')
                settings.exchanges.bybit_paper_trading = bybit_config.get('testnet', False)
        
        # Map backtest configuration
        if 'backtest' in resolved_data:
            backtest_config = resolved_data['backtest']
            
            if 'time_scale_factor' in backtest_config:
                settings.backtest.time_scale_factor = float(backtest_config['time_scale_factor'])
            if 'data_directory' in backtest_config:
                settings.backtest.data_directory = backtest_config['data_directory']
            if 'results_directory' in backtest_config:
                settings.backtest.results_directory = backtest_config['results_directory']
        
        return settings
        
    except Exception as e:
        print(f"[WARNING] Failed to load JSON config from {config_path}: {e}")
        print("[INFO] Using default AppSettings configuration")
        return AppSettings()


def get_settings_from_working_directory() -> AppSettings:
    """
    Load settings from config.json in the current working directory.
    This function handles the path resolution for main.py execution.
    
    Returns:
        Configured AppSettings instance
    """
    # Try different possible paths for config.json
    possible_paths = [
        "config/config.json",                 # From crypto_monitor directory  
        "crypto_monitor/config/config.json",  # From project root
        "../config/config.json",              # Alternative path
    ]
    
    for config_path in possible_paths:
        if Path(config_path).exists():
            print(f"[INFO] Loading configuration from: {config_path}")
            return load_app_settings_from_json(config_path)
    
    print(f"[WARNING] Could not find config.json in any of: {possible_paths}")
    print("[INFO] Using default AppSettings configuration")
    return AppSettings()
