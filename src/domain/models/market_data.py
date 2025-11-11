"""
Market Data Models - Core market data structures
===============================================
Pure data models for market information without external dependencies.
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Tuple
from decimal import Decimal


class MarketData(BaseModel):
    """Core market data event - standardized across all exchanges"""

    model_config = ConfigDict(
        # Use Decimal for precise financial calculations
        json_encoders={
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }
    )

    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    exchange: str = Field(..., description="Exchange name (e.g., mexc)")
    price: Decimal = Field(..., description="Current price")
    volume: Decimal = Field(..., description="Volume in base currency")
    timestamp: datetime = Field(..., description="Event timestamp")
    volume_24h_usdt: Optional[Decimal] = Field(None, description="24h volume in USDT")
    liquidity_usdt: Optional[Decimal] = Field(None, description="Available liquidity in USDT")
    side: Optional[str] = Field(None, description="Trade side: buy/sell/unknown")
    
    @property
    def symbol_key(self) -> str:
        """Unique identifier for this market data"""
        return f"{self.exchange}:{self.symbol}"


class OrderBookLevel(BaseModel):
    """Single level in order book"""
    
    price: Decimal = Field(..., description="Price level")
    quantity: Decimal = Field(..., description="Quantity at this level")


class OrderBook(BaseModel):
    """Order book snapshot"""
    
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange name")
    timestamp: datetime = Field(..., description="Snapshot timestamp")
    bids: List[OrderBookLevel] = Field(default_factory=list, description="Buy orders")
    asks: List[OrderBookLevel] = Field(default_factory=list, description="Sell orders")
    
    @property
    def best_bid(self) -> Optional[Decimal]:
        """Highest bid price"""
        return self.bids[0].price if self.bids else None
    
    @property
    def best_ask(self) -> Optional[Decimal]:
        """Lowest ask price"""
        return self.asks[0].price if self.asks else None
    
    @property
    def spread_pct(self) -> Optional[Decimal]:
        """Bid-ask spread as percentage"""
        if self.best_bid and self.best_ask and self.best_bid > 0:
            # Use Decimal arithmetic throughout to avoid floating-point precision errors
            spread = self.best_ask - self.best_bid
            spread_pct = (spread / self.best_bid) * Decimal('100')
            # Round to 10 decimal places to eliminate precision artifacts
            return spread_pct.quantize(Decimal('0.000001'))
        return None
    
    @property
    def liquidity_usdt(self) -> Decimal:
        """Total liquidity in USDT (top 5 levels each side)"""
        bid_liquidity = sum(
            level.price * level.quantity 
            for level in self.bids[:5]
        )
        ask_liquidity = sum(
            level.price * level.quantity 
            for level in self.asks[:5]
        )
        return bid_liquidity + ask_liquidity


class PriceHistory(BaseModel):
    """Price history for technical analysis"""
    
    symbol: str
    exchange: str
    prices: List[Tuple[datetime, Decimal]] = Field(default_factory=list)
    max_length: int = Field(default=1000, description="Maximum history length")
    
    def add_price(self, timestamp: datetime, price: Decimal) -> None:
        """Add new price point"""
        self.prices.append((timestamp, price))
        if len(self.prices) > self.max_length:
            self.prices.pop(0)
    
    def get_price_change_pct(self, minutes: int) -> Optional[Decimal]:
        """Get price change percentage over specified minutes"""
        if len(self.prices) < 2:
            return None
        
        current_time = self.prices[-1][0]
        current_price = self.prices[-1][1]
        
        # Find price from 'minutes' ago
        target_time = current_time.replace(
            minute=current_time.minute - minutes
        )
        
        for timestamp, price in reversed(self.prices[:-1]):
            if timestamp <= target_time:
                if price > 0:
                    return ((current_price - price) / price) * 100
                break
        
        return None
    
    def get_velocity(self, seconds: int) -> Optional[Decimal]:
        """Get price velocity (change per second)"""
        if len(self.prices) < 2:
            return None
        
        current_time = self.prices[-1][0]
        current_price = self.prices[-1][1]
        
        # Find price from 'seconds' ago
        for timestamp, price in reversed(self.prices[:-1]):
            time_diff = (current_time - timestamp).total_seconds()
            if time_diff >= seconds:
                if time_diff > 0:
                    return (current_price - price) / Decimal(time_diff)
                break
        
        return None