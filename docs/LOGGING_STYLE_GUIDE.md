# Logging Style Guide

Unified logging conventions for FX Agent AI backend (Python) and frontend (TypeScript).

## API Signatures

### Backend (Python)

```python
from src.core.logger import get_logger

logger = get_logger(__name__)

logger.info("event.type", {"key": "value", "count": 42})
logger.warn("event.type", {"key": "value"})
logger.error("event.type", {"key": "value"}, exc_info=True)
logger.debug("event.type", {"key": "value"})
```

**Signature:**
```python
def info(self, event_type: str, data: Dict[str, Any] = None) -> None
def warning(self, event_type: str, data: Dict[str, Any] = None) -> None
def error(self, event_type: str, data: Dict[str, Any] = None, exc_info=False) -> None
def debug(self, event_type: str, data: Dict[str, Any] = None) -> None
```

### Frontend (TypeScript)

```typescript
import { Logger } from '@/services/frontendLogService';

Logger.info('event.type', { key: 'value', count: 42 });
Logger.warn('event.type', { key: 'value' });
Logger.error('event.type', { key: 'value' }, error);
Logger.debug('event.type', { key: 'value' });
```

**Signature:**
```typescript
info(eventType: string, data: Record<string, unknown> = {}): void
warn(eventType: string, data: Record<string, unknown> = {}): void
error(eventType: string, data: Record<string, unknown> = {}, error?: Error): void
debug(eventType: string, data: Record<string, unknown> = {}): void
```

## Event Type Naming Convention

Use `module.action` format with lowercase and dots as separators:

| Pattern | Example | Usage |
|---------|---------|-------|
| `module.action` | `user.login` | Standard events |
| `module.action.detail` | `api.request.failed` | More specific events |
| `component.lifecycle` | `websocket.connected` | Component state changes |

### Categories

| Category | Examples |
|----------|----------|
| **API** | `api.request`, `api.response`, `api.error`, `api.timeout` |
| **WebSocket** | `websocket.connected`, `websocket.disconnected`, `websocket.message` |
| **User** | `user.login`, `user.logout`, `user.action` |
| **Trading** | `trading.order_placed`, `trading.position_opened`, `trading.signal` |
| **State Machine** | `state_machine.transition`, `state_machine.error` |
| **Component** | `component.mounted`, `component.error`, `component.render` |

## Log Levels

| Level | Backend | Frontend | When to Use |
|-------|---------|----------|-------------|
| **DEBUG** | `logger.debug()` | `Logger.debug()` | Development diagnostics, detailed flow tracing |
| **INFO** | `logger.info()` | `Logger.info()` | Normal operations, significant events |
| **WARN** | `logger.warning()` | `Logger.warn()` | Recoverable issues, degraded operation |
| **ERROR** | `logger.error()` | `Logger.error()` | Failures requiring attention |

### Backend-only: Exception Info

```python
try:
    risky_operation()
except Exception as e:
    logger.error("operation.failed", {"context": value}, exc_info=True)
```

### Frontend-only: Error Objects

```typescript
try {
    await riskyOperation();
} catch (error) {
    Logger.error('operation.failed', { context: value }, error as Error);
}
```

## Best Practices

### Always Include Context

```python
# Good
logger.info("order.placed", {"order_id": order.id, "symbol": order.symbol, "side": order.side})

# Bad - missing context
logger.info("order.placed", {})
```

### Use Consistent Field Names

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Trading pair (e.g., "BTCUSDT") |
| `session_id` | string | Trading session identifier |
| `order_id` | string | Order identifier |
| `position_id` | string | Position identifier |
| `strategy_name` | string | Strategy identifier |
| `error` | string | Error message |
| `duration_ms` | number | Operation duration in milliseconds |
| `count` | number | Count of items |

### Frontend: Production vs Development

- **DEBUG** logs only appear in browser console (development mode)
- **INFO** logs appear in browser console only
- **WARN** and **ERROR** logs are sent to backend for persistence

## Files

| Stack | File | Purpose |
|-------|------|---------|
| Backend | `src/core/logger.py` | StructuredLogger implementation |
| Frontend | `frontend/src/services/frontendLogService.ts` | Logger singleton |
