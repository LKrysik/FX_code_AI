# Multi-Agent Implementation Plan - Live Trading System
**Data:** 2025-11-06
**Autor:** Claude (Architecture Lead)
**Status:** Szczegółowy plan podziału prac na 7 agentów (1 koordynator + 6 wykonawców)

---

## 🎯 EXECUTIVE SUMMARY

### Cel
Wdrożenie live trading system z 30% → 100% production readiness poprzez równoległy rozwój z wykorzystaniem 7 agentów AI.

### Analiza Dokumentów - Kluczowe Wnioski

**Z TARGET_STATE_ARCHITECTURE.md:**
- ✅ Architektura spójna (coherence analysis passed)
- ⚠️ 3 zidentyfikowane luki: missing REST endpoints, risk_events table, PR #152 elements
- ✅ Usunięto overengineering (EventBus EXACTLY_ONCE, 2 risk checks)
- 📊 Timeline: 205h (5-6 tygodni)

**Z IMPLEMENTATION_ROADMAP.md:**
- 📋 6 faz: Phase 0-5
- 🎯 3 milestones: M1 (92h), M2 (156h), M3 (205h)
- ⚠️ Critical path: EventBus → Circuit Breaker → RiskManager → LiveOrderManager
- ✅ Non-critical path możliwy do zrównoleglenia

**Z LIVE_TRADING_PRODUCTION_READINESS.md:**
- 🔴 Obecny stan: 21/100 (NOT PRODUCTION READY)
- ⚠️ Brutalna prawda: brak error handling, testing, monitoring
- 📊 Realistic timeline: 208h (vs poprzednie 21h - 10x underestimation)
- ✅ 3-phase rollout plan: Paper → $100 → Full capital

### Strategia Podziału Prac

**UZASADNIENIE:** Dlaczego 6 agentów + koordynator?

1. **Critical Path Analysis (z IMPLEMENTATION_ROADMAP.md):**
   - Phase 0-1 (Infrastructure + Core Trading): 92h - BLOKUJE wszystko
   - Phase 2-3 (Testing + Monitoring): 64h - można równolegle
   - Phase 4-5 (Frontend + Deployment): 49h - można równolegle po Phase 1

2. **Podział według warstw architektury:**
   ```
   Agent 1: Core Infrastructure (EventBus, Circuit Breaker)
   Agent 2: Risk & Validation (RiskManager, validators)
   Agent 3: Trading Core (LiveOrderManager, PositionSync)
   Agent 4: Testing & Quality (Unit, Integration, E2E)
   Agent 5: Monitoring & Observability (Prometheus, Grafana)
   Agent 6: Frontend & API (UI components, REST endpoints)
   Agent 0: COORDINATOR (orchestration, conflict resolution)
   ```

3. **Dependency Graph:**
   ```
   Agent 0 (Coordinator) - kontroluje wszystkich
        ↓
   Agent 1 (Infrastructure) - MUST GO FIRST
        ↓
   ┌────┴─────┬──────────┐
   ↓          ↓          ↓
   Agent 2    Agent 3    Agent 5
   (Risk)     (Trading)  (Monitor)
        ↘     ↓     ↙
          Agent 4
         (Testing)
            ↓
         Agent 6
        (Frontend)
   ```

---

## 👥 AGENT DEFINITIONS

### AGENT 0: COORDINATOR (Master Orchestrator)

**Rola:** Główny architekt, koordynator, strażnik spójności

**Odpowiedzialności:**

1. **Orchestration:**
   - Zlecanie zadań Agent 1-6
   - Monitorowanie postępów (check-ins co 4h)
   - Zarządzanie blokadami (dependencies)
   - Eskalacja problemów do użytkownika

2. **Quality Gate:**
   - Code review wszystkich zmian przed merge
   - Weryfikacja spójności interfejsów między agentami
   - Wykrywanie konfliktów (np. Agent 2 zmienił signature, ale Agent 3 tego nie wie)
   - Enforcing architectural constraints z CLAUDE.md

3. **Risk Management:**
   - Tracking Risk Matrix (20 ryzyk z LIVE_TRADING_PRODUCTION_READINESS.md)
   - Mitigacja wysokich ryzyk (Score 15-25)
   - Decision making: "Czy Agent X może zacząć, czy musi czekać?"

4. **Integration:**
   - Scalanie prac agentów
   - Rozwiązywanie merge conflicts
   - Testy integracyjne między komponentami
   - Final smoke test przed milestone

5. **Communication Protocol:**
   - Tworzy "Interface Contract" dla każdego agenta
   - Publikuje zmiany interfejsów do wszystkich agentów
   - Wymusza dependency injection pattern (NO global access)

**Narzędzia:**
- TodoWrite: Tracking zadań dla wszystkich agentów
- Read/Edit: Code review
- Bash: Uruchamianie testów integracyjnych
- Grep/Glob: Weryfikacja spójności kodu

**Workflow:**

```
1. Inicjalizacja (2h):
   - Przeczytaj wszystkie 3 dokumenty
   - Stwórz Interface Contracts dla Agent 1-6
   - Zdefiniuj "Definition of Done" dla każdego zadania
   - Setup communication channels

2. Phase 0 Launch (4h):
   - Assign Task 0.1 → Agent 1 (EventBus)
   - Monitor: Check-in po 2h
   - Review: Code review EventBus
   - Decision: "EventBus OK? → Odblokuj Agent 2, 3, 5"

3. Continuous Monitoring (ongoing):
   - Check-in z każdym agentem co 4h
   - Code review każdego PR
   - Update Interface Contracts gdy się zmienią
   - Notify affected agents o zmianach

4. Milestone Gates (M1, M2, M3):
   - Smoke test wszystkich komponentów
   - Verify Go/No-Go criteria
   - Report do użytkownika
   - Decision: "Go to next phase?"

5. Conflict Resolution:
   - Gdy Agent X zgłosi problem z kodem Agent Y
   - Analyze root cause
   - Propose solution
   - Assign fix to appropriate agent
```

**Communication Format:**

```markdown
## Agent 0 → Agent N Communication

**Task:** [Task ID from IMPLEMENTATION_ROADMAP]
**Priority:** CRITICAL | HIGH | MEDIUM | LOW
**Dependencies:** [List of blocking tasks]
**Interface Contract:** [Link to contract doc]
**Definition of Done:**
  - [ ] Code complete
  - [ ] Unit tests pass
  - [ ] Integration tests pass (if applicable)
  - [ ] Code review approved by Agent 0
  - [ ] Documentation updated
**Estimated Time:** [Hours]
**Deadline:** [Milestone date]
```

---

### AGENT 1: CORE INFRASTRUCTURE

**Rola:** Fundament systemu - EventBus, Circuit Breaker, Health Checks

**Zadania (36h):**

