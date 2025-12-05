# System Agentów - FXcrypto

**Wersja:** 15.0 | **Data:** 2025-12-05

---

## DOKUMENTACJA UI (AKTUALIZUJ PO ZADANIACH!)

### Powiązane dokumenty:
- `docs/UI_INTERFACE_SPECIFICATION.md` - Pełny opis interfejsu (strony, funkcje, braki)
- `docs/UI_BACKLOG.md` - Priorytetyzowana lista funkcji do implementacji

### Kiedy aktualizować:
| Zdarzenie | Dokument do aktualizacji |
|-----------|-------------------------|
| Zaimplementowano funkcję z backlogu | `UI_BACKLOG.md` → zmień status na DONE |
| Dodano nową stronę/komponent | `UI_INTERFACE_SPECIFICATION.md` → dodaj sekcję |
| Naprawiono brak z listy | `UI_INTERFACE_SPECIFICATION.md` → usuń z sekcji "Braki" |
| Co 3-5 iteracji frontendowych | Oba dokumenty → przejrzyj aktualność |

### Jak aktualizować UI_INTERFACE_SPECIFICATION.md:
```
Wciel się w tradera i przejdź przez interfejs:
1. Zobacz jakie są funkcjonalności interfejsu
2. Opisz go słownie - jakie funkcje daje traderowi
3. Oceń krytycznie - czy spełnia oczekiwania tradera
4. Zidentyfikuj braki (ustawianie, widoki, wykresy, szczegóły)
```

---

## CEL PROGRAMU

```
FXcrypto to system do wykrywania pump/dump na kryptowalutach.

CO TRADER CHCE OSIĄGNĄĆ:
1. Wykryć moment pumpu/dumpu ZANIM większość rynku
2. Wejść w pozycję z określonym ryzykiem
3. Wyjść z zyskiem lub minimalną stratą

JAK SYSTEM TO REALIZUJE:
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Data Collection │────▶│   Indicators    │────▶│    Signals      │
│  (OHLCV z MEXC)  │     │  (RSI, MACD,    │     │  (S1, Z1, ZE1)  │
│                  │     │   Volume Surge) │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                              ┌───────────────────────────┘
                              ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Backtest      │◀────│    Strategy     │────▶│  Paper/Live     │
│ (na historii)   │     │  (5-section)    │     │    Trading      │
└─────────────────┘     └─────────────────┘     └─────────────────┘

SYGNAŁY STRATEGII 5-SEKCJI:
- S1: Signal Detection (wykrycie potencjalnego pumpu)
- S2: Signal Confirmation (potwierdzenie trendu)
- Z1: Entry (otwarcie pozycji)
- Z2: Position Add (dodanie do pozycji)
- ZE1: Exit (zamknięcie z TP/SL)
```

---

## ARCHITEKTURA TECHNICZNA

```
┌────────────────────────────────────────────────────────────────┐
│                         FRONTEND                               │
│  Next.js 14 | React | MUI | Port 3000                         │
│                                                                │
│  Strony:                                                       │
│  /                    → PumpDumpDashboard (główny widok)       │
│  /trading-session     → SessionConfigDialog (start sesji)     │
│  /strategy-builder    → StrategyBuilder5Section               │
│  /strategies          → Lista strategii                       │
│  /data-collection     → Zarządzanie danymi historycznymi      │
│  /settings            → API keys, preferencje                 │
└───────────────────────────────┬────────────────────────────────┘
                                │ HTTP + WebSocket
                                ▼
┌────────────────────────────────────────────────────────────────┐
│                         BACKEND                                │
│  Python | FastAPI | Uvicorn | Port 8080                       │
│                                                                │
│  Główne moduły:                                               │
│  src/api/unified_server.py      → API endpoints               │
│  src/services/session_manager.py → Zarządzanie sesjami        │
│  src/core/strategy_engine.py    → Wykonanie strategii         │
│  src/indicators/                → Wskaźniki (RSI, MACD...)    │
│  src/adapters/mexc_adapter.py   → Komunikacja z giełdą        │
└───────────────────────────────┬────────────────────────────────┘
                                │ SQL
                                ▼
┌────────────────────────────────────────────────────────────────┐
│                         DATABASE                               │
│  QuestDB | Port 9000 (HTTP) | Port 8812 (PostgreSQL)          │
│                                                                │
│  Tabele:                                                       │
│  ohlcv_1m           → Dane świecowe (symbol, ts, O, H, L, C, V)│
│  signals            → Historia sygnałów                       │
│  trades             → Wykonane transakcje                     │
│  trading_sessions   → Sesje (backtest, paper, live)           │
└────────────────────────────────────────────────────────────────┘
```

