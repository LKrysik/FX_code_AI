# TODO - Plan napraw

## Deep Verify F1: Live Trading (2026-01-20)

### BUG-DV-001: Signature mismatch w close_position [CRITICAL]

**Problem:** API wywołuje `close_position()` z niepoprawnymi parametrami. Endpoint crashuje z TypeError.

**Lokalizacja:**
- Wywołanie: `src/api/trading_routes.py:497-503`
- Implementacja: `src/domain/services/order_manager_live.py:668`

**Szczegóły:**
```python
# API wywołuje (trading_routes.py:497):
await live_order_manager.close_position(
    session_id=session_id,
    symbol=symbol,
    quantity=position["quantity"],
    side=reverse_side,
    reason=request.reason
)

# Metoda oczekuje (order_manager_live.py:668):
async def close_position(self, position_id: str, symbol: str,
                         quantity: float, current_price: float) -> bool:
```

**Do naprawy:**
1. Zmienić wywołanie w `trading_routes.py` na zgodne z sygnaturą:
   ```python
   await live_order_manager.close_position(
       position_id=position_id,
       symbol=symbol,
       quantity=position["quantity"],
       current_price=position["current_price"]
   )
   ```
2. LUB rozszerzyć sygnaturę `LiveOrderManager.close_position()` o parametry `side` i `reason`

**Testy:** Dodać test jednostkowy dla `POST /api/trading/positions/:id/close`

---

### BUG-DV-002: Hardcoded exit_side="sell" [CRITICAL]

**Problem:** `close_position()` w LiveOrderManager zakłada że wszystkie pozycje to LONG. Zamknięcie SHORT pozycji POWIĘKSZY pozycję zamiast ją zamknąć (finansowa strata).

**Lokalizacja:** `src/domain/services/order_manager_live.py:685-689`

**Szczegóły:**
```python
# Kod obecnie:
# TODO: Implement position side detection from Position object
exit_side = "sell"  # <-- ZAWSZE sell, nawet dla SHORT
```

**Do naprawy:**
```python
# Poprawna logika:
if position_side == "LONG":
    exit_side = "sell"
elif position_side == "SHORT":
    exit_side = "buy"
```

Wymaga przekazania `side` z pozycji do metody (patrz BUG-DV-001).

**Testy:** Test zamknięcia LONG i SHORT pozycji - sprawdzić że generuje prawidłowy `exit_side`

---

### BUG-DV-003: Case inconsistency w polu 'side' [IMPORTANT]

**Problem:** Niespójność wielkości liter między modułami może powodować ciche błędy.

**Lokalizacja:**
- `src/api/trading_routes.py:493` używa: `"LONG"`, `"SHORT"`, `"SELL"`, `"BUY"`
- `src/domain/services/order_manager_live.py:55` (docstring) używa: `"buy"`, `"sell"`

**Do naprawy:**
1. Wybrać jedną konwencję (rekomendacja: UPPERCASE per MEXC API)
2. Dodać normalizację `.upper()` przy porównaniach lub na granicy API

---

### INFO-DV-001: Single-instance position lock [MINOR]

**Problem:** `PositionLockManager` używa `asyncio.Lock` - działa tylko w single-instance deployment.

**Lokalizacja:** `src/domain/services/position_lock_manager.py:28`

**Status:** Udokumentowane ograniczenie. Jeśli planowane jest horizontal scaling, wymaga Redis-based distributed lock.

---

### BUG-DV-004: File-based strategy persistence violates architecture [CRITICAL]

**Problem:** Konfiguracja strategii jest aktualnie zapisywana i odczytywana z plików JSON w systemie plików (`config/strategies/`) zamiast z dedykowanej bazy danych (QuestDB), co jest niezgodne z wymaganiami architektonicznymi.

**Lokalizacja:**
- Decyzja Architektoniczna: `docs/architecture/DECISIONS.md` (ADR-002) - wskazuje na plikowy system.
- Potencjalne miejsca zapisu/odczytu: `src/api/websocket_server.py`, `src/api/websocket/handlers/strategy_handler.py`, inne moduły operujące na strategiach.
- Związane ryzyka: `docs/architecture/DECISIONS.md` (ADR-002) - ryzyko konfliktów współbieżności i uszkodzenia danych.

**Szczegóły:**
System został pierwotnie zaprojektowany z myślą o przechowywaniu strategii w plikach JSON, co zostało udokumentowane w ADR-002. Jednak aktualne wymagania architektoniczne jasno wskazują na konieczność przechowywania wszystkich konfiguracji w bazie danych. Implementacja oparta na plikach niesie ze sobą ryzyka takie jak:
- Konflikty współbieżności przy jednoczesnym dostępie (brak szczegółów implementacji blokowania plików).
- Uszkodzenie danych w przypadku awarii systemu podczas zapisu (brak mechanizmu atomowego zapisu).
- Trudności w zarządzaniu danymi w środowisku skalowalnym.

**Do naprawy:**
1.  **Usuń logikę plikową:** Zlokalizuj i usuń wszelkie operacje zapisu i odczytu strategii z plików JSON.
2.  **Zaprojektuj schemat DB:** Stwórz tabelę `strategies` w QuestDB z kolumnami takimi jak `id`, `name`, `definition` (JSON jako STRING), `created_at`, `updated_at`.
3.  **Zaimplementuj repozytorium DB:** Stwórz nową klasę repozytorium (np. `StrategyDBRepository`) odpowiedzialną za operacje CRUD na tabeli `strategies` w QuestDB.
4.  **Zaktualizuj API:** Zmodyfikuj endpointy API (REST/WebSocket), aby korzystały z nowego repozytorium bazodanowego.
5.  **Zaktualizuj Container:** Upewnij się, że system wstrzykuje nowe repozytorium DB tam, gdzie jest potrzebne.
6.  **Migracja danych (opcjonalnie):** W przypadku istniejących plików strategii, należy opracować skrypt migracyjny do przeniesienia ich do bazy danych.

**Testy:**
- Testy integracyjne dla operacji CRUD strategii w bazie danych.
- Testy end-to-end weryfikujące tworzenie, edycję i ładowanie strategii przez interfejs użytkownika.

---

### BUG-DV-005: Missing realism models in Backtest UI [CRITICAL]

**Problem:** Okno dialogowe konfiguracji sesji backtestingu nie zawiera opcji wyboru modelu realizmu symulacji (poślizg cenowy i prowizje).

**Lokalizacja:**
- Brakujący komponent: `frontend/src/components/dashboard/SessionConfigDialog.tsx`
- Wymaganie projektowe: `docs/_archive/MVP.md`

**Szczegóły:**
Brak tej opcji w UI zmusza backend do używania domyślnego trybu "idealnego" (zero kosztów transakcyjnych). Prowadzi to do generowania nierealistycznych, nadmiernie optymistycznych wyników backtestów. Użytkownik, nieświadomy tego faktu, może podjąć decyzje o handlu na żywo na podstawie mylących danych, co stwarza wysokie ryzyko strat finansowych.

**Do naprawy:**
1.  **Dodaj opcje w UI:** W komponencie `SessionConfigDialog.tsx`, w sekcji konfiguracji backtestu, dodaj kontrolki (np. `Select` lub `Slider`) do wyboru:
    - **Modelu Poślizgu (Slippage):** z opcjami np. "Brak (idealny)", "Stały procent", "Realistyczny".
    - **Modelu Prowizji (Fees):** z opcjami np. "Brak", "Standardowa (0.1%)".
2.  **Ustaw domyślne wartości:** Rekomendowane jest ustawienie "Realistycznego" / "Standardowego" modelu jako domyślnego, aby chronić użytkowników.
3.  **Zaktualizuj `SessionConfig`:** Rozszerz interfejs `SessionConfig` oraz logikę `handleSubmit`, aby przekazywać wybrane modele do API backendu.

**Testy:**
- Testy komponentu `SessionConfigDialog`, weryfikujące, że nowe pola istnieją i ich wartości są poprawnie przekazywane przy submisji formularza.
- Test E2E sprawdzający, czy uruchomienie backtestu z modelem "realistycznym" daje inne (niższe) wyniki P&L niż z modelem "idealnym".

---

---

## Deep Verify F4: Strategy Management (2026-01-20)

**Verdict: REJECT** (S = 6.5)

### BUG-DV-013: Dwie niespójne ścieżki persystencji strategii [CRITICAL]

**Problem:** WebSocket `UPSERT_STRATEGY` zapisuje strategie do plików (`config/strategies/`), podczas gdy REST API używa QuestDB. Strategie utworzone przez WebSocket są **TRACONE PO RESTARCIE** serwera, bo `load_strategies_from_db()` czyta tylko z QuestDB.

**Lokalizacja:**
- WebSocket (BŁĘDNE): `src/api/websocket_server.py:1947-1952`
- WebSocket handler (BŁĘDNE): `src/api/websocket/handlers/strategy_handler.py:574-579`
- REST API (POPRAWNE): `src/api/unified_server.py:922`
- Load from DB: `src/domain/services/strategy_manager.py:1321-1343`

**Szczegóły:**
```python
# WebSocket UPSERT (websocket_server.py:1949-1952) - BŁĘDNE:
os.makedirs(os.path.join("config", "strategies"), exist_ok=True)
path = os.path.join("config", "strategies", f"{cfg['strategy_name']}.json")
with open(path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)

# REST API (unified_server.py:922) - POPRAWNE:
strategy_id = await strategy_storage.create_strategy(strategy_data)

# Load zawsze z QuestDB (strategy_manager.py:1335-1343):
rows = await conn.fetch("SELECT ... FROM strategies WHERE enabled = true")
```

**Do naprawy:**
1. Zmienić `websocket_server.py:1947-1952` aby używać `QuestDBStrategyStorage.create_strategy()`
2. Zmienić `strategy_handler.py:574-579` analogicznie
3. Usunąć tworzenie katalogu `config/strategies/` z kodu
4. LUB: Usunąć WebSocket UPSERT i kierować użytkowników na REST API

**Testy:**
- Test tworzenia strategii przez WebSocket i weryfikacja persystencji w QuestDB
- Test przetrwania strategii po restarcie serwera

---

### BUG-DV-014: Direction "BOTH" nie zaimplementowane [IMPORTANT]

**Problem:** `Strategy.direction` przyjmuje wartość "BOTH", ale `get_entry_order_type()` rzuca wyjątek dla tej wartości. Użytkownik może ustawić "BOTH" w UI, ale wykonanie strategii zakończy się błędem.

**Lokalizacja:** `src/domain/services/strategy_manager.py:190-195`

**Szczegóły:**
```python
def get_entry_order_type(self) -> OrderType:
    if self.direction == "LONG":
        return OrderType.BUY
    elif self.direction == "SHORT":
        return OrderType.SHORT
    else:
        raise ValueError(f"Unsupported direction for single entry: {self.direction}...")
```

