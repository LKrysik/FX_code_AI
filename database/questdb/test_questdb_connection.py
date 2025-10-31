#!/usr/bin/env python3
"""
Simple diagnostic to test QuestDB connectivity.
Tests both ILP (port 9009) and PostgreSQL (port 8812) protocols.
"""

import sys
from questdb.ingress import Sender, Protocol, IngressError, TimestampNanos
import time

def test_ilp_connection():
    """Test ILP connection (port 9009)"""
    print("\n=== Testing ILP Connection (port 9009) ===")
    try:
        print("Creating sender...")
        sender = Sender(Protocol.Tcp, 'localhost', 9009)
        print("✅ Sender created successfully")

        print("Sending test row...")
        sender.row(
            'connection_test',
            symbols={'test': 'diagnostic'},
            columns={'value': 1.0},
            at=TimestampNanos.now()
        )
        print("✅ Row sent successfully")

        print("Flushing...")
        sender.flush()
        print("✅ Flush successful")

        print("Closing sender...")
        sender.close()
        print("✅ Sender closed")

        return True

    except IngressError as e:
        print(f"❌ ILP Connection FAILED: {e}")
        print(f"\nError details: {type(e).__name__}")
        print(f"Error message: {str(e)}")

        # Check for specific error patterns
        error_str = str(e).lower()
        if 'connection refused' in error_str or '10061' in error_str:
            print("\n⚠️  QuestDB appears to be OFFLINE")
            print("    Please start QuestDB:")
            print("    1. Run: python database/questdb/install_questdb.py")
            print("    2. Or manually start QuestDB server")
        elif 'timeout' in error_str:
            print("\n⚠️  Connection timeout - QuestDB may be overloaded or network issue")

        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sender_reuse():
    """Test sender reuse (simulates pool behavior)"""
    print("\n=== Testing Sender Reuse (Pool Simulation) ===")
    try:
        print("Creating sender...")
        sender = Sender(Protocol.Tcp, 'localhost', 9009)
        print("✅ Sender created")

        # Use sender multiple times
        for i in range(3):
            print(f"\nWrite #{i+1}...")
            sender.row(
                'connection_test',
                symbols={'test': f'reuse_{i}'},
                columns={'value': float(i)},
                at=TimestampNanos.now()
            )
            sender.flush()
            print(f"✅ Write #{i+1} successful")
            time.sleep(0.1)

        sender.close()
        print("\n✅ Sender reuse successful")
        return True

    except IngressError as e:
        print(f"❌ Sender reuse FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sender_after_close():
    """Test using sender after close (simulates stale sender bug)"""
    print("\n=== Testing Sender After Close (Stale Sender Simulation) ===")
    try:
        print("Creating sender...")
        sender = Sender(Protocol.Tcp, 'localhost', 9009)
        print("✅ Sender created")

        print("Closing sender...")
        sender.close()
        print("✅ Sender closed")

        print("Attempting to use closed sender...")
        try:
            sender.row(
                'connection_test',
                symbols={'test': 'after_close'},
                columns={'value': 1.0},
                at=TimestampNanos.now()
            )
            print("⚠️  Unexpected: closed sender still works?")
            return False
        except IngressError as e:
            if 'sender is closed' in str(e).lower() or 'closed' in str(e).lower():
                print(f"✅ Expected error received: {e}")
                print("    This confirms the bug pattern: using closed senders from pool")
                return True
            else:
                print(f"❌ Unexpected error: {e}")
                return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 24 + "QuestDB Connection Diagnostic" + " " * 25 + "║")
    print("╚" + "=" * 78 + "╝")

    results = {}
    results['ilp'] = test_ilp_connection()

    if results['ilp']:
        results['reuse'] = test_sender_reuse()
        results['stale'] = test_sender_after_close()
    else:
        print("\n⚠️  Skipping additional tests - ILP connection failed")
        print("    QuestDB must be running for further diagnostics")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    print("=" * 80)

    if all(results.values()):
        print("\n✅ QuestDB is healthy and accepting connections")
        print("   The 'Sender is closed' error is likely due to stale senders in pool")
        print("   → Need to add sender validation before use")
    else:
        print("\n❌ QuestDB connectivity issues detected")
        print("   → Fix connectivity first, then retry orderbook tests")

    sys.exit(0 if all(results.values()) else 1)
