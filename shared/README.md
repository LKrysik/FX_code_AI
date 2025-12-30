# Shared Type Definitions

This directory contains type definitions shared between backend (Python) and frontend (TypeScript).

## Event Types (`event-types.json`)

**Single source of truth** for event type constants used for internal event-driven communication.

### Structure

```json
{
  "eventTypes": ["market.price_update", "pump.detected", ...],
  "categories": {
    "marketData": [...],
    "signalDetection": [...],
    ...
  }
}
```

### Synchronization Mechanism

Both Python and TypeScript must stay synchronized with this JSON file:

- **Python**: `src/core/events.py` → `EventType` class
- **TypeScript**: `frontend/src/types/events.ts` → `EventType` object

### Adding a New Event Type

1. Add the new type to `shared/event-types.json` in the `eventTypes` array
2. Add it to the appropriate category in `categories`
3. Add to Python class in `src/core/events.py`:
   ```python
   class EventType:
       NEW_EVENT = "category.new_event"
   ```
4. Add to TypeScript object in `frontend/src/types/events.ts`:
   ```typescript
   export const EventType = {
     NEW_EVENT: 'category.new_event',
     ...
   } as const;
   ```

### Validation Tests

Tests automatically validate synchronization:

- **Python**: `tests/integration/test_event_type_sync.py`
- **TypeScript**: `frontend/src/types/__tests__/event-type-sync.test.ts`

---

## Message Types (`message-types.json`)

**Single source of truth** for WebSocket message types used in communication between frontend and backend.

### Structure

```json
{
  "messageTypes": ["subscribe", "unsubscribe", ...],
  "categories": {
    "clientToServer": [...],
    "serverToClient": [...],
    ...
  }
}
```

### Synchronization Mechanism

Both Python and TypeScript must stay synchronized with this JSON file:

- **Python**: `src/api/message_router.py` → `MessageType` enum
- **TypeScript**: `frontend/src/types/api.ts` → `WSMessageType` type

### Adding a New Message Type

1. Add the new type to `shared/message-types.json` in the `messageTypes` array
2. Add it to the appropriate category in `categories`
3. Add to Python enum in `src/api/message_router.py`:
   ```python
   class MessageType(str, Enum):
       NEW_TYPE = "new_type"
   ```
4. Add to TypeScript type in `frontend/src/types/api.ts`:
   ```typescript
   export type WSMessageType =
     | 'subscribe'
     | 'new_type'  // Add here
     | ...
   ```
5. Add to test file `frontend/src/types/__tests__/type-sync.test.ts`:
   ```typescript
   const TYPESCRIPT_MESSAGE_TYPES: WSMessageType[] = [
     'new_type',  // Add here
     ...
   ];
   ```

### Validation Tests

Tests automatically validate synchronization:

- **Python**: `tests/integration/test_type_sync.py` (4 tests)
- **TypeScript**: `frontend/src/types/__tests__/type-sync.test.ts` (7 tests)

Both test suites:
- Compare against shared JSON
- Verify no missing/extra types
- Check for duplicates
- Validate JSON structure

### CI Integration

Run validation as part of your CI pipeline:

```bash
# Python
pytest tests/integration/test_type_sync.py -v

# TypeScript
npm test -- --testPathPattern="type-sync"
```

Build will fail if types are out of sync.
