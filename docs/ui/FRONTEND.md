# Dokumentacja Techniczna Frontendu - Pełna Dokumentacja UI

**Cel dokumentu:** Stworzenie szczegółowego, technicznego opisu architektury, komponentów, stron, funkcji i akcji aplikacji frontendowej. Dokument ten jest generowany na podstawie analizy kodu źródłowego i ma służyć jako "jedno źródło prawdy" dla deweloperów.

**Data ostatniej aktualizacji:** 2025-09-29

**Zakres:** Pełna dokumentacja UI obejmująca wszystkie strony, komponenty, funkcje, akcje, hooks, services i stores aplikacji tradingowej.

---

## 1. Architektura Ogólna

Aplikacja frontendowa jest zbudowana w oparciu o **Next.js 14** z **App Router**, co oznacza architekturę opartą na komponentach serwerowych i klienckich. Za warstwę wizualną odpowiada biblioteka **Material-UI (MUI)**, a za zarządzanie stanem globalnym **Zustand**.

### 1.1. Struktura Katalogów

```
frontend/src/
├── app/                    # Next.js App Router - strony aplikacji
│   ├── layout.tsx         # Główny layout aplikacji
│   ├── page.tsx           # Główny dashboard (PumpDumpDashboard)
│   ├── trading/           # Strona zarządzania tradingiem
│   ├── strategy-builder/  # Wizualny edytor strategii
│   ├── backtesting/       # Backtesting strategii
│   ├── data-collection/   # Zbieranie danych rynkowych
│   ├── indicators/        # Zarządzanie wskaźnikami
│   ├── settings/          # Ustawienia aplikacji
│   └── strategies/        # Lista strategii
├── components/            # Reużywalne komponenty
│   ├── auth/             # Komponenty autoryzacji
│   ├── canvas/           # Komponenty płótna (strategy builder)
│   ├── common/           # Wspólne komponenty
│   ├── dashboard/        # Komponenty dashboardu
│   ├── layout/           # Komponenty layoutu
│   └── theme/            # Komponenty tematyczne
├── hooks/                # Niestandardowe hooks
├── providers/            # React providers
├── services/             # Serwisy API i WebSocket
├── stores/               # Zustand stores
├── types/                # TypeScript types
└── utils/                # Narzędzia pomocnicze
```

### 1.2. Routing Aplikacji

Aplikacja używa Next.js App Router z następującymi trasami:

- `/` - Główny dashboard (PumpDumpDashboard)
- `/trading` - Zarządzanie sesjami tradingowymi
- `/strategy-builder` - Wizualny edytor strategii
- `/backtesting` - Backtesting strategii na danych historycznych
- `/data-collection` - Zbieranie danych rynkowych
- `/indicators` - Zarządzanie wskaźnikami technicznymi
- `/settings` - Ustawienia aplikacji
- `/strategies` - Lista strategii

### 1.3. Zarządzanie Stanem

Aplikacja używa **Zustand** do zarządzania stanem globalnym:

- **authStore**: Stan autoryzacji, tokeny, logowanie/wylogowanie
- **dashboardStore**: Dane dashboardu, market data, sygnały, wskaźniki
- **graphStore**: Stan grafu strategii w strategy builder
- **healthStore**: Status zdrowia systemu
- **tradingStore**: Stan tradingu, sesje, wyniki
- **uiStore**: Stan UI, dialogi, powiadomienia, ładowanie
- **websocketStore**: Stan połączenia WebSocket, statystyki

---

## 2. Komponenty Aplikacji

### 2.1. Komponenty Wspólne (components/common/)

- **ErrorBoundary.tsx**: Komponent do obsługi błędów aplikacji z szczegółami błędu i przyciskami akcji
- **LoadingStates.tsx**: Komponenty ładowania - LoadingSpinner, DataStatusIndicator, SkeletonLoader, TableSkeleton, ProgressBar, ErrorAlert
- **SystemStatusIndicator.tsx**: Wskaźnik statusu systemu z opcjonalnymi szczegółami
- **NotificationProvider.tsx**: Provider dla powiadomień systemowych

### 2.2. Komponenty Autoryzacji (components/auth/)

- **AuthGuard.tsx**: Ochrona tras wymagających autoryzacji
- **LoginForm.tsx**: Formularz logowania
- **UserMenu.tsx**: Menu użytkownika z opcjami wylogowania

### 2.3. Komponenty Canvas (components/canvas/)

- **DataSourceNode.tsx**: Węzeł źródła danych w strategy builder
- **IndicatorNode.tsx**: Węzeł wskaźnika technicznego
- **ConditionNode.tsx**: Węzeł warunku logicznego
- **ActionNode.tsx**: Węzeł akcji (buy/sell/alert)

### 2.4. Komponenty Dashboard (components/dashboard/)

- **TradingDashboardNew.tsx**: Główny dashboard tradingowy

