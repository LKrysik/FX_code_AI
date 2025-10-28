"""
File-based Exchange Connector
==============================
Reads market data from JSONL files and simulates live exchange data.
Used for testing and backtesting with historical data.
"""

import asyncio
import json
import csv
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass

from ..core.event_bus import EventBus
from ..core.logger import StructuredLogger
from ..core.events import PriceEvent
from ..exchanges.base import ExchangeConnector


@dataclass
class FileExchangeConfig:
    """Extended configuration for file-based exchange"""
    enabled: bool
    path: str  # Directory containing JSONL files
    playback_speed: float = 1.0  # 1.0 = real-time, 2.0 = 2x speed, etc.
    loop: bool = False  # Whether to loop the data when reaching the end
    start_from_beginning: bool = True  # Start from first event or continue from last position


class FileConnector(ExchangeConnector):
    """
    Exchange connector that reads from CSV/JSONL files instead of live WebSocket.

    ⚠️ LEGACY: This connector is maintained for external data import only.

    🔄 MIGRATION NOTE (2025-10-28):
    For backtesting with internal data, use QuestDBHistoricalDataSource instead.

    Use cases for FileConnector:
    - Importing external market data from CSV files
    - Replaying historical data from third-party sources
    - Testing with custom datasets

    Features:
    - Reads market data from CSV/JSONL files
    - Simulates real-time playback based on timestamps
    - Supports variable playback speed
    - Can loop data for continuous testing

    Recommended alternative: QuestDBHistoricalDataSource (10x faster, better reliability)
    """
    
    def __init__(
        self,
        config: Dict,
        event_bus: EventBus,
        logger: StructuredLogger
    ):
        self.config = FileExchangeConfig(
            enabled=config.get('enabled', True),
            path=config.get('path', 'logs/market_data/'),
            playback_speed=config.get('playback_speed', 1.0),
            loop=config.get('loop', False),
            start_from_beginning=config.get('start_from_beginning', True)
        )
        self.event_bus = event_bus
        self.logger = logger
        
        # Connection state
        self.connected = False
        self.subscribed_symbols: Set[str] = set()
        
        # Playback control
        self.playback_tasks: Dict[str, asyncio.Task] = {}
        self.stop_event = asyncio.Event()
        
        # File handles and positions
        self.file_handles: Dict[str, any] = {}
        self.file_positions: Dict[str, int] = {}  # Track line number for each file
        
        # Ensure data directory exists
        self.data_dir = Path(self.config.path)
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.logger.warning("file_connector.data_dir_created", {
                "path": str(self.data_dir)
            })
        
        self.logger.info("file_connector.initialized", {
            "data_directory": str(self.data_dir),
            "playback_speed": self.config.playback_speed,
            "loop": self.config.loop
        })
    
    async def connect(self) -> bool:
        """Simulate connection to exchange"""
        if self.connected:
            return True
        
        self.connected = True
        self.stop_event.clear()
        
        self.logger.info("file_connector.connected", {
            "data_source": str(self.data_dir)
        })
        
        return True
    
    async def disconnect(self) -> None:
        """Disconnect and stop all playback tasks"""
        if not self.connected:
            return
        
        self.connected = False
        self.stop_event.set()
        
        # Cancel all playback tasks
        for symbol, task in self.playback_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.playback_tasks.clear()
        
        # Close all file handles
        for handle in self.file_handles.values():
            handle.close()
        self.file_handles.clear()
        
        self.logger.info("file_connector.disconnected", {})
    
    async def subscribe_symbol(self, symbol: str, **kwargs) -> bool:
        """Subscribe to a symbol by starting playback from its data file"""
        if not self.connected:
            self.logger.error("file_connector.subscribe.not_connected", {
                "symbol": symbol
            })
            return False
        
        if symbol in self.subscribed_symbols:
            self.logger.warning("file_connector.already_subscribed", {
                "symbol": symbol
            })
            return True
        
        # Check if data file exists (JSONL or CSV)
        jsonl_path = self.data_dir / f"{symbol}.jsonl"
        csv_path = self.data_dir / symbol / f"data_{kwargs.get('session', '')}" / f"{symbol}_{kwargs.get('session', '')}.csv"
        
        file_path = None
        orderbook_path = None
        file_type = None
        
        if jsonl_path.exists():
            file_path = jsonl_path
            file_type = "jsonl"
        elif csv_path.exists():
            file_path = csv_path
            file_type = "csv"
            # Look for corresponding orderbook file
            orderbook_path = csv_path.parent / f"{csv_path.stem}_orderbook.csv"
        else:
            # Try alternative CSV paths - prefer extended files
            for dir_name in (self.data_dir / symbol).iterdir():
                if dir_name.is_dir():
                    # First try to find extended files
                    extended_file = None
                    extended_orderbook = None
                    regular_file = None
                    regular_orderbook = None
                    
                    for file in dir_name.iterdir():
                        if file.name.startswith(symbol) and file.suffix == '.csv':
                            if 'extended' in file.name and 'orderbook' not in file.name:
                                extended_file = file
                            elif 'extended' in file.name and 'orderbook' in file.name:
                                extended_orderbook = file
                            elif 'orderbook' not in file.name:
                                regular_file = file
                            elif 'orderbook' in file.name:
                                regular_orderbook = file
                    
                    # Prefer extended files if available
                    if extended_file:
                        file_path = extended_file
                        orderbook_path = extended_orderbook
                        file_type = "csv"
                        break
                    elif regular_file:
                        file_path = regular_file
                        orderbook_path = regular_orderbook
                        file_type = "csv"
                        break
        
        if not file_path:
            self.logger.error("file_connector.data_file_not_found", {
                "symbol": symbol,
                "jsonl_path": str(jsonl_path),
                "csv_path": str(csv_path)
            })
            return False
        
        # Check if orderbook file exists for CSV data
        if file_type == "csv" and orderbook_path and not orderbook_path.exists():
            self.logger.warning("file_connector.orderbook_file_not_found", {
                "symbol": symbol,
                "orderbook_path": str(orderbook_path),
                "message": "Will calculate liquidity from volume data"
            })
            orderbook_path = None
        
        # Add to subscribed symbols
        self.subscribed_symbols.add(symbol)
        
        # Start playback task for this symbol
        task = asyncio.create_task(self._playback_symbol(symbol, file_path, file_type, orderbook_path))
        self.playback_tasks[symbol] = task
        
        self.logger.info("file_connector.subscribed", {
            "symbol": symbol,
            "file_path": str(file_path),
            "orderbook_path": str(orderbook_path) if orderbook_path else None,
            "file_type": file_type
        })
        
        return True
    
    def is_connected(self) -> bool:
        """Check connection status"""
        return self.connected
    
    async def _playback_symbol(self, symbol: str, file_path: Path, file_type: str, orderbook_path: Optional[Path] = None):
        """
        Playback data for a specific symbol from its file.
        Simulates real-time data based on timestamps.
        Supports both JSONL and CSV formats with optional orderbook data.
        """
        try:
            if file_type == "csv":
                await self._playback_csv(symbol, file_path, orderbook_path)
            else:
                await self._playback_jsonl(symbol, file_path)
        except Exception as e:
            self.logger.error("file_connector.playback_error", {
                "symbol": symbol,
                "file_path": str(file_path),
                "file_type": file_type,
                "error": str(e)
            })
        finally:
            # Remove from subscribed symbols
            self.subscribed_symbols.discard(symbol)
            if symbol in self.playback_tasks:
                del self.playback_tasks[symbol]
    
    async def _playback_csv(self, symbol: str, file_path: Path, orderbook_path: Optional[Path] = None):
        """Playback CSV data with optional orderbook for liquidity calculation"""
        self.logger.info("file_connector.csv_playback_started", {
            "symbol": symbol,
            "file_path": str(file_path),
            "orderbook_path": str(orderbook_path) if orderbook_path else None
        })
        
        # Load orderbook data if available
        orderbook_data = {}
        if orderbook_path and orderbook_path.exists():
            self.logger.info("file_connector.loading_orderbook", {
                "symbol": symbol,
                "orderbook_path": str(orderbook_path)
            })
            
            with open(orderbook_path, 'r', encoding='utf-8') as ob_file:
                ob_reader = csv.DictReader(ob_file)
                for ob_row in ob_reader:
                    try:
                        timestamp_key = float(ob_row['timestamp'])
                        orderbook_data[timestamp_key] = {
                            'best_bid': float(ob_row['best_bid']),
                            'best_ask': float(ob_row['best_ask']),
                            'bid_qty': float(ob_row['bid_qty']),
                            'ask_qty': float(ob_row['ask_qty']),
                            'spread': float(ob_row['spread'])
                        }
                    except (ValueError, KeyError) as e:
                        self.logger.error("file_connector.orderbook_parse_error", {
                            "symbol": symbol,
                            "error": str(e),
                            "row": ob_row
                        })
                        continue
            
            self.logger.info("file_connector.orderbook_loaded", {
                "symbol": symbol,
                "entries": len(orderbook_data)
            })
        
        # Playback price data
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            last_timestamp = None
            line_number = 0
            
            for row in reader:
                if self.stop_event.is_set():
                    break
                
                line_number += 1
                
                self.logger.debug("file_connector.csv_row_read", {
                    "symbol": symbol,
                    "line_number": line_number,
                    "row": row
                })
                
                try:
                    # Convert timestamp from string to float
                    timestamp = float(row['timestamp'])
                    
                    # Calculate delay to simulate real-time
                    if last_timestamp is not None:
                        delay = (timestamp - last_timestamp) / self.config.playback_speed
                        if delay > 0:
                            self.logger.debug("file_connector.playback_delay", {
                                "symbol": symbol,
                                "delay": delay,
                                "playback_speed": self.config.playback_speed
                            })
                            await asyncio.sleep(delay)
                    
                    last_timestamp = timestamp
                    
                    # Calculate liquidity from orderbook data
                    liquidity_usdt = 0.0
                    if timestamp in orderbook_data:
                        ob_data = orderbook_data[timestamp]
                        # Calculate liquidity as bid_qty * best_bid + ask_qty * best_ask
                        liquidity_usdt = (
                            ob_data['bid_qty'] * ob_data['best_bid'] +
                            ob_data['ask_qty'] * ob_data['best_ask']
                        )
                        
                        self.logger.debug("file_connector.liquidity_calculated", {
                            "symbol": symbol,
                            "timestamp": timestamp,
                            "liquidity_usdt": liquidity_usdt,
                            "best_bid": ob_data['best_bid'],
                            "best_ask": ob_data['best_ask'],
                            "bid_qty": ob_data['bid_qty'],
                            "ask_qty": ob_data['ask_qty']
                        })
                    else:
                        # Fallback: estimate liquidity from volume
                        price = float(row['price'])
                        volume = float(row['volume'])
                        liquidity_usdt = price * volume * 10  # Conservative multiplier
                        
                        self.logger.debug("file_connector.liquidity_estimated", {
                            "symbol": symbol,
                            "timestamp": timestamp,
                            "liquidity_usdt": liquidity_usdt,
                            "price": price,
                            "volume": volume
                        })
                    
                    # Create event data for market.price_update
                    event_data = {
                        'symbol': symbol,
                        'data': {
                            'symbol': symbol,
                            'price': float(row['price']),
                            'volume': float(row['volume']),
                            'timestamp': f"{timestamp:.3f}",  # Keep original format
                            'exchange': row.get('exchange', 'file'),
                            'market_type': row.get('market_type', 'spot'),
                            'liquidity_usdt': liquidity_usdt  # Add calculated liquidity
                        }
                    }
                    
                    self.logger.debug("file_connector.publishing_event", {
                        "symbol": symbol,
                        "event_data": event_data
                    })
                    
                    # Publish event using expected format
                    await self.event_bus.publish("market.price_update", event_data)
                    
                except (ValueError, KeyError) as e:
                    self.logger.error("file_connector.csv_parse_error", {
                        "symbol": symbol,
                        "line_number": line_number,
                        "error": str(e),
                        "row": row
                    })
                    continue
        
        self.logger.info("file_connector.csv_playback_completed", {
            "symbol": symbol,
            "lines_processed": line_number
        })
        
        # Notify end of data stream
        await self.event_bus.publish("market.data_stream_ended", {
            "symbol": symbol,
            "lines_processed": line_number,
            "source": "file_connector"
        })
    
    async def _playback_jsonl(self, symbol: str, file_path: Path):
        """Playback JSONL data (original implementation)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            # Skip to saved position if not starting from beginning
            if not self.config.start_from_beginning and symbol in self.file_positions:
                for _ in range(self.file_positions.get(symbol, 0)):
                    f.readline()
            
            last_timestamp = None
            line_number = self.file_positions.get(symbol, 0)
            
            while not self.stop_event.is_set():
                line = f.readline()
                
                # Check if we've reached the end of file
                if not line:
                    if self.config.loop:
                        # Reset to beginning of file
                        f.seek(0)
                        line_number = 0
                        last_timestamp = None
                        self.logger.info("file_connector.looping", {
                            "symbol": symbol
                        })
                        continue
                    else:
                        # End of data
                        self.logger.info("file_connector.end_of_data", {
                            "symbol": symbol,
                            "lines_processed": line_number
                        })
                        break
                
                line_number += 1
                
                try:
                    # Parse JSON data
                    data = json.loads(line.strip())
                    
                    # Calculate delay to simulate real-time
                    current_timestamp = data['timestamp']
                    if last_timestamp is not None:
                        delay = (current_timestamp - last_timestamp) / self.config.playback_speed
                        if delay > 0:
                            await asyncio.sleep(delay)
                    
                    last_timestamp = current_timestamp
                    
                    # Create PriceEvent from data
                    price_event = PriceEvent(
                        exchange=data.get('exchange', 'file'),
                        symbol=data['symbol'],
                        price=data['price'],
                        volume=data['volume'],
                        timestamp_exchange=data.get('timestamp_exchange'),
                        timestamp_local=data['timestamp'],
                        source=data.get('source', 'file'),
                        market_type=data.get('market_type')
                    )
                    
                    # Publish event
                    await self.event_bus.publish("price_update", price_event)
                    
                    # Save position periodically
                    if line_number % 100 == 0:
                        self.file_positions[symbol] = line_number
                    
                except json.JSONDecodeError as e:
                    self.logger.error("file_connector.json_decode_error", {
                        "symbol": symbol,
                        "line_number": line_number,
                        "error": str(e)
                    })
                    continue
                except KeyError as e:
                    self.logger.error("file_connector.missing_field", {
                        "symbol": symbol,
                        "line_number": line_number,
                        "missing_field": str(e)
                    })
                    continue
                except Exception as e:
                    self.logger.error("file_connector.playback_error", {
                        "symbol": symbol,
                        "line_number": line_number,
                        "error": str(e)
                    }, exc_info=True)
                    continue
    
    def get_statistics(self) -> Dict:
        """Get current connector statistics"""
        return {
            "connected": self.connected,
            "data_directory": str(self.data_dir),
            "playback_speed": self.config.playback_speed,
            "loop_enabled": self.config.loop,
            "subscribed_symbols": list(self.subscribed_symbols),
            "active_playbacks": list(self.playback_tasks.keys()),
            "file_positions": dict(self.file_positions)
        }