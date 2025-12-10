# UI BACKLOG - FXcrypto Pump/Dump Detection

**Wersja:** 4.32 | **Data:** 2025-12-07

**Cel systemu:** Wykrywanie pump/dump i shortowanie na szczycie pumpu

**Filozofia:** STATE MACHINE CENTRIC DESIGN - wszystko w UI musi wspierać:
1. Konfigurację state machine (Strategy Builder)
2. Obserwację state machine w czasie rzeczywistym (Dashboard)
3. Analizę historii state machine (Session History)

**Powiązane dokumenty:**
- `docs/UI_INTERFACE_SPECIFICATION.md` - Pełny opis interfejsu i architektury systemu

---

## JAK UŻYWAĆ TEGO DOKUMENTU

### Dla Driver/frontend-dev:
1. Wybierz zadanie z najwyższym priorytetem (CRITICAL → HIGH → MEDIUM → LOW)
2. Zaimplementuj funkcję
3. Zaktualizuj status na `DONE` i dodaj datę
4. Zaktualizuj `UI_INTERFACE_SPECIFICATION.md`

### Priorytety:
| Priorytet | Znaczenie |
|-----------|-----------|
| CRITICAL | Bez tego trader NIE WIDZI co robi state machine |
| HIGH | Znacząco utrudnia konfigurację lub monitoring |
| MEDIUM | Ułatwia pracę, ale można obejść |
| LOW | Nice to have |

---

## CRITICAL - STATE MACHINE VISIBILITY

**Bez tych funkcji trader NIE WIE co robi system!**

### FAZA 2: LIVE MONITORING (Dashboard)

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| SM-01 | **State overview table** | Tabela: Strategy × Symbol × STAN × Since | ✅ DONE (2025-12-06) |
| SM-02 | **Current state display** | Duży badge: MONITORING / SIGNAL_DETECTED / POSITION_ACTIVE | ✅ DONE (2025-12-06) |
| SM-03 | **Condition progress** | Które warunki Z1/ZE1/E1 spełnione ✅, które pending ❌ | ✅ DONE (2025-12-06) |
| SM-04 | **Transition log** | Lista: timestamp → from_state → to_state → trigger values | ✅ DONE (2025-12-06) |
| SM-05 | **Chart S1/Z1/ZE1 markers** | Markery na wykresie gdzie pump, peak, dump end | ✅ DONE (2025-12-06) |

### FAZA 2: CHART (Dashboard)

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| CH-01 | **Zoom wykresu** | Scroll wheel lub +/- buttons | ✅ EXISTS (lightweight-charts) |
| CH-02 | **Przewijanie wykresu** | Drag w historię (analiza przeszłych pumpów) | ✅ EXISTS (lightweight-charts) |
| CH-03 | **Entry/SL/TP lines** | Poziome linie pokazujące SHORT pozycję | ✅ DONE (2025-12-06) |

### FAZA 2: POSITION MANAGEMENT (Dashboard)

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| PM-01 | **Position panel** | Entry, current, P&L, SL, TP, leverage, time | ✅ ENHANCED (2025-12-07) |
| PM-02 | **Emergency close** | Szybkie zamknięcie gdy pump kontynuuje | ✅ EXISTS (Close 100% button) |
| PM-03 | **Modify SL/TP** | Przesunięcie stopów | ✅ DONE (2025-12-07) |

### FAZA 3: SESSION HISTORY (NOWA STRONA!)

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| SH-01 | **Session list page** | `/session-history` - lista wszystkich sesji | ✅ DONE (2025-12-06) |
| SH-02 | **Session detail page** | `/session-history/[id]` - szczegóły sesji | ✅ DONE (2025-12-07) |
| SH-03 | **Summary stats** | S1 count, Z1 count, O1 count, E1 count, accuracy | ✅ DONE (2025-12-06) |
| SH-04 | **Transition timeline** | Wizualna oś czasu z przejściami | ✅ DONE (2025-12-06) |
| SH-05 | **Transition details** | Expandable: jakie wartości miały wskaźniki | ✅ DONE (2025-12-06) |
| SH-06 | **Chart with markers** | Wykres z zaznaczonymi S1/Z1/ZE1 | ✅ DONE (2025-12-07) |
| SH-07 | **Per-trade breakdown** | Tabela: każdy trade osobno z P&L | ✅ DONE (2025-12-06) |

---

## HIGH - KONFIGURACJA I UNDERSTANDING

**Bez tych funkcji trader nie wie JAK skonfigurować system poprawnie.**

### FAZA 1: STRATEGY BUILDER

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| SB-01 | **State machine diagram** | Wizualizacja: MONITORING → S1 → Z1 → ZE1/E1 | ✅ DONE (2025-12-06) |
| SB-02 | **Quick backtest** | Ile S1, Z1, O1, E1 by wygenerowała strategia | ✅ DONE (2025-12-07) |
| SB-03 | **"Where would S1 trigger"** | Zaznacz na wykresie gdzie byłyby sygnały | ✅ DONE (2025-12-07) |
| SB-04 | **Variant tooltips** | Tooltip: "PumpFast" = t1=5s, t3=30s, d=15s | ✅ DONE (2025-12-06) |

### FAZA 1: INDICATOR VARIANTS

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| IV-01 | **Preview on chart** | Wykres: jak wariant reaguje na historyczne pumpy | ✅ DONE (2025-12-07) |
| IV-02 | **Compare variants** | Fast vs Medium na tym samym wykresie | ✅ DONE (2025-12-06) |
| IV-03 | **Parameter docs** | Co robi t1, t3, d? Jaki efekt ma zmiana? | ✅ DONE (2025-12-06) |
| IV-04 | **Signal count test** | Ile S1 wygenerowałby wariant w 24h | ✅ DONE (2025-12-07) |

