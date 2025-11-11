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
- **CSRF:** Required (`X-CSRF-Token` header)
- Odpowiedź 200: `{ "type": "response", "status": "strategy_activated", "data": {"strategy_name": "...", "symbol": "..."} }`
- Błąd 400/409: `{ "type": "error", "error_code": "strategy_activation_failed", "error_message": "..." }`
- Błąd 403: CSRF token missing/invalid/expired

### POST /strategies/{name}/deactivate
- Body: `{ "symbol": "ALU_USDT" }`
- **CSRF:** Required (`X-CSRF-Token` header)
- Odpowiedź 200: `{ "type": "response", "status": "strategy_deactivated", ... }`
- Błąd 403: CSRF token missing/invalid/expired

### POST /sessions/start
- **CSRF:** Required (`X-CSRF-Token` header)
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
- Błąd 403: CSRF token missing/invalid/expired

### POST /sessions/stop
- **CSRF:** Required (`X-CSRF-Token` header)
- Body: `{ "session_id": "exec_..." }`
- Odpowiedź 200: `{ "type": "response", "status": "session_stopped", "data": {"session_id": "exec_..."} }`
- Błąd 403: CSRF token missing/invalid/expired

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
- **CSRF:** Required (`X-CSRF-Token` header)
- Walidacja i/lub publikacja (upsert) konfiguracji strategii.
- Body: { strategy_config, validate_only? }
- Zastosowania: walidacja w UI (bez zapisu) oraz zapis i odświeżenie StrategyManager.
- Błąd 403: CSRF token missing/invalid/expired

### DELETE /strategies/{name}
- **CSRF:** Required (`X-CSRF-Token` header)
- Usuwa konfigurację oraz rejestrację strategii (dezaktywacja na symbolach).
- Błąd 403: CSRF token missing/invalid/expired

### Indicators (CRUD + filtrowanie)
- GET /indicators/types - lista wspieranych typów.
- GET /indicators?scope=&symbol=&type= - lista instancji z filtrami.
- POST /indicators - **CSRF Required** - dodanie jednej instancji
- PUT /indicators/{key} - **CSRF Required** - aktualizacja
- DELETE /indicators/{key} - **CSRF Required** - usunięcie
- POST /indicators/bulk - **CSRF Required** - operacje bulk
- DELETE /indicators/bulk - **CSRF Required** - usunięcie bulk
- Zastosowania: kreator wskaźników w UI (per użytkownik/sesja przez scope).
- Błąd 403: CSRF token missing/invalid/expired (dla POST/PUT/DELETE)

### Wyniki z fallbackiem
- GET /results/session/{id} � je�eli brak sesji live, pr�ba odczytu acktest/backtest_results/{id}/session_summary.json; pole source: live|file.

### Bud�et (walidacja w /sessions/start)
- config.budget z global_cap i llocations (warto�ci USD lub np. "60%"), b��d udget_cap_exceeded gdy suma > cap.

### Wallet
- GET /wallet/balance � mock lub adapter (MEXC) z polem source.

### Order Management (New)
- GET /orders - lista wszystkich zleceń
- GET /orders/{order_id} - szczegóły konkretnego zlecenia
- POST /orders/cancel/{order_id} - **CSRF Required** - anulowanie zlecenia
- GET /positions - lista wszystkich pozycji
- GET /positions/{symbol} - pozycja dla konkretnego symbolu
- GET /trading/performance - podsumowanie wydajności tradingu
- Błąd 403: CSRF token missing/invalid/expired (dla POST)

### Risk Management (New)
- GET /risk/budget - podsumowanie budżetu
- GET /risk/budget/{strategy_name} - alokacja budżetu dla strategii
- POST /risk/budget/allocate - **CSRF Required** - alokacja budżetu dla strategii
- POST /risk/emergency-stop - **CSRF Required** - zatrzymanie awaryjne (zwolnienie budżetu)
- POST /risk/assess-position - **CSRF Required** - ocena ryzyka pozycji
- Błąd 403: CSRF token missing/invalid/expired (dla POST)

### Authentication (JWT)
- POST /api/v1/auth/login – Login z JWT, zwraca access_token i refresh_token
  - Body: `{"username": "admin", "password": "secret"}`
  - Response: `{"access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 3600, "user": {...}}`
  - Sets HttpOnly cookies: `access_token`, `refresh_token`
  - **CSRF:** Not required (initial login)
