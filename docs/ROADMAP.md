# Product Roadmap

> Last reviewed: 2025-11-02 — Sprint 16 status synchronized; time window semantics problem marked as resolved; database migration status updated.

---

## Automated Updates (2025-11-02)

### Current Sprint Section
**Justification**: Sprint 16 progress requires roadmap updates to reflect completed tasks
**Benefits**: Improves visibility of resolved issues, accurate status tracking
**Consistency improvements**: Ensures roadmap reflects actual implementation status
**Quality enhancements**: Better prioritization prevents duplication of completed work



## 2) Wskaźniki — Od Mocków do Realnych Obliczeń
**Cel:** Przekształcenie silnika wskaźników z prototypu zwracającego fałszywe dane w realnie działający, wydajny i niezawodny komponent obliczeniowy. Bez tego system jest bezużyteczny.

**GOAL_IMPORTANT_01_INDICATORS - Simple Indicators Implementation:**
Implementacja prostych, niezawodnych wskaźników dla Strategy Builder opartych na istniejącym StreamingIndicatorEngine. Priorytet na fundamentalne agregatory (GRUPA A) i podstawowe velocity indicators (GRUPA B) które mogą być natychmiast wykorzystane w strategiach tradingowych.

**Rozwiązane Problemy Krytyczne:**
- ✅ **Problem 1: Semantyka Okien Czasowych** - Standaryzacja na `t1 > t2` gdzie `t1` to sekundy wstecz dla startu, `t2` dla end. Przykład: `TWPA(300, 0)` = "od 5 minut temu do teraz"
- ✅ **Problem 2: Ryzyka DAG Zależności** - Implementacja circuit breaker pattern z timeout 5s, graceful degradation przy utracie danych, mechanizmy fallback
- ✅ **Problem 3: Luka Cache Czasowa** - Time-bucketed cache klucze z timestamp buckets (60s granularity): `"TWPA:BTC_USDT:1m:300:0:1727209200"`

**Implementowane Wskaźniki:**
- **GRUPA A (Priorytet 1):** `max_price()`, `min_price()`, `first_price()`, `last_price()`, `sum_volume()`, `avg_volume()`, `count_deals()`, `TWPA()`, `VWAP()`
- **GRUPA B (Priorytet 2):** `Velocity()`, `Volume_Surge()`, `Volume_Concentration()`

**Architektura i komponenty:**
- **Priorytet #1: Eliminacja Mocków:** Obecnie wiele wskaźników (np. `RSI`, `MACD`) zwraca stałe, hardkodowane wartości. Ten krok polega na zastąpieniu ich **prawdziwymi algorytmami matematycznymi** opisanymi w `INDICATORS_TO_IMPLEMENT.md`. Zaczniemy od kluczowych grup (A, B, C), które są fundamentem dla reszty.

- **Refaktoryzacja `_calculate_parametric_measure`:** Obecnie jest to jedna, gigantyczna metoda, która jest trudna do testowania i modyfikacji. Zostanie ona rozbita na wiele małych, dedykowanych funkcji (np. `_compute_twpa`, `_compute_velocity`), z których każda będzie odpowiedzialna za obliczenie jednego wskaźnika. Ułatwi to zarządzanie kodem i testowanie.

- **Potoki Walidacji Danych (Data Validation Pipelines):** Zanim surowe dane z giełdy trafią do obliczeń, przejdą przez potok walidacyjny. Będzie on sprawdzał, czy dane nie są uszkodzone, czy nie zawierają anomalii lub wartości odstających. Zapobiegnie to sytuacji, w której jeden błędny odczyt z giełdy "zatruwa" wszystkie obliczenia w systemie.

- **Cache Obliczeń:** Obliczanie wskaźników jest kosztowne. Jeśli 10 strategii używa `RSI(14)` dla `BTC_USDT`, nie chcemy liczyć go 10 razy. Wprowadzimy warstwę cache (z użyciem Redis), która będzie przechowywać wyniki obliczeń. Przed każdym obliczeniem system sprawdzi, czy wynik dla danego wskaźnika, symbolu i parametrów jest już w cache. Jeśli tak, pobierze go stamtąd, oszczędzając moc obliczeniową.

## 3) Silnik Strategii — Modularność i Stan
**Cel:** Zapewnienie stabilności, bezpieczeństwa i skalowalności całego systemu poprzez refaktoryzację monolitycznych komponentów i wprowadzenie profesjonalnych rozwiązań do zarządzania stanem i bezpieczeństwem.