### 2.5. Komponenty Layout (components/layout/)

- **Layout.tsx**: Główny layout aplikacji z nawigacją

### 2.6. Komponenty Tematyczne (components/theme/)

- **ThemeProvider.tsx**: Provider motywu aplikacji

---

## 3. Hooks Niestandardowe

- **useFinancialSafety.ts**: Hook bezpieczeństwa finansowego
- **usePerformanceMonitor.ts**: Monitorowanie wydajności aplikacji
- **useSmartCache.ts**: Inteligentne cachowanie danych
- **useVisibilityAwareInterval.ts**: Interwały zależne od widoczności karty przeglądarki

---

## 4. Serwisy

- **api.ts**: Główny serwis API dla REST calls
- **authService.ts**: Serwis autoryzacji
- **globalHealthService.ts**: Serwis zdrowia systemu
- **strategyBuilderApi.ts**: API dla strategy builder
- **websocket.ts**: Serwis WebSocket

---

## 5. Strony Aplikacji i Ich Funkcje

### 5.1. Główny Dashboard (`/`)

**Plik:** `app/page.tsx` (ładowanie dynamiczne PumpDumpDashboard)

**Opis:** Główna strona aplikacji z przeglądem rynku, sygnałami i szybkimi akcjami.

**Funkcje i Akcje:**

- **Wyświetlanie danych rynkowych**: Tabela z symbolami, cenami, zmianami, wskaźnikami pump/dump
- **Sygnały aktywne**: Lista bieżących sygnałów tradingowych z ID, symbolem, typem, siłą
- **Statystyki portfela**: Bilans, P&L, timestampy aktualizacji
- **Szybkie akcje** (Grid container spacing={3} z 6 przyciskami):
  - **Start Pump Scanner** (Button):
    - variant: "outlined"
    - color: "primary"
    - startIcon: FlashIcon
    - onClick: handleStartPumpScanner
    - fullWidth: true
  - **Quick Trade Setup** (Button):
    - variant: "outlined"
    - color: "secondary"
    - startIcon: TrendingUpIcon
    - onClick: handleQuickTradeSetup
    - fullWidth: true
  - **Risk Management** (Button):
    - variant: "outlined"
    - color: "warning"
    - startIcon: SecurityIcon
    - onClick: handleRiskManagement
    - fullWidth: true
  - **Performance Report** (Button):
    - variant: "outlined"
    - color: "info"
    - startIcon: AssessmentIcon
    - onClick: handlePerformanceReport
    - fullWidth: true
  - **Start Backtest** (Button):
    - variant: "outlined"
    - color: "success"
    - startIcon: PlayArrowIcon
    - onClick: handleStartBacktest
    - fullWidth: true
  - **Start Data Collection** (Button):
    - variant: "outlined"
    - color: "error"
    - startIcon: StorageIcon
    - onClick: handleStartDataCollection
    - fullWidth: true
- **Akcje na symbole** (w tabeli marketData):
  - **Quick Trade** (IconButton):
    - size: "small"
    - color: "success"
    - onClick: handleQuickTrade(symbol)
    - Tooltip: "Trade"
  - **Monitor Symbol** (IconButton):
    - size: "small"
    - color: "info"
    - onClick: handleMonitorSymbol(symbol)
    - Tooltip: "Monitor"

**Komponenty używane:** PumpDumpDashboard.tsx, Material-UI Grid, Card, Button, Table, Alert

**Ustawienia i Parametry:**
- Brak konfigurowalnych ustawień na tej stronie
- Dane odświeżane automatycznie przez WebSocket

### 5.2. Trading (`/trading`)

**Plik:** `app/trading/page.tsx`

**Opis:** Zarządzanie sesjami tradingowymi - live/paper trading.

**Funkcje i Akcje:**

- **Przyciski główne**:
  - **Refresh**: Odświeżenie danych sesji
  - **Start New Session**: Otwiera dialog tworzenia nowej sesji
  - **Stop Session**: Zatrzymuje aktywną sesję (tylko gdy sesja jest uruchomiona)

- **Wyświetlanie sesji**: Tabela (TableContainer + Table) z kolumnami:
  - **Session ID** (TableCell): Typography variant="body2" fontWeight="bold", maxWidth=120, wordBreak="break-all"
  - **Status** (TableCell): Chip z getSessionStatusColor(status), icon=getSessionStatusIcon(status)
  - **Symbols** (TableCell): Box z Chip'ami dla każdego symbolu, flexWrap, size="small", variant="outlined"
  - **Date Range** (TableCell): Typography "start_date to end_date", whiteSpace="nowrap"
  - **Strategy** (TableCell): Chip label="strategy_name", size="small", color="primary", variant="outlined"
  - **Trades** (TableCell align="right"): total_trades
  - **Win Rate** (TableCell align="right"): win_rate.toFixed(1) + "%"
  - **P&L** (TableCell align="right"): Typography z kolorem getPerformanceStatusColor(total_pnl), fontWeight="bold", "$" + total_pnl.toFixed(2)
  - **Max DD** (TableCell align="right"): Typography color="error.main", max_drawdown.toFixed(1) + "%"
  - **Actions** (TableCell): View Results (Tooltip + IconButton AssessmentIcon)
