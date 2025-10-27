"""
Execution Data Sources
======================
Implementations of IExecutionDataSource for different execution modes.

✅ STEP 4: Added QuestDBHistoricalDataSource for backtest using QuestDB
"""

import asyncio
import csv
import os
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from .execution_controller import IExecutionDataSource
from ...core.logger import StructuredLogger
from ...domain.interfaces.market_data import IMarketDataProvider
from ...data.questdb_data_provider import QuestDBDataProvider


class HistoricalDataSource(IExecutionDataSource):
    """
    Historical data source for backtesting using CSV files.

    ⚠️ DEPRECATED: This class is deprecated and will be removed in a future version.
    Use QuestDBHistoricalDataSource instead for QuestDB-based backtest.

    CSV-based backtest is no longer supported as all data now goes to QuestDB.
    This class remains for backward compatibility only.
    """
    
    def __init__(self, 
                 data_path: str,
                 symbols: List[str],
                 acceleration_factor: float = 1.0,
                 batch_size: int = 100,
                 logger: Optional[StructuredLogger] = None):
        self.data_path = Path(data_path)
        self.symbols = symbols
        self.acceleration_factor = acceleration_factor
        self.batch_size = batch_size
        self.logger = logger
        
        # State
        self._data_files: Dict[str, Path] = {}
        self._csv_readers: Dict[str, csv.DictReader] = {}
        self._file_handles: Dict[str, Any] = {}
        self._total_rows = 0
        self._processed_rows = 0
        self._is_streaming = False
        
    async def start_stream(self) -> None:
        """Initialize CSV readers for all symbols"""
        if self._is_streaming:
            return
        
        self._is_streaming = True
        
        # Find data files for each symbol
        for symbol in self.symbols:
            symbol_dir = self.data_path / symbol
            if not symbol_dir.exists():
                if self.logger:
                    self.logger.warning("historical_data.symbol_dir_not_found", {
                        "symbol": symbol,
                        "path": str(symbol_dir)
                    })
                continue
            
            # Find latest data file
            price_files = list(symbol_dir.glob("*/*_prices.csv"))
            if not price_files:
                if self.logger:
                    self.logger.warning("historical_data.no_price_files", {
                        "symbol": symbol,
                        "path": str(symbol_dir)
                    })
                continue
            
            # Use most recent file
            latest_file = max(price_files, key=lambda f: f.stat().st_mtime)
            self._data_files[symbol] = latest_file
            
            # Open CSV reader
            file_handle = open(latest_file, 'r', encoding='utf-8')
            csv_reader = csv.DictReader(file_handle)
            
            self._file_handles[symbol] = file_handle
            self._csv_readers[symbol] = csv_reader
            
            # Count total rows for progress
            file_handle.seek(0)
            row_count = sum(1 for _ in csv_reader) - 1  # Subtract header
            self._total_rows += row_count
            file_handle.seek(0)
            next(csv_reader)  # Skip header again
            
            if self.logger:
                self.logger.info("historical_data.file_loaded", {
                    "symbol": symbol,
                    "file": str(latest_file),
                    "rows": row_count
                })
        
        if self.logger:
            self.logger.info("historical_data.stream_started", {
                "symbols": len(self._csv_readers),
                "total_rows": self._total_rows,
                "acceleration_factor": self.acceleration_factor
            })
    
    async def get_next_batch(self) -> Optional[List[Dict[str, Any]]]:
        """Get next batch of historical data"""
        if not self._is_streaming or not self._csv_readers:
            return None
        
        batch = []
        batch_count = 0
        
        # Read from all symbols in round-robin fashion
        for symbol, reader in list(self._csv_readers.items()):
            if batch_count >= self.batch_size:
                break
            
            try:
                row = next(reader)
                
                # Convert to market data format
                price_value = float(row.get("price", 0) or 0)
                volume_value = float(row.get("volume", 0) or 0)
                quote_value_raw = row.get("quote_volume")
                quote_volume = None
                if quote_value_raw not in (None, "", 'None'):
                    try:
                        quote_volume = float(quote_value_raw)
                    except (TypeError, ValueError):
                        quote_volume = None
                if quote_volume is None:
                    quote_volume = price_value * volume_value
                market_data = {
                    "symbol": symbol,
                    "timestamp": row.get("timestamp"),
                    "price": price_value,
                    "volume": volume_value,
                    "quote_volume": quote_volume,
                    "source": "historical",
                    "metadata": {
                        "file": str(self._data_files[symbol]),
                        "acceleration_factor": self.acceleration_factor
                    }
                }
                
                batch.append(market_data)
                batch_count += 1
                self._processed_rows += 1
                
            except StopIteration:
                # This symbol's data is exhausted
                self._file_handles[symbol].close()
                del self._csv_readers[symbol]
                del self._file_handles[symbol]
                
                if self.logger:
                    self.logger.info("historical_data.symbol_completed", {
                        "symbol": symbol
                    })
        
        # Apply time acceleration delay
        if batch and self.acceleration_factor > 0:
            delay = (1.0 / self.acceleration_factor) * 0.001  # Base delay of 1ms
            await asyncio.sleep(delay)
        
        return batch if batch else None
    
    async def stop_stream(self) -> None:
        """Stop streaming and cleanup resources"""
        self._is_streaming = False
        
        # Close all file handles
        for handle in self._file_handles.values():
            try:
                handle.close()
            except Exception as e:
                if self.logger:
                    self.logger.error("historical_data.file_close_error", {
                        "error": str(e)
                    })
        
        self._csv_readers.clear()
        self._file_handles.clear()
        
        if self.logger:
            self.logger.info("historical_data.stream_stopped", {
                "processed_rows": self._processed_rows,
                "total_rows": self._total_rows
            })
    
    def get_progress(self) -> Optional[float]:
        """Get backtest progress percentage"""
        if self._total_rows == 0:
            return 0.0
        
        return min(100.0, (self._processed_rows / self._total_rows) * 100.0)


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
        
        # State
        self._is_streaming = False
        self._data_queues: Dict[str, asyncio.Queue] = {}
        self._consumer_tasks: List[asyncio.Task] = []
    
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
            self._consumer_tasks.append(task)
        
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
        
        # Cancel consumer tasks
        for task in self._consumer_tasks:
            if not task.done():
                task.cancel()
        
        if self._consumer_tasks:
            await asyncio.gather(*self._consumer_tasks, return_exceptions=True)
        
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
            acceleration_factor: Time acceleration (1.0 = realtime, 10.0 = 10x speed)
            batch_size: Number of records to fetch per batch
            logger: Optional structured logger
        """
        self.session_id = session_id
        self.symbols = list(symbols)  # Make a copy
        self.db_provider = db_provider
        self.acceleration_factor = acceleration_factor
        self.batch_size = batch_size
        self.logger = logger
        
        # State tracking
        self._cursors: Dict[str, int] = {}  # symbol -> current offset
        self._total_rows: Dict[str, int] = {}  # symbol -> total row count
        self._is_streaming = False
        self._exhausted_symbols: set = set()
        
    async def start_stream(self) -> None:
        """Initialize streaming from QuestDB"""
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
    
    async def get_next_batch(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get next batch of market data from QuestDB.
        
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
        
        # Apply time acceleration delay
        if self.acceleration_factor > 0:
            # Calculate delay based on acceleration factor
            # Base delay of 10ms, scaled by acceleration
            delay = (10.0 / max(1.0, self.acceleration_factor)) / 1000.0
            await asyncio.sleep(delay)
        
        return batch
    
    async def stop_stream(self) -> None:
        """Stop streaming"""
        self._is_streaming = False
        
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
