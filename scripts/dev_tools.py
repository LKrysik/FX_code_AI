#!/usr/bin/env python
"""
Development Tools for FXcrypto Testing and Diagnostics

This script provides utilities for:
- Starting/stopping backend and frontend
- Running tests
- Checking service health
- Generating test data
- Database diagnostics

Usage:
    python scripts/dev_tools.py --help
    python scripts/dev_tools.py status        # Check all services
    python scripts/dev_tools.py start         # Start backend
    python scripts/dev_tools.py test-api      # Run API tests
    python scripts/dev_tools.py gen-data      # Generate test data
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import random
import uuid

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_service_health(url: str, timeout: int = 5, expect_json: bool = True) -> Dict[str, Any]:
    """Check if a service is healthy."""
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read().decode()
            if expect_json:
                data = json.loads(content)
                return {"status": "healthy", "data": data}
            else:
                # For HTML responses, just check we got content
                return {"status": "healthy", "data": {"content_length": len(content)}}
    except urllib.error.URLError as e:
        return {"status": "unreachable", "error": str(e.reason)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_port(port: int) -> bool:
    """Check if a port is in use (listening)."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0  # Port is in use if connection succeeds
    except Exception:
        return False


def check_all_services():
    """Check status of all services."""
    print("\n=== FXcrypto Service Status ===\n")

    services = [
        ("Backend (FastAPI)", "http://localhost:8080/health", 8080, True),
        ("QuestDB Web UI", "http://localhost:9000", 9000, False),
        ("QuestDB PostgreSQL", None, 8812, None),
        ("QuestDB ILP", None, 9009, None),
        ("Frontend (Next.js)", "http://localhost:3000", 3000, False),
    ]

    all_healthy = True
    for name, url, port, expect_json in services:
        port_status = "OPEN" if check_port(port) else "CLOSED"

        if url:
            result = check_service_health(url, expect_json=expect_json if expect_json is not None else True)
            if result["status"] == "healthy":
                print(f"  [OK] {name} - Port {port}: {port_status}")
            else:
                print(f"  [X]  {name} - Port {port}: {port_status} - {result.get('error', 'Unknown error')}")
                all_healthy = False
        else:
            if port_status == "OPEN":
                print(f"  [OK] {name} - Port {port}: {port_status}")
            else:
                print(f"  [X]  {name} - Port {port}: {port_status}")
                all_healthy = False

    print()
    return all_healthy


def start_backend():
    """Start the backend server."""
    print("Starting backend server...")
    subprocess.Popen(
        ["python", "-m", "uvicorn",
         "src.api.unified_server:create_unified_app",
         "--factory", "--host", "0.0.0.0", "--port", "8080"],
        cwd=PROJECT_ROOT,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    )
    print("Backend started in new console window.")


def start_frontend():
    """Start the frontend server."""
    print("Starting frontend server...")
    frontend_path = PROJECT_ROOT / "frontend"
    subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_path,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
        shell=True
    )
    print("Frontend started in new console window.")