- **Statystyki** (Grid container spacing={3} sx={{ mb: 3 }}):
  - **Active Sessions** (Card):
    - Icon: PlayIcon color="primary"
    - Title: "Active Sessions"
    - Value: sessions.filter(s => s.status === 'running' || s.status === 'active').length
    - Color: primary
  - **Total Signals** (Card):
    - Icon: AssessmentIcon color="secondary"
    - Title: "Total Signals"
    - Value: activeSession?.total_signals || 0
    - Color: secondary
  - **Win Rate** (Card):
    - Icon: TrendingUpIcon color="success"
    - Title: "Win Rate"
    - Value: activeSession?.win_rate ? `${activeSession.win_rate.toFixed(1)}%` : '0%'
    - Color: success
  - **Total P&L** (Card):
    - Icon: TrendingUpIcon color={activeSession?.total_pnl >= 0 ? 'success' : 'error'}
    - Title: "Total P&L"
    - Value: `$${activeSession?.total_pnl ? activeSession.total_pnl.toFixed(2) : '0.00'}`
    - Color: activeSession?.total_pnl >= 0 ? 'success' : 'error'

- **Szczegóły sesji**: Akordeon z informacjami:
  - Session Type: paper/live
  - Status: running/completed/error
  - Symbols: Lista monitorowanych symboli
  - Active Strategies: Lista uruchomionych strategii
  - Start Time: Czas rozpoczęcia
  - Total Trades: Liczba transakcji

- **Start nowej sesji** (Dialog "Start New Trading Session"):
  - **Tytuł dialogu**: "Start New Trading Session"
  - **Pole Session Type** (FormControl + Select):
    - Label: "Session Type"
    - InputLabelProps: { shrink: true }
    - Opcje (MenuItem):
      - "Paper Trading (Virtual)" (value: "paper")
      - "Live Trading (Real Money)" (value: "live")
      - "Backtesting (Historical)" (value: "backtest")
    - Domyślna wartość: "paper"
    - onChange: setSessionForm(prev => ({ ...prev, session_type: e.target.value }))
  - **Pole Symbols** (FormControl + Select multiple):
    - Label: "Symbols"
    - InputLabelProps: { shrink: true }
    - Opcje: "BTC_USDT", "ETH_USDT", "ADA_USDT", "SOL_USDT", "DOT_USDT"
    - Domyślna wartość: ["BTC_USDT"]
    - RenderValue: (selected) => (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
          {selected.map((value) => (
            <Chip key={value} label={value} size="small" />
          ))}
        </Box>
      )
    - onChange: setSessionForm(prev => ({
        ...prev,
        symbols: typeof e.target.value === 'string' ? [e.target.value] : e.target.value
      }))
  - **Pole Global Budget Cap** (TextField):
    - Label: "Global Budget Cap (USD)"
    - Type: "number"
    - Domyślna wartość: 1000
    - HelperText: "Maximum total budget for this session"
    - onChange: setSessionForm(prev => ({
        ...prev,
        config: {
          ...prev.config,
          budget: {
            ...prev.config.budget,
            global_cap: parseFloat(e.target.value) || 1000
          }
        }
      }))
  - **Alert Info** (Alert severity="info"):
    - Icon: InfoIcon
    - Title: brak
    - Content: "Paper Trading: Virtual money, no real trades - perfect for testing strategies\nLive Trading: Real money trades on exchange - use with caution\nFor historical backtesting, use the dedicated Backtesting tab"
  - **Przyciski** (DialogActions):
    - "Cancel" - variant="text", onClick: () => setDialogOpen(false)
    - "Start Session" - variant="contained", color="success", onClick: handleCreateSession
  - **Stan formularza**: sessionForm w useState z wartościami domyślnymi
  - **Walidacja**: Brak widocznej walidacji w kodzie, ale przycisk zawsze aktywny
  - **Źródło danych**: Symbole są hardkodowane w commonSymbols

- **Stop sesji**: Zatrzymanie aktywnej sesji z potwierdzeniem

- **System status**: Wskaźnik zdrowia systemu z opcjonalnymi szczegółami

**Komponenty używane:** Material-UI Table, Dialog, FormControl, Select, TextField, Chip, Alert, Accordion

**Ustawienia i Parametry:**
- Auto-refresh co 30 sekund (pauza gdy karta ukryta)
- Idempotent session start (bezpieczne ponowne uruchomienie)
- Walidacja: wymagane symbole, opcjonalny budżet