**Do naprawy:**
1. Zaimplementować obsługę "BOTH" (np. generowanie dwóch sygnałów)
2. LUB usunąć "BOTH" z dozwolonych wartości w walidacji
3. LUB dodać jasny komunikat w UI że "BOTH" nie jest wspierane

---

---

## Deep Verify F5: WebSocket API (2026-01-20)

**Verdict: REJECT** (S = 9.5)

### BUG-DV-015: Brak uwierzytelnienia na krytycznych handlerach strategii [CRITICAL]

**Problem:** Handlery `_handle_activate_strategy`, `_handle_deactivate_strategy`, `_handle_upsert_strategy` NIE sprawdzają uwierzytelnienia. Atakujący może bez autoryzacji aktywować/dezaktywować strategie i modyfikować ich konfigurację.

**Lokalizacja:** `src/api/websocket_server.py`
- `_handle_activate_strategy`: linie 1683-1757 - **BRAK `authenticated` check**
- `_handle_deactivate_strategy`: linie 1759-1814 - **BRAK `authenticated` check**
- `_handle_upsert_strategy`: linie 1919-1976 - **BRAK `authenticated` check**

**Szczegóły:**
```python
# Handlery BEZ sprawdzania uwierzytelnienia:
async def _handle_activate_strategy(self, client_id: str, message: Dict[str, Any]):
    # ... BRAK: if not getattr(connection, 'authenticated', False): return error
    success = self.strategy_manager.activate_strategy_for_symbol(strategy_name, symbol)

# Dla porównania - handler Z uwierzytelnieniem:
async def _handle_session_start(self, client_id: str, message: Dict[str, Any]):
    connection = await self.connection_manager.get_connection(client_id)
    if not getattr(connection, 'authenticated', False):  # ✓ Jest sprawdzenie
        return {"type": "error", "error_code": "authentication_required", ...}
```

**Do naprawy:**
1. Dodać sprawdzenie uwierzytelnienia na początku każdego handlera:
   ```python
   connection = await self.connection_manager.get_connection(client_id)
   if not getattr(connection, 'authenticated', False):
       return {
           "type": MessageType.ERROR,
           "error_code": "authentication_required",
           "error_message": "Authentication required for strategy operations",
           "timestamp": datetime.now().isoformat()
       }
   ```
2. Rozważyć dodanie middleware auth w `MessageRouter.route_message()` dla wszystkich handlerów

**Testy:**
- Test że nieuwierzytelniony klient otrzymuje błąd przy próbie aktywacji/dezaktywacji strategii
- Test że uwierzytelniony klient może aktywować/dezaktywować strategie

---

### BUG-DV-016: Brak uwierzytelnienia na session_stop [CRITICAL]

**Problem:** Handler `_handle_session_stop` NIE sprawdza uwierzytelnienia. Atakujący może bez autoryzacji zatrzymać aktywne sesje tradingowe innych użytkowników.

**Lokalizacja:** `src/api/websocket_server.py:2428-2490`

**Szczegóły:**
```python
async def _handle_session_stop(self, client_id: str, message: Dict[str, Any]):
    # BRAK sprawdzenia uwierzytelnienia!
    if not self.controller:
        return error
    # ... od razu wywołuje stop
    await self.controller.stop_execution()
```

**Do naprawy:**
1. Dodać sprawdzenie uwierzytelnienia (jak wyżej)
2. Opcjonalnie: sprawdzić czy user ma permission `EXECUTE_LIVE_TRADING`

---

### BUG-DV-017: Brak uwierzytelnienia na pozostałych handlerach [IMPORTANT]

**Problem:** Kolejne handlery nie sprawdzają uwierzytelnienia:
- `_handle_get_strategies` (line 1612) - ekspozycja konfiguracji strategii
- `_handle_get_strategy_status` (line 1816) - ekspozycja stanu strategii
- `_handle_session_status` (line 2492) - ekspozycja stanu sesji

**Lokalizacja:** `src/api/websocket_server.py`

**Do naprawy:**
1. Dodać sprawdzenie uwierzytelnienia na wszystkich handlerach operujących na danych użytkownika
2. `_handle_validate_strategy_config` może pozostać publiczny (tylko walidacja, bez side effects)

---

### BUG-DV-018: Handshake nie jest wymuszony [IMPORTANT]

**Problem:** Komentarz w kodzie mówi: "Graceful fallback for clients without handshake" (linia 1997). Oznacza to, że handshake - opisany jako "CRITICAL SECURITY FEATURE" - nie jest wymuszony.

**Lokalizacja:** `src/api/websocket_server.py:1997`

**Szczegóły:**
```python
# Komentarz w _handle_handshake:
# - Graceful fallback for clients without handshake  # <-- handshake opcjonalny!
# - Maintains backward compatibility with existing connections
```

**Do naprawy:**
1. Opcja A: Wymusić handshake - odrzucać połączenia bez handshake po grace period
2. Opcja B: Usunąć handshake jeśli nie jest wymagany (uprościć kod)
3. Opcja C: Zostawić opcjonalny ale wyraźnie udokumentować w Security Policy

---

## Priorytet napraw

### CRITICAL (blokują deploy):
1. **BUG-DV-015** - WebSocket API: brak auth na strategy handlers (**SECURITY**)
2. **BUG-DV-016** - WebSocket API: brak auth na session_stop (**SECURITY**)
3. **BUG-DV-001** + **BUG-DV-002** - Live Trading close_position (zależne)
4. **BUG-DV-013** - Strategy Management: dwie ścieżki persystencji (utrata danych)
5. **BUG-DV-004** - File-based strategy persistence (związane z BUG-DV-013)

### IMPORTANT (warunki akceptacji):
6. **BUG-DV-017** - WebSocket API: brak auth na pozostałych handlerach
7. **BUG-DV-018** - WebSocket API: handshake nieforcowany
8. **BUG-DV-005** - Backtest UI: brak opcji realizmu
9. **BUG-DV-014** - Direction "BOTH" niezaimplementowane
10. **BUG-DV-003** - Case inconsistency w polu 'side'

### LOWER PRIORITY:
11. **INFO-DV-001** - Single-instance lock (backlog)

---

---

## Deep Verify F6: Indicator System (2026-01-20)

**Verdict: UNCERTAIN** (S = 4.0) - Requires immediate attention

### BUG-DV-019: RSI Algorithm uses undefined `get_int` method [CRITICAL]

**Problem:** `RSIAlgorithm.calculate_from_windows()` calls `params.get_int("period", 14)`, but `IndicatorParameters` class only defines `get_float()`, not `get_int()`. This causes an `AttributeError` at runtime when RSI is calculated through the time-driven scheduler.

**Lokalizacja:**
- Bug: `src/domain/services/indicators/rsi.py:133`
- Missing method: `src/domain/services/indicators/base_algorithm.py:52-75`

**Szczegóły:**
```python
# RSI używa (rsi.py:133):
period = params.get_int("period", 14)  # ← METODA NIE ISTNIEJE!

# IndicatorParameters ma tylko (base_algorithm.py:62-65):
def get_float(self, key: str, default: float) -> float:
    """Get float parameter with validation."""
    value = self.params.get(key, default)
    return float(value) if value is not None else default
# BRAK: def get_int(...)
```

**Call chain prowadzący do błędu:**
1. RSI rejestruje się przez algorithm registry
2. `RSIAlgorithm.is_time_driven()` zwraca `True`
3. Time-driven scheduler tworzy hook via `_create_engine_hook()`
4. Hook wywołuje `calculate_multi_window()` → `calculate_from_windows()`
5. `calculate_from_windows()` wywołuje `params.get_int()` → **AttributeError**

**Do naprawy:**
1. Dodać metodę `get_int` do `IndicatorParameters`:
   ```python
   def get_int(self, key: str, default: int) -> int:
       """Get integer parameter with validation."""
       value = self.params.get(key, default)
       return int(value) if value is not None else default
   ```

**Testy:**
- Test jednostkowy dla RSI calculation z różnymi wartościami `period`
- Test że `IndicatorParameters.get_int()` poprawnie konwertuje float na int

---

### BUG-DV-020: GraphAdapter created with indicator_engine=None [IMPORTANT]

**Problem:** Funkcja `get_graph_adapter()` tworzy `GraphAdapter` z `indicator_engine=None`. Powoduje to, że wskaźniki w trybie graph execution zwracają `None`, a strategie graph-based nie działają poprawnie.

**Lokalizacja:** `src/engine/graph_adapter.py:822-830`

**Szczegóły:**
```python
# Obecna implementacja (graph_adapter.py:822-830):
graph_adapter = GraphAdapter(
    state_persistence_manager=state_persistence_manager,
    indicator_engine=None,  # ✅ FIX: indicator_engine should be injected via DI
    event_bus=event_bus
)
```

Komentarz `✅ FIX` sugeruje, że problem jest znany, ale nie został naprawiony.

**Do naprawy:**
1. Usunąć `get_graph_adapter()` singleton pattern
2. Tworzyć `GraphAdapter` przez Container z proper DI:
   ```python
   # W container_main.py:
   graph_adapter = GraphAdapter(
       state_persistence_manager=state_persistence_manager,
       indicator_engine=streaming_indicator_engine,  # Inject real engine
       event_bus=event_bus
   )
   ```
3. LUB: Dodać lazy initialization w `get_graph_adapter()` która pobiera engine z Container

**Testy:**
- Test że `GraphAdapter` z valid indicator_engine zwraca poprawne wartości wskaźników
- Test integracyjny dla graph-based strategy execution

---

### Clean Passes (obniżające score):

1. **TWPA Division Protection** (`src/domain/services/indicators/twpa.py:225`)
   - Sprawdzenie `total_weight <= 0.0` przed dzieleniem ✓

2. **TWPA_RATIO min_denominator** (`src/domain/services/indicators/twpa_ratio.py:201-203`)
   - Parametr `min_denominator` chroni przed division by zero ✓

3. **RSI avg_loss==0 Handling** (`src/domain/services/indicators/rsi.py:161-162`)
   - Specjalna obsługa przypadku gdy avg_loss == 0 ✓

4. **Indicator Consistency Monitor** (`src/monitoring/indicator_consistency_monitor.py`)
   - Monitorowanie drift między offline/streaming pipeline ✓

---

## Zaktualizowany Priorytet napraw

### CRITICAL (blokują deploy):
1. **BUG-DV-015** - WebSocket API: brak auth na strategy handlers (**SECURITY**)
2. **BUG-DV-016** - WebSocket API: brak auth na session_stop (**SECURITY**)
3. **BUG-DV-001** + **BUG-DV-002** - Live Trading close_position (zależne)
4. **BUG-DV-013** - Strategy Management: dwie ścieżki persystencji (utrata danych)
5. **BUG-DV-004** - File-based strategy persistence (związane z BUG-DV-013)
6. **BUG-DV-019** - Indicator System: RSI `get_int` method missing (**RUNTIME ERROR**)

