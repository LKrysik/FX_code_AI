"""
Chart Data API Routes
======================

REST endpoints for chart OHLCV data and signal markers.

Endpoints:
- GET /api/chart/ohlcv - Get OHLCV candlestick data
- GET /api/chart/signals - Get signal markers for chart overlay

Performance Requirements:
- All endpoints MUST return within <100ms
- Uses QuestDB SAMPLE BY for efficient aggregation

Related Tables:
- tick_prices (OHLCV aggregation source)
- strategy_signals (signal markers)
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import json

from src.core.logger import get_logger
from src.data_feed.questdb_provider import QuestDBProvider
from src.api.response_envelope import ensure_envelope

logger = get_logger(__name__)
router = APIRouter(prefix="/api/chart", tags=["chart"])

# Dependency injection - will be set during app startup
_questdb_provider: Optional[QuestDBProvider] = None


def initialize_chart_dependencies(questdb_provider: QuestDBProvider):
    """
    Initialize dependencies for chart routes.
    Called from unified_server.py during startup.

    Args:
        questdb_provider: QuestDB database provider
    """
    global _questdb_provider
    _questdb_provider = questdb_provider
    logger.info("chart_routes.dependencies_initialized")


def _ensure_dependencies():
    """Verify dependencies are initialized."""
    if _questdb_provider is None:
        raise RuntimeError(
            "Chart routes dependencies not initialized. "
            "Call initialize_chart_dependencies() during app startup."
        )
    return _questdb_provider


# Interval mapping to QuestDB SAMPLE BY syntax
INTERVAL_MAPPING = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}


@router.get("/ohlcv")
async def get_ohlcv_data(
    session_id: str = Query(..., description="Session ID"),
    symbol: str = Query(..., description="Trading pair (e.g., BTC_USDT)"),
    interval: str = Query("1m", description="Candlestick interval (1m, 5m, 15m, 30m, 1h, 4h, 1d)"),
    limit: int = Query(500, ge=1, le=1000, description="Maximum number of candles to return")
) -> JSONResponse:
    """
    Get OHLCV (candlestick) data for chart rendering.

    Uses QuestDB SAMPLE BY for efficient aggregation from tick_prices table.

    Performance Target: <100ms

    Query Parameters:
    - session_id: Required - Session identifier
    - symbol: Required - Trading pair (e.g., BTC_USDT)
    - interval: Optional - Candlestick interval (default: 1m)
      Valid values: 1m, 5m, 15m, 30m, 1h, 4h, 1d
    - limit: Optional - Max candles (default 500, max 1000)

    Returns:
        {
            "session_id": "session_123",
            "symbol": "BTC_USDT",
            "interval": "1m",
            "candles": [
                {
                    "time": 1699999200,  // Unix timestamp in seconds
                    "open": 50000.0,
                    "high": 50100.0,
                    "low": 49900.0,
                    "close": 50050.0,
                    "volume": 1000.0
                }
            ],
            "total_count": 500
        }
    """
    import time
    start_time = time.time()

    questdb = _ensure_dependencies()

    # Validate interval
    if interval not in INTERVAL_MAPPING:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid interval: {interval}. Valid values: {', '.join(INTERVAL_MAPPING.keys())}"
        )

    sample_interval = INTERVAL_MAPPING[interval]

    try:
        # QuestDB SAMPLE BY query for OHLCV aggregation
        # Note: QuestDB SAMPLE BY requires designated timestamp column
        query = f"""
            SELECT
                timestamp,
                first(price) as open,
                max(price) as high,
                min(price) as low,
                last(price) as close,
                sum(volume) as volume
            FROM tick_prices
            WHERE session_id = $1 AND symbol = $2
            SAMPLE BY {sample_interval} ALIGN TO CALENDAR FILL(PREV)
            ORDER BY timestamp DESC
            LIMIT $3
        """

        async with questdb.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, session_id, symbol, limit)

        # Convert to candle format (reverse to chronological order)
        candles = []
        for row in reversed(rows):  # Reverse because query orders DESC
            candle = {
                "time": int(row['timestamp'].timestamp()) if row['timestamp'] else 0,
                "open": float(row['open']) if row['open'] is not None else 0.0,
                "high": float(row['high']) if row['high'] is not None else 0.0,
                "low": float(row['low']) if row['low'] is not None else 0.0,
                "close": float(row['close']) if row['close'] is not None else 0.0,
                "volume": float(row['volume']) if row['volume'] is not None else 0.0,
            }
            candles.append(candle)

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info("chart_routes.ohlcv_success", {
            "session_id": session_id,
            "symbol": symbol,
            "interval": interval,
            "candles_count": len(candles),
            "elapsed_ms": elapsed_ms
        })

        response = {
            "session_id": session_id,
            "symbol": symbol,
            "interval": interval,
            "candles": candles,
            "total_count": len(candles)
        }

        return JSONResponse(content=ensure_envelope(response))

    except Exception as e:
        logger.error("chart_routes.ohlcv_failed", {
            "session_id": session_id,
            "symbol": symbol,
            "interval": interval,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Failed to get OHLCV data: {str(e)}")


@router.get("/signals")
async def get_chart_signals(
    session_id: str = Query(..., description="Session ID"),
    symbol: str = Query(..., description="Trading pair (e.g., BTC_USDT)"),
    start_time: Optional[int] = Query(None, description="Start time (Unix timestamp in seconds)"),
    end_time: Optional[int] = Query(None, description="End time (Unix timestamp in seconds)")
) -> JSONResponse:
    """
    Get signal markers for chart overlay.

    Performance Target: <100ms

    Query Parameters:
    - session_id: Required - Session identifier
    - symbol: Required - Trading pair (e.g., BTC_USDT)
    - start_time: Optional - Filter signals after this time (Unix timestamp)
    - end_time: Optional - Filter signals before this time (Unix timestamp)

    Returns:
        {
            "session_id": "session_123",
            "symbol": "BTC_USDT",
            "markers": [
                {
                    "time": 1699999200,
                    "position": "aboveBar",
                    "color": "#26a69a",
                    "shape": "arrowUp",
                    "text": "S1 BUY",
                    "signal_id": "sig_123",
                    "signal_type": "S1"
                }
            ],
            "total_count": 10
        }
    """
    import time
    start_time_exec = time.time()

    questdb = _ensure_dependencies()

    try:
        # Build query with optional time filters
        query_parts = [
            """
            SELECT
                signal_id, signal_type, timestamp, action, triggered
            FROM strategy_signals
            WHERE session_id = $1 AND symbol = $2
            """
        ]
        params = [session_id, symbol]
        param_idx = 3

        if start_time:
            # Convert Unix timestamp to Python datetime for QuestDB
            query_parts.append(f"AND timestamp >= ${param_idx}")
            start_dt = datetime.fromtimestamp(start_time, tz=timezone.utc)
            params.append(start_dt)
            param_idx += 1

        if end_time:
            # Convert Unix timestamp to Python datetime for QuestDB
            query_parts.append(f"AND timestamp <= ${param_idx}")
            end_dt = datetime.fromtimestamp(end_time, tz=timezone.utc)
            params.append(end_dt)
            param_idx += 1

        query_parts.append("ORDER BY timestamp ASC")
        query = "\n".join(query_parts)

        async with questdb.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        # Convert signals to chart markers
        markers = []
        for row in rows:
            # Determine marker properties based on signal type and action
            signal_type = row['signal_type']
            action = row['action']

            # Position: buy signals below bar, sell signals above bar
            position = "belowBar" if action == "BUY" else "aboveBar"

            # Color and shape based on signal type
            color = "#26a69a"  # Default green
            shape = "arrowUp"  # Default up arrow

            if signal_type == "S1":  # Entry signal
                color = "#FFC107"  # Yellow
                shape = "arrowUp" if action == "BUY" else "arrowDown"
            elif signal_type == "Z1":  # Zone signal
                color = "#4CAF50"  # Green
                shape = "circle"
            elif signal_type == "ZE1":  # Zone exit
                color = "#2196F3"  # Blue
                shape = "circle"
            elif signal_type == "E1":  # Exit signal
                color = "#F44336"  # Red
                shape = "arrowDown" if action == "SELL" else "arrowUp"
            elif signal_type == "O1":  # Override signal
                color = "#9C27B0"  # Purple
                shape = "square"
            elif signal_type == "EMERGENCY":
                color = "#FF5722"  # Deep Orange
                shape = "square"

            # Text label
            text = f"{signal_type} {action}"

            marker = {
                "time": int(row['timestamp'].timestamp()) if row['timestamp'] else 0,
                "position": position,
                "color": color,
                "shape": shape,
                "text": text,
                "signal_id": row['signal_id'],
                "signal_type": signal_type,
                "triggered": row['triggered']
            }
            markers.append(marker)

        elapsed_ms = (time.time() - start_time_exec) * 1000

        logger.info("chart_routes.signals_success", {
            "session_id": session_id,
            "symbol": symbol,
            "markers_count": len(markers),
            "elapsed_ms": elapsed_ms
        })

        response = {
            "session_id": session_id,
            "symbol": symbol,
            "markers": markers,
            "total_count": len(markers)
        }

        return JSONResponse(content=ensure_envelope(response))

    except Exception as e:
        logger.error("chart_routes.signals_failed", {
            "session_id": session_id,
            "symbol": symbol,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Failed to get chart signals: {str(e)}")
