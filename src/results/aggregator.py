"""
Results Aggregation Utilities
=============================
Merge historical session results (signals, trades, summaries) across sessions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os


def _load_json_file(path: Path) -> Optional[Any]:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        # Do not silently swallow errors; log a warning for diagnostics
        print(f"WARNING: Failed to load JSON file {path}: {e}")
        return None
    return None


def discover_sessions(base_dir: str | Path) -> List[str]:
    base = Path(base_dir)
    if not base.exists():
        return []
    return [p.name for p in base.iterdir() if p.is_dir()]


def merge_sessions(base_dir: str | Path, session_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    base = Path(base_dir)
    if not base.exists():
        return {"sessions": [], "totals": {}, "symbols": []}

    if not session_ids:
        session_ids = discover_sessions(base)

    merged_symbols: set[str] = set()
    merged_sessions: List[Dict[str, Any]] = []
    total_pnl = 0.0
    total_fees = 0.0
    total_trades = 0
    winning_trades = 0
    losing_trades = 0

    best_trade = None
    worst_trade = None

    for sid in session_ids:
        sdir = base / sid
        if not sdir.exists():
            continue

        summary = _load_json_file(sdir / "session_summary.json") or {}
        trades = _load_json_file(sdir / "trades.json") or []
        signals = _load_json_file(sdir / "signals.json") or []

        # Symbols
        symbols = summary.get("symbols") or []
        for sym in symbols:
            merged_symbols.add(sym)

        # Aggregate metrics
        total_pnl += float(summary.get("total_pnl", 0.0))
        total_fees += float(summary.get("total_fees", 0.0))
        total_trades += int(summary.get("total_trades", 0))
        winning_trades += int(summary.get("winning_trades", 0))
        losing_trades += int(summary.get("losing_trades", 0))

        # Track best/worst trades
        for t in trades:
            pnl = float(t.get("total_pnl", 0.0))
            if best_trade is None or pnl > best_trade.get("total_pnl", 0.0):
                best_trade = t
            if worst_trade is None or pnl < worst_trade.get("total_pnl", 0.0):
                worst_trade = t

        merged_sessions.append({
            "session_id": sid,
            "summary": summary,
            "trades_count": len(trades),
            "signals_count": len(signals),
        })

    net_pnl = total_pnl - total_fees
    win_rate = (winning_trades / total_trades * 100.0) if total_trades else 0.0

    totals = {
        "total_pnl": total_pnl,
        "total_fees": total_fees,
        "net_pnl": net_pnl,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
    }

    return {
        "sessions": merged_sessions,
        "totals": totals,
        "symbols": sorted(list(merged_symbols)),
    }


def _load_json_file_safe(path: Path, max_size_mb: float = 10.0) -> Optional[Any]:
    """✅ PERFORMANCE: Safe JSON loading with size limits and proper error handling"""
    try:
        if not path.exists():
            return None

        # ✅ FILE SIZE PROTECTION: Check file size before loading
        file_size = path.stat().st_size
        if file_size > max_size_mb * 1024 * 1024:  # Convert MB to bytes
            raise ValueError(f"File too large: {path} ({file_size / (1024*1024):.1f}MB > {max_size_mb}MB)")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        # ✅ ERROR HANDLING: Specific error for JSON corruption
        print(f"WARNING: Corrupted JSON file {path}: {e}")
        return None
    except PermissionError as e:
        # ✅ ERROR HANDLING: Specific error for permission issues
        print(f"WARNING: Permission denied reading {path}: {e}")
        return None
    except Exception as e:
        # ✅ ERROR HANDLING: Log other errors but don't crash
        print(f"WARNING: Error reading {path}: {e}")
        return None


async def merge_sessions_async(base_dir: str | Path, session_ids: Optional[List[str]] = None,
                              max_file_size_mb: float = 10.0, max_symbols: int = 1000) -> Dict[str, Any]:
    """
    ✅ PERFORMANCE OPTIMIZED: Async version with concurrent I/O and memory management

    Key improvements:
    - Concurrent file loading with ThreadPoolExecutor
    - File size limits to prevent OOM
    - Bounded symbol collections
    - Safe type conversions with error handling
    - Single-pass trade analysis (no quadratic complexity)
    """
    base = Path(base_dir)
    if not base.exists():
        return {"sessions": [], "totals": {}, "symbols": []}

    if not session_ids:
        session_ids = discover_sessions(base)

    # ✅ MEMORY MANAGEMENT: Bounded collections
    merged_symbols: set[str] = set()
    merged_sessions: List[Dict[str, Any]] = []
    total_pnl = 0.0
    total_fees = 0.0
    total_trades = 0
    winning_trades = 0
    losing_trades = 0

    best_trade = None
    worst_trade = None

    # ✅ PERFORMANCE: Process sessions in batches for memory efficiency
    batch_size = 10
    session_batches = [session_ids[i:i + batch_size] for i in range(0, len(session_ids), batch_size)]

    for batch in session_batches:
        # ✅ CONCURRENT I/O: Load session data in parallel
        session_data = await _load_session_batch_async(base, batch, max_file_size_mb)

        for sid, data in session_data.items():
            if data is None:
                continue

            summary, trades, signals = data

            # ✅ SAFE TYPE CONVERSIONS: With error handling
            try:
                session_pnl = float(summary.get("total_pnl", 0.0))
                session_fees = float(summary.get("total_fees", 0.0))
                session_trades = int(summary.get("total_trades", 0))
                session_winning = int(summary.get("winning_trades", 0))
                session_losing = int(summary.get("losing_trades", 0))
            except (ValueError, TypeError) as e:
                print(f"WARNING: Invalid data types in session {sid}: {e}")
                continue

            # ✅ MEMORY MANAGEMENT: Bounded symbol collection
            symbols = summary.get("symbols") or []
            for sym in symbols:
                if isinstance(sym, str) and len(merged_symbols) < max_symbols:
                    merged_symbols.add(sym)

            # Aggregate metrics
            total_pnl += session_pnl
            total_fees += session_fees
            total_trades += session_trades
            winning_trades += session_winning
            losing_trades += session_losing

            # ✅ PERFORMANCE: Single-pass trade analysis (no quadratic complexity)
            for t in trades:
                try:
                    pnl = float(t.get("total_pnl", 0.0))
                    if best_trade is None or pnl > best_trade.get("total_pnl", 0.0):
                        best_trade = t
                    if worst_trade is None or pnl < worst_trade.get("total_pnl", 0.0):
                        worst_trade = t
                except (ValueError, TypeError):
                    continue  # Skip invalid trade data

            merged_sessions.append({
                "session_id": sid,
                "summary": summary,
                "trades_count": len(trades),
                "signals_count": len(signals),
            })

    # Calculate final metrics
    net_pnl = total_pnl - total_fees
    win_rate = (winning_trades / total_trades * 100.0) if total_trades else 0.0

    totals = {
        "total_pnl": total_pnl,
        "total_fees": total_fees,
        "net_pnl": net_pnl,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
    }

    return {
        "sessions": merged_sessions,
        "totals": totals,
        "symbols": sorted(list(merged_symbols)),
    }


async def _load_session_batch_async(base: Path, session_ids: List[str], max_file_size_mb: float) -> Dict[str, Optional[Tuple[Dict, List, List]]]:
    """✅ CONCURRENT I/O: Load multiple sessions in parallel"""

    async def load_single_session(sid: str) -> Tuple[str, Optional[Tuple[Dict, List, List]]]:
        """Load data for a single session"""
        sdir = base / sid
        if not sdir.exists():
            return sid, None

        try:
            # Check file sizes before loading
            files_to_check = [
                sdir / "session_summary.json",
                sdir / "trades.json",
                sdir / "signals.json"
            ]

            for file_path in files_to_check:
                if file_path.exists() and file_path.stat().st_size > max_file_size_mb * 1024 * 1024:
                    print(f"WARNING: Skipping session {sid} - file too large: {file_path}")
                    return sid, None

            # Load files concurrently using ThreadPoolExecutor
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=3) as executor:
                tasks = [
                    loop.run_in_executor(executor, _load_json_file_safe, sdir / "session_summary.json", max_file_size_mb),
                    loop.run_in_executor(executor, _load_json_file_safe, sdir / "trades.json", max_file_size_mb),
                    loop.run_in_executor(executor, _load_json_file_safe, sdir / "signals.json", max_file_size_mb)
                ]

                summary, trades, signals = await asyncio.gather(*tasks)

                # Apply consistent defaults
                summary = summary or {}
                trades = trades or []
                signals = signals or []

                return sid, (summary, trades, signals)

        except Exception as e:
            print(f"WARNING: Error loading session {sid}: {e}")
            return sid, None

    # Load all sessions in the batch concurrently
    tasks = [load_single_session(sid) for sid in session_ids]
    results = await asyncio.gather(*tasks)

    return dict(results)
