# Story 1A.3: Indicator Values Panel

Status: review

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

- [x] **Task 1: Create IndicatorPanel Component** (AC: 1, 3)
  - [x] 1.1 Create `IndicatorValuesPanel.tsx`
  - [x] 1.2 Define list of MVP indicators to display
  - [x] 1.3 Create row layout: name | value | unit
  - [x] 1.4 Apply appropriate formatting per indicator type

- [x] **Task 2: Connect to Indicator Data** (AC: 2)
  - [x] 2.1 Identify indicator data source (WebSocket stream)
  - [x] 2.2 Subscribe to `indicator.updated` events
  - [x] 2.3 Update panel values on new data
  - [x] 2.4 Handle missing/stale data gracefully

- [x] **Task 3: Value Formatting** (AC: 5)
  - [x] 3.1 Percentages: `7.25%`
  - [x] 3.2 Ratios: `3.5x`
  - [x] 3.3 Prices: `$45,230.50`
  - [x] 3.4 Add trend arrows (↑↓→) if data available

- [x] **Task 4: Dashboard Integration** (AC: 4)
  - [x] 4.1 Place panel in dashboard layout
  - [x] 4.2 Ensure visibility during trading sessions
  - [x] 4.3 Collapse/hide when no session active (optional)

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
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References
N/A - No issues encountered

### Completion Notes List

**Implementation Summary (2025-12-27):**

1. **Created IndicatorValuesPanel Component** (`frontend/src/components/dashboard/IndicatorValuesPanel.tsx`)
   - Displays 6 MVP indicators: TWPA, pump_magnitude_pct, volume_surge_ratio, price_velocity, spread_pct, unrealized_pnl_pct
   - Each indicator shows label, formatted value, and trend icon (↑↓→)
   - Uses MUI components for consistent styling

2. **WebSocket Integration**
   - Subscribes to `indicators` stream via wsService
   - Handles real-time updates through `onIndicators` callback
   - Syncs with dashboardStore indicators
   - Proper cleanup on unmount

3. **Value Formatting (AC5)**
   - Percentages: `+7.25%` or `-3.12%`
   - Ratios: `3.50x`
   - Prices: `$45,230.50` (USD currency format)
   - Rates: `+0.12%/s`
   - Graceful handling of null/undefined/NaN → displays `--`

4. **Dashboard Integration**
   - Added to dashboard grid layout (line 962)
   - Placed alongside LiveIndicatorPanel and ConditionProgressIntegration
   - Visible only during active sessions (AC4)
   - Shows "No active session" when sessionId is null

5. **Tests**
   - Created comprehensive test suite with 15 tests
   - All acceptance criteria covered
   - 100% tests passing

### File List

**New Files:**
- `frontend/src/components/dashboard/IndicatorValuesPanel.tsx`
- `frontend/src/components/dashboard/__tests__/IndicatorValuesPanel.test.tsx`

**Modified Files:**
- `frontend/src/app/dashboard/page.tsx` (added import and component usage)

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-12-27 | Story implemented - IndicatorValuesPanel component created with WebSocket integration, value formatting, and dashboard integration. All 5 ACs satisfied. 15 tests passing. | Claude Opus 4.5 |