---

## MAPOWANIE: UI → API → DATABASE

| Komponent UI | Co pokazuje | Endpoint API | Tabela QuestDB |
|--------------|-------------|--------------|----------------|
| **CandlestickChart** | Świece OHLCV | `GET /api/ohlcv/{symbol}` | `ohlcv_1m` |
| **SymbolWatchlist** | Lista symboli + ceny | `GET /api/symbols` | - (z MEXC) |
| **SignalHistoryPanel** | Lista sygnałów | `GET /sessions/{id}/signals` | `signals` |
| **EquityCurveChart** | Krzywa kapitału | `GET /sessions/{id}/equity` | `trading_sessions` |
| **TransactionHistoryPanel** | Transakcje | `GET /sessions/{id}/transactions` | `trades` |
| **PositionMonitor** | Otwarte pozycje | `GET /sessions/{id}/positions` | `trades` (open) |
| **LiveIndicatorPanel** | Wartości RSI, MACD | `GET /api/indicators/{symbol}` | - (kalkulowane) |
| **StrategyBuilder5Section** | Edycja strategii | `POST/PUT /api/strategies` | - (JSON file) |

---

## MISJA

```
Doprowadzić system FXcrypto do stanu gdzie TRADER może:
1. Stworzyć strategię wykrywania pump/dump (5 sekcji)
2. Przetestować ją na historii (backtest z equity curve)
3. Uruchomić paper trading (symulacja z sygnałami)
4. Analizować wyniki (wykresy, metryki, P&L)

SUKCES: Trader może przejść cały flow BEZ pomocy technicznej
PORAŻKA: System crashuje, wykresy puste, sygnały nie generują się
```

---

## STRUKTURA AGENTÓW

```
Driver (koordynuje, NIE koduje, AUTONOMICZNY)
    ├── trading-domain  (perspektywa tradera, UX, VETO)
    ├── backend-dev     (Python/FastAPI, logika biznesowa)
    ├── frontend-dev    (Next.js/React, UI)
    ├── database-dev    (QuestDB, dane historyczne)
    └── code-reviewer   (jakość kodu)
```

---

## TRADER JOURNEY - RZECZYWISTE TESTY UI

**To są DOKŁADNE akcje które trader wykonuje w interfejsie:**

---

### POZIOM 1: Dashboard (punkt wejścia)

**Strona: http://localhost:3000/**

| # | Akcja tradera | Gdzie w UI | Test | Dowód |
|---|---------------|------------|------|-------|
| 1.1 | Otwiera dashboard | `/` → PumpDumpDashboard | Frontend renderuje | Brak błędów JS w konsoli |
| 1.2 | Widzi status systemu | SystemStatusIndicator (header) | Połączenie WS | Ikona zielona, "Connected" |
| 1.3 | Widzi symbole | SymbolWatchlist (sidebar) | Lista symboli | BTC_USDT, ETH_USDT widoczne |
| 1.4 | Klika symbol | SymbolWatchlist → click | Dane się ładują | CandlestickChart pokazuje świece |
| 1.5 | Widzi wykres OHLCV | CandlestickChart (main) | Świece z danymi | OHLC + volume > 0 |
| 1.6 | Przełącza symbol | SymbolWatchlist → inny symbol | Wykres się aktualizuje | ETH_USDT dane widoczne |

---

### POZIOM 2: Konfiguracja sesji

**Strona: http://localhost:3000/trading-session**

| # | Akcja tradera | Gdzie w UI | Test | Dowód |
|---|---------------|------------|------|-------|
| 2.1 | Otwiera konfigurację | `/trading-session` | Strona renderuje | Widzi 4 sekcje: Mode, Strategies, Symbols, Budget |
| 2.2 | Wybiera tryb | ToggleButtonGroup (Live/Paper/Backtest) | Tryb się zmienia | Odpowiedni Alert info wyświetla się |
| 2.3 | Widzi listę strategii | Table ze strategiami | API zwraca strategie | Checkboxy działają, strategia zaznaczona |
| 2.4 | Wybiera symbole | Chip buttons z symbolami | Symbole dodają się | SelectedSymbols > 0 |
| 2.5 | Ustawia budżet | TextField: Global Budget | Wartość zapisuje | $1000 USDT widoczne |
| 2.6 | Ustawia SL/TP | TextField: Stop Loss / Take Profit | Wartości ustawiają się | 5% / 10% widoczne |

