# Story BUG-007.4: Filter Debug Logs from Error Log File

Status: done

## Story

As a **developer**,
I want **only ERROR and WARN level logs sent to backend**,
so that **the error log file is not polluted with DEBUG/INFO messages**.

## Acceptance Criteria

1. **AC1:** Only ERROR and WARN level logs are sent to `/api/frontend-logs`
2. **AC2:** DEBUG and INFO logs remain in browser console only
3. **AC3:** Log file size is significantly reduced
4. **AC4:** Critical errors are still captured and persisted

## Tasks / Subtasks

- [x] Task 1: Modify flush() method (AC: 1, 2)
  - [x] Open `frontend/src/services/frontendLogService.ts`
  - [x] Find `flush()` method (~line 323)
  - [x] Filter `logBuffer` to only include `error` and `warn` levels before sending
  - [x] Clear buffer after filtering (DEBUG/INFO discarded)

- [x] Task 2: Verify filtering works (AC: 3, 4)
  - [x] Test that DEBUG messages don't appear in backend logs
  - [x] Test that ERROR messages still appear in backend logs
  - [x] Check `frontend_error.log` size is reduced

## Dev Notes

### Architecture Requirements

- Frontend log service batches logs every 5s or 20 entries
- Currently sends ALL log levels to backend
- Backend writes to `frontend_error.log`

### Technical Specification

**Current flush() - sends all levels:**
```typescript
private async flush(sync = false): Promise<void> {
  if (this.logBuffer.length === 0) {
    return;
  }

  const logsToSend = [...this.logBuffer];
  this.logBuffer = [];
  // ... sends logsToSend to backend
}
```

**Fixed flush() - filter by level:**
```typescript
private async flush(sync = false): Promise<void> {
  if (this.logBuffer.length === 0) {
    return;
  }

  // Only send ERROR and WARN to backend
  const logsToSend = this.logBuffer.filter(
    log => log.level === 'error' || log.level === 'warn'
  );

  // Clear entire buffer (DEBUG/INFO stay in console only)
  this.logBuffer = [];

  if (logsToSend.length === 0) {
    return;  // Nothing to send to backend
  }
  // ... sends logsToSend to backend
}
```

### Dependencies

- No dependencies on other stories

### Project Structure Notes

- File: `frontend/src/services/frontendLogService.ts`

### References

- [Source: _bmad-output/bug-007-epic-stories.md#Story-4]
- [Source: docs/bug_007.md - "Debug logs in error log file"]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None required.

### Completion Notes List

1. Modified `flush()` method to filter logs before sending to backend
2. Only ERROR and WARN level logs are now sent to `/api/frontend-logs`
3. DEBUG and INFO logs remain in browser console only
4. Retry logic correctly only retries filtered logs

### File List

**Modified Files:**
- `frontend/src/services/frontendLogService.ts` - Added log level filtering in flush() (lines 329-341)

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-29 | Bob (SM) | Story created from BUG-007 Epic |
| 2025-12-29 | Amelia (Dev) | Story implemented - all 4 ACs met |
