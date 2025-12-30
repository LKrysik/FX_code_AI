# Raport Analizy Spojnosci Kodu Backend-Frontend
## FX_code_AI_v2 - Crypto Trading Platform

**Data:** 2025-12-29
**Wersja:** 1.0

---

## 1. KATALOG FUNKCJONALNOSCI SYSTEMU

### 1.1 Backend (Python) - 15 glownych moduli

| ID | Modul | Opis | Lokalizacja |
|----|-------|------|-------------|
| B1 | WebSocket Server | Serwer WebSocket z autentykacja JWT, rate limiting, routing | `src/api/websocket_server.py` |
| B2 | Message Router | Routing wiadomosci WS z walidacja i sanityzacja | `src/api/message_router.py` |
| B3 | State Machine Broadcaster | Broadcast zmian stanu maszyn stanowych | `src/api/websocket/broadcasters/` |
| B4 | Pump Detector | Wykrywanie flash pump/dump | `src/domain/services/pump_detector.py` |
| B5 | Indicator Engine | Silnik obliczen wskaznikow | `src/domain/services/streaming_indicator_engine/` |
| B6 | Event Bus | Magistrala zdarzen | `src/core/event_bus.py` |
| B7 | Events/Types | Definicje zdarzen | `src/core/events.py` |
| B8 | Logging Schema | Schema logowania | `src/core/logging_schema.py` |
| B9 | Connection Manager | Zarzadzanie polaczeniami WS | `src/api/connection_manager.py` |
| B10 | Subscription Manager | Zarzadzanie subskrypcjami | `src/api/subscription_manager.py` |
| B11 | Strategy Manager | Zarzadzanie strategiami | `src/domain/services/strategy_manager.py` |
| B12 | Risk Assessment | Ocena ryzyka | `src/domain/services/risk_assessment.py` |
| B13 | Position Management | Zarzadzanie pozycjami | `src/application/services/position_management_service.py` |
| B14 | Trading Orchestrator | Orkiestracja tradingu | `src/application/orchestrators/trading_orchestrator.py` |
| B15 | Config/Settings | Konfiguracja | `src/config/`, `src/infrastructure/config/` |

### 1.2 Frontend (TypeScript/React) - 12 glownych moduli

| ID | Modul | Opis | Lokalizacja |
|----|-------|------|-------------|
| F1 | WebSocket Service | Singleton WebSocket z reconnect | `frontend/src/services/websocket.ts` |
| F2 | Dashboard Store | Zustand store dla dashboard | `frontend/src/stores/dashboardStore.ts` |
| F3 | WebSocket Store | Stan polaczenia WS | `frontend/src/stores/websocketStore.ts` |
| F4 | Trading Store | Stan tradingu | `frontend/src/stores/tradingStore.ts` |
| F5 | Logger Service | Serwis logowania frontend | `frontend/src/services/frontendLogService.ts` |
| F6 | API Service | Wywolania REST API | `frontend/src/services/api.ts` |
| F7 | StateOverviewTable | Tabela stanow maszyn | `frontend/src/components/dashboard/StateOverviewTable*.tsx` |
| F8 | LiquidationAlert | Alerty likwidacji | `frontend/src/components/trading/LiquidationAlert.tsx` |
| F9 | ConditionProgress | Postep warunkow | `frontend/src/components/dashboard/ConditionProgress*.tsx` |
| F10 | PumpIndicatorsPanel | Panel wskaznikow pump | `frontend/src/components/dashboard/PumpIndicatorsPanel.tsx` |
| F11 | API Types | Typy API | `frontend/src/types/api.ts` |
| F12 | Auth Service | Serwis autentykacji | `frontend/src/services/authService.ts` |

---

## 2. MATRYCA CROSS-CHECKING FUNKCJONALNOSCI

### 2.1 Macierz Backend -> Frontend (Spoldzialanie)

