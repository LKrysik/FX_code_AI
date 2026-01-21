# Story 1B-1: Backtest Session Setup

**Status:** done
**Priority:** P0 (MVP)
**Epic:** Epic 1B - First Successful Backtest

---

## Story

As a **trader**,
I want **to configure and start a backtest session**,
So that **I can test my strategy against historical data**.

---

## Acceptance Criteria

1. **AC1:** Setup form allows selecting a strategy from saved strategies
2. **AC2:** Setup form allows selecting a trading symbol (e.g., BTCUSDT, ETHUSDT)
3. **AC3:** Setup form allows selecting a date range (start/end date) for historical data
4. **AC4:** System validates that historical data exists for the selected range
5. **AC5:** Warning shows if data is incomplete or missing for the range
6. **AC6:** "Start Backtest" button starts the session and redirects to dashboard
7. **AC7:** Validation errors highlight missing required fields
8. **AC8:** Start button is disabled until all required fields are filled

---

## Tasks / Subtasks

- [x] Task 1: Create BacktestSetupForm component (AC: 1, 2, 3)
  - [x] Strategy dropdown populated from /api/strategies
  - [x] Symbol dropdown with available trading pairs
  - [x] MUI DatePicker for start/end date selection
  - [x] Form validation with React state and useEffect

- [x] Task 2: Implement data availability check (AC: 4, 5)
  - [x] API endpoint: GET /api/backtest/data-availability?symbol=X&start=Y&end=Z
  - [x] Frontend displays warning for incomplete data
  - [x] Show data coverage percentage

- [x] Task 3: Implement backtest start API (AC: 6)
  - [x] API endpoint: POST /api/backtest/start
  - [x] Request body: { strategy_id, symbol, start_date, end_date }
  - [x] Response: { session_id, status: "started" }
  - [x] Frontend redirects to /dashboard?mode=backtest&session_id=X

- [x] Task 4: Form validation and UX (AC: 7, 8)
  - [x] Required field validation
  - [x] Disabled button state
  - [x] Loading state during submission
  - [x] Error display for API failures

---

## Implementation Details

### Files Created

**Frontend:**
- `frontend/src/components/backtest/BacktestSetupForm.tsx` - Main form component with MUI
- `frontend/src/components/backtest/index.ts` - Component exports
- `frontend/src/services/backtestApi.ts` - API service for backtest endpoints
- `frontend/src/components/backtest/__tests__/BacktestSetupForm.test.tsx` - Unit tests

**Backend:**
- `src/api/backtest_routes.py` - FastAPI routes for backtest endpoints

### API Endpoints Implemented

```
GET /api/backtest/data-availability
Query: symbol, start_date, end_date
Response: {
  status: "success",
  data: {
    available: true,
    symbol: "BTCUSDT",
    start_date: "2025-11-01",
    end_date: "2025-11-07",
    coverage_pct: 98.5,
    total_records: 500000,
    expected_records: 520000,
    missing_ranges: [...],
    data_quality: "good" | "warning" | "error",
    quality_issues: [...]
  }
}

POST /api/backtest/start
Body: {
  strategy_id: "strategy_001",
  symbol: "BTCUSDT",
  start_date: "2025-11-01",
  end_date: "2025-11-07",
  session_id: "dc_xxx" (optional),
  config: {
    acceleration_factor: 10,
    initial_balance: 10000,
    stop_loss_percent: 5.0,
    take_profit_percent: 10.0
  }
}
Response: {
  status: "success",
  data: {
    session_id: "bt_20251128_150000_abc123",
    status: "started",
    symbol: "BTCUSDT",
    strategy_id: "strategy_001",
    start_date: "2025-11-01",
    end_date: "2025-11-07",
    estimated_duration_seconds: 60
  }
}

GET /api/backtest/sessions
Query: limit, status
Response: { status: "success", data: { sessions: [...], count: N } }

GET /api/backtest/sessions/{session_id}
Response: { status: "success", data: { session details... } }
```

### Component Structure

```
frontend/src/components/backtest/
├── BacktestSetupForm.tsx      # Main form component (all-in-one)
├── SessionSelector.tsx        # Existing session selector (reused)
├── index.ts                   # Component exports
└── __tests__/
    └── BacktestSetupForm.test.tsx  # Comprehensive unit tests
```

### Key Features

1. **Strategy Selection (AC1)**
   - Dropdown populated via `backtestApi.getStrategies()`
   - Shows strategy name and description
   - Loading state while fetching

2. **Symbol Selection (AC2)**
   - Dropdown populated via `backtestApi.getSymbols()`
   - Fallback to common symbols on error
   - Optional data collection session selection

3. **Date Range Selection (AC3)**
   - MUI DatePicker components
   - Default: last 7 days
   - Validation: end > start, max 365 days, not future

4. **Data Availability Check (AC4 & AC5)**
   - Auto-checks when symbol/dates change (debounced)
   - Displays coverage percentage with color coding
   - Shows missing data ranges as chips
   - Quality indicators: good/warning/error

5. **Form Submission (AC6)**
   - Calls `POST /api/backtest/start`
   - Shows loading spinner during submission
   - Redirects to `/dashboard?mode=backtest&session_id=X`
   - Optional callback `onBacktestStarted`

6. **Validation (AC7 & AC8)**
   - Required field validation on blur and submit
   - Error messages below each field
   - Start button disabled until form valid
   - General error alert for API failures

### Testing Coverage

Unit tests cover all acceptance criteria:
- AC1: Strategy loading and selection
- AC2: Symbol loading and selection
- AC3: Date picker rendering and defaults
- AC4: Data availability check triggers
- AC5: Warning/error display for partial data
- AC6: Form submission and redirect
- AC7: Validation error display
- AC8: Button disabled state

### Usage Example

```tsx
import { BacktestSetupForm } from '@/components/backtest';

// Basic usage
<BacktestSetupForm />

// With callback
<BacktestSetupForm
  onBacktestStarted={(sessionId) => {
    console.log('Backtest started:', sessionId);
  }}
/>

// With default values
<BacktestSetupForm
  defaultStrategy="strategy_001"
  defaultSymbol="BTCUSDT"
  defaultStartDate={new Date('2025-11-01')}
  defaultEndDate={new Date('2025-11-07')}
/>
```

---

## Definition of Done

1. [x] BacktestSetupForm renders with all required fields
2. [x] Strategy dropdown populated from API
3. [x] Symbol dropdown shows available pairs
4. [x] Date range picker works correctly
5. [x] Data availability check shows warnings
6. [x] Form validation prevents invalid submissions
7. [x] Start button initiates backtest session
8. [x] Redirect to dashboard after start
9. [x] Unit tests for form validation
10. [ ] Integration test for full flow (deferred to E2E tests)

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-12-31 | SM | Story created for Epic 1B kickoff |
| 2025-12-31 | Claude | Implemented BacktestSetupForm component |
| 2025-12-31 | Claude | Created backtestApi.ts service |
| 2025-12-31 | Claude | Created backtest_routes.py backend |
| 2025-12-31 | Claude | Added comprehensive unit tests |
| 2025-12-31 | Claude | Story completed - all ACs met |
