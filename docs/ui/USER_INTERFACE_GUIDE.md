# UI Guide — Trading Interface Overview and Flows (MVP → v2)

**Cel:** Opisać, co oferuje interfejs użytkownika, jak z niego korzystać krok po kroku, jakie zależności występują między modułami oraz jak działania w UI mapują się na wywołania WebSocket i REST API. Dokument ten stanowi przewodnik dla deweloperów i projektantów, zapewniając spójność z `MVP.md` i `TECHNICAL_IMPLEMENTATION_PLAN.md`.

## 1) Widok główny i nawigacja
- Dashboard sesji: aktywna/poprzednie sesje, podstawowe metryki, status wykonania.
- Strumienie: market_data, indicators, signals — podgląd danych czasu rzeczywistego.
- Strategia: lista strategii, statusy (per symbol), aktywacja/dezaktywacja.
- Wyniki: agregacja metryk sesji, wyniki per symbol/strategia, PnL, win‑rate.
- **Strategy Builder (Canvas v2):** Wizualny konstruktor strategii, gdzie użytkownik przeciąga i łączy węzły (`DataSource`, `Indicator`, `Condition`, `Action`). Zapewnia natychmiastową informację zwrotną o poprawności struktury.

## 2) Kroki „start trading” (MVP)
1. Wybór symboli i trybu (backtest/live/paper).
2. Konfiguracja wskaźników: dodać RSI/EMA/PRICE dla wymaganych symboli i timeframe.
3. Wybór/utworzenie strategii (JSON Schema) lub (v2) złożenie warunków w Canvas.
4. Start sesji (idempotentnie): w UI wywołanie „Start” przekazuje `strategy_config` i listę symboli.
5. Podgląd strumieni i wyników: wskaźniki, sygnały, metryki.
6. Stop sesji: zamknięcie, finalizacja wyników i eksport.

## 3) Konfiguracja wskaźników (StreamingIndicatorEngine)
- Zakres: symbol, typ (`PRICE`, `RSI`, `EMA`, …), `timeframe`, `period`, opcjonalnie `scope` (multi‑tenant UI → izolacja).
- UI operacje:
  - Dodaj wskaźnik: POST `/indicators` (REST) lub komenda WS `add_indicator` (jeśli dostępna).
  - Lista wskaźników: `GET /indicators?scope=...&symbol=...&type=...` — filtrowanie dla widoków.
  - Kasuj wskaźnik: DELETE `/indicators/{key}` lub `/indicators/bulk`.
- **Noty:** W architekturze v2 wskaźniki są niezależnymi bytami, a ich wyniki mogą być współdzielone (cache) między strategiami, co jest kluczowe dla wydajności.

## 4) Budowa strategii
- MVP (JSON): pola progowe per grupa (signal_detection, risk_assessment, entry_conditions, emergency_exit). Walidacja: `docs/schema/strategy.schema.json` i `validate_strategy_config`.
- v2 DSL (plan):
  - Kompozycje: `AND/OR` (zagnieżdżanie), `duration` (utrzymanie przez X sekund), `sequence` (kolejność spełnienia).
  - Walidacja i semantyka czasowa w backendzie, podgląd w UI.
- UI operacje:
  - Walidacja/Upsert: POST `/strategies` z `validate_only` lub zapis i wczytanie do StrategyManager.
  - Podgląd statusu: `GET /strategies/status`, `GET /strategies/{name}`.

## 5) Sesje wykonywania
- Start: WS `session_start` lub REST `POST /sessions` z `session_type`, `strategy_config`, `idempotent`.
- Status: WS `execution_status`/`results_request:session_results` lub REST `GET /sessions/{id}`.
- Stop: WS `session_stop` lub REST `POST /sessions/{id}/stop`.
- Idempotencja: stabilny klucz (sha256) z configu strategii + lista symboli.

## 6) Wyniki i metryki
- Bieżące metryki: centralna agregacja w ExecutionController (sygnały, zlecenia, PnL).
- Eksport (MVP): `backtest/backtest_results/{session_id}/(session_summary|trades|signals).json`.
- UI operacje:
  - Wyniki sesji: WS `results_request:session_results` lub REST `GET /sessions/{id}/results`.
  - Wyniki symbolu/strategii: WS `results_request:(symbol|strategy)_results` lub REST `/results/(symbol|strategy)/...`.
  - Historia (nowe): `POST /results/history/merge` — łączenie wielu sesji do jednego widoku.

## 7) Mapowanie działań UI → WS/REST
- Lista strategii: WS `{type:"get_strategies"}` ↔ REST `GET /strategies`.
- Status strategii: WS `{type:"get_strategy_status", strategy_name}` ↔ REST `GET /strategies/{name}`.
- Walidacja/zapis strategii: REST `POST /strategies` (`validate_only` lub zapis).
- Wskaźniki CRUD: REST `/indicators(…|/bulk)`; filtrowanie po `scope`, `symbol`, `type`.
- Start sesji: WS `{type:"session_start", …}` ↔ REST `POST /sessions/start`.
- Stop sesji: WS `{type:"session_stop", session_id}` ↔ REST `POST /sessions/{id}/stop`.
- Wyniki sesji: WS `{type:"results_request", request_type:"session_results", session_id}` ↔ REST `GET /sessions/{id}/results`.
- Merge historii: REST `POST /results/history/merge`.