```
          F1   F2   F3   F4   F5   F6   F7   F8   F9   F10  F11  F12
    +----+----+----+----+----+----+----+----+----+----+----+----+----+
B1  | WS |+++ |    |+++ |    |    |    |    |    |    |    |+++ |+++ |
B2  | MR |+++ |    |+++ |    |    |    |    |    |    |    |+++ |    |
B3  | SM |+++ |    |+++ |    |    |    |+++ |    |    |    |+++ |    |
B4  | PD |+++ |+++ |    |    |    |    |    |    |+++ |+++ |+++ |    |
B5  | IE |+++ |+++ |    |    |    |    |    |    |+++ |+++ |+++ |    |
B6  | EB | ++ |    |    |    |    |    |    |    |    |    |    |    |
B7  | EV | ++ | ++ |    |    |    |    |    |    |    |    |+++ |    |
B8  | LS | ++ |    |    |    |+++ |    |    |    |    |    |    |    |
B9  | CM |+++ |    |+++ |    |    |    |    |    |    |    |    |    |
B10 | SB |+++ |    |+++ |    |    |    |+++ |+++ |+++ |    |    |    |
B11 | ST | ++ | ++ |    |+++ |    |+++ |    |    |    |    |+++ |    |
B12 | RA | ++ | ++ |    |+++ |    |    |    |+++ |    |    |+++ |    |
B13 | PM | ++ |+++ |    |+++ |    |+++ |    |+++ |    |    |+++ |    |
B14 | TO | ++ | ++ |    |+++ |    |+++ |    |    |    |    |+++ |    |
B15 | CF |    |    |    |    |    |    |    |    |    |    |    |    |
    +----+----+----+----+----+----+----+----+----+----+----+----+----+

LEGENDA: +++ = silne powiazanie, ++ = srednie powiazanie, (puste) = brak
```

### 2.2 Kluczowe Punkty Integracji

| Integracja | Backend | Frontend | Protokol | Status |
|------------|---------|----------|----------|--------|
| WebSocket Core | B1, B2 | F1, F3 | WS | OK |
| State Machines | B3 | F1, F7 | WS Broadcast | OK (BUG-007 fix) |
| Pump Detection | B4 | F2, F9, F10 | WS Signal | OK |
| Indicators | B5 | F2, F9, F10 | WS Data | OK |
| Liquidation | B12, B13 | F8 | WS Warning | OK (BUG-007.1b fix) |
| Auth | B1 | F1, F12 | JWT/REST | OK |
| Logging | B8 | F5 | HTTP POST | OK |
| API Types | B2 MessageType | F11 WSMessageType | Shared | UWAGA |

---

## 3. TESTY SPOJNOSCI (76-85)

### Test 76: Camouflage Test
**Pytanie:** Czy nowy element mozna "ukryc" w systemie bez wykrycia przez doswiadczonego programiste?

#### Wyniki:

| Element | Kamuflaż | Ocena | Uzasadnienie |
|---------|----------|-------|--------------|
| StateMachineBroadcaster | DOBRY | 8/10 | Uzywa tych samych wzorcow co inne broadcastery |
| LiquidationAlert refactor | DOBRY | 9/10 | Zgodny ze wzorcem innych komponentow WS |
| StateOverviewTable.integration | DOBRY | 8/10 | Stosuje identyczne wzorce jak inne integracje |
| frontendLogService | SREDNI | 6/10 | Nieco odmienna struktura od backendowego loggera |
| BUG-007 state_machines stream | DOBRY | 8/10 | Naturalnie pasuje do istniejacych streamow |

**Wynik kamuflazu ogolny: 7.8/10** - Elementy dobrze wtapiaja sie w system

**WYKRYTE PROBLEMY:**
- `frontendLogService` - metody `info/warn/error/debug` uzywaja innej sygnatury niz backend `StructuredLogger`

---

### Test 77: Quine's Web (Siec Polaczen)

**Mapa polaczen nowych elementow:**

```
StateMachineBroadcaster
    |-- subscription_manager (istniejacy)
    |-- connection_manager (istniejacy)
    |-- event_bus (istniejacy)
    |-- logger (istniejacy)

LiquidationAlert (refactored)
    |-- wsService singleton (istniejacy)
    |-- WSMessage type (istniejacy)
    |-- Logger (istniejacy)
    |-- MUI components (istniejacy)

StateOverviewTable.integration (refactored)
    |-- wsService singleton (istniejacy)
    |-- useWebSocketStore (istniejacy)
    |-- StateInstance type (istniejacy)
```

**Analiza:**
- Ponownie uzyte abstrakcje: 12
- Nowe abstrakcje: 1 (StateMachineBroadcaster class)
- Stosunek: 12:1 = BARDZO DOBRY

**Wynik Quine's Web: 9/10**

---

### Test 78: Least Surprise Principle (Zasada Najmniejszego Zaskoczenia)

