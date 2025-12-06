# TransitionLog Component

## Overview

`TransitionLog` displays the history of state machine transitions in a tabular format with expandable details. It shows when and how the trading system moved between different states, along with the conditions that triggered each transition.

## Features

- **Chronological Display**: Newest transitions at the top
- **Color-Coded Rows**: Visual indicators for different transition types
  - Green: Entry to POSITION_ACTIVE (successful trade entry)
  - Red: Exit with E1 trigger (emergency exit)
  - Blue: Exit with ZE1 trigger (normal close)
- **Expandable Details**: Click any row to see full timestamp, strategy ID, and trigger conditions
- **Loading States**: Skeleton loaders while data is loading
- **Empty State**: User-friendly message when no transitions exist
- **Auto-Scroll**: Automatically scrolls to top when new transitions arrive
- **Performance**: Limits display to configurable max items (default 50)

## Usage

### Basic Example

```tsx
import { TransitionLog } from '@/components/dashboard';
import type { Transition } from '@/components/dashboard';

function Dashboard() {
  const [transitions, setTransitions] = useState<Transition[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  return (
    <div style={{ height: '600px' }}>
      <TransitionLog
        transitions={transitions}
        isLoading={isLoading}
      />
    </div>
  );
}
```

### With Callback

```tsx
import { TransitionLog } from '@/components/dashboard';
import type { Transition } from '@/components/dashboard';

function Dashboard() {
  const handleTransitionClick = (transition: Transition) => {
    console.log('Selected transition:', transition);
    // Navigate to detail view, show modal, etc.
  };

  return (
    <TransitionLog
      transitions={transitions}
      onTransitionClick={handleTransitionClick}
      maxItems={100}
    />
  );
}
```

## Props

### `TransitionLogProps`

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `transitions` | `Transition[]` | **required** | Array of transition objects to display |
| `maxItems` | `number` | `50` | Maximum number of transitions to display |
| `onTransitionClick` | `(transition: Transition) => void` | `undefined` | Callback fired when a transition row is clicked |
| `isLoading` | `boolean` | `false` | Shows loading skeleton when true |

## Types

### `Transition`

```typescript
interface Transition {
  timestamp: string;        // ISO 8601 format
  strategy_id: string;      // ID of the strategy that generated transition
  symbol: string;           // Trading pair (e.g., "BTC/USDT")
  from_state: string;       // State before transition
  to_state: string;         // State after transition
  trigger: 'S1' | 'O1' | 'Z1' | 'ZE1' | 'E1' | 'MANUAL';
  conditions: Record<string, TransitionCondition>;
}
```

### `TransitionCondition`

```typescript
interface TransitionCondition {
  indicator_name: string;   // Human-readable name
  value: number;            // Current value
  threshold: number;        // Threshold value
  operator: string;         // Comparison operator (>, <, >=, <=, ==)
  met: boolean;             // Whether condition was met
}
```

## Trigger Types

| Trigger | Color | Description |
|---------|-------|-------------|
| `S1` | Warning (Orange) | Signal detected |
| `O1` | Success (Green) | Position opened |
| `Z1` | Info (Blue) | Position closed normally |
| `ZE1` | Primary (Blue) | Position closed with profit target |
| `E1` | Error (Red) | Emergency exit (stop loss) |
| `MANUAL` | Secondary (Grey) | Manual intervention |

## State Machine States

The component displays states using the `StateBadge` component:

- `INACTIVE` - System not monitoring
- `MONITORING` - Actively scanning for signals
- `SIGNAL_DETECTED` - Signal found, evaluating entry
- `POSITION_ACTIVE` - Position open
- `EXITED` - Position closed
- `ERROR` - System error

## Styling

The component uses MUI's theming system and is fully responsive. Key styling features:

- **Row Colors**: Automatically applied based on transition type
- **Hover Effects**: Enhanced row highlighting on hover
- **Expand Indicator**: Blue left border when row is expanded
- **Condition Badges**: Color-coded green (met) or red (not met)

## Integration with WebSocket

```tsx
import { useEffect, useState } from 'react';
import { TransitionLog } from '@/components/dashboard';
import type { Transition } from '@/components/dashboard';

function LiveTransitionLog() {
  const [transitions, setTransitions] = useState<Transition[]>([]);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/transitions');

    ws.onmessage = (event) => {
      const newTransition: Transition = JSON.parse(event.data);
      setTransitions(prev => [newTransition, ...prev]);
    };

    return () => ws.close();
  }, []);

  return (
    <TransitionLog
      transitions={transitions}
      maxItems={100}
    />
  );
}
```

## Performance Considerations

1. **Virtualization**: For lists > 100 items, consider implementing virtual scrolling
2. **Max Items**: Use the `maxItems` prop to limit memory usage
3. **Memoization**: Wrap callback functions with `useCallback` to prevent re-renders

```tsx
const handleClick = useCallback((transition: Transition) => {
  // Handle click
}, []);

<TransitionLog
  transitions={transitions}
  onTransitionClick={handleClick}
/>
```

## Accessibility

- Semantic HTML table structure
- Keyboard navigation support
- Screen reader friendly labels
- ARIA attributes for expand/collapse

## Testing

See `__tests__/TransitionLog.test.tsx` for comprehensive test examples.

```bash
npm test -- TransitionLog.test.tsx
```

## File Location

```
frontend/src/components/dashboard/
├── TransitionLog.tsx           # Main component
├── TransitionLog.example.tsx   # Example usage
├── TransitionLog.README.md     # This file
└── __tests__/
    └── TransitionLog.test.tsx  # Unit tests
```

## Dependencies

- `@mui/material` - UI components
- `@mui/icons-material` - Icons
- `./StateBadge` - State display component
- React 18+

## Related Components

- `StateBadge` - Displays individual state with styling
- `StateOverviewTable` - Overview of all active strategies
- `StateTransitionDiagram` - Visual state machine flow

## Future Enhancements

- [ ] Virtual scrolling for large datasets
- [ ] Export to CSV functionality
- [ ] Filter by symbol/trigger/state
- [ ] Search functionality
- [ ] Column sorting
- [ ] Customizable columns