### IMPORTANT (warunki akceptacji):
7. **BUG-DV-017** - WebSocket API: brak auth na pozostałych handlerach
8. **BUG-DV-018** - WebSocket API: handshake nieforcowany
9. **BUG-DV-020** - Indicator System: GraphAdapter indicator_engine=None
10. **BUG-DV-005** - Backtest UI: brak opcji realizmu
11. **BUG-DV-014** - Direction "BOTH" niezaimplementowane
12. **BUG-DV-003** - Case inconsistency w polu 'side'

### LOWER PRIORITY:
13. **INFO-DV-001** - Single-instance lock (backlog)

---

---

## Deep Verify F7: Signal Processing (2026-01-20)

**Verdict: REJECT** (S = 6.0)

### BUG-DV-021: SignalProcessor._get_market_context raises NotImplementedError [CRITICAL]

**Problem:** `_get_market_context()` throws `NotImplementedError` when cache miss occurs. This crashes the entire signal processing pipeline for flash pump and confluence signals.

**Lokalizacja:** `src/api/signal_processor.py:681-689`

**Szczegóły:**
```python
async def _get_market_context(self, symbol: str) -> Dict[str, Any]:
    """Get market context for symbol with caching"""
    # Try cache first
    cached = await self._get_cached_market_data(symbol)
    if cached:
        return cached

    # Real implementation required - fetch from MEXC API
    raise NotImplementedError("Real MEXC API integration required for market context")
```

**Call chain:**
1. `process_flash_pump_signal()` calls `_enrich_flash_pump_signal()` (line 183)
2. `_enrich_flash_pump_signal()` calls `_get_market_context()` (line 613)
3. If cache miss → **NotImplementedError** → signal processing fails

**Do naprawy:**
1. Zaimplementować integrację z MEXC API dla pobrania kontekstu rynkowego
2. LUB: Dodać fallback który zwraca domyślne wartości zamiast rzucać wyjątek:
   ```python
   # Fallback for missing market data
   return {
       "market_cap_rank": 1000,
       "liquidity_usdt": 0,
       "spread_pct": None,
       "volume_24h": 0
   }
   ```

**Testy:**
- Test że sygnał jest przetwarzany nawet przy braku danych w cache
- Test integracyjny z prawdziwym API MEXC

---

### BUG-DV-022: StrategyEvaluator._generate_signal_reason returns broken format strings [CRITICAL]

**Problem:** Metoda `_generate_signal_reason()` zwraca literał ".2f" zamiast sformatowanego stringa z wartościami. Signal reason jest bezużyteczny dla konsumentów downstream.

**Lokalizacja:** `src/engine/strategy_evaluator.py:279-286`

**Szczegóły:**
```python
def _generate_signal_reason(self, signal_type: SignalType, pump_score: float, confidence: float) -> str:
    """Generate human-readable reason for the signal."""
    if signal_type == SignalType.BUY:
        return ".2f"  # ← BŁĄD: powinno być f"Pump detected: score={pump_score:.2f}, conf={confidence:.2f}"
    elif signal_type == SignalType.SELL:
        return ".2f"
    else:
        return ".2f"
```

**Do naprawy:**
```python
def _generate_signal_reason(self, signal_type: SignalType, pump_score: float, confidence: float) -> str:
    if signal_type == SignalType.BUY:
        return f"Pump detected: score={pump_score:.2f}, confidence={confidence:.2f}"
    elif signal_type == SignalType.SELL:
        return f"Exit signal: score={pump_score:.2f}, confidence={confidence:.2f}"
    else:
        return f"Hold signal: score={pump_score:.2f}, confidence={confidence:.2f}"
```

**Testy:**
- Test że signal.reason zawiera czytelny opis z wartościami

---

### BUG-DV-023: StrategyEvaluator._extract_symbol_from_indicator hardcoded to "BTC_USDT" [IMPORTANT]

**Problem:** Metoda `_extract_symbol_from_indicator()` zawsze zwraca "BTC_USDT" niezależnie od rzeczywistego symbolu. Wszystkie sygnały są błędnie przypisane do BTC_USDT.

**Lokalizacja:** `src/engine/strategy_evaluator.py:152-156`

**Szczegóły:**
```python
def _extract_symbol_from_indicator(self, indicator_name: str) -> str:
    """Extract symbol from indicator name (temporary implementation)."""
    # This is a simplified implementation
    # In production, symbols should be explicitly passed in indicator data
    return "BTC_USDT"  # ← HARDCODED! Wszystkie symbole traktowane jako BTC_USDT
```

**Do naprawy:**
1. Przekazywać symbol explicite w danych indicator events:
   ```python
   def _extract_symbol_from_indicator(self, indicator_name: str, data: Dict[str, Any]) -> str:
       if "symbol" in data:
           return data["symbol"]
       # Parse from indicator_name format: "symbol:indicator_type"
       if ":" in indicator_name:
           return indicator_name.split(":")[0]
       raise ValueError(f"Cannot extract symbol from indicator: {indicator_name}")
   ```

**Testy:**
- Test że sygnały dla różnych symboli są poprawnie atrybuowane

---

### BUG-DV-024: Timezone mismatch in signal validation [IMPORTANT]

**Problem:** `datetime.now()` (naive) jest odejmowane od `datetime.fromisoformat()` (może być aware). Jeśli timestamp w sygnale zawiera strefę czasową, operacja rzuci `TypeError`.

**Lokalizacja:** `src/api/signal_processor.py:387-388`

**Szczegóły:**
```python
# W _validate_flash_pump_signal():
timestamp = datetime.fromisoformat(signal["timestamp"])  # Może być aware (+00:00)
age_seconds = (datetime.now() - timestamp).total_seconds()  # datetime.now() jest NAIVE!
# → TypeError: can't subtract offset-naive and offset-aware datetimes
```

**Do naprawy:**
```python
from datetime import datetime, timezone

timestamp = datetime.fromisoformat(signal["timestamp"])
# Ensure both are aware or both are naive
now = datetime.now(timezone.utc) if timestamp.tzinfo else datetime.now()
age_seconds = (now - timestamp).total_seconds()
```

**Testy:**
- Test walidacji sygnału z timestamp zawierającym timezone (+00:00)
- Test walidacji sygnału z naive timestamp

---

### Clean Passes (obniżające score):

1. **Signal validation with required fields** (`src/api/signal_processor.py:372-407`)
   - Walidacja wymaganych pól przed przetworzeniem ✓

2. **Rate limiting implementation** (`src/api/signal_processor.py:847-861`)
   - `max_signals_per_minute` z async lock protection ✓

3. **Thread-safe processing stats** (`src/api/signal_processor.py:863-870`)
   - `threading.Lock()` dla statystyk ✓

4. **Signal history caching with TTL** (`src/api/signal_processor.py:884-908`)
   - Cache z TTL i LRU eviction ✓

---

## Zaktualizowany Priorytet napraw (v3)

### CRITICAL (blokują deploy):
1. **BUG-DV-015** - WebSocket API: brak auth na strategy handlers (**SECURITY**)
2. **BUG-DV-016** - WebSocket API: brak auth na session_stop (**SECURITY**)
3. **BUG-DV-001** + **BUG-DV-002** - Live Trading close_position (zależne)
4. **BUG-DV-013** - Strategy Management: dwie ścieżki persystencji (utrata danych)
5. **BUG-DV-004** - File-based strategy persistence (związane z BUG-DV-013)
6. **BUG-DV-019** - Indicator System: RSI `get_int` method missing (**RUNTIME ERROR**)
7. **BUG-DV-021** - Signal Processing: `_get_market_context` NotImplementedError (**RUNTIME ERROR**)
8. **BUG-DV-022** - Signal Processing: `_generate_signal_reason` broken format (**DATA QUALITY**)

### IMPORTANT (warunki akceptacji):
9. **BUG-DV-017** - WebSocket API: brak auth na pozostałych handlerach
10. **BUG-DV-018** - WebSocket API: handshake nieforcowany
11. **BUG-DV-020** - Indicator System: GraphAdapter indicator_engine=None
12. **BUG-DV-023** - Signal Processing: hardcoded "BTC_USDT" symbol
13. **BUG-DV-024** - Signal Processing: timezone mismatch
14. **BUG-DV-005** - Backtest UI: brak opcji realizmu
15. **BUG-DV-014** - Direction "BOTH" niezaimplementowane
16. **BUG-DV-003** - Case inconsistency w polu 'side'

### LOWER PRIORITY:
17. **INFO-DV-001** - Single-instance lock (backlog)

---

---

## Deep Verify F8: Risk Management (2026-01-20)

**Verdict: UNCERTAIN** (S = -2.0) - Core RiskManager is well implemented, minor issues in RiskAssessmentService

### BUG-DV-025: RiskAssessmentService.assess_position_risk returns wrong type [IMPORTANT]

**Problem:** `assess_position_risk()` tworzy `RiskAssessment` z polami które nie istnieją w Pydantic modelu. Spowoduje `ValidationError` przy wywołaniu.

**Lokalizacja:** `src/domain/services/risk_assessment.py:365-371`

**Szczegóły:**
```python
# Metoda zwraca (risk_assessment.py:365-371):
return RiskAssessment(
    risk_level=risk_level,
    drawdown_pct=drawdown_pct,        # ← NIE ISTNIEJE W MODELU
    stop_distance_pct=stop_distance_pct,  # ← NIE ISTNIEJE W MODELU
    unrealized_pnl=unrealized_pnl,    # ← NIE ISTNIEJE W MODELU
    recommendations=recommendations    # ← POWINNO BYĆ: risk_reasons
)

# Ale RiskAssessment w risk.py wymaga (wymagane pola):
# - symbol: str
# - exchange: str
# - spread_pct: Decimal
# - liquidity_usdt: Decimal
# ... i wiele innych
```

**Status:** Metoda obecnie nie jest wywoływana w produkcji (dead code). `DetectPumpSignalsUseCase` używa tylko `assess_emergency_conditions()`.

**Do naprawy:**
1. Utworzyć osobną dataclass `PositionRiskAssessment` dla zwracanego typu:
   ```python
   @dataclass
   class PositionRiskAssessment:
       risk_level: RiskLevel
       drawdown_pct: float
       stop_distance_pct: float
       unrealized_pnl: float
       recommendations: List[str]
   ```
2. LUB: Usunąć metodę jeśli nie jest używana

**Testy:**
- Test że `assess_position_risk()` zwraca poprawny typ

---

### BUG-DV-026: calculate_position_size only works for LONG positions [IMPORTANT]

**Problem:** Funkcja `calculate_position_size()` zwraca 0.0 dla pozycji SHORT, ponieważ zakłada że stop_loss < entry_price (prawdziwe tylko dla LONG).

