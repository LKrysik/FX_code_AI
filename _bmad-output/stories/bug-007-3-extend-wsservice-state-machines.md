# Story BUG-007.3: Extend wsService for state_machines Message Handling

Status: done

## Story

As a **frontend developer**,
I want **wsService to handle state_machines stream messages**,
so that **components listening for state updates receive them correctly**.

## Acceptance Criteria

1. **AC1:** `state_change`, `instance_added`, `instance_removed`, `full_update` added to relevant message types
2. **AC2:** These message types are routed via `emitSessionUpdate()`
3. **AC3:** Components using `addSessionUpdateListener()` receive state_machines messages

## Tasks / Subtasks

- [x] Task 1: Add types to isRelevantMessage() (AC: 1)
  - [x] Open `frontend/src/services/websocket.ts`
  - [x] Find `isRelevantMessage()` method
  - [x] Add `state_change`, `instance_added`, `instance_removed`, `full_update` to relevantTypes array

- [x] Task 2: Add case handlers in handleMessage() (AC: 2)
  - [x] Find `handleMessage()` switch statement
  - [x] Add cases for new message types
  - [x] Route to `emitSessionUpdate(message)`

- [x] Task 3: Verify routing works (AC: 3)
  - [x] Test that messages reach registered listeners
  - [x] Verify message structure is preserved

## Dev Notes

### Architecture Requirements

- wsService singleton must route state_machines messages to listeners
- Follow existing message routing patterns in handleMessage()

### Technical Specification

**Add to isRelevantMessage() relevantTypes array:**
```typescript
const relevantTypes = [
  // ... existing types ...
  'state_change',
  'instance_added',
  'instance_removed',
  'full_update'
];
```

**Add to handleMessage() switch:**
```typescript
case 'state_change':
case 'instance_added':
case 'instance_removed':
case 'full_update':
  this.emitSessionUpdate(message);
  break;
```

### Dependencies

- Required for S1, S1b, S1c, S1d to receive messages

### Project Structure Notes

- File: `frontend/src/services/websocket.ts`

### References

- [Source: _bmad-output/bug-007-epic-stories.md#Story-3]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None required.

### Completion Notes List

1. Added 4 new message types to `relevantTypes` array in `isRelevantMessage()` (lines 380-384)
2. Added case handlers in switch statement for state machine messages (lines 348-356)
3. Messages are routed via `emitSessionUpdate()` following existing patterns

### File List

**Modified Files:**
- `frontend/src/services/websocket.ts` - Added state_machines message handling

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-29 | Bob (SM) | Story created from BUG-007 Epic |
| 2025-12-29 | Amelia (Dev) | Story implemented - all 3 ACs met |
