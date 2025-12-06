# ConditionProgress API Documentation

## Overview

`ConditionProgress` is a React component that visualizes the state of trading conditions across different sections of the state machine (S1, O1, Z1, ZE1, E1). It shows which conditions are met and which are pending, with progress bars and color-coded indicators.

## Location

```
frontend/src/components/dashboard/ConditionProgress.tsx
```

## Props

### `ConditionProgressProps`

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `groups` | `ConditionGroup[]` | Yes | - | Array of condition groups to display |
| `currentState` | `string` | Yes | - | Current state machine state (e.g., "MONITORING", "SIGNAL_DETECTED") |
| `isLoading` | `boolean` | No | `false` | Shows loading skeleton when true |

## Types

### `Condition`

Represents a single condition that must be evaluated.

```typescript
interface Condition {
  indicator_name: string;  // e.g., "PUMP_MAGNITUDE_PCT"
  operator: '>' | '<' | '>=' | '<=' | '==' | '!=';
  threshold: number;       // Threshold value to compare against
  current_value: number;   // Current indicator value
  met: boolean;           // Whether condition is satisfied
}
```

### `ConditionGroup`

Represents a group of conditions for a specific section.

```typescript
interface ConditionGroup {
  section: 'S1' | 'O1' | 'Z1' | 'ZE1' | 'E1';
  label: string;          // e.g., "Pump Detection", "Peak Entry"
  logic: 'AND' | 'OR';   // How conditions are combined
  conditions: Condition[];
  all_met: boolean;      // Whether all conditions (AND) or any (OR) are met
}
```

## Section Configuration

Each section has predefined colors and associated states:

| Section | Color | Label | Associated States |
|---------|-------|-------|-------------------|
| **S1** | Orange (#ff9800) | Pump Detection | MONITORING, SIGNAL_DETECTED |
| **O1** | Gray (#9e9e9e) | Cancel Signal | SIGNAL_DETECTED |
| **Z1** | Green (#4caf50) | Peak Entry | SIGNAL_DETECTED, POSITION_ACTIVE |
| **ZE1** | Blue (#2196f3) | Dump End Close | POSITION_ACTIVE, EXITED |
| **E1** | Red (#f44336) | Emergency Exit | POSITION_ACTIVE, ERROR |

## Features

### Visual Indicators

1. **Section Status**
   - Checkmark icon (✅): All conditions met (`all_met: true`)
   - X icon (❌): Some conditions not met (`all_met: false`)
   - Badge showing met/total count (e.g., "2/3")

2. **Active Section Highlighting**
   - Sections matching `currentState` are highlighted with:
     - Glowing border
     - "ACTIVE" badge with pulsing animation
     - Auto-expanded by default

3. **Condition Progress Bars**
   - Green bar: Condition met
   - Section-colored bar: Condition not met but progressing
   - Shows percentage of current_value vs threshold

4. **Loading State**
   - Skeleton loaders for async data fetching

5. **Empty State**
   - Info alert when no conditions configured

## Usage Examples

### Basic Usage

```tsx
import ConditionProgress from '@/components/dashboard/ConditionProgress';

const MyComponent = () => {
  const groups = [
    {
      section: 'S1',
      label: 'Pump Detection',
      logic: 'AND',
      all_met: true,
      conditions: [
        {
          indicator_name: 'PUMP_MAGNITUDE_PCT',
          operator: '>',
          threshold: 5.0,
          current_value: 7.2,
          met: true,
        }
      ]
    }
  ];

  return (
    <ConditionProgress
      groups={groups}
      currentState="SIGNAL_DETECTED"
      isLoading={false}
    />
  );
};
```

### With API Integration

```tsx
import { useState, useEffect } from 'react';
import ConditionProgress, { ConditionGroup } from '@/components/dashboard/ConditionProgress';

const Dashboard = () => {
  const [groups, setGroups] = useState<ConditionGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentState, setCurrentState] = useState('MONITORING');

  useEffect(() => {
    const fetchConditions = async () => {
      const response = await fetch('/api/conditions/status');
      const data = await response.json();
      setGroups(data.groups);
      setCurrentState(data.state);
      setLoading(false);
    };

    fetchConditions();
  }, []);

  return (
    <ConditionProgress
      groups={groups}
      currentState={currentState}
      isLoading={loading}
    />
  );
};
```

### With WebSocket Real-Time Updates

```tsx
import { useState, useEffect } from 'react';
import ConditionProgress, { ConditionGroup } from '@/components/dashboard/ConditionProgress';

const RealTimeDashboard = () => {
  const [groups, setGroups] = useState<ConditionGroup[]>([]);
  const [currentState, setCurrentState] = useState('MONITORING');

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8080/ws');

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === 'condition_update') {
        setGroups(message.groups);
        setCurrentState(message.state);
      }
    };

    return () => ws.close();
  }, []);

  return (
    <ConditionProgress
      groups={groups}
      currentState={currentState}
    />
  );
};
```

## API Response Format

Expected backend response structure:

```json
{
  "state": "SIGNAL_DETECTED",
  "groups": [
    {
      "section": "S1",
      "label": "Pump Detection",
      "logic": "AND",
      "all_met": true,
      "conditions": [
        {
          "indicator_name": "PUMP_MAGNITUDE_PCT",
          "operator": ">",
          "threshold": 5.0,
          "current_value": 7.2,
          "met": true
        }
      ]
    }
  ]
}
```

## Styling & Customization

The component uses Material-UI theming and can be customized via `sx` prop if wrapped:

```tsx
<Box sx={{ maxWidth: 800 }}>
  <ConditionProgress {...props} />
</Box>
```

## Performance Considerations

1. **Rendering Optimization**
   - Uses React.memo for condition rows (if needed)
   - Efficient re-renders only when `groups` or `currentState` change

2. **Large Datasets**
   - Built-in scroll container for many conditions
   - Max height: 700px with overflow scroll

3. **Loading States**
   - Skeleton loaders prevent layout shift
   - Smooth transitions between loading/loaded states

## Accessibility

- All interactive elements have ARIA labels
- Color indicators supplemented with icons (not color-only)
- Tooltips provide additional context on hover
- Keyboard navigation supported via MUI Accordion

## Related Components

- `StateBadge.tsx` - State machine state indicator
- `LiveIndicatorPanel.tsx` - Real-time indicator monitoring
- `SignalDetailPanel.tsx` - Signal details display

## Backend Endpoints

Suggested API endpoints:

```
GET /api/conditions/status?session_id={id}
  - Returns current condition groups and state

WebSocket: /ws
  - Subscribe to: "condition_update" events
  - Payload: { type: "condition_update", groups: [...], state: "..." }
```

## Testing

See `ConditionProgress.example.tsx` for integration example with mock data.

## Changelog

- **v1.0.0** (2025-12-06): Initial implementation (SM-03)
  - Accordion-based section display
  - Progress bars for numeric thresholds
  - Active section highlighting
  - Loading states
  - Color-coded sections
