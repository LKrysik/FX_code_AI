"""
Unified Indicator Calculator Module
===================================
Single source of truth for all indicator calculations.
Consolidates logic from StreamingIndicatorEngine, UnifiedIndicatorEngine, and legacy calculator.

This module provides the core calculation engine used by:
- StreamingIndicatorEngine (live/paper trading)
- OfflineIndicatorEngine (historical/backtest)
- All other indicator-dependent components

Architecture: Single calculator class with static methods for each indicator type.
Each method accepts standardized inputs and returns consistent outputs.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Union, Tuple
import json
import hashlib

from ..types.indicator_types import MarketDataPoint, TimeWindow, IndicatorValue
from ..services.streaming_indicator_engine import IndicatorType


class IndicatorCalculator:
    """
    Unified calculator for all technical indicators.
    
    SINGLE SOURCE OF TRUTH for indicator calculations.
    Used by ALL engines (streaming, offline, backtest) to ensure consistent results.
    """

    @staticmethod
    def _normalize_timestamp(timestamp: float) -> float:
        """Normalize Unix timestamps to seconds precision."""
        if timestamp is None:
            return 0.0
        if timestamp > 1e12:
            return float(timestamp) / 1000.0
        return float(timestamp)
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> List[float]:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return [np.nan] * len(prices)
        
        result = []
        for i in range(len(prices)):
            if i < period - 1:
                result.append(np.nan)
            else:
                avg = sum(prices[i - period + 1:i + 1]) / period
                result.append(avg)
        return result
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average."""
        if not prices:
            return []
        
        result = []
        multiplier = 2 / (period + 1)
        
        # First value is SMA
        if len(prices) >= period:
            sma = sum(prices[:period]) / period
            result = [np.nan] * (period - 1) + [sma]
            
            # Calculate EMA for remaining values
            for i in range(period, len(prices)):
                ema = (prices[i] * multiplier) + (result[i - 1] * (1 - multiplier))
                result.append(ema)
        else:
            result = [np.nan] * len(prices)
            
        return result
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return [np.nan] * len(prices)
        
        result = [np.nan] * period
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        # Initial average gain and loss
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            result.append(rsi)
        
        # Calculate RSI for remaining values
        for i in range(period, len(deltas)):
            avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
            avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period
            
            if avg_loss == 0:
                result.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                result.append(rsi)
        
        return result
    
    @staticmethod
    def calculate_vwap_unified(data_points: List[MarketDataPoint],
                              current_timestamp: float, 
                              t1: float,
                              t2: float = 0.0) -> Optional[float]:
        """
        Unified Volume Weighted Average Price calculation.
        
        Args:
            data_points: List of MarketDataPoint objects with volume
            current_timestamp: Current time reference point
            t1: Time window start (seconds back)
            t2: Time window end (seconds back, default 0)
            
        Returns:
            VWAP value or None if insufficient data
        """
        if not data_points:
            return None
            
        # Filter data points within time window
        start_time = current_timestamp - t1
        end_time = current_timestamp - t2
        
        relevant_points = [
            point for point in data_points 
            if start_time <= point.timestamp <= end_time and point.volume > 0
        ]
        
        if not relevant_points:
            return None
        
        total_volume = 0.0
        volume_weighted_sum = 0.0
        
        for point in relevant_points:
            volume_weighted_sum += point.price * point.volume
            total_volume += point.volume
        
        return volume_weighted_sum / total_volume if total_volume > 0 else None
    
    @staticmethod
    def calculate_volatility(prices: List[float], period: int = 20) -> List[float]:
        """Calculate price volatility (standard deviation)."""
        if len(prices) < period:
            return [np.nan] * len(prices)
        
        result = []
        
        for i in range(len(prices)):
            if i < period - 1:
                result.append(np.nan)
            else:
                window_prices = prices[i - period + 1:i + 1]
                volatility = np.std(window_prices)
                result.append(volatility)
        
        return result
    
    @staticmethod
    def calculate_vwap(prices: List[float], volumes: List[float]) -> List[float]:
        """Calculate Volume Weighted Average Price."""
        if not prices or not volumes or len(prices) != len(volumes):
            return [np.nan] * len(prices)
        
        result = []
        cumulative_pv = 0
        cumulative_volume = 0
        
        for price, volume in zip(prices, volumes):
            cumulative_pv += price * volume
            cumulative_volume += volume
            
            if cumulative_volume > 0:
                vwap = cumulative_pv / cumulative_volume
                result.append(vwap)
            else:
                result.append(np.nan)
        
        return result
    
    @staticmethod
    @staticmethod
    def calculate_indicator(indicator_type: IndicatorType, 
                          data: List[Dict[str, Any]], 
                          period: int = 20,
                          algorithm_registry=None,
                          **kwargs) -> List[float]:
        """
        Main calculation dispatcher using algorithm registry as single source of truth.
        
        Args:
            indicator_type: Type of indicator to calculate
            data: List of data points with 'price', 'volume', 'timestamp' fields
            period: Calculation period
            algorithm_registry: Registry to use for algorithms (optional)
            **kwargs: Additional parameters (e.g., t1, t2 for TWPA)
        """
        if not data:
            return []

        # Try algorithm registry first (NEW ARCHITECTURE)
        if algorithm_registry:
            try:
                return IndicatorCalculator._calculate_via_algorithm_registry(
                    indicator_type, data, period, algorithm_registry, **kwargs)
            except Exception:
                # Fallback to legacy if registry fails
                pass
        
        # Fallback to legacy calculations (OLD ARCHITECTURE)
        return IndicatorCalculator._calculate_via_legacy_methods(indicator_type, data, period, **kwargs)

    @staticmethod
    def _calculate_via_algorithm_registry(indicator_type: IndicatorType, 
                                        data: List[Dict[str, Any]], 
                                        period: int = 20,
                                        algorithm_registry=None,
                                        **kwargs) -> List[float]:
        """
        Calculate indicator using the provided algorithm registry.
        This is the preferred method that ensures consistency with streaming engine.
        """
        if not algorithm_registry:
            raise ValueError("Algorithm registry is required")
        
        # Get algorithm for this indicator type
        algorithm = algorithm_registry.get_algorithm(indicator_type.value)
        if not algorithm:
            raise ValueError(f"Algorithm not found for {indicator_type.value}")
        
        # Convert data to market points
        market_points: List[MarketDataPoint] = []
        for point in data:
            market_points.append(
                MarketDataPoint(
                    timestamp=IndicatorCalculator._normalize_timestamp(point.get("timestamp", 0.0)),
                    symbol=point.get("symbol", ""),
                    price=float(point.get("price", 0.0)),
                    volume=float(point.get("volume", 0.0)),
                )
            )
        
        # Calculate using algorithm's calculation method
        if hasattr(algorithm, 'calculate_multi_window'):
            # Multi-window algorithms like TWPA_RATIO
            return IndicatorCalculator._calculate_multi_window_algorithm(algorithm, market_points, **kwargs)
        else:
            # Single window algorithms like TWPA
            return IndicatorCalculator._calculate_single_window_algorithm(algorithm, market_points, **kwargs)

    @staticmethod 
    def _calculate_multi_window_algorithm(algorithm, market_points: List[MarketDataPoint], **kwargs) -> List[float]:
        """Calculate multi-window algorithms like TWPA_RATIO."""
        # Import algorithm parameters helper
        try:
            from ..services.indicators.base_algorithm import IndicatorParameters
        except ImportError:
            # Fallback if not available
            from typing import Dict
            class IndicatorParameters:
                def __init__(self, params: Dict[str, Any]):
                    self._params = params
                def get_float(self, key: str, default: float) -> float:
                    return float(self._params.get(key, default))
        
        # Extract parameters
        t1 = kwargs.get('t1', 300.0)
        t2 = kwargs.get('t2', 60.0)
        t3 = kwargs.get('t3', 1800.0)
        t4 = kwargs.get('t4', 300.0)
        min_denominator = kwargs.get('min_denominator', 0.001)
        
        params = IndicatorParameters({
            't1': t1, 't2': t2, 't3': t3, 't4': t4,
            'min_denominator': min_denominator
        })
        
        result_series: List[float] = []
        
        for i in range(len(market_points)):
            current_timestamp = market_points[i].timestamp
            
            # Get windows up to current point
            window1_data = [(mp.timestamp, mp.price) for mp in market_points[:i+1] 
                           if current_timestamp - t1 <= mp.timestamp <= current_timestamp - t2]
            window2_data = [(mp.timestamp, mp.price) for mp in market_points[:i+1]
                           if current_timestamp - t3 <= mp.timestamp <= current_timestamp - t4]
            
            if len(window1_data) < 2 or len(window2_data) < 2:
                result_series.append(np.nan)
                continue
            
            # Create windows for algorithm
            windows = [
                (window1_data, current_timestamp - t1, current_timestamp - t2),
                (window2_data, current_timestamp - t3, current_timestamp - t4)
            ]
            
            # Calculate using algorithm
            value = algorithm.calculate_multi_window(windows, params)
            result_series.append(value if value is not None else np.nan)
        
        return result_series

    @staticmethod
    def _calculate_single_window_algorithm(algorithm, market_points: List[MarketDataPoint], **kwargs) -> List[float]:
        """Calculate single window algorithms like TWPA."""
        t1 = kwargs.get('t1', 300.0)
        t2 = kwargs.get('t2', 0.0)
        
        result_series: List[float] = []
        
        for i in range(len(market_points)):
            current_timestamp = market_points[i].timestamp
            
            # Get window data up to current point
            window_data = [(mp.timestamp, mp.price) for mp in market_points[:i+1]
                          if current_timestamp - t1 <= mp.timestamp <= current_timestamp - t2]
            
            if len(window_data) < 2:
                result_series.append(np.nan)
                continue
            
            # Calculate using algorithm
            value = algorithm.calculate(window_data, current_timestamp - t1, current_timestamp - t2)
            result_series.append(value if value is not None else np.nan)
        
        return result_series

    @staticmethod
    def _calculate_via_legacy_methods(indicator_type: IndicatorType, 
                                    data: List[Dict[str, Any]], 
                                    period: int = 20,
                                    **kwargs) -> List[float]:
        """
        Legacy calculation methods for backward compatibility.
        Only used when algorithm registry is not available.
        """
        prices = [point.get('price', 0) for point in data]
        volumes = [point.get('volume', 0) for point in data]
        market_points: List[MarketDataPoint] = []
        for point in data:
            market_points.append(
                MarketDataPoint(
                    timestamp=IndicatorCalculator._normalize_timestamp(point.get("timestamp", 0.0)),
                    symbol=point.get("symbol", ""),
                    price=float(point.get("price", 0.0)),
                    volume=float(point.get("volume", 0.0)),
                )
            )

        if indicator_type == IndicatorType.SMA:
            return IndicatorCalculator.calculate_sma(prices, period)
        
        elif indicator_type == IndicatorType.EMA:
            return IndicatorCalculator.calculate_ema(prices, period)
        
        elif indicator_type == IndicatorType.RSI:
            return IndicatorCalculator.calculate_rsi(prices, period)
        
        elif indicator_type == IndicatorType.TWPA:
            t1 = float(kwargs.get('t1', 300.0))
            t2 = float(kwargs.get('t2', 0.0))
            active_points: List[MarketDataPoint] = []
            result_series: List[float] = []
            for mp in market_points:
                active_points.append(mp)
                value = IndicatorCalculator.calculate_twpa_unified(
                    active_points,
                    mp.timestamp,
                    t1,
                    t2,
                )
                result_series.append(value if value is not None else np.nan)
            return result_series
        
        elif indicator_type == IndicatorType.VOLATILITY:
            return IndicatorCalculator.calculate_volatility(prices, period)
        
        elif indicator_type == IndicatorType.VWAP:
            t1 = float(kwargs.get('t1', 300.0))
            t2 = float(kwargs.get('t2', 0.0))
            active_points: List[MarketDataPoint] = []
            result_series: List[float] = []
            for mp in market_points:
                active_points.append(mp)
                value = IndicatorCalculator.calculate_vwap_unified(
                    active_points,
                    mp.timestamp,
                    t1,
                    t2,
                )
                result_series.append(value if value is not None else np.nan)
            return result_series
        
        else:
            # Fallback for unsupported indicators
            return [np.nan] * len(data)
    
    @staticmethod
    def create_indicator_key(symbol: str, 
                           indicator_type: IndicatorType, 
                           period: int, 
                           timeframe: str,
                           **kwargs) -> str:
        """
        Create a unique key for an indicator configuration.
        Matches the key generation logic from StreamingIndicatorEngine.
        """
        base_key = f"{symbol}_{indicator_type.value}_{period}_{timeframe}"
        
        # For parametric measures, include parameter fingerprint
        param_measures = {"TWPA", "LAST_PRICE", "FIRST_PRICE", "MAX_PRICE", "MIN_PRICE", "VELOCITY"}
        if indicator_type.value in param_measures and kwargs:
            params_only = {k: v for k, v in kwargs.items() if k not in ["scope"]}
            if params_only:
                fp = hashlib.sha1(
                    json.dumps(params_only, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()[:8]
                base_key = f"{base_key}_{fp}"
        
        return base_key

    # ============================================
    # UNIFIED CALCULATION METHODS (NEW)
    # Consolidates logic from all three engines
    # ============================================
    
    @staticmethod
    def calculate_windowed_aggregate(data_points: List[MarketDataPoint],
                                   current_timestamp: float,
                                   aggregate_type: str,
                                   t1: float,
                                   t2: float = 0.0) -> Optional[float]:
        """
        Generic windowed aggregate calculation.
        
        Supports: MAX_PRICE, MIN_PRICE, FIRST_PRICE, LAST_PRICE
        
        Args:
            data_points: List of MarketDataPoint objects
            current_timestamp: Current time reference
            aggregate_type: Type of aggregate (MAX_PRICE, MIN_PRICE, etc.)
            t1: Time window start (seconds back)
            t2: Time window end (seconds back, default 0)
            
        Returns:
            Aggregated value or None if insufficient data
        """
        if not data_points:
            return None
            
        # Filter data points within time window
        start_time = current_timestamp - t1
        end_time = current_timestamp - t2
        
        relevant_points = [
            point for point in data_points 
            if start_time <= point.timestamp <= end_time
        ]
        
        if not relevant_points:
            return None
        
        prices = [point.price for point in relevant_points]
        
        if aggregate_type == "MAX_PRICE":
            return max(prices)
        elif aggregate_type == "MIN_PRICE":
            return min(prices)
        elif aggregate_type == "FIRST_PRICE":
            # Sort by timestamp and get first
            relevant_points.sort(key=lambda x: x.timestamp)
            return relevant_points[0].price
        elif aggregate_type == "LAST_PRICE":
            # Sort by timestamp and get last
            relevant_points.sort(key=lambda x: x.timestamp)
            return relevant_points[-1].price
        else:
            return None

    @staticmethod 
    def calculate_indicator_unified(indicator_type: str,
                                  data_points: List[MarketDataPoint],
                                  current_timestamp: float,
                                  parameters: Dict[str, Any]) -> Optional[float]:
        """
        Unified indicator calculation dispatcher.
        
        Single entry point for all indicator calculations from any engine.
        Ensures consistent results across streaming, offline, and backtest modes.
        
        Args:
            indicator_type: Type of indicator (TWPA, VWAP, MAX_PRICE, etc.)
            data_points: Market data points for calculation
            current_timestamp: Current time reference
            parameters: Indicator-specific parameters
            
        Returns:
            Calculated value or None if insufficient data
        """
        if not data_points:
            return None
            
        # Extract common parameters
        t1 = float(parameters.get('t1', 300.0))  # Default 5 minutes
        t2 = float(parameters.get('t2', 0.0))    # Default current time
        
        # Dispatch to appropriate calculation method
        if indicator_type == "TWPA":
            return IndicatorCalculator.calculate_twpa_unified(
                data_points, current_timestamp, t1, t2
            )
        elif indicator_type == "VWAP":
            return IndicatorCalculator.calculate_vwap_unified(
                data_points, current_timestamp, t1, t2
            )
        elif indicator_type in ["MAX_PRICE", "MIN_PRICE", "FIRST_PRICE", "LAST_PRICE"]:
            return IndicatorCalculator.calculate_windowed_aggregate(
                data_points, current_timestamp, indicator_type, t1, t2
            )
        elif indicator_type == "TWPA_RATIO":
            t3 = float(parameters.get('t3', 1800.0))
            t4 = float(parameters.get('t4', 300.0))
            min_denominator = float(parameters.get('min_denominator', 0.001))

            numerator = IndicatorCalculator.calculate_twpa_unified(
                data_points, current_timestamp, t1, t2
            )
            denominator = IndicatorCalculator.calculate_twpa_unified(
                data_points, current_timestamp, t3, t4
            )

            if numerator is None or denominator is None:
                return None
            if abs(denominator) < min_denominator:
                return None
            return numerator / denominator
        else:
            # For legacy indicators, convert to simple price/timestamp lists
            prices = [point.price for point in data_points]
            timestamps = [point.timestamp for point in data_points]
            
            if indicator_type == "SMA":
                period = int(parameters.get('period', 20))
                result_list = IndicatorCalculator.calculate_sma(prices, period)
                return result_list[-1] if result_list else None
            elif indicator_type == "EMA":
                period = int(parameters.get('period', 20))
                result_list = IndicatorCalculator.calculate_ema(prices, period)
                return result_list[-1] if result_list else None
            elif indicator_type == "RSI":
                period = int(parameters.get('period', 14))
                result_list = IndicatorCalculator.calculate_rsi(prices, period)
                return result_list[-1] if result_list else None
            elif indicator_type == "VOLATILITY":
                period = int(parameters.get('period', 20))
                result_list = IndicatorCalculator.calculate_volatility(prices, period)
                return result_list[-1] if result_list else None
                
        return None

    @staticmethod
    def calculate_twpa_unified(data_points: List[MarketDataPoint],
                             current_timestamp: float,
                             t1: float,
                             t2: float = 0.0) -> Optional[float]:
        """
        Unified Time-Weighted Price Average calculation.
        
        Consolidates TWPA logic from all three indicator engines.
        
        Args:
            data_points: List of MarketDataPoint objects sorted by timestamp
            current_timestamp: Current time reference
            t1: Time window start (seconds back from current)
            t2: Time window end (seconds back from current, default 0)
            
        Returns:
            TWPA value or None if insufficient data
        """
        if not data_points or len(data_points) < 2:
            return None
            
        # Define time window
        window_start = current_timestamp - t1
        window_end = current_timestamp - t2
        
        # Filter points within window
        relevant_points = [
            point for point in data_points
            if window_start <= point.timestamp <= window_end
        ]
        
        if len(relevant_points) < 2:
            return None
            
        # Sort by timestamp to ensure proper ordering
        relevant_points.sort(key=lambda x: x.timestamp)
        
        # Calculate time-weighted average
        total_weighted_price = 0.0
        total_time = 0.0
        
        for i in range(len(relevant_points) - 1):
            current_point = relevant_points[i]
            next_point = relevant_points[i + 1]
            
            # Time duration for this price level
            time_duration = next_point.timestamp - current_point.timestamp
            
            # Weight the price by time duration
            weighted_price = current_point.price * time_duration
            total_weighted_price += weighted_price
            total_time += time_duration
            
        # Include the last point weighted to window end
        last_point = relevant_points[-1]
        final_duration = window_end - last_point.timestamp
        if final_duration > 0:
            total_weighted_price += last_point.price * final_duration
            total_time += final_duration
            
        return total_weighted_price / total_time if total_time > 0 else None

    @staticmethod
    def calculate_vwap_unified(data_points: List[MarketDataPoint],
                             current_timestamp: float,
                             t1: float,
                             t2: float = 0.0) -> Optional[float]:
        """
        Unified Volume-Weighted Average Price calculation.
        
        Consolidates VWAP logic from all three indicator engines.
        
        Args:
            data_points: List of MarketDataPoint objects with volume data
            current_timestamp: Current time reference
            t1: Time window start (seconds back from current)
            t2: Time window end (seconds back from current, default 0)
            
        Returns:
            VWAP value or None if insufficient data
        """
        if not data_points:
            return None
            
        # Define time window
        window_start = current_timestamp - t1
        window_end = current_timestamp - t2
        
        # Filter points within window
        relevant_points = [
            point for point in data_points
            if window_start <= point.timestamp <= window_end and 
               hasattr(point, 'volume') and point.volume > 0
        ]
        
        if not relevant_points:
            return None
            
        # Calculate volume-weighted average
        total_volume_price = 0.0
        total_volume = 0.0
        
        for point in relevant_points:
            volume = getattr(point, 'volume', 0.0)
            if volume > 0:
                total_volume_price += point.price * volume
                total_volume += volume
                
        return total_volume_price / total_volume if total_volume > 0 else None