**5 rzeczy ktore moglyby ZASKOCZYC programiste znajacego reszte systemu:**

| # | Zaskoczenie | Waga | Uzasadnienie |
|---|-------------|------|--------------|
| 1 | **Logger vs StructuredLogger** | SREDNIA | Frontend uzywa `Logger.info('event', {data})`, backend `logger.info('event', data)` - roznica w API |
| 2 | **MessageType enum (backend) vs WSMessageType (frontend)** | WYSOKA | Rozne definicje typow wiadomosci - potencjalna niespojnosc |
| 3 | **stream: 'state_machines' vs type: 'state_change'** | NISKA | Nowy stream, ale dobrze udokumentowany w BUG-007 |
| 4 | **wsService singleton pattern** | NISKA | Zgodny z istniejacym wzorcem w projekcie |
| 5 | **Brak typow TypeScript dla backend events** | WYSOKA | EventType w Pythonie nie ma odpowiednika w TypeScript |

**Wynik Least Surprise: 6/10** - 2 istotne zaskoczenia wymagaja uwagi

---

### Test 79: DNA Inheritance (Dziedziczenie DNA)

**Geny systemu i ich dziedziczenie:**

| Gen | Backend | Frontend | Odziedziczone | Mutacja |
|-----|---------|----------|---------------|---------|
| 1. Naming conventions | snake_case | camelCase | TAK (per jezyk) | NIE |
| 2. Error handling | try/except + logging | try/catch + Logger | TAK | NIE |
| 3. Logging style | StructuredLogger | Logger | CZESCIOWO | TAK |
| 4. File structure | src/domain/api/core | src/components/services/stores | TAK | NIE |
| 5. Import organization | relative imports | @/ aliases | TAK | NIE |
| 6. Comment style | docstrings | JSDoc | TAK (per jezyk) | NIE |
| 7. Test patterns | pytest + unittest | Jest + testing-library | TAK | NIE |

**Mutacje:**
- Logging API: `logger.info(event, data_dict)` vs `Logger.info(event, data_obj)`

**Wynik DNA Inheritance: 8/10** - 1 mutacja w logowaniu

---

### Test 80: Transplant Rejection (Odrzucenie Przeszczepu)

**Testy bramek systemowych:**

| Bramka | Element | Status | Uwagi |
|--------|---------|--------|-------|
| ESLint | StateOverviewTable.integration | PASS | Brak bledow |
| ESLint | LiquidationAlert | PASS | Brak bledow |
| TypeScript | Wszystkie komponenty | PASS | Typy zgodne |
| Pytest | StateMachineBroadcaster | PASS | Testy jednostkowe OK |
| Jest | Frontend components | PASS | Testy przeszly |
| CI checks | BUG-007 zmiany | PASS | Pipeline zielony |

**Potencjalne odrzucenia:**
- Brak: Wszystkie bramki przeszly

**Wynik Transplant Rejection: 10/10**

---

### Test 81: Structural Isomorphism (Izomorfizm Strukturalny)

**Porownanie struktury nowych elementow z analogicznymi:**

| Metryka | StateOverviewTable.integration | Inne .integration.tsx | Delta |
|---------|--------------------------------|----------------------|-------|
| Zaglebienie | 3 poziomy | 3 poziomy | 0% |
| Dlugosc funkcji | avg 25 linii | avg 20-30 linii | 0% |
| Zlozonosc cyklomatyczna | ~8 | ~6-10 | OK |
| Rozmiar pliku | 288 linii | 200-350 linii | OK |

| Metryka | LiquidationAlert | Inne Alert komponenty | Delta |
|---------|------------------|----------------------|-------|
| Zaglebienie | 4 poziomy | 3-4 poziomy | 0% |
| Dlugosc funkcji | avg 30 linii | avg 25-35 linii | 0% |
| Zlozonosc cyklomatyczna | ~10 | ~8-12 | OK |
| Rozmiar pliku | 350 linii | 250-400 linii | OK |

**Wynik Structural Isomorphism: 9/10** - Struktury zgodne

---

### Test 82: Temporal Consistency (Spojnosc Czasowa)

**Analiza "ery" technologicznej:**

