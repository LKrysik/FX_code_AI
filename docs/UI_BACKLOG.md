# UI BACKLOG - FXcrypto Pump/Dump Detection

**Wersja:** 4.0 | **Data:** 2025-12-06

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
| PM-01 | **Position panel** | Entry, current, P&L, SL, TP, leverage, time | ✅ EXISTS (PositionMonitor.tsx) |
| PM-02 | **Emergency close** | Szybkie zamknięcie gdy pump kontynuuje | ✅ EXISTS (Close 100% button) |
| PM-03 | **Modify SL/TP** | Przesunięcie stopów | TODO (UI ready, backend missing) |

### FAZA 3: SESSION HISTORY (NOWA STRONA!)

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| SH-01 | **Session list page** | `/session-history` - lista wszystkich sesji | ✅ DONE (2025-12-06) |
| SH-02 | **Session detail page** | `/session-history/[id]` - szczegóły sesji | ✅ PLACEHOLDER (2025-12-06) |
| SH-03 | **Summary stats** | S1 count, Z1 count, O1 count, E1 count, accuracy | ✅ DONE (2025-12-06) |
| SH-04 | **Transition timeline** | Wizualna oś czasu z przejściami | ✅ DONE (2025-12-06) |
| SH-05 | **Transition details** | Expandable: jakie wartości miały wskaźniki | ✅ DONE (2025-12-06) |
| SH-06 | **Chart with markers** | Wykres z zaznaczonymi S1/Z1/ZE1 | ✅ DONE (SM-05) |
| SH-07 | **Per-trade breakdown** | Tabela: każdy trade osobno z P&L | ✅ DONE (2025-12-06) |

---

## HIGH - KONFIGURACJA I UNDERSTANDING

**Bez tych funkcji trader nie wie JAK skonfigurować system poprawnie.**

### FAZA 1: STRATEGY BUILDER

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| SB-01 | **State machine diagram** | Wizualizacja: MONITORING → S1 → Z1 → ZE1/E1 | ✅ DONE (2025-12-06) |
| SB-02 | **Quick backtest** | Ile S1, Z1, O1, E1 by wygenerowała strategia | TODO |
| SB-03 | **"Where would S1 trigger"** | Zaznacz na wykresie gdzie byłyby sygnały | TODO |
| SB-04 | **Variant tooltips** | Tooltip: "PumpFast" = t1=5s, t3=30s, d=15s | ✅ DONE (2025-12-06) |

### FAZA 1: INDICATOR VARIANTS

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| IV-01 | **Preview on chart** | Wykres: jak wariant reaguje na historyczne pumpy | TODO |
| IV-02 | **Compare variants** | Fast vs Medium na tym samym wykresie | ✅ DONE (2025-12-06) |
| IV-03 | **Parameter docs** | Co robi t1, t3, d? Jaki efekt ma zmiana? | ✅ DONE (2025-12-06) |
| IV-04 | **Signal count test** | Ile S1 wygenerowałby wariant w 24h | TODO |

### FAZA 2: TRADING SESSION

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| TS-01 | **Strategy preview** | Po zaznaczeniu: pokaż warunki S1, Z1, ZE1 | ✅ DONE (2025-12-06) |
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
| DC-02 | Pump history marking | Oznacz gdzie były historyczne pumpy | TODO |
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
| CRITICAL | 17 | 13 |
| HIGH | 14 | 8 |
| MEDIUM | 13 | 10 |
| LOW | 6 | 6 |
| **RAZEM** | **50** | **38** |

### Rozkład według faz

| Faza | CRITICAL | HIGH | MEDIUM | LOW |
|------|----------|------|--------|-----|
| Faza 1: Konfiguracja | 0 | 8 (3 done) | 3 | 0 |
| Faza 2: Monitoring | 10 | 6 (5 done) | 4 | 3 |
| Faza 3: Analiza | 7 (6 done) | 0 | 0 | 2 |
| System | 0 | 0 | 6 | 1 |

---

## CHANGELOG

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
