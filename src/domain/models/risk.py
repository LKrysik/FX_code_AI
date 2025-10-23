"""
Risk Management Models - Risk assessment and safety structures
=============================================================
Pure data models for risk management and safety limits.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, List
from decimal import Decimal
from enum import Enum


class RiskLevel(str, Enum):
    """Risk level assessment"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class StopLossType(str, Enum):
    """Stop loss types"""
    FIXED = "fixed"
    TRAILING = "trailing"
    PEAK_BUFFER = "peak_buffer"
    TIME_BASED = "time_based"


class RiskParams(BaseModel):
    """Risk parameters for a position"""
    
    # Position sizing
    max_position_size_usdt: Decimal = Field(..., description="Maximum position size in USDT")
    risk_per_trade_pct: Decimal = Field(..., description="Risk percentage per trade")
    max_leverage: Decimal = Field(default=Decimal('1'), description="Maximum allowed leverage")
    
    # Stop loss configuration
    stop_loss_type: StopLossType = Field(default=StopLossType.PEAK_BUFFER)
    stop_loss_pct: Optional[Decimal] = Field(None, description="Fixed stop loss percentage")
    peak_buffer_pct: Optional[Decimal] = Field(None, description="Peak buffer percentage")
    trailing_distance_pct: Optional[Decimal] = Field(None, description="Trailing stop distance")
    
    # Take profit
    take_profit_pct: Optional[Decimal] = Field(None, description="Take profit percentage")
    partial_take_profit_pct: Optional[Decimal] = Field(None, description="Partial take profit percentage")
    
    # Time limits
    max_position_duration_minutes: Optional[int] = Field(None, description="Maximum position duration")
    force_close_after_minutes: Optional[int] = Field(None, description="Force close after minutes")
    
    # Market conditions
    max_spread_pct: Decimal = Field(default=Decimal('2'), description="Maximum allowed spread")
    min_liquidity_usdt: Decimal = Field(default=Decimal('1000'), description="Minimum required liquidity")
    
    @property
    def has_stop_loss(self) -> bool:
        """Check if stop loss is configured"""
        return any([
            self.stop_loss_pct is not None,
            self.peak_buffer_pct is not None,
            self.trailing_distance_pct is not None
        ])
    
    @property
    def has_take_profit(self) -> bool:
        """Check if take profit is configured"""
        return self.take_profit_pct is not None
    
    @property
    def has_time_limit(self) -> bool:
        """Check if time limits are set"""
        return any([
            self.max_position_duration_minutes is not None,
            self.force_close_after_minutes is not None
        ])


class SafetyLimits(BaseModel):
    """Daily and overall safety limits"""
    
    # Daily limits
    max_daily_trades: int = Field(default=5, description="Maximum trades per day")
    max_daily_loss_pct: Decimal = Field(default=Decimal('5'), description="Maximum daily loss percentage")
    max_daily_risk_usdt: Decimal = Field(default=Decimal('1000'), description="Maximum daily risk in USDT")
    
    # Consecutive limits
    max_consecutive_losses: int = Field(default=3, description="Maximum consecutive losses")
    max_consecutive_trades_per_symbol: int = Field(default=2, description="Max consecutive trades per symbol")
    
    # Cooldown periods
    loss_cooldown_minutes: int = Field(default=30, description="Cooldown after loss")
    symbol_cooldown_minutes: int = Field(default=60, description="Cooldown per symbol")
    
    # Portfolio limits
    max_open_positions: int = Field(default=3, description="Maximum open positions")
    max_portfolio_risk_pct: Decimal = Field(default=Decimal('10'), description="Maximum portfolio risk")
    
    # Emergency conditions
    emergency_stop_loss_pct: Decimal = Field(default=Decimal('15'), description="Emergency stop loss")
    max_drawdown_pct: Decimal = Field(default=Decimal('20'), description="Maximum drawdown before stop")
    
    @property
    def is_conservative(self) -> bool:
        """Check if limits are conservative"""
        return (
            self.max_daily_trades <= 3 and
            self.max_daily_loss_pct <= 3 and
            self.max_consecutive_losses <= 2
        )
    
    @property
    def is_aggressive(self) -> bool:
        """Check if limits are aggressive"""
        return (
            self.max_daily_trades >= 10 or
            self.max_daily_loss_pct >= 10 or
            self.max_portfolio_risk_pct >= 20
        )


class RiskAssessment(BaseModel):
    """Risk assessment for a trading opportunity"""
    
    # Basic info
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange name")
    assessment_time: datetime = Field(default_factory=datetime.utcnow)
    
    # Market risk factors
    spread_pct: Decimal = Field(..., description="Current spread percentage")
    liquidity_usdt: Decimal = Field(..., description="Available liquidity")
    volatility_score: Decimal = Field(..., description="Volatility score (0-100)")
    
    # Signal risk factors
    signal_confidence: Decimal = Field(..., description="Signal confidence score")
    signal_age_seconds: Decimal = Field(..., description="Signal age in seconds")
    market_conditions_score: Decimal = Field(..., description="Market conditions score")
    
    # Portfolio risk factors
    current_positions: int = Field(..., description="Current open positions")
    daily_trades_count: int = Field(..., description="Trades executed today")
    daily_pnl_pct: Decimal = Field(..., description="Daily PnL percentage")
    consecutive_losses: int = Field(..., description="Consecutive losses")
    
    # Risk scores (0-100, higher = more risky)
    market_risk_score: Decimal = Field(..., description="Market risk score")
    signal_risk_score: Decimal = Field(..., description="Signal risk score")
    portfolio_risk_score: Decimal = Field(..., description="Portfolio risk score")
    overall_risk_score: Decimal = Field(..., description="Overall risk score")
    
    # Assessment result
    risk_level: RiskLevel = Field(..., description="Overall risk level")
    trade_allowed: bool = Field(..., description="Whether trade is allowed")
    risk_reasons: List[str] = Field(default_factory=list, description="Risk factors identified")
    
    @property
    def symbol_key(self) -> str:
        """Unique identifier"""
        return f"{self.exchange}:{self.symbol}"
    
    @property
    def is_safe_to_trade(self) -> bool:
        """Check if it's safe to trade"""
        return (
            self.trade_allowed and
            self.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM] and
            self.overall_risk_score <= 70
        )
    
    @property
    def requires_reduced_size(self) -> bool:
        """Check if position size should be reduced"""
        return (
            self.risk_level == RiskLevel.MEDIUM or
            self.overall_risk_score > 50
        )
    
    def get_size_multiplier(self) -> Decimal:
        """Get position size multiplier based on risk"""
        if self.risk_level == RiskLevel.LOW:
            return Decimal('1.0')
        elif self.risk_level == RiskLevel.MEDIUM:
            return Decimal('0.7')
        elif self.risk_level == RiskLevel.HIGH:
            return Decimal('0.4')
        else:  # CRITICAL
            return Decimal('0.1')


