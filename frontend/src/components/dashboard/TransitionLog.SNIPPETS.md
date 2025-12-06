# TransitionLog - Code Snippets

## Quick Start

### 1. Basic Usage

```tsx
import { TransitionLog } from '@/components/dashboard';

export default function TransitionsPage() {
  return (
    <div style={{ height: '100vh', padding: '20px' }}>
      <TransitionLog
        transitions={[]}
        isLoading={true}
      />
    </div>
  );
}
```

### 2. With Real Data from API

```tsx
'use client';

import { useEffect, useState } from 'react';
import { TransitionLog, Transition } from '@/components/dashboard';
import axios from 'axios';

export default function LiveTransitionsPage() {
  const [transitions, setTransitions] = useState<Transition[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchTransitions = async () => {
      try {
        const response = await axios.get('/api/transitions');
        setTransitions(response.data);
      } catch (error) {
        console.error('Failed to fetch transitions:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTransitions();
  }, []);

  return (
    <div style={{ height: '80vh' }}>
      <TransitionLog
        transitions={transitions}
        maxItems={100}
        isLoading={isLoading}
      />
    </div>
  );
}
```

### 3. With WebSocket Real-Time Updates

```tsx
'use client';

import { useEffect, useState, useCallback } from 'react';
import { TransitionLog, Transition } from '@/components/dashboard';
import { io, Socket } from 'socket.io-client';

export default function RealtimeTransitionsPage() {
  const [transitions, setTransitions] = useState<Transition[]>([]);
  const [socket, setSocket] = useState<Socket | null>(null);

  useEffect(() => {
    const newSocket = io('http://localhost:8000', {
      path: '/ws/socket.io'
    });

    newSocket.on('transition', (data: Transition) => {
      setTransitions(prev => [data, ...prev]);
    });

    newSocket.on('connect', () => {
      console.log('WebSocket connected');
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, []);

  const handleTransitionClick = useCallback((transition: Transition) => {
    console.log('Clicked:', transition);
    // Show detail modal, navigate, etc.
  }, []);

  return (
    <div style={{ height: '90vh', padding: '16px' }}>
      <TransitionLog
        transitions={transitions}
        onTransitionClick={handleTransitionClick}
        maxItems={50}
      />
    </div>
  );
}
```

### 4. With State Management (Zustand)

```tsx
// store/transitionsStore.ts
import { create } from 'zustand';
import { Transition } from '@/components/dashboard';

interface TransitionsState {
  transitions: Transition[];
  addTransition: (transition: Transition) => void;
  clearTransitions: () => void;
}

export const useTransitionsStore = create<TransitionsState>((set) => ({
  transitions: [],
  addTransition: (transition) =>
    set((state) => ({
      transitions: [transition, ...state.transitions]
    })),
  clearTransitions: () => set({ transitions: [] })
}));

// Component
'use client';

import { TransitionLog } from '@/components/dashboard';
import { useTransitionsStore } from '@/store/transitionsStore';

export default function TransitionsWithStore() {
  const transitions = useTransitionsStore(state => state.transitions);

  return (
    <TransitionLog
      transitions={transitions}
      maxItems={100}
    />
  );
}
```

### 5. Filtered View

```tsx
'use client';

import { useState, useMemo } from 'react';
import { TransitionLog, Transition } from '@/components/dashboard';
import { Box, TextField, Select, MenuItem, FormControl, InputLabel } from '@mui/material';

export default function FilteredTransitionsPage() {
  const [transitions, setTransitions] = useState<Transition[]>([]);
  const [symbolFilter, setSymbolFilter] = useState<string>('all');
  const [triggerFilter, setTriggerFilter] = useState<string>('all');

  const filteredTransitions = useMemo(() => {
    return transitions.filter(t => {
      const matchesSymbol = symbolFilter === 'all' || t.symbol === symbolFilter;
      const matchesTrigger = triggerFilter === 'all' || t.trigger === triggerFilter;
      return matchesSymbol && matchesTrigger;
    });
  }, [transitions, symbolFilter, triggerFilter]);

  const uniqueSymbols = useMemo(() => {
    return Array.from(new Set(transitions.map(t => t.symbol)));
  }, [transitions]);

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column', p: 2 }}>
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel>Symbol</InputLabel>
          <Select
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
            label="Symbol"
          >
            <MenuItem value="all">All Symbols</MenuItem>
            {uniqueSymbols.map(symbol => (
              <MenuItem key={symbol} value={symbol}>{symbol}</MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel>Trigger</InputLabel>
          <Select
            value={triggerFilter}
            onChange={(e) => setTriggerFilter(e.target.value)}
            label="Trigger"
          >
            <MenuItem value="all">All Triggers</MenuItem>
            <MenuItem value="S1">S1</MenuItem>
            <MenuItem value="O1">O1</MenuItem>
            <MenuItem value="Z1">Z1</MenuItem>
            <MenuItem value="ZE1">ZE1</MenuItem>
            <MenuItem value="E1">E1</MenuItem>
            <MenuItem value="MANUAL">MANUAL</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Box sx={{ flexGrow: 1 }}>
        <TransitionLog
          transitions={filteredTransitions}
          maxItems={100}
        />
      </Box>
    </Box>
  );
}
```

### 6. With Export to CSV