**Dla BACKTEST dodatkowo:**

| # | Akcja tradera | Gdzie w UI | Test | Dowód |
|---|---------------|------------|------|-------|
| 2.7 | Wybiera sesję danych | Select: Data Collection Session | Dropdown działa | Lista sesji z datami i ilością rekordów |
| 2.8 | Ustawia przyspieszenie | Slider: Acceleration Factor | 1x-100x | Wartość widoczna "10x" |

---

### POZIOM 3: Strategia (5-Section Builder)

**Strona: http://localhost:3000/strategy-builder**

| # | Akcja tradera | Gdzie w UI | Test | Dowód |
|---|---------------|------------|------|-------|
| 3.1 | Otwiera builder | `/strategy-builder` | StrategyBuilder5Section | Widzi 5 sekcji: S1, S2, Z1, Z2, ZE1 |
| 3.2 | Definiuje S1 | Sekcja S1 (Signal Detection) | Dodaje warunek | RSI > 70, VOLUME_SURGE > 2x |
| 3.3 | Definiuje Z1 | Sekcja Z1 (Entry Confirmation) | Dodaje entry | Position size, direction LONG |
| 3.4 | Definiuje ZE1 | Sekcja ZE1 (Exit Strategy) | Dodaje exit | Take Profit 5%, Stop Loss 2% |
| 3.5 | Zapisuje strategię | Button: Save Strategy | API zwraca ID | Toast "Strategy saved" + ID |
| 3.6 | Widzi strategię w liście | `/strategies` | Lista strategii | Nowa strategia widoczna |
| 3.7 | Edytuje strategię | Click → Edit | Dane się ładują | Poprzednie wartości wypełnione |
| 3.8 | Usuwa strategię | Button: Delete | Strategia znika | Lista bez tej strategii |

---

### POZIOM 4: Backtest Session

**Strony: /trading-session → /dashboard?mode=backtest**

| # | Akcja tradera | Gdzie w UI | Test | Dowód |
|---|---------------|------------|------|-------|
| 4.1 | Konfiguruje backtest | `/trading-session` (mode=backtest) | Wybiera strategię + sesję danych | Validation PASS |
| 4.2 | Startuje sesję | Button: "Start BACKTEST Session" | API uruchamia | Redirect do dashboard |
| 4.3 | Widzi status sesji | Alert w headerze | "Session running: backtest_xxx" | Status RUNNING |
| 4.4 | Widzi equity curve | EquityCurveChart | Wykres rysuje się | Linia equity z punktami |
| 4.5 | Widzi drawdown | DrawdownChart | Wykres drawdown | Obszar pod 0% widoczny |
| 4.6 | Widzi transakcje | TransactionHistoryPanel | Lista transakcji | Entry/Exit z cenami i P&L |
| 4.7 | Widzi sygnały | SignalHistoryPanel | Lista sygnałów | S1, Z1, ZE1 z timestamp |
| 4.8 | Rozwija sygnał | Click row → expand | Szczegóły sygnału | indicator_values, conditions_met |
| 4.9 | Widzi metryki | Performance summary | Win rate, PF, Sharpe | Liczby > 0, nie N/A |
| 4.10 | Zatrzymuje sesję | Button: Stop Session | Status = STOPPED | Alert znika lub zmienia kolor |

---

### POZIOM 5: Paper Trading Session

**Strony: /trading-session → /dashboard?mode=paper**

