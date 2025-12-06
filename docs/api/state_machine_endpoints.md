# State Machine API Endpoints

**Status:** ✅ IMPLEMENTED (2025-12-06)

API endpoints for exposing state machine status to UI.

## Architecture

- **ExecutionController** manages session-level state (IDLE, STARTING, RUNNING, PAUSED, STOPPING, STOPPED, ERROR)
- **StrategyManager** manages per-strategy-instance state (MONITORING, SIGNAL_DETECTED, ENTRY_EVALUATION, POSITION_ACTIVE, etc.)

## Endpoints

### 1. GET /api/sessions/{session_id}/state

Get current state machine status for a session.

**Performance Target:** <50ms

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Response:**
```json
{
  "session_id": "exec_20251206_100000_abc123",
  "current_state": "RUNNING",
  "since": "2025-12-06T10:00:00Z",
  "mode": "paper",
  "allowed_transitions": ["PAUSED", "STOPPING"],
  "instances": [
    {
      "strategy_id": "pump_peak_short",
      "symbol": "BTC_USDT",
      "state": "MONITORING",
      "since": "2025-12-06T10:00:00Z"
    },
    {
      "strategy_id": "pump_peak_short",
      "symbol": "ETH_USDT",
      "state": "SIGNAL_DETECTED",
      "since": "2025-12-06T10:05:23Z"
    }
  ]
}
```

**Session States:**
- `IDLE` - No active execution
- `STARTING` - Execution starting up
- `RUNNING` - Execution in progress
- `PAUSED` - Execution paused (can resume)
- `STOPPING` - Execution stopping
- `STOPPED` - Execution stopped
- `ERROR` - Execution error

**Strategy Instance States:**
- `INACTIVE` - Strategy not active
- `MONITORING` - Monitoring for S1 signal
- `SIGNAL_DETECTED` - S1 signal detected
- `SIGNAL_CANCELLED` - O1 cancellation triggered
- `ENTRY_EVALUATION` - Z1 entry evaluation
- `POSITION_ACTIVE` - Position opened
- `CLOSE_ORDER_EVALUATION` - ZE1 close evaluation
- `EMERGENCY_EXIT` - E1 emergency exit
- `EXITED` - Position closed

**Error Responses:**
- `500 Internal Server Error` - Failed to get session state

**Example (Session Not Found):**
```json
{
  "session_id": "unknown_session",
  "current_state": "IDLE",
  "since": null,
  "mode": null,
  "allowed_transitions": ["STARTING"],
  "instances": []
}
```

### 2. GET /api/sessions/{session_id}/transitions

Get state transition history for a session.

**Status:** ⚠️ PLACEHOLDER - Returns empty list (requires event persistence)

**Performance Target:** <100ms

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Response (Current - Empty):**
```json
{
  "session_id": "exec_20251206_100000_abc123",
  "transitions": []
}
```

**Response (Future - When Event Persistence Implemented):**
```json
{
  "session_id": "exec_20251206_100000_abc123",
  "transitions": [
    {
      "timestamp": "2025-12-06T10:05:23Z",
      "strategy_id": "pump_peak_short",
      "symbol": "ETH_USDT",
      "from_state": "MONITORING",
      "to_state": "SIGNAL_DETECTED",
      "trigger": "S1",
      "conditions": {
        "PUMP_MAGNITUDE_PCT": {
          "value": 7.2,
          "threshold": 5.0,
          "operator": ">",
          "met": true
        },
        "PRICE_VELOCITY": {
          "value": 0.42,
          "threshold": 0.3,
          "operator": ">",
          "met": true
        }
      }
    }
  ]
}
```

**Implementation Requirements (Future Sprint):**
1. Persist `strategy.state_transition` events to QuestDB
2. Query QuestDB for historical transitions
3. Parse condition details from event payloads

**Error Responses:**
- `500 Internal Server Error` - Failed to get session transitions

## Usage Examples

### cURL

**Get Session State:**
```bash
curl -X GET "http://localhost:8080/api/sessions/exec_20251206_100000_abc123/state" \
  -H "Content-Type: application/json"
```

**Get Session Transitions:**
```bash
curl -X GET "http://localhost:8080/api/sessions/exec_20251206_100000_abc123/transitions" \
  -H "Content-Type: application/json"
```

### Python (requests)

```python
import requests

# Get current state
session_id = "exec_20251206_100000_abc123"
response = requests.get(f"http://localhost:8080/api/sessions/{session_id}/state")
state_data = response.json()

print(f"Session State: {state_data['current_state']}")
print(f"Active Instances: {len(state_data['instances'])}")

for instance in state_data['instances']:
    print(f"  - {instance['strategy_id']} on {instance['symbol']}: {instance['state']}")

# Get transition history
response = requests.get(f"http://localhost:8080/api/sessions/{session_id}/transitions")
transitions = response.json()['transitions']
print(f"Transition Count: {len(transitions)}")
```

