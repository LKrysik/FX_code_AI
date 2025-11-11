"""
Execution Data Sources
======================
Implementations of IExecutionDataSource for different execution modes.

✅ REMOVED: Deprecated CSV-based HistoricalDataSource (178 lines of dead code)
✅ STEP 4: QuestDBHistoricalDataSource is the only backtest data source
"""

import asyncio
import os
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from .execution_controller import IExecutionDataSource
from ...core.logger import StructuredLogger
from ...domain.interfaces.market_data import IMarketDataProvider
from ...data.questdb_data_provider import QuestDBDataProvider


class LiveDataSource(IExecutionDataSource):
    """
    Live data source for real-time trading.
    Wraps existing market data provider.
    """
    
    def __init__(self, 
                 market_data_provider: IMarketDataProvider,
                 symbols: List[str],
                 logger: Optional[StructuredLogger] = None):
        self.market_data_provider = market_data_provider
        self.symbols = symbols
        self.logger = logger

        # ✅ MEMORY LEAK FIX: Background task tracking with strong references
        self._background_tasks: set = set()

        # State
        self._is_streaming = False
        self._data_queues: Dict[str, asyncio.Queue] = {}
        self._consumer_tasks: List[asyncio.Task] = []  # Legacy list, use _background_tasks instead
    
    async def start_stream(self) -> None:
        """Start live data streaming"""
        if self._is_streaming:
            return
        
        self._is_streaming = True
        
        # Connect to market data provider
        await self.market_data_provider.connect()
        
        # Create queues for each symbol
        for symbol in self.symbols:
            self._data_queues[symbol] = asyncio.Queue(maxsize=1000)
            await self.market_data_provider.subscribe_to_symbol(symbol)
            
            # Start consumer task for this symbol
            task = asyncio.create_task(self._consume_symbol_data(symbol))
            # ✅ MEMORY LEAK FIX: Track task and auto-cleanup when done
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            self._consumer_tasks.append(task)  # Legacy list for backwards compatibility
        
        if self.logger:
            self.logger.info("live_data.stream_started", {
                "symbols": self.symbols
            })
    
    async def get_next_batch(self) -> Optional[List[Dict[str, Any]]]:
        """Get next batch of live data"""
        if not self._is_streaming:
            return None
        
        batch = []
        
        # Collect data from all symbol queues (non-blocking)
        for symbol, queue in self._data_queues.items():
            try:
                while not queue.empty() and len(batch) < 50:  # Max 50 per batch
                    data = queue.get_nowait()
                    batch.append(data)
                    queue.task_done()
            except asyncio.QueueEmpty:
                continue
        
        # If no data available, wait a bit
        if not batch:
            await asyncio.sleep(0.01)  # 10ms wait
        
        return batch if batch else []
    
    async def stop_stream(self) -> None:
        """Stop live data streaming"""
        self._is_streaming = False

        # ✅ MEMORY LEAK FIX: Cancel all background tasks (prevents dangling task warnings)
        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete or be cancelled
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Clear the task set
        self._background_tasks.clear()
        self._consumer_tasks.clear()  # Also clear legacy list
        
        # Disconnect from market data provider
        try:
            await self.market_data_provider.disconnect()
        except Exception as e:
            if self.logger:
                self.logger.error("live_data.disconnect_error", {
                    "error": str(e)
                })
        
        # Clear queues
        self._data_queues.clear()
        self._consumer_tasks.clear()
        
        if self.logger:
            self.logger.info("live_data.stream_stopped")
    
    def get_progress(self) -> Optional[float]:
        """Live trading has no progress concept"""
        return None
    
    async def _consume_symbol_data(self, symbol: str) -> None:
        """Consume data for a specific symbol and normalize format for pipeline"""
        try:
            # Lazy import to avoid circulars for tests
            try:
                from ...domain.models.market_data import MarketData, OrderBook
            except Exception:
                MarketData = None  # type: ignore
                OrderBook = None   # type: ignore

            async for market_data in self.market_data_provider.get_market_data_stream(symbol):
                if not self._is_streaming:
                    break
                
                # Normalize to dict expected by execution pipeline
                payload = market_data
                try:
                    if MarketData is not None and isinstance(market_data, MarketData):
                        payload = {
                            'symbol': str(market_data.symbol).upper(),
                            'timestamp': getattr(market_data, 'timestamp', None),
                            'price': float(getattr(market_data, 'price', 0) or 0),
                            'volume': float(getattr(market_data, 'volume', 0) or 0),
                            'quote_volume': float(getattr(market_data, 'quote_volume', getattr(market_data, 'price', 0) * getattr(market_data, 'volume', 0)) or 0),
                            'exchange': getattr(market_data, 'exchange', 'mexc') or 'mexc',
                        }
                    elif OrderBook is not None and isinstance(market_data, OrderBook):
                        # Convert order book levels to [[price, qty], ...] with None safety
                        bids = [[float(l.price), float(l.quantity)] for l in (market_data.bids or []) if l is not None]
                        asks = [[float(l.price), float(l.quantity)] for l in (market_data.asks or []) if l is not None]
                        payload = {
                            'symbol': str(market_data.symbol).upper(),
                            'timestamp': getattr(market_data, 'timestamp', None),
                            'bids': bids,
                            'asks': asks,
                            'exchange': getattr(market_data, 'exchange', 'mexc') or 'mexc',
                        }
                except Exception:
                    # If normalization fails, fall back to raw
                    payload = market_data

                # Add to queue for batch processing
                try:
                    await self._data_queues[symbol].put(payload)
                except asyncio.QueueFull:
                    # Drop oldest data if queue is full
                    try:
                        self._data_queues[symbol].get_nowait()
                        await self._data_queues[symbol].put(payload)
                    except asyncio.QueueEmpty:
                        pass
                    
                    if self.logger:
                        self.logger.warning("live_data.queue_full", {
                            "symbol": symbol
                        })
        
        except asyncio.CancelledError:
            return
        except Exception as e:
            if self.logger:
                self.logger.error("live_data.consumer_error", {
                    "symbol": symbol,
                    "error": str(e)
                })


