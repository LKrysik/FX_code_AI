# Story 0.6: Connection Status Indicator

Status: ready-for-dev

## Story

As a **trader**,
I want **to always see the WebSocket connection status (green/yellow/red)**,
so that **I know if the system is receiving real-time data and can trust the displayed information**.

## Acceptance Criteria

1. **AC1:** Connection indicator is always visible in header/navbar
2. **AC2:** Green = connected, Yellow = reconnecting, Red = disconnected
3. **AC3:** Clicking indicator shows connection details (latency, last message time)
4. **AC4:** Status updates within 2 seconds of actual connection change
5. **AC5:** Indicator shows "disabled" state when WebSocket is intentionally off

## Tasks / Subtasks

- [ ] **Task 1: Create Status Indicator Component** (AC: 1, 2)
  - [ ] 1.1 Create `frontend/src/components/common/ConnectionStatusIndicator.tsx`
  - [ ] 1.2 Use MUI Chip or Badge with color coding
  - [ ] 1.3 Add pulsing animation for "reconnecting" state
  - [ ] 1.4 Show icon + text label

- [ ] **Task 2: Integrate with WebSocket Store** (AC: 2, 4)
  - [ ] 2.1 Connect to `useWebSocketStore` for connection state
  - [ ] 2.2 Map store states to indicator colors
  - [ ] 2.3 Ensure real-time updates (no stale state)

- [ ] **Task 3: Connection Details Popover** (AC: 3)
  - [ ] 3.1 Add click handler to open popover
  - [ ] 3.2 Display: status, latency, last message timestamp
  - [ ] 3.3 Add manual reconnect button
  - [ ] 3.4 Show connection URL (masked for security)

- [ ] **Task 4: Add to Layout** (AC: 1)
  - [ ] 4.1 Place indicator in header/navbar (right side)
  - [ ] 4.2 Ensure visibility on all pages
  - [ ] 4.3 Test responsive behavior

- [ ] **Task 5: Handle Edge Cases** (AC: 5)
  - [ ] 5.1 Show "Disabled" when WS intentionally off
  - [ ] 5.2 Handle initial loading state
  - [ ] 5.3 Handle backend-down scenario

## Dev Notes

### FR24 Requirement

From PRD: "FR24: Trader can view connection status (WebSocket health)"

### NFR22 Requirement

From PRD: "NFR22: System must track and display connection status"

### UX Design Reference

From UX Spec: "Connection status always visible during active sessions"

### WebSocket Store States

From `websocketStore.ts`:
```typescript
interface WebSocketState {
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error' | 'disabled';
  lastError: string | null;
  // ...
}
```

### Color Mapping

| Store Status | Color | Icon | Label |
|--------------|-------|------|-------|
| connected | Green (#10B981) | ● | Connected |
| connecting | Yellow (#F59E0B) | ○ (pulse) | Connecting... |
| disconnected | Red (#EF4444) | ● | Disconnected |
| error | Red (#EF4444) | ⚠ | Error |
| disabled | Gray (#6B7280) | ○ | Disabled |

### Component Design

```typescript
// ConnectionStatusIndicator.tsx
export function ConnectionStatusIndicator() {
  const { isConnected, connectionStatus } = useWebSocketStore();

  const color = getStatusColor(connectionStatus);
  const label = getStatusLabel(connectionStatus);

  return (
    <Chip
      icon={<FiberManualRecordIcon sx={{ color }} />}
      label={label}
      onClick={openDetailsPopover}
      variant="outlined"
      size="small"
    />
  );
}
```

### Popover Content

```typescript
<Popover>
  <Box p={2}>
    <Typography variant="subtitle2">Connection Status</Typography>
    <Divider />
    <List dense>
      <ListItem>Status: {connectionStatus}</ListItem>
      <ListItem>Latency: {latency}ms</ListItem>
      <ListItem>Last Message: {lastMessageTime}</ListItem>
      <ListItem>URL: ws://***</ListItem>
    </List>
    <Button onClick={reconnect} disabled={isConnected}>
      Reconnect
    </Button>
  </Box>
</Popover>
```

### Existing Component

There's already a `SystemStatusIndicator.tsx` - verify if it can be reused or extended:
```
frontend/src/components/common/SystemStatusIndicator.tsx
```

### References

- [Source: _bmad-output/prd.md#FR24: Connection status]
- [Source: _bmad-output/prd.md#NFR22: Track connection status]
- [Source: frontend/src/stores/websocketStore.ts]
- [Source: frontend/src/components/common/SystemStatusIndicator.tsx]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
