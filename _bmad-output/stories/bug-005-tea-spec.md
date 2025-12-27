# BUG-005 TEA Test Specification

**Epic:** BUG-005 - DEFINITIVE FIX
**Story:** BUG-005-5 - TEA Integration Tests
**Agent:** TEA (Test Engineering Architect)
**Status:** Ready for TEA execution

---

## Test Objective

Create comprehensive tests that would have DETECTED BUG-005 BEFORE production. These tests must FAIL on current code and PASS after fix.

---

## Test Suite 1: Strategy Activation Pipeline Tests

### Test 1.1: Paper Trading Session Activates Strategy

**File:** `tests/integration/test_paper_trading_activation.py`

```python
# Pseudo-code specification
class TestPaperTradingActivation:

    async def test_session_creation_activates_strategy(self):
        """
        GIVEN: A valid strategy exists in database
        WHEN: User creates paper trading session with that strategy
        THEN: StrategyManager has active strategy entry
        """
        # Setup
        strategy_id = await create_test_strategy("Test Strategy")
        symbols = ["BTC/USDT"]

        # Action - call paper trading route
        response = await client.post("/api/paper-trading/sessions", json={
            "strategy_id": strategy_id,
            "strategy_name": "Test Strategy",
            "symbols": symbols,
            "mode": "paper"
        })

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # CRITICAL ASSERTION - This would FAIL currently
        strategy_manager = get_strategy_manager()
        active_strategies = strategy_manager.get_active_strategies_for_symbol("BTC/USDT")

        assert len(active_strategies) > 0, "Strategy should be activated after session creation"
        assert "Test Strategy" in [s.name for s in active_strategies]

    async def test_session_creates_indicator_variants(self):
        """
        GIVEN: Strategy with PUMP_MAGNITUDE_PCT condition
        WHEN: Paper trading session starts
        THEN: Indicator engine has variant for that indicator
        """
        # Setup
        strategy = create_strategy_with_condition("PUMP_MAGNITUDE_PCT")

        # Action
        await create_paper_trading_session(strategy.id)

        # CRITICAL ASSERTION
        indicator_engine = get_indicator_engine()
        variants = indicator_engine.get_variants_for_symbol("BTC/USDT")

        assert "PUMP_MAGNITUDE_PCT" in [v.indicator_name for v in variants]

    async def test_state_machine_shows_active_instance(self):
        """
        GIVEN: Paper trading session created
        WHEN: Querying state machine endpoint
        THEN: Active strategy instance returned
        """
        # Setup
        session = await create_paper_trading_session_with_strategy()

        # Action
        response = await client.get(f"/api/state-machine/{session.session_id}/state")

        # CRITICAL ASSERTION
        data = response.json()
        assert data["current_state"] != "IDLE", "Session should not be IDLE"
        assert len(data["instances"]) > 0, "Should have active instances"
```

### Test 1.2: Execution Controller Integration

```python
async def test_paper_trading_registers_with_execution_controller(self):
    """
    GIVEN: Paper trading session created via routes
    WHEN: Querying execution controller
    THEN: Session is registered and active
    """
    session_id = await create_paper_trading_session()

    controller = get_execution_controller()
    session = controller.get_current_session()

    assert session is not None, "Session should be in ExecutionController"
    assert session.session_id == session_id
    assert session.status == "RUNNING"
```

---

## Test Suite 2: WebSocket Stability Tests

### Test 2.1: Connection Persistence

**File:** `tests/integration/test_websocket_stability.py`

```python
class TestWebSocketStability:

    async def test_connection_survives_5_minutes(self):
        """
        GIVEN: Established WebSocket connection
        WHEN: 5 minutes pass with normal heartbeat
        THEN: Connection remains open without reconnect
        """
        ws = await connect_websocket()
        reconnect_count = 0

        def on_reconnect():
            nonlocal reconnect_count
            reconnect_count += 1

        ws.on_reconnect = on_reconnect

        # Wait 5 minutes
        await asyncio.sleep(300)

        assert ws.is_connected, "WebSocket should still be connected"
        assert reconnect_count == 0, "Should have zero reconnects in 5 minutes"

    async def test_pong_timeout_30_seconds(self):
        """
        GIVEN: WebSocket with delayed pong response
        WHEN: Pong arrives at 15 seconds (within 30s timeout)
        THEN: Connection remains stable, no missed pong counted
        """
        ws = await connect_websocket()

        # Mock delayed pong at 15 seconds
        mock_server.set_pong_delay(15_000)

        # Trigger heartbeat cycle
        await ws.heartbeat()
        await asyncio.sleep(20)  # Wait past old 10s timeout

        assert ws.missed_pongs == 0, "15s delay should not count as missed pong"
        assert ws.is_connected, "Should remain connected"

    async def test_no_duplicate_heartbeat_timers(self):
        """
        GIVEN: WebSocket initialized
        WHEN: Checking internal heartbeat state
        THEN: Only single heartbeat timer exists
        """
        ws = await connect_websocket()

        # This tests for the duplicate heartbeat bug
        assert ws._heartbeat_timers_count() == 1, "Should have exactly one heartbeat timer"
```