class QuestDBHistoricalDataSource(IExecutionDataSource):
    """
    Historical data source for backtesting using QuestDB.
    
    Replays tick_prices from specific data collection session with:
    - Time acceleration support
    - Batch reading for performance
    - Progress tracking
    - Multi-symbol support
    
    ✅ STEP 4: New implementation for QuestDB-based backtest
    """
    
    def __init__(
        self,
        session_id: str,
        symbols: List[str],
        db_provider: QuestDBDataProvider,
        event_bus,
        execution_controller,
        acceleration_factor: float = 1.0,
        batch_size: int = 100,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize QuestDB historical data source.

        Args:
            session_id: Data collection session ID to replay
            symbols: List of trading symbols to backtest
            db_provider: QuestDB data provider for queries
            event_bus: EventBus for publishing market data events
            execution_controller: ExecutionController for direct buffer writes
            acceleration_factor: Time acceleration (1.0 = realtime, 10.0 = 10x speed)
            batch_size: Number of records to fetch per batch
            logger: Optional structured logger
        """
        self.session_id = session_id
        self.symbols = list(symbols)  # Make a copy
        self.db_provider = db_provider
        self.event_bus = event_bus
        self.execution_controller = execution_controller
        self.acceleration_factor = acceleration_factor
        self.batch_size = batch_size
        self.logger = logger

        # ✅ MEMORY LEAK FIX: Background task tracking with strong references
        self._background_tasks: set = set()

        # State tracking
        self._cursors: Dict[str, int] = {}  # symbol -> current offset
        self._total_rows: Dict[str, int] = {}  # symbol -> total row count
        self._is_streaming = False
        self._exhausted_symbols: set = set()
        self._replay_task: Optional[asyncio.Task] = None
        
    async def start_stream(self) -> None:
        """Initialize streaming from QuestDB and start replay task"""
        if self._is_streaming:
            return

        self._is_streaming = True

        # Count total rows for each symbol (for progress tracking)
        for symbol in self.symbols:
            try:
                count = await self.db_provider.count_records(
                    session_id=self.session_id,
                    symbol=symbol,
                    data_type='prices'
                )

                self._total_rows[symbol] = count
                self._cursors[symbol] = 0

                if self.logger:
                    self.logger.info("questdb_historical.stream_started", {
                        "session_id": self.session_id,
                        "symbol": symbol,
                        "total_rows": count
                    })

            except Exception as e:
                if self.logger:
                    self.logger.error("questdb_historical.count_failed", {
                        "session_id": self.session_id,
                        "symbol": symbol,
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                # Mark as exhausted if count fails
                self._exhausted_symbols.add(symbol)

        # ✅ NEW: Start background replay task
        self._replay_task = asyncio.create_task(self._replay_historical_data())
        # ✅ MEMORY LEAK FIX: Track task and auto-cleanup when done
        self._background_tasks.add(self._replay_task)
        self._replay_task.add_done_callback(self._background_tasks.discard)

    async def _replay_historical_data(self):
        """
        Replay historical data as EventBus events.

        Reads batches from QuestDB and publishes to EventBus,
        simulating live market data for backtesting.
        """
        try:
            while self._is_streaming:
                # Fetch next batch using existing logic
                batch = await self._fetch_next_batch()

                if not batch:
                    # End of historical data
                    if self.logger:
                        self.logger.info("questdb_historical.replay_complete", {
                            "session_id": self.session_id,
                            "total_processed": sum(self._cursors.values())
                        })
                    break

                # Publish each tick to EventBus (same as live data)
                for tick in batch:
                    if not self._is_streaming:
                        break

                    # Publish to EventBus for indicators/strategies
                    if self.event_bus:
                        await self.event_bus.publish("market.price_update", {
                            "symbol": tick["symbol"],
                            "price": tick["price"],
                            "volume": tick["volume"],
                            "quote_volume": tick.get("quote_volume", 0.0),
                            "timestamp": tick["timestamp"],
                            "exchange": "questdb_backtest",
                            "source": "backtest",
                            "metadata": tick.get("metadata", {})
                        })

                    # Write to execution_controller buffer (for CSV/persistence)
                    if self.execution_controller:
                        await self.execution_controller._save_data_to_files({
                            "event_type": "price",
                            "symbol": tick["symbol"],
                            "price": tick["price"],
                            "volume": tick["volume"],
                            "quote_volume": tick.get("quote_volume", 0.0),
                            "timestamp": tick["timestamp"],
                            "source": "backtest"
                        })

                    # Apply acceleration delay
                    if self.acceleration_factor > 0:
                        delay = (10.0 / max(1.0, self.acceleration_factor)) / 1000.0
                        await asyncio.sleep(delay)

        except asyncio.CancelledError:
            if self.logger:
                self.logger.info("questdb_historical.replay_cancelled", {
                    "session_id": self.session_id
                })
            raise
        except Exception as e:
            if self.logger:
                self.logger.error("questdb_historical.replay_failed", {
                    "session_id": self.session_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                })

    async def _fetch_next_batch(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch next batch of data from QuestDB.
        
        Returns:
            List of market data dictionaries or None if stream ended
        """
        if not self._is_streaming:
            return None
        
        # Check if all symbols are exhausted
        if len(self._exhausted_symbols) >= len(self.symbols):
            return None
        
        batch = []
        
        # Read from all active symbols in round-robin fashion
        for symbol in list(self.symbols):
            if symbol in self._exhausted_symbols:
                continue
            
            if len(batch) >= self.batch_size:
                break
            
            offset = self._cursors.get(symbol, 0)
            
            try:
                # Query next batch for this symbol
                rows = await self.db_provider.get_tick_prices(
                    session_id=self.session_id,
                    symbol=symbol,
                    limit=self.batch_size - len(batch),
                    offset=offset
                )
                
                if not rows:
                    # Symbol exhausted
                    self._exhausted_symbols.add(symbol)
                    
                    if self.logger:
                        self.logger.info("questdb_historical.symbol_exhausted", {
                            "session_id": self.session_id,
                            "symbol": symbol,
                            "rows_processed": offset
                        })
                    continue
                
                # Convert to market data format
                for row in rows:
                    market_data = {
                        "symbol": symbol,
                        "timestamp": row.get('timestamp'),
                        "price": float(row.get('price', 0)),
                        "volume": float(row.get('volume', 0)),
                        "quote_volume": float(row.get('quote_volume', 0)),
                        "source": "questdb_historical",
                        "metadata": {
                            "session_id": self.session_id,
                            "acceleration_factor": self.acceleration_factor,
                            "batch_offset": offset
                        }
                    }
                    batch.append(market_data)
                
                # Update cursor
                self._cursors[symbol] = offset + len(rows)
                
            except Exception as e:
                if self.logger:
                    self.logger.error("questdb_historical.batch_read_failed", {
                        "session_id": self.session_id,
                        "symbol": symbol,
                        "offset": offset,
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                
                # Mark symbol as exhausted on error
                self._exhausted_symbols.add(symbol)
        
        # No data available
        if not batch:
            return None

        return batch
    
    async def stop_stream(self) -> None:
        """Stop streaming and cancel all background tasks"""
        self._is_streaming = False

        # ✅ MEMORY LEAK FIX: Cancel all background tasks (prevents dangling task warnings)
        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete or be cancelled
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Clear the task set
        self._background_tasks.clear()
        self._replay_task = None

        if self.logger:
            total_processed = sum(self._cursors.values())
            total_available = sum(self._total_rows.values())

            self.logger.info("questdb_historical.stream_stopped", {
                "session_id": self.session_id,
                "total_processed": total_processed,
                "total_available": total_available,
                "symbols_completed": len(self._exhausted_symbols)
            })
    
    def get_progress(self) -> Optional[float]:
        """
        Calculate backtest progress percentage.
        
        Returns:
            Progress as percentage (0.0 - 100.0) or None
        """
        total_available = sum(self._total_rows.values())
        
        if total_available == 0:
            return 0.0
        
        total_processed = sum(self._cursors.values())
        
        progress = (total_processed / total_available) * 100.0
        return min(100.0, progress)
