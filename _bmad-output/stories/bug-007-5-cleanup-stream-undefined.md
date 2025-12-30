# Story BUG-007.5: Clean Up stream:undefined Log Noise

Status: done

## Story

As a **developer**,
I want **graceful handling of missing stream field in WebSocket message logging**,
so that **logs don't show `stream: undefined` for status messages**.

## Acceptance Criteria

1. **AC1:** Logs show meaningful value instead of `undefined`
2. **AC2:** Status messages are logged with `stream: 'N/A'` or similar

## Tasks / Subtasks

- [x] Task 1: Fix logging in websocket.ts (AC: 1, 2)
  - [x] Open `frontend/src/services/websocket.ts`
  - [x] Find logging statement (~line 1047)
  - [x] Replace `stream: message.stream` with `stream: message.stream ?? 'N/A'`

- [x] Task 2: Verify logs are cleaner
  - [x] Test with status messages
  - [x] Verify no `stream: undefined` appears

## Dev Notes

### Architecture Requirements

- Minor cosmetic fix
- Use nullish coalescing for graceful fallback

### Technical Specification

**Current logging:**
```typescript
Logger.debug('websocket.message', {
  direction,
  type: message.type,
  stream: message.stream,  // undefined for status messages
  hasData: !!message.data,
  dataKeys: message.data ? Object.keys(message.data) : [],
  timestamp: logEntry.timestamp,
  client_id: logEntry.client_id
});
```

**Fixed logging:**
```typescript
Logger.debug('websocket.message', {
  direction,
  type: message.type,
  stream: message.stream ?? 'N/A',  // Graceful fallback
  hasData: !!message.data,
  dataKeys: message.data ? Object.keys(message.data) : [],
  timestamp: logEntry.timestamp,
  client_id: logEntry.client_id
});
```

### Dependencies

- No dependencies

### Project Structure Notes

- File: `frontend/src/services/websocket.ts` (line ~1033)

### References

- [Source: _bmad-output/bug-007-epic-stories.md#Story-5]
- [Source: docs/bug_007.md - "stream: undefined in console logs"]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None required - cosmetic fix.

### Completion Notes List

1. Added nullish coalescing operator to `stream` field in Logger.debug at line 1047
2. Status messages now log `stream: 'N/A'` instead of `stream: undefined`

### File List

**Modified Files:**
- `frontend/src/services/websocket.ts` - Fixed undefined stream logging (line 1047)

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-29 | Bob (SM) | Story created from BUG-007 Epic |
| 2025-12-29 | Amelia (Dev) | Story implemented - both ACs met |
