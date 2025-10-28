# WebSocket API — Specyfikacja (v1)

Niniejszy dokument odzwierciedla aktualne zachowanie serwera (`src/api/websocket_server.py`) po unifikacji envelope oraz poprawkach testów.

## Endpoint
- Domyślnie: `ws://localhost:8080` (port konfigurowalny)

## Envelope i Semantyka
- Request: `{ type, id?, ... }`
- Response (envelope wzbogacany automatycznie):
  - `version: "1.0"`, `timestamp: ISO-8601`, `id?: echo z żądania`
  - `type: "response" | "error" | "status" | "data" | "signal" | "alert"`
  - `error_code`, `error_message` (dla `error`)
  - `status` i `data` (dla `response`)

## Idempotencja i Konflikty
- `session_start` rozwiązuje konflikty symboli i (jeśli możliwe) ponownie wykorzystuje zgodną sesję.
- Docelowo stabilny klucz idempotencji: `(session_type, sorted(symbols), sha256(strategy_config))`.

## Kody błędów (wycinek)
`validation_error`, `missing_strategy_config`, `invalid_session_type`, `strategy_activation_failed`, `session_conflict`, `authentication_required`, `service_unavailable`, `routing_error`, `handler_error`, `command_failed`, `message_processing_error`.

## Strumienie i subskrypcje
- `subscribe`: `{ type: "subscribe", stream: "market_data"|"indicators"|"signals", params: {...}, id? }`
- Potwierdzenie: `response/subscribed` z `session_id` (jeśli dostępny)
- Serwer „seeduje” 5 wiadomości na start dla wygody klienta/testów (wszystkie zawierają `session_id`):
  - market_data: `{ type: "data", stream: "market_data", session_id, market_data: {...} }`
  - indicators: `{ type: "data", stream: "indicators", session_id, indicators: [...], data: {...} }`
  - signals: `{ type: "signal", session_id, signal: {...} }`

## Zarządzanie sesjami
- `session_start`: `{ type, session_type: "backtest"|"live"|"paper", strategy_config: {strategy: [symbols]}, config?, id? }`
  - Sukces: `{ type: "response", status: "session_started", session_id, session_type, symbols, ... }`
  - Błędy: `invalid_session_type | missing_strategy_config | session_conflict | strategy_activation_failed`
- `session_stop`: `{ type: "session_stop", session_id }` → `response/session_stopped`
- `session_status`: `{ type: "session_status", session_id? }` → `response/session_status` lub `response/no_active_session`

## Strategy Management
- `get_strategies` → `response/strategies_list`
- `activate_strategy` → `response/strategy_activated` (błąd: `strategy_activation_failed`)
- `deactivate_strategy` → `response/strategy_deactivated`
- `get_strategy_status` → `response/strategy_status` lub `response/all_strategies_status`

## Results API (WS)
- `results_request`:
  - `session_results` → `response/results` z `session_id` i znormalizowanymi metrykami
  - `symbol_results` → `response/results` (symbol + szczegóły)
  - `strategy_results` → `response/results` (strategy + szczegóły)

Uwaga: metryki sesji normalizowane konserwatywnie do sum per-symbol; docelowo będzie użyty jeden autorytatywny licznik w ExecutionController.


## Dodatki (MVP_v2)

- validate_strategy_config � response/strategy_validation (valid, errors, warnings)

- upsert_strategy � response/strategy_upserted (b��dy: validation_error, command_failed)


Uwaga: metryki sesji normalizowane s� wg aktywnych symboli bie��cej sesji (priorytet: session_strategy_map, nast�pnie symbols ze statusu) dla sp�jno�ci z sum� wynik�w per-symbol. W dev, je�li token nie ma formatu JWT (header.payload.signature), jest akceptowany jako prosty token testowy.

## Dodatki (v1+)

### Strategy Lifecycle (nowe akcje)
- alidate_strategy_config � walidacja konfiguracji strategii; odpowied�: strategy_validation (alid, errors, warnings).
- upsert_strategy � zapis strategii do config/strategies/{name}.json i od�wie�enie StrategyManager; odpowied�: strategy_upserted.
- get_strategies / get_strategy_status � lista/status strategii.
- ctivate_strategy / deactivate_strategy � aktywacja/dezaktywacja strategii dla symbolu.

### Sessions (idempotencja i bud�et)
- session_start � rozwi�zywanie konflikt�w, idempotency key: (mode, sorted(symbols), sha256(strategy_config)).
- Walidacja bud�etu analogicznie do REST (global_cap, llocations), w przypadku naruszenia: error z kodem udget_cap_exceeded.

### Data Collection
- collection_start � uruchamia zrzut danych w strukturze sesji (data/session_*), odpowied�: collection_started z collection_id.
- collection_stop / collection_status � zarz�dzanie kolekcj� danych.

### Results (sp�jno�� envelope)
- esults_request � session_results|symbol_results|strategy_results;
  - Metryki sesji centralizowane w ExecutionController (sp�jne REST/WS).

## Zastosowania UI
- Walidacja/publikacja strategii bezpo�rednio z edytora (canvas) � alidate_strategy_config, upsert_strategy.
- Utrzymanie listy i status�w (WS lub REST) � szybkie od�wie�anie w UI.
- Start sesji (backtest/live/paper) z cap bud�etu � session_start; monitorowanie � session_status.
- Podgl�d strumieni: market_data, indicators, signals (seed 5 wiadomo�ci na subskrypcj�).
- Kolekcja danych do p�niejszego backtestu � collection_start/stop/status.