**Lokalizacja:** `src/domain/services/risk_assessment.py:409-413`

**Szczegóły:**
```python
def calculate_position_size(self, account_balance: float, risk_pct: float,
                          entry_price: float, stop_loss: float) -> float:
    # ...
    if entry_price <= 0 or stop_loss <= 0 or entry_price <= stop_loss:
        return 0.0  # ← Dla SHORT: stop_loss > entry_price → zwraca 0.0!

    # Calculate risk per unit
    risk_per_unit = entry_price - stop_loss  # ← Dla SHORT: wynik UJEMNY!
```

**Przykład:**
- LONG: entry=$100, stop=$95 → risk_per_unit = $5 ✓
- SHORT: entry=$100, stop=$105 → entry_price <= stop_loss → returns 0.0 ✗

**Do naprawy:**
```python
def calculate_position_size(self, account_balance: float, risk_pct: float,
                          entry_price: float, stop_loss: float,
                          side: str = "LONG") -> float:
    if entry_price <= 0 or stop_loss <= 0:
        return 0.0

    if side.upper() == "LONG":
        if stop_loss >= entry_price:
            return 0.0  # Invalid: stop_loss must be below entry for LONG
        risk_per_unit = entry_price - stop_loss
    else:  # SHORT
        if stop_loss <= entry_price:
            return 0.0  # Invalid: stop_loss must be above entry for SHORT
        risk_per_unit = stop_loss - entry_price

    max_risk_amount = account_balance * (risk_pct / 100)
    return max(0.0, max_risk_amount / risk_per_unit)
```

**Testy:**
- Test position sizing dla LONG z stop_loss poniżej entry
- Test position sizing dla SHORT z stop_loss powyżej entry

---

### Clean Passes (obniżające score):

1. **RiskManager thread-safety** (`risk_manager.py:117-119`)
   - Async lock (`asyncio.Lock`) + sync lock (`threading.Lock`) ✓

2. **Input validation for positions** (`risk_manager.py:538-581`)
   - Walidacja symbolu, quantity, price, overflow protection ✓

3. **Zero/negative capital handling** (`risk_manager.py:173-180`)
   - Explicit check przed otwarciem pozycji ✓

4. **None notional_value handling** (`risk_manager.py:421-428`)
   - Safe Decimal conversion z try/except ✓

5. **Equity peak protection** (`risk_manager.py:583-604`)
   - Handle zero/negative, ensure peak >= current ✓

6. **Budget allocation validation** (`risk_manager.py:854-865`)
   - Thread-safe, input validation ✓

7. **6 comprehensive risk checks** (`risk_manager.py:191-247`)
   - Position size, max positions, concentration, daily loss, drawdown, margin ✓

8. **Daily P&L tracking with reset** (`risk_manager.py:606-612`)
   - Automatic midnight reset ✓

---

## Zaktualizowany Priorytet napraw (v4)

### CRITICAL (blokują deploy):
1. **BUG-DV-015** - WebSocket API: brak auth na strategy handlers (**SECURITY**)
2. **BUG-DV-016** - WebSocket API: brak auth na session_stop (**SECURITY**)
3. **BUG-DV-001** + **BUG-DV-002** - Live Trading close_position (zależne)
4. **BUG-DV-013** - Strategy Management: dwie ścieżki persystencji (utrata danych)
5. **BUG-DV-004** - File-based strategy persistence (związane z BUG-DV-013)
6. **BUG-DV-019** - Indicator System: RSI `get_int` method missing (**RUNTIME ERROR**)
7. **BUG-DV-021** - Signal Processing: `_get_market_context` NotImplementedError (**RUNTIME ERROR**)
8. **BUG-DV-022** - Signal Processing: `_generate_signal_reason` broken format (**DATA QUALITY**)

### IMPORTANT (warunki akceptacji):
9. **BUG-DV-017** - WebSocket API: brak auth na pozostałych handlerach
10. **BUG-DV-018** - WebSocket API: handshake nieforcowany
11. **BUG-DV-020** - Indicator System: GraphAdapter indicator_engine=None
12. **BUG-DV-023** - Signal Processing: hardcoded "BTC_USDT" symbol
13. **BUG-DV-024** - Signal Processing: timezone mismatch
14. **BUG-DV-025** - Risk Management: RiskAssessment type mismatch (dead code)
15. **BUG-DV-026** - Risk Management: position sizing ignores SHORT positions
16. **BUG-DV-005** - Backtest UI: brak opcji realizmu
17. **BUG-DV-014** - Direction "BOTH" niezaimplementowane
18. **BUG-DV-003** - Case inconsistency w polu 'side'

### LOWER PRIORITY:
19. **INFO-DV-001** - Single-instance lock (backlog)

---

---

## Deep Verify F9: Data Feed (2026-01-21)

**Verdict: ACCEPT** (S = -7.0) - Production-grade implementation with excellent defensive patterns

### No Issues Found

This functional area demonstrated exemplary code quality with extensive defensive patterns:

### Clean Passes (obniżające score):

1. **QuestDBProvider - WAL Race Condition Awareness** (`src/data_feed/questdb_provider.py:15-40`)
   - Extensive documentation of dual-protocol architecture and race conditions ✓
   - Verification after writes via `_verify_wal_commit()` ✓

2. **QuestDBProvider - Parameterized SQL Queries** (`src/data_feed/questdb_provider.py`)
   - All queries use `$N` placeholders for SQL injection protection ✓

3. **QuestDBProvider - Connection Pooling** (`src/data_feed/questdb_provider.py:171-200`)
   - Race condition fix with initialization lock ✓
   - Proper cleanup in `close()` method ✓

4. **QuestDBProvider - Retry Logic** (`src/data_feed/questdb_provider.py:1928`)
   - Exponential backoff for WAL race condition handling ✓

5. **MexcWebSocketAdapter - Circuit Breaker** (`src/infrastructure/exchanges/mexc_websocket_adapter.py:113-118`)
   - Circuit breaker protection with configurable thresholds ✓

6. **MexcWebSocketAdapter - Rate Limiting** (`src/infrastructure/exchanges/mexc_websocket_adapter.py:120-125`)
   - `TokenBucketRateLimiter` for subscription rate limiting ✓

7. **MexcWebSocketAdapter - Per-Symbol Locks** (`src/infrastructure/exchanges/mexc_websocket_adapter.py:612-627`)
   - Per-symbol orderbook locks eliminate global contention ✓

8. **MexcWebSocketAdapter - Memory Leak Prevention** (`src/infrastructure/exchanges/mexc_websocket_adapter.py:558-606`)
   - `_cleanup_tracking_structures()` with TTL and hard limits ✓
   - `_tracking_expiry` mechanism for bounded growth ✓

9. **MexcWebSocketAdapter - Race Condition Prevention** (`src/infrastructure/exchanges/mexc_websocket_adapter.py:1327-1431`)
   - `_message_processing_count` prevents cleanup during in-flight processing ✓
   - Coordination tracking for async message processing ✓

10. **MexcWebSocketAdapter - Data Activity Monitoring** (`src/infrastructure/exchanges/mexc_websocket_adapter.py:219-370`)
    - Symbol-aware thresholds (HIGH/MEDIUM/LOW volume) ✓
    - False positive tracking for AC6 compliance ✓
    - Pre-close health check before inactivity closes ✓

11. **EventBusMarketDataProvider - Memory-Safe Queue Management** (`src/infrastructure/exchanges/eventbus_market_data_provider.py:26-36`)
    - No defaultdict (prevents memory leaks) ✓
    - Explicit `MAX_SYMBOLS` and `MAX_QUEUE_SIZE` limits ✓

12. **EventBusMarketDataProvider - Explicit Symbol Allowlist** (`src/infrastructure/exchanges/eventbus_market_data_provider.py:236-237`)
    - Only processes events for explicitly subscribed symbols ✓

13. **QuestDBDataProvider - SQL Injection Protection** (`src/data/questdb_data_provider.py:63-93`)
    - Parameterized queries with `$N` placeholders throughout ✓

14. **LiveMarketAdapter - Incident Tracking** (`src/data/live_market_adapter.py:309-356`)
    - Structured incident logging with severity classification ✓
    - Memory-bounded (keeps last 100 incidents) ✓

### Wyróżniające się wzorce (Notable Patterns):

1. **Graceful Degradation** - QuestDBProvider continues with PostgreSQL-only mode if ILP fails
2. **Comprehensive Health Checks** - Multiple levels of connection health monitoring
3. **Configurable Thresholds** - All timing and limit parameters externalized to settings
4. **Detailed Logging** - Structured logging with context for all operations
5. **Task Lifecycle Management** - `_create_tracked_task()` prevents dangling tasks

---

## Zaktualizowany Priorytet napraw (v5)

### CRITICAL (blokują deploy):
1. **BUG-DV-015** - WebSocket API: brak auth na strategy handlers (**SECURITY**)
2. **BUG-DV-016** - WebSocket API: brak auth na session_stop (**SECURITY**)
3. **BUG-DV-001** + **BUG-DV-002** - Live Trading close_position (zależne)
4. **BUG-DV-013** - Strategy Management: dwie ścieżki persystencji (utrata danych)
5. **BUG-DV-004** - File-based strategy persistence (związane z BUG-DV-013)
6. **BUG-DV-019** - Indicator System: RSI `get_int` method missing (**RUNTIME ERROR**)
7. **BUG-DV-021** - Signal Processing: `_get_market_context` NotImplementedError (**RUNTIME ERROR**)
8. **BUG-DV-022** - Signal Processing: `_generate_signal_reason` broken format (**DATA QUALITY**)

### IMPORTANT (warunki akceptacji):
9. **BUG-DV-017** - WebSocket API: brak auth na pozostałych handlerach
10. **BUG-DV-018** - WebSocket API: handshake nieforcowany
11. **BUG-DV-020** - Indicator System: GraphAdapter indicator_engine=None
12. **BUG-DV-023** - Signal Processing: hardcoded "BTC_USDT" symbol
13. **BUG-DV-024** - Signal Processing: timezone mismatch
14. **BUG-DV-025** - Risk Management: RiskAssessment type mismatch (dead code)
15. **BUG-DV-026** - Risk Management: position sizing ignores SHORT positions
16. **BUG-DV-005** - Backtest UI: brak opcji realizmu
17. **BUG-DV-014** - Direction "BOTH" niezaimplementowane
18. **BUG-DV-003** - Case inconsistency w polu 'side'

### LOWER PRIORITY:
19. **INFO-DV-001** - Single-instance lock (backlog)

### ACCEPTED (bez napraw wymaganych):
- **F9: Data Feed** - Production-grade implementation ✓

---

---

## Deep Verify F10: Auth & Security (2026-01-21)

