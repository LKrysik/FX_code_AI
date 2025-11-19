# Session Configuration Integration Guide

**Cel:** Pokazać jak zintegrować SessionConfigDialog z istniejącymi stronami dashboardu

## Problem

Obecnie w dashboard/page.tsx (linia 317-318):
```typescript
symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT'], // TODO: Make configurable
strategy_config: {}, // TODO: Load from strategy selection
```

**Symbole i strategie są na sztywno zakodowane!** Brak UI do ich wyboru.

## Rozwiązanie

Użyj `SessionConfigDialog` który otwiera się PRZED startem sesji i pozwala wybrać:
- Tryb (live/paper/backtest)
- Strategie (multi-select)
- Symbole (multi-select)
- Budget i parametry ryzyka
- Dla backtesting: sesję historyczną i acceleration_factor

## Integracja Krok po Kroku

### Krok 1: Import komponentu

```typescript
// W dashboard/page.tsx (lub innej stronie)
import SessionConfigDialog, { SessionConfig } from '@/components/trading/SessionConfigDialog';
```

### Krok 2: Dodaj state dla dialogu

```typescript
const [configDialogOpen, setConfigDialogOpen] = useState(false);
const [pendingSessionConfig, setPendingSessionConfig] = useState<SessionConfig | null>(null);
```

### Krok 3: Zmień handler "Start Session"

**STARY KOD (do usunięcia):**
```typescript
const handleStartSession = async () => {
  if (mode === 'backtest' && !backtestSessionId) {
    // ... validation
  }

  const sessionData: any = {
    session_type: mode,
    symbols: ['BTC_USDT', 'ETH_USDT', 'ADA_USDT'], // ❌ HARDCODED
    strategy_config: {}, // ❌ EMPTY
    config: {
      budget: { global_cap: 1000, allocations: {} },
    },
  };

  // ... start session
};
```

**NOWY KOD (z konfiguracją):**
```typescript
const handleOpenConfigDialog = () => {
  // Otwórz dialog konfiguracji zamiast od razu startować sesję
  setConfigDialogOpen(true);
};

const handleSessionConfigConfirm = async (config: SessionConfig) => {
  try {
    // ✅ Użyj REALNYCH wartości z formularza
    const sessionData: any = {
      session_type: config.mode,
      symbols: config.symbols,  // ✅ Z wyboru użytkownika
      strategy_config: {
        strategies: config.strategies,  // ✅ Z wyboru użytkownika
      },
      config: {
        budget: {
          global_cap: config.config.global_budget,
          allocations: {},
        },
        stop_loss_percent: config.config.stop_loss_percent,
        take_profit_percent: config.config.take_profit_percent,
      },
      idempotent: true,
    };

    // Dla backtest: dodaj session_id i acceleration_factor
    if (config.mode === 'backtest') {
      sessionData.config.session_id = config.config.session_id;
      sessionData.config.acceleration_factor = config.config.acceleration_factor;
    }

    const response = await apiService.startSession(sessionData);

    setSessionId(response.data?.session_id || null);
    setIsSessionRunning(true);

    setSnackbar({
      open: true,
      message: `${config.mode.toUpperCase()} session started with ${config.symbols.length} symbols and ${config.strategies.length} strategies`,
      severity: 'success',
    });
  } catch (error) {
    console.error('Failed to start session:', error);
    setSnackbar({
      open: true,
      message: 'Failed to start session',
      severity: 'error',
    });
  }
};
```

### Krok 4: Zmień przycisk "Start Session" w UI

**STARY KOD:**
```tsx
<Button
  variant="contained"
  color="primary"
  onClick={handleStartSession}  // ❌ Bezpośredni start
  disabled={isSessionRunning || (mode === 'backtest' && !backtestSessionId)}
>
  Start {mode.toUpperCase()} Session
</Button>
```

