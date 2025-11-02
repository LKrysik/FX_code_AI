# REST API — Specyfikacja (MVP Lite, FastAPI)

Cel: uproszczony interfejs HTTP uzupełniający WebSocket API, spójny semantycznie (wspólna envelope), zaimplementowany w FastAPI.

Wspólna Envelope:
- Każda odpowiedź zawiera: `version: "1.0"`, `timestamp: ISO-8601`, `type: "response" | "error"`, opcjonalnie `id` (korelacja klienta), `error_code`, `error_message`.

## Endpoints

### GET /health
- Opis: status komponentów backendu.
- Odpowiedź 200:
```
{
  "type": "response",
  "status": "ok",
  "version": "1.0",
  "timestamp": "2025-09-10T10:00:00Z",
  "data": {
    "websocket_server": {"healthy": true},
    "connection_manager": {"healthy": true},
    "auth_handler": {"healthy": true},
    "subscription_manager": {"healthy": true},
    "message_router": {"healthy": true}
  }
}
```

### GET /strategies
- Opis: lista dostępnych strategii i ich podstawowe atrybuty.
- Odpowiedź 200:
```
{
  "type": "response",
  "status": "strategies_list",
  "version": "1.0",
  "timestamp": "...",
  "data": {
    "strategies": [
      {"strategy_name": "flash_pump_detection", "enabled": true, "current_state": "inactive"}
    ]
  }
}
```

### GET /strategies/{name}
- Opis: szczegółowy status danej strategii (opcjonalnie ?symbol=ALU_USDT).
- Odpowiedź 200:
```
{
  "type": "response",
  "status": "strategy_status",
  "version": "1.0",
  "timestamp": "...",
  "data": {
    "strategy_data": {"strategy_name": "flash_pump_detection", "current_state": "monitoring", "symbol": "ALU_USDT"}
  }
}
```
- Błąd 404: `{ "type": "error", "error_code": "strategy_not_found", ... }`

### POST /strategies/{name}/activate
- Body: `{ "symbol": "ALU_USDT" }`
- Odpowiedź 200: `{ "type": "response", "status": "strategy_activated", "data": {"strategy_name": "...", "symbol": "..."} }`
- Błąd 400/409: `{ "type": "error", "error_code": "strategy_activation_failed", "error_message": "..." }`

### POST /strategies/{name}/deactivate
- Body: `{ "symbol": "ALU_USDT" }`
- Odpowiedź 200: `{ "type": "response", "status": "strategy_deactivated", ... }`

### POST /sessions/start
- Body:
```
{
  "session_type": "backtest"|"live"|"paper",
  "strategy_config": {"flash_pump_detection": ["ALU_USDT", "BTC_USDT"]},
  "config": {"acceleration_factor": 10.0},
  "idempotent": true
}
```
- Odpowiedź 200:
```
{
  "type": "response",
  "status": "session_started",
  "version": "1.0",
  "timestamp": "...",
  "data": {
    "session_id": "exec_2025...",
    "session_type": "backtest",
    "symbols": ["ALU_USDT", "BTC_USDT"]
  }
}
```
- Błąd 400/409: `invalid_session_type | missing_strategy_config | session_conflict | strategy_activation_failed`

### POST /sessions/stop
- Body: `{ "session_id": "exec_..." }`
- Odpowiedź 200: `{ "type": "response", "status": "session_stopped", "data": {"session_id": "exec_..."} }`

### GET /sessions/{id}
- Odpowiedź 200:
```
{
  "type": "response",
  "status": "session_status",
  "version": "1.0",
  "timestamp": "...",
  "data": {
    "session_id": "exec_...",
    "mode": "backtest",
    "status": "running",
    "symbols": ["ALU_USDT"],
    "metrics": {"signals_detected": 2, "orders_placed": 1, ...}
  }
}
```

## Zasady spójności REST/WS
- Wspólna envelope, pola i kody błędów.
- Te same nazwy pól: `session_id`, `strategy_name`, `symbols`, `status`.
- Spójne semantyki dla `session_start/stop/status` i Strategy Management.

## Uwagi implementacyjne (FastAPI)
- Odpowiedzi zawijane przez `ensure_envelope` (version/timestamp zawsze obecne).
- Przygotowany szkielet autoryzacji (w MVP dev tokeny akceptowane w WS; REST może przyjąć `Authorization: Bearer <token>` w przyszłości).

## Dodatkowe endpointy i zachowania (v1+)

### GET /strategies/status
- Zwraca wzbogacony status wszystkich strategii z polami telemetry: ctive_symbols_count, last_event, last_state_change.

### POST /strategies
- Walidacja i/lub publikacja (upsert) konfiguracji strategii.
- Body: { strategy_config, validate_only? }
- Zastosowania: walidacja w UI (bez zapisu) oraz zapis i od�wie�enie StrategyManager.

### DELETE /strategies/{name}
- Usuwa konfiguracj� oraz rejestracj� strategii (dezaktywacja na symbolach).