### FAZA 2: TRADING SESSION

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| TS-01 | **Strategy preview** | Po zaznaczeniu: pokaż warunki S1, Z1, ZE1 | ✅ ENHANCED (2025-12-07) |
| TS-02 | **Session matrix** | Tabela: strategia × symbol = X instancji | ✅ DONE (2025-12-06) |
| TS-03 | **Symbol recommendation** | "SOL_USDT ma wysoki volume - dobry dla pump" | ✅ DONE (2025-12-06) |

### FAZA 2: DASHBOARD - PUMP INDICATORS

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| PI-01 | **Real-time pump values** | PUMP_MAGNITUDE, VELOCITY jako duże liczby | ✅ DONE (2025-12-06) |
| PI-02 | **Velocity trend** | Strzałka: pump przyspiesza ↑ / zwalnia ↓ | ✅ DONE (2025-12-06) |
| PI-03 | **Pump subplot** | Wykres wskaźników pump pod main chart | ✅ DONE (2025-12-06) |

---

## MEDIUM - ULEPSZENIA UX

### DATA COLLECTION

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| DC-01 | Download danych | Eksport do CSV | ✅ DONE (2025-12-06) |
| DC-02 | Pump history marking | Oznacz gdzie były historyczne pumpy | ✅ DONE (2025-12-07) |
| DC-03 | Data quality indicator | Wskaźnik luk w danych | ✅ DONE (2025-12-06) |

### MARKET SCANNER

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| MS-01 | Mini-wykres w tabeli | Sparkline przy każdym symbolu | ✅ DONE (2025-12-06) |
| MS-02 | Signal history | Co się działo z tym symbolem ostatnio | ✅ DONE (2025-12-06) |
| MS-03 | Panel szczegółów | Po kliknięciu wiersza - szczegóły | ✅ DONE (2025-12-06) |

### STRATEGY BUILDER

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| SB-05 | Complex conditions | (A AND B) OR C | ✅ DONE (2025-12-06) |
| SB-06 | Import/export | JSON export/import strategii | ✅ DONE (2025-12-06) |
| SB-07 | Version history | Historia zmian, rollback | ✅ DONE (2025-12-06) |

### SETTINGS

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| ST-01 | Default SL/TP | Domyślne wartości | ✅ DONE (2025-12-06) |
| ST-02 | Keyboard shortcuts | Konfiguracja skrótów | ✅ DONE (2025-12-06) |
| ST-03 | Profiles | Różne profile dla różnych stylów | ✅ DONE (2025-12-06) |

---

## LOW - NICE TO HAVE

### DASHBOARD

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| D-01 | Fibonacci retracement | Drawing tool | ✅ DONE (2025-12-06) |
| D-02 | Rectangle zones | Drawing tool | ✅ DONE (2025-12-06) |
| D-03 | Multi-timeframe | 1m/5m/15m/1h toggle | ✅ DONE (2025-12-06) |

### SESSION HISTORY

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| SH-08 | Replay mode | Odtworzenie sesji krok po kroku | ✅ DONE (2025-12-06) |
| SH-09 | Export report | PDF/CSV raport sesji | ✅ DONE (2025-12-06) |

### SYSTEM

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| SY-01 | Keyboard shortcuts | ESC=stop, C=close, D=dashboard, etc. | ✅ DONE (2025-12-06) |
| SY-02 | Backup/restore | Export/import wszystkich ustawień | ✅ DONE (2025-12-06) |

---

## KEYBOARD SHORTCUTS (do zaimplementowania)

| Skrót | Funkcja | Priorytet |
|-------|---------|-----------|
| ESC | Emergency Stop All | HIGH |
| C | Close current position | HIGH |
| D | Go to Dashboard | MEDIUM |
| T | Go to Trading Session | MEDIUM |
| S | Go to Session History | MEDIUM |
| +/- | Zoom chart | MEDIUM |
| ←→ | Scroll chart | MEDIUM |
| 1-9 | Switch symbols in watchlist | LOW |
| F | Full screen chart | LOW |

---

## BACKEND REQUIREMENTS (dla state machine visibility)

Żeby UI mogło pokazywać state machine, backend MUSI dostarczać:

| Endpoint | Dane | Status |
|----------|------|--------|
| GET /api/sessions/{id}/state | Aktualny stan każdej instancji | ✅ DONE (2025-12-06) |
| GET /api/sessions/{id}/transitions | Lista przejść z wartościami | ✅ DONE (placeholder) |
| GET /api/sessions/{id}/conditions | Aktualny progress warunków S1/O1/Z1/ZE1/E1 | ✅ DONE (2025-12-06) |
| WS /ws | Real-time events (subscription model) | ✅ EXISTS |
| POST /api/sessions/{id}/stop | Emergency stop session | ✅ EXISTS |

---

## STATYSTYKI BACKLOGU

| Priorytet | Liczba | Zrobione |
|-----------|--------|----------|
| CRITICAL | 17 | 17 |
| HIGH | 14 | 14 |
| MEDIUM | 13 | 13 |
| LOW | 6 | 6 |
| **RAZEM** | **50** | **50** |

### Rozkład według faz

| Faza | CRITICAL | HIGH | MEDIUM | LOW |
|------|----------|------|--------|-----|
| Faza 1: Konfiguracja | 0 | 8 (8 done) | 3 | 0 |
| Faza 2: Monitoring | 10 (10 done) | 6 (6 done) | 4 | 3 |
| Faza 3: Analiza | 7 (7 done) | 0 | 0 | 2 |
| System | 0 | 0 | 6 | 1 |

---

## CHANGELOG

