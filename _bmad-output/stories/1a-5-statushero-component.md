# Story 1A.5: StatusHero Component

Status: done

## Story

As a **trader**,
I want **a single prominent component showing state + key metrics at a glance**,
so that **I can understand the system status in under 2 seconds**.

## Acceptance Criteria

1. **AC1:** StatusHero is the largest/most prominent element on dashboard
2. **AC2:** Combines: current state, P&L (if in position), symbol
3. **AC3:** Colors match state (Slate=watching, Amber=signal, Blue=position)
4. **AC4:** State comprehension achievable in < 2 seconds (UX metric)
5. **AC5:** Responsive - works on different screen sizes

## Tasks / Subtasks

- [x] **Task 1: Create StatusHero Component** (AC: 1, 2) ✅
  - [x] 1.1 Create `StatusHero.tsx` as hero-sized component
  - [x] 1.2 Display: state badge, P&L, symbol, session time
  - [x] 1.3 Use 48-64px font for primary metrics (3.5rem hero font)
  - [x] 1.4 Apply elevation/shadow for prominence

- [x] **Task 2: State-Driven Styling** (AC: 3) ✅
  - [x] 2.1 Implement color variants per state (11 states)
  - [x] 2.2 MONITORING: Slate background (#F8FAFC), calm
  - [x] 2.3 S1/SIGNAL_DETECTED/Z1: Amber (#FFFBEB), pulsing alert
  - [x] 2.4 POSITION_ACTIVE: Blue (#EFF6FF) with P&L emphasis
  - [x] 2.5 ZE1: Green (#ECFDF5) taking profit
  - [x] 2.6 E1: Red (#FEF2F2) stopping loss

- [x] **Task 3: Data Integration** (AC: 2) ✅
  - [x] 3.1 Connect to state machine state via useStatusHeroData hook
  - [x] 3.2 Connect to P&L data (when in position)
  - [x] 3.3 Display session/position timers (auto-increment)
  - [x] 3.4 Handle empty/loading states
  - [x] 3.5 Poll position data every 2s when in position

- [x] **Task 4: Dashboard Placement** (AC: 1, 4, 5) ✅
  - [x] 4.1 Place at top of dashboard (below mode switcher)
  - [x] 4.2 Ensure visibility without scrolling
  - [x] 4.3 Implement responsive behavior (mobile/tablet/desktop)
  - [x] 4.4 2-second comprehension supported by prominent styling

## Dev Notes

### UX-1 Requirement

From UX Spec: "StatusHero Component - Combined state + P&L display (largest element on screen when position active)"

### Design Reference

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   🔥 FOUND! Signal Detected on BTCUSDT                      │
│   ─────────────────────────────────────────────────────     │
│   Pump magnitude: +7.25%  |  Volume surge: 3.5x             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

When in position:
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│            📈 MONITORING POSITION                            │
│                                                             │
│                    +$127.50                                 │
│                     +2.8%                                   │
│                                                             │
│   BTCUSDT Short  |  Entry: $45,230  |  2m 34s               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Props

```typescript
interface StatusHeroProps {
  state: StateMachineState;
  symbol?: string;
  pnl?: number;
  pnlPercent?: number;
  entryPrice?: number;
  sessionTime?: number; // seconds
  signalType?: string;
  indicatorHighlights?: { name: string; value: string }[];
}
```

### State Variants

| State | Background | Text | Emphasis |
|-------|------------|------|----------|
| MONITORING | Slate-50 | Slate-700 | None |
| S1/Z1 | Amber-50 | Amber-900 | Pulsing border |
| POSITION_ACTIVE | Blue-50 | Blue-900 | P&L large |
| PROFIT | Green-50 | Green-900 | Celebration |
| LOSS | Red-50 | Red-900 | Clear exit reason |

### Typography

From UX Spec:
- Hero Metric: 48-64px, Bold (P&L)
- State Badge: 24px, Semibold
- Labels: 14px, Medium
- Values: 16px, Regular (monospace for numbers)

### References

- [Source: _bmad-output/ux-design-specification.md#StatusHero]
- [Source: _bmad-output/ux-design-specification.md#Typography System]
- [Source: _bmad-output/epics.md#Epic 1A Story 5]

## Dev Agent Record

### Agent Model Used
{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