async def generate_test_data(session_id: Optional[str] = None,
                             symbols: List[str] = None,
                             duration_seconds: int = 300,
                             interval_ms: int = 100) -> Dict[str, Any]:
    """
    Generate synthetic test data for backtesting.
    Creates pump-and-dump style price movements.
    """
    try:
        # Import QuestDB provider
        from src.data_feed.questdb_provider import QuestDBProvider

        if session_id is None:
            session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if symbols is None:
            symbols = ["BTC_USDT", "ETH_USDT", "DOGE_USDT"]

        print(f"\nGenerating test data for session: {session_id}")
        print(f"Symbols: {symbols}")
        print(f"Duration: {duration_seconds}s, Interval: {interval_ms}ms")

        # Initialize QuestDB provider
        provider = QuestDBProvider(
            ilp_host="localhost",
            ilp_port=9009,
            pg_host="localhost",
            pg_port=8812,
            pg_user="admin",
            pg_password="quest",
            pg_database="qdb"
        )

        # Generate data points
        base_prices = {
            "BTC_USDT": 45000.0,
            "ETH_USDT": 2500.0,
            "DOGE_USDT": 0.08,
        }

        start_time = datetime.utcnow()
        num_points = (duration_seconds * 1000) // interval_ms
        records_written = 0

        print(f"Generating {num_points} data points per symbol...")

        for i in range(num_points):
            current_time = start_time + timedelta(milliseconds=i * interval_ms)

            for symbol in symbols:
                base_price = base_prices.get(symbol, 100.0)

                # Simulate pump-and-dump pattern
                # Phase 1 (0-30%): Accumulation - slight upward trend
                # Phase 2 (30-50%): Pump - sharp increase
                # Phase 3 (50-60%): Distribution - peak with volatility
                # Phase 4 (60-100%): Dump - sharp decrease

                progress = i / num_points

                if progress < 0.3:
                    # Accumulation phase
                    trend = 1.0 + (progress / 0.3) * 0.02
                    volatility = 0.002
                elif progress < 0.5:
                    # Pump phase
                    pump_progress = (progress - 0.3) / 0.2
                    trend = 1.02 + pump_progress * 0.15
                    volatility = 0.005
                elif progress < 0.6:
                    # Distribution phase (peak)
                    trend = 1.17 + random.uniform(-0.02, 0.02)
                    volatility = 0.01
                else:
                    # Dump phase
                    dump_progress = (progress - 0.6) / 0.4
                    trend = 1.17 - dump_progress * 0.20
                    volatility = 0.008

                # Calculate price with noise
                noise = random.gauss(0, volatility)
                price = base_price * trend * (1 + noise)

                # Generate volume (higher during pump/dump)
                base_volume = 1000
                if 0.3 < progress < 0.6:
                    volume = base_volume * random.uniform(3, 10)
                else:
                    volume = base_volume * random.uniform(0.5, 2)

                # Write to QuestDB
                try:
                    provider.write_tick_data(
                        session_id=session_id,
                        symbol=symbol,
                        timestamp=current_time,
                        price=price,
                        volume=volume,
                        quote_volume=price * volume
                    )
                    records_written += 1
                except Exception as e:
                    print(f"Error writing tick: {e}")

            # Show progress every 10%
            if (i + 1) % (num_points // 10) == 0:
                pct = ((i + 1) / num_points) * 100
                print(f"  Progress: {pct:.0f}%")

        # Flush the sender
        provider.flush()

        print(f"\nGenerated {records_written} records for session {session_id}")

        return {
            "status": "success",
            "session_id": session_id,
            "symbols": symbols,
            "records_written": records_written,
            "duration_seconds": duration_seconds
        }

    except ImportError as e:
        print(f"Error: Could not import QuestDB provider: {e}")
        print("Make sure questdb package is installed: pip install questdb")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        print(f"Error generating test data: {e}")
        return {"status": "error", "error": str(e)}


def run_api_tests(verbose: bool = False):
    """Run API tests."""
    print("\n=== Running API Tests ===\n")

    test_path = PROJECT_ROOT / "tests_e2e"
    if not test_path.exists():
        print(f"Test directory not found: {test_path}")
        return False

    cmd = ["python", "-m", "pytest", str(test_path / "api"), "-v" if verbose else ""]
    cmd = [c for c in cmd if c]  # Remove empty strings

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode == 0


def run_frontend_tests(verbose: bool = False):
    """Run frontend tests with Playwright."""
    print("\n=== Running Frontend Tests ===\n")

    test_path = PROJECT_ROOT / "tests_e2e" / "frontend"
    if not test_path.exists():
        print(f"Frontend test directory not found: {test_path}")
        return False

    cmd = ["python", "-m", "pytest", str(test_path), "-v" if verbose else ""]
    cmd = [c for c in cmd if c]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode == 0


def check_database():
    """Check QuestDB status and tables."""
    print("\n=== QuestDB Status ===\n")

    try:
        import asyncpg

        async def check_db():
            conn = await asyncpg.connect(
                host='localhost',
                port=8812,
                user='admin',
                password='quest',
                database='qdb'
            )

            # Get tables
            tables = await conn.fetch("""
                SELECT name, partitionBy, designatedTimestamp, walEnabled
                FROM tables()
            """)

            print("Tables:")
            for table in tables:
                print(f"  - {table['name']} (partition: {table['partitionby']}, WAL: {table['walenabled']})")

            # Check tick_prices count
            try:
                count = await conn.fetchval("SELECT count() FROM tick_prices")
                print(f"\ntick_prices records: {count}")
            except:
                print("\ntick_prices table not found or empty")

            # Check strategies count
            try:
                count = await conn.fetchval("SELECT count() FROM strategies")
                print(f"strategies records: {count}")
            except:
                print("strategies table not found or empty")

            await conn.close()
            return True

        return asyncio.run(check_db())

    except ImportError:
        print("asyncpg not installed. Install with: pip install asyncpg")
        return False
    except Exception as e:
        print(f"Database check failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="FXcrypto Development Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/dev_tools.py status          Check all services
  python scripts/dev_tools.py start           Start backend
  python scripts/dev_tools.py test-api        Run API tests
  python scripts/dev_tools.py gen-data        Generate test data
  python scripts/dev_tools.py check-db        Check database status
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    subparsers.add_parser("status", help="Check all service status")

    # Start commands
    start_parser = subparsers.add_parser("start", help="Start services")
    start_parser.add_argument("--all", action="store_true", help="Start all services")
    start_parser.add_argument("--frontend", action="store_true", help="Start frontend only")

    # Test commands
    test_parser = subparsers.add_parser("test-api", help="Run API tests")
    test_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    test_fe_parser = subparsers.add_parser("test-frontend", help="Run frontend tests")
    test_fe_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # Generate data command
    gen_parser = subparsers.add_parser("gen-data", help="Generate test data")
    gen_parser.add_argument("--session-id", help="Session ID for generated data")
    gen_parser.add_argument("--symbols", nargs="+", help="Symbols to generate data for")
    gen_parser.add_argument("--duration", type=int, default=300, help="Duration in seconds")
    gen_parser.add_argument("--interval", type=int, default=100, help="Interval in milliseconds")

    # Database check
    subparsers.add_parser("check-db", help="Check database status")

    args = parser.parse_args()

    if args.command == "status":
        check_all_services()
    elif args.command == "start":
        if args.frontend:
            start_frontend()
        else:
            start_backend()
            if args.all:
                time.sleep(3)
                start_frontend()
    elif args.command == "test-api":
        run_api_tests(verbose=args.verbose)
    elif args.command == "test-frontend":
        run_frontend_tests(verbose=args.verbose)
    elif args.command == "gen-data":
        asyncio.run(generate_test_data(
            session_id=args.session_id,
            symbols=args.symbols,
            duration_seconds=args.duration,
            interval_ms=args.interval
        ))
    elif args.command == "check-db":
        check_database()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