**Verdict: UNCERTAIN** (S = +0.3) - Strong auth infrastructure but critical credential validation gaps

### BUG-DV-027: Weak fallback passwords used when env vars not set [CRITICAL]

**Problem:** Funkcja `authenticate_credentials()` używa słabych hardcoded haseł jako fallback gdy zmienne środowiskowe nie są ustawione. Hasła typu "admin123", "demo123" są używane w produkcji jeśli operator nie ustawi zmiennych.

**Lokalizacja:** `src/api/auth_handler.py:935-938`

**Szczegóły:**
```python
# Kod obecnie:
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD") or "demo123"
TRADER_PASSWORD = os.getenv("TRADER_PASSWORD") or "trader123"
PREMIUM_PASSWORD = os.getenv("PREMIUM_PASSWORD") or "premium123"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or "admin123"  # ← CRITICAL: weak admin password!
```

System loguje warning ale auth **PRZECHODZI** z słabymi hasłami.

**Do naprawy:**
1. Dodać walidację która BLOKUJE auth gdy używane są domyślne hasła:
   ```python
   WEAK_DEFAULTS = {"demo123", "trader123", "premium123", "admin123"}

   if ADMIN_PASSWORD in WEAK_DEFAULTS:
       return AuthResult(
           success=False,
           error_code="configuration_error",
           error_message="ADMIN_PASSWORD must be changed from default value"
       )
   ```
2. LUB: Wymusić ustawienie zmiennych środowiskowych (bez fallback)
3. LUB: Domyślnie BLOKOWAĆ auth gdy env vars nie są ustawione

**Testy:**
- Test że auth FAILUJE gdy env vars używają domyślnych wartości
- Test że auth FAILUJE gdy env vars nie są ustawione

---

### BUG-DV-028: Security tests testing for non-existent validation [CRITICAL]

**Problem:** Testy w `test_security_vulnerabilities.py` oczekują że system zwróci `configuration_error` dla słabych/brakujących credentials, ale ta logika NIE ISTNIEJE w kodzie `auth_handler.py`. Testy będą FAILOWAĆ, co sugeruje że security fixes nie zostały zaimplementowane.

**Lokalizacja:**
- Testy: `tests_e2e/integration/test_security_vulnerabilities.py:108-159`
- Brakujący kod: `src/api/auth_handler.py:903-985`

**Szczegóły:**
```python
# Test oczekuje (test_security_vulnerabilities.py:131-133):
assert result.error_code == "configuration_error"
assert "DEMO_PASSWORD" in result.error_message

# Ale kod NIE zawiera logiki która zwraca "configuration_error"
# grep -n "configuration_error" src/api/auth_handler.py → No match found
```

**Do naprawy:**
1. Zaimplementować walidację credentials zgodnie z oczekiwaniami testów:
   - Odrzucać hasła zawierające "CHANGE_ME"
   - Odrzucać brakujące zmienne środowiskowe
   - Zwracać `error_code="configuration_error"` w tych przypadkach
2. LUB: Usunąć testy które testują nieistniejącą funkcjonalność

**Testy:**
- Uruchomić `pytest tests_e2e/integration/test_security_vulnerabilities.py -v` i naprawić wszystkie failures

---

### INFO-DV-002: CORS uses wildcard methods/headers [MINOR]

**Problem:** CORS middleware używa `allow_methods=["*"]` i `allow_headers=["*"]`. Jest to akceptowalne dla local development (origins ograniczone do localhost), ale powinno być zaostrzone dla produkcji.

**Lokalizacja:** `src/api/unified_server.py:1337-1338`