### 5.3. Strategy Builder (`/strategy-builder`) (Updated per use1.md)

**Plik:** `app/strategy-builder/page.tsx`

**Opis:** Formularz tworzenia strategii tradingowych z 4 sekcjami (S1/Z1/O1/Emergency) - podejście uproszczone zamiast ReactFlow.

**Funkcje i Akcje:**

- **Górny pasek narzędzi**:
  - **Strategy Name**: Pole tekstowe do edycji nazwy strategii z walidacją unikalności
  - **Validate Strategy**: Przycisk walidacji wszystkich 4 sekcji z szczegółowymi błędami/ostrzeżeniami
  - **Save Strategy**: Przycisk zapisu strategii z walidacją
  - **Load Strategy**: Lista zapisanych strategii z opisami
  - **Save & Run Backtest**: Przycisk bezpośredniego przejścia do backtestu

- **Sekcja 1: SIGNAL DETECTION (S1)**:
  - **Opis**: Definiuje warunki otwarcia sygnału (lock symbol dla analizy)
  - **Conditions (AND logic)**: Lista warunków które muszą być spełnione jednocześnie
  - **Dodawanie warunków**: [+ Add Condition] z wyborem wskaźnika, operatora, wartości
  - **Wskaźniki**: Tylko typu "Ogólny" i "Ryzyko" (nie Cena/Stop Loss/Take Profit)

- **Sekcja 2: ORDER ENTRY (Z1)**:
  - **Opis**: Definiuje warunki złożenia zlecenia po wykryciu sygnału S1
  - **Entry Conditions (AND logic)**: Warunki wykonania zlecenia
  - **Order Configuration**:
    - **Price Calculation**: Wybór wskaźnika typu "Cena zlecenia"
    - **Stop Loss**: Opcjonalny z wyborem wskaźnika typu "Stop Loss"
    - **Take Profit**: Wymagany z wyborem wskaźnika typu "Take Profit"
    - **Position Size**: Fixed amount lub Percentage of balance
    - **Max Slippage**: Limit poślizgu ceny

- **Sekcja 3: SIGNAL CANCELLATION (O1)**:
  - **Opis**: Definiuje warunki anulowania sygnału bez składania zlecenia
  - **Timeout**: Automatyczne anulowanie po X sekundach
  - **OR Custom Conditions**: Warunki anulowania (logika OR)

- **Sekcja 4: EMERGENCY EXIT**:
  - **Opis**: Najwyższy priorytet - natychmiastowe wyjście z pozycji
  - **Emergency Conditions**: Warunki emergency (logika OR)
  - **Cooldown**: Czas blokady strategii po emergency
  - **Actions**: Cancel pending orders, Close positions, Log event

**Komponenty używane:** Material-UI Accordion, TextField, Select, FormControl, Button, Alert, Snackbar

**Ustawienia i Parametry:**
- Sekcje rozwijane/zwijane (accordion) z walidacją każdej sekcji
- Lista wskaźników ładowana z backend z kategoriami i opisami
- Real-time walidacja nazw strategii
- Export strategii jako JSON/YAML
- Maksymalnie 1 strategia aktywna na symbol (globalny limit slotów)

### 5.4. Backtesting (`/backtesting`) (Updated per use1.md)

**Plik:** `app/backtesting/page.tsx`

**Opis:** Szczegółowe testowanie strategii z zapisem wartości wskaźników i analizą wykresową.

**Funkcje i Akcje:**

- **Konfiguracja backtestu** (Dialog "Configure Backtest"):
  - **Data Source**: Wybór sesji zbierania danych
  - **Symbols**: Wybór symboli z dostępnymi danymi
  - **Strategy**: Wybór strategii do testowania
  - **Speed Multiplier**: 1x-100x (10x domyślnie)
  - **Budget**: Początkowy budżet
  - **Analysis Options**: Checkboxy dla szczegółowej analizy

- **Wykonanie backtestu** (Progress View):
  - Live progress z czasem wirtualnym
  - Statystyki w czasie rzeczywistym
  - Możliwość przerwania

- **Wyniki - Główny przegląd** (Results Overview):
  - **Performance Summary**: Final balance, return %, win rate, Sharpe ratio
  - **Navigation**: [📊 Chart View] [🔍 Symbol Breakdown] [📋 All Trades] [⚙️ Settings]

- **Symbol Breakdown**: Szczegółowa analiza per symbol:
  - Lista wszystkich trade'ów z pełnymi szczegółami
  - Dla każdego trade'u: warunki wejścia, wartości wskaźników, P&L, lessons learned
  - False positives analysis z wyjaśnieniami

- **Chart View**: Wykres ceny z nałożonymi wskaźnikami:
  - Timeline wszystkich decyzji
  - Wskaźniki jako oddzielne wykresy z threshold lines
  - Hover dla szczegółów każdego punktu decyzji
  - Zoom do konkretnych okresów