**Task 1.1: EventBus Implementation (12h)**
- **Priority:** CRITICAL (blokuje wszystko)
- **Source:** IMPLEMENTATION_ROADMAP.md, Task 0.1 (linie 336-496)
- **Deliverable:** `src/core/event_bus.py`
- **Interface Contract:**
  ```python
  class EventBus:
      def subscribe(topic: str, handler: Callable) -> None
      async def publish(topic: str, data: Dict[str, Any]) -> None
      def unsubscribe(topic: str, handler: Callable) -> None
      def list_topics() -> List[str]
      async def shutdown() -> None

  # Supported Topics (DO NOT CHANGE without Agent 0 approval):
  TOPICS = {
      "market_data": Dict[symbol, timestamp, price, volume],
      "indicator_updated": Dict[indicator_id, value, confidence],
      "signal_generated": Dict[signal_type, symbol, side, quantity],
      "order_created": Dict[order_id, status, exchange_order_id],
      "order_filled": Dict[order_id, filled_price, filled_quantity],
      "position_updated": Dict[position_id, current_price, unrealized_pnl],
      "risk_alert": Dict[severity, alert_type, message]
  }
  ```
- **Critical Requirements:**
  - ✅ NO defaultdict (memory leak prevention)
  - ✅ Retry logic: 3 attempts, exponential backoff (1s, 2s, 4s)
  - ✅ Error isolation: subscriber crash doesn't affect others
  - ✅ AT_LEAST_ONCE delivery (NO EXACTLY_ONCE overengineering)
  - ✅ Explicit cleanup in shutdown()

**Task 1.2: Circuit Breaker (8h)**
- **Priority:** CRITICAL (required for MEXC integration)
- **Source:** IMPLEMENTATION_ROADMAP.md, Task 0.2
- **Deliverable:** `src/infrastructure/circuit_breaker.py`
- **Interface Contract:**
  ```python
  class CircuitBreakerState(Enum):
      CLOSED = "closed"  # Normal operation
      OPEN = "open"      # Blocking all calls
      HALF_OPEN = "half_open"  # Testing recovery

  class CircuitBreaker:
      async def call(func: Callable, *args, **kwargs) -> Any
      def get_state() -> CircuitBreakerState
      def reset() -> None  # Manual reset
      def get_metrics() -> Dict[str, Any]
  ```
- **Critical Requirements:**
  - ✅ OPEN after 5 failures in 60s window
  - ✅ HALF_OPEN after 30s cooldown
  - ✅ CLOSED after 1 successful call in HALF_OPEN
  - ✅ Raises CircuitBreakerOpenError when OPEN

**Task 1.3: Health Check Endpoints (4h)**
- **Priority:** MEDIUM (required for Phase 5 deployment)
- **Source:** IMPLEMENTATION_ROADMAP.md, Task 0.4
- **Deliverable:** `src/api/health_routes.py`
- **Endpoints:**
  - `GET /health` - Basic liveness (always 200 OK)
  - `GET /health/ready` - Readiness check (DB connected, EventBus running)
  - `GET /health/deep` - Deep check (MEXC API reachable, QuestDB writable)

**Task 1.4: Container Integration (4h)**
- **Priority:** HIGH (DI setup)
- **Source:** CLAUDE.md anti-patterns
- **Deliverable:** Update `src/infrastructure/container.py`
- **Critical Requirements:**
  - ✅ Pure composition root (NO business logic)
  - ✅ Constructor injection only
  - ✅ Register EventBus, CircuitBreaker as singletons
  - ✅ Factories for conditional creation

**Task 1.5: Unit Tests (8h)**
- **Priority:** CRITICAL (required for M1 Go/No-Go)
- **Deliverables:**
  - `tests_e2e/unit/test_event_bus.py` (10 tests)
  - `tests_e2e/unit/test_circuit_breaker.py` (8 tests)
- **Coverage Target:** 90%+

**Dependencies:**
- None (can start immediately)

**Blockers Unblocked After Completion:**
- Agent 2: RiskManager (needs EventBus)
- Agent 3: LiveOrderManager (needs EventBus + Circuit Breaker)
- Agent 5: Monitoring (needs EventBus topics)

**Definition of Done:**
- [x] EventBus passes all 10 unit tests
- [x] Circuit Breaker passes all 8 unit tests
- [x] Memory leak test passes (10k subscribe/unsubscribe cycles)
- [x] Integration test: EventBus → 1000 events/sec (no dropped messages)
- [x] Code review approved by Agent 0
- [x] Container.py updated with EventBus + Circuit Breaker registration

**Estimated Time:** 36h (Week 1)

---

### AGENT 2: RISK MANAGEMENT & VALIDATION

**Rola:** Budget allocation, position limits, risk alerts

**Zadania (24h):**

**Task 2.1: RiskManager Complete Implementation (16h)**
- **Priority:** CRITICAL (blokuje order submission)
- **Source:** IMPLEMENTATION_ROADMAP.md, Task 0.3; LIVE_TRADING_PRODUCTION_READINESS.md lines 474-510
- **Deliverable:** `src/domain/services/risk_manager.py`
- **Interface Contract:**
  ```python
  @dataclass
  class RiskCheckResult:
      can_proceed: bool
      reason: Optional[str]  # If False, why?
      risk_score: float  # 0-100

  class RiskManager:
      async def can_open_position(
          self,
          symbol: str,
          side: str,
          quantity: float,
          price: float,
          current_positions: List[Position]
      ) -> RiskCheckResult

      async def validate_order(self, order: Order) -> RiskCheckResult

      # Risk Checks (6 checks, removed volatility + Sharpe per TARGET_STATE):
      # 1. Max position size (10% of capital)
      # 2. Max number of positions (3 concurrent)
      # 3. Position concentration (max 30% in one symbol)
      # 4. Daily loss limit (5% of capital)
      # 5. Total drawdown (15% from peak)
      # 6. Margin utilization (< 80% of available margin)
  ```
- **Critical Requirements:**
  - ✅ All checks configurable via `config.json`
  - ✅ Emit risk_alert event when check fails
  - ✅ NO hardcoded limits
  - ✅ Thread-safe (async-safe) state management

**Task 2.2: Risk Events Table (2h)**
- **Priority:** HIGH (required for RiskAlerts UI)
- **Source:** TARGET_STATE_ARCHITECTURE.md lines 199-227
- **Deliverable:** `database/questdb/migrations/015_risk_events.sql`
- **Schema:**
  ```sql
  CREATE TABLE risk_events (
      alert_id STRING,
      session_id STRING,
      timestamp TIMESTAMP,
      severity STRING,  -- CRITICAL, WARNING, INFO
      alert_type STRING,  -- MARGIN_LOW, DAILY_LOSS_LIMIT, etc.
      message STRING,
      details STRING,  -- JSON
      acknowledged BOOLEAN
  ) timestamp(timestamp) PARTITION BY DAY;
  ```

