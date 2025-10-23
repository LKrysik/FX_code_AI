"""
Trading Interfaces - Ports for trading operations
=================================================
Abstract interfaces for trading execution and position management.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncIterator
from datetime import datetime
from decimal import Decimal

from ..models.trading import Order, Position, Trade, Portfolio, OrderSide, OrderType
from ..models.market_data import MarketData
from ..models.signals import FlashPumpSignal, ReversalSignal


class IOrderExecutor(ABC):
    """
    Interface for order execution.
    Abstracts away exchange-specific order management.
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to trading API"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to trading API"""
        pass
    
    @abstractmethod
    async def place_market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        client_order_id: Optional[str] = None
    ) -> Order:
        """Place a market order"""
        pass
    
    @abstractmethod
    async def place_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        client_order_id: Optional[str] = None
    ) -> Order:
        """Place a limit order"""
        pass
    
    @abstractmethod
    async def place_stop_loss_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        stop_price: Decimal,
        client_order_id: Optional[str] = None
    ) -> Order:
        """Place a stop loss order"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order"""
        pass
    
    @abstractmethod
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """Cancel all orders for a symbol (or all symbols)"""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: str) -> Optional[Order]:
        """Get current status of an order"""
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders"""
        pass
    
    @abstractmethod
    async def get_order_history(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Order]:
        """Get order history"""
        pass
    
    @abstractmethod
    def get_exchange_name(self) -> str:
        """Get the name of the exchange"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if trading connection is healthy"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        pass
    
    @abstractmethod
    async def get_trading_fees(self, symbol: str) -> Dict[str, Decimal]:
        """Get trading fees for a symbol"""
        pass


class IPositionRepository(ABC):
    """
    Interface for position storage and retrieval.
    Manages position lifecycle and persistence.
    """
    
    @abstractmethod
    async def save_position(self, position: Position) -> None:
        """Save or update a position"""
        pass
    
    @abstractmethod
    async def get_position(self, position_id: str) -> Optional[Position]:
        """Get a position by ID"""
        pass
    
    @abstractmethod
    async def get_position_by_symbol(self, symbol: str, exchange: str) -> Optional[Position]:
        """Get active position for a symbol"""
        pass
    
    @abstractmethod
    async def get_open_positions(self, exchange: Optional[str] = None) -> List[Position]:
        """Get all open positions"""
        pass
    
    @abstractmethod
    async def get_closed_positions(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        exchange: Optional[str] = None
    ) -> List[Position]:
        """Get closed positions within time range"""
        pass
    
    @abstractmethod
    async def update_position_pnl(self, position_id: str, current_price: Decimal) -> None:
        """Update position's unrealized PnL"""
        pass
    
    @abstractmethod
    async def close_position(
        self,
        position_id: str,
        exit_price: Decimal,
        exit_reason: str,
        exit_time: Optional[datetime] = None
    ) -> None:
        """Mark position as closed"""
        pass
    
    @abstractmethod
    async def delete_position(self, position_id: str) -> bool:
        """Delete a position (use with caution)"""
        pass
    
    @abstractmethod
    async def get_positions_by_signal(self, signal_type: str) -> List[Position]:
        """Get positions opened based on specific signal type"""
        pass


class ITradeRepository(ABC):
    """
    Interface for trade history storage and analysis.
    Manages completed trade records.
    """
    
    @abstractmethod
    async def save_trade(self, trade: Trade) -> None:
        """Save a completed trade"""
        pass
    
    @abstractmethod
    async def get_trade(self, trade_id: str) -> Optional[Trade]:
        """Get a trade by ID"""
        pass
    
    @abstractmethod
    async def get_trades(
        self,
        symbol: Optional[str] = None,
        exchange: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Trade]:
        """Get trades with optional filters"""
        pass
    
    @abstractmethod
    async def get_trades_by_signal(self, signal_type: str) -> List[Trade]:
        """Get trades based on specific signal type"""
        pass
    
    @abstractmethod
    async def get_profitable_trades(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Trade]:
        """Get only profitable trades"""
        pass
    
    @abstractmethod
    async def get_losing_trades(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Trade]:
        """Get only losing trades"""
        pass
    
    @abstractmethod
    async def get_trade_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get trade statistics (win rate, avg profit, etc.)"""
        pass
    
    @abstractmethod
    async def delete_trade(self, trade_id: str) -> bool:
        """Delete a trade record"""
        pass


class IPortfolioManager(ABC):
    """
    Interface for portfolio management.
    Tracks overall account performance and risk.
    """
    
    @abstractmethod
    async def get_portfolio(self, account_id: str, exchange: str) -> Optional[Portfolio]:
        """Get current portfolio state"""
        pass
    
    @abstractmethod
    async def update_portfolio(self, portfolio: Portfolio) -> None:
        """Update portfolio information"""
        pass
    
    @abstractmethod
    async def calculate_total_pnl(self, account_id: str, exchange: str) -> Decimal:
        """Calculate total realized + unrealized PnL"""
        pass
    
    @abstractmethod
    async def calculate_daily_pnl(self, account_id: str, exchange: str) -> Decimal:
        """Calculate today's PnL"""
        pass
    
    @abstractmethod
    async def get_position_sizes(self, account_id: str, exchange: str) -> Dict[str, Decimal]:
        """Get position sizes by symbol"""
        pass
    
    @abstractmethod
    async def calculate_risk_exposure(self, account_id: str, exchange: str) -> Decimal:
        """Calculate total risk exposure as percentage of equity"""
        pass
    
    @abstractmethod
    async def check_margin_requirements(self, account_id: str, exchange: str) -> Dict[str, Any]:
        """Check margin requirements and available margin"""
        pass
    
    @abstractmethod
    async def get_portfolio_history(
        self,
        account_id: str,
        exchange: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Portfolio]:
        """Get portfolio snapshots over time"""
        pass