- **Parameter Performance Analysis**:
  - Analiza wpływu parametrów strategii na wyniki
  - Rekomendacje optymalizacji (np. "Zwiększ VWAP threshold z 0.50 do 0.55")
  - A/B testing różnych konfiguracji

- **Trade-by-Trade Breakdown**: Szczegółowa tabela z:
  - Wartościami WSZYSTKICH wskaźników w momencie decyzji
  - Kontekstem decyzyjnym
  - Analizą błędnych decyzji

**Kluczowe Funkcje per use1.md**:
- **Per-Trade Breakdown z Wartościami Wskaźników**: Każdy trade zapisuje pełny kontekst decyzyjny
- **Chart View z Timeline**: Wizualizacja decyzji na wykresie ceny
- **Parameter Optimization**: Automatyczne sugestie ulepszeń
- **False Positives Analysis**: Szczegółowa analiza błędnych sygnałów

**Komponenty używane:** Material-UI Table, Dialog, Tabs, Charts (recharts), Accordion, Timeline

**Ustawienia i Parametry:**
- Szczegółowa analiza włączana opcjonalnie (wolniejsza ale bogatsza)
- Wszystkie wartości wskaźników zapisywane w bazie danych
- Export wyników jako CSV/PDF
- Możliwość rerun z różnymi parametrami

### 5.5. Data Collection (`/data-collection`)

**Plik:** `app/data-collection/page.tsx`

**Opis:** Zarządzanie zbieraniem danych rynkowych z postępem w czasie rzeczywistym.

**Funkcje i Akcje:**

- **Przyciski główne**:
  - **Refresh**: Odświeżenie listy sesji
  - **Start Collection**: Otwiera dialog nowej kolekcji
  - **Check Status**: Logowanie statusu subskrypcji WebSocket

- **Lista sesji**: Tabela z kolumnami:
  - Session ID, Status, Symbols, Data Types, Duration, Records, Storage Path, Actions
  - **Progress Bar**: Dla aktywnych sesji z ETA i procentem
  - **Actions**: View Details, Stop Collection (aktywne), Download Data (zakończone)

- **Statystyki** (Cards):
  - Active Collections: Liczba uruchomionych kolekcji
  - Completed: Liczba zakończonych kolekcji
  - Total Records: Łączna liczba zebranych rekordów
  - Storage Used: Szacowane użycie miejsca (~0.1MB per record)

- **Start kolekcji** (Dialog "Start Data Collection"):
  - **Tytuł dialogu**: "Start Data Collection"
  - **Stan formularza**: collectionForm w useState z wartościami domyślnymi
  - **Pole Symbols** (FormControl + Select multiple):
    - Label: "Symbols"
    - labelId: "symbols-label"
    - id: "symbols-select"
    - Opcje: Ładowane z API przez apiService.getSymbols() w loadAvailableSymbols()
    - Domyślna wartość: Wszystkie symbole (ustawiane automatycznie w useEffect gdy availableSymbols.length > 0)
    - RenderValue: (selected) => (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
          {selected.map((value) => (
            <Chip key={value} label={value} size="small" />
          ))}
        </Box>
      )
    - onChange: setCollectionForm(prev => ({
        ...prev,
        symbols: typeof e.target.value === 'string' ? [e.target.value] : e.target.value
      }))
  - **Kontener Duration** (Box sx={{ display: 'flex', gap: 1 }}):
    - **Pole Duration Value** (TextField):
      - Label: "Duration Value"
      - Type: "number"
      - id: "duration-value-input"
      - Domyślna wartość: 1
      - onChange: setCollectionForm(prev => ({
          ...prev,
          duration_value: Math.max(0, parseInt(e.target.value) || 0)
        }))
      - HelperText: "Enter 0 for continuous"
    - **Pole Duration Unit** (FormControl + Select):
      - Label: "Unit"
      - labelId: "duration-unit-label"
      - id: "duration-unit-select"
      - Opcje (MenuItem):
        - "Seconds" (value: "seconds")
        - "Minutes" (value: "minutes")
        - "Hours" (value: "hours")
        - "Days" (value: "days")
      - Domyślna wartość: "hours"
      - onChange: setCollectionForm(prev => ({
          ...prev,
          duration_unit: e.target.value
        }))
  - **Pole Storage Path** (TextField):
    - Label: "Storage Path"
    - id: "storage-path-input"
    - Domyślna wartość: "data"
    - onChange: setCollectionForm(prev => ({ ...prev, storage_path: e.target.value }))
    - HelperText: "Directory where collected data will be stored"
  - **Alert Info** (Alert severity="info"):
    - Icon: InfoIcon
    - Title: brak
    - Content: "Data Collection: Continuously gather market data for analysis\nData will be stored as CSV files organized by symbol and date"
  - **Przyciski** (DialogActions):
    - "Cancel" - onClick: () => setDialogOpen(false)
    - "Start Collection" - variant="contained", color="success", onClick: handleCreateDataCollection
  - **Walidacja**: Sprawdzanie czy symbols.length > 0, inaczej błąd w snackbar
  - **Źródło danych**: Symbole ładowane z API, błąd wyświetlany gdy API niedostępne

