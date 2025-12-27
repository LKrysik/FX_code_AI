# Logging Refactoring Plan

## Problem Statement
Logging implementation is scattered and inconsistent:
- **Backend**: 16 modules use raw `logging.getLogger()` instead of unified `get_logger()`
- **Frontend**: 83 files use scattered `console.log/error/warn` calls
- No correlation between frontend and backend logs
- Inconsistent log formats and event types

## Goal
Single, unified logging standard across entire codebase with:
1. All Python modules using `get_logger()` from `src.core.logger`
2. All TypeScript code using centralized `Logger` service
3. Correlation IDs linking frontend/backend logs
4. Consistent structured JSON format

---

## Epic 1: Backend Logging Unification

### Story 1.1: Core Module Migration
**Files to update:**
- `src/core/event_bus.py` (line 15)
- `src/core/telemetry.py` (line 20)
- `src/core/cpu_optimization_patch.py` (line 12)
- `src/core/circuit_breaker.py` (line 18)
- `src/core/plugin_system.py` (line 11)

**Change Pattern:**
```python
# FROM:
import logging
logger = logging.getLogger(__name__)
logger.info("message")

# TO:
from src.core.logger import get_logger
logger = get_logger(__name__)
logger.info("event_type", {"message": "details"})
```

### Story 1.2: Domain Services Migration
**Files to update:**
- `src/domain/services/order_manager_live.py` (line 37)
- `src/domain/services/indicator_scheduler_questdb.py` (line 36)
- `src/domain/services/position_sync_service.py` (line 32)
- `src/domain/services/risk_manager.py` (line 33)
- `src/domain/services/strategy_schema.py` (line 55)
- `src/domain/services/strategy_template_service.py` (line 19)

### Story 1.3: Infrastructure Migration
**Files to update:**
- `src/data_feed/questdb_provider.py` (line 105)
- `src/infrastructure/monitoring/prometheus_metrics.py` (line 28)
- `src/api/monitoring_routes.py` (line 18)

### Story 1.4: Application Use Cases Migration
**Files to update:**
- `src/application/use_cases/detect_pump_signals.py` (line 60)
- `src/core/config.py` (line 323) - inline usage

---

## Epic 2: Frontend Logging Unification

### Story 2.1: Create Unified Logger Service
Extend `frontendLogService.ts` to support:
- `Logger.info()`, `Logger.warn()`, `Logger.error()`, `Logger.debug()`
- Optional correlation ID parameter
- Configurable log levels
- Development mode console output

### Story 2.2: Critical Services Migration
**High-priority files:**
- `frontend/src/services/api.ts`
- `frontend/src/services/websocket.ts`
- `frontend/src/services/TradingAPI.ts`
- `frontend/src/services/authService.ts`

### Story 2.3: Hooks Migration
**Files to update:**
- `frontend/src/hooks/useWebSocket.ts`
- `frontend/src/hooks/useStatusHeroData.ts`
- `frontend/src/hooks/useStateMachineState.ts`
- Other hook files with console usage

### Story 2.4: Component Migration (Dashboard)
Dashboard components with console usage

### Story 2.5: Component Migration (Trading)
Trading components with console usage

---

## Epic 3: Log Correlation

### Story 3.1: Add Correlation ID to Backend Logger
- Generate/accept correlation ID in structured logs
- Pass correlation ID through request context

### Story 3.2: Add Correlation ID to Frontend Logger
- Generate session-level correlation ID
- Include in all log entries and API requests

---

## Implementation Priority
1. Backend Core Modules (highest impact, least files)
2. Frontend Logger Service Enhancement
3. Frontend Critical Services
4. Remaining backend files
5. Frontend components (gradual migration)
6. Correlation IDs

---

## Acceptance Criteria
- [ ] All Python files use `get_logger()` - no raw `logging.getLogger()` outside logger.py
- [ ] Frontend has unified Logger with info/warn/error/debug methods
- [ ] Critical frontend services migrated to Logger
- [ ] All logs in JSON structured format
- [ ] Tests pass after migration
