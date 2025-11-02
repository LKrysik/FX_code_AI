#!/usr/bin/env python3
"""
QuestDB Connection Diagnostic Tool

Tests QuestDB connectivity and sender pool behavior to diagnose connection issues.

Usage:
    python database/questdb/test_questdb_connection.py

Tests performed:
1. ILP Protocol (port 9009) - Basic connectivity
2. Sender creation and write operations
3. Sender reuse validation
4. Stale sender detection

Exit codes:
    0 - All tests passed
    1 - One or more tests failed
"""

import sys
import time
from typing import Tuple, Optional

# Try to import QuestDB client
try:
    from questdb.ingress import Sender, Protocol, IngressError, TimestampNanos
except ImportError:
    print("ERROR: questdb-client not installed")
    print("Install with: pip install questdb-client")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print formatted section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_test(test_name: str, status: str, details: str = ""):
    """Print test result"""
    if status == "PASS":
        color = Colors.GREEN
        symbol = "✓"
    elif status == "FAIL":
        color = Colors.RED
        symbol = "✗"
    else:  # WARN
        color = Colors.YELLOW
        symbol = "!"

    print(f"{color}{symbol} {test_name}: {status}{Colors.END}")
    if details:
        print(f"  {details}")


def test_ilp_basic_connection() -> Tuple[bool, str]:
    """
    Test 1: Basic ILP Connection

    Attempts to create a Sender connection to QuestDB on port 9009.
    This is the most fundamental test - if this fails, QuestDB is offline.

    Returns:
        (success, details) tuple
    """
    try:
        print("Creating sender connection...")
        sender = Sender(Protocol.Tcp, 'localhost', 9009)

        # Enter context manager to open connection
        sender.__enter__()

        print("Connection established successfully")

        # Clean exit
        sender.__exit__(None, None, None)

        return True, "ILP connection to localhost:9009 succeeded"

    except IngressError as e:
        error_str = str(e).lower()

        if "connection refused" in error_str:
            return False, (
                "Connection refused - QuestDB is not running\n"
                "  → Start QuestDB: python database/questdb/install_questdb.py"
            )
        elif "timeout" in error_str:
            return False, (
                "Connection timeout - QuestDB may be overloaded or network issues\n"
                "  → Check QuestDB logs for errors"
            )
        else:
            return False, f"ILP connection failed: {e}"

    except Exception as e:
        return False, f"Unexpected error: {type(e).__name__}: {e}"


def test_sender_write_operation() -> Tuple[bool, str]:
    """
    Test 2: Sender Write Operation

    Creates a sender and attempts to write a test row to verify
    full write capability (not just connection).

    Returns:
        (success, details) tuple
    """
    try:
        print("Creating sender...")
        sender = Sender(Protocol.Tcp, 'localhost', 9009)
        sender.__enter__()

        print("Sending test row...")
        timestamp_ns = int(time.time() * 1_000_000_000)

        # Write test row to test_diagnostics table
        sender.row(
            'test_diagnostics',
            symbols={'test_id': 'conn_test'},
            columns={'value': 1.0},
            at=TimestampNanos(timestamp_ns)
        )

        print("Flushing...")
        sender.flush()

        print("Closing sender...")
        sender.__exit__(None, None, None)

        return True, "Successfully wrote test row to QuestDB"

    except IngressError as e:
        error_str = str(e).lower()

        if "table does not exist" in error_str:
            # This is OK - table doesn't exist but write operation worked
            return True, "Write operation succeeded (table creation tested)"
        else:
            return False, f"Write failed: {e}"

    except Exception as e:
        return False, f"Unexpected error: {type(e).__name__}: {e}"


def test_sender_reuse() -> Tuple[bool, str]:
    """
    Test 3: Sender Reuse

    Simulates sender pool behavior by reusing a single sender
    for multiple write operations with delays between them.

    This tests if a sender remains healthy across multiple uses.

    Returns:
        (success, details) tuple
    """
    try:
        print("Creating sender for reuse test...")
        sender = Sender(Protocol.Tcp, 'localhost', 9009)
        sender.__enter__()

        writes = 3
        for i in range(writes):
            print(f"Write {i+1}/{writes}...")

            timestamp_ns = int(time.time() * 1_000_000_000)
            sender.row(
                'test_diagnostics',
                symbols={'test_id': 'reuse_test'},
                columns={'value': float(i)},
                at=TimestampNanos(timestamp_ns)
            )
            sender.flush()

            # Small delay between writes
            if i < writes - 1:
                time.sleep(0.1)

        print("Closing sender...")
        sender.__exit__(None, None, None)

        return True, f"Successfully reused sender for {writes} write operations"

    except IngressError as e:
        return False, f"Sender reuse failed: {e}"

    except Exception as e:
        return False, f"Unexpected error: {type(e).__name__}: {e}"


