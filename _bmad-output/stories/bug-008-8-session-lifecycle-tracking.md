# Story BUG-008-8: Session Lifecycle Tracking

**Status:** backlog
**Priority:** P1
**Epic:** BUG-008 WebSocket Stability & Service Health

---

## Story

As a **session management system**,
I want **robust session lifecycle tracking with proper cleanup**,
so that **session queries never fail with "not found" for valid sessions**.

---

## Problem Statement

Log evidence shows repeated session lookup failures:
```json
{
  "event_type": "questdb_data_provider.session_not_found",
  "data": {
    "session_id": "exec_20251230_020944_4ad060d9",
    "include_deleted": true
  }
}
```

**Issues:**
1. Session was queried but not found, even with `include_deleted: true`
2. Either session was never created in DB, or was hard-deleted
3. No distinction between "never existed" vs "deleted" vs "archived"
4. Multiple occurrences suggest systematic issue, not one-off

---

## Acceptance Criteria

1. **AC1:** Sessions have explicit lifecycle states: CREATING, ACTIVE, STOPPED, DELETED
2. **AC2:** Soft delete: deleted sessions remain queryable with `include_deleted=true`
3. **AC3:** Session creation is atomic: either fully created or not at all
4. **AC4:** "Session not found" response includes reason: never_existed, deleted, archived
5. **AC5:** Session ID validation before queries (fail fast on invalid format)
6. **AC6:** Audit log for session lifecycle transitions

---

## Tasks / Subtasks

- [ ] Task 1: Define session lifecycle states (AC: 1)
  - [ ] Add `SessionState` enum: CREATING, ACTIVE, PAUSED, STOPPED, DELETED
  - [ ] Add `state` column to sessions table
  - [ ] Update session queries to filter by state

- [ ] Task 2: Implement soft delete (AC: 2)
  - [ ] Add `deleted_at` timestamp column
  - [ ] Change delete operation to set `deleted_at` (not remove row)
  - [ ] Default queries exclude deleted (state != DELETED)
  - [ ] `include_deleted=true` includes all states

- [ ] Task 3: Make session creation atomic (AC: 3)
  - [ ] Wrap session creation in transaction
  - [ ] Verify all required fields before commit
  - [ ] On failure, rollback completely
  - [ ] Log creation success/failure

- [ ] Task 4: Enhance "not found" responses (AC: 4)
  - [ ] Check if session_id format is valid first
  - [ ] If format invalid: "not_found_invalid_format"
  - [ ] If valid but not in DB: "not_found_never_existed"
  - [ ] If in DB but deleted: "not_found_deleted"
  - [ ] Return structured response with reason

- [ ] Task 5: Add session ID validation (AC: 5)
  - [ ] Define session ID format: `exec_YYYYMMDD_HHMMSS_xxxxxxxx`
  - [ ] Validate format before any DB query
  - [ ] Return fast error for invalid format
  - [ ] Log validation failures

- [ ] Task 6: Create session audit log (AC: 6)
  - [ ] Log all state transitions with timestamp
  - [ ] Include: session_id, old_state, new_state, reason, user/system
  - [ ] Store in separate audit table or append-only log

---

## Dev Notes

### Session Lifecycle States

```
[CREATING] ──success──► [ACTIVE] ──pause──► [PAUSED]
     │                      │                   │
     │                      │                   │
     │                      ▼                   ▼
     │                  [STOPPED] ◄──stop──────┘
     │                      │
  failure                   │
     │                   delete
     ▼                      ▼
  [null]                [DELETED]
```

### Session Table Schema Update

```sql
ALTER TABLE sessions ADD COLUMN state VARCHAR(20) DEFAULT 'ACTIVE';
ALTER TABLE sessions ADD COLUMN deleted_at TIMESTAMP;
ALTER TABLE sessions ADD COLUMN created_at TIMESTAMP DEFAULT now();
ALTER TABLE sessions ADD COLUMN updated_at TIMESTAMP DEFAULT now();

CREATE INDEX idx_sessions_state ON sessions(state);
```

### Session ID Format Validation

```python
import re

SESSION_ID_PATTERN = re.compile(
    r'^exec_\d{8}_\d{6}_[a-f0-9]{8}$'
)

def validate_session_id(session_id: str) -> bool:
    """Validate session ID format."""
    return bool(SESSION_ID_PATTERN.match(session_id))
```

### Enhanced Not Found Response

```python
class SessionLookupResult:
    found: bool
    session: Optional[Session]
    reason: Literal["ok", "invalid_format", "never_existed", "deleted", "archived"]

def get_session(session_id: str, include_deleted: bool = False) -> SessionLookupResult:
    if not validate_session_id(session_id):
        return SessionLookupResult(found=False, reason="invalid_format")

    session = db.query(Session).filter_by(id=session_id).first()

    if session is None:
        return SessionLookupResult(found=False, reason="never_existed")

    if session.state == SessionState.DELETED and not include_deleted:
        return SessionLookupResult(found=False, reason="deleted")

    return SessionLookupResult(found=True, session=session, reason="ok")
```

### Audit Log Entry

```python
@dataclass
class SessionAuditEntry:
    session_id: str
    timestamp: datetime
    old_state: Optional[SessionState]
    new_state: SessionState
    trigger: str  # "user_action", "system_timeout", "api_call"
    actor: str    # user_id or "system"
    reason: Optional[str]
```

### Files to Modify

- `src/data/questdb_data_provider.py` - Session queries
- `src/models/session.py` - Session model (if exists)
- `src/services/session_service.py` - Session lifecycle management
- Create: `src/models/session_audit.py` - Audit log model

### Dependencies

- Should be implemented after BUG-008-7 (QuestDB resilience) for proper error handling

---

## Definition of Done

1. [ ] Session states are explicit and tracked
2. [ ] Soft delete implemented (deleted sessions queryable)
3. [ ] Session creation is atomic
4. [ ] "Not found" includes reason
5. [ ] Session ID validated before queries
6. [ ] Audit log captures all transitions
7. [ ] Migration script for existing sessions
8. [ ] Unit tests for all lookup scenarios

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-30 | John (PM) | Story created from BUG-008 Epic |
