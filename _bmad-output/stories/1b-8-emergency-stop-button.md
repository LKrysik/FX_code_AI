# Story 1B-8: Emergency Stop Button + Esc Shortcut

**Status:** implemented
**Priority:** P0 (MVP)
**Epic:** Epic 1B - First Successful Backtest

---

## Story

As a **trader**,
I want **to immediately stop any running backtest or trading session**,
So that **I can halt operations quickly in an emergency**.

---

## Acceptance Criteria

1. **AC1:** Prominent red "STOP" button is always visible when session is active
2. **AC2:** Button is labeled clearly (text, not just icon)
3. **AC3:** Pressing Esc key shows confirmation dialog: "Stop session? This cannot be undone."
4. **AC4:** Confirm with Enter or cancel with Esc again
5. **AC5:** Session stops within 1 second of confirmation
6. **AC6:** Open simulated positions are closed at current price
7. **AC7:** Final P&L is calculated and displayed
8. **AC8:** Status shows "Stopped by user" after stop
9. **AC9:** Partial results are preserved and viewable
10. **AC10:** Settings option to toggle "Esc to stop session" on/off

---

## Tasks / Subtasks

- [x] Task 1: Create EmergencyStopButton component (AC: 1, 2)
  - [x] Red button with "STOP" label
  - [x] Fixed position (always visible)
  - [x] Disabled when no session active

- [x] Task 2: Implement Esc shortcut (AC: 3, 4)
  - [x] Global keyboard listener for Esc
  - [x] Confirmation dialog component
  - [x] Enter to confirm, Esc to cancel
  - [x] Focus management for accessibility

- [x] Task 3: Implement stop API (AC: 5, 6, 7)
  - [x] API endpoint: POST /api/paper-trading/emergency-stop
  - [x] Backend closes positions at current price
  - [x] Calculate and return final P&L
  - [x] Response within 1 second (NFR)

- [x] Task 4: Update session status (AC: 8, 9)
  - [x] Update UI to show "Stopped by user"
  - [x] Preserve partial results in state
  - [x] Allow viewing of stopped session results

- [x] Task 5: Settings toggle (AC: 10)
  - [x] Existing settings already has escShortcutEnabled in shortcuts settings
  - [x] Check setting before showing Esc dialog
  - [x] Default: enabled

---

## Implementation Details

### Files Created

**Frontend:**
- `frontend/src/components/session/EmergencyStopButton.tsx` - Main stop button component
- `frontend/src/components/session/StopConfirmationDialog.tsx` - Confirmation dialog with keyboard support
- `frontend/src/components/session/index.ts` - Module exports
- `frontend/src/hooks/useEscShortcut.ts` - Global Esc key handler hook

**Tests:**
- `frontend/src/components/session/__tests__/EmergencyStopButton.test.tsx`
- `frontend/src/components/session/__tests__/StopConfirmationDialog.test.tsx`
- `frontend/src/hooks/__tests__/useEscShortcut.test.ts`

**Backend:**
- `src/api/paper_trading_routes.py` - Added `/api/paper-trading/emergency-stop` endpoint

**API Service:**
- `frontend/src/services/api.ts` - Added `emergencyStop()` and `stopSessionById()` methods

### Component Structure

```typescript
// EmergencyStopButton Props
interface EmergencyStopButtonProps {
  sessionId?: string | null;
  onStop?: () => Promise<void>;
  disabled?: boolean;
  size?: 'small' | 'medium' | 'large';
  showOnlyWhenActive?: boolean;
  variant?: 'inline' | 'fixed';
}

// StopConfirmationDialog Props
interface StopConfirmationDialogProps {
  open: boolean;
  onConfirm: () => void | Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
  sessionId?: string | null;
  sessionType?: string;
}

// useEscShortcut Options
interface UseEscShortcutOptions {
  enabled?: boolean;
  onEscPress: () => void;
  isSessionActive?: boolean;
  preventInInputs?: boolean;
  preventWhenDialogOpen?: boolean;
  isDialogOpen?: boolean;
}
```

### API Endpoint

```
POST /api/paper-trading/emergency-stop
Headers: X-CSRF-Token: <token>
Response: {
  success: true,
  data: {
    sessions_stopped: 1,
    positions_closed: 2,
    total_pnl: -123.45,
    status: "stopped_by_user",
    elapsed_seconds: 0.234,
    message: "Emergency stop completed: 1 session(s) stopped"
  }
}
```

### Usage Example

```tsx
// Basic usage (integrates with trading store)
<EmergencyStopButton />

// Fixed position variant (always visible top-right)
<EmergencyStopButton variant="fixed" />

// With useEscShortcut hook for global keyboard handling
const [showDialog, setShowDialog] = useState(false);

useEscShortcut({
  enabled: settings.shortcuts.shortcutsEnabled,
  onEscPress: () => setShowDialog(true),
  isSessionActive: currentSession !== null,
  isDialogOpen: showDialog,
});
```

### Features

1. **Visual Design**
   - Red MUI Button with error color variant
   - Pulse animation when session active for visibility
   - Stop icon + "STOP" text label
   - Tooltip with keyboard shortcut hint

2. **Keyboard Support**
   - Esc opens confirmation dialog (global listener)
   - Enter confirms stop in dialog
   - Esc cancels/closes dialog
   - Debouncing for rapid key presses
   - Blocked in input/textarea elements

3. **Dialog Features**
   - Warning about irreversibility
   - Lists what will happen on stop
   - Shows session ID and type
   - Loading state during stop operation
   - Focus automatically on confirm button

4. **Integration**
   - Uses tradingStore for session state
   - Uses uiStore for notifications
   - Works with existing settings for shortcut toggle
   - Proper error handling with notifications

---

## Definition of Done

1. [x] Red STOP button visible when session active
2. [x] Button disabled when no session
3. [x] Esc key triggers confirmation dialog
4. [x] Dialog has Enter/Esc keyboard shortcuts
5. [x] Stop API returns within 1 second
6. [x] Positions closed on stop
7. [x] Final P&L displayed
8. [x] "Stopped by user" status shown
9. [x] Partial results viewable
10. [x] Settings toggle for Esc shortcut
11. [x] Unit tests for keyboard handling
12. [ ] Integration test for stop flow (requires E2E test setup)

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-31 | SM | Story created for Epic 1B kickoff |
| 2025-12-31 | Claude Code | Implemented all components, hooks, API endpoint, and unit tests |
