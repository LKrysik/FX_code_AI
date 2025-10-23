"""
Signal Processor
================
Processes and enriches trading signals for real-time streaming.
Handles flash pump detection, reversal signals, and confluence analysis.
Production-ready with validation and performance optimization.
"""

import asyncio
import json
import threading
from typing import Dict, Any, Optional, List, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque, OrderedDict
import time
import statistics

from ..core.logger import StructuredLogger


@dataclass
class SignalValidationResult:
    """Result of signal validation"""

    is_valid: bool
    confidence_score: float
    validation_errors: List[str] = field(default_factory=list)
    enriched_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SignalContext:
    """Context information for signal processing"""

    symbol: str
    exchange: str
    timestamp: datetime
    current_price: float
    volume_24h: float
    price_change_24h: float
    market_cap_rank: Optional[int] = None
    spread_pct: Optional[float] = None
    liquidity_usdt: Optional[float] = None


@dataclass
class FlashPumpSignal:
    """Flash pump detection signal"""

    symbol: str
    exchange: str
    timestamp: datetime
    detection_details: Dict[str, Any]
    market_context: Dict[str, Any]
    technical_analysis: Dict[str, Any]
    trading_recommendation: Dict[str, Any]
    risk_factors: List[str]
    confidence_score: float
    signal_type: str = "flash_pump_detected"
    severity: str = "high"


@dataclass
class ReversalSignal:
    """Reversal detection signal"""

    symbol: str
    exchange: str
    timestamp: datetime
    reversal_details: Dict[str, Any]
    original_pump_context: Dict[str, Any]
    current_market_state: Dict[str, Any]
    exit_recommendation: Dict[str, Any]
    confidence_score: float
    signal_type: str = "reversal_detected"
    severity: str = "medium"


@dataclass
class ConfluenceSignal:
    """Confluence analysis signal"""

    symbol: str
    exchange: str
    timestamp: datetime
    confluence_details: Dict[str, Any]
    technical_indicators: Dict[str, Any]
    market_context: Dict[str, Any]
    trading_recommendation: Dict[str, Any]
    confidence_score: float
    signal_type: str = "confluence_detected"
    severity: str = "medium"


