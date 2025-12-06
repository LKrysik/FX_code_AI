# StateBadge - Quick Code Snippets

## Import

```typescript
import StateBadge from '@/components/dashboard/StateBadge';
import type { StateMachineState, StateBadgeProps } from '@/components/dashboard/StateBadge';
```

## Basic Usage

```typescript
// Minimal
<StateBadge state="MONITORING" />

// With duration
<StateBadge
  state="POSITION_ACTIVE"
  since="2025-12-06T10:30:00Z"
  showDuration
/>

// Custom size
<StateBadge state="SIGNAL_DETECTED" size="large" />
```

## Dashboard Header

```typescript
function DashboardHeader() {
  const [systemState, setSystemState] = useState<StateMachineState>('MONITORING');
  const [since, setSince] = useState(new Date().toISOString());

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
      <Typography variant="h5">System Status:</Typography>
      <StateBadge state={systemState} since={since} showDuration size="large" />
    </Box>
  );
}
```

## Position Card

```typescript
function PositionCard({ position }: { position: Position }) {
  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6">{position.symbol}</Typography>
          <StateBadge
            state={position.state}
            since={position.entryTime}
            showDuration
            size="small"
          />
        </Box>
        {/* Rest of card content */}
      </CardContent>
    </Card>
  );
}
```

## Table Row

```typescript
function PositionTableRow({ position }: { position: Position }) {
  return (
    <TableRow>
      <TableCell>{position.symbol}</TableCell>
      <TableCell>
        <StateBadge
          state={position.state}
          since={position.entryTime}
          showDuration
          size="small"
        />
      </TableCell>
      <TableCell align="right">${position.currentPrice}</TableCell>
      <TableCell align="right">{position.pnl}</TableCell>
    </TableRow>
  );
}
```

## WebSocket Integration

```typescript
function TradingDashboard() {
  const [state, setState] = useState<StateMachineState>('INACTIVE');
  const [since, setSince] = useState<string>(new Date().toISOString());

  useEffect(() => {
    const socket = io('http://localhost:8000');

    socket.on('state_change', (data: { state: StateMachineState; timestamp: string }) => {
      setState(data.state);
      setSince(data.timestamp);
    });

    return () => socket.disconnect();
  }, []);

  return <StateBadge state={state} since={since} showDuration />;
}
```

## Zustand State Management

```typescript
// Store
interface TradingStore {
  systemState: StateMachineState;
  systemStateChangedAt: string;
  setSystemState: (state: StateMachineState) => void;
}

const useTradingStore = create<TradingStore>((set) => ({
  systemState: 'INACTIVE',
  systemStateChangedAt: new Date().toISOString(),
  setSystemState: (state) =>
    set({
      systemState: state,
      systemStateChangedAt: new Date().toISOString()
    })
}));

// Component
function SystemStatus() {
  const systemState = useTradingStore((state) => state.systemState);
  const since = useTradingStore((state) => state.systemStateChangedAt);

  return <StateBadge state={systemState} since={since} showDuration />;
}
```

## All States Example

```typescript
function AllStatesDemo() {
  const states: StateMachineState[] = [
    'INACTIVE',
    'MONITORING',
    'SIGNAL_DETECTED',
    'POSITION_ACTIVE',
    'EXITED',
    'ERROR'
  ];

  return (
    <Stack direction="row" spacing={2}>
      {states.map((state) => (
        <StateBadge key={state} state={state} />
      ))}
    </Stack>
  );
}
```

## Conditional Rendering

```typescript
function ConditionalBadge({ position }: { position: Position }) {
  if (!position.state) return null;

  const shouldShowDuration = ['POSITION_ACTIVE', 'SIGNAL_DETECTED'].includes(position.state);

  return (
    <StateBadge
      state={position.state}
      since={position.stateChangedAt}
      showDuration={shouldShowDuration}
      size="small"
    />
  );
}
```

## Alert/Notification

```typescript
function AlertBanner() {
  const [state, setState] = useState<StateMachineState>('ERROR');

  if (state !== 'ERROR') return null;

  return (
    <Alert
      severity="error"
      icon={false}
      sx={{ display: 'flex', alignItems: 'center', gap: 2 }}
    >
      <StateBadge state={state} size="small" />
      <Typography>System error detected - check logs</Typography>
    </Alert>
  );
}
```

## Grid Layout

```typescript
function StrategyGrid({ strategies }: { strategies: Strategy[] }) {
  return (
    <Grid container spacing={3}>
      {strategies.map((strategy) => (
        <Grid item xs={12} md={4} key={strategy.id}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6">{strategy.name}</Typography>
                <StateBadge
                  state={strategy.state}
                  since={strategy.lastUpdate}
                  showDuration
                  size="small"
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}
```

## Custom Hook

```typescript
function useSystemState() {
  const [state, setState] = useState<StateMachineState>('INACTIVE');
  const [since, setSince] = useState<string>(new Date().toISOString());

  useEffect(() => {
    // WebSocket or API polling
    const socket = io('http://localhost:8000');

    socket.on('state_change', (data) => {
      setState(data.state);
      setSince(data.timestamp);
    });

    return () => socket.disconnect();
  }, []);

  return { state, since };
}

// Usage
function SystemBadge() {
  const { state, since } = useSystemState();
  return <StateBadge state={state} since={since} showDuration />;
}
```

## Multi-Symbol Monitor

```typescript
function MultiSymbolMonitor() {
  const [symbols, setSymbols] = useState<{
    symbol: string;
    state: StateMachineState;
    since: string;
  }[]>([
    { symbol: 'BTC/USDT', state: 'POSITION_ACTIVE', since: new Date().toISOString() },
    { symbol: 'ETH/USDT', state: 'MONITORING', since: new Date().toISOString() },
    { symbol: 'SOL/USDT', state: 'SIGNAL_DETECTED', since: new Date().toISOString() }
  ]);

  return (
    <List>
      {symbols.map((item) => (
        <ListItem key={item.symbol}>
          <ListItemText primary={item.symbol} />
          <StateBadge state={item.state} since={item.since} showDuration size="small" />
        </ListItem>
      ))}
    </List>
  );
}
```

## Type Guard

```typescript
function isValidState(state: string): state is StateMachineState {
  return ['INACTIVE', 'MONITORING', 'SIGNAL_DETECTED', 'POSITION_ACTIVE', 'EXITED', 'ERROR'].includes(state);
}

function SafeStateBadge({ state }: { state: string }) {
  if (!isValidState(state)) {
    console.warn(`Invalid state: ${state}`);
    return null;
  }

  return <StateBadge state={state} />;
}
```

## Dynamic Color Access

```typescript
// If you need to access state colors programmatically
const STATE_COLORS: Record<StateMachineState, string> = {
  INACTIVE: '#9e9e9e',
  MONITORING: '#4caf50',
  SIGNAL_DETECTED: '#ff9800',
  POSITION_ACTIVE: '#f44336',
  EXITED: '#2196f3',
  ERROR: '#d32f2f'
};

function CustomIndicator({ state }: { state: StateMachineState }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Box
        sx={{
          width: 12,
          height: 12,
          borderRadius: '50%',
          bgcolor: STATE_COLORS[state]
        }}
      />
      <StateBadge state={state} size="small" />
    </Box>
  );
}
```

## Loading State

```typescript
function LoadingStateBadge({ isLoading, state }: { isLoading: boolean; state?: StateMachineState }) {
  if (isLoading) {
    return <Skeleton variant="rectangular" width={100} height={32} sx={{ borderRadius: 16 }} />;
  }

  if (!state) return null;

  return <StateBadge state={state} />;
}
```