### v4.32 (2025-12-07)
- **PM-03: Modify SL/TP COMPLETE ✅** (FINAL TASK - 100% COMPLETE!)
  - **Backend:**
    - Added `PATCH /api/trading/positions/{position_id}/sl-tp` endpoint
    - Validates SL/TP values relative to entry price and position side
    - Updates position in QuestDB live_positions table
  - **Frontend:**
    - Edit button in ActivePositionBanner SL/TP section
    - Dialog with:
      - Symbol, side, entry price display
      - Stop Loss input with validation helper text
      - Take Profit input with validation helper text
      - Error display for invalid values
      - Save/Cancel actions
    - Client-side validation before API call
    - Real-time position refresh after update
  - **Trader value:**
    - "My SL is too tight" → click Edit → adjust → Save
    - "Price moved, need to trail TP" → click Edit → adjust → Save
    - No need to close and re-enter position to change stops
  - **Files changed:**
    - `src/api/trading_routes.py` - Added PATCH endpoint
    - `frontend/src/components/dashboard/ActivePositionBanner.tsx` - Added edit UI
  - **Statistics:** ALL 50/50 tasks complete (100%)

### v4.31 (2025-12-07)
- **SH-02: Session Detail Page COMPLETE ✅** (updated from PLACEHOLDER)
  - Session Detail page now has full functionality:
    - Tab 0: Statistics (SH-03) - Signal counts, accuracy metrics
    - Tab 1: Chart (SH-06) - Price chart with S1/Z1/ZE1/E1 markers
    - Tab 2: Timeline (SH-04) - Visual transition timeline
    - Tab 3: Details (SH-05) - Expandable transition details with indicator values
    - Tab 4: Trades (SH-07) - Per-trade breakdown table
    - Tab 5: Replay (SH-08) - Session replay mode
  - All sub-features implemented - marking as DONE
  - Updated statistics: CRITICAL 16/17, total 49/50 (98%)

- **TS-01: Strategy Preview ENHANCED ✅** (STATE MACHINE VISIBILITY)
  - Added State Machine Diagram to Trading Session page
  - **Problem solved:**
    - Trader selected strategies without visual understanding of state flow
    - Strategy Preview showed conditions but not HOW states connect
    - Missing visual context for S1 → Z1 → ZE1/E1 flow
  - **Solution:**
    - Side-by-side layout: State Machine Diagram + Strategy Conditions
    - Diagram shows all states: MONITORING → SIGNAL_DETECTED → POSITION_ACTIVE → MONITORING
    - Transitions labeled with state machine signals (S1, Z1, O1, ZE1, E1)
  - **Features:**
    - Visual flow diagram with color-coded states
    - Legend explaining each transition:
      - S1 = Pump detected (MONITORING → SIGNAL_DETECTED)
      - Z1 = Entry executed (SIGNAL_DETECTED → POSITION_ACTIVE)
      - O1 = Timeout (SIGNAL_DETECTED → MONITORING)
      - ZE1 = Normal exit (POSITION_ACTIVE → MONITORING)
      - E1 = Emergency exit (POSITION_ACTIVE → MONITORING)
    - Grid layout: 5/7 split between diagram and conditions
    - Reuses existing StateMachineDiagram component
  - **Trader value:**
    - "What's the flow of this strategy?" - immediately visible
    - "When does entry happen?" - Z1 transition shown
    - "What triggers exit?" - ZE1/E1 transitions shown
  - Integration: Trading Session page, shown when strategy is selected
  - Location: `/trading-session` page

### v4.30 (2025-12-07)
- **PM-01: Position Panel Visibility ENHANCED ✅** (HIGH priority UX improvement)
  - New `ActivePositionBanner` component for Dashboard
  - **Problem solved:**
    - Position details were hidden in tab (user had to click "Active Positions")
    - Trader could MISS critical P&L changes during position
    - Emergency actions required navigating to hidden tab
  - **Solution:**
    - HIGH VISIBILITY banner appears at TOP of Dashboard when ANY position is open
    - Banner shows IMMEDIATELY - no clicking required
    - Prominent P&L display with color coding (green=profit, red=loss)
    - Quick close button directly in banner
  - **Features:**
    - Total P&L across all positions (MOST IMPORTANT - large, centered)
    - Position count badge with status
    - Low margin warning chips when margin ratio < 25%
    - Expandable details per position:
      - Symbol, Side, Leverage
      - Entry Price, Current Price
      - Unrealized P&L with percentage
      - Margin ratio with progress bar
      - SL/TP/Liquidation prices
      - Time since position opened
    - One-click "Close Position 100%" button
    - "View Details" button to navigate to full position tab
    - Color-coded border (green=profit, red=loss/risk)
  - **STATE MACHINE CONNECTION:**
    - Banner visible when state = POSITION_ACTIVE (after Z1)
    - Banner disappears after ZE1 (Normal Exit) or E1 (Emergency Exit)
    - Trader sees EXACTLY when in position vs monitoring
  - **Trader value:**
    - "Am I in a position?" - immediately visible (banner appears/disappears)
    - "What's my P&L?" - large number at top
    - "Should I emergency close?" - button right there
    - "How long have I been in?" - time display
  - Location: `frontend/src/components/dashboard/ActivePositionBanner.tsx`
  - Integration: Dashboard page, after State Overview table

### v4.29 (2025-12-07)
- **SH-06: Session Chart with Markers COMPLETE ✅** (CRITICAL for trader analysis)
  - New `SessionChartWithMarkers` component for Session History detail page
  - **Why CRITICAL:**
    - Trader MUST see WHERE on price chart the pump was detected (S1)
    - Trader MUST see WHERE short position was entered (Z1)
    - Trader MUST see WHERE position was closed (ZE1/E1/O1)
    - Without this, trader cannot correlate PRICE with DECISION
  - **Features:**
    - OHLCV candlestick chart with historical session data
    - State machine transition markers:
      - ▲ S1 (orange triangle) = Pump detected
      - ● Z1 (green circle) = Entry executed
      - ■ ZE1 (blue square) = Normal exit (dump end)
      - ◆ E1 (red diamond) = Emergency exit
      - ✕ O1 (gray X) = Signal cancelled/timeout
    - Position zones (green/red shading between Z1 and exit)
    - P&L annotation at exit points (+X.X% or -X.X%)
    - Zoom and scroll controls
    - Click-to-expand marker details dialog:
      - Transition time, price, state change
      - Conditions that were met (with values vs thresholds)
      - Position entry/exit prices and P&L
    - Mock data fallback for development
  - **Integration:**
    - Added as new "Chart" tab in Session History detail page
    - Tab order: Statistics → Chart → Timeline → Details → Trades → Replay
    - Connected to session OHLCV and transitions API endpoints
  - **Trader value:**
    - "Did I enter at the ACTUAL peak?" - now visually verifiable
    - "Was the pump magnitude correct?" - marker shows percentage
    - "How long was the position open?" - zone shading shows duration
  - Location: `frontend/src/components/session-history/SessionChartWithMarkers.tsx`