**Architektura i komponenty:**
- **Refaktoryzacja `WebSocketAPIServer`:** Obecnie jest to jedna, ogromna klasa, która robi wszystko. Zostanie ona podzielona na mniejsze, wyspecjalizowane serwisy, np.:
  - `SessionManager`: Zarządza cyklem życia sesji (start, stop).
  - `StrategyManager`: Zarządza konfiguracjami strategii (CRUD).
  - `ResultsProvider`: Dostarcza wyniki i statystyki.
  To uprości kod i pozwoli na niezależny rozwój każdej części.

- **Zarządzanie Stanem i Izolacja:** Obecnie restart serwera powoduje utratę wszystkich danych o sesjach. Wprowadzimy **persystencję stanu** z użyciem bazy danych w pamięci (Redis). Będzie ona przechowywać informacje o aktywnych sesjach oraz stany tymczasowe dla strategii (np. warunki `duration`). Dodatkowo, zapewnimy **izolację multi-tenant**, co oznacza, że dane jednego użytkownika będą w pełni odseparowane od danych innego (np. poprzez osobne przestrzenie nazw w Redis).

- **Warstwa Bezpieczeństwa:** Aby system był gotowy do użytku produkcyjnego, musimy zabezpieczyć dostęp.
  - **Uwierzytelnianie JWT:** Dostęp do API będzie wymagał tokenu JWT, co zapewni, że tylko zalogowani użytkownicy mogą wykonywać operacje.
  - **Zarządzanie Sekretami (Vault):** Klucze API do giełd nie będą przechowywane w plikach konfiguracyjnych, ale w bezpiecznym, zewnętrznym systemie jak HashiCorp Vault.

- **Rola `Execution Controller`:** Po refaktoryzacji, `Execution Controller` pozostanie "dyrygentem" orkiestry. Będzie zarządzał ogólnym cyklem życia sesji, ale całą logikę związaną z oceną warunków strategii przekaże do nowego, wyspecjalizowanego `StrategyEvaluator` (silnika grafowego).

## 4) UX — Interfejs użytkownika
**Cel:** Stworzenie intuicyjnego, niezawodnego i wydajnego interfejsu, który ułatwi tworzenie i monitorowanie strategii, nawet tych bardzo złożonych.

**Komponenty i funkcje:**
- **Strategy Builder (Canvas):** To serce interfejsu użytkownika.
  - **Progresywna Walidacja:** System będzie pomagał użytkownikowi na każdym kroku. Proste błędy (np. brak połączenia między węzłami) będą wykrywane natychmiast w przeglądarce (walidacja lokalna). Bardziej złożone problemy logiczne będą sprawdzane przez serwer w tle (walidacja serwerowa), a użytkownik otrzyma czytelny komunikat.
  - **Tryb Pracy Offline:** Użytkownik nie straci swojej pracy z powodu zerwania połączenia z internetem. Strategie będą zapisywane lokalnie w przeglądarce i automatycznie synchronizowane z serwerem po odzyskaniu połączenia.
  - **Szablony i Komponenty:** Aby obniżyć próg wejścia, system zaoferuje bibliotekę gotowych szablonów strategii (np. "Flash Pump Detection"). Użytkownicy będą mogli również zapisywać własne fragmenty grafów jako komponenty wielokrotnego użytku.

- **Widoki Operacyjne:** Zestaw pulpitów i paneli, które pozwolą na pełny wgląd w działanie systemu: od ogólnego dashboardu, przez podgląd strumieni danych na żywo, aż po szczegółowe, hierarchiczne wyniki dla każdej strategii i symbolu.

## 5) API — Spójność WS/REST
- Envelope: wspólne pola (version, timestamp, id, session_id gdzie ma sens).
- WS: subskrypcje ze wstępnym zasiewem danych; Results API; Strategy Management.
- REST (MVP-lite, FastAPI): `/health`, `GET /strategies`, `GET /strategies/{name}`, `POST /strategies/{name}/activate`, `POST /strategies/{name}/deactivate`, `POST /sessions`, `GET /sessions/{id}`, `POST /sessions/{id}/stop`.

**Cel:** Zapewnienie spójnego i przewidywalnego interfejsu programistycznego (API) dla komunikacji między frontendem a backendem.