## 8) Szczegółowa specyfikacja Strategy Builder (Canvas)
- **Stany węzłów:** Każdy węzeł wizualizuje swój stan (`Idle`, `Computing`, `Error`, `Success`) zgodnie z `USER_INTERFACE_SPECIFICATION.md`, dając użytkownikowi natychmiastową informację zwrotną.
- **Logika połączeń:** UI zapobiega łączeniu niekompatybilnych portów (np. `Boolean` z `Numeric`) i tworzeniu cykli w grafie.
- **Walidacja progresywna:**
  - **Lokalna:** Błędy strukturalne (brak połączeń, cykle) są wykrywane natychmiast w przeglądarce.
  - **Serwerowa:** Logika strategii jest walidowana asynchronicznie przez backend (`POST /strategies` z `validate_only: true`), a błędy/ostrzeżenia są wyświetlane przy odpowiednich węzłach.
- **Warunki czasowe (`duration`, `sequence`):**
  - **Duration:** Użytkownik może skonfigurować warunek, który musi być spełniony przez określony czas (np. `RSI > 70 przez 30s`). W UI jest to reprezentowane jako specjalny parametr węzła `Condition`.
  - **Sequence:** Użytkownik może łączyć warunki w sekwencje, które muszą być spełnione w określonej kolejności. W UI jest to realizowane przez dedykowany węzeł `Sequence` z `CompositionNodes`.

## 8) Multi‑tenant (plan)
- `scope` jako prefiks izolujący (już w wskaźnikach). Docelowo: scope w strategiach, sesjach, wynikach (ścieżki `{base}/{scope}/{session}`), filtrowanie w API.
- UI: każda akcja wykonywana w aktywnym scope (np. użytkownik/sesja UI).

## 9) Wydajność
- Warstwa cache (rekomendacja): współdzielony cache wyników wskaźników i warunków; ograniczenie recalculations; backpressure i batchowanie na EventBridge.
- Testy E2E i load‑tests: scenariusze z wieloma strategiami/symbolami, kontrola opóźnień i zużycia pamięci. Zgodnie z `USER_INTERFACE_SPECIFICATION.md`.

## 10) Kroki kontrolne dla użytkownika
1.  **Konfiguracja Środowiska:** Użytkownik wybiera `scope` (jeśli multi-tenant jest aktywny) i weryfikuje połączenie z giełdą (API keys).
2.  **Zarządzanie Wskaźnikami:** W panelu wskaźników użytkownik tworzy instancje potrzebnych miar (np. `RSI(14)` dla `BTC_USDT`), które stają się dostępne w Strategy Builderze.
3.  **Budowa Strategii:** W Canvasie użytkownik przeciąga węzły, łączy je i konfiguruje parametry. UI na bieżąco waliduje strukturę.
4.  **Walidacja i Zapis:** Użytkownik klika "Validate on Server". Backend sprawdza logikę biznesową. Po uzyskaniu pozytywnej walidacji, strategia jest zapisywana.
5.  **Uruchomienie Sesji:** Użytkownik wybiera strategię, symbole i tryb (backtest/live), a następnie uruchamia sesję. System zapewnia idempotencję, aby uniknąć duplikatów.
6.  **Monitoring i Analiza:** Użytkownik obserwuje na żywo strumienie danych, sygnały i metryki PnL.
7.  **Zakończenie i Raport:** Po zatrzymaniu sesji, użytkownik analizuje zagregowane wyniki w panelu analitycznym i może je wyeksportować.

## 11) Błędy i spójność danych
- Spójna envelopa odpowiedzi (version, timestamp, id/request_id, session_id gdzie ma sens) — zgodna z `MVP.md` i `TECHNICAL_IMPLEMENTATION_PLAN.md`.
- Jednoznaczna taksonomia błędów (`validation_error`, `session_conflict`, `command_failed`, `network_error`, `auth_failed`) — tłumaczone na komunikaty UI w `USER_INTERFACE_SPECIFICATION.md`.
- Race conditions: blokada symboli w ExecutionController; izolacja per-scope dla multi-tenant (z `MVP.md`).
- **Recovery i Tryb Offline:**
  - **Błędy sieciowe:** UI automatycznie próbuje ponownie nawiązać połączenie WebSocket z logiką exponential backoff.
  - **Tryb Offline:** W przypadku utraty połączenia, UI przechodzi w tryb offline, informując o tym użytkownika. Zmiany w budowanej strategii są zapisywane lokalnie w `IndexedDB`. Po odzyskaniu połączenia, UI proponuje synchronizację z serwerem. Szczegóły w `USER_INTERFACE_SPECIFICATION.md`.

## 12) Testowanie i wdrażanie
- **Testy Jednostkowe:** Komponenty React testować z Jest, mockując API. Sprawdzić walidację, state transitions.
- **Testy E2E:** Cypress dla workflowów (np. stworzyć strategię, uruchomić backtest). Symulować błędy sieciowe.
- **Performance:** Lighthouse score >90, WS latency <200ms, obsługa 200+ węzłów w canvas bez spadku płynności.
- **Wdrażanie:** Docker build, env vars dla backend URLs. CI/CD z testami przed merge.
- **Monitoring:** Logi błędów do backend, metryki w Prometheus.

**Wnioski:** Ten przewodnik, w połączeniu z `USER_INTERFACE_SPECIFICATION.md`, tworzy kompletną bazę do implementacji interfejsu użytkownika, który jest spójny z architekturą backendu i celami biznesowymi projektu.