**Szczegóły:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,  # OK - restricted to localhost
    allow_credentials=True,
    allow_methods=["*"],  # Should be restricted
    allow_headers=["*"],  # Should be restricted
)
```

**Do naprawy (low priority):**
```python
allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
```

---

### Clean Passes (obniżające score):

1. **JWT Secret Validation** (`src/api/websocket_server.py:362-378`)
   - Minimum 32 characters enforced ✓
   - Weak secrets rejected via blacklist ✓

2. **bcrypt Password Hashing** (`src/api/auth_handler.py:627-639`)
   - 12 rounds of bcrypt ✓
   - Salt generated per hash ✓

3. **Session Management** (`src/api/auth_handler.py:59-120`)
   - Session expiry with configurable TTL ✓
   - Max sessions per user enforced ✓

4. **IP Blocking** (`src/api/auth_handler.py:676-697`)
   - 5 failed attempts in 5 minutes → IP blocked ✓
   - Auto-unblock after 1 hour ✓

5. **Rate Limiting** (`src/api/auth_handler.py:113-119`)
   - 1000 requests per hour per session ✓
   - Automatic hourly reset ✓

6. **CSRF Protection** (`src/api/unified_server.py`)
   - X-CSRF-Token validation middleware ✓
   - csrf_validation_middleware implemented ✓

7. **InputSanitizer** (`src/core/input_sanitizer.py`)
   - XSS pattern detection ✓
   - Command injection prevention ✓
   - Path traversal prevention ✓

8. **SQL Injection Prevention** (`src/data_feed/questdb_provider.py`, etc.)
   - Parameterized queries ($N placeholders) throughout ✓

9. **Suspicious Activity Logging** (`src/api/auth_handler.py:699-717`)
   - ip_mismatch, permission_denied events logged ✓
   - Last 100 activities retained ✓

10. **Generic Error Messages** (`src/api/auth_handler.py:981-985`)
    - "Invalid username or password" - doesn't leak if username exists ✓

11. **Secure Token Generation** (`src/api/auth_handler.py:619-625`)
    - secrets.token_urlsafe(32) for session/refresh tokens ✓

12. **Timing-Attack Safe Comparison** (`src/api/auth_handler.py:674`)
    - hmac.compare_digest for plaintext comparison ✓

---

## Zaktualizowany Priorytet napraw (v6)

### CRITICAL (blokują deploy):
1. **BUG-DV-015** - WebSocket API: brak auth na strategy handlers (**SECURITY**)
2. **BUG-DV-016** - WebSocket API: brak auth na session_stop (**SECURITY**)
3. **BUG-DV-027** - Auth: weak fallback passwords (**SECURITY**)
4. **BUG-DV-028** - Auth: security tests test non-existent code (**SECURITY**)
5. **BUG-DV-001** + **BUG-DV-002** - Live Trading close_position (zależne)
6. **BUG-DV-013** - Strategy Management: dwie ścieżki persystencji (utrata danych)
7. **BUG-DV-004** - File-based strategy persistence (związane z BUG-DV-013)
8. **BUG-DV-019** - Indicator System: RSI `get_int` method missing (**RUNTIME ERROR**)
9. **BUG-DV-021** - Signal Processing: `_get_market_context` NotImplementedError (**RUNTIME ERROR**)
10. **BUG-DV-022** - Signal Processing: `_generate_signal_reason` broken format (**DATA QUALITY**)

### IMPORTANT (warunki akceptacji):
11. **BUG-DV-017** - WebSocket API: brak auth na pozostałych handlerach
12. **BUG-DV-018** - WebSocket API: handshake nieforcowany
13. **BUG-DV-020** - Indicator System: GraphAdapter indicator_engine=None
14. **BUG-DV-023** - Signal Processing: hardcoded "BTC_USDT" symbol
15. **BUG-DV-024** - Signal Processing: timezone mismatch
16. **BUG-DV-025** - Risk Management: RiskAssessment type mismatch (dead code)
17. **BUG-DV-026** - Risk Management: position sizing ignores SHORT positions
18. **BUG-DV-005** - Backtest UI: brak opcji realizmu
19. **BUG-DV-014** - Direction "BOTH" niezaimplementowane
20. **BUG-DV-003** - Case inconsistency w polu 'side'

### LOWER PRIORITY:
21. **INFO-DV-001** - Single-instance lock (backlog)
22. **INFO-DV-002** - CORS wildcard methods/headers (low risk for local app)

### ACCEPTED (bez napraw wymaganych):
- **F9: Data Feed** - Production-grade implementation ✓

---

---

## Deep Verify F11: Frontend (2026-01-21)

**Verdict: UNCERTAIN** (S = 0.0) - Good defensive patterns but critical credential exposure

### BUG-DV-029: Hardcoded Admin Password Exposed in Frontend Code [CRITICAL]

**Problem:** Funkcja demo login w `LoginForm` zawiera hardcoded hasła dla wszystkich kont demo, **WŁĄCZNIE z hasłem admina**. Hasło `supersecret` jest widoczne dla każdego kto przegląda kod źródłowy w przeglądarce (DevTools → Sources).

**Lokalizacja:** `frontend/src/components/auth/LoginForm.tsx:77-82`

**Szczegóły:**
```typescript
// Komentarz w kodzie twierdzi że to jest "FIX" - ale to WPROWADZA lukę bezpieczeństwa:
const credentials = {
  demo: { username: 'demo', password: 'demo123' },
  trader: { username: 'trader', password: 'trader123' },
  premium: { username: 'premium', password: 'premium123' },
  admin: { username: 'admin', password: 'supersecret' },  // ← HASŁO ADMINA WIDOCZNE!
};
```

Komentarz mówi: "✅ SECURITY FIX: Match credentials with backend .env configuration" - ale to NIE jest fix, to ekspozycja prawdziwego hasła!

**Do naprawy:**
1. **Usunąć hasła z kodu frontendowego** - demo login powinien używać osobnego endpointu
2. LUB: Utworzyć dedykowany endpoint `/api/v1/auth/demo-login` który akceptuje tylko typ konta:
   ```typescript
   // Frontend:
   await fetch('/api/v1/auth/demo-login', {
     method: 'POST',
     body: JSON.stringify({ accountType: 'demo' })
   });

   // Backend obsługuje mapowanie typ → credentials
   ```
3. LUB: Usunąć możliwość demo logowania do kont admin/premium
4. **CRITICAL:** Zmienić hasło admina na backendzie natychmiast po naprawie!

**Testy:**
- Test że żadne hasła nie są hardcoded w kodzie frontendowym
- Security scan na pliki `.tsx` szukający wzorców `password:`

---

### BUG-DV-030: Access Tokens Stored in localStorage via Zustand Persist [IMPORTANT]

**Problem:** AuthStore używa Zustand `persist` middleware które zapisuje `accessToken` i `refreshToken` do localStorage. Mimo że kod w innych miejscach mówi o HttpOnly cookies, tokeny są duplikowane w localStorage gdzie mogą być wykradzione przez XSS.

**Lokalizacja:** `frontend/src/stores/authStore.ts:301-311`

**Szczegóły:**
```typescript
// Persist configuration zapisuje tokeny do localStorage:
{
  name: 'auth-storage',  // localStorage key
  storage: createJSONStorage(() => localStorage),
  partialize: (state) => ({
    user: state.user,
    accessToken: state.accessToken,      // ← ZAPISANE DO localStorage!
    refreshToken: state.refreshToken,    // ← ZAPISANE DO localStorage!
    isAuthenticated: state.isAuthenticated,
    tokenExpiry: state.tokenExpiry,
  }),
}
```

Równocześnie `authService.ts` mówi: "Tokens are in HttpOnly cookies" - jest niespójność.

**Do naprawy:**
1. Usunąć `accessToken` i `refreshToken` z `partialize`:
   ```typescript
   partialize: (state) => ({
     user: state.user,
     isAuthenticated: state.isAuthenticated,
     // NIE zapisuj tokenów do localStorage!
   }),
   ```
2. Polegać wyłącznie na HttpOnly cookies dla tokenów
3. Wyczyścić istniejące tokeny z localStorage przy następnym deployu

**Testy:**
- Test że localStorage nie zawiera tokenów po logowaniu
- Test że tokeny są przesyłane tylko przez cookies

---

### Clean Passes (obniżające score):

1. **No XSS Vulnerabilities** (searched codebase)
   - Zero uses of `dangerouslySetInnerHTML`, `eval`, `innerHTML`, `document.write` ✓

2. **Proper useEffect Cleanup** (`frontend/src/hooks/`)
   - `useDataFreshness.ts`: `return () => clearInterval(interval)` ✓
   - `useKeyboardShortcuts.ts`: `return () => document.removeEventListener(...)` ✓
   - `useVisibilityAwareInterval.ts`: Clears interval + removes event listener ✓

3. **CSRF Tokens in Memory Only** (`frontend/src/services/csrfService.ts:30-31`)
   - `private token: string | null = null` - stored in memory, not localStorage ✓

4. **Error Boundaries with Financial Safety** (`frontend/src/components/common/ErrorBoundary.tsx`)
   - Financial error detection triggers read-only mode ✓
   - Automatic retry with exponential backoff ✓

5. **Comprehensive Safety Guards** (`frontend/src/utils/safetyGuards.ts`)
   - Connection validation before operations ✓
   - Trading amount validation ✓
   - Symbol format validation ✓
   - Rate limiting per operation ✓

6. **Input Validation in Stores** (`frontend/src/stores/dashboardStore.ts`)
   - Array validation: `const validData = Array.isArray(data) ? data : []` ✓
   - Type guards for market data and indicators ✓

7. **CSV Escape in Exports** (`frontend/src/app/session-history/page.tsx:196-207`)
   - `escapeCSV()` function for safe export ✓

8. **Keyboard Shortcuts with Input Detection** (`frontend/src/hooks/useKeyboardShortcuts.ts:69-77`)
   - Skips shortcuts when typing in INPUT/TEXTAREA/contentEditable ✓

---

---

## Deep Verify F15: WebSocket Client (2026-01-21)

**Verdict: REJECT** (S = 7.0)

### BUG-DV-031: Duplicate WebSocket Implementations [CRITICAL]

**Problem:** The codebase contains two separate and conflicting WebSocket client implementations: the singleton `wsService` in `websocket.ts` and the `useWebSocket` hook in `useWebSocket.ts`. They duplicate critical logic for connection, reconnection, and heartbeats. This makes the system's behavior impossible to reason about and is a massive source of potential bugs.

**Lokalizacja:**
- `frontend/src/services/websocket.ts` (monolithic singleton service)
- `frontend/src/hooks/useWebSocket.ts` (unused/competing hook implementation)

**Do naprawy:**
1. **Unify Implementations:** Choose one implementation as the single source of truth. The `wsService` singleton appears to be the one currently integrated.
2. **Remove Dead Code:** Delete `frontend/src/hooks/useWebSocket.ts` to eliminate confusion and prevent its accidental use.
3. **Refactor:** Ensure all WebSocket interactions throughout the application exclusively use the chosen `wsService` instance.

**Testy:**
- Perform a global search for `useWebSocket` to ensure it is not used anywhere.
- Verify that real-time features (dashboard, trading UI) continue to function correctly after removing the unused hook.

---

### BUG-DV-032: Potential Memory Leak in WebSocket Listeners [IMPORTANT]

**Problem:** The `wsService.addSessionUpdateListener` method requires consumers (React components) to manually call a cleanup function. This pattern is error-prone. If a component unmounts without calling the cleanup function, its listener will remain in memory indefinitely, causing a memory leak.

**Lokalizacja:** `frontend/src/services/websocket.ts:803-824`

**Szczegóły:**
```typescript
public addSessionUpdateListener(
  listener: (message: WSMessage) => void,
  componentName = 'unknown'
): () => void { // Returns a cleanup function that MUST be called
  this.sessionUpdateListeners.add(listener);
  // ...
  return () => { // If this is not called on unmount, the listener leaks
    this.sessionUpdateListeners.delete(listener);
    this.listenerMetadata.delete(listener);
  };
}
```

**Do naprawy:**
1. **Create a `useSubscription` Hook:** Develop a new React hook (e.g., `useSocketSubscription`) that wraps the `addSessionUpdateListener` logic.
2. **Automate Cleanup:** This hook should use a `useEffect` to subscribe on mount and automatically call the returned cleanup function on unmount.
3. **Refactor Components:** Replace all manual calls to `addSessionUpdateListener` with the new, safer `useSocketSubscription` hook.

**Testy:**
- Use React DevTools Profiler to mount and unmount a component using the new hook and verify that the number of listeners in `wsService.getListenerStats()` does not grow.

---

### BUG-DV-033: Conflicting WebSocket State Management [IMPORTANT]

**Problem:** There are two sources of truth for WebSocket connection state. The `wsService` singleton writes state to the global `websocketStore` (Zustand), while the unused `useWebSocket` hook manages its own separate, local state using `useState`. This violates the single source of truth principle and will cause UI inconsistencies.

**Lokalizacja:**
- Global state updates: `frontend/src/services/websocket.ts` (e.g., line 545: `useWebSocketStore.getState().setConnected(true)`)
- Local state updates: `frontend/src/hooks/useWebSocket.ts` (e.g., line 105: `const [isConnected, setIsConnected] = useState(false);`)

**Do naprawy:**
1. **Consolidate State Management:** After deleting `useWebSocket.ts` (per BUG-DV-031), ensure that `wsService` is the *only* part of the system that can write to the `websocketStore`.
2. **Read-Only Access for UI:** All UI components should treat the WebSocket state as read-only, consuming it from the `websocketStore` via hooks/selectors. They should not have their own local `isConnected` state variables.

**Testy:**
- Verify that the `connectionStatus` displayed in the UI is consistently derived from the `useWebSocketStore`.

---

## Zaktualizowany Priorytet napraw (v9)

### CRITICAL (blokują deploy):
1. **BUG-DV-031** - Frontend: Duplicate WebSocket Implementations (**ARCHitektura**)
2. **BUG-DV-029** - Frontend: hardcoded admin password (**SECURITY - EXPOSED CREDENTIALS**)
3. **BUG-DV-015** - WebSocket API: brak auth na strategy handlers (**SECURITY**)
4. **BUG-DV-016** - WebSocket API: brak auth na session_stop (**SECURITY**)
5. **BUG-DV-027** - Auth: weak fallback passwords (**SECURITY**)
6. **BUG-DV-028** - Auth: security tests test non-existent code (**SECURITY**)
7. **BUG-DV-001** + **BUG-DV-002** - Live Trading close_position (zależne)
8. **BUG-DV-013** - Strategy Management: dwie ścieżki persystencji (utrata danych)
9. **BUG-DV-004** - File-based strategy persistence (związane z BUG-DV-013)
10. **BUG-DV-019** - Indicator System: RSI `get_int` method missing (**RUNTIME ERROR**)
11. **BUG-DV-021** - Signal Processing: `_get_market_context` NotImplementedError (**RUNTIME ERROR**)
12. **BUG-DV-022** - Signal Processing: `_generate_signal_reason` broken format (**DATA QUALITY**)

### IMPORTANT (warunki akceptacji):
13. **BUG-DV-034** - Strategy Builder: validation stub always returns true (**VALIDATION BYPASS**)
14. **BUG-DV-035** - Strategy Builder: empty indicator variants in embedded builder
15. **BUG-DV-032** - Frontend: Potential Memory Leak in WebSocket Listeners
16. **BUG-DV-033** - Frontend: Conflicting WebSocket State Management
17. **BUG-DV-030** - Frontend: tokens in localStorage (**XSS VULNERABILITY**)
18. **BUG-DV-017** - WebSocket API: brak auth na pozostałych handlerach
19. **BUG-DV-018** - WebSocket API: handshake nieforcowany
20. **BUG-DV-020** - Indicator System: GraphAdapter indicator_engine=None
21. **BUG-DV-023** - Signal Processing: hardcoded "BTC_USDT" symbol
22. **BUG-DV-024** - Signal Processing: timezone mismatch
23. **BUG-DV-025** - Risk Management: RiskAssessment type mismatch (dead code)
24. **BUG-DV-026** - Risk Management: position sizing ignores SHORT positions
25. **BUG-DV-005** - Backtest UI: brak opcji realizmu
26. **BUG-DV-014** - Direction "BOTH" niezaimplementowane
27. **BUG-DV-003** - Case inconsistency w polu 'side'

### LOWER PRIORITY:
28. **INFO-DV-001** - Single-instance lock (backlog)
29. **INFO-DV-002** - CORS wildcard methods/headers (low risk for local app)

### ACCEPTED (bez napraw wymaganych):
- **F9: Data Feed** - Production-grade implementation ✓
- **F12: Dashboard UI** - Excellent defensive patterns ✓
- **F14: Backtest UI** - Comprehensive validation ✓
- **F15: Trading UI** - Production-ready with real API ✓

---

## Deep Verify F12: Dashboard UI (2026-01-21)

**Verdict: ACCEPT** (S = -5.7) - Production-grade dashboard implementation

### No Critical or Important Issues Found

Dashboard UI codebase demonstrates excellent engineering practices.

### Clean Passes (12 × -0.5 = -6.0):

1. **AbortController Cleanup in All Async Operations**
   - `dashboard/page.tsx`: All fetch calls use AbortController with proper cleanup
   - `SessionConfigDialog.tsx`: Three separate useEffects with AbortController + `isMounted` flag
   - Example: Lines 174-254, 262-327, 334-410

2. **Comprehensive Input Validation in SessionConfigDialog**
   - NaN validation: `Number.isFinite()` checks for budget, position size, stop loss, take profit
   - Range validation: 0-100% for stop loss, 0-1000% for take profit
   - Cross-field validation: max position size cannot exceed global budget
   - Location: `SessionConfigDialog.tsx:454-504`

3. **Division by Zero Guards**
   - `ActivePositionBanner.tsx:366`: `if (positions.length === 0) return null;` before division
   - `ConditionProgress.tsx:151`: `if (threshold === 0) return 0;` before calculation

4. **State Machine State Configuration with Fallback**
   - `StatusHero.tsx:301`: `STATE_STYLES[state] || STATE_STYLES.MONITORING`
   - Handles unknown states gracefully

5. **Proper UseEffect Cleanup for Intervals**
   - `ActivePositionBanner.tsx:159-162`: `return () => clearInterval(interval);`
   - `StatusHero.tsx:325`: `return () => clearInterval(interval);`
   - `dashboard/page.tsx:521-531`: abortController cleanup on interval

6. **Memory Management**
   - `dashboard/page.tsx:631`: `setDashboardData(null)` on session stop
   - `dashboardStore.ts:66`: Limits signals to 10 items max

7. **Type-Safe Error Handling**
   - Consistent pattern: `error instanceof Error ? error.message : 'Unknown error'`
   - AbortError detection: `error.name === 'AbortError'` to prevent false error messages

8. **Loading States and Error States**
   - Separate loading states for each data type (market data, signals, indicators)
   - Background refresh flag to prevent UI flickering

9. **Form State Reset on Dialog Close**
   - `SessionConfigDialog.tsx:536-548`: Resets all form fields when dialog closes

10. **Signal Session Filtering**
    - `RecentSignalsPanel.tsx:79-81`: Filters signals by sessionId

11. **Responsive Design**
    - `StatusHero.tsx:293-295`: Mobile/tablet breakpoint detection
    - Dynamic font sizes based on viewport

12. **Real-time P&L Display with Color Coding**
    - Consistent green/red color scheme for profit/loss
    - `StatusHero.tsx:307`: `pnl >= 0 ? '#10B981' : '#EF4444'`

### Minor Note (for future improvement):

**WebSocket Callback Pattern in RecentSignalsPanel** (+0.3)
- `RecentSignalsPanel.tsx:88`: `wsService.setCallbacks()` not cleaned up on unmount
- Comment at line 94: "don't remove callback - other components may need it"
- This is an intentional design decision for shared callbacks

### Score Calculation:
- CRITICAL: 0
- IMPORTANT: 0
- MINOR: +0.3 (WebSocket callback pattern)
- Clean passes: -6.0

**Total: S = -5.7** → **ACCEPT**

### Summary

The Dashboard UI is production-ready with:
- Comprehensive error handling and input validation
- Proper async operation management with AbortController
- Defensive coding patterns (division by zero guards, fallbacks)
- Good UX patterns (loading states, background refresh without flickering)
- Memory management (clearing data, limiting arrays)
- Responsive design considerations

No fixes required for deployment.

---

## Deep Verify F13: Strategy Builder UI (2026-01-21)

**Verdict: UNCERTAIN** (S = -1.4) - Good dedicated builder, issues in embedded builder

### BUG-DV-034: Validation Stub Always Returns Valid [IMPORTANT]

**Problem:** W `strategies/page.tsx` funkcja `handleValidateStrategy` jest stubem który zawsze zwraca `isValid: true`. Strategie mogą być zapisywane bez walidacji.

**Lokalizacja:** `frontend/src/app/strategies/page.tsx:526-534`

**Szczegóły:**
```typescript
const handleValidateStrategy = async (strategy: Strategy5Section): Promise<StrategyValidationResult> => {
  // TODO: Implement validation logic
  return {
    isValid: true,  // ← ZAWSZE true!
    errors: [],     // ← Zawsze pusty
    warnings: [],
    sectionErrors: {}
  };
};
```

**Do naprawy:**
1. Zaimplementować faktyczną walidację lub użyć API walidacji z backendu:
   ```typescript
   const handleValidateStrategy = async (strategy: Strategy5Section): Promise<StrategyValidationResult> => {
     try {
       const response = await apiService.validateStrategy(strategy);
       return response.data;
     } catch (error) {
       // Fallback to local validation (jak w strategy-builder/page.tsx:304-332)
       const errors: string[] = [];
       if (!strategy.name?.trim()) errors.push('Strategy name is required');
       if (!strategy.s1_signal?.conditions?.length) errors.push('S1 section must have at least one condition');
       // ... więcej reguł
       return { isValid: errors.length === 0, errors, warnings: [], sectionErrors: {} };
     }
   };
   ```

**Uwaga:** Dedykowana strona `strategy-builder/page.tsx` MA działającą walidację z fallbackiem (linie 292-333).

---

### BUG-DV-035: Empty Indicator Variants in Embedded Builder [IMPORTANT]

**Problem:** W `strategies/page.tsx` tablica `indicatorVariants` jest zainicjalizowana jako pusta i nigdy nie jest wypełniana. Zakładka "Builder" nie ma dostępnych wskaźników.

**Lokalizacja:** `frontend/src/app/strategies/page.tsx:201`

**Szczegóły:**
```typescript
const [indicatorVariants] = useState<IndicatorVariant[]>([]);  // ← Pusta i nigdy nie ładowana!

