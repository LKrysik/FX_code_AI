"""
Offline Indicator Engine
========================
Calculates indicators for historical data from CSV files.
Used for session analysis and backtesting scenarios.
"""

import os
import pandas as pd
from typing import Dict, List, Optional, Any
from threading import Lock
import json

from ..interfaces.indicator_engine import IIndicatorEngine, EngineMode
from ..calculators.indicator_calculator import IndicatorCalculator
from ..services.streaming_indicator_engine import IndicatorType
from ..services.indicators.algorithm_registry import IndicatorAlgorithmRegistry
from ..types.indicator_types import MarketDataPoint, IndicatorValue
from ..utils import TimeAxisGenerator, TimeAxisBounds
from src.core.logger import get_logger


class OfflineIndicatorEngine(IIndicatorEngine):
    """
    Indicator engine for offline/historical data processing.
    
    Loads data from CSV files and calculates indicators for complete datasets.
    Optimized for batch processing and historical analysis.
    """
    
    def __init__(self, data_path: str = "data"):
        """
        Initialize offline indicator engine.
        
        Args:
            data_path: Base path for data files
        """
        self.data_path = data_path
        self.logger = get_logger("offline_indicator_engine")
        
        # Thread-safe storage for indicators
        self._lock = Lock()
        self._indicators: Dict[str, Dict[str, Any]] = {}
        self._calculated_values: Dict[str, List[IndicatorValue]] = {}
        self._data_cache: Dict[str, List[MarketDataPoint]] = {}
        self._algorithm_registry = IndicatorAlgorithmRegistry()
    
    @property
    def mode(self) -> EngineMode:
        """Get engine mode."""
        return EngineMode.OFFLINE
    
    def add_indicator(self,
                     symbol: str,
                     indicator_type: IndicatorType,
                     timeframe: str = "1m",
                     period: int = 20,
                     scope: Optional[str] = None,
                     **kwargs) -> str:
        """Add an indicator and calculate its values from historical data."""
        with self._lock:
            # Create unique key
            key = IndicatorCalculator.create_indicator_key(
                symbol, indicator_type, period, timeframe, **kwargs
            )
            
            # Store indicator configuration
            self._indicators[key] = {
                "key": key,
                "symbol": symbol,
                "indicator_type": indicator_type,
                "timeframe": timeframe,
                "period": period,
                "scope": scope,
                "params": kwargs,
                "data_points": 0
            }
            
            # Load data and calculate values
            try:
                data_points = self._load_symbol_data(symbol)
                if data_points:
                    series = self._calculate_indicator_series(
                        symbol=symbol,
                        indicator_type=indicator_type,
                        timeframe=timeframe,
                        period=period,
                        params=kwargs,
                        data_points=data_points,
                    )
                    self._calculated_values[key] = series
                    valid_points = len([v for v in series if v.value is not None and not pd.isna(v.value)])
                    self._indicators[key]["data_points"] = valid_points

                    self.logger.info(
                        "offline_indicator_engine.indicator_calculated",
                        {
                            "indicator_key": key,
                            "total_points": len(series),
                            "valid_points": valid_points,
                        },
                    )
                else:
                    self.logger.warning(f"No data found for symbol {symbol}")
                    self._calculated_values[key] = []

            except Exception as e:
                self.logger.error(f"Failed to calculate indicator {key}: {e}")
                self._calculated_values[key] = []
            
            return key
    
    def remove_indicator(self, indicator_key: str) -> bool:
        """Remove an indicator."""
        with self._lock:
            if indicator_key in self._indicators:
                del self._indicators[indicator_key]
                if indicator_key in self._calculated_values:
                    del self._calculated_values[indicator_key]
                return True
            return False
    
    def get_indicator_value(self, indicator_key: str) -> Optional[Dict[str, Any]]:
        """Get current value of an indicator."""
        with self._lock:
            if indicator_key not in self._indicators:
                return None
            
            indicator = self._indicators[indicator_key].copy()
            series = self._calculated_values.get(indicator_key, [])

            # Get latest non-NaN value
            current_value = None
            for value in reversed(series):
                val = value.value if isinstance(value, IndicatorValue) else value
                if val is not None and not pd.isna(val):
                    current_value = val
                    break
            
            return {
                **indicator,
                "current_value": current_value,
                "calculated_points": len(series),
                "valid_points": len(
                    [
                        v
                        for v in series
                        if isinstance(v, IndicatorValue)
                        and v.value is not None
                        and not pd.isna(v.value)
                    ]
                ),
            }
    
    def get_indicators_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """Get all indicators for a specific symbol."""
        with self._lock:
            result = []
            for key, indicator in self._indicators.items():
                if indicator["symbol"] == symbol:
                    value_info = self.get_indicator_value(key)
                    if value_info:
                        result.append(value_info)
            return result
    
    def calculate_for_data(self, symbol: str, data: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """Calculate indicator values for provided data points."""
        with self._lock:
            result = {}

            market_points = [
                MarketDataPoint(
                    timestamp=self._normalize_timestamp(float(point.get("timestamp"))),
                    symbol=point.get("symbol", symbol),
                    price=float(point.get("price", 0.0)),
                    volume=float(point.get("volume", 0.0)),
                )
                for point in data
                if point.get("timestamp") is not None
            ]
            
            # Find indicators for this symbol
            symbol_indicators = [
                (key, ind) for key, ind in self._indicators.items() 
                if ind["symbol"] == symbol
            ]
            
            for key, indicator in symbol_indicators:
                try:
                    series = self._calculate_indicator_series(
                        symbol=symbol,
                        indicator_type=indicator["indicator_type"],
                        timeframe=indicator["timeframe"],
                        period=indicator["period"],
                        params=indicator["params"],
                        data_points=market_points,
                    )
                    result[key] = [
                        value.value if value.value is not None else float("nan")
                        for value in series
                    ]
                except Exception as e:
                    self.logger.error(f"Failed to calculate {key} for provided data: {e}")
                    result[key] = [float('nan')] * len(data)
            
            return result
    
    def get_all_indicators(self) -> List[Dict[str, Any]]:
        """Get all active indicators."""
        with self._lock:
            result = []
            for key in self._indicators:
                value_info = self.get_indicator_value(key)
                if value_info:
                    result.append(value_info)
            return result
    
    def _load_symbol_data(self, symbol: str) -> List[MarketDataPoint]:
        """
        Load historical data for a symbol from CSV files.
        
        Expected file structure:
        data/{session_id}/prices.csv with columns: timestamp, symbol, price, volume
        """
        if symbol in self._data_cache:
            return self._data_cache[symbol]
        
        data_points: List[MarketDataPoint] = []
        
        # Search for data files in all session directories
        try:
            for session_dir in os.listdir(self.data_path):
                session_path = os.path.join(self.data_path, session_dir)
                if not os.path.isdir(session_path):
                    continue
                
                prices_file = os.path.join(session_path, "prices.csv")
                if os.path.exists(prices_file):
                    df = pd.read_csv(prices_file)
                    
                    # Filter for the specific symbol
                    symbol_data = df[df["symbol"] == symbol]
                    
                    for _, row in symbol_data.iterrows():
                        timestamp = self._normalize_timestamp(float(row["timestamp"]))
                        data_points.append(
                            MarketDataPoint(
                                timestamp=timestamp,
                                symbol=row["symbol"],
                                price=float(row.get("price", 0.0)),
                                volume=float(row.get("volume", 0.0)),
                            )
                        )

            # Sort by timestamp
            data_points.sort(key=lambda x: x.timestamp)
            
            # Cache the data
            self._data_cache[symbol] = data_points
            
            self.logger.info(f"Loaded {len(data_points)} data points for symbol {symbol}")
            
        except Exception as e:
            self.logger.error(f"Failed to load data for symbol {symbol}: {e}")
            data_points = []
        
        return data_points

    @staticmethod
    def _normalize_timestamp(timestamp: float) -> float:
        """
        Normalize timestamps to Unix seconds.  Accepts millisecond inputs.
        """
        if timestamp > 1e12:  # assume milliseconds
            return timestamp / 1000.0
        return timestamp

    def _resolve_refresh_interval(self, indicator_type: str, params: Dict[str, Any]) -> float:
        """
        Determine refresh cadence for offline calculations using the shared algorithm registry.
        """
        interval: Optional[float] = None

        try:
            interval = self._algorithm_registry.calculate_refresh_interval(indicator_type, params)
        except Exception as exc:
            self.logger.warning(
                "offline_indicator_engine.refresh_interval_algorithm_failed",
                {"indicator_type": indicator_type, "error": str(exc)},
            )

        if interval is None:
            for key in ("refresh_interval_seconds", "refresh_interval_override", "r"):
                value = params.get(key)
                if value is None:
                    continue
                try:
                    interval = float(value)
                    break
                except (TypeError, ValueError):
                    self.logger.warning(
                        "offline_indicator_engine.refresh_interval_invalid_override",
                        {"indicator_type": indicator_type, "param": key, "value": value},
                    )

        if interval is None:
            interval = 1.0

        return max(0.1, float(interval))

    def _calculate_indicator_series(
        self,
        symbol: str,
        indicator_type: IndicatorType,
        timeframe: str,
        period: int,
        params: Dict[str, Any],
        data_points: List[MarketDataPoint],
    ) -> List[IndicatorValue]:
        """
        Convert raw market data into a timestamp-aligned indicator series.
        """
        if not data_points:
            return []

        sorted_points = sorted(data_points, key=lambda p: p.timestamp)
        start_ts = sorted_points[0].timestamp
        end_ts = sorted_points[-1].timestamp

        params_copy = dict(params or {})
        refresh_interval = self._resolve_refresh_interval(indicator_type.value, params_copy)
        params_copy["refresh_interval_seconds"] = refresh_interval
        bounds = TimeAxisBounds(start=start_ts, end=end_ts, interval=refresh_interval)
        time_axis = list(TimeAxisGenerator.generate(bounds))

        series: List[IndicatorValue] = []
        active_points: List[MarketDataPoint] = []
        point_index = 0

        for target_ts in time_axis:
            while point_index < len(sorted_points) and sorted_points[point_index].timestamp <= target_ts:
                active_points.append(sorted_points[point_index])
                point_index += 1

            value = IndicatorCalculator.calculate_indicator_unified(
                indicator_type.value,
                active_points,
                target_ts,
                params_copy,
            )

            series.append(
                IndicatorValue(
                    timestamp=target_ts,
                    symbol=symbol,
                    indicator_id=f"{indicator_type.value}_{period}_{timeframe}",
                    value=value,
                    metadata={
                        "timeframe": timeframe,
                        "params": dict(params_copy),
                        "refresh_interval_seconds": refresh_interval,
                    },
                )
            )

        return series
    
    def get_indicator_values_for_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Get all calculated indicator values for a symbol.
        Returns format compatible with API endpoint.
        """
        with self._lock:
            indicators = {}
            
            for key, indicator in self._indicators.items():
                if indicator["symbol"] == symbol:
                    values = self._calculated_values.get(key, [])
                    if values and not all(
                        (v.value is None) or pd.isna(v.value) for v in values
                    ):
                        # Get latest non-NaN value
                        current_value = None
                        for value in reversed(values):
                            val = value.value if isinstance(value, IndicatorValue) else value
                            if val is not None and not pd.isna(val):
                                current_value = val
                                break
                        
                        indicators[key] = {
                            "indicator": f"{indicator['indicator_type'].value}_{indicator['period']}",
                            "timeframe": indicator["timeframe"],
                            "current_value": current_value,
                            "value": current_value,  # Alias for compatibility
                            "calculated_points": len(values),
                            "valid_points": len(
                                [
                                    v
                                    for v in values
                                    if isinstance(v, IndicatorValue)
                                    and v.value is not None
                                    and not pd.isna(v.value)
                                ]
                            ),
                            "all_values": [
                                {
                                    "timestamp": v.timestamp,
                                    "value": v.value,
                                    "metadata": v.metadata,
                                }
                                for v in values
                            ],
                        }
            
            return {
                "indicators": indicators,
                "symbol": symbol,
                "mode": "offline"
            }
    
    def clear_cache(self):
        """Clear data cache to free memory."""
        with self._lock:
            self._data_cache.clear()
            self.logger.info("Cleared data cache")
