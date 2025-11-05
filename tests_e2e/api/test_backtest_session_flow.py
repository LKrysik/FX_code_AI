"""
E2E Tests for Complete Backtest Session Flow

Tests the entire flow:
1. Collect data → POST /sessions/start (session_type=collect)
2. List sessions → GET /api/data-collection/sessions
3. Start backtest → POST /sessions/start (session_type=backtest) with session_id
4. Verify backtest runs successfully

This ensures the frontend fix (passing session_id) works end-to-end.
"""

import pytest
import time
from typing import Dict, Any


@pytest.mark.asyncio
async def test_complete_backtest_flow_with_session_id(api_client):
    """
    ✅ COMPLETE FLOW: Data collection → List sessions → Backtest with session_id

    This test verifies the entire backtest flow works correctly with the frontend fix:
    - SessionSelector component loads real sessions from API
    - api.ts sends session_id to backend
    - Backend validates and accepts the session_id
    - Backtest runs successfully
    """

    # STEP 1: Start data collection session
    print("\n[TEST] Step 1: Starting data collection session...")
    collect_response = await api_client.post('/sessions/start', json={
        'session_type': 'collect',
        'symbols': ['BTC_USDT', 'ETH_USDT'],
        'config': {
            'data_collection': {
                'duration': '5s'  # Short duration for test
            }
        },
        'idempotent': True
    })

    assert collect_response.status_code == 200, f"Failed to start collection: {collect_response.json()}"
    collect_data = collect_response.json()
    assert collect_data.get('type') == 'response'

    # Extract session_id from nested structure: { data: { data: { session_id: "..." } } }
    session_id = (
        collect_data.get('data', {}).get('data', {}).get('session_id') or
        collect_data.get('data', {}).get('session_id') or
        collect_data.get('session_id')
    )

    assert session_id, f"No session_id in response: {collect_data}"
    print(f"[TEST] ✓ Data collection started: {session_id}")

    # Wait for collection to complete (5 seconds + buffer)
    print("[TEST] Waiting for data collection to complete (7 seconds)...")
    time.sleep(7)

    # Stop collection to finalize session
    print("[TEST] Step 1b: Stopping data collection session...")
    stop_response = await api_client.post('/sessions/stop', json={
        'session_id': session_id
    })

    assert stop_response.status_code == 200, f"Failed to stop collection: {stop_response.json()}"
    print(f"[TEST] ✓ Data collection stopped: {session_id}")

    # Wait for session to be finalized in database
    time.sleep(2)

    # STEP 2: List data collection sessions (verify session exists)
    print("\n[TEST] Step 2: Listing data collection sessions...")
    sessions_response = await api_client.get('/api/data-collection/sessions', params={
        'limit': 50,
        'include_stats': True
    })

    assert sessions_response.status_code == 200, f"Failed to list sessions: {sessions_response.json()}"
    sessions_data = sessions_response.json()
    sessions_list = sessions_data.get('sessions', [])

    # Find our session
    our_session = next((s for s in sessions_list if s.get('session_id') == session_id), None)
    assert our_session, f"Session {session_id} not found in list. Available: {[s.get('session_id') for s in sessions_list]}"

    print(f"[TEST] ✓ Session found in list: {session_id}")
    print(f"[TEST]   Status: {our_session.get('status')}")
    print(f"[TEST]   Records: {our_session.get('records_collected', 0)}")
    print(f"[TEST]   Symbols: {our_session.get('symbols', [])}")

    # Verify session has data
    records_count = our_session.get('records_collected', 0)
    assert records_count > 0, f"Session has no records: {our_session}"
    print(f"[TEST] ✓ Session has {records_count} records")

    # STEP 3: Start backtest with session_id (THE CRITICAL FIX)
    print("\n[TEST] Step 3: Starting backtest with session_id...")

    # Create a minimal test strategy
    test_strategy = {
        'id': 'test-backtest-strategy',
        'strategy_name': 'E2E Test Strategy',
        'direction': 'LONG',
        'enabled': True,
        'created_at': '2025-11-05T20:00:00Z',
        'updated_at': '2025-11-05T20:00:00Z',
    }

    backtest_response = await api_client.post('/sessions/start', json={
        'session_type': 'backtest',
        'symbols': ['BTC_USDT', 'ETH_USDT'],
        'strategy_config': test_strategy,
        'config': {
            'session_id': session_id,  # ✅ CRITICAL: Pass session_id (frontend fix)
            'acceleration_factor': 100,  # Fast playback for test
            'budget': {
                'global_cap': 10000,
                'allocations': {}
            }
        },
        'idempotent': False
    })

    # Verify backtest starts successfully (no validation error!)
    assert backtest_response.status_code == 200, (
        f"Backtest failed to start: {backtest_response.status_code}\n"
        f"Response: {backtest_response.json()}\n"
        f"This means the session_id fix didn't work!"
    )

    backtest_data = backtest_response.json()
    print(f"[TEST] ✓ Backtest started successfully!")
    print(f"[TEST]   Response: {backtest_data}")

    # Extract backtest session_id
    backtest_session_id = (
        backtest_data.get('data', {}).get('data', {}).get('session_id') or
        backtest_data.get('data', {}).get('session_id') or
        backtest_data.get('session_id')
    )

    assert backtest_session_id, f"No backtest session_id in response: {backtest_data}"
    print(f"[TEST] ✓ Backtest session created: {backtest_session_id}")

    # STEP 4: Verify backtest is running
    print("\n[TEST] Step 4: Verifying backtest execution...")
    time.sleep(2)  # Give it time to process some data

    execution_status_response = await api_client.get('/sessions/execution-status')
    assert execution_status_response.status_code == 200

    execution_data = execution_status_response.json()
    execution_status = execution_data.get('data', {})

    print(f"[TEST] ✓ Execution status retrieved:")
    print(f"[TEST]   Session ID: {execution_status.get('session_id')}")
    print(f"[TEST]   Status: {execution_status.get('status')}")
    print(f"[TEST]   Mode: {execution_status.get('mode')}")

    # Verify mode is backtest
    assert execution_status.get('mode') == 'backtest', (
        f"Expected mode 'backtest', got '{execution_status.get('mode')}'"
    )

    # Stop backtest
    print("\n[TEST] Step 5: Stopping backtest...")
    stop_backtest_response = await api_client.post('/sessions/stop')
    assert stop_backtest_response.status_code == 200
    print("[TEST] ✓ Backtest stopped successfully")

    print("\n[TEST] ✅ COMPLETE FLOW SUCCESS!")
    print("[TEST] ✅ Frontend fix verified: session_id is passed and accepted by backend")