**NOWY KOD:**
```tsx
<Button
  variant="contained"
  color="primary"
  onClick={handleOpenConfigDialog}  // ✅ Najpierw konfiguracja
  disabled={isSessionRunning}
>
  Configure & Start Session
</Button>
```

### Krok 5: Dodaj SessionConfigDialog do JSX

```tsx
return (
  <Box>
    {/* Istniejący kod dashboard... */}

    {/* ✅ NOWY: Dialog konfiguracji sesji */}
    <SessionConfigDialog
      open={configDialogOpen}
      onClose={() => setConfigDialogOpen(false)}
      onConfirm={handleSessionConfigConfirm}
      defaultMode={mode}  // Użyj trybu z ToggleButtonGroup
    />

    {/* Snackbar, inne komponenty... */}
  </Box>
);
```

## Pełny Przykład Kodu

```typescript
'use client';

import React, { useState, useEffect } from 'react';
import { Box, Button, Typography, ToggleButton, ToggleButtonGroup } from '@mui/material';
import SessionConfigDialog, { SessionConfig } from '@/components/trading/SessionConfigDialog';
import { apiService } from '@/services/api';

type TradingMode = 'live' | 'paper' | 'backtest';

export default function TradingDashboard() {
  // State
  const [mode, setMode] = useState<TradingMode>('paper');
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [isSessionRunning, setIsSessionRunning] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Handlers
  const handleModeChange = (event: React.MouseEvent<HTMLElement>, newMode: TradingMode | null) => {
    if (newMode !== null) {
      setMode(newMode);
    }
  };

  const handleOpenConfigDialog = () => {
    setConfigDialogOpen(true);
  };

  const handleSessionConfigConfirm = async (config: SessionConfig) => {
    try {
      // Przygotuj dane sesji z konfiguracji użytkownika
      const sessionData: any = {
        session_type: config.mode,
        symbols: config.symbols,  // ✅ Z wyboru użytkownika
        strategy_config: {
          strategies: config.strategies,  // ✅ Z wyboru użytkownika
        },
        config: {
          budget: {
            global_cap: config.config.global_budget,
            allocations: {},
          },
          stop_loss_percent: config.config.stop_loss_percent,
          take_profit_percent: config.config.take_profit_percent,
        },
        idempotent: true,
      };

      // Dla backtest: dodaj specjalne parametry
      if (config.mode === 'backtest') {
        sessionData.config.session_id = config.config.session_id;
        sessionData.config.acceleration_factor = config.config.acceleration_factor || 10;
      }

      // Wystartuj sesję
      const response = await apiService.startSession(sessionData);

      setSessionId(response.data?.session_id || null);
      setIsSessionRunning(true);

      console.log('✅ Session started:', {
        sessionId: response.data?.session_id,
        mode: config.mode,
        symbols: config.symbols,
        strategies: config.strategies,
      });
    } catch (error) {
      console.error('❌ Failed to start session:', error);
    }
  };

  const handleStopSession = async () => {
    if (!sessionId) return;

    try {
      await apiService.stopSession(sessionId);
      setIsSessionRunning(false);
      setSessionId(null);
    } catch (error) {
      console.error('Failed to stop session:', error);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Trading Dashboard
      </Typography>

      {/* Mode Selection */}
      <ToggleButtonGroup
        value={mode}
        exclusive
        onChange={handleModeChange}
        disabled={isSessionRunning}
        sx={{ mb: 3 }}
      >
        <ToggleButton value="live">Live Trading</ToggleButton>
        <ToggleButton value="paper">Paper Trading</ToggleButton>
        <ToggleButton value="backtest">Backtest</ToggleButton>
      </ToggleButtonGroup>

      {/* Session Controls */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={handleOpenConfigDialog}
          disabled={isSessionRunning}
        >
          Configure & Start Session
        </Button>

        <Button
          variant="outlined"
          color="error"
          onClick={handleStopSession}
          disabled={!isSessionRunning}
        >
          Stop Session
        </Button>
      </Box>

      {/* Session Status */}
      {isSessionRunning && sessionId && (
        <Typography variant="body2" color="success.main">
          Session running: {sessionId}
        </Typography>
      )}

      {/* ✅ Session Configuration Dialog */}
      <SessionConfigDialog
        open={configDialogOpen}
        onClose={() => setConfigDialogOpen(false)}
        onConfirm={handleSessionConfigConfirm}
        defaultMode={mode}
      />

      {/* Dashboard content... */}
    </Box>
  );
}
```

