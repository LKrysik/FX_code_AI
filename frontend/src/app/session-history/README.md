# Session History Module

**Location:** `/session-history`
**Status:** SH-01 COMPLETE, SH-02 PLACEHOLDER
**Backend:** `/api/paper-trading/sessions`

---

## Pages

### 1. Session List (`/session-history`)
**File:** `page.tsx` (447 lines)

**Features:**
- Session table with all past trading sessions
- Filters: Status (Running/Stopped/Completed/Error) + Strategy
- Click row → navigate to session detail
- Color-coded P&L (green/red) and Status (success/info/error/warning)
- Refresh button, loading state, error handling

**Data Source:** `GET /api/paper-trading/sessions?status={}&strategy_id={}&limit=100`

---

### 2. Session Detail (`/session-history/[sessionId]`)
**File:** `[sessionId]/page.tsx` (384 lines)

**Features (Current):**
- Session metadata (ID, strategy, symbols, dates, status)
- Performance cards (Initial Balance, P&L, Return %)
- Breadcrumbs navigation
- "Coming Soon" section listing future features

**Features (Planned - SH-03 to SH-07):**
- State machine transition timeline
- Signal count breakdown (S1/Z1/O1/E1 accuracy)
- Chart with state markers
- Per-trade breakdown table
- Expandable transition details with indicator values

**Data Source:** `GET /api/paper-trading/sessions/{sessionId}`

---

## Quick Test

### Setup
```bash
# 1. Start backend
cd src
python -m src.main

# 2. Start frontend (separate terminal)
cd frontend
npm run dev

# 3. Open browser
http://localhost:3000/session-history
```

### Test Scenario
```
1. Navigate to Session History from sidebar
   ✅ Page loads with empty state message

2. Create a paper trading session:
   - Go to Dashboard
   - Click "Start Paper Session"
   - Configure: strategy="pump_peak_short", symbol="BTC_USDT"
   - Start session

3. Return to Session History
   - Click refresh button
   ✅ New session appears in table
   ✅ Status shows "Running" (blue chip)
   ✅ P&L shows "N/A" (no trades yet)

4. Click session row
   ✅ Navigates to detail page
   ✅ Shows session metadata
   ✅ "Coming Soon" section visible

5. Test filters:
   - Select "Running" status filter
   ✅ Only running sessions shown
   - Clear filters
   ✅ All sessions reappear
```

---

## TypeScript Types

### SessionSummary
```typescript
interface SessionSummary {
  session_id: string;
  strategy_id: string;
  strategy_name: string;
  symbols: string; // Comma-separated
  direction: string;
  status: string;
  created_at: string;
  started_at: string | null;
  stopped_at: string | null;
  initial_balance: number;
  current_balance?: number;
  total_pnl?: number;
  total_return_pct?: number;
  total_trades?: number;
  notes?: string;
}
```

### SessionDetail
Same as SessionSummary (uses `/api/paper-trading/sessions/{id}`)

---

## Component Structure

### Session List Page
```
<Box>
  <Header>
    <Typography>Session History</Typography>
    <RefreshButton />
  </Header>

  <FiltersPanel>
    <StatusFilter />
    <StrategyFilter />
    <ClearFiltersButton />
  </FiltersPanel>

  {error && <Alert severity="error" />}

  {loading ? (
    <CircularProgress />
  ) : sessions.length === 0 ? (
    <EmptyState />
  ) : (
    <Table>
      <TableHead>
        <TableRow>
          Date | Strategy | Symbols | Direction | Initial | P&L | Return% | Trades | Status | Actions
        </TableRow>
      </TableHead>
      <TableBody>
        {sessions.map(session => (
          <TableRow onClick={() => navigate(session.id)}>
            {/* ... */}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )}

  <Footer>
    Showing X sessions
  </Footer>
</Box>
```

### Session Detail Page
```
<Box>
  <Breadcrumbs>
    Session History > {sessionId}
  </Breadcrumbs>

  <Header>
    <Typography>Session Details</Typography>
    <BackButton />
  </Header>

  <SessionInfoPanel>
    <Grid>
      Session ID | Strategy | Symbols | Direction
      Created | Started | Stopped | Status
    </Grid>
  </SessionInfoPanel>

  <PerformanceCards>
    <Card>Initial Balance</Card>
    <Card>Current Balance</Card>
    <Card>Total P&L</Card>
    <Card>Return %</Card>
  </PerformanceCards>

  <PlaceholderPanel>
    "Detailed Analysis Coming Soon"
    - Transition timeline
    - Signal breakdown
    - Chart with markers
    - Per-trade analysis
  </PlaceholderPanel>
</Box>
```

---

## Navigation Integration

**File:** `frontend/src/components/layout/Layout.tsx`

**Menu Item:**
```typescript
{
  text: 'Session History',
  icon: <HistoryIcon />,
  path: '/session-history',
  description: 'Review past trading sessions and performance'
}
```

**Position:** After "Backtesting", before "Data Collection"

---

## Future Work (Backlog)

See `docs/UI_BACKLOG.md` - Tasks SH-03 through SH-07:

- **SH-03:** Summary stats (S1 count, Z1 count, accuracy)
- **SH-04:** Transition timeline visualization
- **SH-05:** Expandable transition details (indicator values)
- **SH-06:** Chart with S1/Z1/ZE1 markers
- **SH-07:** Per-trade breakdown table

**Dependency:** Backend transition history persistence (EventBus → QuestDB)

---

## Troubleshooting

### "No sessions found"
- Check backend is running: `curl http://localhost:8080/api/paper-trading/sessions`
- Create a session via Dashboard
- Click refresh button on Session History page

### Session detail shows "Not found"
- Verify session_id exists in database
- Check browser DevTools console for API errors
- Ensure backend route is registered

### Filters not working
- Check backend supports `?status=` and `?strategy_id=` query params
- Verify filter state updates on dropdown change
- Check URL query params in browser DevTools Network tab

---

## Code Quality

- **TypeScript:** Full type safety, no `any` types
- **Error Handling:** Try-catch blocks, user-friendly error messages
- **Loading States:** CircularProgress during data fetch
- **Responsive:** MUI Grid system, works on mobile/desktop
- **Accessibility:** Icon tooltips, semantic HTML, keyboard navigation
- **Performance:** Efficient re-renders, cleanup in useEffect
- **Code Style:** Follows existing Dashboard patterns, ESLint compliant

---

**Last Updated:** 2025-12-06
**Author:** Frontend Developer Agent
**Review Status:** Ready for QA
