# Story 1A.3: Indicator Values Panel

Status: ready-for-dev

## Story

As a **trader**,
I want **to see current indicator values on the dashboard**,
so that **I understand what data is driving the signal detection**.

## Acceptance Criteria

1. **AC1:** Panel displays MVP indicators: TWPA, pump_magnitude_pct, volume_surge_ratio, price_velocity, spread_pct
2. **AC2:** Values update in real-time as new data arrives
3. **AC3:** Each indicator shows: name, current value, unit/format
4. **AC4:** Panel is visible during active sessions
5. **AC5:** Values are formatted appropriately (%, ratio, price)

## Tasks / Subtasks

- [ ] **Task 1: Create IndicatorPanel Component** (AC: 1, 3)
  - [ ] 1.1 Create `IndicatorValuesPanel.tsx`
  - [ ] 1.2 Define list of MVP indicators to display
  - [ ] 1.3 Create row layout: name | value | unit
  - [ ] 1.4 Apply appropriate formatting per indicator type

- [ ] **Task 2: Connect to Indicator Data** (AC: 2)
  - [ ] 2.1 Identify indicator data source (WebSocket stream)
  - [ ] 2.2 Subscribe to `indicator.updated` events
  - [ ] 2.3 Update panel values on new data
  - [ ] 2.4 Handle missing/stale data gracefully

- [ ] **Task 3: Value Formatting** (AC: 5)
  - [ ] 3.1 Percentages: `7.25%`
  - [ ] 3.2 Ratios: `3.5x`
  - [ ] 3.3 Prices: `$45,230.50`
  - [ ] 3.4 Add trend arrows (↑↓→) if data available

- [ ] **Task 4: Dashboard Integration** (AC: 4)
  - [ ] 4.1 Place panel in dashboard layout
  - [ ] 4.2 Ensure visibility during trading sessions
  - [ ] 4.3 Collapse/hide when no session active (optional)

## Dev Notes

### FR20 Requirement

From PRD: "FR20: Trader can view real-time indicator values"

### MVP Indicators

From PRD:
- **TWPA** (Time-Weighted Price Average) - foundation
- **pump_magnitude_pct** - percentage
- **volume_surge_ratio** - ratio (e.g., 3.5x)
- **price_velocity** - rate
- **spread_pct** - percentage
- **unrealized_pnl_pct** - percentage (when in position)

### Existing Components

Check existing indicator display:
```
frontend/src/components/dashboard/LiveIndicatorPanel.tsx
frontend/src/components/dashboard/PumpIndicatorsPanel.tsx
```

### Data Source

Indicators arrive via WebSocket:
```typescript
// websocket.ts
case 'indicators':
  this.callbacks.onIndicators?.(message);
  break;
```

### Formatting Examples

| Indicator | Raw Value | Formatted |
|-----------|-----------|-----------|
| pump_magnitude_pct | 0.0725 | +7.25% |
| volume_surge_ratio | 3.5 | 3.5x |
| price_velocity | 0.0012 | +0.12%/s |
| spread_pct | 0.0008 | 0.08% |
| unrealized_pnl_pct | 0.15 | +15.0% |

### Component Structure

```typescript
interface IndicatorValue {
  name: string;
  value: number;
  unit: 'percent' | 'ratio' | 'price' | 'rate';
  trend?: 'up' | 'down' | 'flat';
}

const MVP_INDICATORS = [
  { key: 'pump_magnitude_pct', name: 'Pump Magnitude', unit: 'percent' },
  { key: 'volume_surge_ratio', name: 'Volume Surge', unit: 'ratio' },
  // ...
];
```

### References

- [Source: _bmad-output/prd.md#FR20]
- [Source: _bmad-output/prd.md#MVP Indicators]
- [Source: frontend/src/components/dashboard/LiveIndicatorPanel.tsx]
- [Source: frontend/src/services/websocket.ts:275]

## Dev Agent Record

### Agent Model Used
{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
