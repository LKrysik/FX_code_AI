# Coding Standards

**Project:** FX Agent AI
**Last Updated:** 2025-12-25

This document defines coding standards for the FX Agent AI project. All contributors must follow these conventions to ensure consistency across the codebase.

---

## Python Standards

### Style Guide
- Follow **PEP 8** for all Python code
- Maximum line length: **100 characters**
- Use **4 spaces** for indentation (no tabs)

### Type Hints
All functions must include type hints:

```python
# GOOD
async def calculate_indicator(
    symbol: str,
    window_seconds: int,
    timestamp: datetime
) -> Optional[float]:
    """Calculate indicator value for the given symbol."""
    ...

# BAD - missing type hints
async def calculate_indicator(symbol, window_seconds, timestamp):
    ...
```

### Docstrings
Use Google-style docstrings for all public functions:

```python
def process_signal(signal_data: Dict[str, Any]) -> Signal:
    """Process raw signal data into a Signal object.

    Args:
        signal_data: Dictionary containing signal information with keys:
            - symbol: Trading pair (e.g., "BTC_USDT")
            - signal_type: Type of signal (S1, O1, Z1, ZE1, E1)
            - timestamp: ISO-8601 formatted timestamp

    Returns:
        Signal object ready for further processing.

    Raises:
        ValidationError: If signal_data is missing required fields.
    """
    ...
```

### Async/Await
Use `asyncio` for all I/O operations:

```python
# GOOD - async I/O
async def fetch_market_data(symbol: str) -> MarketData:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# BAD - blocking I/O
def fetch_market_data(symbol: str) -> MarketData:
    response = requests.get(url)  # Blocks the event loop!
    return response.json()
```

---

## Naming Conventions

### Python Files
| Pattern | Example | Usage |
|---------|---------|-------|
| `snake_case.py` | `trading_routes.py` | All Python modules |
| Descriptive prefix | `signal_processor.py` | Indicates domain |

### TypeScript/React Files
| Pattern | Example | Usage |
|---------|---------|-------|
| `PascalCase.tsx` | `SignalPanel.tsx` | React components |
| `camelCase.ts` | `websocketService.ts` | Services/utilities |
| `useXxx.ts` | `useWebSocket.ts` | Custom hooks |

### Variables and Functions
```python
# Python - snake_case
order_id = "12345"
entry_price = 50000.0

def calculate_unrealized_pnl(position: Position) -> float:
    ...

# TypeScript - camelCase for variables, PascalCase for components
const orderId = "12345";
const entryPrice = 50000.0;

function SignalPanel({ signals }: SignalPanelProps) {
    ...
}
```

### Database (QuestDB)
| Pattern | Example |
|---------|---------|
| `snake_case` tables | `strategy_signals`, `tick_prices` |
| `snake_case` columns | `session_id`, `entry_price` |
| SYMBOL type for indexes | `symbol`, `indicator_id` |

---

## API Conventions

### Endpoint Naming
```
/api/{resource}/{action}
/api/{resource}/{id}/{action}
```

Examples:
- `GET /api/signals/history`
- `POST /api/trading/positions/{id}/close`
- `PATCH /api/trading/positions/{id}/sl-tp`

### Response Envelope
**All API responses** must use the standard envelope:

```python
{
    "version": "1.0",
    "timestamp": "2025-12-25T10:30:00Z",
    "id": "<request_id>",
    "status": "success",
    "data": {...}
}
```

Use `ensure_envelope()` helper - never return raw data:

```python
# GOOD
from src.api.response_envelope import ensure_envelope

@router.get("/signals")
async def get_signals():
    signals = await signal_service.get_all()
    return ensure_envelope({"signals": signals})

# BAD - raw response without envelope
@router.get("/signals")
async def get_signals():
    return await signal_service.get_all()
```

### Error Response Structure
```python
{
    "type": "error",
    "error_code": "validation_error",
    "error_message": "Symbol is required",
    "http_status": 400
}
```

---

## Event Bus Conventions

### Event Naming
| Category | Pattern | Examples |
|----------|---------|----------|
| Market | `market.*` | `market.price_update`, `market_data` |
| Signal | `signal.*` | `signal_generated`, `indicator_updated` |
| Order | `order.*` | `order_created`, `order_filled` |
| Position | `position.*` | `position_updated`, `position_opened` |

