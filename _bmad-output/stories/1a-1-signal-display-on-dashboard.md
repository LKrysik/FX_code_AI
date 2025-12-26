# Story 1A.1: Signal Display on Dashboard

Status: ready-for-dev

## Story

As a **trader**,
I want **signals to appear prominently on the dashboard when they arrive**,
so that **I immediately know when the system detects a trading opportunity**.

## Acceptance Criteria

1. **AC1:** When `signal_generated` event arrives via WebSocket, signal appears on dashboard within 500ms
2. **AC2:** Signal display includes: type, symbol, timestamp, and key indicator value
3. **AC3:** New signals appear at top of list (most recent first)
4. **AC4:** Maximum 10 signals displayed (older ones removed)
5. **AC5:** Signal display uses prominent styling (not buried in UI)

## Tasks / Subtasks

- [ ] **Task 1: Connect WebSocket to Dashboard** (AC: 1)
  - [ ] 1.1 Verify `onSignals` callback in `websocket.ts` triggers
  - [ ] 1.2 Connect callback to `dashboardStore.addSignal()`
  - [ ] 1.3 Test signal appears in store within 500ms

- [ ] **Task 2: Create Signal Display Component** (AC: 2, 5)
  - [ ] 2.1 Create `SignalCard.tsx` component
  - [ ] 2.2 Display: signal type, symbol, timestamp
  - [ ] 2.3 Show key indicator value (e.g., pump_magnitude)
  - [ ] 2.4 Use prominent styling (elevation, border, size)

- [ ] **Task 3: Signal List on Dashboard** (AC: 3, 4)
  - [ ] 3.1 Create `SignalList.tsx` to display multiple signals
  - [ ] 3.2 Order by timestamp (newest first)
  - [ ] 3.3 Limit to 10 signals (dashboardStore already does this)
  - [ ] 3.4 Add to dashboard layout in prominent position

- [ ] **Task 4: Integration with Existing Dashboard** (AC: 5)
  - [ ] 4.1 Identify best location on dashboard for signals
  - [ ] 4.2 Integrate SignalList into dashboard layout
  - [ ] 4.3 Ensure visibility without scrolling

## Dev Notes

### Dependency

Requires Epic 0 completion (signal flow working).

### FR18 Requirement

From PRD: "FR18: Trader can view generated signals on the price chart"

### Signal Data Structure

From `dashboardStore.ts`:
```typescript
interface ActiveSignal {
  id: string;
  symbol: string;
  signalType: 'pump' | 'dump';
  magnitude: number;
  confidence: number;
  timestamp: string;
  strategy: string;
}
```

### WebSocket Signal Flow

```
websocket.ts onSignals callback
    ↓
dashboardStore.addSignal(signal)
    ↓
SignalList component re-renders
    ↓
Signal visible on dashboard
```

### Component Placement

Dashboard layout suggestion:
```
┌─────────────────────────────────────────────────┐
│  HEADER (Status, Navigation)                    │
├──────────────────────┬──────────────────────────┤
│  SIGNALS (prominent) │  CHART                   │
│  ┌────────────────┐  │                          │
│  │ 🔥 BTCUSDT     │  │                          │
│  │ +7.2% pump     │  │                          │
│  └────────────────┘  │                          │
│  ┌────────────────┐  │                          │
│  │ 🔥 ETHUSDT     │  │                          │
│  │ +5.1% pump     │  │                          │
│  └────────────────┘  │                          │
├──────────────────────┴──────────────────────────┤
│  INDICATORS                                      │
└─────────────────────────────────────────────────┘
```

### References

- [Source: _bmad-output/prd.md#FR18]
- [Source: _bmad-output/epics.md#Epic 1A Story 1]
- [Source: frontend/src/stores/dashboardStore.ts:46-58]
- [Source: frontend/src/services/websocket.ts:277-288]

## Dev Agent Record

### Agent Model Used
{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