### v4.28 (2025-12-07)
- **DC-02: Pump History Marking COMPLETE ✅**
  - New `PumpHistoryMarking` component for Data Collection chart page
  - **Features:**
    - Automatic pump event detection using local minima/maxima algorithm
    - Configurable detection parameters:
      - Min magnitude threshold (default 2%)
      - Min/max duration constraints
      - Lookback window for extrema detection
    - Pump event classification: pump, pump_dump, dump
    - Summary statistics panel:
      - Total pumps detected
      - Maximum magnitude
      - Average magnitude
      - Average pump time
      - Average velocity (%/min)
      - Pump & dump count
    - Detailed pump events table:
      - Type, start time, magnitude, pump time, velocity
      - Start/peak prices
      - Expandable row details with timing, price, and performance metrics
    - Real-time parameter adjustment with sliders
    - Toggle visibility switch
    - Export-ready pump markers (zones and points) for chart integration
  - **Detection Algorithm:**
    - Finds local minima as potential pump starts
    - Finds local maxima after each minimum as peaks
    - Calculates magnitude = (peak - start) / start × 100%
    - Filters by magnitude and duration thresholds
    - Removes overlapping events (keeps higher magnitude)
    - Velocity = magnitude / pumpDuration (in %/min)
  - **Pump Event Data:**
    - Start/peak/end timestamps and prices
    - Pump duration (start → peak)
    - Dump duration (peak → end)
    - Total duration
    - Velocity metric for rapid pump detection
  - **Integration:**
    - Added to Data Collection chart page (`/data-collection/[sessionId]/chart`)
    - Appears after Technical Indicators accordion
    - Connected to processedData for pump detection
    - Exposes `generatePumpMarkers()` helper for chart zone/point overlay
  - Location: `frontend/src/components/data-collection/PumpHistoryMarking.tsx`

### v4.27 (2025-12-07)
- **IV-04: Signal Count Test COMPLETE ✅**
  - New `SignalCountTest` component for Indicators page
  - **Features:**
    - Estimated signal counts for 24h, 7d, 30d periods
    - Per-symbol analysis with volatility adjustment
    - Variant comparison with progress bars
    - Signal frequency calculation based on variant parameters
    - Symbol volatility factors (BTC, ETH, SOL, DOGE, PEPE, XRP, SHIB)
    - Color-coded signal estimates (low=red, medium=yellow, high=green)
    - Expandable symbol details
    - Mock data fallback for development
  - **Signal Frequency Algorithm:**
    - Base frequency: Fast variants (~0.8/hr), Slow variants (~0.2/hr), Medium (~0.4/hr)
    - Threshold factor: Higher thresholds = fewer signals
    - Volatility factor: Symbol-specific multiplier (e.g., SHIB=2.0, BTC=0.8)
    - Formula: signals/hr = baseFrequency × thresholdFactor × volatilityFactor
  - **Metrics Displayed:**
    - Signals per 24h, 7d, 30d
    - Average signals per day
    - Peak hourly estimate
    - Symbol breakdown with individual estimates
  - **Integration:**
    - Added as new "Signal Count Test" tab in Indicators page
    - Auto-loads variants from API or uses mock data
    - Connected to variant selection state
  - Location: `frontend/src/components/indicators/SignalCountTest.tsx`

### v4.26 (2025-12-07)
- **IV-01: Variant Chart Preview COMPLETE ✅**
  - New `VariantChartPreview` component for Indicators page
  - **Features:**
    - SVG-based candlestick chart with OHLCV data visualization
    - Indicator values plotted as overlay/subplot (blue line)
    - Pump events highlighted with orange zones
    - Signal trigger points marked (red dots when threshold crossed)
    - Variant selector dropdown to choose which variant to preview
    - Symbol and timeframe selection (1m, 5m, 15m, 1h)
    - Threshold line showing trigger level
    - Pump detection algorithm based on indicator values
    - Collapsible panel for space efficiency
    - Mock data fallback for development
  - **Chart Elements:**
    - Price candlesticks (green/red coloring)
    - Indicator line chart (blue)
    - Indicator area fill (translucent blue)
    - Pump event zones (orange highlight)
    - Trigger points (red dots)
    - Threshold level (orange dashed line)
    - Zero baseline
  - **Statistics:**
    - Number of pumps detected
    - Number of trigger points
    - Pump accuracy percentage
  - **Interpretation:**
    - Fast variants: quick reaction, more false positives
    - Medium variants: balanced sensitivity
    - Slow variants: filters noise, may miss early signals
  - **Integration:**
    - Added as new "Preview on Chart" tab in Indicators page
    - Auto-loads variants from API or uses mock data
    - Connected to variant selection state
  - Location: `frontend/src/components/indicators/VariantChartPreview.tsx`