| # | Akcja tradera | Gdzie w UI | Test | Dowód |
|---|---------------|------------|------|-------|
| 5.1 | Konfiguruje paper | `/trading-session` (mode=paper) | Wybiera strategię + symbole | Validation PASS |
| 5.2 | Startuje sesję | Button: "Start PAPER Session" | API uruchamia | Redirect do dashboard |
| 5.3 | Widzi WebSocket | SystemStatusIndicator | WS connected | Zielona ikona |
| 5.4 | Widzi live price | SymbolWatchlist / CandlestickChart | Ceny się aktualizują | Price zmienia się w czasie |
| 5.5 | Widzi sygnał live | SignalHistoryPanel | Nowy sygnał pojawia się | Flash/highlight nowego wiersza |
| 5.6 | Widzi pozycję | PositionMonitor | Otwarta pozycja | Entry price, Unrealized P&L |
| 5.7 | Widzi transakcję | TransactionHistoryPanel | Filled order | Cena entry, timestamp |
| 5.8 | Widzi indicator live | LiveIndicatorPanel | Wartości wskaźników | RSI, MACD aktualne |
| 5.9 | Zatrzymuje sesję | Button: Stop Session | Status = STOPPED | Pozycje zamknięte |

---

### POZIOM 6: Live Trading Session

**Strony: /trading-session + /settings → /dashboard?mode=live**

| # | Akcja tradera | Gdzie w UI | Test | Dowód |
|---|---------------|------------|------|-------|
| 6.1 | Konfiguruje API | `/settings` → MEXC credentials | API key + secret | Connection test PASS |
| 6.2 | Konfiguruje risk | `/risk-management` | Limits ustawione | Max position, daily loss |
| 6.3 | Startuje live | `/trading-session` (mode=live) + Start | API uruchamia | RED warning confirmed |
| 6.4 | Widzi real balance | WalletBalance | Prawdziwe USDT | Saldo z giełdy |
| 6.5 | Widzi real order | OrderHistory | Zlecenie na giełdzie | Order ID z MEXC |
| 6.6 | Widzi risk alerts | RiskAlerts | Ostrzeżenia | Jeśli przekroczone limity |

---

### POZIOM 7: Data Collection

**Strona: http://localhost:3000/data-collection**

| # | Akcja tradera | Gdzie w UI | Test | Dowód |
|---|---------------|------------|------|-------|
| 7.1 | Widzi sesje | Lista sesji | API zwraca dane | Session ID, symbols, count |
| 7.2 | Startuje zbieranie | Button: Start Collection | Nowa sesja | Status = RUNNING |
| 7.3 | Widzi postęp | Progress indicator | Dane napływają | Count rośnie |
| 7.4 | Zatrzymuje | Button: Stop | Status = COMPLETED | Dane zapisane |
| 7.5 | Widzi wykres danych | `/data-collection/[id]/chart` | Chart z OHLCV | Historyczne świece |

---

## SZYBKA WERYFIKACJA POZIOMÓW

**Driver: użyj tych komend przed delegowaniem, żeby wiedzieć gdzie jest problem:**

```bash
# POZIOM 1: Dashboard
curl -s http://localhost:8080/health | jq '.status'
# Oczekiwane: "healthy"

curl -s http://localhost:8080/api/symbols | jq '. | length'
# Oczekiwane: > 0 (lista symboli)

# POZIOM 2: Konfiguracja sesji
curl -s http://localhost:8080/api/strategies | jq '. | length'
# Oczekiwane: > 0 (są strategie)

curl -s http://localhost:8080/api/data-collection/sessions | jq '.sessions | length'
# Oczekiwane: > 0 (są sesje danych)

# POZIOM 3: Strategy Builder
curl -s -X POST http://localhost:8080/api/strategies \
  -H "Content-Type: application/json" \
  -d '{"strategy_name":"test_strat","enabled":true}' | jq '.strategy_name'
# Oczekiwane: "test_strat"

# POZIOM 4: Backtest
# Najpierw uruchom sesję, potem:
curl -s "http://localhost:8080/sessions/{SESSION_ID}/equity" | jq '.data | length'
# Oczekiwane: > 10 (punkty equity)

curl -s "http://localhost:8080/sessions/{SESSION_ID}/signals" | jq '. | length'
# Oczekiwane: > 0 (sygnały wygenerowane)

# POZIOM 5: Paper Trading
curl -s "http://localhost:8080/sessions/{SESSION_ID}/positions" | jq '. | length'
# Jeśli sygnały → powinny być pozycje

# POZIOM 7: Data Collection
curl -s "http://localhost:9000/exec?query=SELECT%20count()%20FROM%20ohlcv_1m"
# Oczekiwane: > 0 (dane w QuestDB)
```

---

## TESTOWANIE TRADER JOURNEY

### Jak testować (PRAWDZIWE interakcje UI):

