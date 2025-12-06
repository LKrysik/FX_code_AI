# StateBadge Component

**Lokalizacja:** `frontend/src/components/dashboard/StateBadge.tsx`

## Opis

Komponent wyświetlający aktualny stan state machine jako kolorowy badge z ikoną. Wspiera animacje, tooltips, live duration updates i różne rozmiary.

## Features

- 6 stanów state machine z unikalnymi kolorami i ikonami
- Pulsująca animacja dla stanu SIGNAL_DETECTED (uwaga tradera!)
- Live duration updates (odświeżanie co sekundę)
- Tooltips z pełnym opisem stanu
- 3 rozmiary: small, medium, large
- Material UI integration
- Fully typed TypeScript
- Responsive design

## Stany i kolory

| Stan | Kolor | Ikona | Opis |
|------|-------|-------|------|
| INACTIVE | Gray (#9e9e9e) | ⏸️ | System nie monitoruje aktywnie |
| MONITORING | Green (#4caf50) | 👁️ | Aktywne skanowanie rynków |
| SIGNAL_DETECTED | Yellow (#ff9800) | ⚡ | Sygnał wykryty - PULSUJE! |
| POSITION_ACTIVE | Red (#f44336) | 📍 | Pozycja otwarta |
| EXITED | Blue (#2196f3) | ✓ | Pozycja zamknięta |
| ERROR | Red (#d32f2f) | ⚠️ | Błąd systemu |

## Props

```typescript
interface StateBadgeProps {
  state: StateMachineState;
  since?: string;        // ISO timestamp (np. "2025-12-06T10:30:00Z")
  size?: 'small' | 'medium' | 'large';
  showDuration?: boolean; // Pokazuj "5m 23s"
}

type StateMachineState =
  | 'INACTIVE'
  | 'MONITORING'
  | 'SIGNAL_DETECTED'
  | 'POSITION_ACTIVE'
  | 'EXITED'
  | 'ERROR';
```

## Przykłady użycia

### Podstawowe

```tsx
import StateBadge from '@/components/dashboard/StateBadge';

// Minimalny przykład
<StateBadge state="MONITORING" />

// Z duration
<StateBadge
  state="POSITION_ACTIVE"
  since={position.entryTime}
  showDuration
/>

// Custom size
<StateBadge
  state="SIGNAL_DETECTED"
  size="large"
/>
```

### Dashboard Header

```tsx
<Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
  <Typography variant="h6">System Status:</Typography>
  <StateBadge
    state={systemState}
    since={systemStateChangedAt}
    showDuration
  />
</Box>
```

### Strategy Card

```tsx
<Card>
  <CardContent>
    <Typography variant="h6">BTC/USDT Strategy</Typography>
    <StateBadge
      state={strategy.state}
      since={strategy.stateChangedAt}
      showDuration
      size="small"
    />
  </CardContent>
</Card>
```

### Position Monitor Table

```tsx
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
  <TableCell>{position.pnl}</TableCell>
</TableRow>
```

### Real-time WebSocket Integration

```tsx
function TradingDashboard() {
  const [state, setState] = useState<StateMachineState>('INACTIVE');
  const [since, setSince] = useState<string>(new Date().toISOString());

  useEffect(() => {
    const socket = io('http://localhost:8000');

    socket.on('state_change', (data) => {
      setState(data.state);
      setSince(data.timestamp);
    });

    return () => socket.disconnect();
  }, []);

  return (
    <StateBadge
      state={state}
      since={since}
      showDuration
    />
  );
}
```

## Behavior

### Pulsing Animation

- Tylko stan `SIGNAL_DETECTED` pulsuje automatycznie
- Animacja 2s ease-in-out infinite
- Box shadow rozszerza się od 0 do 8px
- Przyciąga uwagę tradera do nowego sygnału

### Duration Calculation

- Odświeżane co 1 sekundę (setInterval)
- Format: `5m 23s`, `2h 15m`, `3d 12h`
- Graceful handling niepoprawnych dat
- Auto-cleanup przy unmount

### Tooltip

- Pokazuje pełny opis stanu
- Timestamp w lokalnym formacie
- Arrow placement: top
- Hover activation

## Styling

Komponent używa MUI theming:

```tsx
sx={{
  backgroundColor: alpha(config.color, 0.15),
  color: config.color,
  borderColor: config.color,
  border: '1px solid',
  '&:hover': {
    backgroundColor: alpha(config.color, 0.25)
  }
}}
```

## Testing

```bash
npm test StateBadge.test.tsx
```

Testy pokrywają:
- Renderowanie wszystkich stanów
- Size variations
- Duration display
- Icon presence
- Pulsing animation
- Invalid date handling
- Live updates

## Dependencies

- `@mui/material` - Chip, Tooltip, Box, styled
- `@mui/material/styles` - alpha
- React hooks: useState, useEffect

## Performance

- Minimal re-renders
- Efficient duration calculations
- Proper cleanup (clearInterval)
- shouldForwardProp optimization

## Accessibility

- Semantic HTML (Chip renders as button)
- Tooltips for screen readers
- High contrast colors
- Icon + text labels

## Browser Support

- Chrome/Edge: ✅
- Firefox: ✅
- Safari: ✅
- Mobile: ✅

## Future Enhancements

Potencjalne rozszerzenia:

- [ ] Sound alert dla SIGNAL_DETECTED
- [ ] Custom colors przez props
- [ ] Animation speed control
- [ ] Historical state changes log
- [ ] Export do CSV
- [ ] Dark mode optimization

## Troubleshooting

**Problem:** Duration nie aktualizuje się
- Sprawdź czy `since` jest poprawnym ISO timestamp
- Sprawdź czy `showDuration={true}`
- Check console for errors

**Problem:** Pulsing nie działa
- Sprawdź czy state === 'SIGNAL_DETECTED'
- Check CSS animations support
- Verify @keyframes loading

**Problem:** Tooltip nie pokazuje się
- Hover over badge
- Check MUI Tooltip configuration
- Verify z-index conflicts

## Related Components

- `SystemStatusIndicator` - ogólny status systemu
- `PositionMonitor` - monitoring pozycji
- `SignalDetailPanel` - szczegóły sygnałów

## Changelog

### v1.0.0 (2025-12-06)
- Initial release
- 6 stanów state machine
- Pulsing animation
- Live duration updates
- Full TypeScript support
