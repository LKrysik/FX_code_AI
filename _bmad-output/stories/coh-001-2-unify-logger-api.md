# Story COH-001-2: Unify Logger API Signatures

**Status:** review
**Priority:** MEDIUM
**Effort:** S (Small)

---

## Story

As a **developer debugging cross-stack issues**,
I want **consistent logging API between backend and frontend**,
so that **I can use the same mental model when reading logs from either system**.

## Problem Statement

**Backend** (`src/core/logger.py`):
```python
logger.info("event.name", {"key": "value", "count": 42})
# Signature: info(event_type: str, data: Dict[str, Any])
```

**Frontend** (`frontend/src/services/frontendLogService.ts`):
```typescript
Logger.info('event.name', { key: 'value', count: 42 });
// Signature: info(eventType: string, data?: Record<string, unknown>)
```

**Current Differences:**
1. Backend requires data dict, frontend makes it optional
2. Backend uses `event_type` naming, frontend uses `eventType`
3. Minor: Backend `logger` lowercase, Frontend `Logger` PascalCase

**Impact:** Low (patterns are similar), but worth documenting and slightly aligning.

## Acceptance Criteria

1. **AC1:** Logger API documented for both stacks
2. **AC2:** Event type naming convention documented
3. **AC3:** Frontend Logger accepts same signature as backend (data required)
4. **AC4:** Existing code continues to work (backwards compat)

## Tasks / Subtasks

- [x] Task 1: Document current APIs (AC: 1, 2)
  - [x] Create logging style guide (`docs/LOGGING_STYLE_GUIDE.md`)
  - [x] Document event type naming convention: `module.action`
  - [x] List all log levels and their usage

- [x] Task 2: Align frontend Logger (AC: 3, 4)
  - [x] Make `data` parameter required with default `{}`
  - [x] No TypeScript overloads needed (backwards compat via default)
  - [x] Consistent behavior verified

- [x] Task 3: Update usage patterns (AC: 3)
  - [x] Searched for Logger calls without data parameter - **none found**
  - [x] All 426 Logger calls across 72 files already include data

## Dev Notes

### Minimal Change Approach

Since patterns are already similar, focus on:
1. Documentation
2. Making `data` required in frontend to match backend

### Frontend Change

```typescript
// Current (data optional)
info(eventType: string, data?: Record<string, unknown>): void

// Proposed (data required, default empty object)
info(eventType: string, data: Record<string, unknown> = {}): void
```

### Affected Files

- `frontend/src/services/frontendLogService.ts`
- Various frontend files calling `Logger.info/warn/error` without data

## References

- [Coherence Analysis Report - Test 79 DNA Inheritance]
- [Backend logging_schema.py]

---

## Dev Agent Record

### Implementation Plan
- Created comprehensive logging style guide
- Updated frontend Logger to use explicit default `{}` for data parameter
- Verified all 426 existing Logger calls already include data

### Completion Notes
- APIs were already more aligned than story indicated
- Backend: `data: Dict[str, Any] = None` (optional with internal default)
- Frontend: Updated to `data: Record<string, unknown> = {}` (explicit default)
- All 426 Logger calls in 72 files already include data parameter
- No code changes needed beyond Logger API update

### Debug Log
- No issues encountered

---

## File List

**New Files:**
- `docs/LOGGING_STYLE_GUIDE.md` - Comprehensive logging documentation

**Modified Files:**
- `frontend/src/services/frontendLogService.ts` - Updated data parameter to have explicit default

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-29 | John (PM) | Story created from Coherence Analysis |
| 2025-12-30 | Amelia (Dev Agent) | Implemented: style guide + frontend Logger API alignment |
