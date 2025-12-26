# Story 0.4: Debug Panel Foundation

Status: ready-for-dev

## Story

As a **developer**,
I want **a debug panel that shows raw WebSocket messages in real-time**,
so that **I can troubleshoot signal flow and data format issues during development**.

## Acceptance Criteria

1. **AC1:** Debug panel is accessible via keyboard shortcut (Ctrl+Shift+D) or dev menu
2. **AC2:** Panel shows last 50 WebSocket messages with timestamps
3. **AC3:** Messages are filterable by type (market_data, signals, indicators, etc.)
4. **AC4:** Panel can be collapsed/expanded without losing message history
5. **AC5:** Panel only visible in development mode (not production)

## Tasks / Subtasks

- [ ] **Task 1: Create Debug Panel Component** (AC: 1, 4)
  - [ ] 1.1 Create `frontend/src/components/debug/DebugPanel.tsx`
  - [ ] 1.2 Implement collapsible drawer (MUI Drawer component)
  - [ ] 1.3 Add keyboard shortcut listener (Ctrl+Shift+D)
  - [ ] 1.4 Store open/closed state in localStorage

- [ ] **Task 2: Capture WebSocket Messages** (AC: 2)
  - [ ] 2.1 Add message capture hook in `websocket.ts`
  - [ ] 2.2 Store last 50 messages in circular buffer
  - [ ] 2.3 Include: type, stream, timestamp, raw payload
  - [ ] 2.4 Create Zustand store slice for debug messages

- [ ] **Task 3: Message Display** (AC: 2, 3)
  - [ ] 3.1 Render messages in scrollable list
  - [ ] 3.2 Format JSON payload with syntax highlighting
  - [ ] 3.3 Show timestamp in human-readable format
  - [ ] 3.4 Color-code by message type

- [ ] **Task 4: Filtering** (AC: 3)
  - [ ] 4.1 Add filter chips for message types
  - [ ] 4.2 Implement filter logic
  - [ ] 4.3 Persist filter preferences in localStorage

- [ ] **Task 5: Dev-Only Guard** (AC: 5)
  - [ ] 5.1 Wrap panel in `process.env.NODE_ENV === 'development'` check
  - [ ] 5.2 Ensure no debug code in production bundle
  - [ ] 5.3 Add to app layout conditionally

## Dev Notes

### FR34 Requirement

From PRD: "FR34: Trader can access debug panel showing raw WebSocket messages (dev mode)"

### Design Reference

From UX Spec: Debug panel mentioned under "Journey 3: Handling Errors" - raw message viewer for troubleshooting.

### Message Types to Capture

From `websocket.ts:335-340`:
```typescript
const KNOWN_MESSAGE_TYPES = [
  'market_data',
  'indicators',
  'signal',
  'signals',
  'session_status',
  'session_update',
  // ... more
];
```

### Component Structure

```
DebugPanel/
├── DebugPanel.tsx        # Main drawer component
├── MessageList.tsx       # Scrollable message list
├── MessageItem.tsx       # Individual message display
├── FilterChips.tsx       # Type filter controls
└── debugStore.ts         # Zustand store for debug state
```

### Keyboard Shortcut Pattern

```typescript
// In Layout.tsx or app root
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'D') {
      e.preventDefault();
      toggleDebugPanel();
    }
  };
  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, []);
```

### Message Capture Hook

```typescript
// In websocket.ts handleMessage()
if (process.env.NODE_ENV === 'development') {
  useDebugStore.getState().addMessage({
    id: Date.now(),
    type: message.type,
    stream: message.stream,
    timestamp: new Date().toISOString(),
    payload: message
  });
}
```

### Styling

- Use MUI Drawer with `anchor="right"`
- Fixed width: 400px
- Dark theme for code display (matches DevTools)
- Monospace font for JSON

### References

- [Source: _bmad-output/prd.md#FR34: Debug panel]
- [Source: _bmad-output/ux-design-specification.md#Journey 3]
- [Source: frontend/src/services/websocket.ts:335-340]
- [Source: frontend/src/components/layout/Layout.tsx]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
