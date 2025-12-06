# ConditionProgress Component - Quick Reference

## What is this?

A React component that displays trading condition states across state machine sections (S1, O1, Z1, ZE1, E1). Shows which conditions are met (✅) and which are pending (❌) with visual progress bars.

## Quick Start (1 minute)

```tsx
import ConditionProgressIntegration from '@/components/dashboard/ConditionProgress.integration';

function MyDashboard() {
  return (
    <ConditionProgressIntegration
      sessionId="session-123"
      symbol="BTCUSDT"
    />
  );
}
```

Done! The component handles API calls and WebSocket updates automatically.

## Files

```
dashboard/
├── ConditionProgress.tsx              ← Main component (use this if you have data)
├── ConditionProgress.integration.tsx  ← Use this for auto-fetch from API
├── ConditionProgress.example.tsx      ← Demo with mock data
├── ConditionProgress.api.md           ← Full API docs
└── __tests__/
    └── ConditionProgress.test.tsx     ← Unit tests
```

## When to use which file?

| File | Use Case |
|------|----------|
| **ConditionProgress.tsx** | You already have condition data from API/props |
| **ConditionProgress.integration.tsx** | You want auto-fetching + WebSocket updates (recommended) |
| **ConditionProgress.example.tsx** | Testing/demo with mock data |

## Props

### ConditionProgress (base component)

```typescript
<ConditionProgress
  groups={[...]}           // Array of condition groups
  currentState="SIGNAL_DETECTED"  // Current state machine state
  isLoading={false}        // Show skeleton loader
/>
```

### ConditionProgressIntegration (recommended)

```typescript
<ConditionProgressIntegration
  sessionId="session-123"  // Trading session ID
  symbol="BTCUSDT"        // Symbol to monitor
  refreshInterval={5000}  // Polling fallback interval (ms)
/>
```

## Data Format

```typescript
// What the component expects
groups: [
  {
    section: 'S1',                    // S1 | O1 | Z1 | ZE1 | E1
    label: 'Pump Detection',
    logic: 'AND',                     // AND | OR
    all_met: true,
    conditions: [
      {
        indicator_name: 'PUMP_MAGNITUDE_PCT',
        operator: '>',                // > | < | >= | <= | == | !=
        threshold: 5.0,
        current_value: 7.2,
        met: true
      }
    ]
  }
]
```

## Section Colors

| Section | Color | Purpose |
|---------|-------|---------|
| S1 | 🟠 Orange | Pump Detection |
| O1 | ⚫ Gray | Cancel Signal |
| Z1 | 🟢 Green | Peak Entry |
| ZE1 | 🔵 Blue | Dump End Close |
| E1 | 🔴 Red | Emergency Exit |

## Backend Integration

### REST API

```bash
GET /api/conditions/status?session_id={id}&symbol={symbol}
```

Response:
```json
{
  "success": true,
  "data": {
    "state": "SIGNAL_DETECTED",
    "groups": [...]
  }
}
```

### WebSocket

```javascript
// Connect
const ws = new WebSocket('ws://localhost:8080/ws');

// Subscribe
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'conditions',
  session_id: 'session-123',
  symbol: 'BTCUSDT'
}));

// Receive updates
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'condition_update') {
    // Component auto-updates via integration wrapper
  }
};
```

## Common Use Cases

### 1. Add to existing dashboard

```tsx
import { Grid } from '@mui/material';
import ConditionProgressIntegration from '@/components/dashboard/ConditionProgress.integration';

<Grid container spacing={2}>
  <Grid item xs={12} md={6}>
    <ConditionProgressIntegration
      sessionId={activeSession}
      symbol={currentSymbol}
    />
  </Grid>
</Grid>
```

### 2. Standalone page

```tsx
// app/conditions/page.tsx
'use client';

import ConditionProgressIntegration from '@/components/dashboard/ConditionProgress.integration';

export default function ConditionsPage() {
  return (
    <Container maxWidth="lg">
      <ConditionProgressIntegration
        sessionId="session-123"
        symbol="BTCUSDT"
      />
    </Container>
  );
}
```

### 3. With custom data source

```tsx
import ConditionProgress, { ConditionGroup } from '@/components/dashboard/ConditionProgress';
import { useState, useEffect } from 'react';

function CustomDataSource() {
  const [groups, setGroups] = useState<ConditionGroup[]>([]);
  const [state, setState] = useState('MONITORING');

  useEffect(() => {
    // Your custom data fetching logic
    fetchMyData().then(data => {
      setGroups(data.groups);
      setState(data.state);
    });
  }, []);

  return (
    <ConditionProgress
      groups={groups}
      currentState={state}
    />
  );
}
```

## Styling

The component uses Material-UI theme. Wrap in custom container for sizing:

```tsx
<Box sx={{ maxWidth: 800, margin: 'auto' }}>
  <ConditionProgressIntegration {...props} />
</Box>
```

## Troubleshooting

### Component shows "No conditions configured"
- Check `sessionId` is valid
- Verify API endpoint returns data: `GET /api/conditions/status?session_id=...`
- Check browser console for errors

### Data doesn't update in real-time
- Verify WebSocket connection: check browser DevTools → Network → WS
- Check `NEXT_PUBLIC_WS_URL` environment variable
- Fallback to polling: set `refreshInterval={3000}` (3 seconds)

### Build errors
- Ensure Material-UI is installed: `npm list @mui/material`
- Check TypeScript version: `npx tsc --version` (should be ≥4.x)

### Loading spinner never disappears
- Check API response format matches expected structure
- Verify `sessionId` prop is not null/undefined
- Check network tab for failed requests

## Testing

```bash
# Run unit tests
npm test -- ConditionProgress.test.tsx

# Run example in dev mode
npm run dev
# Visit: http://localhost:3000/conditions (if example page created)

# Build check
npm run build
```

## Performance Tips

1. **Large datasets**: Component handles 50+ conditions smoothly (scrollable container)
2. **Update frequency**: Default 5s polling + instant WebSocket updates
3. **Optimize re-renders**: Use React.memo if parent re-renders frequently

```tsx
import React from 'react';
const MemoizedConditionProgress = React.memo(ConditionProgressIntegration);
```

## Accessibility

- ✅ Keyboard navigation (Tab through accordions)
- ✅ Screen reader friendly (ARIA labels)
- ✅ Color + icon indicators (not color-only)
- ✅ Tooltips on hover/focus

## Related Components

- **StateBadge** - State machine status indicator
- **LiveIndicatorPanel** - Real-time indicator monitoring
- **SignalDetailPanel** - Signal details view

## Support

- Full docs: `ConditionProgress.api.md`
- Tests: `__tests__/ConditionProgress.test.tsx`
- Example: `ConditionProgress.example.tsx`

## Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8080/ws
```

## Version

- **v1.0.0** (2025-12-06): Initial release
- Next.js 14 compatible
- React 18 compatible
- Material-UI v5 compatible

---

**Need help?** Check `ConditionProgress.api.md` for detailed documentation.