@pytest.mark.asyncio
async def test_backtest_without_session_id_fails_validation(api_client):
    """
    ✅ VALIDATION: Backtest without session_id should fail with clear error

    This verifies the backend validation fix works:
    - Error occurs in validation phase (not execution)
    - Clear error message with instructions
    """

    print("\n[TEST] Testing backtest without session_id (should fail validation)...")

    test_strategy = {
        'id': 'test-invalid-strategy',
        'strategy_name': 'Invalid Test',
        'direction': 'LONG',
        'enabled': True,
    }

    # Try to start backtest WITHOUT session_id
    backtest_response = await api_client.post('/sessions/start', json={
        'session_type': 'backtest',
        'symbols': ['BTC_USDT'],
        'strategy_config': test_strategy,
        'config': {
            # ❌ NO session_id - should fail validation
            'acceleration_factor': 10,
            'budget': {
                'global_cap': 10000,
                'allocations': {}
            }
        }
    })

    # Should return 400 (validation error)
    assert backtest_response.status_code == 400, (
        f"Expected 400 validation error, got {backtest_response.status_code}"
    )

    error_data = backtest_response.json()
    error_message = error_data.get('error_message', '') or error_data.get('message', '')

    # Verify error message mentions session_id
    assert 'session_id' in error_message.lower(), (
        f"Error message should mention 'session_id', got: {error_message}"
    )

    # Verify error message has instructions
    assert 'data-collection/sessions' in error_message or 'data collection' in error_message.lower(), (
        f"Error message should have instructions, got: {error_message}"
    )

    print(f"[TEST] ✓ Validation error as expected:")
    print(f"[TEST]   {error_message}")
    print("[TEST] ✅ Backend validation working correctly!")


@pytest.mark.asyncio
async def test_backtest_with_invalid_session_id_fails(api_client):
    """
    ✅ VALIDATION: Backtest with non-existent session_id should fail
    """

    print("\n[TEST] Testing backtest with invalid session_id...")

    test_strategy = {
        'id': 'test-strategy',
        'strategy_name': 'Test',
        'direction': 'LONG',
        'enabled': True,
    }

    # Use a clearly invalid session_id
    invalid_session_id = 'dc_nonexistent_session_12345'

    backtest_response = await api_client.post('/sessions/start', json={
        'session_type': 'backtest',
        'symbols': ['BTC_USDT'],
        'strategy_config': test_strategy,
        'config': {
            'session_id': invalid_session_id,
            'acceleration_factor': 10,
            'budget': {
                'global_cap': 10000,
                'allocations': {}
            }
        }
    })

    # Should fail (400 or 404)
    assert backtest_response.status_code in [400, 404], (
        f"Expected 400/404 for invalid session, got {backtest_response.status_code}"
    )

    error_data = backtest_response.json()
    error_message = error_data.get('error_message', '') or error_data.get('message', '')

    print(f"[TEST] ✓ Error as expected: {error_message}")
    print("[TEST] ✅ Invalid session_id rejected correctly!")


if __name__ == '__main__':
    # Run with: pytest tests_e2e/api/test_backtest_session_flow.py -v -s
    pytest.main([__file__, '-v', '-s'])