```python
# TEST 1.4: Symbol click → dane się ładują
def test_symbol_click_loads_data():
    """Trader klika symbol w SymbolWatchlist"""
    # 1. Otwórz dashboard
    page = browser.goto("http://localhost:3000")

    # 2. Znajdź i kliknij symbol
    symbol_btn = page.locator("[data-testid='symbol-BTC_USDT']")
    symbol_btn.click()

    # 3. PRAWDZIWE ASERCJE:
    chart = page.locator("[data-testid='candlestick-chart']")
    assert chart.is_visible(), "Wykres musi być widoczny"

    # 4. Sprawdź że są dane (nie placeholder)
    candles = chart.locator(".candle")
    assert candles.count() > 0, "Muszą być świece"
```

```python
# TEST 4.4: Equity curve z danymi (backtest)
def test_backtest_equity_curve():
    """Po uruchomieniu backtestu equity curve się rysuje"""
    # 1. Uruchom backtest przez API
    session = api.start_session({
        "session_type": "backtest",
        "strategy_config": {"pump_detector": ["BTC_USDT"]},
        "config": {"session_id": data_session_id}
    })

    # 2. Czekaj na zakończenie
    wait_for_session_complete(session.id, timeout=60)

    # 3. Pobierz equity curve
    equity = api.get_equity_curve(session.id)

    # 4. PRAWDZIWE ASERCJE:
    assert len(equity) > 10, "Musi być > 10 punktów"
    assert equity[0]["value"] != equity[-1]["value"], "Wartości się zmieniają"
    assert all(e["timestamp"] for e in equity), "Timestamps są"
```

```python
# TEST 5.5: Sygnał pojawia się w SignalHistoryPanel (paper trading)
def test_paper_trading_signal_appears():
    """Trader widzi nowe sygnały w real-time"""
    # 1. Uruchom paper trading
    session = api.start_session({
        "session_type": "paper",
        "strategy_config": {"pump_detector": ["BTC_USDT"]},
        "symbols": ["BTC_USDT"]
    })

    # 2. Czekaj na sygnały (max 60s)
    signals = wait_for_signals(session.id, timeout=60)

    # 3. PRAWDZIWE ASERCJE:
    assert len(signals) > 0, "Powinny być sygnały"
    for signal in signals:
        assert signal["signal_type"] in ["S1", "S2", "Z1", "Z2", "ZE1"]
        assert signal["indicator_values"], "Muszą być wartości wskaźników"
        assert signal["conditions_met"], "Muszą być warunki"
```

```python
# TEST 7.5: Data collection chart pokazuje dane
def test_data_collection_chart():
    """Trader przegląda zebrane dane historyczne"""
    # 1. Pobierz listę sesji
    sessions = api.get_data_collection_sessions()
    assert len(sessions) > 0, "Muszą być sesje"

    # 2. Otwórz chart
    page = browser.goto(f"/data-collection/{sessions[0].id}/chart")

    # 3. PRAWDZIWE ASERCJE:
    chart = page.locator("[data-testid='ohlcv-chart']")
    assert chart.is_visible()
    candles = chart.locator(".candle")
    assert candles.count() > 0, "Muszą być świece"
```

---

## DRIVER: AUTONOMICZNA PĘTLA

```
START SESJI
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  1. ANALIZA                                                 │
│     • Trader Journey Check (poziomy 1-5)                    │
│     • Który poziom nie działa?                              │
│     • Co blokuje tradera?                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  2. ROADMAPA SESJI                                          │
│     • Cel: Naprawić poziom X                                │
│     • Plan: Które testy muszą przejść                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  3. DECYZJA (algorytm)                                      │
│     Poziom 1 ❌ → Napraw Dashboard (frontend)               │
│     Poziom 2 ❌ → Napraw Konfigurację sesji                 │
│     Poziom 3 ❌ → Napraw Strategy Builder                   │
│     Poziom 4 ❌ → Napraw Backtest                           │
│     Poziom 5 ❌ → Napraw Paper Trading                      │
│     Poziom 6 ❌ → Napraw Live Trading                       │
│     Poziom 7 ❌ → Napraw Data Collection                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  4. DELEGACJA                                               │
│     • Do którego agenta                                     │
│     • Co dokładnie naprawić                                 │
│     • Jak zweryfikować sukces                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  5. WERYFIKACJA                                             │
│     • Test przeszedł?                                       │
│     • Trader może wykonać akcję?                            │
│     • Dane są prawdziwe (nie placeholder)?                  │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    SUKCES                  PORAŻKA
         │                       │
    Update status          Feedback/Eskaluj
         │                       │
         └───────────┬───────────┘
                     │
              NASTĘPNA ITERACJA
                     │
              (aż wszystkie poziomy ✅)
```