### Publishing Events
```python
# GOOD - use defined event types
await event_bus.publish("signal_generated", {
    "signal_type": "S1",
    "symbol": "BTC_USDT",
    "timestamp": datetime.utcnow().isoformat(),
    "metadata": {...}
})

# BAD - inventing new event names
await event_bus.publish("my_custom_signal", {...})  # Not in EventType!
```

---

## Architecture Boundaries

### Clean Architecture Layers

```
src/
├── api/              # HTTP/WebSocket handlers (outermost)
├── application/      # Use cases, controllers
├── domain/           # Business logic (innermost)
├── infrastructure/   # External dependencies
└── core/             # Cross-cutting concerns
```

**Import Rules:**
- Domain layer must NOT import from infrastructure
- API layer can import from application and domain
- Infrastructure implements domain interfaces

```python
# GOOD - domain defines interface, infrastructure implements
# domain/interfaces/exchange.py
class ExchangeAdapter(ABC):
    @abstractmethod
    async def get_price(self, symbol: str) -> float: ...

# infrastructure/exchanges/mexc_adapter.py
class MEXCAdapter(ExchangeAdapter):
    async def get_price(self, symbol: str) -> float:
        # Implementation using MEXC API
        ...

# BAD - domain importing infrastructure
# domain/services/price_service.py
from infrastructure.exchanges.mexc_adapter import MEXCAdapter  # NO!
```

---

## Error Handling

### Use Domain Exceptions
```python
# domain/exceptions.py
class DomainException(Exception):
    """Base exception for domain errors."""
    pass

class ValidationError(DomainException):
    """Raised when validation fails."""
    pass

class InsufficientBalanceError(DomainException):
    """Raised when balance is insufficient for operation."""
    pass
```

### Catch at API Layer
```python
# api/trading_routes.py
from src.api.error_mapper import ErrorMapper

@router.post("/orders")
async def create_order(order: OrderRequest):
    try:
        result = await order_service.create(order)
        return ensure_envelope(result)
    except ValidationError as e:
        return ErrorMapper.to_response(e, status_code=400)
    except InsufficientBalanceError as e:
        return ErrorMapper.to_response(e, status_code=422)
```

### No Silent Failures
```python
# GOOD - log and surface errors
try:
    await process_signal(signal)
except Exception as e:
    logger.error(f"Signal processing failed: {e}", exc_info=True)
    await notify_error(error_code="signal_processing_failed", message=str(e))
    raise

# BAD - swallowing exceptions
try:
    await process_signal(signal)
except Exception:
    pass  # Silent failure - NEVER do this!
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Global mutable state | Use dependency injection |
| Hardcoded values | Use configuration/constants |
| Giant functions (>50 lines) | Split into smaller functions |
| Mixed naming conventions | Consistent `snake_case` for Python |
| Direct infrastructure imports in domain | Use interfaces/abstractions |
| Raw API responses | Always use response envelope |
| Inventing event names | Use defined `EventType` constants |
| `camelCase` in Python | Use `snake_case` |

---

## Testing Standards

### Test File Location
| Layer | Pattern |
|-------|---------|
| Backend | `/tests/` directory + `/src/__tests__/` |
| Frontend | Co-located `/__tests__/` or `*.test.tsx` |

### Test Naming
```python
# tests/unit/test_signal_processor.py

def test_process_signal_with_valid_data_returns_signal():
    """Test that valid signal data produces a Signal object."""
    ...

def test_process_signal_with_missing_symbol_raises_validation_error():
    """Test that missing symbol field raises ValidationError."""
    ...
```

### Run Tests Before Commit
```bash
# Backend
pytest tests/ -v

# Frontend
npm run test
```

---

## Quick Reference

### Before You Code
1. Check existing patterns in similar files
2. Verify event names against `core/events.py`
3. Follow Clean Architecture layer boundaries

### Before You Commit
1. Run `pytest` - all tests must pass
2. Check type hints are complete
3. Verify no hardcoded values
4. Ensure error handling is in place

### When in Doubt
- Reference `_bmad-output/architecture.md` for patterns
- Check existing code for conventions
- Ask before inventing new patterns

---

*This document is the authoritative source for coding standards. When conflicts arise with external style guides, this document takes precedence.*
