"""
Signal Models - Trading signal data structures
==============================================
Pure data models for trading signals and alerts.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal
from enum import Enum


class SignalType(str, Enum):
    """Types of trading signals"""
    FLASH_PUMP = "flash_pump"
    REVERSAL = "reversal"
    FLASH_DUMP = "flash_dump"


class SignalStrength(str, Enum):
    """Signal strength levels"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class FlashPumpSignal(BaseModel):
    """Flash pump detection signal"""
    
    # Basic identification
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange name")
    detection_time: datetime = Field(..., description="When pump was detected")
    
    # Price information
    peak_price: Decimal = Field(..., description="Peak price reached")
    baseline_price: Decimal = Field(..., description="Baseline price before pump")
    pump_magnitude: Decimal = Field(..., description="Pump magnitude in percentage")
    
    # Volume and velocity
    volume_surge_ratio: Decimal = Field(..., description="Volume surge multiplier")
    price_velocity: Decimal = Field(..., description="Price velocity (change per second)")
    baseline_volume: Optional[Decimal] = Field(None, description="Baseline volume before pump")
    
    # Analysis metrics
    confidence_score: Decimal = Field(..., description="Signal confidence (0-100)")
    pump_age_seconds: Decimal = Field(..., description="Time since pump started")
    
    # Market conditions
    market_spread_pct: Optional[Decimal] = Field(None, description="Market spread percentage")
    market_liquidity_usdt: Optional[Decimal] = Field(None, description="Market liquidity in USDT")
    market_rsi: Optional[Decimal] = Field(None, description="RSI indicator value")
    volume_24h_usdt: Optional[Decimal] = Field(None, description="24h volume in USDT")
    
    # Quality assessment
    reversal_quality_score: Decimal = Field(default=Decimal('0'), description="Reversal quality score")
    
    @property
    def symbol_key(self) -> str:
        """Unique identifier for this signal"""
        return f"{self.exchange}:{self.symbol}"
    
    @property
    def signal_strength(self) -> SignalStrength:
        """Determine signal strength based on confidence and magnitude"""
        if self.confidence_score >= 80 and self.pump_magnitude >= 15:
            return SignalStrength.VERY_STRONG
        elif self.confidence_score >= 70 and self.pump_magnitude >= 10:
            return SignalStrength.STRONG
        elif self.confidence_score >= 60 and self.pump_magnitude >= 7:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    @property
    def is_actionable(self) -> bool:
        """Check if signal is strong enough for trading"""
        return (
            self.confidence_score >= 60 and
            self.pump_magnitude >= 7 and
            self.pump_age_seconds <= 60  # Within 1 minute
        )


class ReversalSignal(BaseModel):
    """Reversal detection signal"""
    
    # Basic identification
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange name")
    detection_time: datetime = Field(..., description="When reversal was detected")
    
    # Price information
    pump_peak_price: Decimal = Field(..., description="Original pump peak price")
    reversal_price: Decimal = Field(..., description="Current reversal price")
    retracement_pct: Decimal = Field(..., description="Retracement percentage from peak")
    
    # Volume analysis
    volume_decline_ratio: Decimal = Field(..., description="Volume decline ratio")
    momentum_shift_confirmed: bool = Field(..., description="Whether momentum shift is confirmed")
    
    # Context
    original_pump_signal: FlashPumpSignal = Field(..., description="Original pump signal")
    emergency_exit: bool = Field(default=False, description="Emergency exit conditions met")
    spread_pct: Optional[Decimal] = Field(None, description="Current spread percentage")
    
    @property
    def symbol_key(self) -> str:
        """Unique identifier for this signal"""
        return f"{self.exchange}:{self.symbol}"
    
    @property
    def reversal_strength(self) -> SignalStrength:
        """Determine reversal strength"""
        if self.emergency_exit:
            return SignalStrength.VERY_STRONG
        elif self.retracement_pct >= 5 and self.volume_decline_ratio >= 0.6:
            return SignalStrength.STRONG
        elif self.retracement_pct >= 3 and self.volume_decline_ratio >= 0.4:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    @property
    def should_exit_immediately(self) -> bool:
        """Check if immediate exit is recommended"""
        return (
            self.emergency_exit or
            (self.retracement_pct >= 4 and self.volume_decline_ratio >= 0.5)
        )


class FlashDumpSignal(BaseModel):
    """Flash dump detection signal"""
    
    # Basic identification
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange name")
    detection_time: datetime = Field(..., description="When dump was detected")
    
    # Price information
    dump_start_price: Decimal = Field(..., description="Price when dump started")
    current_price: Decimal = Field(..., description="Current price")
    dump_magnitude: Decimal = Field(..., description="Dump magnitude in percentage")
    
    # Volume and velocity
    volume_spike_ratio: Decimal = Field(..., description="Volume spike multiplier")
    price_velocity: Decimal = Field(..., description="Price velocity (negative)")
    
    # Analysis
    confidence_score: Decimal = Field(..., description="Signal confidence (0-100)")
    dump_age_seconds: Decimal = Field(..., description="Time since dump started")
    
    # Context (if related to previous pump)
    related_pump_signal: Optional[FlashPumpSignal] = Field(None, description="Related pump signal")
    
    @property
    def symbol_key(self) -> str:
        """Unique identifier for this signal"""
        return f"{self.exchange}:{self.symbol}"
    
    @property
    def is_severe(self) -> bool:
        """Check if dump is severe"""
        return (
            self.dump_magnitude >= 10 and
            self.confidence_score >= 70
        )


class SignalSummary(BaseModel):
    """Summary of all signals for a symbol"""
    
    symbol: str
    exchange: str
    last_updated: datetime
    
    # Current signals
    active_pump: Optional[FlashPumpSignal] = None
    active_reversal: Optional[ReversalSignal] = None
    active_dump: Optional[FlashDumpSignal] = None
    
    # Statistics
    total_pumps_today: int = 0
    total_reversals_today: int = 0
    total_dumps_today: int = 0
    
    @property
    def symbol_key(self) -> str:
        """Unique identifier"""
        return f"{self.exchange}:{self.symbol}"
    
    @property
    def has_active_signals(self) -> bool:
        """Check if any signals are active"""
        return any([
            self.active_pump,
            self.active_reversal,
            self.active_dump
        ])
    
    @property
    def dominant_signal(self) -> Optional[str]:
        """Get the most important active signal"""
        if self.active_reversal and self.active_reversal.should_exit_immediately:
            return "reversal"
        elif self.active_dump and self.active_dump.is_severe:
            return "dump"
        elif self.active_pump and self.active_pump.is_actionable:
            return "pump"
        return None