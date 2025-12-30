# Story BUG-007.2: Add state_machines to Valid Streams

Status: done

## Story

As a **backend developer**,
I want **`state_machines` to be a valid stream type in message_router.py**,
so that **clients can subscribe to state machine updates without validation errors**.

## Acceptance Criteria

1. **AC1:** `state_machines` added to `valid_streams` list in MessageValidator
2. **AC2:** Subscribe messages with `stream: "state_machines"` pass validation
3. **AC3:** No validation errors like "Missing required field: stream" for state_machines subscriptions

## Tasks / Subtasks

- [x] Task 1: Add state_machines to valid_streams (AC: 1)
  - [x] Open `src/api/message_router.py`
  - [x] Find `valid_streams` list (line ~403-408)
  - [x] Add `"state_machines"` to the list

- [x] Task 2: Verify validation passes (AC: 2, 3)
  - [x] Run existing tests to ensure no regressions
  - [x] Test subscription with `stream: "state_machines"` passes

## Dev Notes

### Architecture Requirements

- Simple addition to existing whitelist
- No new logic required

### Technical Specification

**Current valid_streams (line 403-408):**
```python
valid_streams = [
    "market_data", "indicators", "signals", "orders", "positions",
    "portfolio", "execution_status", "system_health",
    "health_check", "comprehensive_health_check"
]
```

**Add:**
```python
valid_streams = [
    "market_data", "indicators", "signals", "orders", "positions",
    "portfolio", "execution_status", "system_health",
    "health_check", "comprehensive_health_check",
    "state_machines"  # NEW - for real-time state machine updates
]
```

### Dependencies

- No dependencies
- Can be done in parallel with other stories

### Project Structure Notes

- File: `src/api/message_router.py` (line ~403-408)

### References

- [Source: _bmad-output/bug-007-epic-stories.md#Story-2]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None required - simple whitelist addition.

### Completion Notes List

1. Added `state_machines` to valid_streams list at line 408 in message_router.py
2. Existing tests pass without regressions

### File List

**Modified Files:**
- `src/api/message_router.py` - Added state_machines to valid_streams list

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-29 | Bob (SM) | Story created from BUG-007 Epic |
| 2025-12-29 | Amelia (Dev) | Story implemented - all 3 ACs met |
