# Epic COH-001: Coherence Improvements

**Status:** ready
**Priority:** HIGH
**Sprint:** Next Available
**Source:** Coherence Analysis Report (2025-12-29)

---

## Epic Overview

### Problem Statement

Coherence analysis of FX_code_AI_v2 codebase revealed structural inconsistencies between backend (Python) and frontend (TypeScript) that reduce maintainability, increase bug risk, and slow down development.

**Overall Coherence Score:** 83.3% (GOOD, but improvements needed)

### Business Value

- **Reduced debugging time:** Type synchronization prevents runtime mismatches
- **Faster onboarding:** Consistent patterns reduce learning curve for new developers
- **Lower bug rate:** Explicit contracts catch errors at compile time, not runtime
- **Better DX:** Unified logging makes debugging cross-stack issues easier

### Success Criteria

1. MessageType definitions synchronized between BE and FE
2. Logger API signatures consistent across stack
3. EventType definitions available in TypeScript
4. Strategy validation accepts valid indicator UUIDs
5. No new coherence violations introduced

---

## Stories Summary

| ID | Story | Priority | Effort | Status |
|----|-------|----------|--------|--------|
| COH-001-1 | Synchronize MessageType Definitions | HIGH | M | pending |
| COH-001-2 | Unify Logger API Signatures | MEDIUM | S | pending |
| COH-001-3 | Create TypeScript EventType Definitions | MEDIUM | M | pending |
| COH-001-4 | Refactor Dynamic Store Imports | LOW | S | pending |
| COH-001-5 | Fix Strategy Indicator Validation | CRITICAL | M | pending |

---

## Detailed Requirements

### From Coherence Analysis Report:

**Test 78 (Least Surprise) - Issues Found:**
1. Logger vs StructuredLogger API mismatch (MEDIUM)
2. MessageType enum (backend) vs WSMessageType (frontend) - different definitions (HIGH)
3. Missing TypeScript types for EventType (HIGH)

**Test 83 (Boundary Violation) - Issues Found:**
1. Dynamic import of dashboardStore in websocket.ts (MEDIUM)
2. Debug store coupling in wsService (LOW)

**User-Reported Bug:**
- Strategy validation fails with "unknown indicator type" for valid UUIDs
- Blocks strategy save functionality
- Error example: `s1_signal.conditions[0].indicatorId contains unknown indicator type: 'e15a3064-424c-4f7a-8b8b-77a04e3e7ab3'`

---

## Technical Context

### Affected Files

**Backend:**
- `src/api/message_router.py` - MessageType enum
- `src/core/events.py` - EventType definitions
- `src/core/logging_schema.py` - Logging patterns

**Frontend:**
- `frontend/src/types/api.ts` - WSMessageType union
- `frontend/src/services/frontendLogService.ts` - Logger class
- `frontend/src/services/websocket.ts` - Dynamic imports

**Validation:**
- Strategy validation logic (location TBD - needs investigation)

---

## Dependencies

- No blocking dependencies
- Can be worked in parallel with feature development
- COH-001-5 (Strategy Validation) should be prioritized as it blocks user workflows

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking changes to WS message format | HIGH | Add version field, backwards compat |
| Logger changes break existing logs | MEDIUM | Gradual migration, alias old methods |
| Test coverage gaps | MEDIUM | Add integration tests for type sync |

---

## Definition of Done

- [ ] All 5 stories completed and verified
- [ ] No TypeScript compile errors
- [ ] No Python linting errors
- [ ] All existing tests pass
- [ ] New unit tests for type synchronization
- [ ] Documentation updated

---

## References

- [Coherence Analysis Report](_bmad-output/coherence-analysis-report.md)
- [Architecture Document](_bmad-output/architecture.md)
- [Previous BUG-007 Epic](_bmad-output/bug-007-epic-stories.md)

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-29 | John (PM) | Epic created from Coherence Analysis findings |