// ... później używana w:
<StrategyBuilder5Section
  availableIndicators={indicatorVariants}  // ← Pusta tablica
  onSave={handleSaveStrategy}
  onValidate={handleValidateStrategy}
/>
```

**Do naprawy:**
1. Dodać ładowanie wskaźników w `useEffect`:
   ```typescript
   const [indicatorVariants, setIndicatorVariants] = useState<IndicatorVariant[]>([]);

   useEffect(() => {
     const loadIndicators = async () => {
       const variants = await apiService.getVariants();
       setIndicatorVariants(variants.map(mapApiVariantToIndicatorVariant));
     };
     loadIndicators();
   }, []);
   ```

2. LUB: Usunąć zakładkę "Builder" z `strategies/page.tsx` i kierować użytkowników do dedykowanej strony `/strategy-builder` która ma poprawną implementację.

---

### Minor Issues (nie blokujące):

1. **handleEditStrategy incomplete** (`strategies/page.tsx:453-456`)
   - Przełącza na zakładkę Builder bez ładowania danych strategii
   - TODO komentarz w kodzie

2. **handleCopyStrategy not implemented** (`strategies/page.tsx:458-480`)
   - Wyświetla toast "not yet implemented"
   - Zakomentowana implementacja w kodzie

---

### Clean Passes (8 × -0.5 = -4.0):

1. **NaN Validation in ConditionBlock** (`ConditionBlock.tsx:64-72`)
   - `if (!isNaN(numValue))` przed aktualizacją wartości ✓

2. **maxDepth Protection in ConditionGroup** (`ConditionGroup.tsx:91-94`)
   - `if (depth >= maxDepth) { alert(...); return; }` zapobiega nieskończonemu zagnieżdżaniu ✓

3. **Fallback Local Validation** (`strategy-builder/page.tsx:304-332`)
   - Lokalna walidacja gdy API zawiedzie ✓

4. **Delete Confirmation Dialog** (`strategy-builder/page.tsx:485-506`)
   - Proper MUI Dialog z potwierdzeniem przed usunięciem ✓

5. **Timer Cleanup in QuickBacktestPreview** (`QuickBacktestPreview.tsx:245`)
   - `return () => clearTimeout(timer)` ✓

6. **Strategy Name Validation Before Backtest** (`QuickBacktestPreview.tsx:201-204`)
   - Sprawdza `strategy.name` przed uruchomieniem ✓

7. **UUID-based Condition IDs** (`ConditionGroup.tsx:12,70,97`)
   - Używa `uuidv4()` dla unikalnych ID ✓

8. **Error Handling in All API Calls**
   - try/catch z notification we wszystkich operacjach API ✓

---

### Score Calculation:
- IMPORTANT: 2 × (+1) = +2
- MINOR: 2 × (+0.3) = +0.6
- Clean passes: -4.0

**Total: S = -1.4** → **UNCERTAIN**

### Summary

Strategy Builder UI ma dwa tryby:

1. **`/strategy-builder`** (dedykowana strona) - **DOBRZE ZAIMPLEMENTOWANA**
   - Ładuje wskaźniki z API
   - Ma fallback walidację
   - Pełna funkcjonalność

2. **`/strategies`** (embedded builder) - **MA PROBLEMY**
   - Walidacja jest stubem (zawsze true)
   - Brak wskaźników w builderze
   - Kilka funkcji niezaimplementowanych

**Rekomendacja:** Albo naprawić embedded builder w `/strategies`, albo usunąć zakładkę "Builder" i kierować użytkowników do `/strategy-builder`.

---

## Deep Verify F14: Backtest UI (2026-01-21)

**Verdict: ACCEPT** (S = -6.0) - Excellent implementation with comprehensive validation

### No Issues Found

Backtest UI jest jednym z najlepiej zaimplementowanych obszarów w systemie. Nie znaleziono żadnych problemów.

### Clean Passes (12 × -0.5 = -6.0):

1. **Debounced Data Availability Check with Cleanup** (`BacktestSetupForm.tsx:240-241`)
   ```typescript
   const timeoutId = setTimeout(checkAvailability, 500);
   return () => clearTimeout(timeoutId);
   ```

2. **Auto-refresh Interval with Cleanup** (`SessionSelector.tsx:131-136`)
   ```typescript
   const interval = setInterval(() => loadSessions(), refreshInterval);
   return () => clearInterval(interval);
   ```

3. **Comprehensive Form Validation** (`BacktestSetupForm.tsx:248-291`)
   - Strategy selection validation
   - Symbol selection validation
   - Date format validation (`isValid()`)
   - Date range validation (max 365 days, end after start, not in future)

4. **Date Range Validation** (`BacktestSetupForm.tsx:273-288`)
   - `startDate >= endDate` → "End date must be after start date"
   - `daysDiff > 365` → "Date range cannot exceed 365 days"
   - `endDate > new Date()` → "End date cannot be in the future"

5. **Error Handling with Fallback Responses** (`backtestApi.ts:133-146`)
   - Returns default "unavailable" response on API error instead of crashing
   - `quality_issues: [error.message || 'Failed to check data availability']`

6. **Loading States for All Async Operations**
   - `loadingStrategies`, `loadingSymbols`, `loadingDataSessions`
   - `checkingAvailability`, `isSubmitting`

7. **Session Quality Validation** (`SessionSelector.tsx:163-207`)
   - Minimum records check
   - Required symbols validation
   - Session age warning (> 30 days)

8. **Comprehensive Test Coverage** (`BacktestSetupForm.test.tsx`)
   - 868 lines, 20+ test cases
   - Covers all acceptance criteria (AC1-AC8)
   - Tests rendering, validation, submission, error handling

9. **Graceful API Degradation** (`backtestApi.ts:245-250`)
   - `getSymbols()` returns common symbols as fallback on API error
   - System doesn't crash if exchange API is down

10. **Form Submission Prevention** (`BacktestSetupForm.tsx:333`)
    - `e.preventDefault()` before validation

11. **Input Value Clamping** (`BacktestSetupForm.tsx:736-737`)
    ```typescript
    Math.max(1, Math.min(100, parseInt(e.target.value) || 1))
    ```
    - Prevents invalid acceleration factor values

12. **Data Quality Visual Indicators** (`SessionSelector.tsx:210-218`)
    - `good` → CheckCircleIcon (green)
    - `warning` → WarningIcon (yellow)
    - `error` → ErrorIcon (red)

### Additional Quality Indicators:

- **Acceptance Criteria Documentation**: All AC1-AC8 documented in component header
- **Backward Compatibility**: `/backtesting` redirects to `/dashboard?mode=backtest`
- **Search/Filter Functionality**: Session selector with real-time search
- **Auto-refresh**: Sessions list refreshes every 30 seconds

### Score Calculation:
- CRITICAL: 0
- IMPORTANT: 0
- MINOR: 0
- Clean passes: -6.0

**Total: S = -6.0** → **ACCEPT**

### Summary

Backtest UI jest production-ready z:
- Kompletną walidacją formularza i dat
- Sprawdzaniem dostępności danych z API
- Graceful degradation przy błędach API
- Comprehensive test coverage (868 linii testów)
- Wizualnymi wskaźnikami jakości danych
- Proper cleanup we wszystkich useEffect hooks

No fixes required for deployment.

---

## Deep Verify F15: Trading UI (2026-01-21)

**Verdict: ACCEPT** (S = -5.7) - Production-ready with minor issues

### Issues Found:

#### Related to BUG-DV-031 (Duplicate WebSocket Implementations):

Następujące komponenty używają przestarzałego hooka `useWebSocket` zamiast singletona `wsService`:

| Component | File | Line | Status |
|-----------|------|------|--------|
| PositionMonitor | `components/trading/PositionMonitor.tsx` | 60 | Uses `useWebSocket` hook |
| RiskAlerts | `components/trading/RiskAlerts.tsx` | 58 | Uses `useWebSocket` hook |
| LiquidationAlert | `components/trading/LiquidationAlert.tsx` | 83 | ✅ Uses `wsService` singleton |

**Naprawa:** Przy naprawie BUG-DV-031 należy zaktualizować PositionMonitor.tsx i RiskAlerts.tsx do użycia `wsService` singleton (wzór: LiquidationAlert.tsx).

---

#### Minor Issue: No NaN Validation for SL/TP (+0.3)

**Lokalizacja:** `frontend/src/components/trading/PositionMonitor.tsx:188-189`

```typescript
const stopLoss = parseFloat(editingSLTP.stopLoss);
const takeProfit = parseFloat(editingSLTP.takeProfit);
// Missing: if (isNaN(stopLoss) || isNaN(takeProfit)) return;
```

**Do naprawy:** Dodać walidację NaN przed wysłaniem:
```typescript
const stopLoss = parseFloat(editingSLTP.stopLoss);
const takeProfit = parseFloat(editingSLTP.takeProfit);
if ((editingSLTP.stopLoss && isNaN(stopLoss)) || (editingSLTP.takeProfit && isNaN(takeProfit))) {
  alert('Invalid SL/TP value');
  return;
}
```

---

### Clean Passes (12 × -0.5 = -6.0):

1. **Production-Ready Session Configuration** (`trading-session/page.tsx`)
   - Real API calls to `/api/strategies` and `/api/data-collection/sessions`
   - Proper validation: `canStart` requires strategies + symbols + (backtest session if mode=backtest)
   - Loading states for all async operations
   - Error handling with try/catch

2. **Backward Compatibility** (`trading/page.tsx`)
   - Clean redirect: `/trading` → `/dashboard?mode=live`

3. **LiquidationAlert Uses Correct Pattern** (`LiquidationAlert.tsx:83-142`)
   - Uses `wsService` singleton (BUG-007.1b fix)
   - Proper cleanup: `return () => { cleanup(); wsService.unsubscribe('paper_trading'); }`

4. **Live Trading Warning Alert** (`trading-session/page.tsx:360-365`)
   - Red alert for live mode: "WARNING: Real Money Trading"

5. **Mode-Specific UI** (`trading-session/page.tsx:360-377`)
   - Live: Red warning alert
   - Paper: Blue info alert
   - Backtest: Blue info alert with data session selector

6. **Loading States** (`trading-session/page.tsx:113-115`)
   - `loadingStrategies`, `loadingSessions`, `startingSession`

7. **Error Handling** (`trading-session/page.tsx:117-120`)
   - `strategiesError`, `sessionsError`, `startError`

8. **Margin Ratio Color Coding** (`PositionMonitor.tsx:211-215`)
   - `< 15%` → red (critical)
   - `< 25%` → yellow (warning)
   - `>= 25%` → green (safe)

9. **P&L Color Coding** (`PositionMonitor.tsx:218-222`)
   - Positive → green
   - Negative → red
   - Zero → gray

10. **Audio Alerts for Critical Risks** (`RiskAlerts.tsx:109-113`)
    - Plays `/sounds/alert.mp3` for CRITICAL severity
    - Error handling: `.catch(err => Logger.warn(...))`

11. **Position Close Confirmation** (`PositionMonitor.tsx:129`)
    - Uses `confirm()` dialog before closing position

12. **Mockup Clearly Marked** (`SessionConfigMockup.tsx:183-187`)
    - Warning banner: "⚠️ MOCKUP COMPONENT - NOT FUNCTIONAL"
    - Production code uses `trading-session/page.tsx` instead

---

### Score Calculation:
- CRITICAL: 0
- IMPORTANT: 0 (issues related to BUG-DV-031 already documented)
- MINOR: +0.3 (NaN validation missing)
- Clean passes: -6.0

**Total: S = -5.7** → **ACCEPT**

### Summary

Trading UI jest production-ready z:
- Kompletną konfiguracją sesji tradingowej z real API
- Proper validation i loading states
- Ostrzeżeniami dla live trading mode
- Good UX dla position management (expand details, color coding)
- Mockup component clearly marked as non-functional

Jedyny wymagany fix to NaN validation dla SL/TP, która jest MINOR issue.
Komponenty używające `useWebSocket` hook zostaną naprawione przy okazji BUG-DV-031.

---

## Deep Verify F16: State Management (2026-01-21)

**Scope:** Zustand stores (`frontend/src/stores/`)
**Files examined:** 10 store files - dashboardStore.ts, websocketStore.ts, tradingStore.ts, authStore.ts, uiStore.ts, healthStore.ts, debugStore.ts, types.ts, index.ts
**Verdict: ACCEPT (S = -5.7)**

---

### Clean Passes (12 × -0.5 = -6.0):

1. **All stores use Zustand with devtools middleware**
   - Proper middleware configuration in all 7 implementation stores
   - `enabled: process.env.NODE_ENV === 'development'` for conditional devtools

2. **Good selector patterns for optimized re-renders**
   - All stores export individual selectors (e.g., `useMarketData`, `useActiveSignals`)
   - Prevents unnecessary re-renders through granular subscriptions

3. **No direct state mutations**
   - All state updates use immutable patterns with spread operators
   - No `.push()` or `.splice()` found - all arrays use filter/map/slice

4. **Proper error handling in async actions**
   - All async actions wrapped in try/catch
   - Error states set with meaningful error messages
   - Loading states properly managed (set true before, false after)

5. **Input validation in dashboardStore setters**
   - `setMarketData`: validates array with `Array.isArray(data) ? data : []`
   - `setActiveSignals`: validates array with `Array.isArray(signals) ? signals : []`
   - `addSignal`: null check with `if (!signal) return;`

6. **Circular buffers prevent memory issues**
   - `healthStore`: max 50 alerts with `slice(0, 49)` before adding
   - `debugStore`: max 50 messages with `slice(0, 49)` before adding
   - `dashboardStore.addSignal`: keeps only latest 10 signals

7. **Reset functions for cleanup in all stores**
   - Every store implements `reset: () => set(initialState)`
   - Enables clean state reset on logout or error recovery

8. **SSR-safe checks**
   - `uiStore`: `typeof window !== 'undefined'` before localStorage access
   - `authStore`: safe localStorage access in persist middleware

9. **Type guards for API response validation**
   - `dashboardStore.fetchMarketData`: validates each item has required fields
   - `dashboardStore.fetchIndicators`: validates indicator structure
   - Filters out invalid items with logging

10. **authStore properly clears refresh timers**
    - `clearTimeout(refreshTimer)` called in logout (line 160)
    - `clearTimeout(refreshTimer)` called in token refresh failure (line 97)
    - `clearTimeout(refreshTimer)` called in refresh success before scheduling new (line 209)

11. **Proper immutable state updates**
    - `set(state => ({ ...state, field: newValue }))` pattern throughout
    - Object spread for nested updates in dialogs, loadingStates

12. **Good separation of state, actions, and selectors**
    - All stores follow same pattern: initialState, actions, middleware
    - Exported selectors separate from store for tree-shaking
    - Action hooks (e.g., `useDashboardActions`) bundle related actions

---

### Minor Issues (1 × +0.3 = +0.3):

### NOTE-DV-F16-001: Async fetch operations lack AbortController [MINOR]

**Problem:** Async fetch methods don't use AbortController for cancellation. Rapid calls could cause race conditions where older response overwrites newer state.

**Lokalizacja:** All fetch methods in dashboardStore.ts, tradingStore.ts

**Szczegóły:**
```typescript
// Current pattern (tradingStore.ts:94):
fetchWalletBalance: async () => {
  try {
    set({ walletLoading: true, walletError: null });
    const balance = await apiService.getWalletBalance();
    set({ walletBalance: balance, walletLoading: false });
    // No way to cancel if component unmounts or new fetch starts
  }
}
```

**Uwaga:** This is theoretical risk - in practice, loading states prevent UI issues and the stores are global singletons. Standard Zustand pattern.

**Do rozważenia (nice-to-have):**
```typescript
fetchWalletBalance: async (signal?: AbortSignal) => {
  try {
    set({ walletLoading: true });
    const balance = await apiService.getWalletBalance({ signal });
    if (!signal?.aborted) {
      set({ walletBalance: balance, walletLoading: false });
    }
  }
}
```

---

### Score Calculation:
- CRITICAL: 0
- IMPORTANT: 0
- MINOR: +0.3 (theoretical race condition)
- Clean passes: -6.0

**Total: S = -5.7** → **ACCEPT**

### Summary

State management layer jest dobrze zaprojektowany z:
- Spójnym wzorcem Zustand we wszystkich storach
- Proper validation i error handling
- Memory safeguards (circular buffers)
- Good separation of concerns
- authStore security issue (BUG-DV-030) już udokumentowany w F11

Brak krytycznych lub ważnych problemów. Jedyna uwaga to teoretyczne ryzyko race conditions przy rapid fetch calls, ale jest to standardowy Zustand pattern i loading states zapewniają praktyczną ochronę.
