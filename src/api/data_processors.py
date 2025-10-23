"""
Data Processors
===============
Specialized processors for market data and technical indicators.
Production-ready with data validation, transformation, and filtering.
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
import time

from ..core.logger import StructuredLogger


@dataclass
class ProcessedMarketData:
    """Processed market data with validation and normalization"""

    symbol: str
    price: Decimal
    volume_24h: Optional[Decimal]
    change_24h: Optional[Decimal]
    bid: Optional[Decimal]
    ask: Optional[Decimal]
    spread: Optional[Decimal]
    timestamp: datetime
    exchange: str
    raw_data: Dict[str, Any]

    # Derived fields
    price_change_pct: Optional[Decimal] = None
    volume_usdt: Optional[Decimal] = None
    spread_pct: Optional[Decimal] = None

    def __post_init__(self):
        """Calculate derived fields"""
        if self.change_24h and self.price:
            self.price_change_pct = (self.change_24h / (self.price - self.change_24h)) * 100

        if self.volume_24h and self.price:
            self.volume_usdt = self.volume_24h * self.price

        if self.bid and self.ask and self.ask > 0:
            self.spread = self.ask - self.bid
            self.spread_pct = (self.spread / self.ask) * 100


@dataclass
class ProcessedIndicatorData:
    """Processed technical indicator data"""

    symbol: str
    indicator_type: str
    period: int
    timeframe: str
    value: Any  # Can be single value or dict of values
    timestamp: datetime
    raw_data: Dict[str, Any]

    # Metadata
    confidence: Optional[float] = None
    signal_strength: Optional[str] = None
    trend_direction: Optional[str] = None

    # Additional context
    price_at_calculation: Optional[Decimal] = None
    volume_at_calculation: Optional[Decimal] = None


class MarketDataProcessor:
    """
    Processes and validates market data from various exchanges.

    Features:
    - Data normalization across exchanges
    - Price and volume validation
    - Spread calculation
    - Timestamp synchronization
    - Anomaly detection
    """

    def __init__(self, logger: Optional[StructuredLogger] = None):
        self.logger = logger

        # Exchange-specific configurations
        self.exchange_configs = {
            "mexc": {
                "price_precision": 8,
                "volume_precision": 2,
                "timestamp_format": "milliseconds"
            },
            "binance": {
                "price_precision": 8,
                "volume_precision": 2,
                "timestamp_format": "milliseconds"
            },
            "bybit": {
                "price_precision": 8,
                "volume_precision": 2,
                "timestamp_format": "milliseconds"
            }
        }

        # Validation thresholds
        self.max_price_change_pct = Decimal('50')  # Max 50% price change
        self.min_volume_threshold = Decimal('0.000001')  # Minimum volume
        self.max_spread_pct = Decimal('10')  # Max 10% spread

        # Processing stats
        self.total_processed = 0
        self.total_validated = 0
        self.total_filtered = 0
        self.anomalies_detected = 0

    def process_market_data(self, raw_data: Dict[str, Any], exchange: str) -> Optional[ProcessedMarketData]:
        """
        Process raw market data into standardized format.

        Args:
            raw_data: Raw market data from exchange
            exchange: Exchange name (mexc, binance, etc.)

        Returns:
            Processed market data or None if invalid
        """
        self.total_processed += 1

        try:
            # Extract basic fields
            symbol = self._extract_symbol(raw_data, exchange)
            if not symbol:
                self._log_validation_error("missing_symbol", raw_data)
                return None

            price = self._extract_price(raw_data, exchange)
            if not price:
                self._log_validation_error("invalid_price", raw_data)
                return None

            volume_24h = self._extract_volume(raw_data, exchange)
            change_24h = self._extract_change(raw_data, exchange)
            bid = self._extract_bid(raw_data, exchange)
            ask = self._extract_ask(raw_data, exchange)
            timestamp = self._extract_timestamp(raw_data, exchange)

            # Validate data
            if not self._validate_market_data(symbol, price, volume_24h, change_24h):
                self.total_filtered += 1
                return None

            # Create processed data
            processed = ProcessedMarketData(
                symbol=symbol,
                price=price,
                volume_24h=volume_24h,
                change_24h=change_24h,
                bid=bid,
                ask=ask,
                spread=None,  # Will be calculated in __post_init__
                timestamp=timestamp,
                exchange=exchange,
                raw_data=raw_data
            )

            self.total_validated += 1

            if self.logger:
                self.logger.debug("market_data.processed", {
                    "symbol": symbol,
                    "price": str(price),
                    "exchange": exchange
                })

            return processed

        except Exception as e:
            self._log_processing_error("processing_error", raw_data, str(e))
            return None

    def _extract_symbol(self, data: Dict[str, Any], exchange: str) -> Optional[str]:
        """Extract symbol from raw data"""
        symbol_keys = ["symbol", "s", "instId", "instrument_name"]

        for key in symbol_keys:
            if key in data:
                symbol = str(data[key]).upper()
                # Normalize symbol format
                if exchange == "mexc":
                    return symbol.replace("_", "")
                return symbol

        return None

    def _extract_price(self, data: Dict[str, Any], exchange: str) -> Optional[Decimal]:
        """Extract and validate price"""
        price_keys = ["price", "c", "last", "lastPrice"]

        for key in price_keys:
            if key in data:
                try:
                    price = Decimal(str(data[key]))
                    if price <= 0:
                        return None

                    # Apply precision limits
                    config = self.exchange_configs.get(exchange, {})
                    precision = config.get("price_precision", 8)
                    price = price.quantize(Decimal('1e-{}'.format(precision)), rounding=ROUND_DOWN)

                    return price
                except:
                    continue

        return None

    def _extract_volume(self, data: Dict[str, Any], exchange: str) -> Optional[Decimal]:
        """Extract volume data"""
        volume_keys = ["volume_24h", "v", "volume", "vol", "volume24h"]

        for key in volume_keys:
            if key in data:
                try:
                    volume = Decimal(str(data[key]))
                    if volume < 0:
                        return None

                    # Apply precision limits
                    config = self.exchange_configs.get(exchange, {})
                    precision = config.get("volume_precision", 2)
                    volume = volume.quantize(Decimal('1e-{}'.format(precision)), rounding=ROUND_DOWN)

                    return volume
                except:
                    continue

        return None

    def _extract_change(self, data: Dict[str, Any], exchange: str) -> Optional[Decimal]:
        """Extract 24h price change"""
        change_keys = ["change_24h", "P", "priceChange", "change", "change24h"]

        for key in change_keys:
            if key in data:
                try:
                    change = Decimal(str(data[key]))
                    return change
                except:
                    continue

        return None

    def _extract_bid(self, data: Dict[str, Any], exchange: str) -> Optional[Decimal]:
        """Extract bid price"""
        bid_keys = ["bid", "b", "bidPrice"]

        for key in bid_keys:
            if key in data:
                try:
                    bid = Decimal(str(data[key]))
                    return bid if bid > 0 else None
                except:
                    continue

        return None

    def _extract_ask(self, data: Dict[str, Any], exchange: str) -> Optional[Decimal]:
        """Extract ask price"""
        ask_keys = ["ask", "a", "askPrice"]

        for key in ask_keys:
            if key in data:
                try:
                    ask = Decimal(str(data[key]))
                    return ask if ask > 0 else None
                except:
                    continue

        return None

    def _extract_timestamp(self, data: Dict[str, Any], exchange: str) -> datetime:
        """Extract and normalize timestamp"""
        timestamp_keys = ["timestamp", "T", "time", "eventTime"]

        for key in timestamp_keys:
            if key in data:
                try:
                    ts = data[key]
                    if isinstance(ts, str):
                        # Assume ISO format
                        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    elif isinstance(ts, (int, float)):
                        # Convert from milliseconds or seconds
                        config = self.exchange_configs.get(exchange, {})
                        if config.get("timestamp_format") == "milliseconds":
                            ts = ts / 1000
                        return datetime.fromtimestamp(ts)
                except:
                    continue

        # Fallback to current time
        return datetime.now()

    def _validate_market_data(self, symbol: str, price: Decimal,
                            volume: Optional[Decimal], change: Optional[Decimal]) -> bool:
        """Validate market data for anomalies"""

        # Price validation
        if price <= 0:
            return False

        # Volume validation
        if volume is not None and volume < self.min_volume_threshold:
            return False

        # Price change validation (if available)
        if change is not None and price > 0:
            change_pct = abs(change / (price - change)) * 100
            if change_pct > self.max_price_change_pct:
                self.anomalies_detected += 1
                if self.logger:
                    self.logger.warning("market_data.anomaly_detected", {
                        "symbol": symbol,
                        "price_change_pct": str(change_pct),
                        "threshold": str(self.max_price_change_pct)
                    })
                return False

        return True

    def _log_validation_error(self, error_type: str, data: Dict[str, Any]):
        """Log validation errors"""
        if self.logger:
            self.logger.warning("market_data.validation_error", {
                "error_type": error_type,
                "data_keys": list(data.keys())
            })

    def _log_processing_error(self, error_type: str, data: Dict[str, Any], error: str):
        """Log processing errors"""
        if self.logger:
            self.logger.error("market_data.processing_error", {
                "error_type": error_type,
                "error": error,
                "data_keys": list(data.keys())
            })

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            "total_processed": self.total_processed,
            "total_validated": self.total_validated,
            "total_filtered": self.total_filtered,
            "anomalies_detected": self.anomalies_detected,
            "validation_rate": (self.total_validated / max(self.total_processed, 1)) * 100,
            "filter_rate": (self.total_filtered / max(self.total_processed, 1)) * 100
        }


class IndicatorProcessor:
    """
    Processes technical indicator data with validation and enrichment.

    Features:
    - Indicator value validation
    - Signal strength calculation
    - Trend analysis
    - Confidence scoring
    - Cross-indicator correlation
    """

    def __init__(self, logger: Optional[StructuredLogger] = None):
        self.logger = logger

        # Indicator configurations
        self.indicator_configs = {
            "RSI": {
                "min_value": 0,
                "max_value": 100,
                "overbought_threshold": 70,
                "oversold_threshold": 30
            },
            "MACD": {
                "validate_components": True,  # histogram, signal, macd line
                "min_histogram": -10,
                "max_histogram": 10
            },
            "SMA": {
                "min_period": 5,
                "max_period": 200,
                "validate_trend": True
            },
            "EMA": {
                "min_period": 5,
                "max_period": 200
            },
            "BollingerBands": {
                "validate_bands": True,  # upper, middle, lower
                "min_bandwidth": 0.001
            }
        }

        # Processing stats
        self.total_processed = 0
        self.total_validated = 0
        self.total_enriched = 0
        self.signals_generated = 0

    def process_indicator_data(self, raw_data: Dict[str, Any]) -> Optional[ProcessedIndicatorData]:
        """
        Process raw indicator data into standardized format.

        Args:
            raw_data: Raw indicator data

        Returns:
            Processed indicator data or None if invalid
        """
        self.total_processed += 1

        try:
            # Extract basic fields
            symbol = self._extract_symbol(raw_data)
            if not symbol:
                self._log_validation_error("missing_symbol", raw_data)
                return None

            indicator_type = self._extract_indicator_type(raw_data)
            if not indicator_type:
                self._log_validation_error("missing_indicator_type", raw_data)
                return None

            period = self._extract_period(raw_data)
            timeframe = self._extract_timeframe(raw_data)
            value = self._extract_value(raw_data, indicator_type)
            timestamp = self._extract_timestamp(raw_data)

            # Validate indicator data
            if not self._validate_indicator_data(indicator_type, value, period):
                return None

            # Create processed data
            processed = ProcessedIndicatorData(
                symbol=symbol,
                indicator_type=indicator_type,
                period=period,
                timeframe=timeframe,
                value=value,
                timestamp=timestamp,
                raw_data=raw_data
            )

            # Enrich with additional data
            self._enrich_indicator_data(processed)

            self.total_validated += 1
            self.total_enriched += 1

            if self.logger:
                self.logger.debug("indicator_data.processed", {
                    "symbol": symbol,
                    "indicator_type": indicator_type,
                    "period": period,
                    "timeframe": timeframe
                })

            return processed

        except Exception as e:
            self._log_processing_error("processing_error", raw_data, str(e))
            return None

    def _extract_symbol(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract symbol from indicator data"""
        symbol_keys = ["symbol", "s", "instrument"]

        for key in symbol_keys:
            if key in data:
                return str(data[key]).upper()

        return None

    def _extract_indicator_type(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract indicator type"""
        type_keys = ["indicator_type", "type", "indicator", "name"]

        for key in type_keys:
            if key in data:
                indicator_type = str(data[key]).upper()
                # Normalize common variations
                if indicator_type in ["RELATIVE_STRENGTH_INDEX", "RELATIVE_STRENGTH"]:
                    return "RSI"
                elif indicator_type in ["MOVING_AVERAGE_CONVERGENCE_DIVERGENCE"]:
                    return "MACD"
                elif indicator_type in ["SIMPLE_MOVING_AVERAGE"]:
                    return "SMA"
                elif indicator_type in ["EXPONENTIAL_MOVING_AVERAGE"]:
                    return "EMA"
                elif indicator_type in ["BOLLINGER_BANDS", "BBANDS"]:
                    return "BollingerBands"
                else:
                    return indicator_type

        return None

    def _extract_period(self, data: Dict[str, Any]) -> int:
        """Extract indicator period"""
        period_keys = ["period", "p", "length", "window"]

        for key in period_keys:
            if key in data:
                try:
                    return int(data[key])
                except:
                    continue

        return 14  # Default period

    def _extract_timeframe(self, data: Dict[str, Any]) -> str:
        """Extract timeframe"""
        timeframe_keys = ["timeframe", "tf", "interval", "period"]

        for key in timeframe_keys:
            if key in data:
                timeframe = str(data[key]).lower()
                # Normalize timeframe format
                if timeframe in ["1m", "1min", "1minute"]:
                    return "1m"
                elif timeframe in ["5m", "5min", "5minute"]:
                    return "5m"
                elif timeframe in ["15m", "15min", "15minute"]:
                    return "15m"
                elif timeframe in ["1h", "1hour", "60m"]:
                    return "1h"
                elif timeframe in ["4h", "4hour"]:
                    return "4h"
                elif timeframe in ["1d", "1day", "daily"]:
                    return "1d"
                else:
                    return timeframe

        return "1h"  # Default timeframe

    def _extract_value(self, data: Dict[str, Any], indicator_type: str) -> Any:
        """Extract indicator value(s)"""
        value_keys = ["value", "v", "result", "output"]

        for key in value_keys:
            if key in data:
                value = data[key]

                # Handle different indicator value formats
                if indicator_type == "RSI":
                    return float(value) if isinstance(value, (int, float, str)) else value
                elif indicator_type == "MACD":
                    if isinstance(value, dict):
                        return value
                    elif isinstance(value, list) and len(value) >= 3:
                        return {
                            "macd": value[0],
                            "signal": value[1],
                            "histogram": value[2]
                        }
                elif indicator_type in ["SMA", "EMA"]:
                    return float(value) if isinstance(value, (int, float, str)) else value
                elif indicator_type == "BollingerBands":
                    if isinstance(value, dict):
                        return value
                    elif isinstance(value, list) and len(value) >= 3:
                        return {
                            "upper": value[0],
                            "middle": value[1],
                            "lower": value[2]
                        }

                return value

        return None

    def _extract_timestamp(self, data: Dict[str, Any]) -> datetime:
        """Extract timestamp"""
        timestamp_keys = ["timestamp", "time", "T", "created_at"]

        for key in timestamp_keys:
            if key in data:
                try:
                    ts = data[key]
                    if isinstance(ts, str):
                        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    elif isinstance(ts, (int, float)):
                        return datetime.fromtimestamp(ts)
                except:
                    continue

        return datetime.now()

    def _validate_indicator_data(self, indicator_type: str, value: Any, period: int) -> bool:
        """Validate indicator data"""
        if not value:
            return False

        config = self.indicator_configs.get(indicator_type, {})

        # Period validation
        if "min_period" in config and period < config["min_period"]:
            return False
        if "max_period" in config and period > config["max_period"]:
            return False

        # Value validation based on indicator type
        if indicator_type == "RSI":
            if isinstance(value, (int, float)):
                return 0 <= value <= 100
        elif indicator_type == "MACD":
            if isinstance(value, dict):
                required_keys = ["macd", "signal", "histogram"]
                return all(key in value for key in required_keys)
        elif indicator_type in ["SMA", "EMA"]:
            if isinstance(value, (int, float)):
                return value > 0
        elif indicator_type == "BollingerBands":
            if isinstance(value, dict):
                required_keys = ["upper", "middle", "lower"]
                return all(key in value for key in required_keys)

        return True

    def _enrich_indicator_data(self, processed: ProcessedIndicatorData):
        """Enrich indicator data with additional analysis"""

        # Add confidence scoring
        processed.confidence = self._calculate_confidence(processed)

        # Add signal strength for oscillators
        if processed.indicator_type == "RSI":
            processed.signal_strength = self._analyze_rsi_signal(processed.value)

        # Add trend direction for moving averages
        elif processed.indicator_type in ["SMA", "EMA"]:
            processed.trend_direction = self._analyze_ma_trend(processed)

        # Add market context if available
        if "price" in processed.raw_data:
            processed.price_at_calculation = Decimal(str(processed.raw_data["price"]))

        if "volume" in processed.raw_data:
            processed.volume_at_calculation = Decimal(str(processed.raw_data["volume"]))

    def _calculate_confidence(self, processed: ProcessedIndicatorData) -> float:
        """Calculate confidence score for indicator"""
        # Simple confidence calculation based on data completeness
        confidence = 0.5  # Base confidence

        # Higher confidence for longer periods
        if processed.period >= 20:
            confidence += 0.2
        elif processed.period >= 14:
            confidence += 0.1

        # Higher confidence for well-known timeframes
        if processed.timeframe in ["1h", "4h", "1d"]:
            confidence += 0.2
        elif processed.timeframe in ["15m", "30m"]:
            confidence += 0.1

        # Higher confidence for complete data
        if processed.price_at_calculation and processed.volume_at_calculation:
            confidence += 0.2

        return min(1.0, confidence)

    def _analyze_rsi_signal(self, rsi_value: float) -> str:
        """Analyze RSI signal strength"""
        if rsi_value >= 70:
            return "overbought"
        elif rsi_value <= 30:
            return "oversold"
        elif 40 <= rsi_value <= 60:
            return "neutral"
        else:
            return "moderate"

    def _analyze_ma_trend(self, processed: ProcessedIndicatorData) -> str:
        """Analyze moving average trend"""
        # This would typically compare with previous values
        # For now, return neutral
        return "neutral"

    def _log_validation_error(self, error_type: str, data: Dict[str, Any]):
        """Log validation errors"""
        if self.logger:
            self.logger.warning("indicator_data.validation_error", {
                "error_type": error_type,
                "data_keys": list(data.keys())
            })

    def _log_processing_error(self, error_type: str, data: Dict[str, Any], error: str):
        """Log processing errors"""
        if self.logger:
            self.logger.error("indicator_data.processing_error", {
                "error_type": error_type,
                "error": error,
                "data_keys": list(data.keys())
            })

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            "total_processed": self.total_processed,
            "total_validated": self.total_validated,
            "total_enriched": self.total_enriched,
            "signals_generated": self.signals_generated,
            "validation_rate": (self.total_validated / max(self.total_processed, 1)) * 100,
            "enrichment_rate": (self.total_enriched / max(self.total_validated, 1)) * 100
        }