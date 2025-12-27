# Story 1A.1: Signal Display on Dashboard

Status: completed

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

- [x] **Task 1: Connect WebSocket to Dashboard** (AC: 1)
  - [x] 1.1 Verify `onSignals` callback in `websocket.ts` triggers - lines 313, 436
  - [x] 1.2 Connect callback to `dashboardStore.addSignal()` - RecentSignalsPanel.tsx:59-75
  - [x] 1.3 Test signal appears in store within 500ms - RecentSignalsPanel.test.tsx

- [x] **Task 2: Create Signal Display Component** (AC: 2, 5)
  - [x] 2.1 Create `SignalCard.tsx` component - SignalCard.tsx
  - [x] 2.2 Display: signal type, symbol, timestamp - SignalCard.tsx:95-145
  - [x] 2.3 Show key indicator value (pump_magnitude) - SignalCard.tsx:148-163
  - [x] 2.4 Use prominent styling (elevation, border, size) - SignalCard.tsx:83-97

- [x] **Task 3: Signal List on Dashboard** (AC: 3, 4)
  - [x] 3.1 Create `RecentSignalsPanel.tsx` component - RecentSignalsPanel.tsx
  - [x] 3.2 Order by timestamp (newest first) - dashboardStore.addSignal prepends
  - [x] 3.3 Limit to 10 signals - RecentSignalsPanel.tsx:89, dashboardStore.ts:64
  - [x] 3.4 Add to dashboard layout in prominent position - dashboard/page.tsx:891-901

- [x] **Task 4: Integration with Existing Dashboard** (AC: 5)
  - [x] 4.1 Identify best location: Left column above Symbol Watchlist
  - [x] 4.2 Integrate RecentSignalsPanel into dashboard - dashboard/page.tsx:891-901
  - [x] 4.3 Ensure visibility without scrolling - Placed in Grid md={4} column

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

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Console logs: `[1A-1] Signal received via WebSocket:`, `[1A-1] WebSocket signal callback registered`
- Signal flow logging: `[SIGNAL-FLOW] Signal added to store:`

### Completion Notes List

1. Task 1: WebSocket `onSignals` callback already exists - connected to dashboardStore in RecentSignalsPanel
2. Task 2: Created SignalCard.tsx with prominent styling (colored borders, icons, confidence bar)
3. Task 3: Created RecentSignalsPanel.tsx using Zustand store subscriptions
4. Task 4: Integrated into dashboard left column (Grid md={4}) above SymbolWatchlist
5. Fixed bug: dashboardStore.addSignal was logging `signal_type` instead of `signalType`
6. Tests: Added SignalCard.test.tsx and RecentSignalsPanel.test.tsx

### File List

| File | Changes |
|------|---------|
| `frontend/src/components/dashboard/SignalCard.tsx` | NEW - Signal display card component |
| `frontend/src/components/dashboard/RecentSignalsPanel.tsx` | NEW - Panel with WebSocket integration |
| `frontend/src/components/dashboard/__tests__/SignalCard.test.tsx` | NEW - Unit tests |
| `frontend/src/components/dashboard/__tests__/RecentSignalsPanel.test.tsx` | NEW - Unit tests |
| `frontend/src/app/dashboard/page.tsx:72,891-901` | Added import and RecentSignalsPanel |
| `frontend/src/stores/dashboardStore.ts:56-58` | Fixed signal_type → signalType bug |
