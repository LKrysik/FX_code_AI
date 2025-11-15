# Kompleksowa Dokumentacja Interfejsu Frontend - Trading

**Wersja:** 1.0
**Data:** 2025-11-14
**Autor:** Analiza systemu FX_code_AI_v2

---

## Spis Treści

1. [Przegląd Architektury](#1-przegląd-architektury)
2. [Tryb Live Trading](#2-tryb-live-trading)
3. [Tryb Paper Trading](#3-tryb-paper-trading)
4. [Tryb Backtesting](#4-tryb-backtesting)
5. [Komponenty Wizualizacji](#5-komponenty-wizualizacji)
6. [Zarządzanie Sesjami](#6-zarządzanie-sesjami)
7. [Konfiguracja i Parametry](#7-konfiguracja-i-parametry)
8. [Integracja WebSocket](#8-integracja-websocket)
9. [API i Komunikacja](#9-api-i-komunikacja)
10. [Zarządzanie Ryzykiem](#10-zarządzanie-ryzykiem)

---

## 1. Przegląd Architektury

### 1.1 Technologie

Frontend aplikacji został zbudowany w oparciu o:

- **Next.js 14** - framework React z App Router
- **React 18** - biblioteka UI z TypeScript
- **Material-UI (MUI)** - biblioteka komponentów interfejsu
- **TradingView Lightweight Charts** - wykresy rynkowe
- **WebSocket** - komunikacja w czasie rzeczywistym
- **REST API** - operacje CRUD z ochroną CSRF

### 1.2 Struktura Katalogów

```
frontend/src/
├── app/
│   ├── live-trading/          # Strona Live Trading
│   ├── paper-trading/         # Strona Paper Trading
│   │   └── [sessionId]/       # Szczegóły sesji Paper Trading
│   ├── backtesting/           # Strona Backtesting
│   └── trading/               # Ogólna strona tradingu
├── components/
│   ├── trading/               # Komponenty tradingowe
│   │   ├── TradingChart.tsx
│   │   ├── PositionMonitor.tsx
│   │   ├── OrderHistory.tsx
│   │   ├── SignalLog.tsx
│   │   └── RiskAlerts.tsx
│   └── charts/                # Komponenty wykresów
│       ├── EquityCurveChart.tsx
│       ├── DrawdownChart.tsx
│       ├── WinRatePieChart.tsx
│       └── PnLDistributionChart.tsx
├── hooks/
│   └── useWebSocket.ts        # Hook WebSocket
└── services/
    ├── api.ts                 # Centralna usługa API
    └── TradingAPI.ts          # API operacji tradingowych
```

---

## 2. Tryb Live Trading

### 2.1 Lokalizacja

**Plik:** `frontend/src/app/live-trading/page.tsx`

### 2.2 Opis Interfejsu

Strona Live Trading to **główny interfejs do prowadzenia rzeczywistego tradingu** z połączeniem na żywo do giełdy MEXC.

#### Layout - Układ 3-panelowy:

```
┌─────────────────────────────────────────────────────────────┐
│  [PANEL LEWY]         [PANEL ŚRODKOWY]      [PANEL PRAWY]   │
│                                                               │
│  • QuickSessionStarter │ • TradingChart     │ • PositionMonitor│
│  • Konfiguracja sesji  │ • Wykresy OHLCV    │ • Otwarte pozycje│
│  • Wybór strategii     │ • Markery sygnałów │ • Monitorowanie  │
│  • Wybór symboli       │ • Volume           │   P&L            │
│  • Budget controls     │ • Timeframe        │                  │
│                        │   selector         │ • OrderHistory   │
│                        │                    │   Historia       │
│                        │ • SignalLog        │   zleceń         │
│                        │   Logi sygnałów    │                  │
│                        │                    │ • RiskAlerts     │
│                        │                    │   Alerty ryzyka  │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Dostępne Akcje i Operacje

#### A. Uruchamianie Sesji Live Trading

**Lokalizacja:** Panel lewy - QuickSessionStarter

**Krok po kroku:**

1. **Wybór Strategii**
   - Kliknij pole "Select Strategy"
   - Wybierz strategię z listy dropdown (strategie z bazy QuestDB)
   - Dostępne informacje: nazwa strategii, opis, kategoria, autor

2. **Wybór Symboli (Pary Walutowe)**
   - Kliknij pole "Select Symbols"
   - Zaznacz checkbox przy każdym symbolu (np. BTC_USDT, ETH_USDT)
   - Multi-select - można wybrać wiele symboli jednocześnie
   - Lista symboli pobierana z API: `GET /api/symbols`

3. **Konfiguracja Budżetu**
   - **Global Cap:** Maksymalny budżet na całą sesję (domyślnie: $1000 USD)
   - Slider lub pole input do wprowadzenia wartości
   - Walidacja: wartość musi być > 0

4. **Uruchomienie**
   - Kliknij przycisk **"Start Live Trading"**
   - System waliduje konfigurację
   - Wysyła request: `POST /api/sessions/start`
   ```json
   {
     "session_type": "live",
     "symbols": ["BTC_USDT", "ETH_USDT"],
     "strategies": ["strategy_id_123"],
     "config": {
       "budget": {
         "global_cap": 1000,
         "allocations": {}
       }
     }
   }
   ```
   - Backend łączy się z giełdą MEXC
   - Rozpoczyna się streaming danych w czasie rzeczywistym

#### B. Monitorowanie Aktywnej Sesji

**Co jest prezentowane:**

1. **TradingChart (Panel środkowy)**
   - **Wykres świecowy (Candlestick):** OHLCV (Open, High, Low, Close, Volume)
   - **Interwały czasowe:** 1m, 5m, 15m, 1h, 4h, 1d (przełącznik na górze wykresu)
   - **Markery sygnałów:**
     - 🟡 S1 (Signal Entry) - sygnał wejścia
     - 🟢 Z1 (Zone Entry) - wejście w strefę
     - 🔵 ZE1 (Zone Exit) - wyjście ze strefy
     - 🔴 E1 (Exit) - sygnał wyjścia
   - **Histogram wolumenu** pod wykresem
   - **Kontrolki:**
     - Auto-scroll (automatyczne przewijanie do najnowszych danych)
     - Zoom (przybliżanie/oddalanie)
     - Pan (przesuwanie wykresu)
   - **Aktualizacja:** Real-time przez WebSocket (<1s opóźnienia)

2. **SignalLog (Panel środkowy, dolna część)**
   - **Tabela sygnałów tradingowych:**
     - **Type:** Typ sygnału (S1, Z1, ZE1, E1) - kolorowe badge'e
     - **Symbol:** Para walutowa (BTC_USDT, ETH_USDT)
     - **Side:** Kierunek (LONG/SHORT)
     - **Timestamp:** Data i czas wygenerowania sygnału
     - **Confidence:** Wskaźnik pewności (0-100%) - gauge wizualny
     - **Execution:** Status wykonania (ORDER_CREATED, REJECTED, PENDING)
     - **Indicators:** Rozwijalna sekcja z wartościami wskaźników (kliknij, aby zobaczyć)
   - **Filtry:**
     - Filtr po typie sygnału (dropdown: All, S1, Z1, ZE1, E1)
     - Filtr po symbolu (dropdown: All, BTC_USDT, ETH_USDT, ...)
     - Filtr po minimalnej pewności (slider: 0-100%)
   - **Auto-scroll:** Automatyczne przewijanie do najnowszych sygnałów
   - **Aktualizacja:** Real-time przez WebSocket

3. **PositionMonitor (Panel prawy)**
   - **Tabela otwartych pozycji:**
     - **Symbol:** Para walutowa
     - **Side:** Kierunek pozycji (LONG/SHORT)
     - **Size:** Wielkość pozycji (ilość kontraktów)
     - **Entry Price:** Cena wejścia
     - **Current Price:** Aktualna cena (live update)
     - **P&L ($):** Zysk/strata w dolarach (kolor: zielony = zysk, czerwony = strata)
     - **P&L (%):** Zysk/strata w procentach
     - **Margin Ratio:** Wskaźnik marży
       - **<15%:** 🔴 Czerwony (zagrożenie likwidacji)
       - **15-25%:** 🟡 Żółty (ostrzeżenie)
       - **>25%:** 🟢 Zielony (bezpieczne)
     - **Liquidation Price:** Cena likwidacji pozycji
     - **Close:** Przycisk do zamknięcia pozycji
   - **Footer (podsumowanie):**
     - **Total P&L:** Całkowity zysk/strata
     - **Avg Margin Ratio:** Średni wskaźnik marży
   - **Aktualizacja:** Real-time przez WebSocket

4. **OrderHistory (Panel prawy)**
   - **Tabela historii zleceń:**
     - **Timestamp:** Data i czas zlecenia
     - **Symbol:** Para walutowa
     - **Side:** Kierunek (BUY/SELL)
     - **Type:** Typ zlecenia (MARKET, LIMIT, STOP)
     - **Quantity:** Ilość
     - **Price:** Cena (dla LIMIT/STOP)
     - **Filled Price:** Rzeczywista cena wykonania
     - **Slippage:** Poślizg cenowy (różnica między ceną oczekiwaną a rzeczywistą)
     - **Status:** Status zlecenia (FILLED, PARTIALLY_FILLED, CANCELLED, REJECTED)
   - **Filtry:**
     - Filtr po statusie (dropdown: All, FILLED, CANCELLED, REJECTED)
     - Filtr po symbolu (dropdown: All, BTC_USDT, ETH_USDT, ...)
   - **Paginacja:** 20 zleceń na stronę
   - **Export:** Przycisk "Export CSV" (pobiera historię w formacie CSV)
   - **Aktualizacja:** Real-time przez WebSocket

5. **RiskAlerts (Panel prawy)**
   - **Alerty ryzyka:**
     - **Margin Warnings:** Ostrzeżenia o niskiej marży
     - **Liquidation Proximity:** Alerty o zbliżeniu do ceny likwidacji
     - **Budget Utilization:** Alerty o wykorzystaniu budżetu
   - **Poziomy severity:**
     - 🔴 **CRITICAL:** Natychmiastowe działanie wymagane
     - 🟡 **WARNING:** Ostrzeżenie
     - 🔵 **INFO:** Informacja
   - **Aktualizacja:** Real-time przez WebSocket

#### C. Zarządzanie Pozycjami

**Dostępne operacje:**

1. **Zamknięcie pozycji**
   - Kliknij przycisk "Close" przy wybranej pozycji w PositionMonitor
   - Potwierdź zamknięcie (modal dialog)
   - System wysyła zlecenie MARKET przeciwnego kierunku
   - Request: `POST /api/positions/{position_id}/close`
   - Pozycja zostaje zamknięta natychmiast (MARKET order)
   - P&L zostaje zrealizowany i dodany do salda

2. **Monitorowanie ryzyka**
   - Obserwuj Margin Ratio dla każdej pozycji
   - Jeśli Margin Ratio < 15%: rozważ zamknięcie lub dodanie środków
   - Obserwuj Liquidation Price - nie dopuść do jego osiągnięcia
   - Sprawdzaj RiskAlerts na bieżąco

#### D. Zatrzymanie Sesji

**Krok po kroku:**

1. Kliknij przycisk **"Stop Session"** (na górze strony lub w QuickSessionStarter)
2. System:
   - Zatrzymuje streaming danych z giełdy
   - **NIE zamyka** automatycznie otwartych pozycji (!)
   - Zapisuje stan sesji do bazy QuestDB
   - Request: `POST /api/sessions/stop`
3. **WAŻNE:** Przed zatrzymaniem sesji:
   - Zamknij wszystkie otwarte pozycje ręcznie (jeśli chcesz)
   - Sprawdź, czy wszystkie zlecenia są wykonane lub anulowane
   - Zapisz wyniki (jeśli potrzebujesz)

### 2.4 Konfiguracja Szczegółowa

**Dostępne parametry konfiguracyjne:**

```typescript
interface LiveTradingConfig {
  session_type: 'live';
  symbols: string[];              // Lista par walutowych
  strategies: string[];           // ID strategii z bazy
  config: {
    budget: {
      global_cap: number;         // Maksymalny budżet (USD)
      allocations: {              // Alokacja per symbol (opcjonalne)
        [symbol: string]: number;
      }
    };
    risk_management?: {           // Zarządzanie ryzykiem (opcjonalne)
      max_positions: number;      // Maks. liczba otwartych pozycji
      max_position_size: number;  // Maks. wielkość pojedynczej pozycji
      stop_loss_pct: number;      // Stop loss w %
      take_profit_pct: number;    // Take profit w %
    };
  }
}
```

**Walidacja:**

- `symbols`: Minimum 1 symbol wymagany
- `strategies`: Minimum 1 strategia wymagana
- `budget.global_cap`: Musi być > 0, zalecane minimum: $100
- `risk_management.max_positions`: Jeśli podane, musi być > 0
- `risk_management.max_position_size`: Jeśli podane, musi być > 0 i <= global_cap

---

## 3. Tryb Paper Trading

### 3.1 Lokalizacja

**Pliki:**
- Lista sesji: `frontend/src/app/paper-trading/page.tsx`
- Szczegóły sesji: `frontend/src/app/paper-trading/[sessionId]/page.tsx`

### 3.2 Opis Interfejsu

Paper Trading to **symulowany trading** z użyciem wirtualnych środków, bez rzeczywistych transakcji na giełdzie.

#### 3.2.1 Strona Listy Sesji (`/paper-trading`)

**Layout:**

```
┌───────────────────────────────────────────────────────┐
│  PAPER TRADING SESSIONS                               │
│                                                       │
│  [+ Create New Session]                              │
│                                                       │
│  ┌─────────────────────────────────────────────────┐│
│  │ Tabela Sesji:                                   ││
│  │ - Session ID                                    ││
│  │ - Strategy Name                                 ││
│  │ - Symbols                                       ││
│  │ - Status (RUNNING, STOPPED, COMPLETED)         ││
│  │ - Start Time                                    ││
│  │ - Total P&L                                     ││
│  │ - Win Rate                                      ││
│  │ - Actions: [View Details] [Stop] [Delete]     ││
│  └─────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────┘
```

### 3.3 Dostępne Akcje i Operacje

#### A. Tworzenie Nowej Sesji Paper Trading

**Krok po kroku:**

1. **Kliknij "Create New Session"**
   - Otwiera się modal dialog z formularzem

2. **Formularz konfiguracji:**

   a. **Strategy Selection**
      - Dropdown z listą strategii
      - Pobierane z: `GET /api/strategies`
      - Wyświetla: nazwa, opis, kierunek (LONG/SHORT/BOTH)

   b. **Symbols (Pary walutowe)**
      - Multi-select checkbox
      - Można wybrać wiele symboli
      - Przykład: BTC_USDT, ETH_USDT, SOL_USDT

   c. **Direction (Kierunek tradingu)**
      - Radio buttons: LONG / SHORT / BOTH
      - LONG: tylko pozycje długie
      - SHORT: tylko pozycje krótkie
      - BOTH: oba kierunki

   d. **Leverage (Dźwignia finansowa)**
      - Dropdown: 1x, 2x, 3x, 5x, 10x
      - Wyższy leverage = większe zyski/straty
      - **OSTRZEŻENIE:** Leverage >3x zwiększa ryzyko likwidacji

   e. **Initial Balance (Kapitał początkowy)**
      - Input pole numeryczne
      - Zalecane: $10,000 - $50,000
      - Walidacja: musi być > 0

   f. **Notes (Notatki)**
      - Textarea - opcjonalne
      - Miejsce na notatki o celach/strategii sesji

3. **Walidacja formularza:**
   - Strategy: wymagane
   - Symbols: minimum 1 symbol wymagany
   - Direction: wymagane
   - Leverage: wymagane
   - Initial Balance: wymagane, musi być > 0

4. **Kliknij "Create Session"**
   - Request: `POST /api/paper-trading/sessions`
   ```json
   {
     "strategy_id": "strategy_123",
     "symbols": ["BTC_USDT", "ETH_USDT"],
     "direction": "BOTH",
     "leverage": 3,
     "initial_balance": 10000,
     "notes": "Test strategii momentum"
   }
   ```
   - Backend tworzy sesję w bazie QuestDB
   - Uruchamia symulowany trading z danymi live
   - Przekierowuje do strony szczegółów sesji

#### B. Przeglądanie Sesji Paper Trading

**Strona szczegółów:** `/paper-trading/[sessionId]`

**Co jest prezentowane:**

1. **Header z podstawowymi informacjami:**
   - Session ID
   - Strategy Name
   - Status (RUNNING/STOPPED/COMPLETED)
   - Created At / Updated At
   - Initial Balance / Current Balance
   - Total P&L ($, %)

2. **Liquidation Alerts (Alerty likwidacji)**
   - Wyświetlane dla pozycji z dźwignią (leverage >1x)
   - Ostrzeżenia gdy Margin Ratio < 25%
   - CRITICAL gdy Margin Ratio < 15%

3. **Performance Charts (Wykresy wydajności)**

   a. **Equity Curve (Krzywa kapitału)**
      - Wykres liniowy pokazujący zmianę salda w czasie
      - Zielony dla zysku, czerwony dla straty
      - Linia bazowa = initial balance
      - Komponent: `EquityCurveChart.tsx`

   b. **Drawdown Chart (Wykres obsunięcia)**
      - Wykres obszarowy pokazujący % drawdown
      - Podświetla okresy maksymalnego drawdownu
      - Komponent: `DrawdownChart.tsx`

   c. **Win Rate (Wskaźnik wygranych)**
      - Wykres kołowy: Winning trades vs Losing trades
      - Kolorowe (zielony/czerwony)
      - Procent wygranych transakcji
      - Komponent: `WinRatePieChart.tsx`

   d. **P&L Distribution (Rozkład zysków/strat)**
      - Histogram rozkładu zysków/strat transakcji
      - Pokazuje, czy większość transakcji to małe zyski czy duże straty
      - Komponent: `PnLDistributionChart.tsx`

4. **Performance Metrics (Metryki wydajności)**
   - **Total Trades:** Całkowita liczba transakcji
   - **Winning Trades:** Liczba wygranych transakcji
   - **Losing Trades:** Liczba przegranych transakcji
   - **Win Rate:** Procent wygranych (%)
   - **Average Win:** Średni zysk na wygranej transakcji
   - **Average Loss:** Średnia strata na przegranej transakcji
   - **Profit Factor:** Stosunek zysków do strat
   - **Sharpe Ratio:** Wskaźnik Sharpe'a (ryzyko vs zwrot)
   - **Max Drawdown:** Maksymalne obsunięcie (%)
   - **Max Drawdown Duration:** Czas trwania maks. obsunięcia

5. **Order History Table (Historia zleceń)**
   - Identyczna jak w Live Trading
   - Timestamp, Symbol, Side, Type, Quantity, Price, Status
   - Filtry i paginacja
   - Export CSV

6. **Controls (Kontrolki)**
   - **Stop Session:** Zatrzymuje sesję paper trading
   - **Export Results:** Eksportuje wyniki do CSV/JSON
   - **Delete Session:** Usuwa sesję (po potwierdzeniu)

**Aktualizacja danych:**
- Real-time polling co 3 sekundy
- Request: `GET /api/paper-trading/sessions/{sessionId}`
- Aktualizuje wszystkie metryki, pozycje, zlecenia

#### C. Zatrzymanie Sesji Paper Trading

**Krok po kroku:**

1. Na stronie listy sesji lub na stronie szczegółów kliknij **"Stop Session"**
2. Potwierdź zatrzymanie (modal dialog)
3. System:
   - Zatrzymuje generowanie nowych sygnałów
   - Zamyka wszystkie otwarte pozycje (opcjonalne - zależne od konfiguracji)
   - Zapisuje finalne wyniki do bazy QuestDB
   - Zmienia status na STOPPED
   - Request: `POST /api/paper-trading/sessions/{sessionId}/stop`
4. Sesja pozostaje dostępna do przeglądania wyników

#### D. Usunięcie Sesji Paper Trading

1. Kliknij **"Delete"** przy wybranej sesji
2. Potwierdź usunięcie (modal dialog z ostrzeżeniem)
3. **OSTRZEŻENIE:** Ta operacja jest nieodwracalna!
4. Request: `DELETE /api/paper-trading/sessions/{sessionId}`
5. Sesja zostaje usunięta z bazy QuestDB

---

## 4. Tryb Backtesting

### 4.1 Lokalizacja

**Plik:** `frontend/src/app/backtesting/page.tsx`

### 4.2 Opis Interfejsu

Backtesting to **testowanie strategii na danych historycznych** z użyciem uprzednio zebranych sesji data collection.

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  BACKTESTING                                                │
│                                                             │
│  [Start New Backtest]                                       │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐│
│  │ Configuration Panel:                                  ││
│  │                                                       ││
│  │ 1. SESSION SELECTOR                                  ││
│  │    - Lista sesji data collection                     ││
│  │    - Wybór sesji historycznej                        ││
│  │    - Info: symbol, czas trwania, liczba rekordów    ││
│  │                                                       ││
│  │ 2. STRATEGY SELECTION                                ││
│  │    - Dropdown strategii                              ││
│  │    - Multi-select                                    ││
│  │                                                       ││
│  │ 3. SYMBOLS                                           ││
│  │    - Multi-select symboli                            ││
│  │                                                       ││
│  │ 4. ACCELERATION FACTOR                               ││
│  │    - Slider: 1x - 100x                               ││
│  │    - Kontrola szybkości odtwarzania danych          ││
│  │                                                       ││
│  │ 5. BUDGET CONFIGURATION                              ││
│  │    - Global Cap                                      ││
│  │                                                       ││
│  │ [Run Backtest]                                       ││
│  └───────────────────────────────────────────────────────┘│
│                                                             │
│  ┌───────────────────────────────────────────────────────┐│
│  │ Results Panel:                                        ││
│  │                                                       ││
│  │ - Performance Analytics Dashboard                    ││
│  │ - Equity Curve Chart                                 ││
│  │ - Drawdown Chart                                     ││
│  │ - Win Rate Pie Chart                                 ││
│  │ - P&L Distribution                                   ││
│  │ - Trade List                                         ││
│  │ - Performance Metrics                                ││
│  └───────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Dostępne Akcje i Operacje

#### A. Uruchomienie Backtesting

**Krok po kroku:**

1. **Wybór Sesji Data Collection (WYMAGANE)**
   - Kliknij "Session Selector"
   - Lista sesji pobierana z: `GET /api/data-collection/sessions`
   - Wyświetlane informacje:
     - Session ID
     - Symbols (pary walutowe zbierane w sesji)
     - Data Types (tick_prices, orderbook)
     - Start Time / End Time
     - Records Collected (liczba rekordów)
   - Wybierz sesję klikając na wiersz
   - **UWAGA:** Bez wybrania sesji backtest nie może się uruchomić!

2. **Wybór Strategii**
   - Multi-select dropdown
   - Można wybrać wiele strategii jednocześnie
   - System porówna ich wydajność na tych samych danych
   - Pobierane z: `GET /api/strategies`

3. **Wybór Symboli**
   - Multi-select checkbox
   - Symbole muszą być dostępne w wybranej sesji data collection
   - System waliduje, czy wybrane symbole są w sesji

4. **Acceleration Factor (Współczynnik przyspieszenia)**
   - Slider: 1x - 100x
   - **1x:** Real-time playback (jeśli sesja trwała 1h, backtest trwa 1h)
   - **10x:** 10 razy szybciej (sesja 1h → backtest 6 minut)
   - **100x:** 100 razy szybciej (sesja 1h → backtest 36 sekund)
   - Zalecane: 10x-50x dla balance pomiędzy szybkością a realistycznością

5. **Budget Configuration**
   - Global Cap: Maksymalny budżet na backtest (domyślnie: $1000)
   - Input pole numeryczne

6. **Kliknij "Run Backtest"**
   - Walidacja konfiguracji
   - Request: `POST /api/sessions/start`
   ```json
   {
     "session_type": "backtest",
     "symbols": ["BTC_USDT", "ETH_USDT"],
     "selected_strategies": ["strategy_123"],
     "acceleration_factor": 10,
     "session_id": "data_collection_session_456",
     "config": {
       "budget": {
         "global_cap": 1000
       }
     }
   }
   ```
   - Backend:
     - Pobiera dane historyczne z QuestDB (tabela: tick_prices)
     - Odtwarza dane z przyspieszeniem (acceleration_factor)
     - Wskaźniki kalkulują się inkrementalnie
     - Strategia generuje sygnały
     - Zlecenia są symulowane
     - Pozycje są śledzone
   - Wyniki są streamowane przez WebSocket w czasie rzeczywistym

#### B. Monitorowanie Backtesting

**Co jest prezentowane podczas wykonywania:**

1. **Progress Bar (Pasek postępu)**
   - Procent ukończenia backtestingu
   - Aktualna data/czas w danych historycznych
   - Szacowany czas do końca

2. **Real-time Charts (Wykresy w czasie rzeczywistym)**
   - **Equity Curve:** Aktualizacja w czasie rzeczywistym
   - **Drawdown Chart:** Aktualizacja w czasie rzeczywistym
   - Pokazuje ewolucję kapitału podczas odtwarzania danych

3. **Trade Log (Log transakcji)**
   - Każda transakcja pojawia się w logu natychmiast po wykonaniu
   - Timestamp, Symbol, Side, Entry/Exit Price, P&L

4. **Current Metrics (Aktualne metryki)**
   - Total Trades (aktualizacja live)
   - Current P&L
   - Win Rate
   - Max Drawdown

**Aktualizacja:** Real-time przez WebSocket

#### C. Analiza Wyników Backtesting

**Po zakończeniu backtestingu prezentowane są:**

1. **Performance Analytics Dashboard**

   **Kluczowe metryki:**
   - **Total Return:** Całkowity zwrot ($ i %)
   - **Total Trades:** Liczba transakcji
   - **Winning Trades / Losing Trades:** Liczba wygranych/przegranych
   - **Win Rate:** Procent wygranych (%)
   - **Average Win / Average Loss:** Średni zysk/strata
   - **Profit Factor:** Stosunek zysków do strat (>1 = zyskowna strategia)
   - **Sharpe Ratio:** Wskaźnik Sharpe'a
   - **Sortino Ratio:** Wskaźnik Sortino (fokus na downside risk)
   - **Max Drawdown:** Maksymalne obsunięcie kapitału (%)
   - **Max Drawdown Duration:** Czas trwania maks. obsunięcia
   - **Recovery Factor:** Stosunek zysku do max drawdown
   - **Calmar Ratio:** Stosunek rocznego zwrotu do max drawdown

2. **Charts (Wykresy)**
   - Equity Curve (finalna wersja)
   - Drawdown Chart
   - Win Rate Pie Chart
   - P&L Distribution Histogram
   - Monthly Returns Heatmap (jeśli backtest trwał >1 miesiąc)

3. **Trade List (Lista transakcji)**
   - Kompletna lista wszystkich transakcji
   - Timestamp Entry/Exit, Symbol, Side, Prices, P&L, Duration
   - Sortowanie po dowolnej kolumnie
   - Filtry
   - Export CSV

4. **Strategy Comparison (Porównanie strategii)**
   - Jeśli testowano wiele strategii:
     - Tabela porównawcza metryk
     - Wykresy Equity Curve dla każdej strategii (overlay)
     - Ranking strategii według wybranego kryterium (Sharpe, Profit Factor, Win Rate)

#### D. Export Wyników

**Dostępne formaty:**

1. **CSV Export**
   - Kliknij "Export CSV"
   - Plik zawiera:
     - Wszystkie transakcje
     - Metryki wydajności
     - Dzienne saldo kapitału

2. **JSON Export**
   - Kliknij "Export JSON"
   - Kompletne wyniki w formacie JSON
   - Zawiera wszystkie dane, wykresy, metryki

3. **PDF Report (opcjonalnie)**
   - Kliknij "Generate PDF Report"
   - Raport PDF zawiera:
     - Podsumowanie strategii i konfiguracji
     - Kluczowe metryki
     - Wykresy (embedded images)
     - Lista transakcji

**Lokalizacja zapisanych wyników:**
- Backend: `backtest_results/` directory
- Nazwa pliku: `backtest_{session_id}_{timestamp}.json`

---

## 5. Komponenty Wizualizacji

### 5.1 TradingChart

**Plik:** `frontend/src/components/trading/TradingChart.tsx`

**Opis:**
Wykres świecowy (candlestick) z integracją TradingView Lightweight Charts.

**Funkcjonalności:**

1. **Candlestick Chart (OHLCV)**
   - Open, High, Low, Close, Volume
   - Zielone świece: cena zamknięcia > cena otwarcia (wzrost)
   - Czerwone świece: cena zamknięcia < cena otwarcia (spadek)

2. **Signal Markers (Markery sygnałów)**
   - Nakładka na wykres pokazująca sygnały tradingowe
   - Typy markerów:
     - 🟡 **S1** (Signal Entry) - pozycja: poniżej świecy dla LONG, powyżej dla SHORT
     - 🟢 **Z1** (Zone Entry)
     - 🔵 **ZE1** (Zone Exit)
     - 🔴 **E1** (Exit)
   - Tooltip przy najechaniu: szczegóły sygnału (confidence, indicators)

3. **Volume Histogram**
   - Histogram wolumenu pod wykresem głównym
   - Kolor zielony: wolumen w świecy wzrostowej
   - Kolor czerwony: wolumen w świecy spadkowej

4. **Timeframe Selector (Wybór interwału)**
   - Przyciski na górze wykresu: 1m, 5m, 15m, 1h, 4h, 1d
   - Kliknięcie zmienia interwał wykresu
   - Request: `GET /api/market-data/candles?symbol={symbol}&interval={interval}`

5. **Controls (Kontrolki)**
   - **Auto-scroll:** Checkbox - automatyczne przewijanie do najnowszych świec
   - **Zoom:** Scroll myszy lub pinch gesture
   - **Pan:** Przeciąganie wykres w lewo/prawo
   - **Crosshair:** Krzyżyk pokazujący dokładną cenę i czas

**Integracja z WebSocket:**
- Subskrybuje temat: `market_data.{symbol}`
- Otrzymuje nowe świece w czasie rzeczywistym
- Dodaje do wykresu bez pełnego odświeżania

**Props:**
```typescript
interface TradingChartProps {
  symbol: string;          // Para walutowa
  interval: string;        // 1m, 5m, 15m, 1h, 4h, 1d
  signals?: Signal[];      // Sygnały do wyświetlenia
  height?: number;         // Wysokość wykresu (px)
}
```

### 5.2 PositionMonitor

**Plik:** `frontend/src/components/trading/PositionMonitor.tsx`

**Opis:**
Komponent do monitorowania otwartych pozycji tradingowych.

**Kolumny tabeli:**

1. **Symbol:** Para walutowa (np. BTC_USDT)
2. **Side:** LONG / SHORT
3. **Size:** Wielkość pozycji (liczba kontraktów)
4. **Entry Price:** Cena wejścia
5. **Current Price:** Aktualna cena (live update co 1s)
6. **P&L ($):** Zysk/strata w dolarach
   - Kalkulacja: `(current_price - entry_price) * size * direction`
   - Kolor: zielony (zysk), czerwony (strata)
7. **P&L (%):** Zysk/strata w procentach
   - Kalkulacja: `((current_price - entry_price) / entry_price) * 100`
8. **Margin Ratio:** Wskaźnik marży
   - Kalkulacja: `(equity / maintenance_margin) * 100`
   - Kod kolorów:
     - <15%: 🔴 Czerwony (CRITICAL - zagrożenie likwidacji)
     - 15-25%: 🟡 Żółty (WARNING)
     - >25%: 🟢 Zielony (SAFE)
9. **Liquidation Price:** Cena, przy której pozycja zostanie automatycznie zamknięta
10. **Actions:** Przycisk "Close" - zamyka pozycję

**Footer (Podsumowanie):**
- **Total P&L:** Suma zysków/strat wszystkich pozycji
- **Avg Margin Ratio:** Średni wskaźnik marży

**Integracja z WebSocket:**
- Subskrybuje temat: `positions`
- Otrzymuje aktualizacje pozycji w czasie rzeczywistym
- Aktualizuje Current Price, P&L, Margin Ratio automatycznie

**Props:**
```typescript
interface PositionMonitorProps {
  positions: Position[];
  onClosePosition: (positionId: string) => void;
}
```

### 5.3 OrderHistory

**Plik:** `frontend/src/components/trading/OrderHistory.tsx`

**Opis:**
Tabela historii zleceń tradingowych.

**Kolumny:**

1. **Timestamp:** Data i czas złożenia zlecenia (format: YYYY-MM-DD HH:mm:ss)
2. **Symbol:** Para walutowa
3. **Side:** BUY / SELL
4. **Type:** MARKET / LIMIT / STOP / STOP_LIMIT
5. **Quantity:** Ilość kontraktów
6. **Price:** Cena zlecenia (dla LIMIT/STOP)
7. **Filled Price:** Rzeczywista cena wykonania
8. **Slippage:** Poślizg cenowy
   - Kalkulacja: `|filled_price - price|`
   - Kolor: zielony (korzystny), czerwony (niekorzystny)
9. **Status:**
   - FILLED (zielony) - zlecenie wykonane
   - PARTIALLY_FILLED (żółty) - częściowo wykonane
   - CANCELLED (szary) - anulowane
   - REJECTED (czerwony) - odrzucone

**Filtry:**
- **Status:** Dropdown (All, FILLED, PARTIALLY_FILLED, CANCELLED, REJECTED)
- **Symbol:** Dropdown (All, BTC_USDT, ETH_USDT, ...)
- **Date Range:** Date picker (From - To)

**Paginacja:**
- 20 zleceń na stronę
- Przyciski: Previous, Next, numery stron

**Export:**
- Przycisk "Export CSV" - eksportuje przefiltrowane zlecenia do CSV

**Integracja z WebSocket:**
- Subskrybuje temat: `orders`
- Nowe zlecenia pojawiają się automatycznie na górze tabeli
- Aktualizacje statusu zleceń w czasie rzeczywistym

### 5.4 SignalLog

**Plik:** `frontend/src/components/trading/SignalLog.tsx`

**Opis:**
Komponent wyświetlający logi sygnałów tradingowych generowanych przez strategie.

**Elementy sygnału:**

1. **Type Badge:** Kolorowy badge typu sygnału
   - 🟡 S1 (Signal Entry) - żółty
   - 🟢 Z1 (Zone Entry) - zielony
   - 🔵 ZE1 (Zone Exit) - niebieski
   - 🔴 E1 (Exit) - czerwony

2. **Symbol:** Para walutowa

3. **Side:** LONG / SHORT

4. **Timestamp:** Data i czas wygenerowania sygnału

5. **Confidence Gauge:** Wizualny wskaźnik pewności (0-100%)
   - Kolorowa belka:
     - 0-30%: Czerwony (LOW)
     - 30-70%: Żółty (MEDIUM)
     - 70-100%: Zielony (HIGH)
   - Wartość liczbowa

6. **Execution Result:** Status wykonania sygnału
   - ORDER_CREATED (zielony) - zlecenie utworzone
   - REJECTED (czerwony) - odrzucone przez risk manager
   - PENDING (żółty) - oczekujące
   - ERROR (czerwony) - błąd wykonania

7. **Indicators (rozwijane):** Kliknij, aby zobaczyć wartości wskaźników
   - Lista wskaźników użytych do wygenerowania sygnału
   - Nazwa wskaźnika, wartość, timestamp

**Filtry:**

1. **Signal Type:** Dropdown (All, S1, Z1, ZE1, E1)
2. **Symbol:** Dropdown (All, BTC_USDT, ETH_USDT, ...)
3. **Min Confidence:** Slider (0-100%)
   - Filtruje sygnały poniżej wybranego poziomu pewności

**Auto-scroll:**
- Checkbox "Auto-scroll" - automatyczne przewijanie do najnowszych sygnałów

**Integracja z WebSocket:**
- Subskrybuje temat: `signals`
- Nowe sygnały pojawiają się na górze logu w czasie rzeczywistym
- Dźwiękowe powiadomienie o nowym sygnale (opcjonalne)

### 5.5 RiskAlerts

**Plik:** `frontend/src/components/trading/RiskAlerts.tsx`

**Opis:**
Komponent wyświetlający alerty ryzyka w czasie rzeczywistym.

**Typy alertów:**

1. **Margin Warnings (Ostrzeżenia marży)**
   - **Trigger:** Margin Ratio < 25%
   - **Severity:** WARNING (żółty)
   - **Message:** "Position {symbol} margin ratio is {ratio}% - approaching liquidation"
   - **Action:** Rozważ zamknięcie pozycji lub dodanie środków

2. **Liquidation Proximity (Zbliżenie do likwidacji)**
   - **Trigger:** Current price jest w odległości <2% od liquidation price
   - **Severity:** CRITICAL (czerwony)
   - **Message:** "Position {symbol} is near liquidation! Current: {current_price}, Liquidation: {liq_price}"
   - **Action:** Natychmiastowe zamknięcie pozycji zalecane

3. **Budget Utilization (Wykorzystanie budżetu)**
   - **Trigger:** Wykorzystanie budżetu > 80%
   - **Severity:** INFO (niebieski) lub WARNING (>90%, żółty)
   - **Message:** "Budget utilization: {percentage}%"
   - **Action:** Brak dostępnych środków na nowe pozycje

4. **Max Positions Reached (Limit pozycji)**
   - **Trigger:** Liczba otwartych pozycji = max_positions (z konfiguracji)
   - **Severity:** INFO (niebieski)
   - **Message:** "Maximum number of positions reached ({count}/{max})"

5. **Risk Limit Exceeded (Przekroczenie limitu ryzyka)**
   - **Trigger:** Potencjalna strata pozycji > risk limit
   - **Severity:** WARNING (żółty)
   - **Message:** "Position {symbol} exceeds risk limit"

**Wyświetlanie:**
- Alerty w kolejności chronologicznej (najnowsze na górze)
- Ikony severity: 🔴 CRITICAL, 🟡 WARNING, 🔵 INFO
- Timestamp każdego alertu
- Przycisk "Dismiss" przy każdym alercie (ukrywa alert)
- Przycisk "Dismiss All" (ukrywa wszystkie alerty)

**Integracja z WebSocket:**
- Subskrybuje temat: `risk_alerts`
- Nowe alerty pojawiają się natychmiast
- Dźwięk powiadomienia dla CRITICAL alerts

### 5.6 Wykresy Wydajności (Performance Charts)

#### A. EquityCurveChart

**Plik:** `frontend/src/components/charts/EquityCurveChart.tsx`

**Opis:**
Wykres liniowy pokazujący zmianę kapitału (equity) w czasie.

**Dane:**
- Oś X: Czas (timestamp)
- Oś Y: Wartość kapitału (USD)
- Linia: Zmiana kapitału w czasie
- Linia bazowa: Initial balance (pozioma linia przerywana)

**Kolorowanie:**
- Zielony: Equity > initial balance (zysk)
- Czerwony: Equity < initial balance (strata)

**Funkcjonalności:**
- Zoom (scroll myszy)
- Tooltip: Najechanie na punkt pokazuje dokładny czas i wartość
- Marker: Ostatnia wartość (oznaczenie kółkiem)

**Dane źródłowe:**
- Request: `GET /api/backtesting/sessions/{sessionId}/equity`
- Response:
  ```json
  {
    "equity_data": [
      {"timestamp": "2025-01-01T00:00:00Z", "equity": 10000},
      {"timestamp": "2025-01-01T01:00:00Z", "equity": 10150},
      ...
    ]
  }
  ```

#### B. DrawdownChart

**Plik:** `frontend/src/components/charts/DrawdownChart.tsx`

**Opis:**
Wykres obszarowy pokazujący drawdown (obsunięcie kapitału) w czasie.

**Drawdown Calculation:**
```
Drawdown = (Peak Equity - Current Equity) / Peak Equity * 100
```

**Dane:**
- Oś X: Czas
- Oś Y: Drawdown (%)
- Wykres obszarowy: Czerwony obszar pod linią drawdown

**Podświetlenia:**
- Max Drawdown: Najniższy punkt na wykresie (specjalny marker)
- Kolory: Gradient od jasnoczerwonego (małe drawdown) do ciemnoczerwonego (duże drawdown)

**Funkcjonalności:**
- Tooltip: Najechanie pokazuje dokładny % drawdown i czas
- Linia 0%: Pozioma linia bazowa (brak drawdown)

#### C. WinRatePieChart

**Plik:** `frontend/src/components/charts/WinRatePieChart.tsx`

**Opis:**
Wykres kołowy pokazujący proporcję wygranych do przegranych transakcji.

**Segmenty:**
- Zielony: Winning Trades (transakcje zyskowne)
- Czerwony: Losing Trades (transakcje stratne)

**Etykiety:**
- Procent dla każdego segmentu
- Liczba transakcji (np. "Winning: 45 (60%)")

**Tooltip:**
- Najechanie na segment: szczegóły (liczba, procent, suma zysków/strat)

#### D. PnLDistributionChart

**Plik:** `frontend/src/components/charts/PnLDistributionChart.tsx`

**Opis:**
Histogram rozkładu zysków/strat transakcji.

**Dane:**
- Oś X: Przedziały P&L (bins) - np. [-1000, -500), [-500, 0), [0, 500), [500, 1000), ...
- Oś Y: Liczba transakcji w przedziale

**Kolorowanie:**
- Czerwony: Bins ze stratą (P&L < 0)
- Zielony: Bins z zyskiem (P&L > 0)

**Funkcjonalności:**
- Tooltip: Najechanie na bin pokazuje zakres P&L i liczbę transakcji
- Linia średniej: Pionowa linia pokazująca średni P&L transakcji

**Interpretacja:**
- Szeroki rozkład: Wysoka zmienność wyników
- Rozkład przesunięty w prawo: Więcej zyskownych transakcji
- Rozkład przesunięty w lewo: Więcej stratnych transakcji

---

## 6. Zarządzanie Sesjami

### 6.1 Typy Sesji

System obsługuje 4 typy sesji:

1. **Data Collection:** Zbieranie danych rynkowych
2. **Live Trading:** Rzeczywisty trading na giełdzie
3. **Paper Trading:** Symulowany trading z wirtualnymi środkami
4. **Backtesting:** Testowanie strategii na danych historycznych

### 6.2 Lifecycle Sesji

**Stany sesji:**

```
IDLE → STARTING → RUNNING → STOPPING → STOPPED
```

**Opis stanów:**

- **IDLE:** Sesja nie uruchomiona
- **STARTING:** Inicjalizacja (łączenie z giełdą, setup komponentów)
- **RUNNING:** Sesja aktywna (streaming danych, generowanie sygnałów)
- **STOPPING:** Zamykanie (cleanup, zapisywanie wyników)
- **STOPPED:** Sesja zakończona

**Przejścia:**

1. **IDLE → STARTING:**
   - Trigger: `POST /api/sessions/start`
   - Akcje: Walidacja konfiguracji, inicjalizacja komponentów

2. **STARTING → RUNNING:**
   - Trigger: Pomyślne połączenie z giełdą/źródłem danych
   - Akcje: Start streaming danych, aktywacja strategii

3. **RUNNING → STOPPING:**
   - Trigger: `POST /api/sessions/stop` lub błąd krytyczny
   - Akcje: Stop streaming, zamknięcie pozycji (opcjonalnie), cleanup

4. **STOPPING → STOPPED:**
   - Trigger: Zakończenie cleanup
   - Akcje: Zapisanie wyników, update statusu w bazie

### 6.3 API Sesji

**Endpoints:**

1. **`POST /api/sessions/start`**
   - Uruchamia nową sesję
   - Body: Konfiguracja sesji (różna dla każdego typu)
   - Response: Session ID, status

2. **`POST /api/sessions/stop`**
   - Zatrzymuje aktywną sesję
   - Body: `{"session_id": "..."}`
   - Response: Status sesji

3. **`GET /api/sessions/{sessionId}`**
   - Pobiera szczegóły sesji
   - Response: Konfiguracja, status, metryki

4. **`GET /api/sessions`**
   - Pobiera listę wszystkich sesji
   - Query params: `?type=live&status=RUNNING`
   - Response: Lista sesji

5. **`DELETE /api/sessions/{sessionId}`**
   - Usuwa sesję (tylko STOPPED)
   - Response: Status

### 6.4 Zapisywanie Sesji (Persistence)

**Data Collection Sessions:**
- Tabela: `data_collection_sessions`
- Dane rynkowe: `tick_prices`, `orderbook`
- Format: QuestDB time-series

**Paper Trading Sessions:**
- Tabela: `paper_trading_sessions`
- Transakcje: `paper_trades`
- Metryki: obliczane on-the-fly

**Backtest Results:**
- Katalog: `backtest_results/`
- Format: JSON
- Zawiera: konfigurację, transakcje, metryki, wykresy (data points)

---

## 7. Konfiguracja i Parametry

### 7.1 Konfiguracja Strategii

**Struktura JSON strategii:**

```json
{
  "id": "strategy_123",
  "strategy_name": "Momentum Strategy",
  "description": "Strategia oparta na momentum i volume surge",
  "direction": "BOTH",
  "enabled": true,
  "conditions": {
    "entry": [
      {
        "indicator_id": "TWPA_300_0",
        "operator": ">",
        "value": 50000,
        "weight": 0.4
      },
      {
        "indicator_id": "Velocity_300_60",
        "operator": ">",
        "value": 0.5,
        "weight": 0.3
      },
      {
        "indicator_id": "Volume_Surge_300_0",
        "operator": ">",
        "value": 1.5,
        "weight": 0.3
      }
    ],
    "exit": [
      {
        "indicator_id": "Velocity_300_60",
        "operator": "<",
        "value": 0,
        "weight": 1.0
      }
    ]
  },
  "parameters": {
    "min_confidence": 0.7,
    "max_positions": 3,
    "position_size_pct": 10
  }
}
```

**Parametry strategii:**

- **min_confidence:** Minimalna pewność sygnału (0-1)
- **max_positions:** Maksymalna liczba otwartych pozycji
- **position_size_pct:** Wielkość pozycji jako % dostępnego kapitału
- **stop_loss_pct:** Stop loss w % (opcjonalnie)
- **take_profit_pct:** Take profit w % (opcjonalnie)

### 7.2 Konfiguracja Wskaźników

**Warianty wskaźników:**

System używa systemu wariantów wskaźników - ten sam wskaźnik bazowy z różnymi parametrami.

**Przykład:**

```json
{
  "name": "TWPA_300_0",
  "base_indicator_type": "TWPA",
  "variant_type": "price",
  "parameters": {
    "t1": 300,
    "t2": 0
  }
}
```

**Parametry okna czasowego (t1, t2):**
- **t1:** Początek okna (sekundy wstecz od teraz)
- **t2:** Koniec okna (sekundy wstecz od teraz)
- **Przykład:** `(300, 0)` = "ostatnie 5 minut"
- **Przykład:** `(300, 60)` = "5 minut temu do 1 minuty temu"

**Kluczowe wskaźniki:**

1. **TWPA (Time-Weighted Price Average)**
   - Średnia ważona czasowo
   - Parametry: t1, t2
   - Przykład: `TWPA_300_0` = średnia cena z ostatnich 5 minut

2. **Velocity (Prędkość zmiany ceny)**
   - Zmiana ceny między dwoma oknami
   - Parametry: t1, t2
   - Przykład: `Velocity_300_60` = zmiana ceny między 5 min temu a 1 min temu

3. **Volume_Surge (Anomalia wolumenu)**
   - Wykrywa gwałtowne wzrosty wolumenu
   - Parametry: t1, t2, threshold
   - Przykład: `Volume_Surge_300_0` = surge w ostatnich 5 minutach

### 7.3 Konfiguracja Risk Management

**Parametry zarządzania ryzykiem:**

```json
{
  "risk_management": {
    "max_positions": 5,
    "max_position_size": 1000,
    "max_position_size_pct": 20,
    "stop_loss_pct": 2,
    "take_profit_pct": 5,
    "max_drawdown_pct": 10,
    "max_leverage": 3,
    "maintenance_margin_pct": 15,
    "liquidation_buffer_pct": 2
  }
}
```

**Opis parametrów:**

- **max_positions:** Maks. liczba otwartych pozycji jednocześnie
- **max_position_size:** Maks. wielkość pojedynczej pozycji (USD)
- **max_position_size_pct:** Maks. wielkość pozycji jako % kapitału
- **stop_loss_pct:** Stop loss w % od ceny wejścia
- **take_profit_pct:** Take profit w % od ceny wejścia
- **max_drawdown_pct:** Maksymalny dopuszczalny drawdown (%)
- **max_leverage:** Maksymalna dźwignia
- **maintenance_margin_pct:** Minimalny margin ratio (poniżej = alert)
- **liquidation_buffer_pct:** Bufor przed ceną likwidacji (dla alertów)

### 7.4 Konfiguracja Budżetu

**Budget Allocation:**

```json
{
  "budget": {
    "global_cap": 10000,
    "allocations": {
      "BTC_USDT": 5000,
      "ETH_USDT": 3000,
      "SOL_USDT": 2000
    },
    "reserve": 0
  }
}
```

**Opis:**

- **global_cap:** Całkowity budżet sesji (USD)
- **allocations:** Alokacja per symbol (opcjonalne)
  - Jeśli nie podano: równa alokacja dla wszystkich symboli
- **reserve:** Rezerwa kapitału (nieużywana do tradingu)

**Walidacja:**
- Suma alokacji <= global_cap
- Reserve >= 0
- Każda alokacja > 0

---

## 8. Integracja WebSocket

### 8.1 Połączenie WebSocket

**URL:** `ws://127.0.0.1:8080/ws`

**Plik:** `frontend/src/hooks/useWebSocket.ts`

**Funkcjonalności:**

1. **Auto-reconnect z exponential backoff**
   - Przy utracie połączenia: automatyczne ponowne łączenie
   - Backoff: 1s, 2s, 4s, 8s, 16s, max 30s
   - Infinite retry

2. **Heartbeat (Ping-Pong)**
   - Co 30 sekund: klient wysyła ping
   - Serwer odpowiada pong
   - Jeśli brak pong w 10s: reconnect

3. **Message Queue**
   - Jeśli brak połączenia: wiadomości trafiają do kolejki
   - Po reconnect: kolejka jest wysyłana

4. **Connection State Management**
   - States: CONNECTING, CONNECTED, DISCONNECTED, RECONNECTING
   - UI pokazuje status połączenia (ikona + tooltip)

**Użycie w komponencie:**

```typescript
import { useWebSocket } from '@/hooks/useWebSocket';

const MyComponent = () => {
  const { isConnected, subscribe, sendMessage } = useWebSocket();

  useEffect(() => {
    const unsubscribe = subscribe('market_data.BTC_USDT', (data) => {
      console.log('Received market data:', data);
    });

    return () => unsubscribe();
  }, []);

  const handleStart = () => {
    sendMessage({
      type: 'start_session',
      data: { session_type: 'live', symbols: ['BTC_USDT'] }
    });
  };

  return <div>Connected: {isConnected ? 'Yes' : 'No'}</div>;
};
```

### 8.2 Message Protocol

**Format wiadomości:**

```json
{
  "type": "message_type",
  "stream": "optional_stream_name",
  "data": { ... },
  "timestamp": "2025-01-01T00:00:00Z"
}
```

**Typy wiadomości (Client → Server):**

1. **`authenticate`**
   ```json
   {
     "type": "authenticate",
     "data": {
       "token": "JWT_TOKEN_HERE"
     }
   }
   ```

2. **`subscribe`**
   ```json
   {
     "type": "subscribe",
     "data": {
       "streams": ["market_data.BTC_USDT", "signals", "positions"]
     }
   }
   ```

3. **`unsubscribe`**
   ```json
   {
     "type": "unsubscribe",
     "data": {
       "streams": ["market_data.BTC_USDT"]
     }
   }
   ```

4. **`start_session`**
   ```json
   {
     "type": "start_session",
     "data": {
       "session_type": "live",
       "symbols": ["BTC_USDT"],
       "strategies": ["strategy_123"],
       "config": { ... }
     }
   }
   ```

5. **`stop_session`**
   ```json
   {
     "type": "stop_session",
     "data": {
       "session_id": "session_456"
     }
   }
   ```

6. **`ping`**
   ```json
   {
     "type": "ping",
     "timestamp": "2025-01-01T00:00:00Z"
   }
   ```

**Typy wiadomości (Server → Client):**

1. **`market_data`**
   ```json
   {
     "type": "market_data",
     "stream": "market_data.BTC_USDT",
     "data": {
       "symbol": "BTC_USDT",
       "timestamp": "2025-01-01T00:00:00Z",
       "price": 50000,
       "volume": 1000,
       "quote_volume": 50000000
     }
   }
   ```

2. **`signal`**
   ```json
   {
     "type": "signal",
     "stream": "signals",
     "data": {
       "signal_id": "signal_789",
       "type": "S1",
       "symbol": "BTC_USDT",
       "side": "LONG",
       "confidence": 0.85,
       "timestamp": "2025-01-01T00:00:00Z",
       "indicators": {
         "TWPA_300_0": 50000,
         "Velocity_300_60": 0.75,
         "Volume_Surge_300_0": 1.8
       },
       "execution": "ORDER_CREATED"
     }
   }
   ```

3. **`position_update`**
   ```json
   {
     "type": "position_update",
     "stream": "positions",
     "data": {
       "position_id": "pos_123",
       "symbol": "BTC_USDT",
       "side": "LONG",
       "size": 0.1,
       "entry_price": 50000,
       "current_price": 50500,
       "pnl": 50,
       "pnl_pct": 1.0,
       "margin_ratio": 35.5,
       "liquidation_price": 45000
     }
   }
   ```

4. **`order_update`**
   ```json
   {
     "type": "order_update",
     "stream": "orders",
     "data": {
       "order_id": "order_456",
       "symbol": "BTC_USDT",
       "side": "BUY",
       "type": "MARKET",
       "quantity": 0.1,
       "price": null,
       "filled_price": 50000,
       "status": "FILLED",
       "timestamp": "2025-01-01T00:00:00Z"
     }
   }
   ```

5. **`risk_alert`**
   ```json
   {
     "type": "risk_alert",
     "stream": "risk_alerts",
     "data": {
       "alert_id": "alert_789",
       "severity": "WARNING",
       "message": "Position BTC_USDT margin ratio is 18% - approaching liquidation",
       "timestamp": "2025-01-01T00:00:00Z",
       "position_id": "pos_123"
     }
   }
   ```

6. **`session_status`**
   ```json
   {
     "type": "session_status",
     "stream": "session",
     "data": {
       "session_id": "session_456",
       "status": "RUNNING",
       "uptime": 3600,
       "total_pnl": 150,
       "active_positions": 2
     }
   }
   ```

7. **`pong`**
   ```json
   {
     "type": "pong",
     "timestamp": "2025-01-01T00:00:00Z"
   }
   ```

8. **`error`**
   ```json
   {
     "type": "error",
     "data": {
       "error_code": "INVALID_SESSION",
       "message": "Session not found",
       "details": { ... }
     }
   }
   ```

### 8.3 Subscription Management

**SubscriptionManager** (`frontend/src/services/SubscriptionManager.ts`)

**Funkcjonalności:**

1. **Subskrypcja strumieni:**
   ```typescript
   subscriptionManager.subscribe(['market_data.BTC_USDT', 'signals']);
   ```

2. **Anulowanie subskrypcji:**
   ```typescript
   subscriptionManager.unsubscribe(['market_data.BTC_USDT']);
   ```

3. **Obsługa wiadomości:**
   ```typescript
   subscriptionManager.onMessage('market_data.BTC_USDT', (data) => {
     console.log('Market data:', data);
   });
   ```

4. **Czyszczenie:**
   ```typescript
   subscriptionManager.clear(); // Usuwa wszystkie subskrypcje
   ```

**Dostępne strumienie:**

- `market_data.{symbol}` - Dane rynkowe dla symbolu
- `signals` - Wszystkie sygnały tradingowe
- `signals.{symbol}` - Sygnały dla konkretnego symbolu
- `positions` - Wszystkie pozycje
- `positions.{symbol}` - Pozycje dla symbolu
- `orders` - Wszystkie zlecenia
- `orders.{symbol}` - Zlecenia dla symbolu
- `risk_alerts` - Alerty ryzyka
- `session` - Status sesji
- `backtest_progress` - Postęp backtestingu

---

## 9. API i Komunikacja

### 9.1 REST API Endpoints

**Plik:** `frontend/src/services/api.ts`

**Base URL:** `http://localhost:8080/api`

**Nagłówki:**
- `Content-Type: application/json`
- `X-CSRF-Token: {token}` (pobierany automatycznie)
- `Cookie: access_token={JWT}` (JWT w httpOnly cookie)

#### A. Sessions

1. **`POST /api/sessions/start`**
   - Uruchamia nową sesję (live/paper/backtest/data_collection)
   - Body: Konfiguracja sesji
   - Response: `{ session_id, status }`

2. **`POST /api/sessions/stop`**
   - Zatrzymuje sesję
   - Body: `{ session_id }`
   - Response: `{ status }`

3. **`GET /api/sessions/{sessionId}`**
   - Pobiera szczegóły sesji
   - Response: Konfiguracja, status, metryki

4. **`GET /api/sessions`**
   - Lista sesji
   - Query: `?type=live&status=RUNNING`
   - Response: Array sesji

5. **`DELETE /api/sessions/{sessionId}`**
   - Usuwa sesję
   - Response: `{ status }`

#### B. Strategies

1. **`GET /api/strategies`**
   - Lista wszystkich strategii
   - Response: Array strategii

2. **`GET /api/strategies/{strategyId}`**
   - Szczegóły strategii
   - Response: Konfiguracja strategii

3. **`POST /api/strategies`**
   - Tworzy nową strategię
   - Body: Konfiguracja strategii
   - Response: `{ id, ... }`

4. **`PUT /api/strategies/{strategyId}`**
   - Aktualizuje strategię
   - Body: Zaktualizowana konfiguracja
   - Response: `{ id, ... }`

5. **`DELETE /api/strategies/{strategyId}`**
   - Usuwa strategię (soft delete)
   - Response: `{ status }`

#### C. Symbols

1. **`GET /api/symbols`**
   - Lista dostępnych par walutowych
   - Response: `["BTC_USDT", "ETH_USDT", ...]`

2. **`GET /api/symbols/{symbol}/info`**
   - Szczegóły symbolu
   - Response: Tick size, min quantity, fee, etc.

#### D. Market Data

1. **`GET /api/market-data/candles`**
   - Pobiera dane świecowe
   - Query: `?symbol=BTC_USDT&interval=1h&limit=100`
   - Response: Array świec (OHLCV)

2. **`GET /api/market-data/latest`**
   - Ostatnia cena dla symbolu
   - Query: `?symbol=BTC_USDT`
   - Response: `{ price, volume, timestamp }`

#### E. Positions

1. **`GET /api/positions`**
   - Lista otwartych pozycji
   - Query: `?session_id=session_456`
   - Response: Array pozycji

2. **`POST /api/positions/{positionId}/close`**
   - Zamyka pozycję
   - Response: `{ status, pnl }`

#### F. Orders

1. **`GET /api/orders`**
   - Historia zleceń
   - Query: `?session_id=session_456&status=FILLED&limit=100&offset=0`
   - Response: Array zleceń + pagination info

2. **`GET /api/orders/{orderId}`**
   - Szczegóły zlecenia
   - Response: Order details

#### G. Paper Trading

1. **`POST /api/paper-trading/sessions`**
   - Tworzy sesję paper trading
   - Body: Konfiguracja
   - Response: `{ session_id }`

2. **`GET /api/paper-trading/sessions`**
   - Lista sesji paper trading
   - Response: Array sesji

3. **`GET /api/paper-trading/sessions/{sessionId}`**
   - Szczegóły sesji
   - Response: Metryki, pozycje, zlecenia

4. **`POST /api/paper-trading/sessions/{sessionId}/stop`**
   - Zatrzymuje sesję
   - Response: `{ status }`

5. **`DELETE /api/paper-trading/sessions/{sessionId}`**
   - Usuwa sesję
   - Response: `{ status }`

#### H. Backtesting

1. **`GET /api/backtesting/sessions/{sessionId}/equity`**
   - Krzywa kapitału dla backtestingu
   - Response: Array equity points

2. **`GET /api/backtesting/sessions/{sessionId}/trades`**
   - Lista transakcji z backtestingu
   - Response: Array transakcji

3. **`GET /api/backtesting/sessions/{sessionId}/metrics`**
   - Metryki wydajności
   - Response: Sharpe, win rate, drawdown, etc.

#### I. Data Collection

1. **`GET /api/data-collection/sessions`**
   - Lista sesji zbierania danych
   - Response: Array sesji

2. **`GET /api/data-collection/sessions/{sessionId}`**
   - Szczegóły sesji
   - Response: Symbols, data types, records count

### 9.2 Request Deduplication

**Mechanizm:**
- `api.ts` zawiera cache dla identycznych requestów
- Jeśli ten sam request jest wykonywany wielokrotnie w krótkim czasie: zwraca cached promise
- TTL: 500ms
- Dotyczy tylko GET requests

**Przykład:**
```typescript
// Wywołane jednocześnie 3 razy:
api.get('/api/symbols');
api.get('/api/symbols');
api.get('/api/symbols');

// Faktycznie wykonuje tylko 1 HTTP request
// Pozostałe dwa otrzymują ten sam promise
```

### 9.3 Error Handling

**Typy błędów:**

1. **Network Errors** (brak połączenia)
   - Retry z exponential backoff: 1s, 2s, 4s
   - Max 3 próby
   - Toast notification: "Connection lost. Retrying..."

2. **4xx Errors** (Client errors)
   - 400 Bad Request: Walidacja danych
   - 401 Unauthorized: Przekierowanie do /login
   - 403 Forbidden: Toast notification: "Access denied"
   - 404 Not Found: Toast notification: "Resource not found"

3. **5xx Errors** (Server errors)
   - 500 Internal Server Error: Toast notification: "Server error. Please try again."
   - 503 Service Unavailable: Retry z backoff

**Error Response Format:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid session configuration",
    "details": {
      "field": "symbols",
      "issue": "At least one symbol is required"
    }
  }
}
```

### 9.4 CSRF Protection

**Mechanizm:**
- Backend generuje CSRF token przy pierwszym request
- Token zwracany w cookie: `csrf_token`
- Frontend automatycznie dołącza token w headerze: `X-CSRF-Token`
- Walidacja po stronie backend dla wszystkich POST/PUT/DELETE

**Implementacja w `api.ts`:**
```typescript
const csrfToken = getCookie('csrf_token');
if (csrfToken) {
  headers['X-CSRF-Token'] = csrfToken;
}
```

---

## 10. Zarządzanie Ryzykiem

### 10.1 Risk Manager

**Komponent backendu:** `src/domain/services/risk_manager.py`

**Funkcjonalności:**

1. **Budget Allocation**
   - Alokacja kapitału per symbol
   - Sprawdzanie dostępnych środków przed otwarciem pozycji
   - Rezerwa kapitału

2. **Position Size Limits**
   - Max wielkość pojedynczej pozycji (USD lub %)
   - Max liczba otwartych pozycji jednocześnie

3. **Margin Monitoring**
   - Obliczanie margin ratio dla każdej pozycji
   - Alerty przy niskim margin ratio (<25%)
   - CRITICAL alert przy <15% (zagrożenie likwidacji)

4. **Liquidation Proximity Detection**
   - Obliczanie ceny likwidacji dla pozycji z leverage
   - Alert gdy current price jest w odległości <2% od liquidation price

5. **Stop Loss / Take Profit**
   - Automatyczne zamykanie pozycji przy osiągnięciu SL/TP
   - SL/TP jako % od ceny wejścia lub jako wartość bezwzględna

6. **Max Drawdown Protection**
   - Monitoring drawdown sesji
   - Zatrzymanie tradingu przy przekroczeniu max_drawdown_pct

### 10.2 Alerty Ryzyka (Frontend)

**Komponent:** `RiskAlerts.tsx`

**Prezentowane alerty:**

1. **Margin Warning**
   - Trigger: Margin Ratio < 25%
   - Akcja: Rozważ zamknięcie pozycji lub dodanie środków

2. **Liquidation Proximity**
   - Trigger: Distance do liquidation price < 2%
   - Akcja: Natychmiastowe zamknięcie pozycji zalecane

3. **Budget Exceeded**
   - Trigger: Wykorzystanie budżetu > 90%
   - Akcja: Brak środków na nowe pozycje

4. **Max Positions Reached**
   - Trigger: Liczba pozycji = max_positions
   - Akcja: Nie można otworzyć nowych pozycji

5. **Max Drawdown Exceeded**
   - Trigger: Drawdown > max_drawdown_pct
   - Akcja: Trading został automatycznie zatrzymany

### 10.3 Leverage i Margin

**Leverage:**
- Dźwignia finansowa: 1x, 2x, 3x, 5x, 10x
- Wyższy leverage = większe zyski i straty
- Wyższy leverage = większe ryzyko likwidacji

**Margin Ratio Calculation:**
```
Margin Ratio = (Equity / Maintenance Margin) * 100
```

Gdzie:
- **Equity** = Initial Margin + Unrealized P&L
- **Maintenance Margin** = Position Size * Maintenance Margin Rate

**Przykład:**
- Position Size: $10,000
- Leverage: 5x
- Maintenance Margin Rate: 0.5% (zależne od giełdy)
- Initial Margin: $10,000 / 5 = $2,000
- Maintenance Margin: $10,000 * 0.005 = $50
- Equity (jeśli P&L = +$100): $2,000 + $100 = $2,100
- Margin Ratio: ($2,100 / $50) * 100 = 4200%

**Liquidation Price Calculation (LONG):**
```
Liq Price = Entry Price * (1 - 1 / Leverage + Maintenance Margin Rate)
```

**Liquidation Price Calculation (SHORT):**
```
Liq Price = Entry Price * (1 + 1 / Leverage - Maintenance Margin Rate)
```

### 10.4 Risk Metrics w UI

**Position Monitor:**
- Margin Ratio per pozycja (kolor-coded)
- Liquidation Price per pozycja
- P&L per pozycja

**Performance Metrics:**
- Max Drawdown (%)
- Max Drawdown Duration (czas)
- Sharpe Ratio (risk-adjusted return)
- Sortino Ratio (downside risk)
- Profit Factor (gross profit / gross loss)

**Risk Alerts:**
- Real-time alerty o zagrożeniach
- Severity levels: INFO, WARNING, CRITICAL

---

## Podsumowanie

### Kluczowe Funkcjonalności Systemu

1. **Live Trading**
   - Rzeczywisty trading na giełdzie MEXC
   - Real-time streaming danych (<1s latency)
   - Automatyczne generowanie sygnałów przez strategie
   - Zarządzanie pozycjami i zleceniami
   - Monitoring ryzyka w czasie rzeczywistym

2. **Paper Trading**
   - Symulowany trading bez ryzyka
   - Testowanie strategii na live data
   - Pełna analiza wydajności
   - Dźwignia finansowa (leverage)
   - Metryki wydajności (Sharpe, win rate, drawdown)

3. **Backtesting**
   - Testowanie strategii na danych historycznych
   - Szybkie odtwarzanie (acceleration factor 1x-100x)
   - Porównanie wielu strategii
   - Szczegółowa analiza wyników
   - Export raportów

4. **Data Collection**
   - Zbieranie danych rynkowych do QuestDB
   - Tick prices, orderbook
   - Sesje historyczne do backtestingu

### Dostęp Użytkownika

**Użytkownik ma dostęp do:**

1. **Konfiguracji:**
   - Wybór strategii (z bazy QuestDB)
   - Wybór symboli (par walutowych)
   - Ustawienie budżetu i alokacji
   - Parametry risk management
   - Leverage (dla paper trading)
   - Acceleration factor (dla backtesting)

2. **Monitoringu:**
   - Wykresy świecowe (TradingView) z markerami sygnałów
   - Otwarte pozycje (real-time P&L, margin, liquidation price)
   - Historia zleceń
   - Logi sygnałów tradingowych
   - Alerty ryzyka

3. **Analizy:**
   - Performance charts (equity curve, drawdown, win rate, P&L distribution)
   - Metryki wydajności (Sharpe, profit factor, win rate, max drawdown)
   - Trade list z filtrowaniem i sortowaniem
   - Export danych (CSV, JSON, PDF)

4. **Zarządzania:**
   - Uruchamianie/zatrzymywanie sesji
   - Zamykanie pozycji
   - Usuwanie sesji
   - Tworzenie/edycja strategii (przez API)

### Architektura Komunikacji

- **REST API:** Operacje CRUD, inicjalizacja sesji
- **WebSocket:** Real-time streaming danych, alerty, aktualizacje
- **QuestDB:** Persistence dla wszystkich danych (time-series, strategie, sesje)

### Bezpieczeństwo

- **JWT Authentication:** Tokeny w httpOnly cookies
- **CSRF Protection:** Token validation dla mutating operations
- **CORS:** Konfiguracja dla frontend origin
- **Input Validation:** Po stronie backend dla wszystkich requestów

---

**Koniec dokumentacji**