**Komponenty i funkcje:**
- **Envelope (Koperta):** Każda wiadomość wymieniana między klientem a serwerem będzie opakowana w standardową strukturę (kopertę), zawierającą metadane takie jak wersja, znacznik czasu i ID sesji. Ułatwi to debugowanie i zarządzanie komunikacją.
- **Role WS i REST:**
  - **WebSocket (WS):** Używany do komunikacji w czasie rzeczywistym — subskrypcji na strumienie danych (wskaźniki, sygnały) i otrzymywania natychmiastowych aktualizacji.
  - **REST API:** Używany do operacji, które nie wymagają natychmiastowej odpowiedzi, takich jak zarządzanie konfiguracjami strategii (CRUD), uruchamianie/zatrzymywanie sesji czy pobieranie danych historycznych.

## 6) Niezawodność i Wydajność
- **Współbieżność:** Audyt i naprawa `race conditions` w `EventBus` i `ConnectionManager` poprzez wprowadzenie `asyncio.Lock`.
- **Asynchroniczność:** Zastąpienie wszystkich synchronicznych operacji I/O (np. zapis plików) ich asynchronicznymi odpowiednikami (`aiofiles`).
- **Monitoring i Obserwowalność:** Integracja z Prometheus do zbierania szczegółowych metryk (wydajność grafu, cache-ratio, opóźnienia). Wprowadzenie rozproszonego śledzenia (distributed tracing).
- **Bezpieczeństwo:** Wdrożenie uwierzytelniania JWT, zarządzania sekretami (Vault) i szyfrowania komunikacji wewnętrznej.

**Cel:** Zbudowanie systemu, który jest nie tylko funkcjonalny, ale także stabilny, szybki i bezpieczny — gotowy do działania w wymagającym środowisku produkcyjnym.

**Komponenty i funkcje:**
- **Współbieżność:** W systemie asynchronicznym wiele operacji dzieje się naraz. `Race conditions` to błędy, które powstają, gdy kolejność tych operacji jest nieprzewidywalna. Przeprowadzimy audyt kodu i wprowadzimy blokady (`asyncio.Lock`) w krytycznych sekcjach, aby zapewnić, że operacje na współdzielonych zasobach są wykonywane w bezpieczny, atomowy sposób.

- **Asynchroniczność:** Operacje wejścia/wyjścia (I/O), takie jak zapis do pliku, mogą blokować całą aplikację. Zastąpimy wszystkie takie operacje ich asynchronicznymi odpowiednikami (np. używając biblioteki `aiofiles`), aby system pozostał responsywny nawet pod dużym obciążeniem.

