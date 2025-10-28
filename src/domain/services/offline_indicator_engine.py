"""
Offline Indicator Engine
========================
Calculates indicators for historical data from QuestDB.

🔄 MIGRATED FROM CSV TO QUESTDB (2025-10-28)

Used for session analysis and backtesting scenarios.
"""

import os
import pandas as pd
from typing import Dict, List, Optional, Any
from threading import Lock
import json
from datetime import datetime
import asyncio

from ..interfaces.indicator_engine import IIndicatorEngine, EngineMode
from ..calculators.indicator_calculator import IndicatorCalculator
from ..services.streaming_indicator_engine import IndicatorType
from ..types.indicator_types import MarketDataPoint, IndicatorValue
from ..utils import TimeAxisGenerator, TimeAxisBounds
from src.core.logger import get_logger

try:
    from src.data.questdb_data_provider import QuestDBDataProvider
    from src.data_feed.questdb_provider import QuestDBProvider
except ImportError:
    from ...data.questdb_data_provider import QuestDBDataProvider
    from ...data_feed.questdb_provider import QuestDBProvider


class OfflineIndicatorEngine(IIndicatorEngine):
    """
    Indicator engine for offline/historical data processing.
    
    Loads data from CSV files and calculates indicators for complete datasets.
    Optimized for batch processing and historical analysis.
    """
    
    def __init__(
        self,
        data_path: str = "data",
        questdb_data_provider: Optional[QuestDBDataProvider] = None
    ):
        """
        Initialize offline indicator engine with QuestDB support.

        🔄 MIGRATED: Now uses QuestDB as primary data source instead of CSV files.

        Args:
            data_path: Legacy base path for data files (kept for backward compatibility)
            questdb_data_provider: QuestDB data provider (auto-initialized if None)
        """
        self.data_path = data_path
        self.logger = get_logger("offline_indicator_engine")

        # QuestDB provider for database operations
        self.questdb_data_provider = questdb_data_provider
        if self.questdb_data_provider is None:
            # Lazy initialization
            questdb_provider = QuestDBProvider()
            self.questdb_data_provider = QuestDBDataProvider(
                questdb_provider,
                self.logger
            )
            self.logger.info("offline_indicator_engine.questdb_auto_initialized")

        # Thread-safe storage for indicators
        self._lock = Lock()
        self._indicators: Dict[str, Dict[str, Any]] = {}
        self._calculated_values: Dict[str, List[IndicatorValue]] = {}
        self._data_cache: Dict[str, List[MarketDataPoint]] = {}

        # Initialize algorithm registry for new pure function interface
        try:
            from .indicators.algorithm_registry import IndicatorAlgorithmRegistry
            self._algorithm_registry = IndicatorAlgorithmRegistry(self.logger)
            discovered_count = self._algorithm_registry.auto_discover_algorithms()
            self.logger.info(
                "offline_indicator_engine.algorithm_registry_initialized",
                {"discovered_algorithms": discovered_count}
            )
        except Exception as e:
            self.logger.error(
                "offline_indicator_engine.algorithm_registry_init_failed",
                {"error": str(e)}
            )
            self._algorithm_registry = None
    
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
    
    async def _load_symbol_data_async(self, symbol: str, session_id: Optional[str] = None) -> List[MarketDataPoint]:
        """
        Load historical data for a symbol from QuestDB.

        🔄 MIGRATED: Now uses QuestDB aggregated_ohlcv or tick_prices instead of CSV files.

        Args:
            symbol: Trading symbol
            session_id: Optional session ID to filter data

        Returns:
            List of MarketDataPoint objects
        """
        # Check cache first
        cache_key = f"{session_id}_{symbol}" if session_id else symbol
        if cache_key in self._data_cache:
            return self._data_cache[cache_key]

        data_points: List[MarketDataPoint] = []

        try:
            # Try to load from aggregated_ohlcv first (faster, pre-aggregated)
            if session_id:
                ohlcv_data = await self.questdb_data_provider.get_aggregated_ohlcv(
                    session_id=session_id,
                    symbol=symbol,
                    interval='1m'  # 1-minute aggregation
                )

                if ohlcv_data:
                    for row in ohlcv_data:
                        timestamp = row.get('timestamp')
                        if isinstance(timestamp, datetime):
                            timestamp = timestamp.timestamp()
                        else:
                            timestamp = float(timestamp)

                        data_points.append(
                            MarketDataPoint(
                                timestamp=self._normalize_timestamp(timestamp),
                                symbol=symbol,
                                price=float(row.get('close', row.get('price', 0.0))),
                                volume=float(row.get('volume', 0.0)),
                            )
                        )

            # Fall back to tick_prices if no aggregated data
            if not data_points and session_id:
                tick_data = await self.questdb_data_provider.get_tick_prices(
                    session_id=session_id,
                    symbol=symbol
                )

                if tick_data:
                    for row in tick_data:
                        timestamp = row.get('timestamp')
                        if isinstance(timestamp, datetime):
                            timestamp = timestamp.timestamp()
                        else:
                            timestamp = float(timestamp)

                        data_points.append(
                            MarketDataPoint(
                                timestamp=self._normalize_timestamp(timestamp),
                                symbol=symbol,
                                price=float(row.get('price', 0.0)),
                                volume=float(row.get('volume', 0.0)),
                            )
                        )

            # Sort by timestamp
            data_points.sort(key=lambda x: x.timestamp)

            # Cache the data
            self._data_cache[cache_key] = data_points

            self.logger.info("offline_indicator_engine.symbol_data_loaded", {
                "symbol": symbol,
                "session_id": session_id,
                "data_points": len(data_points),
                "source": "questdb"
            })

        except Exception as e:
            self.logger.error("offline_indicator_engine.load_symbol_data_failed", {
                "symbol": symbol,
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            data_points = []

        return data_points

    def _load_symbol_data(self, symbol: str, session_id: Optional[str] = None) -> List[MarketDataPoint]:
        """
        Synchronous wrapper for _load_symbol_data_async.

        🔄 MIGRATED: Now uses QuestDB via async method.

        Args:
            symbol: Trading symbol
            session_id: Optional session ID to filter data

        Returns:
            List of MarketDataPoint objects
        """
        try:
            # Run async method in event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create a task
                future = asyncio.ensure_future(
                    self._load_symbol_data_async(symbol, session_id)
                )
                # Note: This might not complete immediately
                return []
            else:
                # Run in new event loop
                return loop.run_until_complete(
                    self._load_symbol_data_async(symbol, session_id)
                )
        except Exception as e:
            self.logger.error("offline_indicator_engine.sync_wrapper_failed", {
                "symbol": symbol,
                "error": str(e)
            })
            return []

    @staticmethod
    def _normalize_timestamp(timestamp: float) -> float:
        """
        Normalize timestamps to Unix seconds.  Accepts millisecond inputs.
        """
        if timestamp > 1e12:  # assume milliseconds
            return timestamp / 1000.0
        return timestamp

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

        NEW: Uses algorithm registry with pure function interface when available.
        Falls back to legacy calculate_indicator_unified for unmigrated indicators.
        """
        if not data_points:
            return []

        # Try new algorithm registry method first
        if self._algorithm_registry:
            algorithm = self._algorithm_registry.get_algorithm(indicator_type.value)
            if algorithm and hasattr(algorithm, 'calculate_from_windows'):
                try:
                    return self._calculate_indicator_series_new(
                        symbol, indicator_type, timeframe, period, params, data_points
                    )
                except Exception as e:
                    self.logger.warning(
                        "offline_indicator_engine.new_method_failed_fallback_to_old",
                        {
                            "indicator_type": indicator_type.value,
                            "error": str(e)
                        }
                    )
                    # Fall through to old method

        # Fallback to legacy method for unmigrated indicators
        return self._calculate_indicator_series_old(
            symbol, indicator_type, timeframe, period, params, data_points
        )

    def _calculate_indicator_series_old(
        self,
        symbol: str,
        indicator_type: IndicatorType,
        timeframe: str,
        period: int,
        params: Dict[str, Any],
        data_points: List[MarketDataPoint],
    ) -> List[IndicatorValue]:
        """
        LEGACY: Old implementation using calculate_indicator_unified.

        Kept for backward compatibility with unmigrated algorithms.
        Will be removed in Phase 3 after all algorithms are migrated.
        """
        if not data_points:
            return []

        sorted_points = sorted(data_points, key=lambda p: p.timestamp)
        start_ts = sorted_points[0].timestamp
        end_ts = sorted_points[-1].timestamp

        params_copy = dict(params or {})
        refresh_interval = float(
            params_copy.get("refresh_interval_seconds")
            or params_copy.get("refresh_interval_override")
            or 1.0
        )

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
                    },
                )
            )

        return series

    def _extract_windows_at_timestamp(
        self,
        sorted_data: List[MarketDataPoint],
        target_ts: float,
        window_specs: List,
    ) -> List:
        """
        Extract multiple data windows for a single timestamp.

        CRITICAL: Each window INCLUDES one transaction BEFORE the window start.
        This is required by TWPA and time-weighted algorithms to calculate
        the duration of the first price in the window.

        EFFICIENT: Single pass through data to extract all windows.
        Returns DataWindow objects ready for pure function calculation.

        Args:
            sorted_data: All data points sorted by timestamp
            target_ts: Target timestamp for calculation
            window_specs: List of WindowSpec objects

        Returns:
            List of DataWindow objects, each including pre-window point if available
        """
        from .indicators.base_algorithm import DataWindow

        windows = []

        for spec in window_specs:
            # Calculate window bounds
            start_ts = target_ts - spec.t1
            end_ts = target_ts - spec.t2

            # ✅ TWPA FIX: Find last transaction BEFORE window (required by TWPA)
            # AND extract window data - optimized single pass
            pre_window_point = None
            window_data = []
            for point in sorted_data:
                if point.timestamp > target_ts:
                    break  # Early exit - data is sorted
                if point.timestamp < start_ts:
                    # Keep updating to get the LAST point before window
                    pre_window_point = (point.timestamp, point.price)
                elif start_ts <= point.timestamp < end_ts:
                    window_data.append((point.timestamp, point.price))

            # ✅ TWPA FIX: ALWAYS include the pre-window point at the beginning
            # This is REQUIRED by TWPA algorithm to calculate duration of first price
            # This handles both cases:
            #   1. Window has points: pre_window_point is inserted at position 0
            #   2. Window is empty: pre_window_point creates a single-element list
            if pre_window_point:
                window_data.insert(0, pre_window_point)

            windows.append(DataWindow(
                data=tuple(window_data),  # Immutable
                start_ts=start_ts,
                end_ts=end_ts
            ))

        return windows

    def _calculate_indicator_series_new(
        self,
        symbol: str,
        indicator_type: IndicatorType,
        timeframe: str,
        period: int,
        params: Dict[str, Any],
        data_points: List[MarketDataPoint],
    ) -> List[IndicatorValue]:
        """
        NEW IMPLEMENTATION: Calculate indicator series using algorithm registry.

        Uses pure function interface with zero coupling.
        More efficient than old method - single pass window extraction.

        Args:
            symbol: Symbol identifier
            indicator_type: Type of indicator
            timeframe: Timeframe
            period: Period (for compatibility)
            params: Calculation parameters
            data_points: Historical data points

        Returns:
            List of IndicatorValue objects
        """
        if not data_points:
            return []

        # Get algorithm from registry
        algorithm = self._algorithm_registry.get_algorithm(indicator_type.value)
        if not algorithm:
            self.logger.warning(
                "offline_indicator_engine.algorithm_not_found",
                {"indicator_type": indicator_type.value}
            )
            return []

        # Wrap parameters
        from .indicators.base_algorithm import IndicatorParameters
        wrapped_params = IndicatorParameters(params or {})

        # Get window specifications from algorithm
        try:
            window_specs = algorithm.get_window_specs(wrapped_params)
        except Exception as e:
            self.logger.error(
                "offline_indicator_engine.get_window_specs_failed",
                {"indicator_type": indicator_type.value, "error": str(e)}
            )
            return []

        # Sort data once
        sorted_points = sorted(data_points, key=lambda p: p.timestamp)
        start_ts = sorted_points[0].timestamp
        end_ts = sorted_points[-1].timestamp

        # Generate time axis
        refresh_interval = float(
            params.get("refresh_interval_seconds")
            or params.get("refresh_interval_override")
            or 1.0
        )

        bounds = TimeAxisBounds(start=start_ts, end=end_ts, interval=refresh_interval)
        time_axis = list(TimeAxisGenerator.generate(bounds))

        # Calculate indicator values
        series: List[IndicatorValue] = []

        for target_ts in time_axis:
            # Extract all windows for this timestamp
            windows = self._extract_windows_at_timestamp(
                sorted_points, target_ts, window_specs
            )

            # Calculate using pure function
            try:
                value = algorithm.calculate_from_windows(windows, wrapped_params)
            except Exception as e:
                self.logger.error(
                    "offline_indicator_engine.calculate_failed",
                    {
                        "indicator_type": indicator_type.value,
                        "timestamp": target_ts,
                        "error": str(e)
                    }
                )
                value = None

            series.append(
                IndicatorValue(
                    timestamp=target_ts,
                    symbol=symbol,
                    indicator_id=f"{indicator_type.value}_{period}_{timeframe}",
                    value=value,
                    metadata={
                        "timeframe": timeframe,
                        "params": dict(params),
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