## ⚠️ WAŻNE: Stan MOCKUP

**Obecnie SessionConfigDialog zawiera MOCKUP dane:**
- Strategie są hardcoded (MOCK_STRATEGIES)
- Symbole są hardcoded (MOCK_SYMBOLS)
- Sesje historyczne są hardcoded (MOCK_DATA_SESSIONS)
- Przyciski tylko logują do konsoli

**Aby użyć w produkcji, musisz:**

1. **Podłączyć prawdziwe API:**
```typescript
// W SessionConfigMockup.tsx - zamień MOCK_STRATEGIES na:
useEffect(() => {
  fetch('/api/strategies')
    .then(res => res.json())
    .then(data => setStrategies(data.strategies));
}, []);

// Zamień MOCK_SYMBOLS na:
useEffect(() => {
  fetch('/api/exchange/symbols')
    .then(res => res.json())
    .then(data => setSymbols(data.symbols));
}, []);

// Zamień MOCK_DATA_SESSIONS na:
useEffect(() => {
  fetch('/api/data-collection/sessions')
    .then(res => res.json())
    .then(data => setSessions(data.sessions));
}, []);
```

2. **Usunąć MOCKUP warningi:**
```typescript
// Usuń wszystkie <Alert> z "⚠️ MOCKUP" po podłączeniu prawdziwych API
```

3. **Dodać walidację:**
```typescript
// Sprawdź czy wybrano przynajmniej 1 strategię
if (selectedStrategies.length === 0) {
  setError('Please select at least one strategy');
  return;
}

// Sprawdź czy wybrano przynajmniej 1 symbol
if (selectedSymbols.length === 0) {
  setError('Please select at least one symbol');
  return;
}
```

## Gdzie Używać

**Strony do zintegrowania:**

1. **[/app/dashboard/page.tsx](../../frontend/src/app/dashboard/page.tsx)** - Główny dashboard
2. **[/app/paper/page.tsx](../../frontend/src/app/paper/)** - Paper trading
3. **[/app/trading/page.tsx](../../frontend/src/app/trading/)** - Live trading
4. **[/app/backtesting/page.tsx](../../frontend/src/app/backtesting/)** - Backtesting

W każdej z tych stron zamień hardcoded `symbols` i `strategy_config` na wartości z `SessionConfigDialog`.

## Testowanie

1. **Otwórz dowolną stronę z trading dashboard**
2. **Kliknij "Configure & Start Session"**
3. **Wybierz strategie i symbole** (obecnie MOCKUP data)
4. **Zobacz w konsoli** co zostało wybrane (console.log)
5. **Implementuj prawdziwe API** żeby dane były realne

## Dalsze Kroki

- [ ] Podłączyć GET /api/strategies
- [ ] Podłączyć GET /api/exchange/symbols
- [ ] Podłączyć GET /api/data-collection/sessions
- [ ] Dodać walidację formularza
- [ ] Dodać loading states
- [ ] Usunąć MOCKUP warningi
- [ ] Dodać zapisywanie ulubionych konfiguracji
- [ ] Dodać preview strategii przed startem

---

**Pytania?** Zobacz [SessionConfigMockup.tsx](../../frontend/src/components/trading/SessionConfigMockup.tsx) i [SessionConfigDialog.tsx](../../frontend/src/components/trading/SessionConfigDialog.tsx)
