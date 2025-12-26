# Story 0.5: Error Display Pattern

Status: ready-for-dev

## Story

As a **trader**,
I want **all errors to be displayed visibly in the UI with context**,
so that **I never experience silent failures and always know what went wrong**.

## Acceptance Criteria

1. **AC1:** API errors display in a toast/snackbar with error message
2. **AC2:** WebSocket disconnection shows visible banner
3. **AC3:** Critical errors (data loss risk) show full-screen modal
4. **AC4:** All errors include actionable recovery suggestion
5. **AC5:** Error state is logged for debugging (console + optional backend)

## Tasks / Subtasks

- [ ] **Task 1: Establish Error Display Components** (AC: 1, 3)
  - [ ] 1.1 Create/verify `ErrorToast` component for transient errors
  - [ ] 1.2 Create/verify `ErrorBanner` component for persistent warnings
  - [ ] 1.3 Create/verify `CriticalErrorModal` for blocking errors
  - [ ] 1.4 Define error severity levels (info, warning, error, critical)

- [ ] **Task 2: API Error Handling** (AC: 1, 4)
  - [ ] 2.1 Audit existing try/catch in `api.ts`
  - [ ] 2.2 Ensure all API calls show toast on failure
  - [ ] 2.3 Include error message from backend response
  - [ ] 2.4 Add retry button where applicable

- [ ] **Task 3: WebSocket Error Handling** (AC: 2)
  - [ ] 3.1 Add disconnect banner to Layout
  - [ ] 3.2 Show reconnection countdown
  - [ ] 3.3 Banner dismisses on successful reconnect
  - [ ] 3.4 Integrate with existing `websocketStore` status

- [ ] **Task 4: Critical Error Handling** (AC: 3, 4)
  - [ ] 4.1 Define critical error triggers (position at risk, data corruption)
  - [ ] 4.2 Create full-screen modal with recovery options
  - [ ] 4.3 Prevent user from dismissing without action
  - [ ] 4.4 Optional: sound alert for critical errors

- [ ] **Task 5: Error Logging** (AC: 5)
  - [ ] 5.1 Ensure all errors log to console with context
  - [ ] 5.2 Include stack trace where available
  - [ ] 5.3 Optional: send error to backend logging endpoint
  - [ ] 5.4 Test error capture in production build

## Dev Notes

### NFR7 Requirement

From PRD: "NFR7: System must not have silent failures - all errors must surface to UI"

### UX Design Rule

From UX Spec: "Error states MUST be impossible to miss - Full-screen if critical"

### Error Severity Levels

| Level | Component | Auto-dismiss | Example |
|-------|-----------|--------------|---------|
| INFO | Toast | 3s | "Strategy saved" |
| WARNING | Toast | 5s | "Slow connection detected" |
| ERROR | Toast | Persist | "Failed to load strategy" |
| CRITICAL | Modal | Never | "Position at risk - action required" |

### Existing Error Infrastructure

From `statusUtils.tsx`:
```typescript
categorizeError(error)      // Categorize error type
logUnifiedError(error)      // Structured logging
getErrorRecoveryStrategy()  // Suggest recovery action
```

From `ErrorBoundaryProvider.tsx`:
```typescript
// React Error Boundary for component crashes
```

### Toast Pattern (MUI Snackbar)

```typescript
import { useSnackbar } from 'notistack';

const { enqueueSnackbar } = useSnackbar();

// On API error
enqueueSnackbar('Failed to save strategy', {
  variant: 'error',
  action: (key) => (
    <Button onClick={() => retry()}>Retry</Button>
  )
});
```

### WebSocket Banner Pattern

```typescript
// In Layout.tsx
const { isConnected, connectionStatus } = useWebSocketStore();

{!isConnected && (
  <Alert severity="warning" sx={{ position: 'fixed', top: 0, width: '100%' }}>
    Connection lost. Reconnecting in {countdown}s...
    <Button onClick={manualReconnect}>Reconnect Now</Button>
  </Alert>
)}
```

### Critical Error Modal Pattern

```typescript
// Full-screen blocking modal
<Dialog fullScreen open={criticalError !== null} disableEscapeKeyDown>
  <DialogTitle>Critical Error</DialogTitle>
  <DialogContent>
    <Typography>{criticalError.message}</Typography>
    <Typography>Recovery: {criticalError.recovery}</Typography>
  </DialogContent>
  <DialogActions>
    <Button onClick={handleRecovery}>Take Action</Button>
  </DialogActions>
</Dialog>
```

### Key Files to Touch

| File | Purpose |
|------|---------|
| `frontend/src/utils/statusUtils.tsx` | Error categorization |
| `frontend/src/providers/ErrorBoundaryProvider.tsx` | React error boundary |
| `frontend/src/services/api.ts` | API error handling |
| `frontend/src/services/websocket.ts` | WS error handling |
| `frontend/src/components/layout/Layout.tsx` | Error banner placement |

### References

- [Source: _bmad-output/prd.md#NFR7: No silent failures]
- [Source: _bmad-output/ux-design-specification.md#Error Visibility]
- [Source: frontend/src/utils/statusUtils.tsx]
- [Source: frontend/src/providers/ErrorBoundaryProvider.tsx]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