- **Stop kolekcji**: Zatrzymanie z potwierdzeniem

- **Szczegóły sesji** (Accordion):
  - Session Summary: ID, Status, Records Collected, Storage Path, Start Time
  - Data Types & Symbols: Lista typów danych i monitorowanych symboli

- **WebSocket monitoring**: Real-time updates postępu z debouncing (200ms)

**Komponenty używane:** Material-UI Table, LinearProgress, Dialog, Accordion, Alert, Snackbar

**Ustawienia i Parametry:**
- Auto-refresh co 5 minut (backup gdy WebSocket niedostępny)
- WebSocket subskrypcja na 'execution_status'
- Debounced updates (200ms) dla płynności UI
- Optymistyczne UI updates
- Walidacja: wymagane symbole

### 5.6. Indicators (`/indicators`) (Updated per use1.md)

**Plik:** `app/indicators/page.tsx`

**Opis:** Zarządzanie wariantami wskaźników z systemowymi typami bazowymi i konfigurowalnymi parametrami.

**Funkcje i Akcje:**

- **Przyciski główne**:
  - **Refresh**: Odświeżenie listy wariantów wskaźników
  - **Create Variant**: Otwiera dialog tworzenia nowego wariantu

- **System Indicators (Read-only)**: Lista bazowych typów wskaźników:
  - **Price-based**: VWAP, TWPA, Price_Velocity
  - **Volume-based**: Volume_Surge_Ratio, Volume_MA, Smart_Money_Flow
  - **Composite**: Pump_Magnitude, Risk_Score, Momentum_Index
  - **Każdy typ**: Opis, parametry, przycisk "[Create Variant]"

- **My Custom Variants**: Tabela z kolumnami:
  - Name, Base Type, Window, Symbols, Used In, Actions
  - **Actions**: Edit, Duplicate, Test, Delete (z ostrzeżeniem jeśli używany w strategiach)

- **Statystyki** (Cards):
  - Total Variants: Liczba własnych wariantów
  - System Types: Liczba bazowych typów
  - Active Calculations: Warianty z bieżącymi wartościami
  - Strategies Using: Łączna liczba użyć w strategiach

- **Tworzenie wariantu** (Dialog "Create Indicator Variant"):
  - **Step 1: Select Base Type**: Lista systemowych typów z opisami
  - **Step 2: Name Your Variant**: Pole nazwy z walidacją unikalności
  - **Step 3: Configure Parameters**: Dynamiczny formularz na podstawie typu:
    - **Dla VWAP**: window_start, window_end (sekundy wstecz)
    - **Dla Risk Calculator**: fast_mode (boolean), window (sekundy)
    - **Dla Volume Surge**: threshold, lookback_window
  - **Step 4: Select Symbols**: All symbols lub specific list
  - **Step 5: Test Configuration**: [Test with Live Data] → pokazuje wartość

- **Edycja wariantu**: Podobny dialog z ostrzeżeniem jeśli używany w strategiach:
  - "⚠️ This variant is used in 2 strategies. Changes will affect: Strategy A, Strategy B"

- **Usuwanie**: Z blokadą jeśli używany w strategiach:
  - "Cannot delete: Used in strategies. Remove from strategies first or create new variant."

- **Chart View**: Dla każdego wariantu przycisk wykresu z timeline wartości

**Komponenty używane:** Material-UI Table, Dialog, Tabs, Accordion, TextField, Select, Chip

**Ustawienia i Parametry:**
- Warianty zapisywane jako JSON/YAML z identyfikatorem bazowego typu
- Kategoryzacja: General, Risk, Price (Entry), Stop Loss, Take Profit, Exit Price
- Walidacja parametrów per typ wskaźnika
- Real-time wartości dla wszystkich wariantów





### 5.9. Settings (`/settings`) (Simplified per use1.md)

**Plik:** `app/settings/page.tsx`

**Opis:** Proste ustawienia aplikacji - tylko podstawowe parametry bez złożonych zakładek.

**Funkcje i Akcje:**

- **Global Strategy Limits**:
  - **Max Concurrent Signals**: Slider 1-10 (domyślnie 3)
  - Opis: "Maximum number of strategies that can have active signals simultaneously"

- **Default Trading Parameters**:
  - **Default Budget**: TextField w USD (domyślnie 1000)
  - **Default Position Size**: Percentage of budget (domyślnie 10%)
  - **Emergency Cooldown**: Minutes (domyślnie 5)

- **API Connection**:
  - **Backend URL**: TextField (domyślnie localhost:8000)
  - **Test Connection**: Button

