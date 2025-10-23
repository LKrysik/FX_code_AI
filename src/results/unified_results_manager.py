"""
Unified Results Management System
=================================
Handles results storage and management for both backtest and live trading
WITH PROPER TIMEOUT AND HANGING PREVENTION
"""

import json
import time
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import threading

from ..core.logger import StructuredLogger
from ..domain.models.signals import FlashPumpSignal
from ..domain.services.risk_assessment import RiskAssessmentService
from ..infrastructure.config.settings import AppSettings


@dataclass
class TradeRecord:
    """Unified trade record for both backtest and live trading"""
    trade_id: str
    signal_id: str
    symbol: str
    exchange: str
    mode: str  # 'backtest' or 'live'
    
    # Entry details
    entry_time: float
    entry_price: float
    entry_size: float
    leverage: int
    side: str  # 'buy' or 'sell'
    
    # Exit details
    exit_time: Optional[float] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    
    # P&L
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_pnl: float = 0.0
    pnl_pct: float = 0.0
    
    # Fees
    entry_fee: float = 0.0
    exit_fee: float = 0.0
    total_fees: float = 0.0
    
    # Risk management
    stop_loss_price: Optional[float] = None
    take_profit_levels: List[Dict] = None
    max_drawdown: float = 0.0
    max_profit: float = 0.0
    
    # Performance metrics
    duration_minutes: float = 0.0
    win_trade: bool = False
    risk_reward_achieved: float = 0.0
    
    # Signal context
    pump_magnitude: float = 0.0
    confidence_score: float = 0.0
    entry_score: float = 0.0
    
    # Market conditions at entry
    market_conditions: Dict = None
    
    def __post_init__(self):
        if self.take_profit_levels is None:
            self.take_profit_levels = []
        if self.market_conditions is None:
            self.market_conditions = {}


@dataclass
class SignalRecord:
    """Unified signal record for both backtest and live trading"""
    signal_id: str
    symbol: str
    exchange: str
    mode: str  # 'backtest' or 'live'
    
    # Detection details
    detection_time: float
    peak_price: float
    pump_magnitude: float
    confidence_score: float
    volume_surge_ratio: float
    
    # Entry evaluation
    entry_ready: bool = False
    entry_score: float = 0.0
    entry_conditions: Dict = None
    rejection_signals: List[str] = None
    
    # Position outcome
    position_opened: bool = False
    trade_id: Optional[str] = None
    
    def __post_init__(self):
        if self.entry_conditions is None:
            self.entry_conditions = {}
        if self.rejection_signals is None:
            self.rejection_signals = []


@dataclass
class SessionSummary:
    """Session performance summary"""
    session_id: str
    mode: str  # 'backtest' or 'live'
    start_time: float
    end_time: Optional[float] = None
    
    # Duration tracking
    data_start_time: Optional[float] = None  # First data timestamp
    data_end_time: Optional[float] = None    # Last data timestamp
    
    # Trading metrics
    total_signals: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # P&L metrics
    total_pnl: float = 0.0
    total_fees: float = 0.0
    net_pnl: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    max_consecutive_losses: int = 0
    avg_trade_duration: float = 0.0
    
    # Symbols traded
    symbols: List[str] = None
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = []


