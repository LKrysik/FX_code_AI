# WebSocket API â€” Specyfikacja (v1)

Niniejszy dokument odzwierciedla aktualne zachowanie serwera (`src/api/websocket_server.py`) po unifikacji envelope oraz poprawkach testÃ³w.

## Endpoint
- DomyÅ›lnie: `ws://localhost:8080` (port konfigurowalny)

## Envelope i Semantyka
- Request: `{ type, id?, ... }`
- Response (envelope wzbogacany automatycznie):
  - `version: "1.0"`, `timestamp: ISO-8601`, `id?: echo z Å¼Ä…dania`
  - `type: "response" | "error" | "status" | "data" | "signal" | "alert"`
  - `error_code`, `error_message` (dla `error`)
  - `status` i `data` (dla `response`)

## Idempotencja i Konflikty
- `session_start` rozwiÄ…zuje konflikty symboli i (jeÅ›li moÅ¼liwe) ponownie wykorzystuje zgodnÄ… sesjÄ™.
- Docelowo stabilny klucz idempotencji: `(session_type, sorted(symbols), sha256(strategy_config))`.

## Kody bÅ‚Ä™dÃ³w (wycinek)
`validation_error`, `missing_strategy_config`, `invalid_session_type`, `strategy_activation_failed`, `session_conflict`, `authentication_required`, `service_unavailable`, `routing_error`, `handler_error`, `command_failed`, `message_processing_error`.

## Strumienie i subskrypcje
- `subscribe`: `{ type: "subscribe", stream: "market_data"|"indicators"|"signals", params: {...}, id? }`
- Potwierdzenie: `response/subscribed` z `session_id` (jeÅ›li dostÄ™pny)
- Serwer â€seedujeâ€ 5 wiadomoÅ›ci na start dla wygody klienta/testÃ³w (wszystkie zawierajÄ… `session_id`):
  - market_data: `{ type: "data", stream: "market_data", session_id, market_data: {...} }`
  - indicators: `{ type: "data", stream: "indicators", session_id, indicators: [...], data: {...} }`
  - signals: `{ type: "signal", session_id, signal: {...} }`

## ZarzÄ…dzanie sesjami
- `session_start`: `{ type, session_type: "backtest"|"live"|"paper", strategy_config: {strategy: [symbols]}, config?, id? }`
  - Sukces: `{ type: "response", status: "session_started", session_id, session_type, symbols, ... }`
  - BÅ‚Ä™dy: `invalid_session_type | missing_strategy_config | session_conflict | strategy_activation_failed`
- `session_stop`: `{ type: "session_stop", session_id }` â†’ `response/session_stopped`
- `session_status`: `{ type: "session_status", session_id? }` â†’ `response/session_status` lub `response/no_active_session`

## Strategy Management
- `get_strategies` â†’ `response/strategies_list`
- `activate_strategy` â†’ `response/strategy_activated` (bÅ‚Ä…d: `strategy_activation_failed`)
- `deactivate_strategy` â†’ `response/strategy_deactivated`
- `get_strategy_status` â†’ `response/strategy_status` lub `response/all_strategies_status`

## Results API (WS)
- `results_request`:
  - `session_results` â†’ `response/results` z `session_id` i znormalizowanymi metrykami
  - `symbol_results` â†’ `response/results` (symbol + szczegÃ³Å‚y)
  - `strategy_results` â†’ `response/results` (strategy + szczegÃ³Å‚y)

Uwaga: metryki sesji normalizowane konserwatywnie do sum per-symbol; docelowo bÄ™dzie uÅ¼yty jeden autorytatywny licznik w ExecutionController.


## Dodatki (MVP_v2)

- validate_strategy_config › response/strategy_validation (valid, errors, warnings)

- upsert_strategy › response/strategy_upserted (b³êdy: validation_error, command_failed)


Uwaga: metryki sesji normalizowane s¹ wg aktywnych symboli bie¿¹cej sesji (priorytet: session_strategy_map, nastêpnie symbols ze statusu) dla spójnoœci z sum¹ wyników per-symbol. W dev, jeœli token nie ma formatu JWT (header.payload.signature), jest akceptowany jako prosty token testowy.

## Dodatki (v1+)

### Strategy Lifecycle (nowe akcje)
- alidate_strategy_config — walidacja konfiguracji strategii; odpowiedŸ: strategy_validation (alid, errors, warnings).
- upsert_strategy — zapis strategii do config/strategies/{name}.json i odœwie¿enie StrategyManager; odpowiedŸ: strategy_upserted.
- get_strategies / get_strategy_status — lista/status strategii.
- ctivate_strategy / deactivate_strategy — aktywacja/dezaktywacja strategii dla symbolu.

### Sessions (idempotencja i bud¿et)
- session_start — rozwi¹zywanie konfliktów, idempotency key: (mode, sorted(symbols), sha256(strategy_config)).
- Walidacja bud¿etu analogicznie do REST (global_cap, llocations), w przypadku naruszenia: error z kodem udget_cap_exceeded.

### Data Collection
- collection_start — uruchamia zrzut danych w strukturze sesji (data/session_*), odpowiedŸ: collection_started z collection_id.
- collection_stop / collection_status — zarz¹dzanie kolekcj¹ danych.

### Results (spójnoœæ envelope)
- esults_request — session_results|symbol_results|strategy_results;
  - Metryki sesji centralizowane w ExecutionController (spójne REST/WS).

## Zastosowania UI
- Walidacja/publikacja strategii bezpoœrednio z edytora (canvas) — alidate_strategy_config, upsert_strategy.
- Utrzymanie listy i statusów (WS lub REST) — szybkie odœwie¿anie w UI.
- Start sesji (backtest/live/paper) z cap bud¿etu — session_start; monitorowanie — session_status.
- Podgl¹d strumieni: market_data, indicators, signals (seed 5 wiadomoœci na subskrypcjê).
- Kolekcja danych do póŸniejszego backtestu — collection_start/stop/status.