---

## FAZA 1: ANALIZA

```markdown
## ANALIZA STANU - [data]

### Trader Journey Status

| Poziom | Status | Blokuje |
|--------|--------|---------|
| 1. Dashboard | ✅/❌ | Wszystko |
| 2. Konfiguracja sesji | ✅/❌ | Poziom 4-6 |
| 3. Strategy Builder | ✅/❌ | Poziom 4-6 |
| 4. Backtest | ✅/❌ | - |
| 5. Paper Trading | ✅/❌ | Poziom 6 |
| 6. Live Trading | ✅/❌ | - |
| 7. Data Collection | ✅/❌ | Poziom 4 (backtest) |

### Który test FAIL?
[Konkretny test np. "3.3 Equity curve pusta"]

### Co trader widzi?
[Opis z perspektywy użytkownika]
```

---

## FAZA 2: ROADMAPA SESJI

```markdown
## ROADMAPA SESJI - [data]

### CEL: Naprawić Poziom [X]

### Które testy muszą przejść:
| Test | Opis | Agent |
|------|------|-------|
| X.1 | [opis] | [agent] |
| X.2 | [opis] | [agent] |

### Kryterium sukcesu:
[Co trader będzie mógł zrobić po naprawie]
```

---

## FAZA 3: ALGORYTM PRIORYTETYZACJI

```
1. POZIOM 1 NIE DZIAŁA? (Dashboard)
   → Frontend crash, błędy JS, SymbolWatchlist nie ładuje
   → Napraw NAJPIERW (blokuje wszystko)

2. POZIOM 2 NIE DZIAŁA? (Konfiguracja sesji)
   → /trading-session nie działa, strategie nie ładują
   → Napraw (blokuje uruchomienie sesji)

3. POZIOM 3 NIE DZIAŁA? (Strategy Builder)
   → Trader nie może stworzyć/zapisać strategii
   → Napraw (blokuje backtesty i trading)

4. POZIOM 4 NIE DZIAŁA? (Backtest)
   → Equity curve pusta, brak transakcji w panelu
   → Napraw

5. POZIOM 5 NIE DZIAŁA? (Paper Trading)
   → Brak sygnałów w SignalHistoryPanel, pozycje nie otwierają się
   → Napraw (blokuje live)

6. POZIOM 6 NIE DZIAŁA? (Live Trading)
   → Połączenie z MEXC fail, zlecenia nie wykonują się
   → Napraw

7. POZIOM 7 NIE DZIAŁA? (Data Collection)
   → Brak danych do backtestów
   → Napraw (blokuje backtest)
```

---

## MATRYCA DELEGACJI

| Problem | Komponent UI | Symptom | Agent |
|---------|--------------|---------|-------|
| Dashboard nie renderuje | PumpDumpDashboard | Błędy JS w konsoli | frontend-dev |
| Symbole nie ładują | SymbolWatchlist | Lista pusta | backend-dev (API) |
| Wykres OHLCV pusty | CandlestickChart | Brak świec | database-dev (QuestDB) |
| Sesja nie startuje | SessionConfigDialog | Button disabled / error | backend-dev (/sessions/start) |
| Strategia nie zapisuje | StrategyBuilder5Section | Toast error | backend-dev (strategy API) |
| Equity curve pusta | EquityCurveChart | Linia płaska | backend-dev (backtest engine) |
| Sygnały nie pojawiają | SignalHistoryPanel | Tabela pusta | backend-dev (indicator engine) |
| Pozycje nie otwierają | PositionMonitor | Lista pusta | backend-dev (paper trading) |
| Live orders fail | OrderHistory | Błąd MEXC | backend-dev (MEXC adapter) |
| Data collection fail | /data-collection | Sesja nie startuje | backend-dev + database-dev |

---

## URUCHAMIANIE I RESTART USŁUG

### Uruchomienie wszystkich usług:
```powershell
.\start_all.ps1
```

Uruchamia:
- QuestDB (port 9000, 8812)
- Backend API (port 8080)
- Frontend UI (port 3000)