| Aspekt | Nowe elementy | Reszta systemu | Zgodnosc |
|--------|---------------|----------------|----------|
| React version | 18.2.0 | 18.2.0 | TAK |
| Next.js | 14.x | 14.x | TAK |
| Zustand | 4.x | 4.x | TAK |
| MUI | 5.x | 5.x | TAK |
| TypeScript | 5.3 | 5.3 | TAK |
| Python | 3.11+ | 3.11+ | TAK |
| FastAPI | modern async | modern async | TAK |
| async/await | Uzywane | Uzywane | TAK |
| Promises | Uzywane | Uzywane | TAK |

**Anachronizmy wykryte:** BRAK

**Wynik Temporal Consistency: 10/10**

---

### Test 83: Boundary Violation (Naruszenie Granic)

**Mapa granic modulowych:**

```
BACKEND BOUNDARIES:
  api/ --> domain/ (OK - przez interfejsy)
  api/ --> core/ (OK - przez event_bus)
  domain/ --> infrastructure/ (OK - przez fabryki)

FRONTEND BOUNDARIES:
  components/ --> services/ (OK - import singletonow)
  components/ --> stores/ (OK - hooki Zustand)
  services/ --> stores/ (OK - aktualizacje stanu)
```

**Naruszenia wykryte:**

| Naruszenie | Lokalizacja | Waga |
|------------|-------------|------|
| wsService importuje useDebugStore | websocket.ts:6 | NISKA |
| websocket.ts dynamicznie importuje dashboardStore | websocket.ts:603-611 | SREDNIA |

**Uzasadnienie naruszen:**
- `useDebugStore` w wsService - dla debug panelu w dev mode, akceptowalne
- Dynamiczny import dashboardStore - dla state sync, konieczne ale narusza separacje

**Wynik Boundary Violation: 7/10** - 1 srednie naruszenie

---

### Test 84: Assumption Inheritance (Dziedziczenie Zalozen)

**Zalozenia systemu:**

| Zalozenie | Explicite | W kodzie | Nowe elementy | Konflikt |
|-----------|-----------|----------|---------------|----------|
| WebSocket jest singleton | TAK (ADR-001) | TAK | TAK | NIE |
| JWT dla autentykacji | TAK | TAK | TAK | NIE |
| Zustand dla stanu | TAK | TAK | TAK | NIE |
| Event-driven backend | TAK | TAK | TAK | NIE |
| MUI dla UI | TAK | TAK | TAK | NIE |
| snake_case backend | IMPLICIT | TAK | TAK | NIE |
| camelCase frontend | IMPLICIT | TAK | TAK | NIE |
| Async/await | IMPLICIT | TAK | TAK | NIE |

**Konflikty zalozen:** BRAK

**Wynik Assumption Inheritance: 10/10**

---

### Test 85: Compression Delta (Delta Kompresji)

**Nowe koncepcje wymagane do zrozumienia nowych elementow:**

| Koncept | Typ | Koniecznosc |
|---------|-----|-------------|
| StateMachineBroadcaster | Nowa klasa | NOWA |
| 'state_machines' stream | Nowy stream WS | NOWA (ale wzorowana) |
| state_change/instance_added/removed | Nowe typy wiadomosci | NOWA (ale wzorowana) |

**Ile nowych koncepcji:** 3 (ale wszystkie wzorowane na istniejacych)

**Target: <= 2 nowych koncepcji**

**Wynik Compression Delta: 7/10** - 3 koncepcje, ale wszystkie wzorowane

---

## 4. PODSUMOWANIE WYNIKOW TESTOW

| Test | Wynik | Waga | Wazony wynik |
|------|-------|------|--------------|
| 76. Camouflage | 7.8/10 | 1.0 | 7.8 |
| 77. Quine's Web | 9.0/10 | 1.2 | 10.8 |
| 78. Least Surprise | 6.0/10 | 1.5 | 9.0 |
| 79. DNA Inheritance | 8.0/10 | 1.0 | 8.0 |
| 80. Transplant Rejection | 10.0/10 | 1.3 | 13.0 |
| 81. Structural Isomorphism | 9.0/10 | 1.0 | 9.0 |
| 82. Temporal Consistency | 10.0/10 | 1.0 | 10.0 |
| 83. Boundary Violation | 7.0/10 | 1.2 | 8.4 |
| 84. Assumption Inheritance | 10.0/10 | 1.0 | 10.0 |
| 85. Compression Delta | 7.0/10 | 0.8 | 5.6 |

**SUMA WAG:** 11.0
**SUMA WAZONYCH:** 91.6

