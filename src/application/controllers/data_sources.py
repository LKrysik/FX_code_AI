"""
Execution Data Sources
======================
Implementations of IExecutionDataSource for different execution modes.
"""

import asyncio
import csv
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from .execution_controller import IExecutionDataSource
from ...core.logger import StructuredLogger
from ...domain.interfaces.market_data import IMarketDataProvider


class HistoricalDataSource(IExecutionDataSource):
    """
    Historical data source for backtesting.
    Replays CSV files with time acceleration.
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