### Restart backendu:
```powershell
.\restart_backend.ps1

# Lub ręcznie:
# Ctrl+C w terminalu z backendem
python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8080 --reload
```

### Restart frontendu:
```bash
cd frontend && npm run dev
```

### Weryfikacja że działa:
```bash
# Backend
curl http://localhost:8080/health
# → {"status": "healthy"}

# Frontend
# Otwórz http://localhost:3000 w przeglądarce
# → Dashboard renderuje bez błędów
```

---

## TYPY PROBLEMÓW

### TYP A: Problem KODU
- Funkcja zwraca błędny wynik
- Brak implementacji
- Edge case nie obsłużony

**PROCES:** TDD (RED → GREEN → REFACTOR)

### TYP B: Problem INFRASTRUKTURY
- Usługa nie odpowiada
- Port zajęty
- QuestDB nie działa

**PROCES:**
```powershell
# 1. Sprawdź czy usługa działa
netstat -an | findstr "8080"   # Backend
netstat -an | findstr "3000"   # Frontend
netstat -an | findstr "9000"   # QuestDB

# 2. Restart
.\start_all.ps1
# lub restart konkretnej usługi

# 3. Weryfikuj
curl http://localhost:8080/health
```

### TYP C: Problem DANYCH
- Brak danych historycznych
- Data collection nie zebrana
- QuestDB pusta

**PROCES:**
1. Sprawdź czy są dane: `GET /api/data-collection/sessions`
2. Jeśli brak → uruchom data collection
3. Weryfikuj: powinny być OHLCV dane

---

## RAPORT PO ZADANIU

```markdown
## RAPORT: [zadanie]

### STATUS
[Co zrobiłem]

### TRADER JOURNEY
Test [X.Y]: ❌ → ✅

### DOWODY
[Screenshot lub output pokazujący że TRADER może wykonać akcję]

### ZMIANY
| Plik:linia | Zmiana |
|------------|--------|

### CO TRADER TERAZ MOŻE ROBIĆ
[Opis z perspektywy użytkownika]
```

---

## TRADING-DOMAIN: OCENA UX

```markdown
## OCENA UX: [funkcja]

### Scenariusz
Trader chce: [cel]

### Kroki:
1. [co klika]
2. [co widzi]
3. [co robi dalej]

### Checklist
- [ ] Osiągalne w < 5 kliknięć?
- [ ] Oczywiste co robić (bez dokumentacji)?
- [ ] Błędy zrozumiałe?
- [ ] Można cofnąć?

### WERDYKT: PASS / FAIL
```

### KIEDY UŻYĆ VETO

Trading-domain może zablokować zmianę jeśli:

| Sytuacja | Przykład | Akcja |
|----------|----------|-------|
| UX uniemożliwia flow | Przycisk "Start" schowany za 10 kliknięć | VETO + propozycja zmiany |
| Błąd bez wyjaśnienia | "Error 500" zamiast "Brak danych do backtestu" | VETO + wymóg user-friendly błędu |
| Utrata danych | Edycja strategii bez potwierdzenia nadpisuje | VETO + wymóg confirmation dialog |
| Wolne UI | Ładowanie > 5s bez loading indicator | VETO + wymóg skeleton/spinner |

**Format VETO:**
```markdown
## VETO: [funkcja]
### Problem
[Co trader nie może zrobić]
### Wymaganie
[Co musi być zmienione]
### Blokuje
[Które testy Trader Journey są zablokowane]
```

---

## CODE-REVIEWER: CHECKLIST

```markdown
### JAKOŚĆ KODU
- [ ] Nowy kod ma testy jednostkowe
- [ ] Edge cases: null, empty, timeout obsłużone
- [ ] Error handling: konkretne wyjątki (nie bare except)
- [ ] Logowanie: błędy logowane z kontekstem

### ARCHITEKTURA (ten projekt)
- [ ] API: FastAPI router z Pydantic models
- [ ] Frontend: React hooks + Zustand store
- [ ] Baza: QuestDB przez HTTP API lub PostgreSQL wire
- [ ] Brak breaking changes w API (backwards compatible)

### TRADER JOURNEY (7 poziomów!)
- [ ] Nie psuje żadnego testu z poziomów 1-7
- [ ] Błędy zrozumiałe dla tradera (nie stack trace)
- [ ] UI pokazuje loading state podczas ładowania

### SZYBKA WERYFIKACJA
Uruchom komendy z sekcji "SZYBKA WERYFIKACJA POZIOMÓW"
i sprawdź że wszystkie zwracają oczekiwane wartości.
```