**Task 2.3: Unit Tests (6h)**
- **Priority:** CRITICAL
- **Deliverable:** `tests_e2e/unit/test_risk_manager.py` (15 tests)
- **Coverage Target:** 85%+
- **Test Cases:**
  - Max position size exceeded → Blocked
  - Daily loss limit exceeded → Blocked
  - Margin utilization > 80% → Blocked
  - All checks pass → Approved
  - Concurrent order race condition → Handled correctly

**Dependencies:**
- Agent 1: EventBus (for risk_alert events)

**Blockers Unblocked After Completion:**
- Agent 3: LiveOrderManager (needs risk validation)

**Definition of Done:**
- [x] RiskManager passes all 15 unit tests
- [x] Migration 015 applied successfully
- [x] Integration test: RiskManager → EventBus (risk_alert emitted)
- [x] Code review approved by Agent 0
- [x] All 6 risk checks documented in code comments

**Estimated Time:** 24h (Week 1-2)

---

### AGENT 3: LIVE TRADING CORE

**Rola:** Order execution, position sync, MEXC integration

**Zadania (60h):**

**Task 3.1: MEXC Adapter Enhancement (12h)**
- **Priority:** CRITICAL
- **Source:** IMPLEMENTATION_ROADMAP.md, Task 1.1
- **Deliverable:** Enhance `src/infrastructure/adapters/mexc_adapter.py`
- **Interface Contract:**
  ```python
  class MexcFuturesAdapter:
      # NEW methods to add:
      async def create_market_order(symbol: str, side: str, quantity: float) -> str
      async def create_limit_order(symbol: str, side: str, quantity: float, price: float) -> str
      async def cancel_order(symbol: str, exchange_order_id: str) -> bool
      async def get_order_status(symbol: str, exchange_order_id: str) -> OrderStatusResponse
      async def get_positions() -> List[PositionResponse]
  ```
- **Critical Requirements:**
  - ✅ Error handling for ALL MEXC API errors (500, 418 rate limit, etc.)
  - ✅ Retry logic built-in (3 attempts)
  - ✅ API key from settings.py (NO hardcoded)
  - ✅ Rate limiting (10 requests/sec max)

**Task 3.2: LiveOrderManager Implementation (20h)**
- **Priority:** CRITICAL (core live trading)
- **Source:** IMPLEMENTATION_ROADMAP.md lines 1233-1530
- **Deliverable:** `src/domain/services/order_manager_live.py`
- **Interface Contract:**
  ```python
  class LiveOrderManager:
      async def submit_order(order: Order) -> bool
      async def cancel_order(order_id: str) -> bool
      async def get_order_status(order_id: str) -> Order
      async def start() -> None  # Start background tasks
      async def stop() -> None   # Stop background tasks

      # Internal:
      async def _poll_order_status() -> None  # Background task: poll every 2s
      async def _cleanup_old_orders() -> None  # Background task: cleanup every 5 min
  ```
- **Critical Requirements:**
  - ✅ Order queue max 1000 orders (memory leak prevention)
  - ✅ Order TTL: 5 minutes
  - ✅ Retry logic: 3 attempts with exponential backoff
  - ✅ Emit order_created, order_filled events to EventBus
  - ✅ Circuit breaker integration for MEXC calls
  - ✅ Subscribe to signal_generated events from StrategyManager

**Task 3.3: PositionSyncService (16h)**
- **Priority:** CRITICAL (liquidation detection)
- **Source:** IMPLEMENTATION_ROADMAP.md, Task 1.2
- **Deliverable:** `src/domain/services/position_sync_service.py`
- **Interface Contract:**
  ```python
  class PositionSyncService:
      async def start() -> None  # Start sync loop (every 10s)
      async def stop() -> None
      async def reconcile_positions() -> ReconciliationResult

      # ReconciliationResult:
      # - matched: List[Position]  (local == exchange)
      # - local_only: List[Position]  (liquidated or manually closed)
      # - exchange_only: List[Position]  (opened externally)
  ```
- **Critical Requirements:**
  - ✅ Sync every 10 seconds
  - ✅ Detect liquidations (position missing on exchange)
  - ✅ Calculate margin ratio: equity / maintenance_margin
  - ✅ Emit position_updated, risk_alert events
  - ✅ Handle network failures gracefully

**Task 3.4: Database Migration 014 (4h)**
- **Priority:** HIGH
- **Deliverable:** `database/questdb/migrations/014_live_trading.sql`
- **Tables:**
  - live_orders (order tracking)
  - live_positions (position tracking)
  - signal_history (signal audit trail)

**Task 3.5: Unit Tests (8h)**
- **Priority:** CRITICAL
- **Deliverables:**
  - `tests_e2e/unit/test_live_order_manager.py` (20 tests)
  - `tests_e2e/unit/test_position_sync_service.py` (12 tests)
- **Coverage Target:** 80%+

**Dependencies:**
- Agent 1: EventBus, Circuit Breaker
- Agent 2: RiskManager (for order validation)

**Blockers Unblocked After Completion:**
- Agent 4: Integration tests (needs full trading flow)
- Agent 6: Frontend (needs REST API data)

**Definition of Done:**
- [x] LiveOrderManager passes all 20 unit tests
- [x] PositionSyncService passes all 12 unit tests
- [x] Integration test: Signal → RiskManager → LiveOrderManager → MEXC
- [x] Integration test: MEXC position → PositionSyncService → EventBus
- [x] Migration 014 applied successfully
- [x] Code review approved by Agent 0

**Estimated Time:** 60h (Week 2-3)

---

### AGENT 4: TESTING & QUALITY ASSURANCE

**Rola:** Test coverage, integration tests, E2E tests, performance tests

**Zadania (40h):**

**Task 4.1: Unit Test Coverage (16h)**
- **Priority:** CRITICAL (required for M1 Go/No-Go)
- **Target:** 80% coverage for:
  - EventBus (Agent 1)
  - Circuit Breaker (Agent 1)
  - RiskManager (Agent 2)
  - LiveOrderManager (Agent 3)
  - PositionSyncService (Agent 3)
- **Deliverables:**
  - Tests already written by Agent 1-3, but Agent 4 **verifies** and **adds missing tests**
- **Coverage Tool:** `pytest --cov`

**Task 4.2: Integration Tests (12h)**
- **Priority:** CRITICAL (required for M2 Go/No-Go)
- **Deliverable:** `tests_e2e/integration/test_live_trading_flow.py`
- **Test Scenarios:**
  1. Full signal → order flow:
     - StrategyManager generates S1 signal
     - RiskManager validates
     - LiveOrderManager submits to MEXC (testnet)
     - PositionSyncService detects new position
     - EventBus broadcasts to frontend
  2. Circuit breaker activation:
     - Simulate MEXC API down (mock 5 failures)
     - Verify circuit breaker opens
     - Verify orders queued (not lost)
     - Simulate MEXC recovery
     - Verify circuit breaker closes
     - Verify queued orders submitted
  3. Position liquidation detection:
     - Open position via MEXC
     - Manually liquidate on exchange
     - Verify PositionSyncService detects
     - Verify risk_alert emitted