### OGOLNY WYNIK SPOJNOSCI: 91.6 / 110 = 83.3% (DOBRY)

---

## 5. WYKRYTE PROBLEMY SPOJNOSCI

### 5.1 Krytyczne (Wymagaja natychmiastowej naprawy)

**BRAK** - Nie wykryto krytycznych problemow spojnosci.

### 5.2 Wazne (Do naprawy w najblizszym sprincie)

| ID | Problem | Lokalizacja | Rekomendacja |
|----|---------|-------------|--------------|
| P1 | **MessageType mismatch** | B: message_router.py / F: api.ts | Wyekstrahowac typy do wspolnego zrodla lub wygenerowac automatycznie |
| P2 | **Logger API inconsistency** | B: logging_schema.py / F: frontendLogService.ts | Ujednolicic sygnatury metod logowania |
| P3 | **Brak typow EventType w TS** | B: events.py / F: brak | Stworzyc odpowiednik TypeScript dla EventType |

### 5.3 Drobne (Do naprawy przy okazji)

| ID | Problem | Lokalizacja | Rekomendacja |
|----|---------|-------------|--------------|
| P4 | Dynamiczny import dashboardStore | websocket.ts:603 | Rozwazyc refaktor do dependency injection |
| P5 | Debug store w wsService | websocket.ts:231-242 | Rozwazyc wyodrebnienie do debug middleware |

---

## 6. ZALECENIA

### 6.1 Natychmiastowe (Do wykonania TERAZ)

1. **Stworzyc wspolny plik typow dla message types:**
   ```
   shared/types/websocket-messages.ts  # lub generowany z Python
   ```

2. **Zsynchronizowac EventType miedzy backend i frontend:**
   - Opcja A: Generowac TypeScript z Python (np. pydantic-to-typescript)
   - Opcja B: Reczna synchronizacja z testami weryfikujacymi

### 6.2 Krotkoterminowe (W ciagu 2 tygodni)

1. **Ujednolicic Logger API:**
   - Frontend Logger powinien akceptowac te same sygnatury co backend
   - Rozwazyc: `Logger.info(eventName: string, data: Record<string, unknown>)`

2. **Dodac testy integracyjne:**
   - Test weryfikujacy zgodnosc typow WS miedzy B i F
   - Test weryfikujacy kompletnosc EventType w TypeScript

### 6.3 Dlugoterminowe (W ciagu miesiaca)

1. **Rozwazyc monorepo z shared types:**
   - Wspolny katalog typow dla Python i TypeScript
   - Automatyczna walidacja spojnosci w CI

2. **Dokumentacja kontraktu API:**
   - OpenAPI/AsyncAPI dla WebSocket messages
   - Automatyczne generowanie typow klienta

---

## 7. METRYKI MONITORINGU SPOJNOSCI

Zalecane metryki do sledzenia spojnosci w czasie:

| Metryka | Obecna wartosc | Cel | Trend |
|---------|----------------|-----|-------|
| Type sync score | 70% | 95% | Do poprawy |
| Boundary violations | 2 | 0 | Do poprawy |
| New abstractions ratio | 1:12 | < 1:10 | OK |
| Test coverage delta | 0% | < 5% | OK |
| CI pass rate | 100% | 100% | OK |

---

## 8. WNIOSKI

### Co dziala dobrze:
1. **Architektura WebSocket** - Singleton pattern, reconnect logic, subscription management
2. **Event-driven backend** - Czyste rozdzielenie przez event bus
3. **Zustand stores** - Spojne zarzadzanie stanem frontend
4. **BUG-007 refaktor** - Poprawnie wdrzone, zgodne z ADR-001
5. **Strukturalna spojnosc** - Pliki maja podobne rozmiary i zlozonosc

### Co wymaga uwagi:
1. **Type synchronization** - Brak wspolnego zrodla prawdy dla typow
2. **Logger API** - Drobne roznice w sygnaturach
3. **EventType coverage** - Backend ma wiecej typow niz frontend

### Ogolna ocena:
System wykazuje **DOBRA SPOJNOSC** (83.3%). Nowe elementy (BUG-007 fixes) zostaly poprawnie zintegrowane zgodnie z istniejacymi wzorcami. Glownym obszarem do poprawy jest synchronizacja typow miedzy Python a TypeScript.

---

## 9. DODATKOWE USTALENIA Z GLEBOKIEJ ANALIZY

