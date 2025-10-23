"""
File Market Data Provider
=========================
Adapter that makes FileConnector compatible with IMarketDataProvider interface.
Used for backtest mode to provide standardized market data interface.
"""

import asyncio
from typing import AsyncIterator, Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from ...domain.interfaces.market_data import IMarketDataProvider
from ...domain.models.market_data import MarketData
from ...exchanges.file_connector import FileConnector
from ...core.event_bus import EventBus
from ...core.logger import StructuredLogger


class FileMarketDataProvider(IMarketDataProvider):
    """
    Market data provider that uses FileConnector for backtesting.
    Adapts FileConnector to IMarketDataProvider interface.
    """
    
    def __init__(self, file_connector: FileConnector, event_bus: EventBus, logger: StructuredLogger):
        self.file_connector = file_connector
        self.event_bus = event_bus
        self.logger = logger
        self._subscribed_symbols = set()
        self._market_data_queues: Dict[str, asyncio.Queue] = {}
        
        # Subscribe to market data events from file connector
        import asyncio
        asyncio.create_task(self.event_bus.subscribe('market.price_update', self._handle_price_update))
        asyncio.create_task(self.event_bus.subscribe('market.data_stream_ended', self._handle_stream_ended))
    
    async def connect(self) -> None:
        """Establish connection to file data source"""
        await self.file_connector.connect()
        self.logger.info("file_market_data_provider.connected", {})
    
    async def disconnect(self) -> None:
        """Close connection to file data source"""
        await self.file_connector.disconnect()
        self.logger.info("file_market_data_provider.disconnected", {})
    
    async def subscribe_to_symbol(self, symbol: str) -> None:
        """Subscribe to market data for a specific symbol"""
        if symbol not in self._subscribed_symbols:
            # Subscribe via file connector
            success = await self.file_connector.subscribe_symbol(symbol)
            
            if success:
                self._subscribed_symbols.add(symbol)
                # Create queue for this symbol's data
                self._market_data_queues[symbol] = asyncio.Queue()
                
                self.logger.info("file_market_data_provider.subscribed", {
                    "symbol": symbol
                })
            else:
                self.logger.error("file_market_data_provider.subscription_failed", {
                    "symbol": symbol
                })
                raise RuntimeError(f"Failed to subscribe to symbol {symbol}")
    
    async def unsubscribe_from_symbol(self, symbol: str) -> None:
        """Unsubscribe from market data for a specific symbol"""
        if symbol in self._subscribed_symbols:
            # Note: FileConnector doesn't have unsubscribe method
            # For backtest, we just remove from our tracking
            self._subscribed_symbols.discard(symbol)
            if symbol in self._market_data_queues:
                del self._market_data_queues[symbol]
            
            self.logger.info("file_market_data_provider.unsubscribed", {
                "symbol": symbol
            })
    
    async def get_market_data_stream(self, symbol: str) -> AsyncIterator[MarketData]:
        """
        Get real-time market data stream for a symbol.
        Yields MarketData objects as they arrive from file playback.
        """
        if symbol not in self._subscribed_symbols:
            await self.subscribe_to_symbol(symbol)
        
        queue = self._market_data_queues.get(symbol)
        if not queue:
            raise RuntimeError(f"No data queue for symbol {symbol}")
        
        self.logger.info("file_market_data_provider.stream_started", {
            "symbol": symbol
        })
        
        try:
            while True:
                # Wait for market data from the queue
                market_data = await queue.get()
                if market_data is None:  # Sentinel for end of stream
                    break
                yield market_data
        except asyncio.CancelledError:
            self.logger.info("file_market_data_provider.stream_cancelled", {
                "symbol": symbol
            })
            raise
        finally:
            self.logger.info("file_market_data_provider.stream_ended", {
                "symbol": symbol
            })
    
    async def get_latest_price(self, symbol: str) -> Optional[MarketData]:
        """Get the latest price for a symbol"""
        # For file-based provider, this would require maintaining latest state
        # For now, return None as backtest typically uses streaming data
        self.logger.warning("file_market_data_provider.get_latest_price_not_implemented", {
            "symbol": symbol
        })
        return None
    
    async def get_24h_volume(self, symbol: str) -> Optional[float]:
        """Get 24h volume for a symbol in USDT"""
        self.logger.warning("file_market_data_provider.get_24h_volume_not_implemented", {
            "symbol": symbol
        })
        return None
    
    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information (precision, limits, etc.)"""
        self.logger.warning("file_market_data_provider.get_symbol_info_not_implemented", {
            "symbol": symbol
        })
        return None
    
    async def is_symbol_active(self, symbol: str) -> bool:
        """Check if symbol is actively trading"""
        # For file-based provider, symbol is active if we have data for it
        file_path = self.file_connector.data_dir / f"{symbol}.jsonl"
        return file_path.exists()
    
    def get_exchange_name(self) -> str:
        """Get the name of the exchange"""
        return "file"
    
    async def health_check(self) -> bool:
        """Check if connection is healthy"""
        return self.file_connector.connected
    
    async def get_order_book(self, symbol: str, depth: int = 10) -> Optional[Any]:
        """Get order book for a symbol (not implemented for file provider)"""
        self.logger.warning("file_market_data_provider.get_order_book_not_implemented", {
            "symbol": symbol,
            "depth": depth
        })
        return None
    
    async def get_price_history(self, symbol: str, timeframe: str, limit: int = 100) -> List[Any]:
        """Get historical price data (not implemented for file provider)"""
        self.logger.warning("file_market_data_provider.get_price_history_not_implemented", {
            "symbol": symbol,
            "timeframe": timeframe,
            "limit": limit
        })
        return []
    
    async def _handle_price_update(self, event_data: dict):
        """Handle price update events from FileConnector"""
        try:
            symbol = event_data.get('symbol')
            if not symbol or symbol not in self._subscribed_symbols:
                return
            
            # Convert event data to MarketData object
            price_data = event_data.get('data', {})
            
            # Handle timestamp conversion - can be Unix timestamp or ISO string
            timestamp_raw = price_data.get('timestamp')
            self.logger.debug("file_market_data_provider.timestamp_debug", {
                "timestamp_raw": timestamp_raw,
                "timestamp_type": type(timestamp_raw).__name__,
                "symbol": symbol
            })
            
            try:
                # Handle different timestamp formats
                if isinstance(timestamp_raw, (int, float)):
                    # Already a number
                    timestamp = datetime.fromtimestamp(timestamp_raw)
                elif isinstance(timestamp_raw, str):
                    try:
                        # Try Unix timestamp first (numeric string)
                        timestamp_float = float(timestamp_raw)
                        timestamp = datetime.fromtimestamp(timestamp_float)
                    except ValueError:
                        # Fall back to ISO format
                        timestamp = datetime.fromisoformat(timestamp_raw.replace('Z', '+00:00'))
                else:
                    # Fallback to current time
                    timestamp = datetime.now()
                    self.logger.warning("file_market_data_provider.timestamp_fallback", {
                        "timestamp_raw": timestamp_raw,
                        "symbol": symbol
                    })
                
                self.logger.debug("file_market_data_provider.timestamp_converted", {
                    "timestamp_final": timestamp.isoformat(),
                    "symbol": symbol
                })
                
            except Exception as e:
                self.logger.error("file_market_data_provider.timestamp_conversion_error", {
                    "timestamp_raw": timestamp_raw,
                    "error": str(e),
                    "symbol": symbol
                })
                # Use current time as fallback
                timestamp = datetime.now()
            
            market_data = MarketData(
                symbol=symbol,
                exchange="file",  # File-based data source
                price=Decimal(str(price_data.get('price', 0))),
                timestamp=timestamp,
                volume=Decimal(str(price_data.get('volume', 0)))
            )
            
            # Put data in the symbol's queue
            queue = self._market_data_queues.get(symbol)
            if queue:
                await queue.put(market_data)
                
        except Exception as e:
            self.logger.error("file_market_data_provider.price_update_error", {
                "error": str(e),
                "event_data": event_data
            })
    
    async def _handle_stream_ended(self, event_data: dict):
        """Handle end of data stream event"""
        try:
            symbol = event_data.get('symbol')
            if not symbol:
                return
            
            self.logger.info("file_market_data_provider.stream_ending", {
                "symbol": symbol,
                "lines_processed": event_data.get('lines_processed', 0)
            })
            
            # Send sentinel to end the stream
            queue = self._market_data_queues.get(symbol)
            if queue:
                await queue.put(None)  # Sentinel value to end stream
                
        except Exception as e:
            self.logger.error("file_market_data_provider.stream_ended_error", {
                "error": str(e),
                "event_data": event_data
            })
    
    async def shutdown(self):
        """Clean shutdown of the provider"""
        # Signal end of streams
        for queue in self._market_data_queues.values():
            await queue.put(None)  # Sentinel
        
        # Disconnect file connector
        await self.disconnect()
        
        # Unsubscribe from events
        self.event_bus.unsubscribe('market.price_update', self._handle_price_update)
        self.event_bus.unsubscribe('market.data_stream_ended', self._handle_stream_ended)
        
        self.logger.info("file_market_data_provider.shutdown_complete", {})