### JavaScript (fetch)

```javascript
// Get current state
const sessionId = 'exec_20251206_100000_abc123';
const stateResponse = await fetch(`http://localhost:8080/api/sessions/${sessionId}/state`);
const stateData = await stateResponse.json();

console.log(`Session State: ${stateData.current_state}`);
console.log(`Active Instances: ${stateData.instances.length}`);

stateData.instances.forEach(instance => {
  console.log(`  - ${instance.strategy_id} on ${instance.symbol}: ${instance.state}`);
});

// Get transition history
const transitionsResponse = await fetch(`http://localhost:8080/api/sessions/${sessionId}/transitions`);
const transitionsData = await transitionsResponse.json();
console.log(`Transition Count: ${transitionsData.transitions.length}`);
```

## Implementation Details

**Files:**
- `src/api/state_machine_routes.py` - API router with endpoints
- `src/api/unified_server.py` - Router registration and dependency injection

**Dependencies:**
- `ExecutionController` - Session-level state machine (from UnifiedTradingController)
- `StrategyManager` - Per-strategy-instance state machine

**Initialization:**
```python
# In unified_server.py lifespan()
state_machine_routes_module.initialize_state_machine_dependencies(
    execution_controller=ws_controller.execution_controller,
    strategy_manager=ws_strategy_manager
)
```

**Performance Optimizations:**
- Direct access to in-memory state (no DB queries for current state)
- <50ms response time for state endpoint
- Empty list for transitions (no DB query overhead until persistence is implemented)

## Future Enhancements

### Transition History Persistence (Next Sprint)

**Requirements:**
1. Subscribe to `strategy.state_transition` events in EventBus
2. Persist events to QuestDB `state_transitions` table:
   ```sql
   CREATE TABLE state_transitions (
     timestamp TIMESTAMP,
     session_id SYMBOL,
     strategy_id SYMBOL,
     symbol SYMBOL,
     from_state SYMBOL,
     to_state SYMBOL,
     trigger SYMBOL,
     conditions STRING,
     INDEX(session_id),
     INDEX(strategy_id)
   ) TIMESTAMP(timestamp) PARTITION BY DAY;
   ```
3. Update `/transitions` endpoint to query QuestDB
4. Add filtering parameters (symbol, strategy_id, from_state, to_state)

**Performance Target:** <100ms with 1000+ transitions

### Real-Time State Updates (WebSocket)

**Requirements:**
1. Add WebSocket endpoint `/ws/sessions/{session_id}/state`
2. Push state changes in real-time when ExecutionState or StrategyState changes
3. Client-side UI updates without polling

## Testing

### Manual Testing

1. Start a session (paper trading or backtest)
2. Query `/api/sessions/{session_id}/state`
3. Verify current_state matches execution status
4. Verify instances list matches active strategies
5. Verify allowed_transitions are correct

### Unit Tests (TODO)

```python
# tests/unit/test_state_machine_routes.py
async def test_get_session_state_running():
    # Mock ExecutionController with RUNNING session
    # Mock StrategyManager with active strategies
    # Call endpoint
    # Assert response matches expected format
    pass

async def test_get_session_state_not_found():
    # Mock ExecutionController with no session
    # Call endpoint
    # Assert returns IDLE state with empty instances
    pass

async def test_get_allowed_transitions():
    # Test all ExecutionState -> allowed transitions mapping
    pass
```

### Integration Tests (TODO)

```python
# tests_e2e/test_state_machine_api.py
async def test_state_machine_api_full_workflow():
    # Start paper trading session
    # Query state (should be RUNNING)
    # Pause session
    # Query state (should be PAUSED)
    # Resume session
    # Query state (should be RUNNING)
    # Stop session
    # Query state (should be STOPPED)
    pass
```

## Related Documentation

- [ExecutionController](../application/execution_controller.md) - Session state machine
- [StrategyManager](../domain/strategy_manager.md) - Strategy instance state machine
- [UI State Machine Integration](../../frontend/docs/state_machine_ui.md) - Frontend integration
- [EventBus Architecture](../core/event_bus.md) - Event-driven state changes

## Change Log

- **2025-12-06**: Initial implementation
  - Added `GET /api/sessions/{session_id}/state`
  - Added `GET /api/sessions/{session_id}/transitions` (placeholder)
  - Registered router in unified_server.py
  - Dependencies initialized via DI pattern
