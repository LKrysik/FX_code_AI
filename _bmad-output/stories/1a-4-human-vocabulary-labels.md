# Story 1A.4: Human Vocabulary Labels

Status: review

## Story

As a **trader**,
I want **to see human-readable labels instead of technical codes (S1, O1, Z1, etc.)**,
so that **I immediately understand what each state means without memorizing codes**.

## Acceptance Criteria

1. **AC1:** UI displays "Found!" instead of "S1", "Entering" instead of "Z1", etc.
2. **AC2:** Data contracts remain unchanged (API still uses S1, Z1, etc.)
3. **AC3:** Labels include appropriate icons/emojis
4. **AC4:** Transformation is centralized (single source of truth)
5. **AC5:** All dashboard components use human vocabulary

## Tasks / Subtasks

- [x] **Task 1: Create Vocabulary Mapping** (AC: 2, 4)
  - [x] 1.1 Create `utils/stateVocabulary.ts` with mappings
  - [x] 1.2 Map all state codes to human labels
  - [x] 1.3 Include icon/emoji for each state
  - [x] 1.4 Export helper functions for components

- [x] **Task 2: Update StateBadge** (AC: 1, 3)
  - [x] 2.1 Import vocabulary mapping from stateVocabulary.ts
  - [x] 2.2 Display human label instead of code via getStateVocabulary()
  - [x] 2.3 Show icon alongside label (already present, now centralized)

- [x] **Task 3: Update Signal Display** (AC: 1, 5)
  - [x] 3.1 Apply vocabulary to SignalCard.tsx
  - [x] 3.2 Use getSignalVocabulary() for pump/dump labels
  - [x] 3.3 Use consistent icons from centralized vocabulary

- [x] **Task 4: Update Any Other Displays** (AC: 5)
  - [x] 4.1 Audited: SignalLog.tsx, StateOverviewTable.tsx, TransitionLog.tsx
  - [x] 4.2 Updated SignalLog.tsx to use getSignalLabel()
  - [x] 4.3 Updated StateOverviewTable STATE_PRIORITY to include all states
  - [x] 4.4 StatusHero.tsx noted for update in Story 1A-5 (separate story)

## Dev Notes

### UX Requirement

From UX Spec: "Human Vocabulary Transformation"

**IMPORTANT:** This is UI-ONLY. Data contracts (API, WebSocket, database) continue to use S1, Z1, etc. Only the display layer transforms to human words.

### Vocabulary Mapping

| Technical | Human | Icon |
|-----------|-------|------|
| MONITORING | Watching | 👀 |
| S1 | Found! | 🔥 |
| O1 | False Alarm | ❌ |
| Z1 | Entering | 🎯 |
| POSITION_ACTIVE | Monitoring | 📈 |
| ZE1 | Taking Profit | 💰 |
| E1 | Stopping Loss | 🛑 |

### Implementation Pattern

```typescript
// utils/stateVocabulary.ts
export const STATE_VOCABULARY = {
  MONITORING: { label: 'Watching', icon: '👀', description: 'Scanning for signals' },
  S1: { label: 'Found!', icon: '🔥', description: 'Signal detected' },
  O1: { label: 'False Alarm', icon: '❌', description: 'Signal cancelled' },
  Z1: { label: 'Entering', icon: '🎯', description: 'Entry conditions met' },
  POSITION_ACTIVE: { label: 'Monitoring', icon: '📈', description: 'Position open' },
  ZE1: { label: 'Taking Profit', icon: '💰', description: 'Profit target reached' },
  E1: { label: 'Stopping Loss', icon: '🛑', description: 'Emergency exit triggered' },
} as const;

export function getHumanLabel(state: string): string {
  return STATE_VOCABULARY[state]?.label || state;
}

export function getStateIcon(state: string): string {
  return STATE_VOCABULARY[state]?.icon || '❓';
}
```

### Usage in Components

```tsx
import { getHumanLabel, getStateIcon } from '@/utils/stateVocabulary';

// In StateBadge
<Chip
  icon={<span>{getStateIcon(state)}</span>}
  label={getHumanLabel(state)}
/>
```

### Why UI-Only?

- Backend/API contracts are stable and tested
- Changing data contracts risks breaking integrations
- Multiple UIs could have different vocabularies
- Keeps data layer language-agnostic

### References

- [Source: _bmad-output/ux-design-specification.md#Vocabulary Transformation]
- [Source: _bmad-output/epics.md#Epic 1A Story 4]
- [Source: frontend/src/components/dashboard/StateBadge]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References
- Console logs: `[1A-4]` prefix used in vocabulary utility

### Completion Notes List
1. Created centralized vocabulary in `utils/stateVocabulary.ts` with STATE_VOCABULARY and SIGNAL_TYPE_VOCABULARY
2. Updated StateBadge.tsx to import from centralized vocabulary instead of inline STATE_CONFIG
3. Updated SignalCard.tsx to use getSignalVocabulary() for pump/dump labels
4. Updated SignalLog.tsx to use getSignalLabel() instead of hardcoded switch statement
5. Updated StateOverviewTable.tsx STATE_PRIORITY to include all states (S1, O1, Z1, ZE1, E1)
6. Created 25 comprehensive tests in stateVocabulary.test.ts
7. StatusHero.tsx has duplicate vocabulary but is part of Story 1A-5 - will be updated there
8. All tests pass (25/25)
9. Data contracts unchanged (API still uses S1, Z1, etc.) - transformation is UI-only (AC2)

### File List

| File | Changes |
|------|---------|
| `frontend/src/utils/stateVocabulary.ts` | NEW - Centralized vocabulary mapping (AC4) |
| `frontend/src/utils/__tests__/stateVocabulary.test.ts` | NEW - 25 tests for vocabulary utility |
| `frontend/src/components/dashboard/StateBadge.tsx` | Updated to import from stateVocabulary.ts |
| `frontend/src/components/dashboard/SignalCard.tsx` | Updated to use getSignalVocabulary() |
| `frontend/src/components/trading/SignalLog.tsx` | Updated to use getSignalLabel() |
| `frontend/src/components/dashboard/StateOverviewTable.tsx` | Updated STATE_PRIORITY with all states |