### v4.25 (2025-12-07)
- **SB-03: Signal Preview Chart COMPLETE ✅**
  - New `SignalPreviewChart` component for Strategy Builder
  - **Features:**
    - SVG-based candlestick chart with OHLCV data visualization
    - Signal markers showing where S1 (pump detected) would trigger
    - Z1 (entry) and O1 (timeout) prediction based on strategy configuration
    - Mock OHLCV data generation with realistic pump patterns
    - Symbol and timeframe selection (1m, 5m, 15m, 1h)
    - Candlestick rendering with proper open/close coloring
    - Horizontal price grid lines with labels
    - Time axis with formatted labels
    - Signal legend explaining S1/Z1/O1 markers
    - Collapsible panel for space efficiency
    - Pump detection algorithm based on price magnitude over lookback period
    - Threshold adapts to S1 condition count (more conditions = higher threshold)
  - **Signal Flow:**
    - S1 (orange up arrow): Pump detected based on magnitude threshold
    - Z1 (green circle): Entry confirmed - Z1 conditions met
    - O1 (red X): Timeout - Z1 conditions not met within timeout window
  - **Algorithm:**
    - Scans OHLCV data for price movements exceeding threshold
    - Threshold = 2% + (0.5% × S1 condition count)
    - Z1 probability based on Z1 condition count
    - Timeout window based on O1 timeoutSeconds configuration
  - **Integration:**
    - Added to Strategy Builder page below QuickBacktestPreview
    - Auto-generates mock data when strategy has conditions configured
    - Shows signal distribution across simulated historical data
  - Location: `frontend/src/components/strategy/SignalPreviewChart.tsx`

### v4.24 (2025-12-07)
- **SB-02: Quick Backtest Preview COMPLETE ✅**
  - New `QuickBacktestPreview` component for Strategy Builder
  - **Features:**
    - Signal count estimates: S1, Z1, O1, ZE1, E1 based on strategy configuration
    - Performance metrics: Win rate, Avg P&L, Total P&L, Max Drawdown, Sharpe Ratio
    - Entry accuracy: Z1 / S1 - how often pump signals lead to actual entries
    - Exit accuracy: ZE1 / (ZE1 + E1) - how often exits are planned vs emergency
    - Timing stats: Signals per day, avg hold time, time between signals
    - Period selection: 24h, 7d, 30d simulation windows
    - Symbol selection for simulation (BTC, ETH, SOL, DOGE, PEPE)
    - Visual progress bars and color-coded metrics
    - Collapsible panel for space efficiency
    - Interpretation alerts (good/moderate/below breakeven)
    - Mock data fallback for development
  - **Algorithm:**
    - Base signal frequency adjusted by strategy complexity (more conditions = fewer signals)
    - Entry rate based on Z1 conditions and timeouts
    - Exit split based on SL/TP configuration
    - Win rate influenced by trading direction (SHORT favored for pump/dump)
  - **Integration:**
    - Added to Strategy Builder page below StrategyBuilder5Section form
    - Auto-runs when strategy has name and S1 conditions configured
    - "Run Full Backtest" button for future backend integration
  - Location: `frontend/src/components/strategy/QuickBacktestPreview.tsx`

### v4.23 (2025-12-07)
- **TS-03: Symbol Recommendation Panel COMPLETE ✅**
  - New `SymbolRecommendation` component for Trading Session page
  - **Features:**
    - Pump suitability scoring algorithm (0-100 scale)
    - Volume analysis (0-30 points) - higher volume = better liquidity
    - Volatility analysis (0-30 points) - optimal volatility range for pump detection
    - Price movement analysis (0-20 points) - recent movement indicates opportunity
    - Liquidity scoring (0-20 points) - ensures tradability
    - Recommendation levels: Excellent (80-100), Good (60-79), Moderate (40-59), Poor (0-39)
    - Score breakdown with reasons for each component
    - Color-coded progress bars and badges
    - Quick add/remove buttons for selected symbols
    - Expandable details showing scoring factors
    - Mock data fallback for development
  - **Integration:**
    - Added to Trading Session page below Symbol Selection card
    - Only visible in live/paper mode (not backtest)
    - Connected to symbol selection state
    - Shows top 5 recommended symbols by default
  - Location: `frontend/src/components/trading/SymbolRecommendation.tsx`

### v4.22 (2025-12-06)
- **MS-02: Signal History Panel COMPLETE ✅**
  - New `SignalHistoryPanel` component showing recent state machine signals
  - **Features:**
    - Timeline visualization using MUI Timeline components
    - Signal types: S1 (pump detected), Z1 (entry), O1 (timeout), ZE1 (planned exit), E1 (emergency)
    - Color-coded signal badges and timeline dots
    - Expandable panels showing trigger values and notes
    - Outcome indicators (profit/loss/pending/timeout)
    - Time ago formatting ("2h ago", "10m ago")
    - Trade duration display for exit signals
    - Summary chips showing signal type counts
    - Mock data fallback for development
  - **Integration:**
    - Added to Market Scanner symbol details drawer (MS-03 panel)
    - Shows between Signal Strength and Action Buttons sections
    - Loads from `/api/market-scanner/{symbol}/signals` endpoint (with mock fallback)
  - Location: `frontend/src/components/market-scanner/SignalHistoryPanel.tsx`

### v4.21 (2025-12-06)
- **SH-05: Transition Details COMPLETE ✅**
  - New `TransitionDetails` component for expandable transition information
  - **Features:**
    - Accordion-based UI with expandable panels for each transition
    - State machine transition timeline (from → to state)
    - Indicator values at moment of transition
    - Threshold progress bars showing how close indicators were to trigger values
    - Before/after state comparison
    - Color-coded state badges
    - Expand/Collapse all buttons
    - Trigger information (what caused the transition)
    - Mock data fallback for development
  - **Integration:**
    - Added as new "Details" tab in Session Detail page
    - Shows between Timeline and Trades tabs
  - Location: `frontend/src/components/session-history/TransitionDetails.tsx`

