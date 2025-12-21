# Znane Problemy i Ograniczenia

## Aktywne Problemy

### [NAPRAWIONE 2025-12-03] KI1: Backtest czasem nie generuje sygnałów
**Objawy:** ticks_processed > 0, ale signals_detected = 0
**Przyczyna:**
1. Timeout 2.0s w `on_indicator_updated` powodował anulowanie generowania sygnałów przed ich opublikowaniem
2. `add_indicator_to_session()` nie rejestrowała wskaźników time-driven dla symboli
3. `MexcPaperAdapter` brakowało metody `create_market_order()` wymaganej przez `LiveOrderManager`

**Fix (2025-12-03):**
1. Usunięto timeout w `strategy_manager.py:on_indicator_updated` - sygnały mogą się teraz generować bez ograniczenia czasowego
2. Dodano rejestrację time-driven indicators w `add_indicator_to_session()`
3. Dodano metodę `create_market_order()` w `MexcPaperAdapter` jako wrapper na `place_futures_order()`

**Status:** NAPRAWIONE - Backtest generuje sygnały i otwiera pozycje paper

**Weryfikacja:** Logi pokazują pełny przepływ:
- `strategy_manager.slot_acquire_result` → `slot_acquired: true`
- `mexc_paper_adapter.create_market_order_wrapper`
- `mexc_paper_adapter.order_filled`
- `strategy_manager.signal_generated`


### KI2: WebSocket reconnection nie zawsze działa
**Objawy:** Frontend traci połączenie i nie odzyskuje automatycznie
**Przyczyna:** Brak pełnej implementacji reconnection logic
**Workaround:** Odśwież stronę (F5)
**Status:** Do naprawy

### KI3: Memory usage rośnie przy długich sesjach
**Objawy:** Backend zużywa coraz więcej RAM przy >24h pracy
**Przyczyna:** Niektóre struktury danych nie są czyszczone
**Workaround:** Restartuj backend co 24h
**Status:** Wymaga audytu memory management

### [NAPRAWIONE 2025-12-02] KI4: Brakująca metoda RiskManager.use_budget()
**Objawy:** `AttributeError: 'RiskManager' object has no attribute 'use_budget'` przy próbie otwarcia pozycji
**Lokalizacja:** `strategy_manager.py:1624` wywołuje `risk_manager.use_budget()` która nie istnieje w `risk_manager.py`
**Przyczyna:** Metoda została zaplanowana ale nigdy zaimplementowana

**Fix:** Dodano kompletną implementację zarządzania budżetem w `risk_manager.py`:
- `use_budget(strategy_name, amount)` - rezerwuje budżet dla strategii
- `release_budget(strategy_name, amount)` - zwalnia budżet gdy pozycja jest zamknięta
- `get_allocated_budget(strategy_name)` - pobiera alokowany budżet
- `get_available_capital()` - dostępny kapitał

Dodano również zwolnienie budżetu w `strategy_manager.py` przy zamykaniu pozycji (ZE1 i E1).

**Impact:** Odblokowuje otwieranie pozycji w live/paper trading.

---

## Problemy Bezpieczeństwa (Red Team Analysis 2025-12-21)

Zidentyfikowane przez analizę adversarialną Red Team vs Blue Team.

### SEC-P0: Race Condition w Position Close/Modify
**Severity:** 🔴 CRITICAL
**Wektor:** Jednoczesne wysłanie dwóch requestów close na tę samą pozycję
**Ryzyko:** Double-close pozycji, nieprawidłowe obliczenie P&L, osierocone ordery
**Fix:** Dodać distributed locking na operacjach pozycji (mutex per position_id)
**Status:** Do naprawy

### SEC-P0: Strategy JSON Injection
**Severity:** 🔴 CRITICAL
**Wektor:** Malformed strategy JSON z visual buildera może zawierać złośliwe nazwy indykatorów
**Ryzyko:** Wykonanie nieautoryzowanego kodu, crash systemu
**Fix:** Implementacja allowlist dla nazw indykatorów/akcji, walidacja server-side
**Status:** Do naprawy

