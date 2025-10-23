"""
Signal Processor - Production Version with AppSettings
======================================================
Signal processing using Clean Architecture with AppSettings configuration.
Legacy class - consider using DetectPumpSignalsUseCase for new implementations.
"""

from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import threading
import asyncio
from ..infrastructure.config.settings import AppSettings
from ..infrastructure.config.symbol_config import SymbolConfigurationManager
from ..core.logger import StructuredLogger
from ..domain.models.signals import FlashPumpSignal

class SignalProcessor:
    """
    Legacy signal processor implementing ALU_USDT features.
    NOTE: For new implementations, use DetectPumpSignalsUseCase instead.
    This class is kept for backward compatibility.
    """
    
    def __init__(self, settings: AppSettings, symbol_config_manager: SymbolConfigurationManager, 
                 logger: StructuredLogger, symbol: str = "BTC_USDT"):
        """
        Initialize with AppSettings instead of dict config.
        
        Args:
            settings: Application settings (Pydantic)
            symbol_config_manager: Symbol configuration manager
            logger: Structured logger
            symbol: Trading symbol for configuration
        """
        self.settings = settings
        self.symbol_config_manager = symbol_config_manager
        self.logger = logger
        self.symbol = symbol
        
        # Get symbol-specific configuration
        symbol_config = symbol_config_manager.get_symbol_config(symbol)
        
        # Entry thresholds from symbol config
        self.min_confidence_threshold = float(symbol_config.entry_conditions.min_confidence_threshold)
        self.min_pump_age = symbol_config.entry_conditions.min_pump_age_seconds
        self.max_entry_delay = symbol_config.entry_conditions.max_entry_delay_seconds
        self.max_spread_pct = float(symbol_config.entry_conditions.max_spread_pct)
        self.min_liquidity_usdt = float(symbol_config.entry_conditions.min_liquidity_usdt)
        self.rsi_max = float(symbol_config.entry_conditions.rsi_max)
        
        # Safety limits from symbol config
        self.max_daily_signals = symbol_config.safety_limits.max_daily_trades
        self.min_cooldown_minutes = symbol_config.safety_limits.min_cooldown_minutes
        self.max_consecutive_losses = symbol_config.safety_limits.max_consecutive_losses
        self.max_drawdown_pct = float(symbol_config.safety_limits.daily_loss_limit_pct)
        
        # Emergency conditions from symbol config risk management
        self.emergency_max_spread = float(symbol_config.risk_management.spread_blowout_pct)
        self.emergency_min_liquidity = float(symbol_config.risk_management.emergency_min_liquidity)
        self.emergency_max_rsi = 85.0  # Default as not in settings yet
        self.emergency_min_volume_24h = float(symbol_config.flash_pump_detection.min_volume_24h_usdt)
        
        # Advanced scoring weights - using defaults as not in settings yet
        self.weights = {
            'magnitude': 0.25,
            'volume_surge': 0.25,
            'reversal_clarity': 0.25,
            'market_conditions': 0.25
        }
        
        self.scalers = {
            'magnitude': {'min': 7, 'max': 50},
            'volume_surge': {'min': 3, 'max': 20},
            'confidence': {'min': 50, 'max': 100},
            'spread': {'min': 0, 'max': 5},
            'liquidity': {'min': 100, 'max': 2000}
        }
        
        # ✅ THREAD SAFETY: Add locks for shared state
        self._state_lock = threading.RLock()
        self._cache_lock = threading.RLock()

        # Safety tracking with thread-safe access
        self.daily_signal_count = 0
        self.last_signal_time = None
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.max_daily_pnl = 0.0
        self.trading_active = True

        # Cooldown tracking
        self.cooldown_until = None

        # ✅ PERFORMANCE: Pre-compute expensive conversions and scalers
        self._precomputed_scalers = self._build_scalers()
        self._current_time = None  # Cache current time to avoid repeated calls
        self._time_cache_expiry = 0
        
        # Log configuration loaded
        self.logger.info("signal_processor.initialized", {
            "symbol": symbol,
            "configuration_source": "AppSettings_with_SymbolConfig",
            "min_confidence_threshold": self.min_confidence_threshold,
            "emergency_max_spread": self.emergency_max_spread,
            "max_daily_signals": self.max_daily_signals
        })

    def _build_scalers(self) -> Dict[str, Tuple[float, float]]:
        """✅ PERFORMANCE: Pre-compute scaler factors to avoid repeated calculations"""
        return {
            'magnitude': (self.scalers['magnitude']['min'],
                         self.scalers['magnitude']['max'] - self.scalers['magnitude']['min']),
            'volume_surge': (self.scalers['volume_surge']['min'],
                           self.scalers['volume_surge']['max'] - self.scalers['volume_surge']['min']),
            'confidence': (self.scalers['confidence']['min'],
                          self.scalers['confidence']['max'] - self.scalers['confidence']['min']),
            'spread': (self.scalers['spread']['min'],
                      self.scalers['spread']['max'] - self.scalers['spread']['min']),
            'liquidity': (self.scalers['liquidity']['min'],
                         self.scalers['liquidity']['max'] - self.scalers['liquidity']['min'])
        }

    def _get_current_time(self) -> datetime:
        """✅ PERFORMANCE: Cache current time to avoid repeated datetime.utcnow() calls"""
        current_timestamp = datetime.utcnow().timestamp()
        if current_timestamp - self._time_cache_expiry > 0.1:  # Cache for 100ms
            self._current_time = datetime.utcnow()
            self._time_cache_expiry = current_timestamp
        return self._current_time

    def process_signal(self, signal: FlashPumpSignal) -> Dict:
        """
        Comprehensive signal processing with all safety checks and emergency conditions.
        """
        # First check emergency conditions
        emergency_check = self._check_emergency_conditions(signal)
        if emergency_check['emergency']:
            return self._create_emergency_response(signal, emergency_check)
        
        # Check safety limits
        safety_check = self._check_safety_limits(signal)
        if not safety_check['safe']:
            return self._create_safety_response(signal, safety_check)
        
        # Check cooldown
        if self._is_in_cooldown():
            return self._create_cooldown_response(signal)
        
        # Calculate advanced scores
        entry_score = self._calculate_advanced_entry_score(signal)
        reversal_quality = self._calculate_reversal_quality_score(signal)
        market_health = self._assess_market_health(signal)
        
        # Comprehensive entry validation
        entry_ready, rejection_reasons = self._comprehensive_entry_check(signal, entry_score)
        
        # Risk assessment
        risk_level = self._calculate_risk_level(signal, entry_score)
        position_recommendation = self._recommend_position_size(signal, entry_score)
        
        # Update tracking
        if entry_ready:
            self._update_signal_tracking(signal)
        
        # ✅ PERFORMANCE: Pre-compute values to avoid repeated calculations
        pump_age_valid = self.min_pump_age <= signal.pump_age_seconds <= self.max_entry_delay
        confidence_met = signal.confidence_score >= self.min_confidence_threshold
        spread_ok = signal.market_spread_pct <= self.max_spread_pct
        liquidity_ok = signal.market_liquidity_usdt >= self.min_liquidity_usdt
        rsi_ok = signal.market_rsi is None or signal.market_rsi <= self.rsi_max
        entry_score_ok = entry_score >= 60.0
        volume_ok = signal.volume_24h_usdt >= self.emergency_min_volume_24h

        # ✅ PERFORMANCE: Create response dict with minimal allocations
        processed_data = {
            # Core signal data
            'symbol': signal.symbol,
            'exchange': signal.exchange,
            'detection_time': signal.detection_time,
            'peak_price': signal.peak_price,
            'pump_magnitude': signal.pump_magnitude,
            'confidence_score': signal.confidence_score,
            'volume_surge_ratio': signal.volume_surge_ratio,

            # Scoring results
            'entry_score': entry_score,
            'reversal_quality_score': reversal_quality,
            'market_health_score': market_health,

            # Decision
            'entry_ready': entry_ready,
            'rejection_reasons': rejection_reasons,

            # Market data
            'pump_age_seconds': signal.pump_age_seconds,
            'market_spread_pct': signal.market_spread_pct,
            'market_liquidity_usdt': signal.market_liquidity_usdt,
            'market_rsi': signal.market_rsi,
            'volume_24h_usdt': signal.volume_24h_usdt,

            # Risk assessment
            'risk_level': risk_level,
            'recommended_position_size_pct': position_recommendation,

            # Safety status (cached where possible)
            'safety_status': safety_check,
            'daily_signal_count': self.daily_signal_count,
            'consecutive_losses': self.consecutive_losses,
            'cooldown_active': self._is_in_cooldown(),

            # ✅ PERFORMANCE: Pre-computed conditions (no repeated calculations)
            'entry_conditions': {
                'min_confidence_threshold': self.min_confidence_threshold,
                'confidence_threshold_met': confidence_met,
                'pump_age_valid': pump_age_valid,
                'spread_acceptable': spread_ok,
                'liquidity_sufficient': liquidity_ok,
                'rsi_not_overbought': rsi_ok,
                'entry_score_threshold': entry_score_ok,
                'volume_24h_sufficient': volume_ok
            }
        }

        # ✅ PERFORMANCE: Calculate drawdown only when needed
        if safety_check['safe'] and entry_ready:
            processed_data['current_drawdown_pct'] = self._calculate_current_drawdown()
        
        self.logger.info("signal_processor.processed", {
            "symbol": signal.symbol,
            "entry_score": round(entry_score, 1),
            "entry_ready": entry_ready,
            "risk_level": risk_level,
            "safety_safe": safety_check['safe'],
            "emergency": emergency_check['emergency']
        })

        return processed_data

    def _check_emergency_conditions(self, signal: FlashPumpSignal) -> Dict:
        """Check for emergency conditions that should prevent any trading."""
        emergency_reasons = []
        
        # 1. Extreme spread
        if signal.market_spread_pct > self.emergency_max_spread:
            emergency_reasons.append(f"Emergency spread: {signal.market_spread_pct:.2f}% > {self.emergency_max_spread}%")
        
        # 2. Critical liquidity
        if signal.market_liquidity_usdt < self.emergency_min_liquidity:
            emergency_reasons.append(f"Emergency liquidity: ${signal.market_liquidity_usdt:.0f} < ${self.emergency_min_liquidity}")
        
        # 3. Extreme RSI (overbought)
        if signal.market_rsi is not None and signal.market_rsi > self.emergency_max_rsi:
            emergency_reasons.append(f"Emergency RSI: {signal.market_rsi:.1f} > {self.emergency_max_rsi}")
        
        # 4. Insufficient 24h volume
        if signal.volume_24h_usdt < self.emergency_min_volume_24h:
            emergency_reasons.append(f"Emergency volume 24h: ${signal.volume_24h_usdt:.0f} < ${self.emergency_min_volume_24h}")
        
        # 5. Extreme pump magnitude (potential manipulation)
        if signal.pump_magnitude > 100:  # 100%+ pump is suspicious
            emergency_reasons.append(f"Extreme pump magnitude: {signal.pump_magnitude:.1f}%")
        
        return {
            'emergency': len(emergency_reasons) > 0,
            'reasons': emergency_reasons
        }

    def _check_safety_limits(self, signal: FlashPumpSignal) -> Dict:
        """Check safety limits for trading."""
        safety_issues = []
        
        # 1. Daily signal limit
        if self.daily_signal_count >= self.max_daily_signals:
            safety_issues.append(f"Daily signal limit reached: {self.daily_signal_count} >= {self.max_daily_signals}")
        
        # 2. Consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            safety_issues.append(f"Max consecutive losses: {self.consecutive_losses} >= {self.max_consecutive_losses}")
        
        # 3. Drawdown limit
        current_drawdown = self._calculate_current_drawdown()
        if current_drawdown > self.max_drawdown_pct:
            safety_issues.append(f"Max drawdown exceeded: {current_drawdown:.1f}% > {self.max_drawdown_pct}%")
        
        # 4. Trading active flag
        if not self.trading_active:
            safety_issues.append("Trading manually disabled")
        
        return {
            'safe': len(safety_issues) == 0,
            'issues': safety_issues
        }

    def _is_in_cooldown(self) -> bool:
        """✅ PERFORMANCE: Check cooldown with cached time"""
        if self.cooldown_until is None:
            return False

        return self._get_current_time() < self.cooldown_until

    def _calculate_advanced_entry_score(self, signal: FlashPumpSignal) -> float:
        """Calculate advanced entry score with all components."""
        
        # Component 1: Spike strength - using config values only
        magnitude_normalized = self._normalize(signal.pump_magnitude, self.scalers['magnitude'])
        spike_strength = magnitude_normalized * self.weights['magnitude'] * 100
        
        # Component 2: Volume confirmation - using config values only
        volume_normalized = self._normalize(signal.volume_surge_ratio, self.scalers['volume_surge'])
        volume_confirmation = volume_normalized * self.weights['volume_surge'] * 100
        
        # Component 3: Reversal clarity - using config values only
        reversal_clarity = self._calculate_reversal_quality_score(signal) * self.weights['reversal_clarity']
        
        # Component 4: Market conditions - using config values only
        market_conditions = self._assess_market_health(signal) * self.weights['market_conditions']
        
        total_score = spike_strength + volume_confirmation + reversal_clarity + market_conditions
        
        # Apply safety discount if needed
        if self.consecutive_losses > 0:
            safety_discount = min(0.2, self.consecutive_losses * 0.05)  # Up to 20% discount
            total_score *= (1 - safety_discount)
        
        return total_score

    def _calculate_reversal_quality_score(self, signal: FlashPumpSignal) -> float:
        """Calculate reversal quality score with enhanced factors."""
        score = 0.0
        
        # Base score from confidence - using config values only
        confidence_normalized = self._normalize(signal.confidence_score, self.scalers['confidence'])
        score += confidence_normalized * 50  # Up to 50 points
        
        # Timing bonus - optimal pump age
        if self.min_pump_age <= signal.pump_age_seconds <= 30:  # Sweet spot: 5-30 seconds
            timing_bonus = 25
        elif signal.pump_age_seconds <= self.max_entry_delay:
            # Linear decay after 30 seconds
            timing_factor = max(0, (self.max_entry_delay - signal.pump_age_seconds) / (self.max_entry_delay - 30))
            timing_bonus = timing_factor * 25
        else:
            timing_bonus = 0
        
        score += timing_bonus
        
        # Velocity bonus - strong price movement
        if signal.price_velocity > 1.0:  # Very strong velocity
            velocity_bonus = 25
        elif signal.price_velocity > 0.5:  # Good velocity
            velocity_bonus = 15
        else:
            velocity_bonus = 5
        
        score += velocity_bonus
        
        # Volume 24h bonus - sufficient trading volume
        if signal.volume_24h_usdt >= self.emergency_min_volume_24h * 2:  # 2x minimum
            volume_bonus = 10
        elif signal.volume_24h_usdt >= self.emergency_min_volume_24h:  # Minimum met
            volume_bonus = 5
        else:
            volume_bonus = 0
        
        score += volume_bonus
        
        return min(score, 100.0)

    def _assess_market_health(self, signal: FlashPumpSignal) -> float:
        """Assess overall market health with enhanced factors."""
        health_score = 0.0
        
        # Spread health (35% of market health)
        if signal.market_spread_pct <= 1.0:  # Excellent spread
            spread_score = 35
        elif signal.market_spread_pct <= self.max_spread_pct:  # Acceptable spread
            spread_factor = (self.max_spread_pct - signal.market_spread_pct) / self.max_spread_pct
            spread_score = spread_factor * 35
        else:  # Poor spread
            spread_score = 0
        
        health_score += spread_score
        
        # Liquidity health (35% of market health)
        liquidity_factor = min(signal.market_liquidity_usdt / self.min_liquidity_usdt, 3.0)  # Cap at 3x minimum
        liquidity_score = (liquidity_factor / 3.0) * 35
        health_score += liquidity_score
        
        # RSI health (20% of market health)
        if signal.market_rsi is None:
            rsi_score = 15  # Neutral if no RSI data
        elif signal.market_rsi <= 50:  # Not overbought
            rsi_score = 20
        elif signal.market_rsi <= self.rsi_max:  # Acceptable
            rsi_factor = (self.rsi_max - signal.market_rsi) / (self.rsi_max - 50)
            rsi_score = rsi_factor * 20
        else:  # Overbought
            rsi_score = 0
        
        health_score += rsi_score
        
        # Volume 24h health (10% of market health)
        volume_factor = min(signal.volume_24h_usdt / self.emergency_min_volume_24h, 5.0)  # Cap at 5x minimum
        volume_score = (volume_factor / 5.0) * 10
        health_score += volume_score
        
        return min(health_score, 100.0)

    def _comprehensive_entry_check(self, signal: FlashPumpSignal, entry_score: float) -> Tuple[bool, List[str]]:
        """Comprehensive entry readiness check with all validations."""
        rejection_reasons = []
        
        # 1. Confidence threshold
        if signal.confidence_score < self.min_confidence_threshold:
            rejection_reasons.append(f"Low confidence: {signal.confidence_score:.1f} < {self.min_confidence_threshold}")
        
        # 2. Entry score threshold
        if entry_score < 60.0:
            rejection_reasons.append(f"Low entry score: {entry_score:.1f} < 60.0")
        
        # 3. Pump age validation
        if signal.pump_age_seconds < self.min_pump_age:
            rejection_reasons.append(f"Pump too young: {signal.pump_age_seconds:.1f}s < {self.min_pump_age}s")
        elif signal.pump_age_seconds > self.max_entry_delay:
            rejection_reasons.append(f"Pump too old: {signal.pump_age_seconds:.1f}s > {self.max_entry_delay}s")
        
        # 4. Spread validation
        if signal.market_spread_pct > self.max_spread_pct:
            rejection_reasons.append(f"High spread: {signal.market_spread_pct:.2f}% > {self.max_spread_pct}%")
        
        # 5. Liquidity validation
        if signal.market_liquidity_usdt < self.min_liquidity_usdt:
            rejection_reasons.append(f"Low liquidity: ${signal.market_liquidity_usdt:.0f} < ${self.min_liquidity_usdt}")
        
        # 6. RSI validation
        if signal.market_rsi is not None and signal.market_rsi > self.rsi_max:
            rejection_reasons.append(f"Overbought RSI: {signal.market_rsi:.1f} > {self.rsi_max}")
        
        # 7. Volume 24h validation
        if signal.volume_24h_usdt < self.emergency_min_volume_24h:
            rejection_reasons.append(f"Insufficient 24h volume: ${signal.volume_24h_usdt:.0f} < ${self.emergency_min_volume_24h}")
        
        # 8. Minimum pump magnitude
        if signal.pump_magnitude < 7.0:
            rejection_reasons.append(f"Weak pump: {signal.pump_magnitude:.1f}% < 7.0%")
        
        entry_ready = len(rejection_reasons) == 0
        
        return entry_ready, rejection_reasons

    def _update_signal_tracking(self, signal: FlashPumpSignal):
        """✅ THREAD SAFETY & PERFORMANCE: Update signal tracking with proper synchronization"""
        with self._state_lock:
            self.daily_signal_count += 1
            self.last_signal_time = signal.detection_time

            # ✅ PERFORMANCE: Use cached time
            self.cooldown_until = self._get_current_time() + timedelta(minutes=self.min_cooldown_minutes)

        # ✅ PERFORMANCE: Log outside lock
        self.logger.info("signal_tracking.updated", {
            "symbol": signal.symbol,
            "daily_count": self.daily_signal_count,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None
        })

    def _calculate_current_drawdown(self) -> float:
        """Calculate current drawdown percentage."""
        if self.max_daily_pnl <= 0:
            return 0.0
        
        drawdown = ((self.max_daily_pnl - self.daily_pnl) / self.max_daily_pnl) * 100
        return max(0.0, drawdown)

    def _is_timing_optimal(self, signal: FlashPumpSignal) -> bool:
        """Check if timing is in the optimal window."""
        return self.min_pump_age <= signal.pump_age_seconds <= 30

    def _calculate_risk_level(self, signal: FlashPumpSignal, entry_score: float) -> str:
        """Calculate risk level with enhanced factors."""
        risk_factors = 0
        
        # High spread = risk
        if signal.market_spread_pct > 1.5:
            risk_factors += 1
        
        # Low liquidity = risk
        if signal.market_liquidity_usdt < self.min_liquidity_usdt * 1.5:
            risk_factors += 1
        
        # High RSI = risk
        if signal.market_rsi is not None and signal.market_rsi > 70:
            risk_factors += 1
        
        # Low entry score = risk
        if entry_score < 70:
            risk_factors += 1
        
        # Old pump = risk
        if signal.pump_age_seconds > 60:
            risk_factors += 1
        
        # Low volume 24h = risk
        if signal.volume_24h_usdt < self.emergency_min_volume_24h * 1.5:
            risk_factors += 1
        
        # Consecutive losses = risk
        if self.consecutive_losses > 0:
            risk_factors += self.consecutive_losses
        
        if risk_factors >= 4:
            return "HIGH"
        elif risk_factors >= 2:
            return "MEDIUM"
        else:
            return "LOW"

    def _recommend_position_size(self, signal: FlashPumpSignal, entry_score: float) -> float:
        """Recommend position size with enhanced safety adjustments."""
        base_multiplier = 1.0
        
        # Adjust based on entry score
        if entry_score >= 90:
            base_multiplier = 1.5  # 150% of base
        elif entry_score >= 80:
            base_multiplier = 1.2  # 120% of base
        elif entry_score >= 70:
            base_multiplier = 1.0  # 100% of base
        elif entry_score >= 60:
            base_multiplier = 0.8  # 80% of base
        else:
            base_multiplier = 0.5  # 50% of base
        
        # Adjust based on consecutive losses
        if self.consecutive_losses >= 2:
            base_multiplier *= 0.5  # Cut in half after 2 losses
        elif self.consecutive_losses == 1:
            base_multiplier *= 0.7  # Reduce after 1 loss
        
        # Adjust based on market conditions
        if signal.market_spread_pct > 1.5:
            base_multiplier *= 0.8  # Reduce for high spread
        
        if signal.market_liquidity_usdt < self.min_liquidity_usdt * 1.5:
            base_multiplier *= 0.8  # Reduce for low liquidity
        
        # Adjust based on drawdown
        current_drawdown = self._calculate_current_drawdown()
        if current_drawdown > 10:
            base_multiplier *= 0.7  # Reduce at 10% drawdown
        elif current_drawdown > 5:
            base_multiplier *= 0.85  # Slight reduction at 5% drawdown
        
        # Adjust based on confidence
        if signal.confidence_score >= 90:
            base_multiplier *= 1.1
        elif signal.confidence_score < 70:
            base_multiplier *= 0.9
        
        return max(0.1, min(2.0, base_multiplier))  # Cap between 10% and 200%

    def _create_emergency_response(self, signal: FlashPumpSignal, emergency_check: Dict) -> Dict:
        """Create emergency response for critical conditions."""
        response = {
            'symbol': signal.symbol,
            'exchange': signal.exchange,
            'detection_time': signal.detection_time,
            'emergency': True,
            'entry_ready': False,
            'rejection_reasons': emergency_check['reasons'],
            'emergency_type': 'CRITICAL',
            'action_required': 'STOP_TRADING',
            'market_conditions': {
                'spread_pct': signal.market_spread_pct,
                'liquidity_usdt': signal.market_liquidity_usdt,
                'rsi': signal.market_rsi,
                'volume_24h_usdt': signal.volume_24h_usdt
            }
        }
        
        self.logger.info("emergency_condition.detected", {
            "symbol": signal.symbol,
            "reasons": emergency_check['reasons']
        })
        
        return response

    def _create_safety_response(self, signal: FlashPumpSignal, safety_check: Dict) -> Dict:
        """Create safety response for limit violations."""
        response = {
            'symbol': signal.symbol,
            'exchange': signal.exchange,
            'detection_time': signal.detection_time,
            'emergency': False,
            'entry_ready': False,
            'rejection_reasons': safety_check['issues'],
            'safety_violation': True,
            'action_required': 'WAIT',
            'safety_status': {
                'daily_signal_count': self.daily_signal_count,
                'consecutive_losses': self.consecutive_losses,
                'current_drawdown_pct': self._calculate_current_drawdown(),
                'cooldown_active': self._is_in_cooldown()
            }
        }
        
        self.logger.warning("safety_limit.violated", {
            "symbol": signal.symbol,
            "issues": safety_check['issues']
        })
        
        return response

    def _create_cooldown_response(self, signal: FlashPumpSignal) -> Dict:
        """Create cooldown response."""
        remaining_minutes = 0
        if self.cooldown_until:
            remaining_seconds = (self.cooldown_until - datetime.utcnow()).total_seconds()
            remaining_minutes = max(0, remaining_seconds / 60)
        
        response = {
            'symbol': signal.symbol,
            'exchange': signal.exchange,
            'detection_time': signal.detection_time,
            'emergency': False,
            'entry_ready': False,
            'rejection_reasons': [f"Cooldown active: {remaining_minutes:.1f} minutes remaining"],
            'cooldown_active': True,
            'cooldown_remaining_minutes': remaining_minutes,
            'action_required': 'WAIT'
        }
        
        self.logger.info("cooldown.active", {
            "symbol": signal.symbol,
            "remaining_minutes": round(remaining_minutes, 1)
        })
        
        return response

    def _normalize(self, value: float, scaler_name: str) -> float:
        """✅ PERFORMANCE: Normalize using pre-computed scaler factors"""
        try:
            min_val, range_val = self._precomputed_scalers[scaler_name]
            if range_val == 0.0:
                return 0.0

            normalized = (value - min_val) / range_val
            return min(max(normalized, 0.0), 1.0)
        except KeyError:
            # Fallback to old method if scaler not pre-computed
            scaler = self.scalers.get(scaler_name, {})
            if 'min' not in scaler or 'max' not in scaler:
                raise ValueError(f"Scaler missing min/max values: {scaler}")

            min_val = scaler['min']
            max_val = scaler['max']
            if max_val == min_val:
                return 0.0

            normalized = (value - min_val) / (max_val - min_val)
            return min(max(normalized, 0.0), 1.0)

    def update_trading_result(self, symbol: str, pnl: float, success: bool):
        """✅ THREAD SAFETY: Update trading results with proper synchronization"""
        with self._state_lock:
            if success:
                self.consecutive_losses = 0
            else:
                self.consecutive_losses += 1

            self.daily_pnl += pnl
            self.max_daily_pnl = max(self.max_daily_pnl, self.daily_pnl)

        # ✅ PERFORMANCE: Log outside lock to reduce lock contention
        self.logger.info("trading_result.updated", {
            "symbol": symbol,
            "pnl": pnl,
            "success": success,
            "consecutive_losses": self.consecutive_losses,
            "daily_pnl": self.daily_pnl
        })

    def reset_daily_tracking(self):
        """Reset daily tracking counters."""
        self.daily_signal_count = 0
        self.daily_pnl = 0.0
        self.max_daily_pnl = 0.0
        self.consecutive_losses = 0
        self.cooldown_until = None
        
        self.logger.info("daily_tracking.reset", {})

    def set_trading_active(self, active: bool):
        """Manually set trading active status."""
        self.trading_active = active
        self.logger.info("trading_status.set", {"active": active})

    def get_processing_statistics(self) -> Dict:
        """Get comprehensive processor statistics."""
        return {
            "daily_signal_count": self.daily_signal_count,
            "consecutive_losses": self.consecutive_losses,
            "daily_pnl": self.daily_pnl,
            "current_drawdown_pct": self._calculate_current_drawdown(),
            "cooldown_active": self._is_in_cooldown(),
            "trading_active": self.trading_active,
            "safety_limits": {
                "max_daily_signals": self.max_daily_signals,
                "min_cooldown_minutes": self.min_cooldown_minutes,
                "max_consecutive_losses": self.max_consecutive_losses,
                "max_drawdown_pct": self.max_drawdown_pct
            },
            "emergency_conditions": {
                "max_spread_pct": self.emergency_max_spread,
                "min_liquidity_usdt": self.emergency_min_liquidity,
                "max_rsi": self.emergency_max_rsi,
                "min_volume_24h_usdt": self.emergency_min_volume_24h
            }
        }