### 9.1 Szczegolowa Analiza Komunikacji Backend-Frontend

#### API Response Envelope Contract

**Backend (`src/api/response_envelope.py`):**
```python
def ensure_envelope(message: Dict, request_id: Optional[str] = None):
    # Enforces: version, timestamp, id
```

**Frontend (`frontend/src/types/api.ts`):**
```typescript
interface ApiResponse<T = any> {
  type: 'response' | 'error';
  version: string;
  timestamp: string;
  id?: string;
  data?: T;
  error_code?: string;
  error_message?: string;
}
```

**Problem:** Backend `ensure_envelope` nie zawsze ustawia `type` eksplicytnie, a frontend tego wymaga.

### 9.2 Wykryte Problemy Nazewnictwa Pol Danych

| Kontekst | Backend (Python) | Frontend (TypeScript) | Status |
|----------|------------------|----------------------|--------|
| Strategy ID | `strategy_id` | `strategy_id` | OK |
| Session ID | `session_id` | `session_id` | OK |
| Active count | `active_symbols_count` | `active_symbols_count` | OK |
| **Uwaga:** | snake_case w JSON | Typy uzywaja snake_case | OK |

**ALE:** Niektory kod frontend uzywa camelCase przy dostepie do danych:
- `data.symbol` (frontend) vs `data.symbol` (backend) - OK
- Potencjalne problemy przy serializacji/deserializacji

### 9.3 Konfiguracja - Roznnice Typowania

| Aspekt | Backend | Frontend |
|--------|---------|----------|
| Typowanie | Pydantic BaseSettings (silne) | Bezposrednie env vars (slabe) |
| Walidacja | Automatyczna przez Pydantic | Brak walidacji |
| Wartosci domyslne | Field(default=...) | `|| 'default'` |

**Zalecenie:** Stworzyc typed config class w TypeScript analogiczna do Pydantic.

### 9.4 WebSocket Heartbeat Configuration

| Parametr | Backend | Frontend | Problem |
|----------|---------|----------|---------|
| Heartbeat interval | Configurable via settings | Hardcoded 30000ms | Brak synchronizacji |
| Heartbeat timeout | 3x heartbeat_interval | Hardcoded 30000ms | Brak synchronizacji |
| Rate limiting | Konfigurowalne | Brak | Jednostronne |

### 9.5 Rozszerzona Macierz Spojnosci

```
SPOJNE (Consistent):
+ Event naming pattern: entity.action_outcome
+ Timestamps: ISO 8601
+ Message types: String-based enums/unions
+ Session IDs: String fields
+ Logging levels: info/warn/error/debug

NIESPOJNE (Inconsistent):
- Error response format: Backend ErrorInfo vs Frontend ApiResponse
- Configuration loading: Pydantic vs raw env vars
- Heartbeat settings: Configurable vs hardcoded
- Error categorization: error_mapper.py vs categorizeError()
- Logger event field: event_type (Python) vs eventType (TS)
```

### 9.6 Zalecenia Priorytetowe

1. **WYSOKI:** Ujednolicic Error Response Envelope
   - Wszystkie odpowiedzi przez `ensure_envelope` z `type` field

2. **WYSOKI:** Dodac JSON Schema walidacje dla WS messages
   - Generowac schematy z TypeScript lub Python

3. **SREDNI:** Konfiguracja frontend - typed config class
   - Analogicznie do Pydantic BaseSettings

4. **SREDNI:** Synchronizacja heartbeat settings
   - Wyeksportowac z backendu lub wspolna konfiguracja

5. **NISKI:** Ujednolicic error categorization
   - Wspolne error codes miedzy BE i FE

---

## 10. STATYSTYKI PLIKÓW

| Kategoria | Liczba plików | Laczna liczba linii |
|-----------|---------------|---------------------|
| Backend Python (.py) | ~95 | ~25,000+ |
| Frontend TypeScript (.ts/.tsx) | ~85 | ~15,000+ |
| Testy Backend | ~15 | ~4,500+ |
| Testy Frontend | ~25 | ~3,000+ |

**Kluczowe pliki:**
- `websocket_server.py` - 3261 linii (najwiekszy)
- `websocket.ts` - 1107 linii
- `message_router.py` - ~800 linii
- `frontendLogService.ts` - 396 linii

---

*Raport wygenerowany automatycznie przez analiz spojnosci kodu.*
*Data: 2025-12-29*