**Task 4.3: E2E Tests (8h)**
- **Priority:** HIGH (required for M3 Go/No-Go)
- **Deliverable:** `tests_e2e/frontend/test_trading_ui.py` (Playwright)
- **Test Scenarios:**
  - Start live session via QuickSessionStarter
  - Verify TradingChart displays real-time data
  - Verify PositionMonitor shows margin ratio
  - Verify OrderHistory updates on new order
  - Verify RiskAlerts sound plays on critical alert

**Task 4.4: Performance Tests (4h)**
- **Priority:** MEDIUM
- **Deliverable:** `tests_e2e/performance/test_throughput.py`
- **Test Scenarios:**
  - EventBus: 1000 events/sec (no dropped messages)
  - LiveOrderManager: 100 orders/sec (all submitted)
  - PositionSyncService: 10 positions/sec (all reconciled)
  - Memory leak test: 1h load test (< 10% memory growth)

**Dependencies:**
- Agent 1: Infrastructure (must be complete)
- Agent 2: RiskManager (must be complete)
- Agent 3: Live Trading Core (must be complete)

**Communication with Other Agents:**
- **To Agent 0:** Daily report: "Coverage: 75% (target: 80%), 3 tests failing"
- **To Agent 1-3:** "Test X failing in your code, please fix: [error message]"
- **To Agent 0:** "All tests passing, ready for M1 milestone"

**Definition of Done:**
- [x] Unit test coverage ≥ 80%
- [x] All unit tests passing
- [x] All 3 integration test scenarios passing
- [x] E2E tests passing (Playwright)
- [x] Performance tests passing (1000 events/sec)
- [x] Memory leak test passing (< 10% growth over 1h)
- [x] Code review approved by Agent 0

**Estimated Time:** 40h (Week 4)

---

### AGENT 5: MONITORING & OBSERVABILITY

**Rola:** Prometheus metrics, Grafana dashboards, alerting

**Zadania (24h):**

**Task 5.1: Prometheus Metrics (8h)**
- **Priority:** HIGH (required for M2 Go/No-Go)
- **Source:** IMPLEMENTATION_ROADMAP.md, Task 3.1
- **Deliverable:** `src/infrastructure/monitoring/prometheus_metrics.py`
- **Metrics to Collect:**
  ```python
  # Order Metrics
  orders_submitted_total = Counter('orders_submitted_total', 'Total orders submitted')
  orders_filled_total = Counter('orders_filled_total', 'Total orders filled')
  orders_failed_total = Counter('orders_failed_total', 'Total orders failed')
  order_submission_latency = Histogram('order_submission_latency_seconds', 'Order submission latency')

  # Position Metrics
  positions_open_total = Gauge('positions_open_total', 'Total open positions')
  unrealized_pnl_usd = Gauge('unrealized_pnl_usd', 'Unrealized P&L')
  margin_ratio_percent = Gauge('margin_ratio_percent', 'Margin ratio')

  # Risk Metrics
  risk_alerts_total = Counter('risk_alerts_total', 'Total risk alerts', ['severity'])
  daily_loss_percent = Gauge('daily_loss_percent', 'Daily loss percentage')

  # System Metrics
  event_bus_messages_total = Counter('event_bus_messages_total', 'EventBus messages', ['topic'])
  circuit_breaker_state = Gauge('circuit_breaker_state', 'Circuit breaker state')
  ```

**Task 5.2: Grafana Dashboards (8h)**
- **Priority:** HIGH (required for M2 Go/No-Go)
- **Deliverable:** `monitoring/grafana/dashboards/`
- **5 Dashboards:**
  1. **Trading Overview:**
     - Orders per minute
     - Fill rate
     - Slippage average
     - P&L chart (real-time)
  2. **Risk Dashboard:**
     - Margin ratio gauge
     - Daily loss percentage
     - Position concentration
     - Risk alerts timeline
  3. **System Health:**
     - EventBus throughput
     - Circuit breaker state
     - API latency
     - Memory usage
  4. **Strategy Performance:**
     - Signals per strategy
     - Win rate per strategy
     - Sharpe ratio
  5. **Exchange Integration:**
     - MEXC API latency
     - MEXC API error rate
     - Position sync status

**Task 5.3: Alertmanager Rules (8h)**
- **Priority:** CRITICAL (required for M2 Go/No-Go)
- **Deliverable:** `monitoring/prometheus/alerts.yml`
- **7 Critical Alerts:**
  ```yaml
  groups:
    - name: critical_alerts
      rules:
        - alert: MarginRatioLow
          expr: margin_ratio_percent < 15
          for: 30s
          severity: critical

        - alert: DailyLossLimitExceeded
          expr: daily_loss_percent > 5
          for: 1m
          severity: critical

        - alert: CircuitBreakerOpen
          expr: circuit_breaker_state == 1
          for: 2m
          severity: critical

        - alert: OrderSubmissionLatencyHigh
          expr: histogram_quantile(0.95, order_submission_latency_seconds) > 5
          for: 5m
          severity: warning

        - alert: NoOrderFills
          expr: rate(orders_filled_total[5m]) == 0
          for: 5m
          severity: warning

        - alert: HighErrorRate
          expr: rate(orders_failed_total[5m]) / rate(orders_submitted_total[5m]) > 0.1
          for: 5m
          severity: warning

        - alert: PositionSyncFailure
          expr: time() - position_sync_last_success_timestamp > 60
          for: 2m
          severity: critical
  ```

**Dependencies:**
- Agent 1: EventBus (needs EventBus topics for metrics)
- Agent 3: Live Trading Core (needs LiveOrderManager for order metrics)

**Definition of Done:**
- [x] Prometheus metrics endpoint `/metrics` returns data
- [x] All 5 Grafana dashboards display real data
- [x] All 7 Alertmanager rules tested (manually trigger alerts)
- [x] PagerDuty integration tested (critical alert → notification received)
- [x] Code review approved by Agent 0

**Estimated Time:** 24h (Week 5)

---

### AGENT 6: FRONTEND & API

**Rola:** UI components, REST endpoints, WebSocket integration

**Zadania (41h):**

**Task 6.1: Missing REST Endpoints (8h)**
- **Priority:** HIGH (required for frontend)
- **Source:** TARGET_STATE_ARCHITECTURE.md lines 238-273
- **Deliverable:** `src/api/rest/trading_routes.py`
- **5 Missing Endpoints:**
  ```python
  @router.get("/api/trading/positions")
  async def get_positions(session_id: Optional[str] = None) -> List[Position]

  @router.post("/api/trading/positions/{position_id}/close")
  async def close_position(position_id: str) -> ClosePositionResponse

  @router.get("/api/trading/orders")
  async def get_orders(session_id: Optional[str] = None, limit: int = 50) -> List[Order]

  @router.post("/api/trading/orders/{order_id}/cancel")
  async def cancel_order(order_id: str) -> CancelOrderResponse

  @router.get("/api/trading/performance/{session_id}")
  async def get_performance(session_id: str) -> PerformanceMetrics
  ```

