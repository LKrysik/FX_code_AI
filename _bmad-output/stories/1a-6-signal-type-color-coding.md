# Story 1A.6: Signal Type Color Coding

Status: ready-for-dev

## Story

As a **trader**,
I want **different signal types to have distinct colors**,
so that **I can instantly distinguish between S1, O1, Z1, ZE1, and E1 signals**.

## Acceptance Criteria

1. **AC1:** Each signal type has a unique, distinct color
2. **AC2:** Colors are consistent across all signal displays
3. **AC3:** Colors match UX specification
4. **AC4:** Color-blind friendly (icons supplement colors)
5. **AC5:** Works in both light and dark modes

## Tasks / Subtasks

- [ ] **Task 1: Define Color Palette** (AC: 1, 3)
  - [ ] 1.1 Create signal color constants from UX spec
  - [ ] 1.2 Define both light and dark variants
  - [ ] 1.3 Add to theme configuration

- [ ] **Task 2: Apply to Signal Cards** (AC: 2)
  - [ ] 2.1 Update SignalCard border/background color
  - [ ] 2.2 Use signal type to select color
  - [ ] 2.3 Test consistency across components

- [ ] **Task 3: Apply to State Badge** (AC: 2)
  - [ ] 3.1 Update StateBadge colors
  - [ ] 3.2 Ensure consistency with signal cards

- [ ] **Task 4: Accessibility** (AC: 4, 5)
  - [ ] 4.1 Add icons that work without color
  - [ ] 4.2 Test color contrast (4.5:1 minimum)
  - [ ] 4.3 Test in dark mode
  - [ ] 4.4 Verify color-blind accessibility

## Dev Notes

### UX-17 Requirement

From UX Spec: "Signal Type Color Coding - Visual distinction between signal types"

### Color Mapping

From UX Spec:
| Signal Type | Color | Hex | Icon |
|-------------|-------|-----|------|
| S1 (Signal Detected) | Amber | #F59E0B | 🔥 |
| O1 (Cancellation) | Gray | #6B7280 | ❌ |
| Z1 (Entry) | Amber | #F59E0B | 🎯 |
| ZE1 (Take Profit) | Green | #10B981 | 💰 |
| E1 (Emergency Exit) | Red | #EF4444 | 🛑 |

### Theme Implementation

```typescript
// theme/signalColors.ts
export const SIGNAL_COLORS = {
  S1: {
    light: { bg: '#FEF3C7', border: '#F59E0B', text: '#92400E' },
    dark: { bg: '#78350F', border: '#F59E0B', text: '#FEF3C7' },
  },
  O1: {
    light: { bg: '#F3F4F6', border: '#6B7280', text: '#374151' },
    dark: { bg: '#374151', border: '#6B7280', text: '#F3F4F6' },
  },
  Z1: {
    light: { bg: '#FEF3C7', border: '#F59E0B', text: '#92400E' },
    dark: { bg: '#78350F', border: '#F59E0B', text: '#FEF3C7' },
  },
  ZE1: {
    light: { bg: '#D1FAE5', border: '#10B981', text: '#065F46' },
    dark: { bg: '#065F46', border: '#10B981', text: '#D1FAE5' },
  },
  E1: {
    light: { bg: '#FEE2E2', border: '#EF4444', text: '#991B1B' },
    dark: { bg: '#991B1B', border: '#EF4444', text: '#FEE2E2' },
  },
} as const;

export function getSignalColor(signalType: string, mode: 'light' | 'dark') {
  return SIGNAL_COLORS[signalType]?.[mode] || SIGNAL_COLORS.S1[mode];
}
```

### Color-Blind Support

Icons must be visible alongside colors:
- S1: 🔥 Fire emoji (signal/alert)
- O1: ❌ Cross (cancelled)
- Z1: 🎯 Target (entry)
- ZE1: 💰 Money bag (profit)
- E1: 🛑 Stop sign (emergency)

### Contrast Requirements

WCAG 2.1 AA:
- Normal text: 4.5:1 minimum
- Large text (24px+): 3:1 minimum

Use online contrast checker to verify.

### References

- [Source: _bmad-output/ux-design-specification.md#Color System]
- [Source: _bmad-output/ux-design-specification.md#Color-Blind Support]
- [Source: _bmad-output/epics.md#Epic 1A Story 6]

## Dev Agent Record

### Agent Model Used
{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