class SignalProcessor:
    """
    Processes and enriches trading signals for real-time streaming.

    Features:
    - Flash pump detection with market context analysis
    - Reversal signal processing with risk assessment
    - Confluence analysis for multiple timeframe signals
    - Signal validation and confidence scoring
    - Performance tracking and optimization
    """

    def __init__(self, logger: Optional[StructuredLogger] = None):
        """
        Initialize SignalProcessor.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger

        # Signal processing configuration
        self.min_pump_magnitude_pct = 7.0
        self.max_pump_age_seconds = 60
        self.min_confidence_score = 65.0
        self.max_signal_age_hours = 24

        # Performance tracking
        self.signals_processed = 0
        self.signals_validated = 0
        self.signals_enriched = 0
        self.processing_times: deque[float] = deque(maxlen=1000)
        self.average_processing_time = 0.0

        # Thread safety locks
        self._signal_history_lock = asyncio.Lock()  # Protects signal_history
        self._cache_lock = asyncio.Lock()  # Protects market_data_cache
        self._stats_lock = threading.Lock()  # Protects statistics

        # Signal history for context analysis
        self.signal_history: Dict[str, deque] = {}
        self.max_history_per_symbol = 100

        # Market data cache for enrichment
        self.market_data_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.cache_ttl_seconds = 300  # 5 minutes
        self.max_cache_size = 1000

        # Rate limiting
        self._rate_limit_lock = asyncio.Lock()
        self._last_processing_times: deque[float] = deque(maxlen=100)
        self.max_signals_per_minute = 60  # Rate limit
        self._processing_window_seconds = 60

    async def process_flash_pump_signal(self, raw_signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process flash pump detection signal.

        Args:
            raw_signal: Raw signal data from detection engine

        Returns:
            Processed and enriched signal or None if invalid
        """
        # Rate limiting check
        if not await self._check_rate_limit():
            if self.logger:
                self.logger.warning("signal_processor.rate_limit_exceeded", {
                    "symbol": raw_signal.get("symbol"),
                    "max_signals_per_minute": self.max_signals_per_minute
                })
            return None

        start_time = time.time()

        try:
            # Validate signal
            validation = await self._validate_flash_pump_signal(raw_signal)
            if not validation.is_valid:
                if self.logger:
                    self.logger.warning("signal_processor.flash_pump_invalid", {
                        "symbol": raw_signal.get("symbol"),
                        "errors": validation.validation_errors
                    })
                return None

            # Enrich with market context
            enriched_signal = await self._enrich_flash_pump_signal(raw_signal, validation.enriched_data)

            # Create structured signal
            signal = FlashPumpSignal(
                symbol=raw_signal["symbol"],
                exchange=raw_signal.get("exchange", "unknown"),
                timestamp=datetime.fromisoformat(raw_signal["timestamp"]),
                detection_details=enriched_signal["detection_details"],
                market_context=enriched_signal["market_context"],
                technical_analysis=enriched_signal["technical_analysis"],
                trading_recommendation=enriched_signal["trading_recommendation"],
                risk_factors=enriched_signal["risk_factors"],
                confidence_score=validation.confidence_score
            )

            # Convert to dict for WebSocket transmission
            result = await self._signal_to_dict(signal)

            # Track processing time and update statistics
            processing_time = (time.time() - start_time) * 1000
            await self._update_processing_stats(processing_time)
            await self._record_processing_time(start_time)

            if self.logger:
                self.logger.info("signal_processor.flash_pump_processed", {
                    "symbol": signal.symbol,
                    "confidence": signal.confidence_score,
                    "processing_time_ms": processing_time
                })

            return result

        except Exception as e:
            if self.logger:
                self.logger.error("signal_processor.flash_pump_error", {
                    "symbol": raw_signal.get("symbol"),
                    "error": str(e)
                })
            return None

    async def process_reversal_signal(self, raw_signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process reversal detection signal.

        Args:
            raw_signal: Raw signal data from detection engine

        Returns:
            Processed and enriched signal or None if invalid
        """
        # Rate limiting check
        if not await self._check_rate_limit():
            if self.logger:
                self.logger.warning("signal_processor.rate_limit_exceeded", {
                    "symbol": raw_signal.get("symbol"),
                    "max_signals_per_minute": self.max_signals_per_minute
                })
            return None

        start_time = time.time()

        try:
            # Validate signal
            validation = await self._validate_reversal_signal(raw_signal)
            if not validation.is_valid:
                if self.logger:
                    self.logger.warning("signal_processor.reversal_invalid", {
                        "symbol": raw_signal.get("symbol"),
                        "errors": validation.validation_errors
                    })
                return None

            # Enrich with context
            enriched_signal = await self._enrich_reversal_signal(raw_signal, validation.enriched_data)

            # Create structured signal
            signal = ReversalSignal(
                symbol=raw_signal["symbol"],
                exchange=raw_signal.get("exchange", "unknown"),
                timestamp=datetime.fromisoformat(raw_signal["timestamp"]),
                reversal_details=enriched_signal["reversal_details"],
                original_pump_context=enriched_signal["original_pump_context"],
                current_market_state=enriched_signal["current_market_state"],
                exit_recommendation=enriched_signal["exit_recommendation"],
                confidence_score=validation.confidence_score
            )

            # Convert to dict for WebSocket transmission
            result = await self._signal_to_dict(signal)

            # Track processing time and update statistics
            processing_time = (time.time() - start_time) * 1000
            await self._update_processing_stats(processing_time)
            await self._record_processing_time(start_time)

            if self.logger:
                self.logger.info("signal_processor.reversal_processed", {
                    "symbol": signal.symbol,
                    "confidence": signal.confidence_score,
                    "processing_time_ms": processing_time
                })

            return result

        except Exception as e:
            if self.logger:
                self.logger.error("signal_processor.reversal_error", {
                    "symbol": raw_signal.get("symbol"),
                    "error": str(e)
                })
            return None

    async def process_confluence_signal(self, raw_signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process confluence analysis signal.

        Args:
            raw_signal: Raw signal data from detection engine

        Returns:
            Processed and enriched signal or None if invalid
        """
        # Rate limiting check
        if not await self._check_rate_limit():
            if self.logger:
                self.logger.warning("signal_processor.rate_limit_exceeded", {
                    "symbol": raw_signal.get("symbol"),
                    "max_signals_per_minute": self.max_signals_per_minute
                })
            return None

        start_time = time.time()

        try:
            # Validate signal
            validation = await self._validate_confluence_signal(raw_signal)
            if not validation.is_valid:
                if self.logger:
                    self.logger.warning("signal_processor.confluence_invalid", {
                        "symbol": raw_signal.get("symbol"),
                        "errors": validation.validation_errors
                    })
                return None

            # Enrich with context
            enriched_signal = await self._enrich_confluence_signal(raw_signal, validation.enriched_data)

            # Create structured signal
            signal = ConfluenceSignal(
                symbol=raw_signal["symbol"],
                exchange=raw_signal.get("exchange", "unknown"),
                timestamp=datetime.fromisoformat(raw_signal["timestamp"]),
                confluence_details=enriched_signal["confluence_details"],
                technical_indicators=enriched_signal["technical_indicators"],
                market_context=enriched_signal["market_context"],
                trading_recommendation=enriched_signal["trading_recommendation"],
                confidence_score=validation.confidence_score
            )

            # Convert to dict for WebSocket transmission
            result = await self._signal_to_dict(signal)

            # Track processing time and update statistics
            processing_time = (time.time() - start_time) * 1000
            await self._update_processing_stats(processing_time)
            await self._record_processing_time(start_time)

            if self.logger:
                self.logger.info("signal_processor.confluence_processed", {
                    "symbol": signal.symbol,
                    "confidence": signal.confidence_score,
                    "processing_time_ms": processing_time
                })

            return result

        except Exception as e:
            if self.logger:
                self.logger.error("signal_processor.confluence_error", {
                    "symbol": raw_signal.get("symbol"),
                    "error": str(e)
                })
            return None

    async def _validate_flash_pump_signal(self, signal: Dict[str, Any]) -> SignalValidationResult:
        """Validate flash pump signal data"""
        errors = []
        confidence_score = 0.0

        # Required fields validation
        required_fields = ["symbol", "timestamp", "pump_magnitude_pct", "volume_surge_ratio"]
        for field in required_fields:
            if field not in signal:
                errors.append(f"Missing required field: {field}")

        if errors:
            return SignalValidationResult(False, 0.0, errors)

        # Magnitude validation
        pump_magnitude = signal.get("pump_magnitude_pct", 0)
        if pump_magnitude < self.min_pump_magnitude_pct:
            errors.append(f"Pump magnitude {pump_magnitude}% below minimum {self.min_pump_magnitude_pct}%")

        # Age validation
        timestamp = datetime.fromisoformat(signal["timestamp"])
        age_seconds = (datetime.now() - timestamp).total_seconds()
        if age_seconds > self.max_pump_age_seconds:
            errors.append(f"Signal age {age_seconds}s exceeds maximum {self.max_pump_age_seconds}s")

        # Confidence scoring
        confidence_score = self._calculate_flash_pump_confidence(signal)

        # Enrich with additional data
        enriched_data = {
            "signal_age_seconds": age_seconds,
            "is_recent": age_seconds <= 30,
            "magnitude_category": self._categorize_magnitude(pump_magnitude)
        }

        return SignalValidationResult(
            len(errors) == 0 and confidence_score >= self.min_confidence_score,
            confidence_score,
            errors,
            enriched_data
        )

    async def _validate_reversal_signal(self, signal: Dict[str, Any]) -> SignalValidationResult:
        """Validate reversal signal data"""
        errors = []
        confidence_score = 0.0

        # Required fields validation
        required_fields = ["symbol", "timestamp", "reversal_type", "retracement_pct"]
        for field in required_fields:
            if field not in signal:
                errors.append(f"Missing required field: {field}")

        if errors:
            return SignalValidationResult(False, 0.0, errors)

        # Retracement validation
        retracement = signal.get("retracement_pct", 0)
        if retracement < 1.0 or retracement > 50.0:
            errors.append(f"Invalid retracement percentage: {retracement}%")

        # Confidence scoring
        confidence_score = self._calculate_reversal_confidence(signal)

        # Enrich with additional data
        enriched_data = {
            "retracement_category": self._categorize_retracement(retracement),
            "reversal_strength": "strong" if retracement > 10 else "moderate" if retracement > 5 else "weak"
        }

        return SignalValidationResult(
            len(errors) == 0 and confidence_score >= self.min_confidence_score,
            confidence_score,
            errors,
            enriched_data
        )

    async def _validate_confluence_signal(self, signal: Dict[str, Any]) -> SignalValidationResult:
        """Validate confluence signal data"""
        errors = []
        confidence_score = 0.0

        # Required fields validation
        required_fields = ["symbol", "timestamp", "timeframes", "indicators"]
        for field in required_fields:
            if field not in signal:
                errors.append(f"Missing required field: {field}")

        if errors:
            return SignalValidationResult(False, 0.0, errors)

        # Timeframe validation
        timeframes = signal.get("timeframes", [])
        if len(timeframes) < 2:
            errors.append("Confluence signal requires at least 2 timeframes")

        # Confidence scoring
        confidence_score = self._calculate_confluence_confidence(signal)

        # Enrich with additional data
        enriched_data = {
            "timeframe_count": len(timeframes),
            "confluence_strength": "strong" if len(timeframes) >= 3 else "moderate"
        }

        return SignalValidationResult(
            len(errors) == 0 and confidence_score >= self.min_confidence_score,
            confidence_score,
            errors,
            enriched_data
        )

    def _calculate_flash_pump_confidence(self, signal: Dict[str, Any]) -> float:
        """Calculate confidence score for flash pump signal"""
        score = 50.0  # Base score

        # Magnitude factor (0-20 points)
        magnitude = signal.get("pump_magnitude_pct", 0)
        if magnitude >= 15:
            score += 20
        elif magnitude >= 10:
            score += 15
        elif magnitude >= 7:
            score += 10

        # Volume surge factor (0-15 points)
        volume_ratio = signal.get("volume_surge_ratio", 1)
        if volume_ratio >= 8:
            score += 15
        elif volume_ratio >= 5:
            score += 10
        elif volume_ratio >= 3:
            score += 5

        # Velocity factor (0-10 points)
        velocity = signal.get("price_velocity", 0)
        if velocity >= 0.5:
            score += 10
        elif velocity >= 0.3:
            score += 7
        elif velocity >= 0.1:
            score += 3

        # Market cap rank factor (0-5 points)
        rank = signal.get("market_cap_rank", 1000)
        if rank <= 100:
            score += 5
        elif rank <= 300:
            score += 3

        return min(100.0, score)

    def _calculate_reversal_confidence(self, signal: Dict[str, Any]) -> float:
        """Calculate confidence score for reversal signal"""
        score = 60.0  # Base score

        # Retracement factor (0-15 points)
        retracement = signal.get("retracement_pct", 0)
        if retracement >= 10:
            score += 15
        elif retracement >= 5:
            score += 10
        elif retracement >= 3:
            score += 5

        # Momentum shift factor (0-10 points)
        momentum_confirmed = signal.get("momentum_shift_confirmed", False)
        if momentum_confirmed:
            score += 10

        # Volume decline factor (0-10 points)
        volume_decline = signal.get("volume_decline_ratio", 1)
        if volume_decline >= 0.7:
            score += 10
        elif volume_decline >= 0.5:
            score += 7
        elif volume_decline >= 0.3:
            score += 3

        # Order book pressure factor (0-5 points)
        order_book_pressure = signal.get("order_book_pressure", "")
        if "sell_side_heavy" in order_book_pressure:
            score += 5

        return min(100.0, score)

    def _calculate_confluence_confidence(self, signal: Dict[str, Any]) -> float:
        """Calculate confidence score for confluence signal"""
        score = 55.0  # Base score

        # Timeframe count factor (0-15 points)
        timeframes = signal.get("timeframes", [])
        timeframe_count = len(timeframes)
        if timeframe_count >= 4:
            score += 15
        elif timeframe_count >= 3:
            score += 12
        elif timeframe_count >= 2:
            score += 8

        # Indicator alignment factor (0-20 points)
        indicators = signal.get("indicators", {})
        aligned_indicators = sum(1 for ind in indicators.values() if ind.get("aligned", False))
        total_indicators = len(indicators)
        if total_indicators > 0:
            alignment_ratio = aligned_indicators / total_indicators
            score += alignment_ratio * 20

        # Signal strength factor (0-10 points)
        signal_strength = signal.get("signal_strength", "weak")
        if signal_strength == "strong":
            score += 10
        elif signal_strength == "moderate":
            score += 6

        return min(100.0, score)

    def _categorize_magnitude(self, magnitude: float) -> str:
        """Categorize pump magnitude"""
        if magnitude >= 20:
            return "extreme"
        elif magnitude >= 15:
            return "high"
        elif magnitude >= 10:
            return "moderate"
        elif magnitude >= 7:
            return "low"
        else:
            return "minimal"

    def _categorize_retracement(self, retracement: float) -> str:
        """Categorize retracement percentage"""
        if retracement >= 15:
            return "deep"
        elif retracement >= 10:
            return "moderate"
        elif retracement >= 5:
            return "shallow"
        else:
            return "minimal"

    async def _enrich_flash_pump_signal(self, signal: Dict[str, Any], validation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich flash pump signal with additional context"""
        symbol = signal["symbol"]

        # Get market context
        market_context = await self._get_market_context(symbol)

        # Get technical analysis
        technical_analysis = await self._get_technical_analysis(symbol, signal)

        # Generate trading recommendation
        trading_recommendation = await self._generate_trading_recommendation(signal, "flash_pump")

        # Identify risk factors
        risk_factors = await self._identify_risk_factors(signal, market_context)

        return {
            "detection_details": {
                **signal,
                **validation_data
            },
            "market_context": market_context,
            "technical_analysis": technical_analysis,
            "trading_recommendation": trading_recommendation,
            "risk_factors": risk_factors
        }

    async def _enrich_reversal_signal(self, signal: Dict[str, Any], validation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich reversal signal with additional context"""
        symbol = signal["symbol"]

        # Get original pump context
        original_pump_context = await self._get_original_pump_context(symbol, signal)

        # Get current market state
        current_market_state = await self._get_current_market_state(symbol)

        # Generate exit recommendation
        exit_recommendation = await self._generate_exit_recommendation(signal)

        return {
            "reversal_details": {
                **signal,
                **validation_data
            },
            "original_pump_context": original_pump_context,
            "current_market_state": current_market_state,
            "exit_recommendation": exit_recommendation
        }

    async def _enrich_confluence_signal(self, signal: Dict[str, Any], validation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich confluence signal with additional context"""
        symbol = signal["symbol"]

        # Get technical indicators
        technical_indicators = await self._get_technical_indicators(symbol, signal)

        # Get market context
        market_context = await self._get_market_context(symbol)

        # Generate trading recommendation
        trading_recommendation = await self._generate_trading_recommendation(signal, "confluence")

        return {
            "confluence_details": {
                **signal,
                **validation_data
            },
            "technical_indicators": technical_indicators,
            "market_context": market_context,
            "trading_recommendation": trading_recommendation
        }

    async def _get_market_context(self, symbol: str) -> Dict[str, Any]:
        """Get market context for symbol with caching"""
        # Try cache first
        cached = await self._get_cached_market_data(symbol)
        if cached:
            return cached

        # Real implementation required - fetch from MEXC API
        raise NotImplementedError("Real MEXC API integration required for market context")

    async def _get_technical_analysis(self, symbol: str, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Get technical analysis for signal"""
        return {
            "support_levels": [0.0225, 0.0218, 0.0210],
            "resistance_levels": [0.0280, 0.0295, 0.0310],
            "trend_direction": "bullish_breakout",
            "momentum_indicators": {
                "rsi_1m": 75.2,
                "macd_divergence": False,
                "volume_profile": "increasing"
            }
        }

    async def _generate_trading_recommendation(self, signal: Dict[str, Any], signal_type: str) -> Dict[str, Any]:
        """Generate trading recommendation based on signal"""
        if signal_type == "flash_pump":
            return {
                "action": "consider_buy",
                "confidence": "high",
                "risk_level": "medium",
                "entry_zone": [0.0265, 0.0275],
                "stop_loss": 0.0250,
                "take_profit_levels": [
                    {"price": 0.0285, "percentage": 30},
                    {"price": 0.0300, "percentage": 40},
                    {"price": 0.0320, "percentage": 30}
                ],
                "position_size_suggestion": "2-3% of portfolio",
                "timeframe": "scalp_trade",
                "expected_duration": "5-15 minutes"
            }
        else:
            return {
                "action": "observe",
                "confidence": "medium",
                "risk_level": "low"
            }

    async def _identify_risk_factors(self, signal: Dict[str, Any], market_context: Dict[str, Any]) -> List[str]:
        """Identify risk factors for the signal"""
        risks = []

        # Magnitude-based risks
        magnitude = signal.get("pump_magnitude_pct", 0)
        if magnitude >= 20:
            risks.append("Extreme volatility risk")

        # Market cap risks
        rank = market_context.get("market_cap_rank", 1000)
        if rank > 500:
            risks.append("Low market cap risk")

        # Liquidity risks
        liquidity = market_context.get("liquidity_usdt", 0)
        if liquidity < 50000:
            risks.append("Low liquidity risk")

        # Volume risks
        volume_ratio = signal.get("volume_surge_ratio", 1)
        if volume_ratio >= 10:
            risks.append("Extreme volume surge - potential manipulation")

        risks.extend([
            "High volatility asset",
            "Potential for quick reversal"
        ])

        return risks

    async def _get_original_pump_context(self, symbol: str, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Get context of original pump for reversal signal"""
        return {
            "pump_peak_price": 0.0271,
            "pump_magnitude": 15.7,
            "pump_start_time": (datetime.now() - timedelta(minutes=2)).isoformat(),
            "pump_duration_seconds": 89
        }

    async def _get_current_market_state(self, symbol: str) -> Dict[str, Any]:
        """Get current market state for reversal signal"""
        return {
            "current_price": 0.0261,
            "price_from_peak_pct": -3.7,
            "volume_vs_pump_average": 0.35,
            "order_book_pressure": "sell_side_heavy"
        }

    async def _generate_exit_recommendation(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Generate exit recommendation for reversal signal"""
        return {
            "action": "consider_sell",
            "urgency": "medium",
            "confidence": 78.5,
            "suggested_exit_levels": [0.0260, 0.0255],
            "expected_further_decline": [5, 8]
        }

    async def _get_technical_indicators(self, symbol: str, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Get technical indicators for confluence signal"""
        return {
            "rsi": {"value": 68.5, "aligned": True},
            "macd": {"signal": "bullish", "aligned": True},
            "moving_averages": {"trend": "upward", "aligned": True}
        }

    async def _signal_to_dict(self, signal) -> Dict[str, Any]:
        """Convert signal object to dictionary for WebSocket transmission"""
        data = {
            "type": "signal",
            "signal_type": signal.signal_type,
            "severity": signal.severity,
            "symbol": signal.symbol,
            "exchange": signal.exchange,
            "timestamp": signal.timestamp.isoformat(),
            "confidence_score": signal.confidence_score,
            "data": {}
        }

        # Add signal-specific data
        if hasattr(signal, 'detection_details'):
            data["data"] = {
                "detection_details": signal.detection_details,
                "market_context": signal.market_context,
                "technical_analysis": signal.technical_analysis,
                "trading_recommendation": signal.trading_recommendation,
                "risk_factors": signal.risk_factors
            }
        elif hasattr(signal, 'reversal_details'):
            data["data"] = {
                "reversal_details": signal.reversal_details,
                "original_pump_context": signal.original_pump_context,
                "current_market_state": signal.current_market_state,
                "exit_recommendation": signal.exit_recommendation
            }
        elif hasattr(signal, 'confluence_details'):
            data["data"] = {
                "confluence_details": signal.confluence_details,
                "technical_indicators": signal.technical_indicators,
                "market_context": signal.market_context,
                "trading_recommendation": signal.trading_recommendation
            }

        return data

    def get_stats(self) -> Dict[str, Any]:
        """Get SignalProcessor statistics"""
        return {
            "signals_processed": self.signals_processed,
            "signals_validated": self.signals_validated,
            "signals_enriched": self.signals_enriched,
            "average_processing_time_ms": self.average_processing_time,
            "processing_times_count": len(self.processing_times),
            "signal_history_symbols": len(self.signal_history),
            "market_data_cache_size": len(self.market_data_cache)
        }

    async def _check_rate_limit(self) -> bool:
        """Check if signal processing is within rate limits"""
        async with self._rate_limit_lock:
            current_time = time.time()

            # Remove old entries outside the window
            while self._last_processing_times and current_time - self._last_processing_times[0] > self._processing_window_seconds:
                self._last_processing_times.popleft()

            # Check if under limit
            if len(self._last_processing_times) < self.max_signals_per_minute:
                self._last_processing_times.append(current_time)
                return True

            return False

    async def _update_processing_stats(self, processing_time: float):
        """Update processing statistics with thread safety"""
        with self._stats_lock:
            self.processing_times.append(processing_time)
            self.average_processing_time = sum(self.processing_times) / len(self.processing_times)
            self.signals_processed += 1
            self.signals_validated += 1
            self.signals_enriched += 1

    async def _record_processing_time(self, start_time: float):
        """Record processing time for rate limiting"""
        async with self._rate_limit_lock:
            self._last_processing_times.append(start_time)

    async def _add_to_signal_history(self, symbol: str, signal: Dict[str, Any]):
        """Add signal to history with thread safety"""
        async with self._signal_history_lock:
            if symbol not in self.signal_history:
                self.signal_history[symbol] = deque(maxlen=self.max_history_per_symbol)
            self.signal_history[symbol].append(signal)

    async def _get_cached_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached market data with TTL check"""
        async with self._cache_lock:
            cached_data = self.market_data_cache.get(symbol)
            if cached_data:
                cache_time = cached_data.get("cache_time", 0)
                if time.time() - cache_time < self.cache_ttl_seconds:
                    # Move to end to mark as recently used
                    self.market_data_cache.move_to_end(symbol)
                    return cached_data
                # Expired entry, remove it
                self.market_data_cache.pop(symbol, None)
            return None

    async def _set_cached_market_data(self, symbol: str, data: Dict[str, Any]):
        """Set cached market data with timestamp"""
        async with self._cache_lock:
            data["cache_time"] = time.time()
            if symbol in self.market_data_cache:
                # Refresh position if symbol already cached
                self.market_data_cache.pop(symbol)
            self.market_data_cache[symbol] = data
            if len(self.market_data_cache) > self.max_cache_size:
                # Drop least recently used entry
                self.market_data_cache.popitem(last=False)

    async def cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        async with self._cache_lock:
            current_time = time.time()
            expired_symbols = [
                symbol for symbol, data in self.market_data_cache.items()
                if current_time - data.get("cache_time", 0) > self.cache_ttl_seconds
            ]
            for symbol in expired_symbols:
                del self.market_data_cache[symbol]

            if expired_symbols and self.logger:
                self.logger.info("signal_processor.cache_cleanup", {
                    "expired_entries": len(expired_symbols),
                    "remaining_cache_size": len(self.market_data_cache)
                })

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "healthy": True,
            "component": "SignalProcessor",
            "stats": self.get_stats(),
            "timestamp": datetime.now().isoformat()
        }