- **Display Preferences**:
  - **Theme**: Select (Light/Dark)
  - **Language**: Select (English/Polski)

**Komponenty używane:** Material-UI Card, TextField, Select, Slider, Button

**Ustawienia i Parametry:**
- Minimalistyczny interfejs bez zakładek
- Tylko krytyczne ustawienia systemowe
- Brak złożonych konfiguracji powiadomień/wydajności

### 5.10. Strategies (`/strategies`) (Simplified per use1.md)

**Plik:** `app/strategies/page.tsx`

**Opis:** Lista własnych strategii bez szablonów - tylko strategie utworzone przez użytkownika.

**Funkcje i Akcje:**

- **Przyciski główne**:
  - **[+ Create New Strategy]**: Przekierowanie do /strategy-builder

- **Lista strategii**: Tabela z kolumnami:
  - Name, Status, Created, Last Modified, Symbols, Actions
  - **Actions**: Edit (strategy-builder), Duplicate, Delete

- **Status indicators**:
  - Draft: Nie zatwierdzona
  - Valid: Przesła walidację
  - Tested: Ma wyniki backtestu
  - Active: Uruchomiona w tradingu

- **Brak szablonów/galerii** - zgodnie z use1.md, użytkownicy tworzą strategie od podstaw

**Komponenty używane:** Material-UI Table, Button, Chip

**Ustawienia i Parametry:**
- Lista strategii ładowana z backendu
- Brak predefiniowanych szablonów
- Prosta lista bez złożonych kart/galerii

---

## 6. Akcje UI i Interakcje

### 6.1. Akcje Globalne

- **Nawigacja**: Pasek nawigacyjny między stronami
- **Autoryzacja**: Login/logout, token refresh
- **Powiadomienia**: Snackbar dla komunikatów sukces/błąd
- **Ładowanie**: Progress bars i skeleton loaders
- **Błędy**: Error boundaries i alerty

### 6.2. Akcje Specyficzne dla Handlu

- **Start/Stop sesji**: Kontrola sesji tradingowych
- **Konfiguracja parametrów**: Budżet, symbole, strategie
- **Monitorowanie**: Real-time updates przez WebSocket
- **Raporty**: Generowanie i eksport wyników

### 6.3. Akcje Strategy Builder

- **Drag & Drop**: Tworzenie grafu strategii
- **Walidacja**: Sprawdzanie poprawności strategii
- **Save/Load**: Zarządzanie blueprintami strategii
- **Live editing**: Edycja parametrów węzłów

---

## 7. Komunikacja z Backendem

### 7.1. REST API

- **GET/POST /api/v1/sessions**: Zarządzanie sesjami
- **GET/POST /api/v1/strategy-blueprints**: Zarządzanie strategiami
- **GET /api/v1/market-data**: Dane rynkowe
- **GET /api/v1/indicators**: Wskaźniki
- **GET /api/v1/health**: Status systemu

### 7.2. WebSocket

- **execution_status**: Status sesji i postęp
- **market_data**: Dane rynkowe w czasie rzeczywistym
- **indicators**: Wartości wskaźników
- **signals**: Sygnały tradingowe

---

## 8. Testowanie

**Plik:** `setupTests.ts`

- Mock window.matchMedia
- Mock ResizeObserver
- Mock IntersectionObserver
- Konfiguracja @testing-library/jest-dom

---

## 9. Kluczowe Funkcjonalności Systemu

### 9.1. Real-time Data Streaming
- **WebSocket connections** do backendu dla live updates
- **Market data** - ceny, wolumeny, wskaźniki w czasie rzeczywistym
- **Session updates** - statusy sesji tradingowych
- **Signal notifications** - alerty o wykrytych sygnałach
- **Health monitoring** - status systemu i usług

### 9.2. Risk Management System
- **Portfolio risk limits** - maksymalny % portfela w ryzyku
- **Position size controls** - limity wielkości pozycji
- **Stop-loss orders** - automatyczne zamykanie stratnych pozycji
- **Drawdown protection** - emergency stops przy dużych spadkach
- **Daily loss limits** - maksymalne dzienne straty

### 9.3. Strategy Engine
- **Visual strategy builder** - drag & drop konstruktor strategii
- **Template system** - predefiniowane szablony strategii
- **Backtesting** - testowanie strategii na danych historycznych
- **Live execution** - automatyczne wykonywanie strategii
- **Performance analytics** - metryki i raporty wydajności

### 9.4. Data Collection & Analysis
- **Multi-symbol support** - jednoczesne monitorowanie wielu par
- **Multiple data types** - price, orderbook, trades, volume
- **Historical data** - zbieranie i przechowywanie danych
- **Technical indicators** - 15+ wskaźników technicznych
- **Real-time calculations** - live obliczenia wskaźników