- POST /api/v1/auth/refresh – Odświeżenie tokenu
  - Requires: `refresh_token` cookie or header
  - Response: nowy `access_token` i `refresh_token`
  - **CSRF:** Not required (token refresh)
- POST /api/v1/auth/logout – Wylogowanie
  - Requires: valid `access_token`
  - Clears cookies and invalidates session
  - **CSRF:** Required

## CSRF Protection

All state-changing operations (POST, PUT, PATCH, DELETE) require valid CSRF tokens, except authentication endpoints (`/api/v1/auth/login`, `/api/v1/auth/refresh`) and test endpoints.

### Obtaining a CSRF Token

**Endpoint:** `GET /csrf-token`

**Description:** Generates a new CSRF token for the current session.

**Response (200 OK):**
```json
{
  "type": "response",
  "data": {
    "token": "your-csrf-token-here",
    "expires_in": 3600
  }
}
```

**Example:**
```bash
curl -X GET http://localhost:8080/csrf-token
```

### Using CSRF Tokens

Include the token in the `X-CSRF-Token` header for all state-changing requests:

**Example - Creating a Strategy:**
```bash
curl -X POST http://localhost:8080/api/strategies \
  -H "X-CSRF-Token: your-csrf-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "My Strategy",
    "s1_signal": {...},
    "z1_entry": {...},
    "o1_cancel": {...},
    "emergency_exit": {...}
  }'
```

**Example - Starting a Session:**
```bash
curl -X POST http://localhost:8080/sessions/start \
  -H "X-CSRF-Token: your-csrf-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "session_type": "backtest",
    "strategy_config": {"flash_pump_detection": ["ALU_USDT"]},
    "config": {"acceleration_factor": 10.0}
  }'
```

**Example - Activating a Strategy:**
```bash
curl -X POST http://localhost:8080/strategies/flash_pump_detection/activate \
  -H "X-CSRF-Token: your-csrf-token-here" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "ALU_USDT"}'
```

### CSRF-Protected Endpoints

**All POST/PUT/PATCH/DELETE endpoints require CSRF tokens EXCEPT:**
- `/api/v1/auth/login` - Initial login (no token available yet)
- `/api/v1/auth/refresh` - Token refresh (uses refresh token)
- `/test` - Test endpoint (development only)

**CSRF-protected endpoints include:**
- `POST /strategies` - Creating strategies
- `PUT /strategies/{strategy_id}` - Updating strategies
- `DELETE /strategies/{strategy_id}` - Deleting strategies
- `POST /strategies/{name}/activate` - Activating strategies
- `POST /strategies/{name}/deactivate` - Deactivating strategies
- `POST /sessions/start` - Starting sessions
- `POST /sessions/stop` - Stopping sessions
- `POST /indicators` - Creating indicators
- `PUT /indicators/{key}` - Updating indicators
- `DELETE /indicators/{key}` - Deleting indicators
- `POST /indicators/bulk` - Bulk indicator operations
- `DELETE /indicators/bulk` - Bulk indicator deletion
- `POST /orders/cancel/{order_id}` - Canceling orders
- `POST /risk/budget/allocate` - Budget allocation
- `POST /risk/emergency-stop` - Emergency stop
- `POST /risk/assess-position` - Position risk assessment
- `POST /api/v1/auth/logout` - Logout
- All other state-changing endpoints

### Error Responses

**Missing Token (403 Forbidden):**
```json
{
  "type": "error",
  "error_code": "csrf_missing",
  "error_message": "CSRF token required",
  "timestamp": "2025-11-11T10:00:00Z",
  "version": "1.0"
}
```

**Invalid Token (403 Forbidden):**
```json
{
  "type": "error",
  "error_code": "csrf_invalid",
  "error_message": "Invalid CSRF token",
  "timestamp": "2025-11-11T10:00:00Z",
  "version": "1.0"
}
```

**Expired Token (403 Forbidden):**
```json
{
  "type": "error",
  "error_code": "csrf_expired",
  "error_message": "CSRF token expired",
  "timestamp": "2025-11-11T10:00:00Z",
  "version": "1.0"
}
```

### Token Lifecycle

- **Validity:** 1 hour (3600 seconds)
- **Storage:** Tokens are stored in-memory on the server (cleared on server restart)
- **Renewal:** Fetch a new token when you receive `csrf_expired` error
- **Best Practice:**
  - Fetch a new token immediately after successful login
  - Store the token in memory (not localStorage for security)
  - Include the token in all state-changing requests
  - Handle `csrf_expired` errors by fetching a new token and retrying the request

