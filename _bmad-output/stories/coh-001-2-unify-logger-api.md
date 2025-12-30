# Story COH-001-2: Unify Logger API Signatures

**Status:** pending
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

- [ ] Task 1: Document current APIs (AC: 1, 2)
  - [ ] Create logging style guide
  - [ ] Document event type naming convention: `module.action`
  - [ ] List all log levels and their usage

- [ ] Task 2: Align frontend Logger (AC: 3, 4)
  - [ ] Make `data` parameter required (or provide empty object default)
  - [ ] Add TypeScript overloads for backwards compat if needed
  - [ ] Ensure consistent behavior

- [ ] Task 3: Update usage patterns (AC: 3)
  - [ ] Search for Logger calls without data parameter
  - [ ] Add empty object where needed: `Logger.info('event', {})`

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

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-29 | John (PM) | Story created from Coherence Analysis |
