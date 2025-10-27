"""
Data Analysis Service for Sprint 5A - Data Collection Enhancements

Provides comprehensive analysis of collected market data including:
- Price and volume statistics
- Time-series data for charting
- Data completeness analysis
- Performance metrics calculation

✅ STEP 3.2: Refactored to use QuestDB instead of CSV files
"""

import asyncio
import json
import logging
import statistics
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass

from ..core.logger import get_logger
from ..core.utils import calculate_volatility, calculate_distribution
from .questdb_data_provider import QuestDBDataProvider

logger = get_logger(__name__)

@dataclass
class PriceStats:
    """Price statistics for a symbol"""
    min_price: float
    max_price: float
    avg_price: float
    price_range: float
    volatility: float
    start_price: float
    end_price: float
    price_change_pct: float

@dataclass
class VolumeStats:
    """Volume statistics for a symbol"""
    total_volume: float
    avg_volume: float
    peak_volume: float
    volume_distribution: Dict[str, float]
    volume_change_pct: float

@dataclass
class TimeSeriesPoint:
    """Single point in time series data"""
    timestamp: int
    price: float
    volume: float
    symbol: str

@dataclass
class GapInfo:
    """Information about data gaps"""
    start_time: int
    end_time: int
    duration_ms: int
    missing_points: int
    severity: str  # 'minor', 'moderate', 'critical'

@dataclass
class AnomalyInfo:
    """Information about data anomalies"""
    timestamp: int
    field: str
    value: Any
    expected_range: Tuple[float, float]
    severity: str