### Test 2.2: Message Validation

```python
async def test_subscription_without_stream_rejected(self):
    """
    GIVEN: Malformed subscription message (missing stream)
    WHEN: Attempting to send via sendMessage()
    THEN: Message rejected at client side, not sent to server
    """
    ws = await connect_websocket()

    with pytest.raises(ValidationError):
        ws.sendMessage({"type": "subscribe", "params": {}})  # Missing stream

    # Verify nothing sent to server
    assert mock_server.messages_received == 0

async def test_subscription_with_stream_accepted(self):
    """
    GIVEN: Valid subscription message
    WHEN: Sending via subscribe()
    THEN: Message sent with stream field
    """
    ws = await connect_websocket()

    ws.subscribe("market_data", {"symbol": "BTC/USDT"})

    message = mock_server.last_message
    assert message["type"] == "subscribe"
    assert message["stream"] == "market_data"  # Required field present
```

---

## Test Suite 3: End-to-End Tests

**File:** `tests/e2e/test_paper_trading_dashboard.py`

```python
class TestPaperTradingE2E:

    async def test_full_paper_trading_flow(self, browser):
        """
        Complete user journey: select strategy → start session → see data
        """
        page = await browser.new_page()
        await page.goto("/dashboard?mode=paper")

        # Step 1: Select strategy
        await page.click("[data-testid='strategy-selector']")
        await page.click("[data-testid='strategy-option-test-momentum']")

        # Step 2: Select symbols
        await page.click("[data-testid='symbol-BTC-USDT']")

        # Step 3: Start session
        await page.click("[data-testid='start-session-btn']")

        # Step 4: Wait for session active
        await page.wait_for_selector("[data-testid='session-status-running']")

        # CRITICAL ASSERTIONS
        # State Machine should show the strategy
        state_machine = await page.query_selector("[data-testid='state-machine-overview']")
        instances_text = await state_machine.text_content()

        assert "No active instances" not in instances_text, \
            "State Machine should show active strategy"
        assert "Test Momentum" in instances_text, \
            "Selected strategy should appear"

        # WebSocket should remain stable
        await asyncio.sleep(60)  # Wait 1 minute

        ws_status = await page.query_selector("[data-testid='ws-status']")
        status_text = await ws_status.text_content()

        assert "disconnected" not in status_text.lower(), \
            "WebSocket should remain connected"

    async def test_dashboard_recovers_after_reconnect(self, browser):
        """
        Test that dashboard state persists through WebSocket reconnect
        """
        page = await browser.new_page()
        await setup_active_session(page)

        # Force disconnect
        await page.evaluate("window.wsService.disconnect()")
        await asyncio.sleep(2)

        # Should auto-reconnect
        await page.wait_for_selector("[data-testid='ws-status-connected']", timeout=10000)

        # Subscriptions should be restored
        state_machine = await page.query_selector("[data-testid='state-machine-overview']")
        assert "No active instances" not in await state_machine.text_content()
```

---

## Test Execution Requirements

### Before Fix (Expected Results)

| Test | Expected Result |
|------|-----------------|
| `test_session_creation_activates_strategy` | **FAIL** - StrategyManager empty |
| `test_state_machine_shows_active_instance` | **FAIL** - instances = 0 |
| `test_connection_survives_5_minutes` | **FAIL** - reconnects occur |
| `test_pong_timeout_30_seconds` | **FAIL** - old 10s timeout triggers |
| `test_full_paper_trading_flow` | **FAIL** - "No active instances" appears |

### After Fix (Expected Results)

| Test | Expected Result |
|------|-----------------|
| `test_session_creation_activates_strategy` | **PASS** |
| `test_state_machine_shows_active_instance` | **PASS** |
| `test_connection_survives_5_minutes` | **PASS** |
| `test_pong_timeout_30_seconds` | **PASS** |
| `test_full_paper_trading_flow` | **PASS** |

---

## CI Integration

```yaml
# .github/workflows/test.yml
jobs:
  bug-005-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup
        run: |
          npm ci
          pip install -r requirements.txt

      - name: Integration Tests
        run: |
          pytest tests/integration/test_paper_trading_activation.py -v
          pytest tests/integration/test_websocket_stability.py -v

      - name: E2E Tests
        run: |
          pytest tests/e2e/test_paper_trading_dashboard.py -v

      - name: Verify No Regressions
        run: |
          # These tests must pass - block merge if fail
          pytest tests/integration/ tests/e2e/ --tb=short
```

---

## TEA Handoff

**For TEA Agent:**
1. Implement tests from this specification
2. Verify tests FAIL before fix (confirms they detect the bug)
3. After dev fix, verify tests PASS
4. Add to CI to prevent regression

**Quality Gate:** BUG-005 cannot be marked "Done" until all tests pass.

---

*Test Specification by PM Agent*
*Ready for TEA Agent Implementation*
