# Story COH-001-1: Synchronize MessageType Definitions

**Status:** pending
**Priority:** HIGH
**Effort:** M (Medium)

---

## Story

As a **developer working on WebSocket communication**,
I want **MessageType definitions to be synchronized between backend and frontend**,
so that **type mismatches are caught at compile time rather than runtime**.

## Problem Statement

**Backend** (`src/api/message_router.py`):
```python
class MessageType(str, Enum):
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    COMMAND = "command"
    # ... 20+ types
```

**Frontend** (`frontend/src/types/api.ts`):
```typescript
type WSMessageType = 'subscribe' | 'unsubscribe' | 'command' | ...
```

**Issues:**
1. Definitions maintained separately - can drift
2. Adding new type requires changes in 2 places
3. Typos cause runtime errors, not compile errors
4. No automated validation of synchronization

## Acceptance Criteria

1. **AC1:** Single source of truth for message types exists
2. **AC2:** Adding new message type requires change in only 1 place
3. **AC3:** TypeScript compilation fails if types are out of sync
4. **AC4:** All existing message types are covered
5. **AC5:** Documentation explains the synchronization mechanism

## Tasks / Subtasks

- [ ] Task 1: Audit current message types (AC: 4)
  - [ ] Extract all MessageType values from Python enum
  - [ ] Extract all WSMessageType values from TypeScript
  - [ ] Create comparison matrix
  - [ ] Identify any mismatches

- [ ] Task 2: Choose synchronization strategy (AC: 1, 2)
  - [ ] Option A: Generate TypeScript from Python (pydantic-to-typescript)
  - [ ] Option B: Generate Python from TypeScript
  - [ ] Option C: Shared JSON schema defining types
  - [ ] Option D: Manual sync with CI validation test

- [ ] Task 3: Implement chosen strategy (AC: 1, 2, 3)
  - [ ] Create shared type definition (if Option A/B/C)
  - [ ] Create synchronization script/tool
  - [ ] Add to build process

- [ ] Task 4: Add validation (AC: 3)
  - [ ] Create test that validates sync
  - [ ] Add to CI pipeline
  - [ ] Fail build on mismatch

- [ ] Task 5: Update documentation (AC: 5)
  - [ ] Document the sync mechanism
  - [ ] Add instructions for adding new types
  - [ ] Update ADR if exists

## Dev Notes

### Recommended Approach: Option D (Pragmatic)

For this project size, manual sync with CI validation is likely best:

1. Create `shared/message-types.json`:
```json
{
  "messageTypes": [
    "subscribe",
    "unsubscribe",
    "command",
    "query",
    "heartbeat",
    "auth",
    "data",
    "signal",
    "alert",
    "response",
    "error",
    "status"
  ]
}
```

2. Add test in `tests/integration/test_type_sync.py`:
```python
def test_message_types_synchronized():
    with open("shared/message-types.json") as f:
        shared_types = set(json.load(f)["messageTypes"])

    python_types = {t.value for t in MessageType}

    assert shared_types == python_types, f"Mismatch: {shared_types.symmetric_difference(python_types)}"
```

3. Add Jest test for frontend validation

### Affected Files

**Backend:**
- `src/api/message_router.py` - MessageType enum

**Frontend:**
- `frontend/src/types/api.ts` - WSMessageType type
- `frontend/src/services/websocket.ts` - type usage

**New:**
- `shared/message-types.json` (or similar)
- `tests/integration/test_type_sync.py`
- `frontend/src/__tests__/type-sync.test.ts`

## References

- [Coherence Analysis Report - Test 78]
- [Architecture Document - API Contracts section]

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-29 | John (PM) | Story created from Coherence Analysis |
