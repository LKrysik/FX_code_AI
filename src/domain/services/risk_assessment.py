"""
Risk Assessment Domain Service
==============================
Pure business logic for risk management and safety checks
Separated from infrastructure and configuration concerns
"""


import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from ..models.market_data import MarketData
from ..models.signals import FlashPumpSignal
from ..models.risk import RiskLevel, RiskAssessment


@dataclass
class RiskManagementSettings:
    """Risk management configuration - Domain Model"""
    max_drawdown_pct: float = 6.0
    spread_blowout_pct: float = 5.0
    volume_death_threshold_pct: float = 80.0
    emergency_min_liquidity: float = 100.0


@dataclass 
class EntryConditionsSettings:
    """Entry conditions configuration - Domain Model"""
    min_volume_usdt: float = 10000.0
    min_magnitude: float = 0.15
    max_age_seconds: int = 30


@dataclass
class SafetyLimitsSettings:
    """Safety limits configuration - Domain Model"""
    max_daily_trades: int = 3
    max_position_size_usdt: float = 100.0


@dataclass
class RiskLimits:
    """Risk management limits configuration"""
    max_drawdown_pct: float = 6.0
    spread_blowout_pct: float = 5.0
    volume_death_threshold_pct: float = 80.0
    emergency_min_liquidity: float = 100.0
    max_daily_trades: int = 3
    max_consecutive_losses: int = 2
    daily_loss_limit_pct: float = 2.0


@dataclass
class EntryConditions:
    """Entry conditions configuration"""
    min_pump_age: int = 5
    max_entry_delay: int = 45
    min_confidence_threshold: float = 60.0
    max_spread_pct: float = 2.0


@dataclass
class PositionRiskAssessment:
    """
    BUG-DV-025 FIX: Structured dataclass for position risk assessment results.

    Provides a clean interface for risk assessment outputs instead of
    returning untyped dictionaries.
    """
    is_allowed: bool
    position_size: float
    risk_per_unit: float
    max_risk_amount: float
    side: str  # "LONG" or "SHORT"
    reason: Optional[str] = None
    warnings: Optional[List[str]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "is_allowed": self.is_allowed,
            "position_size": self.position_size,
            "risk_per_unit": self.risk_per_unit,
            "max_risk_amount": self.max_risk_amount,
            "side": self.side,
            "reason": self.reason,
            "warnings": self.warnings or []
        }


@dataclass
class AdvancedEntryConditions:
    """Advanced entry conditions configuration"""
    min_liquidity_usdt: float = 1000.0
    rsi_max: float = 70.0


@dataclass
class SafetyMetrics:
    """Current safety metrics"""
    daily_trades_count: int = 0
    consecutive_losses: int = 0
    daily_pnl: float = 0.0
    last_trade_time: float = 0.0