### Security Considerations

1. **Token Storage:** Store CSRF tokens in memory only (e.g., React state, Vuex store). Never store in localStorage or sessionStorage as they are accessible to XSS attacks.

2. **Token Rotation:** Tokens expire after 1 hour. Implement automatic token refresh in your client application.

3. **Error Handling:** Always handle CSRF errors gracefully by fetching a new token and retrying the request once.

4. **Development vs Production:** CSRF protection is enabled in all environments. Use the `/csrf-token` endpoint to obtain tokens during development.

### Client Implementation Example (JavaScript)

```javascript
// Fetch CSRF token after login
async function fetchCsrfToken() {
  const response = await fetch('http://localhost:8080/csrf-token');
  const data = await response.json();
  return data.data.token;
}

// Make CSRF-protected request
async function makeProtectedRequest(csrfToken, endpoint, method, body) {
  try {
    const response = await fetch(`http://localhost:8080${endpoint}`, {
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken
      },
      body: JSON.stringify(body)
    });

    if (response.status === 403) {
      const error = await response.json();
      if (error.error_code === 'csrf_expired') {
        // Token expired, fetch new one and retry
        const newToken = await fetchCsrfToken();
        return makeProtectedRequest(newToken, endpoint, method, body);
      }
    }

    return response.json();
  } catch (error) {
    console.error('Request failed:', error);
    throw error;
  }
}

// Usage
const csrfToken = await fetchCsrfToken();
const result = await makeProtectedRequest(
  csrfToken,
  '/api/strategies',
  'POST',
  { strategy_name: 'My Strategy', ... }
);
```

### Strategy Management (4-Section)
- POST /api/strategies – Utworzenie strategii
  - **CSRF:** Required (`X-CSRF-Token` header)
  - Body: `{"strategy_name": "...", "s1_signal": {...}, "z1_entry": {...}, "o1_cancel": {...}, "emergency_exit": {...}}`
  - Validates all 4 sections required
  - Response: `{"strategy": {"id": "...", "strategy_name": "...", "created_at": "..."}}`
  - Błąd 403: CSRF token missing/invalid/expired
- GET /api/strategies – Lista strategii
  - Response: `{"strategies": [...]}`
- GET /api/strategies/{strategy_id} – Szczegóły strategii
  - Response: `{"strategy": {...}}`
- PUT /api/strategies/{strategy_id} – Aktualizacja strategii
  - **CSRF:** Required (`X-CSRF-Token` header)
  - Body: complete strategy config
  - Validates before updating
  - Błąd 403: CSRF token missing/invalid/expired
- DELETE /api/strategies/{strategy_id} – Usunięcie strategii
  - **CSRF:** Required (`X-CSRF-Token` header)
  - Response: `{"message": "Strategy deleted successfully", "strategy_id": "...", "strategy_name": "..."}`
  - Błąd 403: CSRF token missing/invalid/expired
- POST /api/strategies/validate – Walidacja konfiguracji
  - **CSRF:** Required (`X-CSRF-Token` header)
  - Body: strategy config
  - Response: `{"isValid": true/false, "errors": [...], "warnings": [...]}`
  - Błąd 403: CSRF token missing/invalid/expired

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
- POST /health/services/{service_name}/enable – **CSRF Required** – Włączenie serwisu
- POST /health/services/{service_name}/disable – **CSRF Required** – Wyłączenie serwisu
- POST /health/clear-cache – **CSRF Required** – Czyszczenie cache health endpoint
- GET /metrics – Metryki systemowe (telemetry)
  - Returns comprehensive system metrics
- GET /metrics/health – Metryki zdrowia
- GET /circuit-breakers – Status circuit breakerów
  - Returns status of all registered circuit breakers
- GET /alerts – Aktywne alerty
- POST /alerts/{alert_id}/resolve – **CSRF Required** – Rozwiązanie alertu
- Błąd 403: CSRF token missing/invalid/expired (dla wszystkich POST)

## Zastosowania UI (skr�cony przewodnik)
- Strategia: /strategies (validate_only/upsert), /strategies/status do tabeli w UI.
- Wska�niki: /indicators + filtry i bulk do zarz�dzania instancjami.
- Sesje: /sessions/start|stop|{id} z bud�etem i statusem.
- Wyniki: /results/session|strategy|symbol do dashboardu i drilldown�w.
- Wallet: /wallet/balance do kafla salda i pracy z cap.
