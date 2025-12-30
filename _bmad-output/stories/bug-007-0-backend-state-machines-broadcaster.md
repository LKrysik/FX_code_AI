# Story BUG-007.0: Backend state_machines Broadcaster

Status: done

## Story

As a **frontend developer**,
I want **the backend to broadcast state machine events via WebSocket**,
so that **dashboard components receive real-time state updates without needing separate WebSocket connections**.

## Acceptance Criteria

1. **AC1:** Create `StateMachineBroadcaster` service class in `src/api/websocket/broadcasters/`
2. **AC2:** Broadcaster emits `state_change` events when strategy state transitions occur
3. **AC3:** Broadcaster emits `instance_added` when new strategy instance starts
4. **AC4:** Broadcaster emits `instance_removed` when strategy instance stops
5. **AC5:** Broadcaster emits `full_update` with initial state when client subscribes to `state_machines` stream
6. **AC6:** Clients subscribed to `state_machines` stream receive all broadcast messages

## Tasks / Subtasks

- [x] Task 1: Create StateMachineBroadcaster class (AC: 1)
  - [x] Create new file `src/api/websocket/broadcasters/state_machine_broadcaster.py`
  - [x] Implement `__init__` with subscription_manager and connection_manager dependencies
  - [x] Implement `broadcast_state_change(session_id, data)` method
  - [x] Implement `broadcast_instance_added(session_id, instance_data)` method
  - [x] Implement `broadcast_instance_removed(session_id, instance_id)` method
  - [x] Implement `broadcast_full_update(client_id, session_id)` method
  - [x] Add proper logging for all broadcast events

- [x] Task 2: Register broadcaster in WebSocket server (AC: 1, 6)
  - [x] Import StateMachineBroadcaster in `websocket_server.py`
  - [x] Instantiate broadcaster with subscription_manager and connection_manager
  - [x] Register broadcaster as singleton accessible to handlers

- [x] Task 3: Integrate with subscription handler (AC: 5, 6)
  - [x] Modify subscription handler to trigger `full_update` on `state_machines` subscription
  - [x] Ensure `get_subscribers("state_machines")` returns correct client list

- [x] Task 4: Hook broadcaster to trading coordinator (AC: 2, 3, 4)
  - [x] Subscribe to EventBus session.started and session.stopped events
  - [x] Call `broadcast_instance_added` on session start via event handler
  - [x] Call `broadcast_instance_removed` on session stop via event handler

- [x] Task 5: Write unit tests
  - [x] Test broadcaster initialization
  - [x] Test each broadcast method sends correct message format
  - [x] Test subscriber filtering works correctly
  - [x] Test integration with connection_manager.send_to_client

## Dev Notes

### Architecture Requirements

- **ADR-002:** Backend must broadcast state machine events for real-time dashboard updates
- Broadcaster follows existing patterns in `src/api/websocket/` structure
- Messages must include `type`, `stream`, `session_id`, `data`, `timestamp` fields

### Technical Specification

**Message Format:**
```python
{
    "type": "state_change",  # or instance_added, instance_removed, full_update
    "stream": "state_machines",
    "session_id": "exec_YYYYMMDD_HHMMSS_xxxxxxxx",
    "data": {...},
    "timestamp": "2025-12-29T15:00:00.000Z"
}
```

**Broadcaster Class Template:**
```python
from datetime import datetime
from typing import Dict, Any
from src.core.logger import get_logger

class StateMachineBroadcaster:
    def __init__(self, subscription_manager, connection_manager):
        self.subscription_manager = subscription_manager
        self.connection_manager = connection_manager
        self.logger = get_logger(__name__)

    async def broadcast_state_change(self, session_id: str, data: Dict[str, Any]):
        subscribers = self.subscription_manager.get_subscribers("state_machines")
        message = {
            "type": "state_change",
            "stream": "state_machines",
            "session_id": session_id,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        for client_id in subscribers:
            await self.connection_manager.send_to_client(client_id, message)
        self.logger.info("state_machine.broadcast", {"type": "state_change", "subscribers": len(subscribers)})
```

### Dependencies

- `subscription_manager.py` - must have `get_subscribers(stream_type)` method
- `connection_manager.py` - must have `send_to_client(client_id, message)` method
- This story BLOCKS all frontend refactoring stories (S1, S1b, S1c, S1d)

### Project Structure Notes

- New file: `src/api/websocket/broadcasters/state_machine_broadcaster.py`
- Modify: `src/api/websocket_server.py` (register broadcaster)
- Modify: `src/trading/trading_coordinator.py` (emit events)

### References

- [Source: _bmad-output/bug-007-epic-stories.md#Story-0]
- [Source: docs/bug_007.md - original bug report]
- [ADR-002: Backend Must Broadcast State Machine Events]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None required - all tests passed on first run.

### Completion Notes List

1. Created StateMachineBroadcaster class with full event-driven architecture
2. Broadcaster subscribes to EventBus `session.started` and `session.stopped` events
3. Added `start()` and `stop()` lifecycle methods for proper event subscription management
4. Integrated with WebSocketAPIServer - broadcaster starts/stops with server
5. Added 17 unit tests covering all acceptance criteria - 100% pass rate

### File List

**New Files:**
- `src/api/websocket/broadcasters/__init__.py` - Package init with exports
- `src/api/websocket/broadcasters/state_machine_broadcaster.py` - Main broadcaster class (355 lines)
- `tests/unit/test_state_machine_broadcaster.py` - Unit tests (17 tests)

**Modified Files:**
- `src/api/websocket_server.py` - Added broadcaster initialization, start/stop calls

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-29 | Bob (SM) | Story created from BUG-007 Epic |
| 2025-12-29 | Amelia (Dev) | Story implemented - all 6 ACs met, 17 tests passing |