class RiskAssessmentService:
    """
    Core business logic for risk assessment and safety checks.
    
    This service contains pure domain logic for:
    - Emergency condition detection
    - Entry condition validation
    - Safety limit enforcement
    - Risk level assessment
    """
    
    def __init__(self, 
                 risk_management_settings: "RiskManagementSettings", 
                 entry_conditions_settings: "EntryConditionsSettings",
                 safety_limits_settings: "SafetyLimitsSettings"):
        """
        Initialize with Pydantic settings objects.
        
        Args:
            risk_management_settings: RiskManagementSettings from AppSettings
            entry_conditions_settings: EntryConditionsSettings from AppSettings
            safety_limits_settings: SafetyLimitsSettings from AppSettings
        """
        self.risk_limits = RiskLimits(
            max_drawdown_pct=float(risk_management_settings.max_drawdown_pct),
            spread_blowout_pct=float(risk_management_settings.spread_blowout_pct),
            volume_death_threshold_pct=float(risk_management_settings.volume_death_threshold_pct),
            emergency_min_liquidity=float(risk_management_settings.emergency_min_liquidity),
            max_daily_trades=safety_limits_settings.max_daily_trades,
            max_consecutive_losses=safety_limits_settings.max_consecutive_losses,
            daily_loss_limit_pct=float(safety_limits_settings.daily_loss_limit_pct)
        )
        
        self.entry_conditions = EntryConditions(
            min_pump_age=entry_conditions_settings.min_pump_age_seconds,
            max_entry_delay=entry_conditions_settings.max_entry_delay_seconds,
            min_confidence_threshold=float(entry_conditions_settings.min_confidence_threshold),
            max_spread_pct=float(entry_conditions_settings.max_spread_pct),
            min_liquidity_usdt=float(entry_conditions_settings.min_liquidity_usdt),
            rsi_max=float(entry_conditions_settings.rsi_max)
        )
        
        self.safety_metrics = SafetyMetrics()
    
    def assess_emergency_conditions(self, market_data: MarketData, 
                                  spread_pct: Optional[float], 
                                  liquidity_usdt: float) -> Tuple[bool, List[str]]:
        """
        Assess emergency conditions that should halt trading.
        
        Returns:
            Tuple of (is_safe, list_of_emergency_reasons)
        """
        emergency_reasons = []
        
        # Check spread blowout
        if spread_pct is not None and spread_pct > self.risk_limits.spread_blowout_pct:
            emergency_reasons.append(
                f"Emergency spread: {spread_pct:.2f}% > {self.risk_limits.spread_blowout_pct}%"
            )
        
        # Check volume death (if 24h volume data available)
        if hasattr(market_data, 'volume_24h_usdt') and market_data.volume_24h_usdt:
            if market_data.volume_24h_usdt > 0 and market_data.volume > 0:
                volume_drop_pct = (1 - market_data.volume / market_data.volume_24h_usdt) * 100
                if volume_drop_pct > self.risk_limits.volume_death_threshold_pct:
                    emergency_reasons.append(
                        f"Volume death: drop {volume_drop_pct:.2f}% > {self.risk_limits.volume_death_threshold_pct}%"
                    )
        
        # Check minimum liquidity
        if liquidity_usdt < self.risk_limits.emergency_min_liquidity:
            emergency_reasons.append(
                f"Low liquidity: ${liquidity_usdt:.0f} < ${self.risk_limits.emergency_min_liquidity}"
            )
        
        is_safe = len(emergency_reasons) == 0
        return is_safe, emergency_reasons
    
    def validate_entry_conditions(self, signal: FlashPumpSignal, 
                                 spread_pct: Optional[float],
                                 liquidity_usdt: float,
                                 rsi: Optional[float]) -> Tuple[bool, Dict]:
        """
        Validate entry conditions for a pump signal.
        
        Returns:
            Tuple of (entry_allowed, detailed_results)
        """
        results = {
            "passed_conditions": [],
            "failed_conditions": [],
            "all_conditions": {}
        }
        
        # 1. Pump age check
        pump_age_valid = (
            signal.pump_age_seconds is not None and
            self.entry_conditions.min_pump_age <= signal.pump_age_seconds <= self.entry_conditions.max_entry_delay
        )
        
        results["all_conditions"]["pump_age"] = {
            "actual": signal.pump_age_seconds,
            "required_min": self.entry_conditions.min_pump_age,
            "required_max": self.entry_conditions.max_entry_delay,
            "passed": pump_age_valid
        }
        
        if pump_age_valid:
            results["passed_conditions"].append("pump_age")
        else:
            if signal.pump_age_seconds is not None:
                if signal.pump_age_seconds < self.entry_conditions.min_pump_age:
                    results["failed_conditions"].append(
                        f"Pump too young: {signal.pump_age_seconds:.1f}s < {self.entry_conditions.min_pump_age}s"
                    )
                else:
                    results["failed_conditions"].append(
                        f"Pump too old: {signal.pump_age_seconds:.1f}s > {self.entry_conditions.max_entry_delay}s"
                    )
            else:
                results["failed_conditions"].append("Pump age is None")
        
        # 2. Confidence threshold
        confidence_valid = (
            signal.confidence_score is not None and
            signal.confidence_score >= self.entry_conditions.min_confidence_threshold
        )
        
        results["all_conditions"]["confidence"] = {
            "actual": signal.confidence_score,
            "required_min": self.entry_conditions.min_confidence_threshold,
            "passed": confidence_valid
        }
        
        if confidence_valid:
            results["passed_conditions"].append("confidence")
        else:
            if signal.confidence_score is not None:
                results["failed_conditions"].append(
                    f"Low confidence: {signal.confidence_score:.1f} < {self.entry_conditions.min_confidence_threshold}"
                )
            else:
                results["failed_conditions"].append("Confidence score is None")
        
        # 3. Spread check
        spread_valid = spread_pct is not None and spread_pct <= self.entry_conditions.max_spread_pct
        
        results["all_conditions"]["spread"] = {
            "actual": spread_pct,
            "required_max": self.entry_conditions.max_spread_pct,
            "passed": spread_valid
        }
        
        if spread_valid:
            results["passed_conditions"].append("spread")
        else:
            if spread_pct is not None:
                results["failed_conditions"].append(
                    f"High spread: {spread_pct:.2f}% > {self.entry_conditions.max_spread_pct}%"
                )
            else:
                results["failed_conditions"].append("Market spread is None")
        
        # 4. Liquidity check
        liquidity_valid = liquidity_usdt >= self.entry_conditions.min_liquidity_usdt
        
        results["all_conditions"]["liquidity"] = {
            "actual": liquidity_usdt,
            "required_min": self.entry_conditions.min_liquidity_usdt,
            "passed": liquidity_valid
        }
        
        if liquidity_valid:
            results["passed_conditions"].append("liquidity")
        else:
            results["failed_conditions"].append(
                f"Low liquidity: ${liquidity_usdt:.0f} < ${self.entry_conditions.min_liquidity_usdt}"
            )
        
        # 5. RSI check
        rsi_valid = rsi is None or rsi <= self.entry_conditions.rsi_max
        
        results["all_conditions"]["rsi"] = {
            "actual": rsi,
            "required_max": self.entry_conditions.rsi_max,
            "passed": rsi_valid
        }
        
        if rsi_valid:
            results["passed_conditions"].append("rsi")
        else:
            results["failed_conditions"].append(
                f"Overbought RSI: {rsi:.1f} > {self.entry_conditions.rsi_max}"
            )
        
        # 6. Pump magnitude check
        min_magnitude = 7.0  # Minimum pump magnitude
        magnitude_valid = (
            signal.pump_magnitude is not None and
            signal.pump_magnitude >= min_magnitude
        )
        
        results["all_conditions"]["pump_magnitude"] = {
            "actual": signal.pump_magnitude,
            "required_min": min_magnitude,
            "passed": magnitude_valid
        }
        
        if magnitude_valid:
            results["passed_conditions"].append("pump_magnitude")
        else:
            if signal.pump_magnitude is not None:
                results["failed_conditions"].append(
                    f"Weak pump: {signal.pump_magnitude:.1f}% < {min_magnitude}%"
                )
            else:
                results["failed_conditions"].append("Pump magnitude is None")
        
        entry_allowed = len(results["failed_conditions"]) == 0
        return entry_allowed, results
    
    def check_safety_limits(self) -> Tuple[bool, List[str]]:
        """
        Check all safety limits.
        
        Returns:
            Tuple of (limits_ok, list_of_violations)
        """
        violations = []
        
        # Daily trades limit
        if self.safety_metrics.daily_trades_count >= self.risk_limits.max_daily_trades:
            violations.append(
                f"Daily trades limit: {self.safety_metrics.daily_trades_count} >= {self.risk_limits.max_daily_trades}"
            )
        
        # Consecutive losses limit
        if self.safety_metrics.consecutive_losses >= self.risk_limits.max_consecutive_losses:
            violations.append(
                f"Consecutive losses: {self.safety_metrics.consecutive_losses} >= {self.risk_limits.max_consecutive_losses}"
            )
        
        # Daily loss limit
        if self.safety_metrics.daily_pnl <= -self.risk_limits.daily_loss_limit_pct:
            violations.append(
                f"Daily loss limit: {self.safety_metrics.daily_pnl:.2f}% <= -{self.risk_limits.daily_loss_limit_pct}%"
            )
        
        limits_ok = len(violations) == 0
        return limits_ok, violations
    
    def assess_position_risk(self, current_price: float, entry_price: float,
                           stop_loss: float, unrealized_pnl: float) -> RiskAssessment:
        """
        Assess risk level for an open position.
        
        Returns:
            RiskAssessment with risk level and recommendations
        """
        # Calculate drawdown from entry
        drawdown_pct = 0.0
        if entry_price > 0:
            drawdown_pct = ((entry_price - current_price) / entry_price) * 100
        
        # Calculate distance to stop loss
        stop_distance_pct = 0.0
        if current_price > 0 and stop_loss > 0:
            stop_distance_pct = ((current_price - stop_loss) / current_price) * 100
        
        # Determine risk level
        risk_level = RiskLevel.LOW
        recommendations = []
        
        if drawdown_pct > self.risk_limits.max_drawdown_pct:
            risk_level = RiskLevel.HIGH
            recommendations.append("Consider emergency exit - max drawdown exceeded")
        elif drawdown_pct > self.risk_limits.max_drawdown_pct * 0.7:
            risk_level = RiskLevel.MEDIUM
            recommendations.append("Monitor closely - approaching max drawdown")
        
        if stop_distance_pct < 1.0:  # Very close to stop loss
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.MEDIUM
            recommendations.append("Very close to stop loss")
        
        if unrealized_pnl < -100:  # Significant unrealized loss
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.MEDIUM
            recommendations.append("Significant unrealized loss")
        
        return RiskAssessment(
            risk_level=risk_level,
            drawdown_pct=drawdown_pct,
            stop_distance_pct=stop_distance_pct,
            unrealized_pnl=unrealized_pnl,
            recommendations=recommendations
        )
    
    def update_trade_result(self, pnl: float) -> None:
        """Update safety metrics with trade result"""
        self.safety_metrics.daily_trades_count += 1
        self.safety_metrics.daily_pnl += pnl
        
        if pnl < 0:
            self.safety_metrics.consecutive_losses += 1
        else:
            self.safety_metrics.consecutive_losses = 0
        
        self.safety_metrics.last_trade_time = time.time()
    
    def reset_daily_metrics(self) -> None:
        """Reset daily metrics (call at midnight)"""
        self.safety_metrics.daily_trades_count = 0
        self.safety_metrics.consecutive_losses = 0
        self.safety_metrics.daily_pnl = 0.0
    
    def get_safety_metrics(self) -> SafetyMetrics:
        """Get current safety metrics"""
        return self.safety_metrics
    
    def calculate_position_size(self, account_balance: float, risk_pct: float,
                              entry_price: float, stop_loss: float,
                              side: str = "LONG") -> float:
        """
        Calculate position size based on risk management rules.

        BUG-DV-026 FIX: Added side parameter to handle LONG and SHORT positions correctly.
        For LONG: stop_loss < entry_price (risk = entry - stop_loss)
        For SHORT: stop_loss > entry_price (risk = stop_loss - entry)

        Args:
            account_balance: Total account balance
            risk_pct: Risk percentage per trade (e.g., 2.0 for 2%)
            entry_price: Planned entry price
            stop_loss: Stop loss price
            side: Position side - "LONG" or "SHORT" (default: "LONG")

        Returns:
            Position size in base currency
        """
        if entry_price <= 0 or stop_loss <= 0:
            return 0.0

        # BUG-DV-026 FIX: Calculate risk per unit based on position side
        side_upper = side.upper()
        if side_upper == "LONG":
            # LONG: stop_loss should be below entry
            if stop_loss >= entry_price:
                return 0.0
            risk_per_unit = entry_price - stop_loss
        elif side_upper == "SHORT":
            # SHORT: stop_loss should be above entry
            if stop_loss <= entry_price:
                return 0.0
            risk_per_unit = stop_loss - entry_price
        else:
            # Invalid side, fallback to LONG logic
            if stop_loss >= entry_price:
                return 0.0
            risk_per_unit = entry_price - stop_loss

        # Calculate maximum risk amount
        max_risk_amount = account_balance * (risk_pct / 100)

        # Calculate position size
        position_size = max_risk_amount / risk_per_unit

        return max(0.0, position_size)