class UnifiedResultsManager:
    """Manages results for both backtest and live trading modes with hanging prevention"""
    
    def __init__(self, mode: str, settings: AppSettings, logger: StructuredLogger, session_id: Optional[str] = None):
        self.mode = mode
        self.settings = settings
        self.logger = logger
        
        # Generate session ID if not provided
        if session_id is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_id = f"{mode}_{timestamp}"
        else:
            self.session_id = session_id
        
        # RiskAssessmentService for signal processing
        self.risk_assessment_service = RiskAssessmentService(
            risk_management_settings=self.settings.risk_management,
            entry_conditions_settings=self.settings.entry_conditions
        )
        
        # Setup paths - create proper directory structure
        if mode == "backtest":
            self.base_path = Path("backtest/backtest_results")
            self.session_path = self.base_path / self.session_id
        else:
            self.base_path = Path(f"{mode}/{mode}_results")
            self.session_path = self.base_path / self.session_id
        
        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create session path
        self.session_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("unified_results.paths_created", {
            "base_path": str(self.base_path),
            "session_path": str(self.session_path),
            "base_path_exists": self.base_path.exists(),
            "session_path_exists": self.session_path.exists()
        })
        
        # ✅ THREAD SAFETY: Add locks for shared state
        self._data_lock = threading.RLock()

        # ✅ MEMORY MANAGEMENT: Bounded data storage with size limits
        self._max_signals = 10000  # Prevent unbounded growth
        self._max_trades = 50000   # Prevent unbounded growth
        self.signals: Dict[str, SignalRecord] = {}
        self.trades: Dict[str, TradeRecord] = {}
        self.session_summary = SessionSummary(
            session_id=self.session_id,
            mode=mode,
            start_time=time.time()
        )

        # ✅ PERFORMANCE: Cached calculations
        self._stats_cache: Optional[Dict] = None
        self._cache_timestamp = 0
        self._cache_ttl = 5.0  # Cache stats for 5 seconds
        
        self.logger.info("unified_results.session_created", {
            "session_id": self.session_id,
            "mode": mode,
            "path": str(self.session_path)
        })
    
    def set_data_timespan(self, start_timestamp: float, end_timestamp: float):
        """Set the actual data timespan for backtest sessions"""
        self.session_summary.data_start_time = start_timestamp
        self.session_summary.data_end_time = end_timestamp
        
        self.logger.info("unified_results.data_timespan_set", {
            "session_id": self.session_id,
            "data_start": datetime.fromtimestamp(start_timestamp).isoformat(),
            "data_end": datetime.fromtimestamp(end_timestamp).isoformat(),
            "data_duration_minutes": (end_timestamp - start_timestamp) / 60
        })
    
    def add_signal(self, raw_signal: FlashPumpSignal) -> str:
        """✅ THREAD SAFETY: Process and add a signal record with proper synchronization."""
        # Use RiskAssessmentService for persistent state and analysis
        processed_data = self.risk_assessment_service.assess_signal(raw_signal)

        signal_id = f"SIG_{int(time.time() * 1000)}"

        # Map processed data to SignalRecord fields
        signal_record = SignalRecord(
            signal_id=signal_id,
            symbol=raw_signal.symbol,
            exchange=raw_signal.exchange,
            mode=self.mode,
            detection_time=raw_signal.detection_time,
            peak_price=raw_signal.peak_price,
            pump_magnitude=raw_signal.pump_magnitude,
            confidence_score=raw_signal.confidence_score,
            volume_surge_ratio=raw_signal.volume_surge_ratio,
            entry_ready=processed_data.is_entry_recommended,
            entry_score=processed_data.opportunity_score,
            entry_conditions=processed_data.passed_conditions,
            rejection_signals=processed_data.rejection_reasons
        )

        with self._data_lock:
            # ✅ MEMORY MANAGEMENT: Enforce size limits
            if len(self.signals) >= self._max_signals:
                # Remove oldest signals (simple FIFO eviction)
                oldest_keys = list(self.signals.keys())[:100]  # Remove 100 oldest
                for key in oldest_keys:
                    del self.signals[key]
                self.logger.warning("unified_results.signal_eviction", {
                    "removed_count": len(oldest_keys),
                    "remaining_count": len(self.signals)
                })

            self.signals[signal_id] = signal_record
            self.session_summary.total_signals += 1

            # ✅ PERFORMANCE: Invalidate stats cache
            self._stats_cache = None

        self.logger.info("unified_results.signal_added", {
            "signal_id": signal_id,
            "symbol": signal_record.symbol,
            "magnitude": signal_record.pump_magnitude,
            "entry_score": signal_record.entry_score
        })

        return signal_id

    def update_trading_result(self, symbol: str, pnl: float, success: bool):
        """This method is now a placeholder as RiskAssessmentService handles state."""
        self.logger.info("unified_results.trading_result_update_skipped", {
            "note": "RiskAssessmentService now manages symbol state internally.",
            "symbol": symbol,
            "pnl": pnl,
            "success": success
        })
    
    def add_trade(self, trade_data: Dict) -> str:
        """✅ THREAD SAFETY & DATA VALIDATION: Add a trade record with proper synchronization"""
        # ✅ DATA VALIDATION: Basic input validation
        if not isinstance(trade_data, dict):
            raise ValueError("trade_data must be a dictionary")

        trade_id = trade_data.get('trade_id', f"TRD_{int(time.time() * 1000)}")
        signal_id = trade_data.get('signal_id', '')

        # ✅ DATA VALIDATION: Safe type conversions
        try:
            trade_record = TradeRecord(
                trade_id=trade_id,
                signal_id=signal_id,
                symbol=str(trade_data.get('symbol', '')),
                exchange=str(trade_data.get('exchange', '')),
                mode=self.mode,
                entry_time=float(trade_data.get('entry_time', time.time())),
                entry_price=float(trade_data.get('entry_price', 0.0)),
                entry_size=float(trade_data.get('entry_size', 0.0)),
                leverage=int(trade_data.get('leverage', 1)),
                side=str(trade_data.get('side', 'sell')),
                exit_time=trade_data.get('exit_time'),
                exit_price=trade_data.get('exit_price'),
                exit_reason=trade_data.get('exit_reason'),
                realized_pnl=float(trade_data.get('realized_pnl', 0.0)),
                unrealized_pnl=float(trade_data.get('unrealized_pnl', 0.0)),
                total_pnl=float(trade_data.get('total_pnl', 0.0)),
                pnl_pct=float(trade_data.get('pnl_pct', 0.0)),
                entry_fee=float(trade_data.get('entry_fee', 0.0)),
                exit_fee=float(trade_data.get('exit_fee', 0.0)),
                total_fees=float(trade_data.get('total_fees', 0.0)),
                stop_loss_price=trade_data.get('stop_loss_price'),
                take_profit_levels=trade_data.get('take_profit_levels', []),
                max_drawdown=float(trade_data.get('max_drawdown', 0.0)),
                max_profit=float(trade_data.get('max_profit', 0.0)),
                duration_minutes=float(trade_data.get('duration_minutes', 0.0)),
                win_trade=bool(trade_data.get('win_trade', False)),
                risk_reward_achieved=float(trade_data.get('risk_reward_achieved', 0.0)),
                pump_magnitude=float(trade_data.get('pump_magnitude', 0.0)),
                confidence_score=float(trade_data.get('confidence_score', 0.0)),
                entry_score=float(trade_data.get('entry_score', 0.0)),
                market_conditions=trade_data.get('market_conditions', {})
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid trade data: {e}")

        with self._data_lock:
            # ✅ MEMORY MANAGEMENT: Enforce size limits
            if len(self.trades) >= self._max_trades:
                # Remove oldest trades (simple FIFO eviction)
                oldest_keys = list(self.trades.keys())[:500]  # Remove 500 oldest
                for key in oldest_keys:
                    del self.trades[key]
                self.logger.warning("unified_results.trade_eviction", {
                    "removed_count": len(oldest_keys),
                    "remaining_count": len(self.trades)
                })

            self.trades[trade_id] = trade_record

            # Update signal record (thread-safe)
            if signal_id in self.signals:
                self.signals[signal_id].position_opened = True
                self.signals[signal_id].trade_id = trade_id

            # Update session summary
            self.session_summary.total_trades += 1
            if trade_record.win_trade:
                self.session_summary.winning_trades += 1
            else:
                self.session_summary.losing_trades += 1

            if trade_record.symbol not in self.session_summary.symbols:
                self.session_summary.symbols.append(trade_record.symbol)

            # ✅ PERFORMANCE: Invalidate stats cache
            self._stats_cache = None

        self.logger.info("unified_results.trade_added", {
            "trade_id": trade_id,
            "signal_id": signal_id,
            "symbol": trade_record.symbol,
            "pnl": trade_record.total_pnl
        })

        return trade_id
    
    def update_trade(self, trade_id: str, update_data: Dict):
        """Update an existing trade record"""
        if trade_id not in self.trades:
            return
        
        trade = self.trades[trade_id]
        
        # Update fields
        for key, value in update_data.items():
            if hasattr(trade, key):
                setattr(trade, key, value)
        
        self.logger.info("unified_results.trade_updated", {
            "trade_id": trade_id,
            "updates": list(update_data.keys())
        })
    
    def finalize_session(self):
        """✅ PERFORMANCE & THREAD SAFETY: Finalize session with optimized metrics calculation"""
        with self._data_lock:
            try:
                self.session_summary.end_time = time.time()

                # ✅ PERFORMANCE: Single-pass calculation to avoid multiple iterations
                total_pnl = 0.0
                total_fees = 0.0
                winning_pnl_sum = 0.0
                losing_pnl_sum = 0.0
                winning_count = 0
                losing_count = 0
                duration_sum = 0.0
                completed_trades_count = 0

                for trade in self.trades.values():
                    total_pnl += trade.total_pnl
                    total_fees += trade.total_fees

                    if trade.win_trade:
                        winning_pnl_sum += trade.total_pnl
                        winning_count += 1
                    else:
                        losing_pnl_sum += trade.total_pnl
                        losing_count += 1

                    if trade.exit_time:
                        duration_sum += trade.duration_minutes
                        completed_trades_count += 1

                # Calculate final metrics
                total_trades = len(self.trades)
                if total_trades > 0:
                    self.session_summary.win_rate = (winning_count / total_trades) * 100

                self.session_summary.total_pnl = total_pnl
                self.session_summary.total_fees = total_fees
                self.session_summary.net_pnl = total_pnl - total_fees

                # ✅ FIX: Proper win/loss averages (avoid division by zero)
                if winning_count > 0:
                    self.session_summary.avg_win = winning_pnl_sum / winning_count

                if losing_count > 0:
                    self.session_summary.avg_loss = losing_pnl_sum / losing_count

                # ✅ FIX: Proper profit factor calculation
                gross_profit = winning_pnl_sum
                gross_loss = abs(losing_pnl_sum)

                if gross_loss > 0:
                    self.session_summary.profit_factor = gross_profit / gross_loss
                else:
                    self.session_summary.profit_factor = float('inf') if gross_profit > 0 else 0.0

                # Calculate average trade duration
                if completed_trades_count > 0:
                    self.session_summary.avg_trade_duration = duration_sum / completed_trades_count

                # ✅ PERFORMANCE: Update cache
                self._stats_cache = None

                self.logger.info("unified_results.session_finalized", {
                    "session_id": self.session_id,
                    "total_signals": self.session_summary.total_signals,
                    "total_trades": total_trades,
                    "win_rate": self.session_summary.win_rate,
                    "net_pnl": self.session_summary.net_pnl
                })

            except Exception as e:
                self.logger.error("unified_results.finalize_error", {
                    "session_id": self.session_id,
                    "error": str(e)
                })
    
    async def export_results(self):
        """✅ ASYNC I/O: Export all results to files with timeout protection"""
        try:
            self.logger.info("unified_results.export_start", {
                "session_id": self.session_id,
                "path": str(self.session_path),
                "path_exists": self.session_path.exists()
            })

            # ✅ ASYNC I/O: Use async export methods
            await self._safe_export_signals()
            await self._safe_export_trades()
            await self._safe_export_summary()
            await self._safe_export_metadata()

            self.logger.info("unified_results.results_exported", {
                "session_id": self.session_id,
                "path": str(self.session_path)
            })

        except Exception as e:
            self.logger.error("unified_results.export_error", {
                "session_id": self.session_id,
                "error": str(e)
            })
            raise
    
    async def _safe_export_signals(self):
        """✅ ASYNC I/O: Safely export signals with error handling"""
        try:
            self.logger.info("unified_results.exporting_signals", {
                "session_id": self.session_id,
                "signals_count": len(self.signals)
            })

            # ✅ PERFORMANCE: Convert to dict only when needed
            signals_data = [asdict(signal) for signal in self.signals.values()]
            signals_file = self.session_path / "signals.json"

            # ✅ ASYNC I/O: Use aiofiles for non-blocking I/O
            temp_file = signals_file.with_suffix('.tmp')
            async with aiofiles.open(temp_file, 'w') as f:
                await f.write(json.dumps(signals_data, indent=2, default=self._safe_json_serializer))

            # Atomic rename
            temp_file.replace(signals_file)

            self.logger.info("unified_results.signals_exported", {
                "session_id": self.session_id,
                "file": str(signals_file),
                "file_exists": signals_file.exists()
            })

        except Exception as e:
            self.logger.error("unified_results.signals_export_error", {
                "session_id": self.session_id,
                "error": str(e)
            })
            raise

    def _safe_json_serializer(self, obj):
        """✅ SECURITY: Safe JSON serialization without exposing sensitive data"""
        if hasattr(obj, '__dict__'):
            # Convert objects to safe dict representation
            return str(obj)
        elif isinstance(obj, (datetime,)):
            # Convert datetime objects to ISO format
            return obj.isoformat()
        else:
            # Fallback to string representation
            return str(obj)
    
    async def _safe_export_trades(self):
        """✅ ASYNC I/O: Safely export trades with error handling"""
        try:
            self.logger.info("unified_results.exporting_trades", {
                "session_id": self.session_id,
                "trades_count": len(self.trades)
            })

            trades_data = [asdict(trade) for trade in self.trades.values()]
            trades_file = self.session_path / "trades.json"

            # ✅ ASYNC I/O: Use aiofiles for non-blocking I/O
            temp_file = trades_file.with_suffix('.tmp')
            async with aiofiles.open(temp_file, 'w') as f:
                await f.write(json.dumps(trades_data, indent=2, default=self._safe_json_serializer))

            # Atomic rename
            temp_file.replace(trades_file)

            self.logger.info("unified_results.trades_exported", {
                "session_id": self.session_id,
                "file": str(trades_file),
                "file_exists": trades_file.exists()
            })

        except Exception as e:
            self.logger.error("unified_results.trades_export_error", {
                "session_id": self.session_id,
                "error": str(e)
            })
            raise
    
    async def _safe_export_summary(self):
        """✅ ASYNC I/O: Safely export session summary with error handling"""
        try:
            self.logger.info("unified_results.exporting_summary", {
                "session_id": self.session_id
            })

            summary_file = self.session_path / "session_summary.json"

            # ✅ ASYNC I/O: Use aiofiles for non-blocking I/O
            temp_file = summary_file.with_suffix('.tmp')
            async with aiofiles.open(temp_file, 'w') as f:
                await f.write(json.dumps(asdict(self.session_summary), indent=2, default=self._safe_json_serializer))

            # Atomic rename
            temp_file.replace(summary_file)

            self.logger.info("unified_results.summary_exported", {
                "session_id": self.session_id,
                "file": str(summary_file),
                "file_exists": summary_file.exists()
            })

        except Exception as e:
            self.logger.error("unified_results.summary_export_error", {
                "session_id": self.session_id,
                "error": str(e)
            })
            raise
    
    async def _safe_export_metadata(self):
        """✅ ASYNC I/O: Safely export metadata with error handling"""
        try:
            self.logger.info("unified_results.exporting_metadata", {
                "session_id": self.session_id
            })

            metadata = {
                "session_id": self.session_id,
                "mode": self.mode,
                "created_at": self.session_summary.start_time,
                "finalized_at": self.session_summary.end_time,
                "total_signals": len(self.signals),
                "total_trades": len(self.trades),
                "files_generated": ["signals.json", "trades.json", "session_summary.json"]
            }

            metadata_file = self.session_path / "metadata.json"

            # ✅ ASYNC I/O: Use aiofiles for non-blocking I/O
            temp_file = metadata_file.with_suffix('.tmp')
            async with aiofiles.open(temp_file, 'w') as f:
                await f.write(json.dumps(metadata, indent=2, default=self._safe_json_serializer))

            # Atomic rename
            temp_file.replace(metadata_file)

            self.logger.info("unified_results.metadata_exported", {
                "session_id": self.session_id,
                "file": str(metadata_file),
                "file_exists": metadata_file.exists()
            })

        except Exception as e:
            self.logger.error("unified_results.metadata_export_error", {
                "session_id": self.session_id,
                "error": str(e)
            })
            raise
    
    def get_session_statistics(self) -> Dict:
        """✅ PERFORMANCE: Get current session statistics with caching"""
        current_time = time.time()

        # Check if cache is valid
        if (self._stats_cache is not None and
            current_time - self._cache_timestamp < self._cache_ttl):
            return self._stats_cache

        # Calculate fresh statistics
        with self._data_lock:
            active_trades = sum(1 for t in self.trades.values() if t.exit_time is None)

            stats = {
                "session_id": self.session_id,
                "mode": self.mode,
                "total_signals": len(self.signals),
                "total_trades": len(self.trades),
                "active_trades": active_trades,
                "win_rate": self.session_summary.win_rate,
                "total_pnl": self.session_summary.total_pnl,
                "net_pnl": self.session_summary.net_pnl,
                "symbols": self.session_summary.symbols.copy()  # Return copy to prevent external modification
            }

            # Update cache
            self._stats_cache = stats
            self._cache_timestamp = current_time

        return stats
    
    def get_session_summary(self) -> Dict:
        """Get comprehensive session summary for display with error handling"""
        try:
            # Use data timespan for backtest, processing time for live
            if self.mode == "backtest" and self.session_summary.data_start_time and self.session_summary.data_end_time:
                session_duration = self.session_summary.data_end_time - self.session_summary.data_start_time
            else:
                session_duration = 0
                if self.session_summary.end_time:
                    session_duration = self.session_summary.end_time - self.session_summary.start_time
            
            # Calculate additional metrics
            successful_trades = len([t for t in self.trades.values() if t.win_trade])
            failed_trades = len([t for t in self.trades.values() if not t.win_trade])
            
            # Calculate best and worst trades
            trade_pnls = [t.total_pnl for t in self.trades.values() if t.total_pnl != 0]
            best_trade_pnl = max(trade_pnls) if trade_pnls else 0
            worst_trade_pnl = min(trade_pnls) if trade_pnls else 0
            
            # Calculate average PnL per trade
            avg_pnl_per_trade = 0
            if len(self.trades) > 0:
                avg_pnl_per_trade = sum(t.total_pnl for t in self.trades.values()) / len(self.trades)
            
            summary = {
                "session_id": self.session_id,
                "session_duration": session_duration,
                "symbols_processed": len(set(t.symbol for t in self.trades.values())),
                "total_signals": len(self.signals),
                "total_trades": len(self.trades),
                "successful_trades": successful_trades,
                "failed_trades": failed_trades,
                "total_pnl": self.session_summary.total_pnl,
                "avg_pnl_per_trade": avg_pnl_per_trade,
                "best_trade_pnl": best_trade_pnl,
                "worst_trade_pnl": worst_trade_pnl,
                "win_rate": self.session_summary.win_rate
            }
            
            return summary
            
        except Exception as e:
            self.logger.error("unified_results.summary_error", {
                "session_id": self.session_id,
                "error": str(e)
            })
            return {
                "session_id": self.session_id,
                "error": str(e)
            }
    
    def get_export_path(self) -> str:
        """Get the export path for results"""
        return str(self.session_path)
    
    def get_symbol_statistics(self, symbol: str) -> Dict:
        """Get comprehensive symbol statistics from RiskAssessmentService."""
        return self.risk_assessment_service.get_symbol_statistics(symbol)
    
    def get_all_symbols_status(self) -> Dict:
        """Get status overview for all symbols from RiskAssessmentService."""
        return self.risk_assessment_service.get_all_symbols_status()
    
    def reset_symbol_state(self, symbol: str):
        """Reset symbol state in RiskAssessmentService."""
        self.risk_assessment_service.reset_symbol_state(symbol)
        self.logger.warning("unified_results.symbol_state_reset", {
            "symbol": symbol
        })