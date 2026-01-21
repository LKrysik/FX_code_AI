# Story 1B-5: JourneyBar Component

**Status:** complete
**Priority:** P0 (MVP)
**Epic:** Epic 1B - First Successful Backtest

---

## Story

As a **trader**,
I want **to see a visual representation of the trading flow**,
So that **I can understand where I am in the trading cycle**.

---

## Acceptance Criteria

1. **AC1:** JourneyBar displays trading flow as connected steps: Watch -> Found -> Enter -> Monitor -> Exit
2. **AC2:** Each step is represented by an icon and label
3. **AC3:** Current step is highlighted (bold, colored, or glowing) based on state machine state
4. **AC4:** Completed steps show a checkmark
5. **AC5:** Future steps are dimmed/grayed
6. **AC6:** JourneyBar animates smoothly (300ms transition) when state changes
7. **AC7:** Exit step shows specific outcome color (green for profit, red for loss)

---

## Tasks / Subtasks

- [x] Task 1: Create JourneyBar component (AC: 1, 2)
  - [x] Horizontal stepper layout with 5 steps
  - [x] Icons for each step (Watch, Found, Enter, Monitor, Exit)
  - [x] Labels below icons
  - [x] Use MUI Stepper as base component

- [x] Task 2: State machine integration (AC: 3, 4, 5)
  - [x] Map state machine states to journey steps
  - [x] useStateMachineState hook integration (component accepts currentState prop)
  - [x] Determine completed/current/future status

- [x] Task 3: Visual styling (AC: 3, 6, 7)
  - [x] Current step highlight (primary color, glow effect with pulse animation)
  - [x] Completed step checkmark icon
  - [x] Future step dimmed styling
  - [x] 300ms CSS transitions on all state changes

- [x] Task 4: Exit state handling (AC: 7)
  - [x] Detect profit/loss from exit state (ZE1/EXITED_PROFIT = profit, E1/EXITED_LOSS = loss)
  - [x] Green color for profitable exit
  - [x] Red color for loss exit
  - [x] exitPnL prop support for explicit profit/loss coloring

---

## Dev Notes

### State Machine to Journey Mapping

| State Machine State | Journey Step | Icon |
|---------------------|--------------|------|
| IDLE, MONITORING | Watch | 👁️ Visibility |
| SIGNAL_DETECTED | Found | 🎯 Target |
| ENTERING, POSITION_OPEN | Enter | 📈 TrendingUp |
| POSITION_MONITORING | Monitor | ⚡ Activity |
| EXITING, EXITED_PROFIT, EXITED_LOSS | Exit | 🚪 ExitToApp |

### Component Props

```typescript
interface JourneyBarProps {
  currentState: StateMachineState;
  exitPnL?: number;  // For coloring exit step
  compact?: boolean; // Smaller version for mobile
}
```

### Visual Design

```
┌─────────────────────────────────────────────────────────────┐
│  [👁️]────[🎯]────[📈]────[⚡]────[🚪]                        │
│  Watch   Found   Enter  Monitor  Exit                       │
│    ✓       ●                                                │
│ (done) (current)  (future steps dimmed)                     │
└─────────────────────────────────────────────────────────────┘
```

### Files to Create

**Frontend:**
- `frontend/src/components/dashboard/JourneyBar.tsx` (new)
- `frontend/src/components/dashboard/JourneyBar.test.tsx` (new)

---

## Definition of Done

1. [x] JourneyBar component renders 5 steps
2. [x] Icons and labels display correctly
3. [x] Current step highlighted based on state
4. [x] Completed steps show checkmarks
5. [x] Future steps are dimmed
6. [x] Smooth animation on state change
7. [x] Exit step shows profit/loss color
8. [x] Unit tests for state mapping (58 tests passing)
9. [ ] Integration with dashboard page (pending - component ready for integration)

---

## Implementation Details

### Files Created

- `frontend/src/components/dashboard/JourneyBar.tsx` - Main component (280 lines)
- `frontend/src/components/dashboard/__tests__/JourneyBar.test.tsx` - Unit tests (58 tests)

### Component API

```typescript
interface JourneyBarProps {
  currentState: StateMachineState;  // Required - current state machine state
  exitPnL?: number;                 // Optional - for explicit profit/loss coloring
  compact?: boolean;                // Optional - smaller version for mobile
}
```

### State Mapping Implementation

| State Machine State | Journey Step Index | Journey Step |
|---------------------|-------------------|--------------|
| IDLE, MONITORING, INACTIVE, ERROR | 0 | Watch |
| SIGNAL_DETECTED, S1 | 1 | Found |
| ENTERING, POSITION_OPEN, Z1 | 2 | Enter |
| POSITION_MONITORING, POSITION_ACTIVE | 3 | Monitor |
| EXITING, EXITED_PROFIT, EXITED_LOSS, ZE1, E1, EXITED, O1 | 4 | Exit |

### Visual Features

- **Current step**: Primary color with pulse animation glow effect
- **Completed steps**: Green with checkmark icon
- **Future steps**: Gray/dimmed styling
- **Exit step profit**: Green glow and color
- **Exit step loss**: Red glow and color
- **All transitions**: 300ms ease-in-out CSS animations

### Exported Utilities

- `getStepIndexFromState(state)` - Maps state to step index
- `isExitProfit(state)` - Determines if exit is profit/loss/neutral
- `JOURNEY_STEPS` - Array of step definitions

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-31 | SM | Story created for Epic 1B kickoff |
| 2025-12-31 | Dev | Implemented JourneyBar component with all ACs |
| 2025-12-31 | Dev | Added 58 unit tests covering all acceptance criteria |
| 2025-12-31 | Dev | Story marked complete - component ready for dashboard integration |