### 9.5. User Interface Features
- **Responsive design** - działa na desktop i mobile
- **Dark/Light themes** - konfigurowalne motywy
- **Multi-language** - wsparcie dla wielu języków
- **Real-time notifications** - toast notifications i alerts
- **Loading states** - skeleton loaders i progress bars
- **Error handling** - graceful error handling z retry

### 9.6. Security & Performance
- **Authentication** - login/logout system
- **API security** - token-based auth, HTTPS
- **Input validation** - client-side validation
- **Rate limiting** - protection przed spamem
- **Caching** - intelligent caching dla lepszej wydajności
- **Compression** - data compression dla mniejszego transferu

---

## 10. Setup i Deployment

### 10.1. Wymagania Systemowe
- **Node.js** 18+ (LTS)
- **npm** lub **yarn**
- **Backend API** uruchomiony na porcie 8000

### 10.2. Instalacja
```bash
# Clone repository
git clone <repository-url>
cd frontend

# Install dependencies
npm install

# Setup environment variables
cp .env.example .env.local
# Edit .env.local with your configuration
```

### 10.3. Environment Variables
```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# App Configuration
NEXT_PUBLIC_APP_NAME="Pump & Dump Trading Dashboard"
NEXT_PUBLIC_APP_VERSION="1.0.0"

# Feature Flags
NEXT_PUBLIC_ENABLE_DEBUG=false
NEXT_PUBLIC_ENABLE_ANALYTICS=true
```

### 10.4. Development
```bash
# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run tests
npm test

# Run linting
npm run lint
```

### 10.5. Build Output
- **Static export** dla deploymentu na CDN
- **Server-side rendering** dla lepszej SEO
- **Code splitting** dla optymalizacji ładowania
- **Service worker** dla offline functionality

### 10.6. Deployment Options
- **Vercel** - recommended dla Next.js
- **Netlify** - static hosting
- **Docker** - containerized deployment
- **AWS S3 + CloudFront** - static hosting

---

## 9. Podsumowanie

Aplikacja frontendowa to kompleksowe narzędzie do tradingu algorytmicznego z następującymi kluczowymi cechami:

1. **Modularna architektura** oparta na Next.js i Zustand
2. **Real-time updates** przez WebSocket
3. **Wizualne projektowanie strategii** w ReactFlow
4. **Kompleksowe zarządzanie** wszystkimi aspektami tradingu
5. **Responsywny UI** w Material-UI

Dokumentacja ta stanowi kompletną specyfikację UI i powinna być aktualizowana wraz ze zmianami w kodzie.

```mermaid
graph TD
    subgraph "Framework & UI"
        NextJS[Next.js App Router]
        React[React]
        MUI[Material-UI]
        ReactFlow[ReactFlow - Strategy Builder]
    end

    subgraph "Zarządzanie Stanem"
        Zustand[Zustand Stores]
        Hooks[Custom Hooks]
    end

    subgraph "Komunikacja"
        ApiService[api.ts]
        WsService[websocket.ts]
        AuthService[authService.ts]
        StrategyBuilderApi[strategyBuilderApi.ts]
    end

    subgraph "Komponenty Aplikacji"
        Pages[Pages (app/)]
        Components[Reusable Components]
        Layout[Layout Component]
    end

    Pages --> Components
    Pages --> Zustand
    Pages --> Hooks
    Zustand --> ApiService
    Zustand --> WsService
    ApiService --> AuthService
    StrategyBuilderApi --> ApiService
```

### Uzasadnienie Diagramu

*   **Krok 1: Identyfikacja głównych komponentów.** Dokument `docs/ui/STRATEGY_BUILDER_USER_GUIDE.md` w sekcji "Komponenty Interfejsu" jawnie wymienia: "Górny Pasek Narzędzi", "Lewy Panel - Biblioteka Węzłów" (Toolbox), "Główne Płótno (Canvas)", "Prawy Panel - Właściwości Węzła" oraz "Dolny Pasek Statusu". Te elementy stanowią rdzeń diagramu.
*   **Krok 2: Identyfikacja głównych widoków.** Dokument `docs/MVP_interface.md` oraz `docs/ui/USER_INTERFACE_GUIDE.md` opisują różne pulpity i przepływy, takie jak "Dashboard sesji", "Strategy Builder", "Wyniki" (Analytics) i "Backtest". Zostały one przedstawione jako oddzielne widoki, między którymi użytkownik może nawigować.
*   **Krok 3: Określenie relacji.** Logika interakcji jest następująca: użytkownik używa `Paska Nawigacyjnego` (A) i `Toolboxa` (B) do manipulacji zawartością `Głównego Obszaru Roboczego` (C). Zaznaczenie elementu w (C) powoduje wyświetlenie jego szczegółów w `Panelu Właściwości` (D). `Pasek Statusu` (E) odzwierciedla ogólny stan obszaru roboczego. Widok `Strategy Builder` (W2) jest głównym widokiem wykorzystującym ten layout.