class DataAnalysisService:
    """
    Service for analyzing collected market data

    Provides methods to:
    - Load and analyze session data
    - Calculate price and volume statistics
    - Generate chart-ready time series data
    - Compute data completeness metrics
    """

    def __init__(self, db_provider: Optional[QuestDBDataProvider] = None):
        """
        Initialize DataAnalysisService with QuestDB data provider.

        Args:
            db_provider: QuestDB data provider (required for production use)

        ✅ STEP 3.2: Changed from data_directory to db_provider
        """
        if db_provider is None:
            raise ValueError(
                "QuestDBDataProvider is required for DataAnalysisService.\n"
                "CSV-based data access has been removed. All data now comes from QuestDB."
            )

        self.db_provider = db_provider

        # Thread-safe cache with RLock for concurrent access protection
        self._cache_lock = threading.RLock()
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._symbol_cache: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

    async def analyze_session_data(self, session_id: str) -> Dict[str, Any]:
        """
        Analyze collected data for a complete session

        Args:
            session_id: Unique session identifier

        Returns:
            Comprehensive analysis including statistics and metadata
        """
        try:
            # Load session metadata
            session_meta = await self._load_session_metadata(session_id)
            if not session_meta:
                raise ValueError(f"Session {session_id} not found")

            # Load data for all symbols
            symbols_data = {}
            for symbol in session_meta['symbols']:
                symbol_data = await self._load_symbol_data(session_id, symbol)
                if symbol_data:
                    symbols_data[symbol] = symbol_data

            # Calculate comprehensive statistics
            analysis = {
                'session_id': session_id,
                'session_info': session_meta,
                'symbols_analyzed': list(symbols_data.keys()),
                'timestamp': datetime.utcnow().isoformat(),
                'summary': await self._calculate_session_summary(symbols_data),
                'symbols': {}
            }

            # Analyze each symbol
            for symbol, data in symbols_data.items():
                analysis['symbols'][symbol] = await self._analyze_symbol_data(symbol, data)

            logger.info(f"Completed analysis for session {session_id} with {len(symbols_data)} symbols")
            return analysis

        except Exception as e:
            logger.error("session_analysis_failed", {"session_id": session_id, "error": str(e)})
            raise

    async def get_session_chart_data(self, session_id: str, symbol: str, max_points: int = 10000) -> List[Dict[str, Any]]:
        """
        Get time-series data formatted for frontend charting

        Args:
            session_id: Session identifier
            symbol: Trading symbol to analyze
            max_points: Maximum number of data points to return

        Returns:
            List of chart-ready data points
        """
        try:
            data_points = await self._load_symbol_data(session_id, symbol)
            if not data_points:
                return []

            # Convert to chart format and limit points using downsampling
            chart_data = []
            step = max(1, len(data_points) // max_points)

            for i in range(0, len(data_points), step):
                point = data_points[i]
                chart_point = {
                    'timestamp': point['timestamp'],
                    'price': point['price'],
                    'volume': point['volume'],
                    'symbol': symbol
                }
                chart_data.append(chart_point)

            logger.info(f"Generated {len(chart_data)} chart points for {symbol} in session {session_id}")
            return chart_data

        except Exception as e:
            logger.error(f"Failed to get chart data for {symbol} in session {session_id}: {e}")
            raise

    async def _load_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load session metadata from QuestDB.

        ✅ STEP 3.2: Changed from file system to QuestDB query
        """
        if not session_id:
            return None

        # Check cache with lock
        with self._cache_lock:
            if session_id in self._metadata_cache:
                return self._metadata_cache[session_id]

        # Load from QuestDB
        try:
            metadata = await self.db_provider.get_session_metadata(session_id)

            if metadata:
                # Cache the result
                with self._cache_lock:
                    self._metadata_cache[session_id] = metadata

            return metadata

        except Exception as e:
            logger.error(f"Failed to load session metadata for {session_id}: {e}")
            return None

    async def list_sessions(self, limit: int = 50, include_stats: bool = False) -> Dict[str, Any]:
        """
        List data collection sessions from QuestDB.

        ✅ STEP 3.2: Changed from directory scanning to QuestDB query
        """
        try:
            # Get sessions from QuestDB
            sessions_raw = await self.db_provider.get_sessions_list(limit=limit)

            sessions = []
            for session_meta in sessions_raw:
                session_info: Dict[str, Any] = {
                    "session_id": session_meta.get("session_id"),
                    "status": session_meta.get("status", "completed"),
                    "symbols": session_meta.get("symbols", []),
                    "records_collected": session_meta.get("records_collected", 0),
                    "start_time": session_meta.get("start_time"),
                    "end_time": session_meta.get("end_time"),
                    "duration_seconds": session_meta.get("duration_seconds"),
                    "created_at": session_meta.get("created_at"),
                    "updated_at": session_meta.get("updated_at"),
                    "exchange": session_meta.get("exchange"),
                    "prices_count": session_meta.get("prices_count", 0),
                    "orderbook_count": session_meta.get("orderbook_count", 0),
                }

                if include_stats and session_info["symbols"]:
                    try:
                        # Get detailed statistics from QuestDB
                        stats = await self.db_provider.get_session_statistics(session_info["session_id"])
                        if stats:
                            session_info["stats"] = stats
                    except Exception as e:
                        logger.error("session_summary_failed", {"session_id": session_info["session_id"], "error": str(e)})

                sessions.append(session_info)

            return {
                "sessions": sessions,
                "total_count": len(sessions),
                "limit": limit,
            }

        except Exception as e:
            logger.error("list_sessions_failed", {"error": str(e), "error_type": type(e).__name__})
            raise

    async def delete_session(self, session_id: str) -> Dict[str, Any]:
        """Delete a data collection session and its associated files."""
        deleted_files = []
        session_found = False
        
        for base_dir in self._data_directories:
            session_dir = base_dir / session_id
            if session_dir.exists():
                session_found = True
                try:
                    # Recursively delete all files and subdirectories
                    import shutil
                    shutil.rmtree(session_dir)
                    deleted_files.append(str(session_dir))
                    logger.info(f"Deleted session directory: {session_dir}")
                except Exception as e:
                    logger.error(f"Failed to delete session directory {session_dir}: {e}")
                    return {
                        "success": False,
                        "error": f"Failed to delete session files: {str(e)}",
                        "deleted_files": deleted_files
                    }
        
        if not session_found:
            return {
                "success": False,
                "error": f"Session {session_id} not found",
                "deleted_files": []
            }
        
        # Clear cache for deleted session with lock
        with self._cache_lock:
            cache_keys_to_remove = [key for key in self._symbol_cache.keys() if key[0] == session_id]
            for key in cache_keys_to_remove:
                del self._symbol_cache[key]

            if session_id in self._metadata_cache:
                del self._metadata_cache[session_id]
        
        return {
            "success": True,
            "deleted_files": deleted_files
        }

    async def _load_symbol_data(self, session_id: str, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        Load price data points for a specific symbol from QuestDB.

        ✅ STEP 3.2: Changed from CSV/JSON files to QuestDB query
        """
        if not session_id or not symbol:
            return None

        cache_key = (session_id, symbol)

        # Check cache with lock
        with self._cache_lock:
            if cache_key in self._symbol_cache:
                return self._symbol_cache[cache_key]

        # Load from QuestDB
        try:
            data = await self.db_provider.get_tick_prices(
                session_id=session_id,
                symbol=symbol
            )

            if data:
                # Cache the result
                with self._cache_lock:
                    self._symbol_cache[cache_key] = data

            return data

        except Exception as e:
            logger.error(f"Failed to load symbol data for {symbol} in session {session_id}: {e}")
            return None

    def _initialize_data_directories(self, primary: Path) -> List[Path]:
        """Build a prioritized list of directories to scan for session data."""
        candidates: List[Path] = []
        seen: Set[Path] = set()

        def add(path_like: Any) -> None:
            if not path_like:
                return
            p = Path(path_like)
            try:
                resolved = p.resolve()
            except FileNotFoundError:
                resolved = p.absolute()
            if resolved in seen:
                return
            candidates.append(p)
            seen.add(resolved)

        add(primary)
        env_dir = os.getenv("DATA_COLLECTION_DIR")
        if env_dir:
            add(env_dir)
        add(Path("data"))
        add(Path("data/historical"))
        return candidates

    def _find_session_directory(self, session_id: str) -> Optional[Path]:
        if not session_id:
            return None

        normalized = session_id.strip().rstrip("/\\")

        candidate_names: List[str] = []
        if normalized:
            candidate_names.append(normalized)
        if normalized and not normalized.startswith("session_"):
            candidate_names.append(f"session_{normalized}")

        unique_names: List[str] = []
        seen_names: Set[str] = set()
        for name in candidate_names:
            if name not in seen_names:
                unique_names.append(name)
                seen_names.add(name)

        for base_dir in self._data_directories:
            for name in unique_names:
                candidate = base_dir / name
                if candidate.exists() and candidate.is_dir():
                    return candidate
        return None

    async def _collect_session_summary(self, session_id: str, symbols: List[str]) -> Optional[Dict[str, Any]]:
        symbols_data: Dict[str, List[Dict[str, Any]]] = {}
        for symbol in symbols:
            data = await self._load_symbol_data(session_id, symbol)
            if data:
                symbols_data[symbol] = data
        if not symbols_data:
            return None
        return await self._calculate_session_summary(symbols_data)

    def _build_metadata_from_session(self, session_id: str, session_dir: Path) -> Optional[Dict[str, Any]]:
        symbols = sorted([entry.name for entry in session_dir.iterdir() if entry.is_dir()])
        if not symbols:
            return {
                "session_id": session_id,
                "symbols": [],
                "status": "empty",
                "data_path": str(session_dir),
                "records_collected": 0,
            }

        records_collected = 0
        min_ts = None
        max_ts = None

        for symbol in symbols:
            price_csv = session_dir / symbol / "prices.csv"
            if not price_csv.exists():
                continue
            summary = self._summarize_price_csv(price_csv)
            records_collected += summary["count"]
            if summary["min_ts"] is not None:
                min_ts = summary["min_ts"] if min_ts is None else min(min_ts, summary["min_ts"])
            if summary["max_ts"] is not None:
                max_ts = summary["max_ts"] if max_ts is None else max(max_ts, summary["max_ts"])

        metadata: Dict[str, Any] = {
            "session_id": session_id,
            "symbols": symbols,
            "status": "completed",
            "data_path": str(session_dir),
            "records_collected": records_collected,
        }

        if min_ts is not None:
            metadata["start_timestamp"] = min_ts
            metadata["start_time"] = self._timestamp_to_iso(min_ts)
        if max_ts is not None:
            metadata["end_timestamp"] = max_ts
            metadata["end_time"] = self._timestamp_to_iso(max_ts)
            if min_ts is not None:
                metadata["duration_seconds"] = max(0.0, max_ts - min_ts)

        try:
            stats = session_dir.stat()
            metadata["created_at"] = datetime.utcfromtimestamp(stats.st_ctime).isoformat() + "Z"
            metadata["updated_at"] = datetime.utcfromtimestamp(stats.st_mtime).isoformat() + "Z"
        except Exception:
            pass

        return metadata

    def _summarize_price_csv(self, price_csv: Path) -> Dict[str, Optional[int]]:
        count = 0
        min_ts = None
        max_ts = None

        with price_csv.open("r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = self._normalize_timestamp(row.get("timestamp"))
                if timestamp is None:
                    continue
                count += 1
                if min_ts is None or timestamp < min_ts:
                    min_ts = timestamp
                if max_ts is None or timestamp > max_ts:
                    max_ts = timestamp

        return {"count": count, "min_ts": min_ts, "max_ts": max_ts}

    def _parse_price_csv(self, price_csv: Path) -> List[Dict[str, Any]]:
        points: List[Dict[str, Any]] = []

        with price_csv.open("r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = self._normalize_timestamp(row.get("timestamp"))
                if timestamp is None:
                    continue
                price = self._safe_float(row.get("price"), default=0.0)
                volume = self._safe_float(row.get("volume"), default=0.0)
                quote_volume = self._safe_float(row.get("quote_volume"), default=None)

                point: Dict[str, Any] = {
                    "timestamp": timestamp,
                    "price": price,
                    "volume": volume,
                }
                if quote_volume is not None:
                    point["quote_volume"] = quote_volume
                points.append(point)

        points.sort(key=lambda x: x["timestamp"])
        return points

    def _normalize_timestamp(self, value: Any) -> Optional[float]:
        """
        Normalize timestamp to seconds with decimal precision to match indicator format.
        
        This ensures timestamps are consistent between price data and technical indicators.
        Both use seconds format (e.g., 1759841422.461) rather than milliseconds.
        """
        if value is None or value == "":
            return None

        try:
            ts = float(value)
        except (TypeError, ValueError):
            return None

        # Convert various timestamp formats to seconds with decimal precision
        if ts > 1e14:  # Microseconds
            return ts / 1000000
        if ts > 1e12:  # Milliseconds 
            return ts / 1000
        if ts > 1e9:   # Seconds (already correct format)
            return ts
        if ts > 1e6:   # Likely seconds with large integer part
            return ts
        return ts

    def _safe_float(self, value: Any, default: Optional[float]) -> Optional[float]:
        if value is None or value == "":
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _timestamp_to_iso(self, timestamp_seconds: float) -> str:
        try:
            return datetime.utcfromtimestamp(timestamp_seconds).isoformat() + "Z"
        except (ValueError, OSError, OverflowError):
            return ""
    async def _calculate_session_summary(self, symbols_data: Dict[str, List]) -> Dict[str, Any]:
        """Calculate overall session statistics"""
        total_points = sum(len(data) for data in symbols_data.values())
        total_symbols = len(symbols_data)

        # Calculate time range
        all_timestamps = []
        for data in symbols_data.values():
            all_timestamps.extend([point['timestamp'] for point in data])

        if all_timestamps:
            min_time = min(all_timestamps)
            max_time = max(all_timestamps)
            duration_hours = (max_time - min_time) / (60 * 60)  # Convert seconds to hours
        else:
            min_time = max_time = 0
            duration_hours = 0

        return {
            'total_data_points': total_points,
            'total_symbols': total_symbols,
            'time_range': {
                'start': min_time,
                'end': max_time,
                'duration_hours': round(duration_hours, 2)
            },
            'avg_points_per_symbol': total_points // max(1, total_symbols)
        }

    async def _analyze_symbol_data(self, symbol: str, data_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze data for a specific symbol"""
        if not data_points:
            return {'error': 'No data points available'}

        # Extract price and volume series
        prices = [point['price'] for point in data_points]
        volumes = [point['volume'] for point in data_points]
        timestamps = [point['timestamp'] for point in data_points]

        # Calculate statistics
        price_stats = self._calculate_price_stats(prices)
        volume_stats = self._calculate_volume_stats(volumes)

        # Calculate time-based metrics
        time_metrics = self._calculate_time_metrics(timestamps)

        return {
            'data_points': len(data_points),
            'price_stats': price_stats,
            'volume_stats': volume_stats,
            'time_metrics': time_metrics,
            'data_quality': self._assess_data_quality(data_points)
        }

    def _calculate_price_stats(self, prices: List[float]) -> Dict[str, Any]:
        """Calculate comprehensive price statistics"""
        if not prices:
            return {}

        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)
        start_price = prices[0]
        end_price = prices[-1]

        return {
            'min_price': min_price,
            'max_price': max_price,
            'avg_price': round(avg_price, 2),
            'price_range': round(max_price - min_price, 2),
            'volatility': round(calculate_volatility(prices), 4),
            'start_price': start_price,
            'end_price': end_price,
            'price_change_pct': round(((end_price - start_price) / start_price) * 100, 2) if start_price > 0 else 0
        }

    def _calculate_volume_stats(self, volumes: List[float]) -> Dict[str, Any]:
        """Calculate comprehensive volume statistics"""
        if not volumes:
            return {}

        total_volume = sum(volumes)
        avg_volume = total_volume / len(volumes)
        peak_volume = max(volumes)

        # Calculate volume distribution
        distribution = calculate_distribution(volumes)

        # Calculate volume change
        start_volume = volumes[0] if volumes else 0
        end_volume = volumes[-1] if volumes else 0
        volume_change_pct = ((end_volume - start_volume) / start_volume) * 100 if start_volume > 0 else 0

        return {
            'total_volume': round(total_volume, 2),
            'avg_volume': round(avg_volume, 2),
            'peak_volume': round(peak_volume, 2),
            'volume_distribution': distribution,
            'volume_change_pct': round(volume_change_pct, 2)
        }

    def _calculate_time_metrics(self, timestamps: List[int], max_gaps: int = 10) -> Dict[str, Any]:
        """Calculate time-based metrics with early exit optimization"""
        if not timestamps:
            return {}

        # Calculate gaps between points with early exit
        gaps = []
        expected_interval = 1.0  # 1 second in seconds (timestamps are in seconds)

        for i in range(1, len(timestamps)):
            # Early exit optimization: stop when we have enough gaps for summary
            if len(gaps) >= max_gaps:
                break

            gap = timestamps[i] - timestamps[i-1]
            if gap > expected_interval * 2:  # Significant gap
                gaps.append({
                    'start_time': timestamps[i-1],
                    'end_time': timestamps[i],
                    'duration_ms': gap,
                    'missing_points': int(gap / expected_interval) - 1
                })

        return {
            'total_gaps': len(gaps),
            'total_gap_duration_ms': sum(gap['duration_ms'] for gap in gaps),
            'avg_gap_duration_ms': round(sum(gap['duration_ms'] for gap in gaps) / max(1, len(gaps)), 2),
            'gaps': gaps  # Already limited by max_gaps
        }

    def _assess_data_quality(self, data_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess overall data quality"""
        if not data_points:
            return {'score': 0, 'issues': ['No data points']}

        issues = []
        score = 100  # Start with perfect score

        # Check for missing values
        missing_prices = sum(1 for p in data_points if p.get('price') is None or p.get('price') == 0)
        missing_volumes = sum(1 for p in data_points if p.get('volume') is None)

        if missing_prices > 0:
            issues.append(f"{missing_prices} missing price values")
            score -= min(20, missing_prices * 2)

        if missing_volumes > 0:
            issues.append(f"{missing_volumes} missing volume values")
            score -= min(10, missing_volumes)

        # Check for unrealistic values
        unrealistic_prices = sum(1 for p in data_points if p.get('price', 0) < 0 or p.get('price', 0) > 1000000)
        if unrealistic_prices > 0:
            issues.append(f"{unrealistic_prices} unrealistic price values")
            score -= min(15, unrealistic_prices)

        # Check timestamp ordering
        timestamps = [p['timestamp'] for p in data_points]
        if timestamps != sorted(timestamps):
            issues.append("Timestamps not in chronological order")
            score -= 10

        return {
            'score': max(0, score),
            'issues': issues,
            'completeness_pct': round((len(data_points) - missing_prices) / len(data_points) * 100, 1)
        }

