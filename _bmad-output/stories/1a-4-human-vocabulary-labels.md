# Story 1A.4: Human Vocabulary Labels

Status: ready-for-dev

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

- [ ] **Task 1: Create Vocabulary Mapping** (AC: 2, 4)
  - [ ] 1.1 Create `utils/stateVocabulary.ts` with mappings
  - [ ] 1.2 Map all state codes to human labels
  - [ ] 1.3 Include icon/emoji for each state
  - [ ] 1.4 Export helper functions for components

- [ ] **Task 2: Update StateBadge** (AC: 1, 3)
  - [ ] 2.1 Import vocabulary mapping
  - [ ] 2.2 Display human label instead of code
  - [ ] 2.3 Show icon alongside label

- [ ] **Task 3: Update Signal Display** (AC: 1, 5)
  - [ ] 3.1 Apply vocabulary to signal cards
  - [ ] 3.2 Show "Found!" for S1 signals
  - [ ] 3.3 Use consistent icons

- [ ] **Task 4: Update Any Other Displays** (AC: 5)
  - [ ] 4.1 Audit all places showing state codes
  - [ ] 4.2 Apply vocabulary mapping
  - [ ] 4.3 Test visual consistency

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
{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
