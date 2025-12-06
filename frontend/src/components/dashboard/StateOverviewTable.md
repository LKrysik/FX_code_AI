# StateOverviewTable Component (SM-01)

## Overview

The `StateOverviewTable` component provides a real-time overview of all state machine instances across strategies and symbols. It displays the current state, duration since last state change, and allows users to view detailed information about each instance.

## Features

- **Real-time State Display**: Shows current state for each Strategy × Symbol combination
- **Auto-updating Duration**: Time since last state change updates every second
- **Priority Sorting**: Automatically sorts by state priority (POSITION_ACTIVE → SIGNAL_DETECTED → ERROR → MONITORING → EXITED → INACTIVE)
- **Visual Highlights**: Colored row backgrounds for critical states (POSITION_ACTIVE = red, SIGNAL_DETECTED = yellow)
- **Loading States**: Skeleton loading animation while data is being fetched
- **Empty State**: User-friendly message when no instances are active
- **Click Interaction**: Click row or "View" button to see instance details
- **Responsive Design**: Adapts to different screen sizes

## Props

```typescript
interface StateOverviewTableProps {
  sessionId: string;              // Current trading session ID
  instances: StateInstance[];     // Array of state machine instances
  onInstanceClick?: (instance: StateInstance) => void; // Optional click handler
  isLoading?: boolean;            // Show loading state
}

interface StateInstance {
  strategy_id: string;            // Strategy identifier (e.g., "pump_dump_v1")
  symbol: string;                 // Trading pair (e.g., "BTCUSDT")
  state: StateMachineState;       // Current state
  since: string | null;           // ISO timestamp of last state change
}

type StateMachineState =
  | 'INACTIVE'
  | 'MONITORING'
  | 'SIGNAL_DETECTED'
  | 'POSITION_ACTIVE'
  | 'EXITED'
  | 'ERROR';
```

## Usage

### Basic Usage

```tsx
import StateOverviewTable from '@/components/dashboard/StateOverviewTable';

function MyDashboard() {
  const [instances, setInstances] = useState<StateInstance[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  return (
    <StateOverviewTable
      sessionId="session-123"
      instances={instances}
      isLoading={isLoading}
    />
  );
}
```

### With Click Handler

```tsx
import StateOverviewTable, { StateInstance } from '@/components/dashboard/StateOverviewTable';

function MyDashboard() {
  const handleInstanceClick = (instance: StateInstance) => {
    console.log('Selected instance:', instance);
    // Navigate to detail view or open modal
  };

  return (
    <StateOverviewTable
      sessionId="session-123"
      instances={instances}
      onInstanceClick={handleInstanceClick}
    />
  );
}
```

### With WebSocket Updates

```tsx
import { useEffect, useState } from 'react';
import StateOverviewTable from '@/components/dashboard/StateOverviewTable';
import { useWebSocket } from '@/hooks/useWebSocket';

function LiveDashboard() {
  const [instances, setInstances] = useState<StateInstance[]>([]);
  const { data } = useWebSocket('/api/state-machines/live');

  useEffect(() => {
    if (data?.instances) {
      setInstances(data.instances);
    }
  }, [data]);

  return (
    <StateOverviewTable
      sessionId="session-123"
      instances={instances}
    />
  );
}
```

## State Priority & Sorting

Instances are automatically sorted by state priority:

1. **POSITION_ACTIVE** (Priority 1) - Active trades appear first with red background
2. **SIGNAL_DETECTED** (Priority 2) - Potential entries appear next with yellow background
3. **ERROR** (Priority 3) - Errors need attention
4. **MONITORING** (Priority 4) - Actively scanning
5. **EXITED** (Priority 5) - Recently closed positions
6. **INACTIVE** (Priority 6) - Not currently active

Within the same state priority, instances are sorted alphabetically by:
- Strategy ID (primary)
- Symbol (secondary)

## Visual Highlights

### Row Background Colors

- **POSITION_ACTIVE**: Light red background (`alpha(error.main, 0.08)`)
- **SIGNAL_DETECTED**: Light yellow background (`alpha(warning.main, 0.08)`)
- **Other states**: Transparent background

### Hover Effects

All rows have hover effect:
- Transparent rows: Standard MUI hover color
- Colored rows: Enhanced color on hover (1.5x alpha)

## Time Display

The "Since" column shows elapsed time in human-readable format:

- `< 1 minute`: "30s"
- `1-60 minutes`: "5m 23s"
- `1-24 hours`: "2h 15m"
- `> 24 hours`: "3d 12h"
- `No timestamp`: "N/A"

Time updates automatically every second for each instance.

## Empty State

When no instances are available (`instances.length === 0`), the table displays:

```
No active instances
State machines will appear here when strategies are running
```

## Loading State

When `isLoading={true}` and no instances exist, the table shows a skeleton loading animation with 5 placeholder rows.

When `isLoading={true}` and instances exist, a small loading spinner appears in the footer.

## Responsive Design

The table is fully responsive:

- **Desktop**: Full table with all columns
- **Tablet**: Optimized column widths
- **Mobile**: Horizontal scroll enabled via MUI TableContainer

## Integration with Backend

### Expected API Response Format

```typescript
// GET /api/state-machines?session_id=123
{
  "data": {
    "instances": [
      {
        "strategy_id": "pump_dump_v1",
        "symbol": "BTCUSDT",
        "state": "POSITION_ACTIVE",
        "since": "2025-12-06T10:30:00Z"
      },
      // ... more instances
    ]
  }
}
```

### WebSocket Event Format

```typescript
// Event: "state_change"
{
  "strategy_id": "pump_dump_v1",
  "symbol": "BTCUSDT",
  "state": "SIGNAL_DETECTED",
  "since": "2025-12-06T10:35:23Z",
  "previous_state": "MONITORING"
}
```

## Testing

### Run Tests

```bash
npm test -- StateOverviewTable.test.tsx
```

### Test Coverage

- Basic rendering (table headers, session ID)
- State sorting and priority
- Empty state handling
- Loading state handling
- Click event handlers
- Time display formatting
- Background color application
- Footer count display

## Example Implementation

See `StateOverviewTable.example.tsx` for a complete working example with:
- Mock data generation
- Click handlers
- Loading simulation
- State management

## Related Components

- **StateBadge**: Used to display state chips with icons and colors
- **SignalHistoryPanel**: Shows historical signals
- **TransactionHistoryPanel**: Shows trade history

## Performance Considerations

- **Time Updates**: Each instance has its own interval for time updates. With 100+ instances, consider throttling updates.
- **Re-rendering**: Component uses `useMemo` for sorted instances to minimize re-renders.
- **Large Datasets**: For >500 instances, consider adding pagination or virtualization.

## Accessibility

- Semantic HTML table structure
- Proper ARIA labels on interactive elements
- Keyboard navigation support via MUI components
- Screen reader friendly time displays

## Browser Support

Tested and working on:
- Chrome 120+
- Firefox 120+
- Safari 17+
- Edge 120+

## Changelog

### Version 1.0.0 (2025-12-06)
- Initial implementation
- Support for all 6 state machine states
- Real-time time display
- Priority sorting
- Visual highlights for critical states
