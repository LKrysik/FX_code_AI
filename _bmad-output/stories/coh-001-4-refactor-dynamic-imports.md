# Story COH-001-4: Refactor Dynamic Store Imports

**Status:** pending
**Priority:** LOW
**Effort:** S (Small)

---

## Story

As a **developer maintaining the WebSocket service**,
I want **clean dependency boundaries in websocket.ts**,
so that **the service is easier to test and understand**.

## Problem Statement

**Current Code** (`frontend/src/services/websocket.ts:603-611`):
```typescript
// Dynamic import of dashboardStore - creates hidden dependency
const { useDashboardStore } = await import('@/stores/dashboardStore');
useDashboardStore.getState().addSignal(signalData);
```

**Issues:**
1. Hidden runtime dependency - not visible in imports
2. Harder to mock in tests
3. Violates service → store boundary (services should be consumed by stores, not vice versa)
4. Creates circular dependency risk

## Acceptance Criteria

1. **AC1:** WebSocket service has no dynamic store imports
2. **AC2:** State updates flow through proper channels (events/callbacks)
3. **AC3:** All tests continue to pass
4. **AC4:** No circular dependencies

## Tasks / Subtasks

- [ ] Task 1: Analyze current usage (AC: 1)
  - [ ] Find all dynamic imports in websocket.ts
  - [ ] Document what each does
  - [ ] Identify callback alternatives

- [ ] Task 2: Implement callback pattern (AC: 2)
  - [ ] Add `onSignal` callback option to WebSocket service
  - [ ] Store subscribes to callback, not service to store
  - [ ] Remove dynamic imports

- [ ] Task 3: Update store connections (AC: 2, 3)
  - [ ] Dashboard initialization passes callback to wsService
  - [ ] Store updates itself based on callback

- [ ] Task 4: Test and verify (AC: 3, 4)
  - [ ] Run all tests
  - [ ] Check for circular dependencies
  - [ ] Verify signal flow works

## Dev Notes

### Proposed Pattern

**Before (service imports store):**
```typescript
// websocket.ts
const { useDashboardStore } = await import('@/stores/dashboardStore');
useDashboardStore.getState().addSignal(signalData);
```

**After (store subscribes to service):**
```typescript
// websocket.ts
class WebSocketService {
  private signalCallbacks: Array<(signal: Signal) => void> = [];

  onSignal(callback: (signal: Signal) => void): () => void {
    this.signalCallbacks.push(callback);
    return () => {
      this.signalCallbacks = this.signalCallbacks.filter(cb => cb !== callback);
    };
  }

  private handleSignal(signalData: Signal) {
    this.signalCallbacks.forEach(cb => cb(signalData));
  }
}

// dashboardStore.ts (or initialization code)
useEffect(() => {
  const unsubscribe = wsService.onSignal((signal) => {
    useDashboardStore.getState().addSignal(signal);
  });
  return unsubscribe;
}, []);
```

### Alternative: Event-based

```typescript
// websocket.ts emits custom events
window.dispatchEvent(new CustomEvent('ws:signal', { detail: signalData }));

// Store listens
window.addEventListener('ws:signal', (e) => {
  useDashboardStore.getState().addSignal(e.detail);
});
```

### Affected Files

- `frontend/src/services/websocket.ts`
- `frontend/src/stores/dashboardStore.ts`
- App initialization code (where subscriptions are set up)

## References

- [Coherence Analysis Report - Test 83 Boundary Violation]
- [ADR-001: WebSocket Singleton Pattern]

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-29 | John (PM) | Story created from Coherence Analysis |