### SEC-P0: WebSocket State Desync
**Severity:** 🔴 CRITICAL
**Wektor:** Brak Redis = stan w pamięci. Disconnect/reconnect = stale data
**Ryzyko:** Użytkownik widzi nieaktualne pozycje, podejmuje błędne decyzje tradingowe
**Fix:** Protokół rekoncyliacji stanu przy WS reconnect
**Status:** Do naprawy (powiązane z KI2)

### SEC-P1: API Key Exposure w Logach/Błędach
**Severity:** 🟠 HIGH
**Wektor:** Błędy z MEXC adapter mogą zawierać API keys w stack trace
**Ryzyko:** Kompromitacja konta exchange
**Fix:** Sanityzacja wszystkich error messages, maskowanie credentials
**Status:** Do naprawy

### SEC-P1: Order Idempotency
**Severity:** 🟠 HIGH
**Wektor:** Brak idempotency keys na orderach
**Ryzyko:** Duplikaty orderów przy retry/reconnect
**Fix:** Dodać idempotency key do każdego order request
**Status:** Do naprawy

### SEC-P1: State Machine Transition Bypass
**Severity:** 🟠 HIGH
**Wektor:** Wymuszenie nieprawidłowych przejść stanów przez API
**Ryzyko:** Korupcja lifecycle pozycji
**Fix:** Server-side walidacja wszystkich state transitions
**Status:** Do naprawy

### SEC-P2: MEXC Adapter Circuit Breaker
**Severity:** 🟡 MEDIUM
**Wektor:** Kaskadowe awarie przy problemach z API MEXC
**Ryzyko:** System hang, utrata responsywności
**Fix:** Implementacja circuit breaker pattern
**Status:** Do rozważenia

### SEC-P2: Division by Zero w Indykatorach
**Severity:** 🟡 MEDIUM
**Wektor:** Edge cases w custom indicators (zero volume, zero price)
**Ryzyko:** Crash kalkulacji, brak sygnałów
**Fix:** Defensive math we wszystkich indykatorach
**Status:** Do rozważenia

---

## Ograniczenia Architektury

### OA1: Tylko MEXC Futures
System obecnie wspiera tylko giełdę MEXC Futures. Inne giełdy (Binance, Bybit) wymagają nowych adapterów.

### OA2: Single-node deployment
System nie jest zaprojektowany na skalowanie horyzontalne. Dla wysokich obciążeń potrzebna byłaby architektura distributed.

### OA3: Brak persystencji stanu strategii
Restart backendu resetuje stan strategii (np. czy jest w trakcie oczekiwania na entry). Warunki czasowe (duration) tracą kontekst.

---

## Naprawione Problemy (Historia)

### [NAPRAWIONE 2025-12-02] KI6: Case sensitivity w condition mapping
**Objawy:** Condition z uppercase condition_type (np. "PRICE_VELOCITY") nie matchuje lowercase indicator_type ("price_velocity")
**Przyczyna:** Brak normalizacji case przy porównywaniu
**Fix:** Dodano case-insensitive matching w `Condition.evaluate()` - porównuje lowercase obu stron
**Impact:** Warunki strategii działają niezależnie od wielkości liter w condition_type

### [NAPRAWIONE 2025-12-02] KI5: Brak wskaźnika signal_age_seconds
**Objawy:** Strategia używa `signal_age_seconds` w O1 (Signal Cancellation), ale wskaźnik nie istnieje
**Przyczyna:** Wskaźnik nie zaimplementowany
**Fix:**
1. Dodano `SIGNAL_AGE_SECONDS` do IndicatorType enum
2. Dodano `signal_detection_time` do Strategy dataclass
3. StrategyManager oblicza signal_age_seconds przed ewaluacją O1
**Impact:** O1 (Signal Cancellation) działa poprawnie - może anulować sygnały na podstawie czasu