class RiskMetrics(BaseModel):
    """Risk metrics tracking"""
    
    # Time period
    period_start: datetime = Field(..., description="Metrics period start")
    period_end: datetime = Field(..., description="Metrics period end")
    
    # Trade metrics
    total_trades: int = Field(default=0)
    winning_trades: int = Field(default=0)
    losing_trades: int = Field(default=0)
    
    # Risk metrics
    max_drawdown_pct: Decimal = Field(default=Decimal('0'))
    current_drawdown_pct: Decimal = Field(default=Decimal('0'))
    sharpe_ratio: Optional[Decimal] = Field(None)
    sortino_ratio: Optional[Decimal] = Field(None)
    
    # Safety violations
    daily_limit_violations: int = Field(default=0)
    consecutive_loss_violations: int = Field(default=0)
    emergency_stops: int = Field(default=0)
    
    # Risk-adjusted returns
    total_return_pct: Decimal = Field(default=Decimal('0'))
    risk_adjusted_return_pct: Decimal = Field(default=Decimal('0'))
    
    @property
    def win_rate(self) -> Decimal:
        """Calculate win rate"""
        if self.total_trades > 0:
            return (Decimal(self.winning_trades) / Decimal(self.total_trades)) * 100
        return Decimal('0')
    
    @property
    def risk_score(self) -> Decimal:
        """Calculate overall risk score"""
        score = Decimal('0')
        
        # Drawdown penalty
        score += self.max_drawdown_pct * 2
        
        # Violation penalty
        score += Decimal(self.daily_limit_violations) * 10
        score += Decimal(self.consecutive_loss_violations) * 15
        score += Decimal(self.emergency_stops) * 25
        
        # Win rate bonus
        if self.win_rate >= 60:
            score -= 10
        elif self.win_rate <= 40:
            score += 15
        
        return max(Decimal('0'), min(Decimal('100'), score))
    
    @property
    def risk_level(self) -> RiskLevel:
        """Determine risk level from metrics"""
        score = self.risk_score
        
        if score <= 25:
            return RiskLevel.LOW
        elif score <= 50:
            return RiskLevel.MEDIUM
        elif score <= 75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL


class EmergencyConditions(BaseModel):
    """Emergency trading conditions"""
    
    # Market conditions
    extreme_spread_pct: Decimal = Field(default=Decimal('5'), description="Extreme spread threshold")
    liquidity_death_threshold: Decimal = Field(default=Decimal('100'), description="Minimum liquidity")
    
    # Portfolio conditions
    max_portfolio_drawdown_pct: Decimal = Field(default=Decimal('15'))
    max_daily_loss_pct: Decimal = Field(default=Decimal('8'))
    
    # System conditions
    max_consecutive_system_errors: int = Field(default=3)
    max_order_rejection_rate_pct: Decimal = Field(default=Decimal('20'))
    
    # Time-based conditions
    market_close_buffer_minutes: int = Field(default=30)
    maintenance_mode: bool = Field(default=False)
    
    def check_emergency_conditions(
        self,
        current_spread: Decimal,
        current_liquidity: Decimal,
        portfolio_drawdown: Decimal,
        daily_loss: Decimal,
        system_errors: int,
        rejection_rate: Decimal
    ) -> tuple[bool, List[str]]:
        """Check if emergency conditions are met"""
        
        emergency = False
        reasons = []
        
        if current_spread > self.extreme_spread_pct:
            emergency = True
            reasons.append(f"Extreme spread: {current_spread}%")
        
        if current_liquidity < self.liquidity_death_threshold:
            emergency = True
            reasons.append(f"Low liquidity: ${current_liquidity}")
        
        if portfolio_drawdown > self.max_portfolio_drawdown_pct:
            emergency = True
            reasons.append(f"Portfolio drawdown: {portfolio_drawdown}%")
        
        if daily_loss > self.max_daily_loss_pct:
            emergency = True
            reasons.append(f"Daily loss limit: {daily_loss}%")
        
        if system_errors >= self.max_consecutive_system_errors:
            emergency = True
            reasons.append(f"System errors: {system_errors}")
        
        if rejection_rate > self.max_order_rejection_rate_pct:
            emergency = True
            reasons.append(f"Order rejection rate: {rejection_rate}%")
        
        if self.maintenance_mode:
            emergency = True
            reasons.append("Maintenance mode active")
        
        return emergency, reasons