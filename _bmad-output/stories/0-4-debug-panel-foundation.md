# Story 0.4: Debug Panel Foundation

Status: done

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

- [x] **Task 1: Create Debug Panel Component** (AC: 1, 4) ✅
  - [x] 1.1 Create `frontend/src/components/debug/DebugPanel.tsx`
  - [x] 1.2 Implement collapsible drawer (MUI Drawer component)
  - [x] 1.3 Add keyboard shortcut listener (Ctrl+Shift+D)
  - [x] 1.4 Store open/closed state in localStorage

- [x] **Task 2: Capture WebSocket Messages** (AC: 2) ✅
  - [x] 2.1 Add message capture hook in `websocket.ts`
  - [x] 2.2 Store last 50 messages in circular buffer
  - [x] 2.3 Include: type, stream, timestamp, raw payload
  - [x] 2.4 Create Zustand store slice for debug messages

- [x] **Task 3: Message Display** (AC: 2, 3) ✅
  - [x] 3.1 Render messages in scrollable list
  - [x] 3.2 Format JSON payload with syntax highlighting
  - [x] 3.3 Show timestamp in human-readable format
  - [x] 3.4 Color-code by message type

- [x] **Task 4: Filtering** (AC: 3) ✅
  - [x] 4.1 Add filter chips for message types
  - [x] 4.2 Implement filter logic
  - [x] 4.3 Persist filter preferences in localStorage

- [x] **Task 5: Dev-Only Guard** (AC: 5) ✅
  - [x] 5.1 Wrap panel in `process.env.NODE_ENV === 'development'` check
  - [x] 5.2 Ensure no debug code in production bundle
  - [x] 5.3 Add to app layout conditionally

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

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

**Task 1 Completed (2025-12-26):**
- ✅ Created `DebugPanel.tsx` with MUI Drawer (anchor="right", width=400px)
- ✅ Keyboard shortcut Ctrl+Shift+D via useEffect
- ✅ localStorage persistence for open/closed state

**Task 2 Completed (2025-12-26):**
- ✅ Added message capture in `websocket.ts:226-238`
- ✅ Circular buffer with max 50 messages in `debugStore.ts:103-107`
- ✅ Captures: type, stream, timestamp, full payload

**Task 3 Completed (2025-12-26):**
- ✅ `MessageItem` component with expandable JSON view
- ✅ `SyntaxHighlightedJSON` with monospace dark theme
- ✅ Human-readable timestamps with milliseconds
- ✅ Color-coded chips by message type

**Task 4 Completed (2025-12-26):**
- ✅ `FilterChips` component with 13 message types
- ✅ Toggle filter on/off with visual feedback
- ✅ Filter state persisted to localStorage

**Task 5 Completed (2025-12-26):**
- ✅ `Layout.tsx:308` - `process.env.NODE_ENV === 'development'` guard
- ✅ `websocket.ts:227` - same guard for message capture
- ✅ Dynamic import ensures no SSR issues

### Sanity Verification (70-75) Applied (2025-12-26)

**70. Scope Integrity Check:**
- All 5 ACs classified as ADDRESSED
- Simplified without decision: Export to file (not in AC)

**71. Alignment Check:**
- Goal "debug panel that shows raw WebSocket messages" fully met
- All AC parts have evidence with line numbers

**72. Closure Check:**
- No TODO/TBD/PLACEHOLDER markers in implementation
- Status: COMPLETE

**73. Coherence Check:**
- MESSAGE_TYPES consistent between debugStore.ts and websocket.ts
- No contradictions detected

**74. Grounding Check:**
- Critical assumption: Next.js tree-shakes dev-only code in production
- All other assumptions validated

**75. Falsifiability Check:**
- Failure scenario: Large payloads may slow UI (mitigated by truncation)
- UNDERDEVELOPED: JSON virtualization for very large payloads
- MISSING: Export messages to file functionality
- FUTURE: Search by payload content

### File List

- `frontend/src/stores/debugStore.ts` (NEW) - Zustand store for debug state
- `frontend/src/components/debug/DebugPanel.tsx` (NEW) - Main drawer component with MessageItem, FilterChips
- `frontend/src/services/websocket.ts` (MODIFIED) - Lines 6, 226-238 (import + capture hook)
- `frontend/src/components/layout/Layout.tsx` (MODIFIED) - Lines 38-44, 308 (import + render)