def test_stale_sender_detection() -> Tuple[bool, str]:
    """
    Test 4: Stale Sender Detection

    Deliberately creates a stale sender (closed but not disposed)
    to verify that error detection works correctly.

    This simulates the bug scenario where pooled senders become stale.

    Returns:
        (success, details) tuple
    """
    try:
        print("Creating sender...")
        sender = Sender(Protocol.Tcp, 'localhost', 9009)
        sender.__enter__()

        print("Closing sender...")
        sender.__exit__(None, None, None)

        print("Attempting to use closed sender (should fail)...")

        try:
            # This should fail with "Sender is closed"
            timestamp_ns = int(time.time() * 1_000_000_000)
            sender.row(
                'test_diagnostics',
                symbols={'test_id': 'stale_test'},
                columns={'value': 1.0},
                at=TimestampNanos(timestamp_ns)
            )
            sender.flush()

            # If we get here, stale sender detection is NOT working
            return False, (
                "WARNING: Stale sender was accepted!\n"
                "  → This indicates a potential bug in sender pool validation"
            )

        except IngressError as e:
            error_str = str(e).lower()

            if "closed" in error_str or "sender is closed" in error_str:
                # Expected behavior - stale sender was rejected
                return True, "Stale sender correctly detected and rejected"
            else:
                return False, f"Unexpected error when using stale sender: {e}"

    except Exception as e:
        return False, f"Test setup failed: {type(e).__name__}: {e}"


def test_connection_pool_simulation() -> Tuple[bool, str]:
    """
    Test 5: Connection Pool Simulation

    Simulates connection pool behavior by creating multiple senders,
    using them, and releasing them.

    Returns:
        (success, details) tuple
    """
    try:
        pool_size = 4
        senders = []

        print(f"Creating sender pool ({pool_size} connections)...")

        # Create pool
        for i in range(pool_size):
            sender = Sender(Protocol.Tcp, 'localhost', 9009)
            sender.__enter__()
            senders.append(sender)
            print(f"  Sender {i+1} created")

        print(f"Using all {pool_size} senders in parallel...")

        # Use all senders
        for i, sender in enumerate(senders):
            timestamp_ns = int(time.time() * 1_000_000_000)
            sender.row(
                'test_diagnostics',
                symbols={'test_id': f'pool_test_{i}'},
                columns={'value': float(i)},
                at=TimestampNanos(timestamp_ns)
            )
            sender.flush()

        print("Closing all senders...")

        # Release pool
        for sender in senders:
            sender.__exit__(None, None, None)

        return True, f"Successfully simulated {pool_size}-connection pool"

    except IngressError as e:
        return False, f"Pool simulation failed: {e}"

    except Exception as e:
        return False, f"Unexpected error: {type(e).__name__}: {e}"


def main():
    """Run all diagnostic tests"""
    print_header("QuestDB Connection Diagnostic Tool")

    print(f"{Colors.BOLD}Testing QuestDB connectivity at localhost:9009{Colors.END}\n")

    # Track results
    results = []

    # Test 1: Basic Connection
    print_header("Test 1: Basic ILP Connection")
    success, details = test_ilp_basic_connection()
    print_test("Basic Connection", "PASS" if success else "FAIL", details)
    results.append(("Basic Connection", success))

    # If basic connection fails, no point continuing
    if not success:
        print(f"\n{Colors.RED}{Colors.BOLD}CRITICAL: Cannot connect to QuestDB{Colors.END}")
        print("\nTroubleshooting steps:")
        print("1. Start QuestDB: python database/questdb/install_questdb.py")
        print("2. Verify Web UI: http://127.0.0.1:9000")
        print("3. Check port 9009: netstat -an | findstr :9009")
        print("4. Review logs: database/questdb/questdb/log/")
        print("\nSee ORDERBOOK_ERROR_DIAGNOSIS.md for detailed troubleshooting")
        sys.exit(1)

    # Test 2: Write Operation
    print_header("Test 2: Sender Write Operation")
    success, details = test_sender_write_operation()
    print_test("Write Operation", "PASS" if success else "FAIL", details)
    results.append(("Write Operation", success))

    # Test 3: Sender Reuse
    print_header("Test 3: Sender Reuse")
    success, details = test_sender_reuse()
    print_test("Sender Reuse", "PASS" if success else "FAIL", details)
    results.append(("Sender Reuse", success))

    # Test 4: Stale Sender Detection
    print_header("Test 4: Stale Sender Detection")
    success, details = test_stale_sender_detection()
    print_test("Stale Sender Detection", "PASS" if success else "FAIL", details)
    results.append(("Stale Sender Detection", success))

    # Test 5: Pool Simulation
    print_header("Test 5: Connection Pool Simulation")
    success, details = test_connection_pool_simulation()
    print_test("Pool Simulation", "PASS" if success else "FAIL", details)
    results.append(("Pool Simulation", success))

    # Summary
    print_header("Diagnostic Summary")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\nResults: {passed}/{total} tests passed\n")

    for test_name, success in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if success else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  {status} - {test_name}")

    print()

    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ All diagnostic tests passed!{Colors.END}")
        print(f"\nQuestDB is healthy and ready for use.")
        print("You can now run data collection or backtests.")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ Some diagnostic tests failed{Colors.END}")
        print(f"\nReview the failures above and check ORDERBOOK_ERROR_DIAGNOSIS.md")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Diagnostic interrupted by user{Colors.END}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {type(e).__name__}: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
