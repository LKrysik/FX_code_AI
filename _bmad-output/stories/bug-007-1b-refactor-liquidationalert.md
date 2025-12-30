# Story BUG-007.1b: Refactor LiquidationAlert to Use Shared WebSocket

Status: done

## Story

As a **frontend developer**,
I want **LiquidationAlert to use the shared wsService singleton**,
so that **there is only one WebSocket connection with proper auth, heartbeat, and reconnection**.

## Acceptance Criteria

1. **AC1:** LiquidationAlert uses `wsService` singleton instead of `new WebSocket()`
2. **AC2:** Component subscribes to appropriate liquidation stream
3. **AC3:** Remove standalone WebSocket management code
4. **AC4:** Connection remains stable with proper heartbeat

## Tasks / Subtasks

- [ ] Task 1: Analyze current WebSocket usage (line 84)
  - [ ] Read LiquidationAlert.tsx to understand current implementation
  - [ ] Identify what stream/channel it subscribes to
  - [ ] Document message types it handles

- [ ] Task 2: Remove standalone WebSocket code (AC: 3)
  - [ ] Remove `new WebSocket()` instantiation
  - [ ] Remove WebSocket event handlers (onopen, onmessage, onclose, onerror)
  - [ ] Remove reconnection logic

- [ ] Task 3: Add wsService integration (AC: 1, 2)
  - [ ] Import `wsService` from `@/services/websocket`
  - [ ] Subscribe to appropriate stream
  - [ ] Add session update listener for liquidation events

- [ ] Task 4: Cleanup on unmount (AC: 1)
  - [ ] Proper cleanup of listeners
  - [ ] Unsubscribe from stream

## Dev Notes

### Architecture Requirements

- **ADR-001:** All components must use `wsService` singleton
- Component at `frontend/src/components/trading/LiquidationAlert.tsx:84` creates own WebSocket

### Technical Specification

Pattern same as Story 1 - use wsService singleton with addSessionUpdateListener.

### Dependencies

- Same pattern as BUG-007-S1

### Project Structure Notes

- File: `frontend/src/components/trading/LiquidationAlert.tsx`

### References

- [Source: _bmad-output/bug-007-epic-stories.md#Story-1b]

## Dev Agent Record

### Agent Model Used

_To be filled by dev agent_

### Debug Log References

### Completion Notes List

### File List

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-29 | Bob (SM) | Story created from BUG-007 Epic |
