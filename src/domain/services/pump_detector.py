"""
Flash Pump Detector - Pure Business Logic
=========================================
Core pump detection logic without external dependencies.
Easy to test and reason about.
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
from collections import deque
import statistics

from ..models.market_data import MarketData, PriceHistory
from ..models.signals import FlashPumpSignal, ReversalSignal, SignalStrength


class PumpDetectionConfig:
    """Configuration for pump detection"""
    
    def __init__(
        self,
        min_pump_magnitude: Decimal = Decimal('7.0'),
        volume_surge_multiplier: Decimal = Decimal('3.5'),
        price_velocity_threshold: Decimal = Decimal('0.5'),
        min_volume_24h_usdt: Decimal = Decimal('100000'),
        peak_confirmation_window_seconds: int = 30,
        min_confidence_threshold: Decimal = Decimal('60'),
        baseline_window_minutes: int = 10,
        velocity_window_seconds: int = 30
    ):
        self.min_pump_magnitude = min_pump_magnitude
        self.volume_surge_multiplier = volume_surge_multiplier
        self.price_velocity_threshold = price_velocity_threshold
        self.min_volume_24h_usdt = min_volume_24h_usdt
        self.peak_confirmation_window_seconds = peak_confirmation_window_seconds
        self.min_confidence_threshold = min_confidence_threshold
        self.baseline_window_minutes = baseline_window_minutes
        self.velocity_window_seconds = velocity_window_seconds


class VolumeAnalyzer:
    """Analyzes volume patterns for pump detection"""
    
    def __init__(self, max_history: int = 1000):
        self.volume_history: deque = deque(maxlen=max_history)
        self.timestamp_history: deque = deque(maxlen=max_history)
    
    def add_volume_point(self, volume: Decimal, timestamp: datetime) -> None:
        """Add volume data point"""
        self.volume_history.append(volume)
        self.timestamp_history.append(timestamp)
    
    def get_baseline_volume(self, minutes: int, current_time: datetime) -> Optional[Decimal]:
        """Calculate baseline volume over specified minutes"""
        if len(self.volume_history) < 10:
            return None
        
        cutoff_time = current_time - timedelta(minutes=minutes)
        baseline_volumes = []
        
        for i, timestamp in enumerate(self.timestamp_history):
            if timestamp >= cutoff_time:
                baseline_volumes.append(self.volume_history[i])
        
        if len(baseline_volumes) < 5:
            return None
        
        return Decimal(str(statistics.median(baseline_volumes)))
    
    def calculate_volume_surge_ratio(self, current_volume: Decimal, baseline_volume: Optional[Decimal]) -> Decimal:
        """Calculate volume surge ratio"""
        if baseline_volume is None or baseline_volume == 0:
            return Decimal('1.0')
        
        return current_volume / baseline_volume
    
    def get_volume_trend(self, minutes: int, current_time: datetime) -> str:
        """Get volume trend (increasing, decreasing, stable)"""
        if len(self.volume_history) < 20:
            return "unknown"
        
        cutoff_time = current_time - timedelta(minutes=minutes)
        recent_volumes = []
        
        for i, timestamp in enumerate(self.timestamp_history):
            if timestamp >= cutoff_time:
                recent_volumes.append(float(self.volume_history[i]))
        
        if len(recent_volumes) < 10:
            return "unknown"
        
        # Simple trend analysis
        first_half = recent_volumes[:len(recent_volumes)//2]
        second_half = recent_volumes[len(recent_volumes)//2:]
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        change_pct = ((second_avg - first_avg) / first_avg) * 100
        
        if change_pct > 20:
            return "increasing"
        elif change_pct < -20:
            return "decreasing"
        else:
            return "stable"


class PriceAnalyzer:
    """Analyzes price patterns for pump detection"""
    
    def __init__(self, max_history: int = 1000):
        self.price_history: deque = deque(maxlen=max_history)
        self.timestamp_history: deque = deque(maxlen=max_history)
    
    def add_price_point(self, price: Decimal, timestamp: datetime) -> None:
        """Add price data point"""
        self.price_history.append(price)
        self.timestamp_history.append(timestamp)
    
    def get_baseline_price(self, minutes: int, current_time: datetime) -> Optional[Decimal]:
        """Calculate baseline price over specified minutes"""
        if len(self.price_history) < 10:
            return None
        
        cutoff_time = current_time - timedelta(minutes=minutes)
        baseline_prices = []
        
        for i, timestamp in enumerate(self.timestamp_history):
            if timestamp >= cutoff_time:
                baseline_prices.append(self.price_history[i])
        
        if len(baseline_prices) < 5:
            return None
        
        return Decimal(str(statistics.median(baseline_prices)))
    
    def calculate_price_velocity(self, seconds: int, current_time: datetime) -> Optional[Decimal]:
        """Calculate price velocity (change per second)"""
        if len(self.price_history) < 2:
            return None
        
        cutoff_time = current_time - timedelta(seconds=seconds)
        
        # Find price from 'seconds' ago
        for i in reversed(range(len(self.timestamp_history))):
            if self.timestamp_history[i] <= cutoff_time:
                time_diff = (current_time - self.timestamp_history[i]).total_seconds()
                if time_diff > 0:
                    price_diff = self.price_history[-1] - self.price_history[i]
                    return price_diff / Decimal(str(time_diff))
                break
        
        return None
    
    def calculate_pump_magnitude(self, current_price: Decimal, baseline_price: Optional[Decimal]) -> Decimal:
        """Calculate pump magnitude percentage"""
        if baseline_price is None or baseline_price == 0:
            return Decimal('0')
        
        return ((current_price - baseline_price) / baseline_price) * 100
    
    def detect_price_breakout(self, current_price: Decimal, resistance_levels: List[Decimal]) -> bool:
        """Detect if price broke through resistance levels"""
        if not resistance_levels:
            return False
        
        # Check if current price is above any resistance level
        for resistance in resistance_levels:
            if current_price > resistance * Decimal('1.01'):  # 1% buffer
                return True
        
        return False


class ConfidenceCalculator:
    """Calculates confidence scores for pump signals"""
    
    def __init__(self):
        self.weights = {
            'magnitude': Decimal('0.30'),
            'volume_surge': Decimal('0.30'),
            'velocity': Decimal('0.25'),
            'market_conditions': Decimal('0.15')
        }
    
    def calculate_confidence(
        self,
        pump_magnitude: Decimal,
        volume_surge_ratio: Decimal,
        price_velocity: Optional[Decimal],
        market_spread_pct: Optional[Decimal] = None,
        market_liquidity_usdt: Optional[Decimal] = None,
        volume_24h_usdt: Optional[Decimal] = None
    ) -> Decimal:
        """Calculate overall confidence score (0-100)"""
        
        # Magnitude score (0-100)
        magnitude_score = min(Decimal('100'), (pump_magnitude / Decimal('20')) * 100)
        
        # Volume surge score (0-100)
        volume_score = min(Decimal('100'), ((volume_surge_ratio - 1) / Decimal('4')) * 100)
        
        # Velocity score (0-100)
        velocity_score = Decimal('50')  # Default neutral
        if price_velocity is not None:
            velocity_score = min(Decimal('100'), abs(price_velocity) * 100)
        
        # Market conditions score (0-100)
        market_score = Decimal('70')  # Default good
        
        if market_spread_pct is not None:
            if market_spread_pct > 3:
                market_score -= Decimal('30')
            elif market_spread_pct > 1:
                market_score -= Decimal('15')
        
        if market_liquidity_usdt is not None:
            if market_liquidity_usdt < 500:
                market_score -= Decimal('20')
            elif market_liquidity_usdt < 1000:
                market_score -= Decimal('10')
        
        if volume_24h_usdt is not None:
            if volume_24h_usdt < 50000:
                market_score -= Decimal('25')
            elif volume_24h_usdt < 100000:
                market_score -= Decimal('10')
        
        # Weighted average
        confidence = (
            magnitude_score * self.weights['magnitude'] +
            volume_score * self.weights['volume_surge'] +
            velocity_score * self.weights['velocity'] +
            market_score * self.weights['market_conditions']
        )
        
        return max(Decimal('0'), min(Decimal('100'), confidence))


class PumpDetectionService:
    """
    Pure business logic for flash pump detection.
    No external dependencies - easy to test and reason about.
    """
    
    def __init__(self, config: PumpDetectionConfig):
        self.config = config
        self.volume_analyzer = VolumeAnalyzer()
        self.price_analyzer = PriceAnalyzer()
        self.confidence_calculator = ConfidenceCalculator()
        
        # State tracking
        self.active_pump: Optional[Dict[str, Any]] = None
        self.last_signal_time: Optional[datetime] = None
        
    def process_market_data(self, data: MarketData) -> Optional[FlashPumpSignal]:
        """
        Process market data and return pump signal if detected.
        Pure function - no side effects except internal state.
        """
        # Add data to analyzers
        self.volume_analyzer.add_volume_point(data.volume, data.timestamp)
        self.price_analyzer.add_price_point(data.price, data.timestamp)
        
        # Check for new pump if none active
        if self.active_pump is None:
            pump_detected = self._detect_new_pump(data)
            if pump_detected:
                self.active_pump = pump_detected
                return None  # Wait for confirmation
        
        # Check for peak confirmation if pump is active
        if self.active_pump is not None:
            signal = self._check_peak_confirmation(data)
            if signal:
                self.active_pump = None  # Reset after signal
                self.last_signal_time = data.timestamp
                return signal
            
            # Update peak if new high
            if data.price > self.active_pump['peak_price']:
                self.active_pump['peak_price'] = data.price
                self.active_pump['peak_time'] = data.timestamp
        
        return None
    
    def _detect_new_pump(self, data: MarketData) -> Optional[Dict[str, Any]]:
        """Detect new pump conditions"""
        
        # Get baseline metrics
        baseline_price = self.price_analyzer.get_baseline_price(
            self.config.baseline_window_minutes, 
            data.timestamp
        )
        baseline_volume = self.volume_analyzer.get_baseline_volume(
            self.config.baseline_window_minutes,
            data.timestamp
        )
        
        if baseline_price is None or baseline_volume is None:
            return None
        
        # Calculate pump metrics
        pump_magnitude = self.price_analyzer.calculate_pump_magnitude(data.price, baseline_price)
        volume_surge_ratio = self.volume_analyzer.calculate_volume_surge_ratio(data.volume, baseline_volume)
        price_velocity = self.price_analyzer.calculate_price_velocity(
            self.config.velocity_window_seconds,
            data.timestamp
        )
        
        # Check conditions
        conditions_met = (
            pump_magnitude >= self.config.min_pump_magnitude and
            volume_surge_ratio >= self.config.volume_surge_multiplier and
            (price_velocity is None or price_velocity >= self.config.price_velocity_threshold) and
            (data.volume_24h_usdt is None or data.volume_24h_usdt >= self.config.min_volume_24h_usdt)
        )
        
        if conditions_met:
            return {
                'symbol': data.symbol,
                'exchange': data.exchange,
                'detection_time': data.timestamp,
                'baseline_price': baseline_price,
                'peak_price': data.price,
                'peak_time': data.timestamp,
                'pump_magnitude': pump_magnitude,
                'volume_surge_ratio': volume_surge_ratio,
                'price_velocity': price_velocity or Decimal('0'),
                'baseline_volume': baseline_volume
            }
        
        return None
    
    def _check_peak_confirmation(self, data: MarketData) -> Optional[FlashPumpSignal]:
        """Check if pump peak is confirmed"""
        if self.active_pump is None:
            return None
        
        # Check if enough time has passed since peak
        time_since_peak = (data.timestamp - self.active_pump['peak_time']).total_seconds()
        if time_since_peak < self.config.peak_confirmation_window_seconds:
            return None
        
        # Calculate confidence
        confidence = self.confidence_calculator.calculate_confidence(
            pump_magnitude=self.active_pump['pump_magnitude'],
            volume_surge_ratio=self.active_pump['volume_surge_ratio'],
            price_velocity=self.active_pump['price_velocity'],
            volume_24h_usdt=data.volume_24h_usdt
        )
        
        # Check confidence threshold
        if confidence < self.config.min_confidence_threshold:
            return None
        
        # Create signal
        pump_age = (data.timestamp - self.active_pump['detection_time']).total_seconds()
        
        return FlashPumpSignal(
            symbol=data.symbol,
            exchange=data.exchange,
            detection_time=self.active_pump['detection_time'],
            peak_price=self.active_pump['peak_price'],
            baseline_price=self.active_pump['baseline_price'],
            pump_magnitude=self.active_pump['pump_magnitude'],
            volume_surge_ratio=self.active_pump['volume_surge_ratio'],
            price_velocity=self.active_pump['price_velocity'],
            confidence_score=confidence,
            pump_age_seconds=Decimal(str(pump_age)),
            baseline_volume=self.active_pump['baseline_volume'],
            volume_24h_usdt=data.volume_24h_usdt
        )
    
    def detect_reversal(
        self,
        current_data: MarketData,
        original_signal: FlashPumpSignal,
        min_retracement_pct: Decimal = Decimal('2.0')
    ) -> Optional[ReversalSignal]:
        """
        Detect reversal from pump peak.
        Pure function - no state changes.
        """
        
        # Calculate retracement
        retracement_pct = ((original_signal.peak_price - current_data.price) / original_signal.peak_price) * 100
        
        if retracement_pct < min_retracement_pct:
            return None
        
        # Check volume decline
        current_volume_surge = self.volume_analyzer.calculate_volume_surge_ratio(
            current_data.volume,
            original_signal.baseline_volume
        )
        
        volume_decline_ratio = max(Decimal('0'), 
            (original_signal.volume_surge_ratio - current_volume_surge) / original_signal.volume_surge_ratio
        )
        
        # Check momentum shift
        current_velocity = self.price_analyzer.calculate_price_velocity(
            self.config.velocity_window_seconds,
            current_data.timestamp
        )
        momentum_shift = current_velocity is not None and current_velocity < 0
        
        return ReversalSignal(
            symbol=current_data.symbol,
            exchange=current_data.exchange,
            detection_time=current_data.timestamp,
            pump_peak_price=original_signal.peak_price,
            reversal_price=current_data.price,
            retracement_pct=retracement_pct,
            volume_decline_ratio=volume_decline_ratio,
            momentum_shift_confirmed=momentum_shift,
            original_pump_signal=original_signal
        )
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current detector state for debugging"""
        return {
            'has_active_pump': self.active_pump is not None,
            'active_pump_details': self.active_pump,
            'last_signal_time': self.last_signal_time,
            'price_history_length': len(self.price_analyzer.price_history),
            'volume_history_length': len(self.volume_analyzer.volume_history)
        }
    
    def reset_state(self) -> None:
        """Reset detector state (useful for testing)"""
        self.active_pump = None
        self.last_signal_time = None
        self.volume_analyzer = VolumeAnalyzer()
        self.price_analyzer = PriceAnalyzer()