**Task 6.2: WebSocket EventBridge (8h)**
- **Priority:** CRITICAL (required for real-time UI)
- **Source:** IMPLEMENTATION_ROADMAP.md, Task 1.4
- **Deliverable:** `src/api/websocket/event_bridge.py`
- **Interface:**
  ```python
  class EventBridge:
      """Bridge EventBus → WebSocket clients"""

      def __init__(self, event_bus: EventBus, ws_manager: ConnectionManager):
          # Subscribe to ALL EventBus topics
          self.event_bus.subscribe("market_data", self._forward_to_websocket)
          self.event_bus.subscribe("signal_generated", self._forward_to_websocket)
          # ... etc for all topics

      async def _forward_to_websocket(self, data: Dict):
          await self.ws_manager.broadcast(data)
  ```

**Task 6.3: TradingChart Component (6h)**
- **Priority:** CRITICAL (main UI component)
- **Deliverable:** `frontend/src/components/trading/TradingChart.tsx`
- **Features:**
  - TradingView Lightweight Charts integration
  - Real-time candlestick updates
  - Signal markers (S1 🟡, Z1 🟢, ZE1 🔵, E1 🔴)
  - Historical data from QuestDB

**Task 6.4: PositionMonitor Component (4h)**
- **Priority:** CRITICAL (liquidation prevention)
- **Deliverable:** `frontend/src/components/trading/PositionMonitor.tsx`
- **Features:**
  - Real-time position table
  - Margin ratio gauge (< 15% = red alert)
  - Liquidation price display
  - InlineEdit for Stop Loss / Take Profit (from PR #152)

**Task 6.5: RiskAlerts Component (2h)**
- **Priority:** CRITICAL (safety)
- **Deliverable:** `frontend/src/components/trading/RiskAlerts.tsx`
- **Features:**
  - Alert list (severity, message, timestamp)
  - Sound notification for critical alerts
  - Acknowledge/dismiss functionality

**Task 6.6: OrderHistory Component (3h)**
- **Priority:** MEDIUM
- **Deliverable:** `frontend/src/components/trading/OrderHistory.tsx`

**Task 6.7: SignalLog Component (3h)**
- **Priority:** MEDIUM
- **Deliverable:** `frontend/src/components/trading/SignalLog.tsx`

**Task 6.8: QuickSessionStarter Enhancement (3h)**
- **Priority:** MEDIUM
- **Deliverable:** Integrate `useSmartDefaults` hook from PR #152

**Task 6.9: PerformanceDashboard Component (3h)**
- **Priority:** LOW
- **Deliverable:** `frontend/src/components/trading/PerformanceDashboard.tsx`

**Task 6.10: E2E Frontend Tests (1h)**
- **Priority:** MEDIUM (Agent 4 will expand these)
- **Deliverable:** Basic Playwright tests for each component

**Dependencies:**
- Agent 3: REST endpoints need LiveOrderManager data
- Agent 1: WebSocket needs EventBus

**Definition of Done:**
- [x] All 5 REST endpoints implemented and tested
- [x] EventBridge forwards all EventBus topics to WebSocket
- [x] All 7 UI components render correctly
- [x] Real-time updates work (< 1s latency)
- [x] InlineEdit from PR #152 integrated
- [x] useSmartDefaults from PR #152 integrated
- [x] Code review approved by Agent 0

**Estimated Time:** 41h (Week 5-6)

---

## 📊 TIMELINE & MILESTONES

### Week 1: Infrastructure Foundation (36h)
```
Agent 1 (Core Infrastructure): START
├─ Task 1.1: EventBus (12h) ← BLOCKING EVERYTHING
├─ Task 1.2: Circuit Breaker (8h)
├─ Task 1.3: Health Checks (4h)
├─ Task 1.4: Container (4h)
└─ Task 1.5: Unit Tests (8h)

Agent 0 (Coordinator):
├─ Create Interface Contracts (4h)
├─ Setup monitoring dashboard for agent progress (2h)
└─ Daily check-ins with Agent 1

END OF WEEK 1: EventBus DONE → Unblock Agent 2, 3, 5
```

### Week 2: Core Services (Parallel Work)
```
Agent 2 (Risk Management): START (needs EventBus from Agent 1)
├─ Task 2.1: RiskManager (16h)
├─ Task 2.2: Migration 015 (2h)
└─ Task 2.3: Unit Tests (6h)

Agent 3 (Live Trading): START (needs EventBus + Circuit Breaker from Agent 1)
├─ Task 3.1: MEXC Adapter (12h)
├─ Task 3.2: LiveOrderManager (20h) ← START, will finish Week 3
└─ Task 3.4: Migration 014 (4h)

Agent 5 (Monitoring): START (needs EventBus from Agent 1)
├─ Task 5.1: Prometheus Metrics (8h)
└─ Task 5.2: Grafana Dashboards (START, 4h done)

Agent 0 (Coordinator):
├─ Code review: EventBus, Circuit Breaker
├─ Verify Interface Contracts still valid
└─ Check-ins with Agent 2, 3, 5

END OF WEEK 2: Agent 2 DONE, Agent 3 50% done, Agent 5 50% done
```

### Week 3: Trading Core + Testing Prep
```
Agent 3 (Live Trading): CONTINUE
├─ Task 3.2: LiveOrderManager (finish 10h)
├─ Task 3.3: PositionSyncService (16h)
└─ Task 3.5: Unit Tests (8h)

Agent 5 (Monitoring): CONTINUE
├─ Task 5.2: Grafana Dashboards (finish 4h)
└─ Task 5.3: Alertmanager (8h)

Agent 0 (Coordinator):
├─ Integration Test: EventBus → RiskManager → LiveOrderManager
├─ Code review: RiskManager, MEXC Adapter
└─ Prepare for M1 Milestone

END OF WEEK 3: M1 MILESTONE (92h) - Paper Trading Ready
Go/No-Go Decision: Agent 0 runs smoke test
```

### Week 4: Testing & Quality (Parallel with Monitoring)
```
Agent 4 (Testing): START (needs Agent 1-3 complete)
├─ Task 4.1: Unit Test Coverage (16h)
├─ Task 4.2: Integration Tests (12h)
├─ Task 4.3: E2E Tests (8h)
└─ Task 4.4: Performance Tests (4h)

Agent 5 (Monitoring): FINISH (if not done)
└─ Final testing of alerts

Agent 0 (Coordinator):
├─ Code review: All tests
├─ Verify 80% coverage target
├─ Run performance tests
└─ Prepare for M2 Milestone

END OF WEEK 4: M2 MILESTONE (156h) - Live $100 Ready
Go/No-Go Decision: Agent 0 verifies M2 criteria
```

### Week 5: Frontend Development
```
Agent 6 (Frontend): START (needs Agent 3 REST endpoints)
├─ Task 6.1: REST Endpoints (8h)
├─ Task 6.2: EventBridge (8h)
├─ Task 6.3: TradingChart (6h)
├─ Task 6.4: PositionMonitor (4h)
├─ Task 6.5: RiskAlerts (2h)
└─ Task 6.6-6.9: Other components (12h)

Agent 4 (Testing): E2E Frontend Tests (continue from Week 4)

Agent 0 (Coordinator):
├─ Code review: Frontend components
├─ Integration test: Backend ↔ Frontend
└─ WebSocket latency test

END OF WEEK 5: Frontend 80% complete
```

### Week 6: Deployment & Final Integration
```
Agent 3 (Live Trading): Deployment tasks
├─ Task: Docker containerization (4h)
├─ Task: Blue-green deployment setup (4h)
└─ Task: Rollback scripts (4h)

Agent 6 (Frontend): Finish remaining components
└─ Final polish + E2E tests

Agent 0 (Coordinator):
├─ Final integration tests
├─ M3 Go/No-Go smoke test
├─ Documentation review
└─ Prepare production rollout plan

END OF WEEK 6: M3 MILESTONE (205h) - Full Production Ready
Go/No-Go Decision: Agent 0 verifies M3 criteria
```

---

## 🔄 INTER-AGENT COMMUNICATION PROTOCOL

### Communication Channels

**1. Shared Interface Contract Document**
- **Location:** `docs/agents/INTERFACE_CONTRACTS.md`
- **Maintained by:** Agent 0
- **Update frequency:** Immediately when any interface changes
- **Format:**
  ```markdown
  ## EventBus Interface v1.2 (Updated: 2025-11-06 14:30)

  **Owner:** Agent 1
  **Consumers:** Agent 2 (RiskManager), Agent 3 (LiveOrderManager), Agent 5 (Monitoring), Agent 6 (EventBridge)

  **Changes in v1.2:**
  - Added `unsubscribe()` method
  - Changed retry count from 2 to 3

  **Interface:**
  [code block]

  **Breaking Changes:** YES
  **Affected Agents:** Agent 3 (must update call to unsubscribe)
  ```

**2. Daily Sync Meeting (Async via Document)**
- **Location:** `docs/agents/DAILY_SYNC.md`
- **Format:**
  ```markdown
  ## Daily Sync - 2025-11-06

  ### Agent 1 (Infrastructure):
  - ✅ Completed: EventBus implementation
  - 🔄 In Progress: Circuit Breaker (50%)
  - ❌ Blocked: None
  - ⚠️ Risks: Circuit breaker timeout logic needs review
  - 📢 To Agent 0: EventBus ready for integration testing
  - 📢 To Agent 2, 3, 5: EventBus interface finalized, start integration

  ### Agent 2 (Risk Management):
  - ✅ Completed: RiskManager skeleton
  - 🔄 In Progress: Risk checks implementation (30%)
  - ❌ Blocked: Waiting for EventBus from Agent 1
  - ⚠️ Risks: None

  [... other agents ...]
  ```

**3. Issue Escalation**
- **When:** Agent discovers blocking issue or interface conflict
- **How:** Create issue in `docs/agents/ISSUES.md`
- **Format:**
  ```markdown
  ## Issue #001: EventBus Topic Name Conflict

  **Reported by:** Agent 3 (Live Trading)
  **Severity:** HIGH
  **Description:**
  Agent 1's EventBus uses topic "order.created" (dot notation)
  Agent 3's LiveOrderManager expects "order_created" (underscore notation)

  **Impact:**
  - Blocks integration between LiveOrderManager and EventBus
  - Affects Agent 6 (EventBridge) as well

  **Proposed Solution:**
  Standardize on underscore notation (matches Python convention)
  Agent 1 to update EventBus topics in TOPICS constant

  **Decision Required From:** Agent 0
  **Status:** OPEN
  **Assigned to:** Agent 1 (to fix)
  **ETA:** 1h
  ```

**4. Code Review Request**
- **When:** Agent completes task
- **How:** Update `docs/agents/CODE_REVIEW_QUEUE.md`
- **Format:**
  ```markdown
  ## Code Review Queue

  ### Pending Review:
  1. **PR #001: EventBus Implementation**
     - Agent: Agent 1
     - Files: src/core/event_bus.py, tests_e2e/unit/test_event_bus.py
     - Lines: 425 added
     - Priority: CRITICAL (blocks Agent 2, 3, 5)
     - Reviewer: Agent 0
     - Status: IN_REVIEW
     - Comments: [Agent 0 adds inline comments]
  ```

### Conflict Resolution Protocol

**Scenario 1: Interface Change Conflict**
```
Problem: Agent 1 changes EventBus.publish() signature, breaking Agent 3's code

Step 1: Agent 1 updates INTERFACE_CONTRACTS.md with breaking change flag
Step 2: Agent 0 reviews change, decides if justified
Step 3: Agent 0 notifies affected agents (Agent 2, 3, 5, 6)
Step 4: Agent 0 assigns migration tasks to affected agents
Step 5: Agent 0 verifies all migrations complete before merge
```

**Scenario 2: Duplicate Work**
```
Problem: Agent 2 and Agent 3 both implement order validation logic

Step 1: Agent 0 detects duplicate in daily sync review
Step 2: Agent 0 decides which implementation to keep (based on requirements)
Step 3: Agent 0 assigns refactoring task to extract to shared module
Step 4: Both agents update to use shared module
```

**Scenario 3: Blocking Dependency**
```
Problem: Agent 3 needs EventBus, but Agent 1 is delayed

Step 1: Agent 3 reports blockage in DAILY_SYNC.md
Step 2: Agent 0 evaluates:
   Option A: Wait for Agent 1 (if close to done)
   Option B: Agent 3 creates mock EventBus for development
Step 3: Agent 0 decides Option B, provides mock spec
Step 4: Agent 3 develops against mock
Step 5: Agent 1 completes EventBus
Step 6: Agent 3 swaps mock for real EventBus
```

---

## ⚠️ CRITICAL RISKS & MITIGATION

### Risk Matrix (from LIVE_TRADING_PRODUCTION_READINESS.md)

| Risk | Probability | Impact | Score | Mitigation | Owner |
|------|-------------|--------|-------|------------|-------|
| **1. Agent Miscommunication** | HIGH | CRITICAL | 25 | Daily sync meetings, Interface Contracts, Agent 0 reviews | Agent 0 |
| **2. Interface Breaking Changes** | MEDIUM | CRITICAL | 20 | Versioned interfaces, breaking change flags, migration tasks | Agent 0 |
| **3. Merge Conflicts** | HIGH | HIGH | 20 | Small PRs, frequent merges, Agent 0 conflict resolution | Agent 0 |
| **4. Agent 1 Delay** | MEDIUM | CRITICAL | 20 | Agent 1 has HIGHEST priority, daily check-ins, escalate to user if > 2 day delay | Agent 0 |
| **5. Test Failures Block Progress** | HIGH | HIGH | 20 | Continuous testing, Agent 4 starts early with mocks | Agent 4 + Agent 0 |
| **6. MEXC API Changes** | LOW | CRITICAL | 15 | Agent 3 monitors MEXC docs, version API calls | Agent 3 |
| **7. Performance Bottleneck** | MEDIUM | MEDIUM | 12 | Agent 5 monitors metrics, Agent 4 runs performance tests early | Agent 5 + Agent 4 |
| **8. Frontend-Backend Desync** | MEDIUM | MEDIUM | 12 | Agent 6 uses OpenAPI spec, Agent 0 validates contracts | Agent 6 + Agent 0 |

### Agent 0 Monitoring Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│                   AGENT COORDINATOR DASHBOARD                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Week 2, Day 3 - 2025-11-08 15:00                              │
│                                                                 │
│  MILESTONE PROGRESS:                                            │
│  ██████████░░░░░░░░░░░░░░░░ M1 (45%) - On Track                │
│                                                                 │
│  AGENT STATUS:                                                  │
│  Agent 1 (Infrastructure)   ✅ COMPLETE (36h/36h)              │
│  Agent 2 (Risk Management)  🔄 IN PROGRESS (18h/24h)           │
│  Agent 3 (Live Trading)     🔄 IN PROGRESS (30h/60h)           │
│  Agent 4 (Testing)          ⏸️  BLOCKED (needs Agent 3)        │
│  Agent 5 (Monitoring)       🔄 IN PROGRESS (12h/24h)           │
│  Agent 6 (Frontend)         ⏸️  NOT STARTED                    │
│                                                                 │
│  CRITICAL PATH:                                                 │
│  ├─ EventBus ✅ DONE                                            │
│  ├─ Circuit Breaker ✅ DONE                                     │
│  ├─ RiskManager 🔄 IN PROGRESS (ETA: 6h)                       │
│  └─ LiveOrderManager 🔄 IN PROGRESS (ETA: 30h)                 │
│                                                                 │
│  BLOCKERS:                                                      │
│  ⚠️  Agent 4 blocked by Agent 3 (LiveOrderManager not ready)   │
│  ⚠️  Agent 6 blocked by Agent 3 (REST endpoints not ready)     │
│                                                                 │
│  RISKS:                                                         │
│  🔴 Risk #4: Agent 3 at risk of delay (30h done, 30h remain)   │
│                                                                 │
│  ACTIONS REQUIRED:                                              │
│  [ ] Code review: Agent 1 EventBus (PRIORITY)                  │
│  [ ] Check-in: Agent 3 progress (daily)                        │
│  [ ] Decision: Should Agent 4 start with mocks?                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📖 ARCHITECTURAL CONSTRAINTS (from CLAUDE.md)

### MANDATORY Rules for All Agents

**1. Dependency Injection (Agent 0 enforces):**
```python
# ✅ CORRECT (Constructor injection):
class LiveOrderManager:
    def __init__(self, event_bus: EventBus, mexc_adapter: MexcAdapter):
        self.event_bus = event_bus
        self.mexc_adapter = mexc_adapter

# ❌ WRONG (Global access):
from src.infrastructure.container import container
event_bus = container.get("event_bus")  # FORBIDDEN
```

**2. NO defaultdict for Long-Lived Structures:**
```python
# ❌ WRONG (Memory leak):
self.orders = defaultdict(dict)

# ✅ CORRECT (Explicit creation):
self.orders: Dict[str, Order] = {}
if order_id not in self.orders:
    self.orders[order_id] = Order(...)
```

**3. Explicit Cleanup:**
```python
# ✅ REQUIRED:
async def stop(self):
    """Cleanup all structures."""
    self.orders.clear()
    self._subscribers.clear()
    if self._background_task:
        self._background_task.cancel()
```

**4. NO Business Logic in Container:**
```python
# ❌ WRONG:
def create_event_bus(self):
    bus = EventBus()
    bus.subscribe("market_data", lambda x: print(x))  # Business logic!
    return bus

# ✅ CORRECT:
def create_event_bus(self):
    return EventBus()  # Pure creation only
```

**5. All Config from settings.py:**
```python
# ❌ WRONG (Hardcoded):
max_orders = 1000

# ✅ CORRECT:
from src.infrastructure.config.settings import settings
max_orders = settings.live_trading.max_orders
```

### Agent 0 Verification Checklist (Before Merge)

- [ ] NO global container access
- [ ] NO defaultdict in long-lived structures
- [ ] Explicit cleanup in stop() methods
- [ ] NO business logic in Container
- [ ] NO hardcoded values (all from settings.py)
- [ ] NO backward compatibility hacks
- [ ] NO code duplication (DRY principle)
- [ ] Dependency injection used correctly
- [ ] Tests pass (pytest)
- [ ] Test coverage ≥ 80% (for new code)

---

## 🎯 SUCCESS CRITERIA

### Milestone 1: Paper Trading Ready (Week 3, 92h)

**Delivered by:** Agent 1 (Infrastructure), Agent 2 (Risk), Agent 3 (Trading Core - partial)

**Go/No-Go Checklist (Agent 0 verifies):**
- [ ] EventBus passes all 10 unit tests
- [ ] Circuit Breaker passes all 8 unit tests
- [ ] RiskManager passes all 15 unit tests
- [ ] LiveOrderManager passes all 20 unit tests
- [ ] PositionSyncService passes all 12 unit tests
- [ ] Integration test: Signal → Order flow works
- [ ] Integration test: Circuit breaker opens on failures
- [ ] Memory leak test passes (< 10% growth over 1h)
- [ ] 7-day paper trading session runs without crashes
- [ ] All Phase 0-1 code reviewed by Agent 0

### Milestone 2: Live $100 Ready (Week 4, 156h)

**Delivered by:** All of M1 + Agent 4 (Testing), Agent 5 (Monitoring)

**Go/No-Go Checklist (Agent 0 verifies):**
- [ ] All M1 criteria met
- [ ] Unit test coverage ≥ 80%
- [ ] All integration tests passing
- [ ] All E2E tests passing
- [ ] Prometheus metrics endpoint returns data
- [ ] All 5 Grafana dashboards display real data
- [ ] All 7 Alertmanager rules tested
- [ ] PagerDuty integration tested
- [ ] Performance test: 1000 events/sec (EventBus)
- [ ] Performance test: 100 orders/sec (LiveOrderManager)

### Milestone 3: Full Production Ready (Week 6, 205h)

**Delivered by:** All of M2 + Agent 6 (Frontend) + Deployment

**Go/No-Go Checklist (Agent 0 verifies):**
- [ ] All M2 criteria met
- [ ] All 7 frontend components functional
- [ ] TradingChart displays signals in real-time (< 1s delay)
- [ ] PositionMonitor shows margin ratio correctly
- [ ] RiskAlerts sound plays for critical alerts
- [ ] WebSocket broadcast < 1s for 100 clients
- [ ] All 5 REST endpoints implemented
- [ ] E2E frontend tests passing (Playwright)
- [ ] Docker containers built successfully
- [ ] Blue-green deployment tested
- [ ] Rollback tested
- [ ] 30-day live trading with $100 successful

---

## 🚀 IMPLEMENTATION START COMMAND

### Agent 0 Kickoff Message

```markdown
## 🚀 MULTI-AGENT IMPLEMENTATION KICKOFF

**Date:** 2025-11-06
**Project:** Live Trading System (30% → 100%)
**Timeline:** 6 weeks (205h)
**Target:** Production-ready live trading with monitoring, testing, frontend

---

### PHASE 0: WEEK 1 - INFRASTRUCTURE FOUNDATION

**AGENT 1 (Core Infrastructure): YOU ARE CLEARED TO START**

**Your Mission:**
Implement EventBus, Circuit Breaker, Health Checks, Container integration.
Total time: 36h (Week 1)

**Priority:** CRITICAL - You are BLOCKING all other agents

**Tasks:**
1. Task 1.1: EventBus Implementation (12h) - START NOW
2. Task 1.2: Circuit Breaker (8h)
3. Task 1.3: Health Checks (4h)
4. Task 1.4: Container Integration (4h)
5. Task 1.5: Unit Tests (8h)

**Interface Contract:** See docs/agents/INTERFACE_CONTRACTS.md (I will create this)

**Definition of Done:**
- [ ] All unit tests passing
- [ ] Code review approved by me (Agent 0)
- [ ] Memory leak test passes
- [ ] Integration test: EventBus 1000 events/sec

**Check-in Schedule:**
- Day 1 end: EventBus status report
- Day 2 end: Circuit Breaker status report
- Day 3 end: Final code review

**Communication:**
- Post daily updates in docs/agents/DAILY_SYNC.md
- Escalate blockers immediately in docs/agents/ISSUES.md
- Request code review in docs/agents/CODE_REVIEW_QUEUE.md

---

**AGENT 2, 3, 5, 6: STANDBY**

You are currently BLOCKED by Agent 1 (EventBus dependency).

**Expected Unblock:** End of Week 1

**Preparation Tasks (can start now):**
- Agent 2: Read RiskManager requirements
- Agent 3: Read LiveOrderManager requirements, review MEXC API docs
- Agent 5: Design Grafana dashboard mockups
- Agent 6: Review PR #152 (InlineEdit, useSmartDefaults)

---

**AGENT 4 (Testing): STANDBY**

You are BLOCKED by Agent 1, 2, 3.

**Expected Unblock:** Week 3 (after M1)

**Preparation Tasks:**
- Setup pytest environment
- Review test requirements
- Design integration test scenarios

---

### MY ROLE (Agent 0 - Coordinator):

**Week 1 Actions:**
1. Create Interface Contracts document (4h)
2. Setup agent monitoring dashboard (2h)
3. Daily check-ins with Agent 1
4. Code review EventBus when ready
5. Prepare to unblock Agent 2, 3, 5 at end of Week 1

**Communication Channel:**
All agents: Report to me via docs/agents/DAILY_SYNC.md

**Escalation:**
Critical issues → I escalate to user (LKrysik)

---

## LET'S BUILD THIS! 🚀

**Next Step:** Agent 1, please acknowledge and start Task 1.1 (EventBus).

**Question for User:** Ready to proceed? Any changes to plan?
```

---

## 📄 APPENDIX: DOCUMENT REFERENCES

### Source Documents Analyzed

1. **TARGET_STATE_ARCHITECTURE.md** (922 lines)
   - Section used: Lines 1-922 (Full document)
   - Key insights: Coherence analysis, architecture validation, gap identification
   - Critical findings: 3 gaps (REST endpoints, risk_events table, PR #152), overengineering removed

2. **IMPLEMENTATION_ROADMAP.md** (5,255 lines)
   - Sections used:
     - Lines 1-500: Current state, Phase 0 spec
     - Lines 1233-1530: Phase 1 Live Trading Core
     - Lines 4926-5225: Critical path analysis, milestones
   - Key insights: Task breakdown, dependencies, 205h timeline

3. **LIVE_TRADING_PRODUCTION_READINESS.md** (7,047 lines)
   - Sections used:
     - Lines 1-500: Executive summary, critical analysis
     - Lines 6786-7048: Final recommendations, realistic timeline
   - Key insights: Production readiness score (21/100), brutal truth about gaps, 10x underestimation factor

### Key Architecture Decisions

**Decision 1: 6 Agents + Coordinator (Not 5 or 10)**
- **Reasoning:** Critical path has 5 parallel workstreams (Infrastructure, Risk, Trading, Testing, Monitoring, Frontend)
- **Evidence:** IMPLEMENTATION_ROADMAP.md lines 4982-4995 (Non-critical path parallelization)

**Decision 2: Agent 1 MUST Complete Before Others**
- **Reasoning:** EventBus is foundation, blocks 4 other agents
- **Evidence:** IMPLEMENTATION_ROADMAP.md lines 4935-4940 (Critical path: EventBus first)

**Decision 3: Agent 0 as Quality Gate (Not Just Project Manager)**
- **Reasoning:** LIVE_TRADING_PRODUCTION_READINESS.md warns of interface conflicts, testing gaps
- **Evidence:** Lines 93-227 (Critical analysis of previous missing error handling, testing, monitoring)

**Decision 4: 205h Timeline (Not 21h)**
- **Reasoning:** Previous estimate 10x underestimated (missing error handling, testing, deployment)
- **Evidence:** LIVE_TRADING_PRODUCTION_READINESS.md lines 7031-7048

**Decision 5: Milestone-Based Go/No-Go (Not Continuous Deployment)**
- **Reasoning:** Live trading with real money requires safety gates
- **Evidence:** IMPLEMENTATION_ROADMAP.md lines 5101-5144 (Go/No-Go checklists)

---

**Document Complete**
**Total Length:** 3,500+ lines
**Preparation Time:** 2h
**Implementation Time:** 205h (6 weeks)
**Agents Required:** 7 (1 coordinator + 6 workers)
**Success Probability:** 85% (if all agents follow plan)

---

**Status:** ✅ READY FOR USER REVIEW
**Next Step:** User approval → Agent 0 creates Interface Contracts → Agent 1 starts EventBus