- **Monitoring i Obserwowalność:** Aby wiedzieć, co dzieje się "pod maską", zintegrujemy system z profesjonalnymi narzędziami:
  - **Prometheus:** Do zbierania szczegółowych metryk wydajności (np. jak szybko działa silnik grafowy, jak często trafiamy do cache'a, jakie są opóźnienia).
  - **Distributed Tracing:** Do śledzenia pojedynczego żądania przez wszystkie serwisy w systemie, co drastycznie ułatwia diagnozowanie problemów.

- **Bezpieczeństwo:** Ponowne podkreślenie kluczowych elementów z Filaru 3: wdrożenie uwierzytelniania JWT, bezpiecznego zarządzania sekretami (Vault) oraz szyfrowania komunikacji między komponentami systemu.


### 🎯 **REMAINING TASKS PRIORITY**

#### **High Priority (Next Sprint)**
1. **Implementacja Rzeczywistych Miar**: Usunięcie mocków z `StreamingIndicatorEngine`.
2. **Naprawa Błędów Współbieżności**: Zabezpieczenie krytycznych sekcji kodu (`EventBus`, `ConnectionManager`).
3. **Refaktoryzacja Architektury (Część 1)**: Podział `_calculate_parametric_measure`.

#### **Medium Priority**
4. **Refaktoryzacja Architektury (Część 2)**: Podział `WebSocketAPIServer`.
6. **Warstwa Cache i Persystencji**: Integracja z Redis.

#### **Low Priority**
7. **Implementacja Warstwy Bezpieczeństwa**: JWT i Vault.
8. **Rozbudowa UI Canvas**: Pełne wsparcie dla grafowego budowania strategii, praca offline.


### ✅ **1. Problem z Semantyką Okien Czasowych** (ROZWIĄZANY)
**Problem**: System (t1, t2) gdzie t1 > t2 był mylący i niejednoznaczny w systemie rozproszonym.
- `VWAP(300, 0)` - "od 5 minut temu do teraz" - ale co oznacza "teraz"?
- Czy to czas otrzymania danych, czas przetwarzania, czy timestamp ostatniej transakcji?

**Status**: ✅ ROZWIĄZANE w Sprint 14 (USER_REC_14)

**Rozwiązanie Zaimplementowane**:
- ✅ Standaryzacja na `(t1, t2)` gdzie `t1` to sekundy wstecz dla startu okna, `t2` dla końca
- ✅ Przykład: `TWPA(300, 0)` = "od 5 minut temu (300s) do teraz (0s)"
- ✅ Konsystentne używanie `timestamp` ostatniej transakcji jako punktu odniesienia
- ✅ Dokumentacja w `docs/trading/INDICATORS.md` i `CLAUDE.md`
- ✅ Walidacja parametrów czasowych w `src/core/time_normalization.py`

**Dowód**: Zobacz `docs/STATUS.md` - Sprint 14 ✅ Completed


### 🚨 **4. Nieadekwatne Zarządzanie Stanem dla Warunków Czasowych**
**Problem**: Warunki `duration` i `sequence` wymagają utrzymywania stanu, ale architektura nie precyzuje:
- **Persystencja stanu**: Co się dzieje ze stanem `RSI > 70 przez 30s` podczas restartu systemu?
- **Synchronizacja**: Jak zapewnić spójność stanu między różnymi instancjami systemu?
- **Cleanup**: Kiedy i jak usuwać stary stan dla nieaktywnych symboli?

**Ryzyko**: Utrata krytycznego stanu podczas restartów, niespójne decyzje między instancjami.

**Rozwiązanie Wymagane**:
- Persystencja stanu warunków czasowych w Redis z TTL
- Synchronizacja stanu między instancjami systemu
- Automatyczne cleanup nieaktywnych stanów
- Recovery mechanizmy po restartach

### 🚨 **5. Naiwne Podejście do WebSocket Reconnection**
**Problem**: Dokumentacja wspomina reconnection logic, ale nie uwzględnia:
- **Message ordering**: Po reconnection nie ma gwarancji kolejności komunikatów
- **Duplicate handling**: Brak deduplikacji komunikatów podczas reconnection
- **State recovery**: Jak odbudować stan wskaźników po utracie połączenia?

**Ryzyko**: Przetwarzanie komunikatów w złej kolejności, duplikaty transakcji, niespójny stan systemu.

**Rozwiązanie Wymagane**:
- Sequence numbering dla wszystkich komunikatów
- Deduplikacja oparta na timestamp + sequence number
- State recovery protokół z snapshot + delta updates
- Graceful handling reconnection gaps
.

## Usprawnienia i rozszerzenia (propozycje)
- Strategia
  - Wzbogacone statusy: liczba aktywnych symboli, ostatnie zdarzenia stanu; endpoint `GET /strategies/status` (wdrożony) rozszerzyć o telemetry.
  - Schemata DSL: rozbudować `docs/schema/strategy.schema.json` o `AND/OR`, `duration`, `sequence`, tolerancje i priorytety sygnałów.
- Wskaźniki
  - Filtrowanie REST po `scope`, symbolu i typie; bulk add/delete; widoczność w UI per sesja/użytkownik.
  - Kolejki obliczeń i limity CPU; harmonogram aktualizacji (rate limiter, batchowanie).
- Wyniki
  - Agregator wyników historycznych (per strategia, per symbol, per tryb) z pamięcią dyskową; łączenie live+file.
  - Endpointy: paginacja, filtry czasowe, wsparcie dla eksportów (CSV/Parquet/JSONL).
- Portfel i limity
  - Adapter MEXC (real API) + cache; walidacja budżetu per strategia i globalnie (kwota/% + rezerwy na opłaty).
  - Symulacja przy backtestach: „wirtualne" saldo i odliczanie ekspozycji.
- Operacyjność
  - Telemetria i alerty (czas odpowiedzi, błędy handlerów, liczba wiadomości); dashboard health.
  - Retry i circuit-breaker w krytycznych ścieżkach (np. zapis wyników, publikacja eventów).
  - Obsługa degradacji (tryb tylko do odczytu przy problemach z adapterami).