```tsx
'use client';

import { useState } from 'react';
import { TransitionLog, Transition } from '@/components/dashboard';
import { Box, Button } from '@mui/material';
import { Download } from '@mui/icons-material';

export default function ExportableTransitionsPage() {
  const [transitions, setTransitions] = useState<Transition[]>([]);

  const exportToCSV = () => {
    const headers = ['Timestamp', 'Symbol', 'From State', 'To State', 'Trigger', 'Strategy ID'];
    const rows = transitions.map(t => [
      t.timestamp,
      t.symbol,
      t.from_state,
      t.to_state,
      t.trigger,
      t.strategy_id
    ]);

    const csv = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transitions_${new Date().toISOString()}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column', p: 2 }}>
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          startIcon={<Download />}
          onClick={exportToCSV}
          disabled={transitions.length === 0}
        >
          Export to CSV
        </Button>
      </Box>

      <Box sx={{ flexGrow: 1 }}>
        <TransitionLog
          transitions={transitions}
          maxItems={100}
        />
      </Box>
    </Box>
  );
}
```

### 7. With Modal Detail View

```tsx
'use client';

import { useState, useCallback } from 'react';
import { TransitionLog, Transition } from '@/components/dashboard';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Chip
} from '@mui/material';

export default function TransitionsWithModal() {
  const [transitions, setTransitions] = useState<Transition[]>([]);
  const [selectedTransition, setSelectedTransition] = useState<Transition | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const handleTransitionClick = useCallback((transition: Transition) => {
    setSelectedTransition(transition);
    setModalOpen(true);
  }, []);

  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedTransition(null);
  };

  return (
    <>
      <div style={{ height: '90vh', padding: '16px' }}>
        <TransitionLog
          transitions={transitions}
          onTransitionClick={handleTransitionClick}
          maxItems={50}
        />
      </div>

      <Dialog
        open={modalOpen}
        onClose={handleCloseModal}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Transition Details</DialogTitle>
        <DialogContent>
          {selectedTransition && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Timestamp
                </Typography>
                <Typography variant="body1">
                  {new Date(selectedTransition.timestamp).toLocaleString()}
                </Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Symbol
                </Typography>
                <Typography variant="body1">{selectedTransition.symbol}</Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Strategy
                </Typography>
                <Typography variant="body1">{selectedTransition.strategy_id}</Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Transition
                </Typography>
                <Typography variant="body1">
                  {selectedTransition.from_state} → {selectedTransition.to_state}
                </Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Trigger
                </Typography>
                <Chip label={selectedTransition.trigger} color="primary" />
              </Box>

              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Conditions
                </Typography>
                {Object.entries(selectedTransition.conditions).map(([key, cond]) => (
                  <Box key={key} sx={{ ml: 2, mb: 1 }}>
                    <Typography variant="body2">
                      <strong>{cond.indicator_name}:</strong> {cond.value.toFixed(2)}{' '}
                      {cond.operator} {cond.threshold.toFixed(2)}{' '}
                      <Chip
                        label={cond.met ? 'MET' : 'NOT MET'}
                        color={cond.met ? 'success' : 'error'}
                        size="small"
                      />
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseModal}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
```

## Mock Data Generator

```typescript
import { Transition } from '@/components/dashboard';

export function generateMockTransition(index: number = 0): Transition {
  const symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'MATIC/USDT'];
  const states = ['INACTIVE', 'MONITORING', 'SIGNAL_DETECTED', 'POSITION_ACTIVE', 'EXITED'];
  const triggers: Array<'S1' | 'O1' | 'Z1' | 'ZE1' | 'E1' | 'MANUAL'> =
    ['S1', 'O1', 'Z1', 'ZE1', 'E1', 'MANUAL'];

  return {
    timestamp: new Date(Date.now() - index * 60000).toISOString(),
    strategy_id: `PUMP_DUMP_${String(index).padStart(3, '0')}`,
    symbol: symbols[index % symbols.length],
    from_state: states[index % states.length],
    to_state: states[(index + 1) % states.length],
    trigger: triggers[index % triggers.length],
    conditions: {
      volume_surge: {
        indicator_name: 'Volume Surge',
        value: Math.random() * 5,
        threshold: 2.0,
        operator: '>',
        met: Math.random() > 0.5
      },
      price_spike: {
        indicator_name: 'Price Spike',
        value: Math.random() * 10,
        threshold: 3.0,
        operator: '>',
        met: Math.random() > 0.5
      }
    }
  };
}

export function generateMockTransitions(count: number = 20): Transition[] {
  return Array.from({ length: count }, (_, i) => generateMockTransition(i));
}
```

## Integration Patterns

### Pattern 1: Polling

```tsx
useEffect(() => {
  const interval = setInterval(async () => {
    const response = await axios.get('/api/transitions');
    setTransitions(response.data);
  }, 5000); // Poll every 5 seconds

  return () => clearInterval(interval);
}, []);
```

### Pattern 2: WebSocket with Reconnection

```tsx
useEffect(() => {
  let ws: WebSocket;
  let reconnectTimeout: NodeJS.Timeout;

  const connect = () => {
    ws = new WebSocket('ws://localhost:8000/ws/transitions');

    ws.onmessage = (event) => {
      const transition: Transition = JSON.parse(event.data);
      setTransitions(prev => [transition, ...prev]);
    };

    ws.onclose = () => {
      reconnectTimeout = setTimeout(connect, 3000);
    };
  };

  connect();

  return () => {
    clearTimeout(reconnectTimeout);
    ws?.close();
  };
}, []);
```