class IRiskManager(ABC):
    """
    Interface for risk management.
    Validates trades and manages risk limits.
    """
    
    @abstractmethod
    async def validate_trade_entry(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Optional[Decimal] = None
    ) -> tuple[bool, List[str]]:
        """
        Validate if trade entry is allowed.
        Returns (is_allowed, risk_reasons)
        """
        pass
    
    @abstractmethod
    async def calculate_position_size(
        self,
        signal: FlashPumpSignal,
        account_balance: Decimal,
        risk_per_trade_pct: Decimal
    ) -> Decimal:
        """Calculate optimal position size based on risk parameters"""
        pass
    
    @abstractmethod
    async def calculate_stop_loss_price(
        self,
        entry_price: Decimal,
        side: OrderSide,
        risk_pct: Decimal
    ) -> Decimal:
        """Calculate stop loss price based on risk percentage"""
        pass
    
    @abstractmethod
    async def check_daily_limits(self, account_id: str, exchange: str) -> tuple[bool, List[str]]:
        """Check if daily trading limits are exceeded"""
        pass
    
    @abstractmethod
    async def check_position_limits(self, account_id: str, exchange: str) -> tuple[bool, List[str]]:
        """Check if position limits are exceeded"""
        pass
    
    @abstractmethod
    async def assess_market_risk(
        self,
        symbol: str,
        market_data: MarketData,
        signal: Optional[FlashPumpSignal] = None
    ) -> Dict[str, Any]:
        """Assess current market risk for a symbol"""
        pass
    
    @abstractmethod
    async def should_force_close_position(self, position: Position, current_price: Decimal) -> tuple[bool, str]:
        """
        Check if position should be force-closed due to risk.
        Returns (should_close, reason)
        """
        pass
    
    @abstractmethod
    async def update_stop_loss(
        self,
        position: Position,
        current_price: Decimal,
        trailing_enabled: bool = False
    ) -> Optional[Decimal]:
        """Update stop loss price, returns new stop loss if changed"""
        pass


class ISignalProcessor(ABC):
    """
    Interface for processing trading signals.
    Converts signals into trading decisions.
    """
    
    @abstractmethod
    async def process_pump_signal(self, signal: FlashPumpSignal) -> Optional[Dict[str, Any]]:
        """
        Process flash pump signal and return trading decision.
        Returns None if no action should be taken.
        """
        pass
    
    @abstractmethod
    async def process_reversal_signal(self, signal: ReversalSignal) -> Optional[Dict[str, Any]]:
        """
        Process reversal signal and return trading decision.
        Usually results in position closure.
        """
        pass
    
    @abstractmethod
    async def validate_signal_quality(self, signal: FlashPumpSignal) -> tuple[bool, float]:
        """
        Validate signal quality.
        Returns (is_valid, confidence_score)
        """
        pass
    
    @abstractmethod
    async def calculate_entry_timing(self, signal: FlashPumpSignal) -> Dict[str, Any]:
        """Calculate optimal entry timing for a signal"""
        pass
    
    @abstractmethod
    async def should_ignore_signal(
        self,
        signal: FlashPumpSignal,
        current_positions: List[Position]
    ) -> tuple[bool, str]:
        """
        Check if signal should be ignored.
        Returns (should_ignore, reason)
        """
        pass


class ITradingStrategy(ABC):
    """
    Interface for trading strategies.
    Defines how signals are converted to trades.
    """
    
    @abstractmethod
    async def should_enter_trade(
        self,
        signal: FlashPumpSignal,
        market_data: MarketData,
        portfolio: Portfolio
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Decide if trade should be entered.
        Returns (should_enter, trade_params)
        """
        pass
    
    @abstractmethod
    async def should_exit_trade(
        self,
        position: Position,
        current_price: Decimal,
        market_data: MarketData,
        reversal_signal: Optional[ReversalSignal] = None
    ) -> tuple[bool, str]:
        """
        Decide if trade should be exited.
        Returns (should_exit, exit_reason)
        """
        pass
    
    @abstractmethod
    async def calculate_take_profit_levels(
        self,
        entry_price: Decimal,
        signal: FlashPumpSignal
    ) -> List[Decimal]:
        """Calculate take profit levels"""
        pass
    
    @abstractmethod
    async def adjust_position_size(
        self,
        base_size: Decimal,
        signal: FlashPumpSignal,
        market_conditions: Dict[str, Any]
    ) -> Decimal:
        """Adjust position size based on market conditions"""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get strategy name"""
        pass
    
    @abstractmethod
    async def get_strategy_parameters(self) -> Dict[str, Any]:
        """Get current strategy parameters"""
        pass