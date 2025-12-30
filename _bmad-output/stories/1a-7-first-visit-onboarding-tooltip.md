# Story 1A.7: First-Visit Onboarding Tooltip

Status: review

## Story

As a **new trader (Trader A)**,
I want **a simple welcome tooltip explaining the dashboard on first visit**,
so that **I understand where signals will appear and how to start**.

## Acceptance Criteria

1. **AC1:** Tooltip appears on first visit to dashboard
2. **AC2:** Tooltip explains: "This is your dashboard where signals appear"
3. **AC3:** Tooltip points to key areas (signal area, status, indicators)
4. **AC4:** User can dismiss tooltip and it doesn't reappear
5. **AC5:** Tooltip is non-blocking (user can interact with dashboard)

## Tasks / Subtasks

- [x] **Task 1: Detect First Visit** (AC: 1, 4)
  - [x] 1.1 Check localStorage for `hasSeenOnboarding` flag
  - [x] 1.2 Show tooltip if flag is not set
  - [x] 1.3 Set flag after dismissal
  - [x] 1.4 Provide "Reset onboarding" option in settings (optional)

- [x] **Task 2: Create Tooltip Content** (AC: 2, 3)
  - [x] 2.1 Write friendly welcome message
  - [x] 2.2 Highlight key dashboard areas
  - [x] 2.3 Add "Got it!" dismiss button
  - [ ] 2.4 Optional: multi-step tour (if time permits)

- [x] **Task 3: Tooltip Component** (AC: 5)
  - [x] 3.1 Use MUI Tooltip or Popper component
  - [x] 3.2 Position near StatusHero
  - [x] 3.3 Ensure non-blocking (can click through)
  - [x] 3.4 Add subtle animation

- [x] **Task 4: Styling** (AC: 5)
  - [x] 4.1 Friendly, welcoming design
  - [x] 4.2 Match overall theme
  - [x] 4.3 Mobile-friendly positioning

## Dev Notes

### Trader A Requirement

From Epics: "First-Visit Onboarding Tooltip - Simple welcome explaining 'This is your dashboard where signals appear' (Trader A)"

Trader A = Beginner trader who needs guidance.

### Content Suggestion

```
🎉 Welcome to FX Agent AI!

This is your trading dashboard where you'll see:
• 🔥 Signals when the system detects opportunities
• 📈 Current state of your strategy
• 📊 Real-time indicator values

Ready to start? Click "Quick Start" to load a template strategy!

[Got it!]
```

### Implementation Pattern

```typescript
// hooks/useOnboarding.ts
export function useOnboarding() {
  const [hasSeenOnboarding, setHasSeenOnboarding] = useState(() => {
    return localStorage.getItem('hasSeenOnboarding') === 'true';
  });

  const dismissOnboarding = () => {
    localStorage.setItem('hasSeenOnboarding', 'true');
    setHasSeenOnboarding(true);
  };

  return { showOnboarding: !hasSeenOnboarding, dismissOnboarding };
}
```

### Component Example

```tsx
// components/onboarding/WelcomeTooltip.tsx
export function WelcomeTooltip({ onDismiss }: { onDismiss: () => void }) {
  return (
    <Paper elevation={8} sx={{ p: 3, maxWidth: 320 }}>
      <Typography variant="h6">🎉 Welcome!</Typography>
      <Typography variant="body2" sx={{ my: 2 }}>
        This is your trading dashboard where signals appear...
      </Typography>
      <Button variant="contained" onClick={onDismiss}>
        Got it!
      </Button>
    </Paper>
  );
}
```

### UX Considerations

- Keep text minimal and friendly
- Use emojis for visual interest
- Don't overwhelm with too much info
- Make dismiss button prominent
- Consider "Don't show again" checkbox

### References

- [Source: _bmad-output/epics.md#Epic 1A Story 7]
- [Source: _bmad-output/ux-design-specification.md#Trader A Persona]
- [Source: _bmad-output/ux-design-specification.md#Onboarding]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References
N/A - No debug issues encountered

### Completion Notes List
- Implemented `useOnboarding` hook with localStorage persistence for first-visit detection
- Created `WelcomeTooltip` component with MUI Paper, Fade animation, and List for features
- Hook provides `showOnboarding`, `dismissOnboarding`, and `resetOnboarding` functions
- Tooltip is non-blocking (fixed position, no backdrop) and mobile-friendly (responsive maxWidth)
- Integrated into dashboard page - tooltip appears on first visit, dismisses on "Got it!" click
- All 26 tests passing (9 for useOnboarding hook, 17 for WelcomeTooltip component)

### File List
- `frontend/src/hooks/useOnboarding.ts` (NEW)
- `frontend/src/hooks/__tests__/useOnboarding.test.tsx` (NEW)
- `frontend/src/components/onboarding/WelcomeTooltip.tsx` (NEW)
- `frontend/src/components/onboarding/index.ts` (NEW)
- `frontend/src/components/onboarding/__tests__/WelcomeTooltip.test.tsx` (NEW)
- `frontend/src/app/dashboard/page.tsx` (MODIFIED - added imports and WelcomeTooltip integration)

### Change Log
- 2025-12-30: Story implemented with useOnboarding hook, WelcomeTooltip component, and dashboard integration. 26 tests added.