### v4.20 (2025-12-06)
- **SH-03: Session Summary Stats COMPLETE ✅**
- **SH-07: Trade Breakdown Table COMPLETE ✅**
  - New `SessionSummaryStats` component for session statistics
  - New `TradeBreakdownTable` component for per-trade analysis
  - **SH-03 Features:**
    - Signal counts: S1 (pump detected), Z1 (entry), O1 (timeout), ZE1 (planned exit), E1 (emergency)
    - Entry accuracy: Z1 / (Z1 + O1) - how often S1 signals result in entry
    - Exit accuracy: ZE1 / (ZE1 + E1) - how often exits are planned vs emergency
    - Win rate and average P&L per trade
    - Total session P&L
    - Progress bars with color-coded accuracy levels
    - Signal flow explanation
    - Mock data fallback for development
  - **SH-07 Features:**
    - Per-trade breakdown table with all trades from session
    - Entry/exit price, P&L, P&L%, duration
    - Exit type indicator (ZE1 planned vs E1 emergency)
    - Sortable columns (time, P&L, P&L%, duration)
    - Expandable row details with triggers
    - Win/loss highlighting
    - Summary chips (total trades, wins, losses, planned exits, total P&L)
    - Mock data fallback for development
  - **Integration:**
    - Session Detail page now has 4 tabs: Statistics, Timeline, Trades, Replay
    - Statistics tab shows SessionSummaryStats component
    - Trades tab shows TradeBreakdownTable component
  - **Locations:**
    - `frontend/src/components/session-history/SessionSummaryStats.tsx`
    - `frontend/src/components/session-history/TradeBreakdownTable.tsx`

### v4.19 (2025-12-06)
- **IV-02: Compare Variants COMPLETE ✅**
  - New `VariantComparison` component for side-by-side variant analysis
  - **Features:**
    - Select 2 variants to compare from dropdown
    - Swap variants button
    - Side-by-side info cards with descriptions
    - Speed category badges (Fast/Medium/Slow)
    - Use case recommendations per category
    - Parameter comparison table with:
      - Values for each variant
      - Highlighted differences
      - Percentage diff for numeric params
      - Same/Different icons
    - Stats chips showing count of same vs different params
    - Trading recommendations based on variant speeds
  - **Integration:**
    - Added as new "Compare Variants" tab in Indicators page
    - Auto-loads variants from API
    - Auto-selects first two variants for comparison
  - Location: `frontend/src/components/indicators/VariantComparison.tsx`

### v4.18 (2025-12-06)
- **SH-04: Transition Timeline COMPLETE ✅**
  - New `TransitionTimeline` component for visual state machine timeline
  - **Features:**
    - MUI Timeline visualization (vertical/horizontal orientation toggle)
    - Color-coded state nodes (MONITORING=blue, SIGNAL_DETECTED=orange, etc.)
    - Expandable node details with trigger values
    - Zoom controls (50%-200%)
    - Time labels and duration display
    - State legend at bottom
    - Click to expand transition details
    - Hover tooltips with transition info
  - **Integration:**
    - Added as new "Timeline" tab in Session Detail page
    - Loads transitions from `/api/sessions/{id}/transitions` endpoint
  - Location: `frontend/src/components/session-history/TransitionTimeline.tsx`

### v4.17 (2025-12-06)
- **SB-07: Version History COMPLETE ✅**
  - New `StrategyVersionHistory` component for strategy change tracking
  - **Features:**
    - Auto-save versions to localStorage
    - View version history list with timestamps
    - Compare versions (side-by-side diff view)
    - Rollback to previous versions
    - Delete individual versions or clear all
    - Manual save with descriptions
    - Keep last N versions (configurable, default 20)
  - **Integration:**
    - Added to StrategyBuilder5Section action buttons area
    - Badge shows version count
    - Restore notification on rollback
  - Location: `frontend/src/components/strategy/StrategyVersionHistory.tsx`

### v4.16 (2025-12-06)
- **SH-08: Session Replay Mode COMPLETE ✅**
  - New `SessionReplayPlayer` component for step-by-step playback
  - **Features:**
    - Play/Pause/Step controls
    - Speed adjustment (0.5x, 1x, 2x, 4x, 8x)
    - Timeline scrubber with progress bar
    - State transition highlights
    - Current state badge display
    - Indicator values at current step
    - Data point details panel
  - **Integration:**
    - Added to Session Detail page as new "Replay Mode" tab
    - Loads OHLCV data and transitions from backend
    - Merges candle data with state transitions
  - Location: `frontend/src/components/session-history/SessionReplayPlayer.tsx`

### v4.15 (2025-12-06)
- **D-01: Fibonacci Retracement COMPLETE ✅**
- **D-02: Rectangle Zones COMPLETE ✅**
  - New `ChartDrawingTools` component with toolbar
  - **Features:**
    - Fibonacci retracement tool with levels: 0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%
    - Color-coded levels (green to red gradient)
    - Rectangle zone tool for support/resistance areas
    - Click & drag drawing on chart
    - Drawing management menu (show/hide, delete)
    - Clear all drawings option
    - Persist drawings to localStorage per symbol
    - Active drawing preview while dragging
    - Crosshair cursor in drawing mode
  - **Overlays:**
    - `FibonacciOverlay` - SVG-based Fibonacci levels rendering
    - `RectangleOverlay` - SVG-based zone rendering with fill and labels
  - **Integration:**
    - Added to CandlestickChart component
    - Mouse event handlers for drawing
    - Price/time coordinate conversion
  - Location: `frontend/src/components/dashboard/ChartDrawingTools.tsx`

### v4.14 (2025-12-06)
- **SY-01: Global Keyboard Shortcuts COMPLETE ✅**
  - New `useKeyboardShortcuts` hook
  - **Features:**
    - ESC: Emergency Stop all trading sessions
    - C: Close current position
    - D: Navigate to Dashboard
    - T: Navigate to Trading Session
    - S: Navigate to Session History
    - +/-: Zoom in/out
    - F: Toggle fullscreen
    - Disabled when typing in input fields
  - Integrated into Layout.tsx for global availability
  - Location: `frontend/src/hooks/useKeyboardShortcuts.ts`