### [NAPRAWIONE 2025-12-02] OfflineIndicatorEngine nie ładował danych z session_id
**Objawy:** `add_indicator()` zwracał 0 data points mimo że dane były w QuestDB
**Przyczyna:** Metoda `add_indicator()` nie przekazywała `session_id` do `_load_symbol_data()`; dodatkowo `_load_symbol_data()` używała niepoprawnego `asyncio.get_event_loop()` w Python 3.13
**Fix:**
1. Dodano parametr `session_id` do `add_indicator()`
2. Naprawiono `_load_symbol_data()` - użycie `asyncio.run()` zamiast deprecjonowanego `get_event_loop()`
**Impact:** Wskaźniki są teraz poprawnie obliczane na danych historycznych

### [NAPRAWIONE 2025-12-02] Błędy testów E2E - niezgodność z architekturą RiskManager
**Objawy:** ~13 testów failowało z błędami:
- `AttributeError: 'RiskManager' object has no attribute 'settings'`
- `AttributeError: 'dict' object has no attribute 'level'`
- `AttributeError: 'AppSettings' object has no attribute 'max_position_size_percent'`

**Przyczyna:** Testy nie zostały zaktualizowane po zmianie architekturalnej 2025-11-30 (RiskManager: settings → risk_config)

**Fix:** Zaktualizowano 3 pliki testowe:
- [test_container_multi_agent_integration.py](tests_e2e/e2e/test_container_multi_agent_integration.py) - zmiana `risk_manager.settings` → `risk_manager.risk_config`
- [test_security_vulnerabilities.py](tests_e2e/integration/test_security_vulnerabilities.py) - dodanie `SimpleNamespace` helper dla StructuredLogger
- [test_risk_manager.py](tests_e2e/unit/test_risk_manager.py) - zmiana fixture `settings` → `risk_config`

**Impact:** +41 testów przeszło (317 → 358), -40 błędów (124 → 84). Pass rate: 59% → 66.8%

### [NAPRAWIONE 2025-12-02] Bloker: Endpoint /api/strategies/active nie działał
**Objawy:** Endpoint `/api/strategies/active` zwracał błąd "Strategy active not found or deleted"
**Przyczyna:** Brak dedykowanego endpointa - "active" było traktowane jako `{strategy_id}` w parametrze ścieżki
**Fix:** Dodano nowy endpoint `GET /api/strategies/active` w [unified_server.py:885-903](src/api/unified_server.py#L885-L903) przed endpointem `/{strategy_id}`. Zwraca listę enabled strategii.
**Impact:** Trader może teraz widzieć które strategie są aktywne.

### [NAPRAWIONE 2025-12] Bug G1: Dead code w evaluate_risk_assessment
Metoda `evaluate_risk_assessment()` odwoływała się do nieistniejącego `self.risk_assessment`.
**Fix:** Usunięto dead code

### [NAPRAWIONE 2025-12] Bug G2: Brakujące metody w RiskManager
`strategy_manager.py` wywoływał `assess_position_risk()` i `can_open_position_sync()` które nie istniały.
**Fix:** Dodano brakujące metody

### [NAPRAWIONE 2025-11] Security fixes Sprint 16
- Credentials w logach
- Słabe JWT secrets
- CORS issues
**Fix:** 7 poprawek bezpieczeństwa

### [NAPRAWIONE 2025-11] Race conditions
5 race conditions w StrategyManager i ExecutionController
**Fix:** Dodano locki i synchronizację

---

## Jak Zgłaszać Nowe Problemy

1. Sprawdź czy problem nie jest już na liście
2. Dodaj sekcję z formatem:

```markdown
### KI[numer]: [Krótki tytuł]
**Objawy:** Co użytkownik widzi
**Przyczyna:** Jeśli znana
**Workaround:** Tymczasowe rozwiązanie
**Status:** Do naprawy / Wymaga analizy / Niski priorytet
```

3. Jeśli naprawiłeś problem, przenieś do sekcji "Naprawione Problemy"
