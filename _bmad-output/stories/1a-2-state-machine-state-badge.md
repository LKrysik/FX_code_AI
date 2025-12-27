# Story 1A.2: State Machine State Badge

Status: done

## Story

As a **trader**,
I want **to see a large, colored badge showing the current state machine state**,
so that **I instantly know what phase of trading the system is in**.

## Acceptance Criteria

1. **AC1:** Badge displays current state (MONITORING, S1, O1, Z1, ZE1, E1, POSITION_ACTIVE)
2. **AC2:** Badge color matches state (Slate=watching, Amber=signal, Blue=position, Green=profit, Red=loss)
3. **AC3:** Badge is large and prominent (hero element, not small indicator)
4. **AC4:** Badge updates in real-time when state changes
5. **AC5:** Badge shows human-readable label with icon

## Tasks / Subtasks

- [x] **Task 1: Create StateBadge Component** (AC: 1, 3, 5)
  - [x] 1.1 Create `StateBadge.tsx` with large, prominent styling
  - [x] 1.2 Map state values to display labels
  - [x] 1.3 Add appropriate icons for each state
  - [x] 1.4 Size: minimum 48px font, prominent shadow

- [x] **Task 2: Implement Color System** (AC: 2)
  - [x] 2.1 Define color palette from UX spec
  - [x] 2.2 Map each state to color
  - [x] 2.3 Implement as MUI theme or styled components
  - [x] 2.4 Include dark mode support (alpha transparency works in both modes)

- [x] **Task 3: Connect to State Data** (AC: 4)
  - [x] 3.1 Identify source of state machine state (WebSocket/store)
  - [x] 3.2 Subscribe to state changes
  - [x] 3.3 Update badge on state transition
  - [x] 3.4 Add transition animation

- [x] **Task 4: Place on Dashboard** (AC: 3)
  - [x] 4.1 Position badge prominently (top area)
  - [x] 4.2 Ensure always visible without scrolling
  - [x] 4.3 Test across viewport sizes

## Dev Notes

### FR19 Requirement

From PRD: "FR19: Trader can view current state machine state (which section is active)"

### UX Color System

From UX Spec:
| State | Color | Hex |
|-------|-------|-----|
| MONITORING | Slate | #64748B |
| S1 (Signal Detected) | Amber | #F59E0B |
| O1 (Cancellation) | Gray | #6B7280 |
| Z1 (Entry) | Amber | #F59E0B |
| POSITION_ACTIVE | Blue | #3B82F6 |
| ZE1 (Take Profit) | Green | #10B981 |
| E1 (Emergency Exit) | Red | #EF4444 |

### State to Label Mapping

From UX Spec (Human Vocabulary):
| Technical | Human | Icon |
|-----------|-------|------|
| MONITORING | Watching | 👀 |
| S1 | Found! | 🔥 |
| O1 | False Alarm | ❌ |
| Z1 | Entering | 🎯 |
| POSITION_ACTIVE | Monitoring | 📈 |
| ZE1 | Taking Profit | 💰 |
| E1 | Stopping Loss | 🛑 |

### Existing Component

Check if `StateBadge.tsx` already exists:
```
frontend/src/components/dashboard/StateBadge.integration.tsx
frontend/src/components/dashboard/StateBadge.README.md
```

### Component Structure

```typescript
interface StateBadgeProps {
  state: StateMachineState;
  size?: 'small' | 'medium' | 'large';
  showIcon?: boolean;
  showLabel?: boolean;
}

const STATE_CONFIG = {
  MONITORING: { color: '#64748B', label: 'Watching', icon: '👀' },
  S1: { color: '#F59E0B', label: 'Found!', icon: '🔥' },
  // ...
};
```

### References

- [Source: _bmad-output/prd.md#FR19]
- [Source: _bmad-output/ux-design-specification.md#Color System]
- [Source: _bmad-output/ux-design-specification.md#Vocabulary Transformation]
- [Source: frontend/src/components/dashboard/StateBadge.README.md]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References
- All 21 StateBadge tests passing

### Completion Notes List
- Updated StateBadge.tsx with 11 states (7 primary + 4 legacy)
- Implemented UX spec colors: Slate (#64748B), Amber (#F59E0B), Gray (#6B7280), Blue (#3B82F6), Green (#10B981), Red (#EF4444)
- Added hero size with 48px/3rem font and prominent shadow
- Created useStateMachineState hook for real-time WebSocket updates
- Placed hero badge on dashboard (page.tsx) visible without scrolling
- Updated tests for all new states

### File List
- `frontend/src/components/dashboard/StateBadge.tsx` - Updated component
- `frontend/src/components/dashboard/__tests__/StateBadge.test.tsx` - Updated tests
- `frontend/src/hooks/useStateMachineState.ts` - NEW: Hook for state machine state
- `frontend/src/app/dashboard/page.tsx` - Added hero StateBadge