### Indicators (CRUD + filtrowanie)
- GET /indicators/types � lista wspieranych typ�w.
- GET /indicators?scope=&symbol=&type= � lista instancji z filtrami.
- POST /indicators � dodanie jednej instancji; PUT /indicators/{key} � aktualizacja; DELETE /indicators/{key} � usuni�cie.
- Bulk: POST /indicators/bulk, DELETE /indicators/bulk.
- Zastosowania: kreator wska�nik�w w UI (per u�ytkownik/sesja przez scope).

### Wyniki z fallbackiem
- GET /results/session/{id} � je�eli brak sesji live, pr�ba odczytu acktest/backtest_results/{id}/session_summary.json; pole source: live|file.

### Bud�et (walidacja w /sessions/start)
- config.budget z global_cap i llocations (warto�ci USD lub np. "60%"), b��d udget_cap_exceeded gdy suma > cap.

### Wallet
- GET /wallet/balance � mock lub adapter (MEXC) z polem source.

### Order Management (New)
- GET /orders � lista wszystkich zleceń
- GET /orders/{order_id} � szczegóły konkretnego zlecenia
- POST /orders/cancel/{order_id} � anulowanie zlecenia
- GET /positions � lista wszystkich pozycji
- GET /positions/{symbol} � pozycja dla konkretnego symbolu
- GET /trading/performance � podsumowanie wydajności tradingu

### Risk Management (New)
- GET /risk/budget � podsumowanie budżetu
- GET /risk/budget/{strategy_name} � alokacja budżetu dla strategii
- POST /risk/budget/allocate � alokacja budżetu dla strategii
- POST /risk/emergency-stop � zatrzymanie awaryjne (zwolnienie budżetu)
- POST /risk/assess-position � ocena ryzyka pozycji

### Authentication (JWT)
- POST /api/v1/auth/login – Login z JWT, zwraca access_token i refresh_token
  - Body: `{"username": "admin", "password": "secret"}`
  - Response: `{"access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 3600, "user": {...}}`
  - Sets HttpOnly cookies: `access_token`, `refresh_token`
- POST /api/v1/auth/refresh – Odświeżenie tokenu
  - Requires: `refresh_token` cookie or header
  - Response: nowy `access_token` i `refresh_token`
- POST /api/v1/auth/logout – Wylogowanie
  - Requires: valid `access_token`
  - Clears cookies and invalidates session
- GET /csrf-token – Generowanie tokenu CSRF
  - Response: `{"token": "..."}`
  - Token expires in 1 hour

### Strategy Management (4-Section)
- POST /api/strategies – Utworzenie strategii
  - Body: `{"strategy_name": "...", "s1_signal": {...}, "z1_entry": {...}, "o1_cancel": {...}, "emergency_exit": {...}}`
  - Validates all 4 sections required
  - Response: `{"strategy": {"id": "...", "strategy_name": "...", "created_at": "..."}}`
- GET /api/strategies – Lista strategii
  - Response: `{"strategies": [...]}`
- GET /api/strategies/{strategy_id} – Szczegóły strategii
  - Response: `{"strategy": {...}}`
- PUT /api/strategies/{strategy_id} – Aktualizacja strategii
  - Body: complete strategy config
  - Validates before updating
- DELETE /api/strategies/{strategy_id} – Usunięcie strategii
  - Response: `{"message": "Strategy deleted successfully", "strategy_id": "...", "strategy_name": "..."}`
- POST /api/strategies/validate – Walidacja konfiguracji
  - Body: strategy config
  - Response: `{"isValid": true/false, "errors": [...], "warnings": [...]}`

### Health & Monitoring
- GET /health – Ultra-fast liveness probe (<10ms)
  - Response: `{"status": "healthy", "timestamp": "...", "uptime": 12345, "version": "1.0"}`
- GET /health/detailed – Comprehensive health check
  - Returns: overall status, component health, degradation info, circuit breakers, telemetry
  - Response includes: `status`, `degradation_info`, `components`, `health_checks`, `active_alerts`, `circuit_breakers`
- GET /health/status – Detailed health monitoring status
  - Returns: health checks, active alerts, timestamps
- GET /health/checks/{check_name} – Szczegóły konkretnego health checku
- GET /health/services – Lista zarejestrowanych serwisów
- GET /health/services/{service_name} – Status konkretnego serwisu
- POST /health/services/{service_name}/enable – Włączenie serwisu
- POST /health/services/{service_name}/disable – Wyłączenie serwisu
- POST /health/clear-cache – Czyszczenie cache health endpoint
- GET /metrics – Metryki systemowe (telemetry)
  - Returns comprehensive system metrics
- GET /metrics/health – Metryki zdrowia
- GET /circuit-breakers – Status circuit breakerów
  - Returns status of all registered circuit breakers
- GET /alerts – Aktywne alerty
- POST /alerts/{alert_id}/resolve – Rozwiązanie alertu

## Zastosowania UI (skr�cony przewodnik)
- Strategia: /strategies (validate_only/upsert), /strategies/status do tabeli w UI.
- Wska�niki: /indicators + filtry i bulk do zarz�dzania instancjami.
- Sesje: /sessions/start|stop|{id} z bud�etem i statusem.
- Wyniki: /results/session|strategy|symbol do dashboardu i drilldown�w.
- Wallet: /wallet/balance do kafla salda i pracy z cap.
