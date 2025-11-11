"""
Trading Models - Core trading data structures
============================================
Pure data models for trading operations and positions.
"""

from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from decimal import Decimal
from enum import Enum


class OrderSide(str, Enum):
    """Order side"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderStatus(str, Enum):
    """Order status"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class PositionStatus(str, Enum):
    """Position status"""
    OPEN = "open"
    CLOSED = "closed"
    CLOSING = "closing"


class Order(BaseModel):
    """Trading order"""
    
    # Basic identification
    order_id: str = Field(..., description="Unique order ID")
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange name")
    
    # Order details
    side: OrderSide = Field(..., description="Buy or sell")
    order_type: OrderType = Field(..., description="Order type")
    quantity: Decimal = Field(..., description="Order quantity")
    price: Optional[Decimal] = Field(None, description="Order price (None for market orders)")
    
    # Status and timing
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = Field(None)
    cancelled_at: Optional[datetime] = Field(None)
    
    # Execution details
    filled_quantity: Decimal = Field(default=Decimal('0'))
    average_fill_price: Optional[Decimal] = Field(None)
    fee: Decimal = Field(default=Decimal('0'))
    
    # Metadata
    client_order_id: Optional[str] = Field(None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def symbol_key(self) -> str:
        """Unique identifier"""
        return f"{self.exchange}:{self.symbol}"
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled"""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_active(self) -> bool:
        """Check if order is still active"""
        return self.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def fill_percentage(self) -> Decimal:
        """Get fill percentage"""
        if self.quantity > 0:
            return (self.filled_quantity / self.quantity) * 100
        return Decimal('0')


class Position(BaseModel):
    """Trading position"""
    
    # Basic identification
    position_id: str = Field(..., description="Unique position ID")
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange name")
    
    # Position details
    side: OrderSide = Field(..., description="Position side (buy=long, sell=short)")
    size: Decimal = Field(..., description="Position size")
    entry_price: Decimal = Field(..., description="Average entry price")
    leverage: Decimal = Field(default=Decimal('1'), description="Position leverage")
    
    # Status and timing
    status: PositionStatus = Field(default=PositionStatus.OPEN)
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = Field(None)
    
    # Exit details
    exit_price: Optional[Decimal] = Field(None)
    exit_reason: Optional[str] = Field(None)
    
    # Orders
    entry_order: Optional[Order] = Field(None)
    exit_order: Optional[Order] = Field(None)
    
    # Risk management
    stop_loss_price: Optional[Decimal] = Field(None)
    take_profit_price: Optional[Decimal] = Field(None)
    
    # Performance tracking
    unrealized_pnl: Decimal = Field(default=Decimal('0'))
    realized_pnl: Optional[Decimal] = Field(None)
    max_profit: Decimal = Field(default=Decimal('0'))
    max_drawdown: Decimal = Field(default=Decimal('0'))
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def symbol_key(self) -> str:
        """Unique identifier"""
        return f"{self.exchange}:{self.symbol}"
    
    @property
    def is_long(self) -> bool:
        """Check if position is long"""
        return self.side == OrderSide.BUY
    
    @property
    def is_short(self) -> bool:
        """Check if position is short"""
        return self.side == OrderSide.SELL
    
    @property
    def is_open(self) -> bool:
        """Check if position is open"""
        return self.status == PositionStatus.OPEN
    
    @property
    def is_closed(self) -> bool:
        """Check if position is closed"""
        return self.status == PositionStatus.CLOSED
    
    @property
    def duration_seconds(self) -> Optional[Decimal]:
        """Get position duration in seconds"""
        if self.closed_at:
            return Decimal((self.closed_at - self.opened_at).total_seconds())
        return Decimal((datetime.now(timezone.utc) - self.opened_at).total_seconds())
    
    @property
    def notional_value(self) -> Decimal:
        """Get notional value of position"""
        return self.size * self.entry_price * self.leverage
    
    def calculate_pnl(self, current_price: Decimal) -> Decimal:
        """Calculate current PnL"""
        if self.is_long:
            return (current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - current_price) * self.size
    
    def calculate_pnl_percentage(self, current_price: Decimal) -> Decimal:
        """Calculate PnL as percentage"""
        pnl = self.calculate_pnl(current_price)
        if self.notional_value > 0:
            return (pnl / (self.notional_value / self.leverage)) * 100
        return Decimal('0')
    
    def update_unrealized_pnl(self, current_price: Decimal) -> None:
        """Update unrealized PnL and tracking metrics"""
        self.unrealized_pnl = self.calculate_pnl(current_price)
        
        # Update max profit/drawdown
        if self.unrealized_pnl > self.max_profit:
            self.max_profit = self.unrealized_pnl
        elif self.unrealized_pnl < self.max_drawdown:
            self.max_drawdown = self.unrealized_pnl


class Trade(BaseModel):
    """Completed trade record"""
    
    # Basic identification
    trade_id: str = Field(..., description="Unique trade ID")
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange name")
    
    # Trade details
    side: OrderSide = Field(..., description="Trade side")
    quantity: Decimal = Field(..., description="Trade quantity")
    entry_price: Decimal = Field(..., description="Entry price")
    exit_price: Decimal = Field(..., description="Exit price")
    
    # Timing
    entry_time: datetime = Field(..., description="Entry timestamp")
    exit_time: datetime = Field(..., description="Exit timestamp")
    
    # Performance
    pnl: Decimal = Field(..., description="Realized PnL")
    pnl_percentage: Decimal = Field(..., description="PnL percentage")
    fees: Decimal = Field(default=Decimal('0'), description="Total fees paid")
    
    # Context
    exit_reason: str = Field(..., description="Why trade was closed")
    original_position: Optional[Position] = Field(None, description="Original position")
    
    # Signal context (if available)
    entry_signal: Optional[str] = Field(None, description="Entry signal type")
    exit_signal: Optional[str] = Field(None, description="Exit signal type")
    
    @property
    def symbol_key(self) -> str:
        """Unique identifier"""
        return f"{self.exchange}:{self.symbol}"
    
    @property
    def duration_seconds(self) -> Decimal:
        """Get trade duration in seconds"""
        return Decimal((self.exit_time - self.entry_time).total_seconds())
    
    @property
    def duration_minutes(self) -> Decimal:
        """Get trade duration in minutes"""
        return self.duration_seconds / 60
    
    @property
    def is_profitable(self) -> bool:
        """Check if trade was profitable"""
        return self.pnl > 0
    
    @property
    def net_pnl(self) -> Decimal:
        """Get net PnL after fees"""
        return self.pnl - self.fees
    
    @property
    def return_on_investment(self) -> Decimal:
        """Calculate ROI"""
        investment = self.quantity * self.entry_price
        if investment > 0:
            return (self.net_pnl / investment) * 100
        return Decimal('0')


class Portfolio(BaseModel):
    """Portfolio summary"""
    
    # Basic info
    account_id: str = Field(..., description="Account identifier")
    exchange: str = Field(..., description="Exchange name")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # Balances
    total_balance_usdt: Decimal = Field(..., description="Total balance in USDT")
    available_balance_usdt: Decimal = Field(..., description="Available balance")
    used_margin_usdt: Decimal = Field(default=Decimal('0'), description="Used margin")
    
    # Positions
    open_positions: int = Field(default=0, description="Number of open positions")
    total_unrealized_pnl: Decimal = Field(default=Decimal('0'), description="Total unrealized PnL")
    
    # Performance
    total_realized_pnl: Decimal = Field(default=Decimal('0'), description="Total realized PnL")
    daily_pnl: Decimal = Field(default=Decimal('0'), description="Today's PnL")
    
    @property
    def equity(self) -> Decimal:
        """Calculate total equity"""
        return self.total_balance_usdt + self.total_unrealized_pnl
    
    @property
    def margin_ratio(self) -> Decimal:
        """Calculate margin utilization ratio"""
        if self.total_balance_usdt > 0:
            return (self.used_margin_usdt / self.total_balance_usdt) * 100
        return Decimal('0')
    
    @property
    def free_margin(self) -> Decimal:
        """Calculate free margin"""
        return self.available_balance_usdt - self.used_margin_usdt