### v4.13 (2025-12-06)
- **MS-03: Symbol Details Panel COMPLETE ✅**
  - Added sliding drawer panel in Market Scanner
  - **Features:**
    - Click any row to open detailed view
    - Large price display with 24h change chip
    - Larger sparkline chart (340x80px)
    - Key metrics grid: Volume 24h, Trend, Volatility, Liquidity
    - Pump/Dump detection section with progress bars
    - Signal strength display
    - Action buttons: Quick Trade, View Chart, Set Alert
  - **UX Improvements:**
    - Cursor pointer on hover
    - Selected row highlighting
    - Responsive width (100% on mobile, 400px on desktop)
  - Location: `frontend/src/app/market-scanner/page.tsx` - Drawer component

### v4.12 (2025-12-06)
- **SB-06: Strategy Import/Export (JSON) COMPLETE ✅**
  - Added Import and Export buttons to Strategy Builder
  - **Features:**
    - Export strategy as JSON file with metadata (version, timestamp, type)
    - Import strategy from JSON file with validation
    - Sanitized filename generation from strategy name
    - Validation of required sections (S1, Z1, O1, E1)
    - Automatic expansion of all sections after import
    - Error handling for invalid files
  - **File format:**
    - `_meta`: Export metadata (version, timestamp, type)
    - `strategy`: Full strategy configuration
    - Includes all 5 sections: S1, Z1, O1, ZE1, E1
  - Location: `frontend/src/components/strategy/StrategyBuilder5Section.tsx`
  - Functions: `handleExportJSON()`, `handleImportJSON()`

### v4.11 (2025-12-06)
- **DC-01: Download Data (CSV Export) COMPLETE ✅**
  - Implemented CSV export functionality for Data Collection sessions
  - **Features:**
    - Fetches price data for all symbols in session via `getChartData` API
    - Generates CSV with columns: timestamp, datetime, symbol, price, volume, bid, ask
    - Browser-side download with proper file naming
    - Progress notification during export
    - Error handling with user feedback
    - Only enabled for completed sessions
  - **File format:**
    - Header row with column names
    - ISO 8601 formatted datetime
    - Unix timestamp for programmatic use
    - One row per data point per symbol
  - Location: `frontend/src/app/data-collection/page.tsx` - `handleDownloadData` function

### v4.10 (2025-12-06)
- **MS-01: Mini Sparkline Charts in Market Scanner COMPLETE ✅**
  - New reusable `MiniSparkline` component for inline SVG charts
  - **Features:**
    - Pure SVG rendering - no external chart libraries
    - Auto-color based on trend (green=up, red=down, gray=neutral)
    - Area fill with gradient
    - Current value marker (dot)
    - Tooltip with price and % change
    - Configurable size, stroke width, color
  - **Integration:**
    - Added to Market Scanner table as new column
    - Price history tracking (last 20 values)
    - Mock data generation on first load based on trend
    - Updates with each refresh
  - Location: `frontend/src/components/charts/MiniSparkline.tsx`

### v4.9 (2025-12-06)
- **TS-02: Session Matrix COMPLETE ✅**
  - New `SessionMatrix` component showing strategy × symbol grid
  - **Features:**
    - Visual matrix showing which combinations are selected
    - Checkmark/X icons for active/inactive cells
    - Total instance count with color-coded chip (green/yellow/red)
    - Row totals (per strategy) and column totals (per symbol)
    - Warning message when instance count > 6 (risk of monitoring overload)
    - Compact mode (summary only) and full mode (complete grid)
    - Tooltips with explanations
  - **Integration:**
    - Added to Trading Session page after Strategy Preview Panel
    - Shows compact mode until both strategies and symbols selected
    - Switches to full matrix when selections made
  - Location: `frontend/src/components/trading/SessionMatrix.tsx`

### v4.8 (2025-12-06)
- **IV-03: Parameter Documentation COMPLETE ✅**
- **SB-04: Variant Tooltips COMPLETE ✅**
  - New `IndicatorParameterDocs` component with comprehensive parameter documentation
  - **Parameter definitions** for t1, t2, t3, d, window, threshold, decay
    - Description explaining purpose
    - Effect of increasing/decreasing values
    - Recommended values for fast/medium/slow configurations
    - Warning thresholds
  - **Variant presets** documented: PumpFast, PumpMedium, PumpSlow, VelocityFast, VelocityMedium
    - Each preset shows exact parameters (t1, t3, d, threshold)
    - Use case descriptions
    - Color-coded chips
  - **Integration points:**
    - `ConditionBlock.tsx`: Parameter chips now show tooltips with full documentation
    - `VariantManager.tsx`: Help icon shows full parameter docs panel
    - `VariantManager.tsx`: Parameter input fields have help tooltips
  - **Components exported:**
    - `PARAMETER_DOCS` - Parameter documentation database
    - `VARIANT_PRESETS` - Preset definitions
    - `ParameterTooltipContent` - Tooltip component for parameters
    - `VariantPresetTooltipContent` - Tooltip component for presets
    - `ParameterDocsPanel` - Full documentation table
    - `VariantChip` - Chip with tooltip for variant presets
  - Location: `frontend/src/components/indicators/IndicatorParameterDocs.tsx`

### v4.7 (2025-12-06)
- **TS-01: Strategy Preview Panel COMPLETE ✅**
  - New `StrategyPreviewPanel` component showing S1/O1/Z1/ZE1/E1 conditions
  - Shows all condition groups when a strategy is selected in Trading Session page
  - Accordion-based UI with color-coded sections matching state machine
  - Each section displays:
    - Condition name and threshold (e.g., PUMP_MAGNITUDE_PCT >= 5.0)
    - AND/OR logic indicator
    - Enabled/disabled status
    - Description text
  - State machine flow summary at bottom
  - Integrated into `/trading-session` page after strategy selection
  - Location: `frontend/src/components/trading/StrategyPreviewPanel.tsx`

