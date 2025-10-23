# Unified Status System

## Overview

The unified status system provides consistent status display and management across the entire application. It eliminates scattered status logic and ensures uniform user experience.

## Architecture

### Core Components

1. **`SystemStatusIndicator`** - Main status display component
2. **`StatusChip`** - Reusable status chip component
3. **`StatusAlert`** - Status alert component for detailed messages
4. **`CompactStatusDisplay`** - Compact status display for headers
5. **`statusUtils.ts`** - Centralized status utilities

### Status Types

```typescript
type SystemStatusType = 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
type WebSocketStatusType = 'connected' | 'disconnected' | 'connecting' | 'error';
type OverallStatusType = 'healthy' | 'warning' | 'error';
type SessionStatusType = 'running' | 'active' | 'stopped' | 'completed' | 'failed' | 'error';
```

## Usage Examples

### Basic Status Display

```tsx
import { SystemStatusIndicator } from '@/components/common/SystemStatusIndicator';

function MyComponent() {
  return (
    <div>
      <SystemStatusIndicator showDetails={true} />
    </div>
  );
}
```

### Status Chip

```tsx
import { StatusChip } from '@/components/common/SystemStatusIndicator';

function MyComponent() {
  return (
    <StatusChip
      status="healthy"
      type="overall"
      size="small"
      showIcon={true}
    />
  );
}
```

### Status Alert

```tsx
import { StatusAlert } from '@/components/common/SystemStatusIndicator';

function MyComponent() {
  return (
    <StatusAlert
      status="warning"
      title="System Warning"
      message="Some services are experiencing issues"
      showDetails={true}
      backendStatus="degraded"
      websocketStatus="connected"
    />
  );
}
```

### Compact Status Display

```tsx
import { CompactStatusDisplay } from '@/components/common/SystemStatusIndicator';

function MyComponent() {
  return (
    <CompactStatusDisplay
      backendStatus="healthy"
      websocketStatus="connected"
      showLabels={true}
    />
  );
}
```

### Status Utilities

```tsx
import {
  getOverallStatusColor,
  getWebSocketStatusIcon,
  getSessionStatusText,
  convertSessionStatusToOverall
} from '@/utils/statusUtils';

// Get status color
const color = getOverallStatusColor('healthy'); // 'success'

// Get status icon
const icon = getWebSocketStatusIcon('connected'); // <WifiIcon />

// Convert between status types
const overallStatus = convertSessionStatusToOverall('running'); // 'healthy'
```

## Status Color Scheme

### Overall Status
- **Healthy**: Green (`success`)
- **Warning**: Orange (`warning`)
- **Error**: Red (`error`)

### WebSocket Status
- **Connected**: Green (`success`)
- **Connecting**: Orange (`warning`)
- **Disconnected**: Orange (`warning`)
- **Error**: Red (`error`)

### Backend Status
- **Healthy**: Green (`success`)
- **Degraded**: Orange (`warning`)
- **Unhealthy**: Red (`error`)
- **Unknown**: Gray (`default`)

### Session Status
- **Running/Active**: Green (`success`)
- **Stopped/Completed**: Gray (`default`)
- **Failed/Error**: Red (`error`)

## Migration Guide

### Before (Scattered Logic)

```tsx
// Different status logic in each component
const getStatusColor = (status: string) => {
  switch (status) {
    case 'running': return 'success';
    case 'stopped': return 'default';
    case 'error': return 'error';
    // ... more cases
  }
};
```

### After (Unified System)

```tsx
// Import from centralized utilities
import { getSessionStatusColor } from '@/utils/statusUtils';

const color = getSessionStatusColor('running'); // 'success'
```

## Best Practices

1. **Always use the unified components** instead of creating custom status displays
2. **Import status utilities** from `@/utils/statusUtils` for consistent behavior
3. **Use appropriate status types** for different contexts (overall, websocket, backend, session)
4. **Leverage StatusChip** for inline status display
5. **Use StatusAlert** for important status notifications
6. **Consider CompactStatusDisplay** for header/toolbars

## Benefits

- ✅ **Consistency**: Uniform status display across the application
- ✅ **Maintainability**: Single source of truth for status logic
- ✅ **Reusability**: Components can be used anywhere
- ✅ **Type Safety**: TypeScript support for all status types
- ✅ **Extensibility**: Easy to add new status types and utilities
- ✅ **Performance**: Centralized logic reduces bundle size

## Testing

Status components include comprehensive TypeScript types and should be tested for:

- Correct color mapping for all status types
- Proper icon rendering
- Text display accuracy
- Responsive behavior
- Accessibility compliance

## Future Enhancements

- Status history and trends
- Status notifications and alerts
- Status-based routing and permissions
- Status analytics and reporting