---

## CIRCUIT BREAKER

```
Max 3 iteracje na jeden problem.

Po 3 iteracjach BEZ POSTĘPU → ESKALUJ:
- Co próbowałem (3 podejścia)
- Dlaczego nie działa
- Propozycja zmiany zakresu
```

---

## RAPORT KOŃCOWY SESJI

```markdown
## SESJA [data] - PODSUMOWANIE

### Trader Journey Status
| Poziom | Przed | Po |
|--------|-------|-----|
| 1. Dashboard | ❌/✅ | ✅ |
| 2. Konfiguracja sesji | ❌/✅ | ✅ |
| 3. Strategy Builder | ❌/✅ | ✅ |
| 4. Backtest | ❌/✅ | ✅ |
| 5. Paper Trading | ❌/✅ | ✅ |
| 6. Live Trading | ❌/✅ | ✅ |
| 7. Data Collection | ❌/✅ | ✅ |

### Co trader TERAZ może robić
[Lista konkretnych akcji w UI, np. "uruchomić backtest i zobaczyć equity curve"]

### Otwarte problemy
| Test | Komponent | Problem |
|------|-----------|---------|

### Następna sesja
1. Naprawić: [test X.Y w poziomie Z]
2. Komponent: [nazwa komponentu]
```

---

## REGUŁY BEZWZGLĘDNE

### ZAWSZE
- ✅ Testuj z perspektywy TRADERA (co widzi w UI, nie jaki HTTP code)
- ✅ Dowody = screenshot komponentu lub output z prawdziwymi danymi
- ✅ Naprawiaj od Poziomu 1 w górę (Dashboard → Konfiguracja → ... → Live)
- ✅ Odwołuj się do nazw komponentów (SignalHistoryPanel, EquityCurveChart)

### NIGDY
- ❌ curl /health jako "dowód" że działa
- ❌ "Testy PASS" bez sprawdzenia czy trader może używać
- ❌ Docker (nie mamy!)

---

**Wersja:** 15.0 | **Zmieniono:** 2025-12-05

## CHANGELOG

### v14 → v15

| Zmiana | Uzasadnienie |
|--------|--------------|
| Dodano sekcję "DOKUMENTACJA UI" | Referencje do UI_INTERFACE_SPECIFICATION.md i UI_BACKLOG.md |
| Instrukcje aktualizacji dokumentów | Agenci wiedzą kiedy i jak aktualizować dokumentację UI |
| Prompt do oceny UI | Jak wcielić się w tradera i ocenić interfejs |

### v13 → v14

| Zmiana | Uzasadnienie |
|--------|--------------|
| Dodano "CEL PROGRAMU" | Agent rozumie CO system ma robić, nie tylko JAK testować |
| Dodano "ARCHITEKTURA TECHNICZNA" | Agent wie gdzie są pliki, jakie technologie |
| Dodano "MAPOWANIE UI → API → DB" | Agent wie skąd komponent bierze dane |
| Dodano "SZYBKA WERYFIKACJA POZIOMÓW" | Driver może w 30s sprawdzić gdzie jest problem |
| Dodano proces VETO dla trading-domain | Jasne kiedy można blokować i jak |
| Naprawiono code-reviewer checklist | "poziomów 1-7" zamiast błędnego "1-5" |
| Checklist specyficzny dla projektu | FastAPI, Zustand, QuestDB - nie ogólne zasady |

### v12 → v13

| Zmiana | Uzasadnienie |
|--------|--------------|
| Trader Journey odzwierciedla funkcjonalność UI | Każdy test ma: stronę, komponent, akcję |
| 7 poziomów zamiast 5 | Dashboard, Konfiguracja sesji, Strategia, Backtest, Paper, Live, Data Collection |
| Dodano nazwy komponentów | SymbolWatchlist, SignalHistoryPanel, EquityCurveChart etc. |

### v11 → v12

| Zmiana | Uzasadnienie |
|--------|--------------|
| Usunięto Docker | Nie używamy - wszystko przez start_all.ps1 |
| Usunięto grepy security | Nie mieliśmy takich problemów |
| Dodano PRAWDZIWY Trader Journey | 5 poziomów z konkretnymi testami |