### v4.6 (2025-12-06)
- **PI-01/02/03: Pump Indicators Panel COMPLETE ✅**
  - New `PumpIndicatorsPanel` component in Dashboard
  - **PI-01**: Large, prominent PUMP_MAGNITUDE and PRICE_VELOCITY values
    - Color-coded by severity (green → yellow → orange → red)
    - Threshold progress bars showing % of trigger level
    - Glowing effect when above threshold (pump active)
  - **PI-02**: Velocity trend arrows
    - Linear regression-based trend calculation
    - Animated arrows: ↑ accelerating, ↓ decelerating, → stable
    - Tooltip explanations
  - **PI-03**: Mini sparkline charts
    - Last 60 values history
    - SVG-based sparklines under each indicator
    - Area fill showing trend direction
  - Real-time updates via WebSocket + polling fallback
  - Integrated into Dashboard single-view layout
  - Location: `frontend/src/components/dashboard/PumpIndicatorsPanel.tsx`

### v4.5 (2025-12-06)
- **SB-01: State Machine Diagram COMPLETE ✅**
  - Visual SVG-based diagram showing MONITORING → S1 → Z1 → ZE1/E1 flow
  - Interactive tooltips with state/transition descriptions
  - Color-coded states matching StateBadge component
  - Active state highlighting with pulsing animation
  - Legend showing transition types (main flow, timeout, return)
  - Integrated into Strategy Builder page (StrategyBuilder5Section.tsx)
  - Location: `frontend/src/components/strategy/StateMachineDiagram.tsx`
  - Example component: `StateMachineDiagram.example.tsx`
  - Comprehensive README with usage examples
  - Pure SVG implementation (no external diagram libraries)
  - Trader-centric labels (pump/peak/dump, not technical jargon)

### v4.4 (2025-12-06)
- **CH-01/02: Chart Zoom i Przewijanie** - już istnieją w lightweight-charts ✅
- **CH-03: Entry/SL/TP Price Lines COMPLETE ✅**
  - Poziome linie cenowe na wykresie dla aktywnej pozycji
  - Entry: żółta linia przerywana
  - Stop Loss: czerwona linia ciągła
  - Take Profit: zielona linia ciągła
  - Nowy prop `positionLines` w CandlestickChart
- **PM-01/02: Position Panel i Emergency Close** - już istnieją (PositionMonitor.tsx) ✅

### v4.3 (2025-12-06)
- **SH-01: Session History List Page COMPLETE ✅**
  - Nowa strona `/session-history` z tabelą sesji
  - Filtrowanie po status i strategy
  - Kliknięcie wiersza → nawigacja do szczegółów
  - Integracja z `/api/paper-trading/sessions`
  - Dodano link "Session History" w nawigacji (Layout.tsx)
  - Kolory statusów: success/error/warning/info
  - Formatowanie dat i P&L z kolorami
- **SH-02: Session Detail Page PLACEHOLDER ✅**
  - Strona `/session-history/[sessionId]` z podstawowymi info
  - Sekcja "Coming Soon" z listą zaplanowanych funkcji (SH-03 - SH-07)
  - Breadcrumbs nawigacja
  - Summary cards: Initial Balance, Current Balance, P&L, Return %

### v4.2 (2025-12-06)
- SM-05: Chart State Machine Markers COMPLETE ✅
  - Dodano wizualne markery na wykresie candlestick
  - S1 (Signal Detection): Pomarańczowy trójkąt w górę
  - Z1/O1 (Entry): Zielone kółko
  - ZE1 (Close): Niebieski kwadrat
  - E1 (Emergency): Czerwony trójkąt w dół
  - Legenda z tooltip (pokazuje liczbę markerów + wyjaśnienie)
  - Auto-refresh: markery aktualizują się wraz z danymi z `/api/sessions/{id}/transitions`

### v4.1 (2025-12-06)
- Backend: GET /api/sessions/{id}/conditions ✅ - pełna implementacja
- Naprawiono SM integration components - poprawne endpointy:
  - StateOverviewTable.integration.tsx → /api/sessions/{id}/state
  - TransitionLog.integration.tsx → /api/sessions/{id}/transitions
  - ConditionProgress.integration.tsx → /api/sessions/{id}/conditions
- Weryfikacja: Strategy evaluation loop ISTNIEJE (event-driven przez indicator.updated)
- Analiza architektury: session flow, UI-backend communication verified

### v4.0 (2025-12-06)
- **STATE MACHINE VISIBILITY ZAIMPLEMENTOWANA!**
- SM-01: StateOverviewTable - tabela wszystkich instancji ✅
- SM-02: StateBadge - kolorowe badge stanów ✅
- SM-03: ConditionProgress - progress warunków S1/Z1/ZE1/E1 ✅
- SM-04: TransitionLog - historia przejść ✅
- Backend: GET /api/sessions/{id}/state ✅
- Backend: GET /api/sessions/{id}/transitions (placeholder) ✅
- Integracja komponentów w Dashboard page.tsx ✅
- Nowy Tab "State Transitions" w Dashboard ✅

### v3.0 (2025-12-06)
- **MAJOR REFACTOR:** Backlog przeprojektowany pod STATE MACHINE CENTRIC DESIGN
- Nowa struktura: CRITICAL = state machine visibility
- Dodano całą sekcję Session History (NOWA STRONA!) - 7 pozycji CRITICAL
- Dodano Backend Requirements - co API musi dostarczać
- Przenumerowano wszystkie ID dla jasności
- Dodano statystyki według faz

### v2.0 (2025-12-06)
- Restrukturyzacja pod pump/dump workflow
- Dodano kategorie CRITICAL dla pump detection

### v1.0 (2025-12-05)
- Początkowa wersja backlogu
