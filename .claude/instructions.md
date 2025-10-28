# Claude Code Instructions

**Single source of truth for Claude Code when working in this repository.**

## 🎯 Project Identity

**What**: Cryptocurrency Trading System (Real-time + Backtesting)
**Stack**: Python FastAPI + Next.js 14 + QuestDB
**Architecture**: Layered + Event-Driven
**Current Sprint**: Sprint 16 - Indicator System Consolidation
**Status**: [docs/STATUS.md](../docs/STATUS.md)

## 🚀 Quick Actions (Most Common Tasks)

### Start the Application

```bash
# Full stack
.\start_all.ps1

# Backend only (port 8080)
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload

# Frontend only (port 3000)
cd frontend && npm run dev
```

### Add New Indicator

1. **Create**: `src/domain/services/indicators/my_indicator.py`
   ```python
   from src.domain.services.indicators.incremental_base import IncrementalIndicator

   class MyIndicator(IncrementalIndicator):
       def update(self, price_data):
           # Incremental calculation logic
           pass
   ```

2. **Register**: `src/domain/calculators/indicator_calculator.py`
   ```python
   INDICATORS = {
       'my_indicator': MyIndicator
   }
   ```

3. **Test**: `tests/domain/services/indicators/test_my_indicator.py`

4. **Document**: `docs/trading/INDICATORS.md`

### Add REST Endpoint

1. **Create route**: `src/api/my_routes.py`
2. **Register**: `src/api/unified_server.py`
   ```python
   app.include_router(my_router, prefix="/api/myfeature", tags=["My Feature"])
   ```
3. **Document**: `docs/api/REST.md`

### Add WebSocket Message Type

1. **Add handler**: `src/api/message_router.py`
   ```python
   async def handle_my_message(self, client_id: str, message: Dict):
       # Handle message
   ```
2. **Register**: In MessageRouter route mapping
3. **Document**: `docs/api/WEBSOCKET.md`

### Debug QuestDB Connection

```bash
# 1. Check if QuestDB is running
netstat -an | findstr "9000 8812 9009"

# 2. Check logs
# tail -f <questdb_root>/log/questdb.log  # Linux/Mac
type <questdb_root>\log\questdb.log  # Windows

# 3. Restart QuestDB
python database/questdb/install_questdb.py

# 4. Test connection
psql -h localhost -p 8812 -U admin -d qdb
```

### Run Tests

```bash
# All tests
pytest

# Specific layer
pytest tests/domain/

# Specific type
pytest -m unit
pytest -m integration

# With coverage
pytest --cov=src --cov-report=html
```

## 🏗️ Architecture (Critical Concepts)

### Layered Architecture

```
API Layer           → unified_server.py (FastAPI + WebSocket)
Application Layer   → execution_controller.py (State Machine)
Domain Layer        → StreamingIndicatorEngine, StrategyManager
Infrastructure      → QuestDB, MEXC, Container (DI)
Core               → EventBus, Logger, Config
```

**Rule**: Each layer depends only on layers below. No circular dependencies.

### Event-Driven Communication

**ALL component communication goes through EventBus** (pub/sub pattern).

```python
# Subscribe
await event_bus.subscribe("market_data", handle_market_data)

# Publish
await event_bus.publish("market_data", data)
```

**Common Topics**:
- `market_data` - New price tick
- `indicator_updated` - Indicator calculated
- `signal_generated` - Strategy signal
- `order_created` - Order placed
- `position_updated` - Position changed

**Why EventBus**: Loose coupling, testability, replay ability for debugging.

### Dependency Injection

**Container** (`src/infrastructure/container.py`) is a **pure composition root**.

**RULES**:
- ✅ Constructor injection ONLY
- ✅ Dependencies passed through constructors
- ❌ NEVER access Container globally
- ❌ NEVER add business logic to Container

```python
# ✅ GOOD
class MyService:
    def __init__(self, db_provider: IDatabase):
        self.db = db_provider

# Container composes:
db = QuestDBProvider(...)
service = MyService(db)

# ❌ BAD
from src.infrastructure.container import container
db = container.get("database")  # NO!
```

### State Machine

**ExecutionController** manages execution lifecycle.

**States**: `IDLE` → `STARTING` → `RUNNING` → `STOPPING` → `STOPPED`

**Rule**: NEVER skip states. Always transition through intermediate states.

```python
# ✅ GOOD
await controller.start()  # IDLE → STARTING → RUNNING

# ❌ BAD
controller.state = ExecutionState.RUNNING  # Skips STARTING!
```

## 🔍 Finding Things

### "Where is X?"

| What | Where |
|------|-------|
| Market data collection | `src/data/data_collection_persistence_service.py` |
| Indicator calculation | `src/domain/services/streaming_indicator_engine.py` (PRIMARY) |
| Strategy evaluation | `src/domain/services/strategy_manager.py` |
| QuestDB writes | `src/data_feed/questdb_provider.py` |
| WebSocket server | `src/api/websocket_server.py` |
| REST endpoints | `src/api/*_routes.py` |
| State machine | `src/application/controllers/execution_controller.py` |
| Event bus | `src/core/event_bus.py` |
| DI Container | `src/infrastructure/container.py` |
| MEXC exchange | `src/infrastructure/adapters/mexc_adapter.py` |

### File Naming Patterns

- Tests: `test_*.py` or `*_test.py`
- Routes: `src/api/*_routes.py`
- Services: `src/domain/services/*_service.py` or `*_manager.py`
- Configs: `config/*.json`

### Test Location

Tests mirror src/ structure:
- `tests/domain/services/` ↔ `src/domain/services/`
- `tests/api/` ↔ `src/api/`
- `tests/infrastructure/adapters/` ↔ `src/infrastructure/adapters/`

## ⚠️ CRITICAL ANTI-PATTERNS

### NEVER DO THIS:

1. **❌ defaultdict for long-lived structures**
   ```python
   # ❌ BAD - Causes memory leak
   self.cache = defaultdict(list)  # Unbounded growth!

   # ✅ GOOD - Explicit with max size
   self.cache: Dict[str, List] = {}
   MAX_CACHE_SIZE = 1000
   ```

2. **❌ Global Container access**
   ```python
   # ❌ BAD
   from src.infrastructure.container import container
   db = container.get("database")

   # ✅ GOOD
   def __init__(self, db: IDatabase):
       self.db = db
   ```

3. **❌ Business logic in Container**
   ```python
   # ❌ BAD - Container should only assemble objects
   def create_service(self):
       service = MyService()
       service.calculate_something()  # NO!
       return service

   # ✅ GOOD - Pure composition
   def create_service(self):
       return MyService(self.db, self.config)
   ```

4. **❌ Code duplication**
   ```python
   # ❌ BAD - Same logic in 3 places
   def method1():
       result = complex_calculation()

   def method2():
       result = complex_calculation()  # Duplicate!

   # ✅ GOOD - Extract to shared function
   def shared_calculation():
       return complex_calculation()
   ```

5. **❌ Hardcoded values**
   ```python
   # ❌ BAD
   timeout = 300

   # ✅ GOOD
   timeout = config.get("timeout_seconds", 300)
   ```

6. **❌ Skip pre-change protocol**
   - ALWAYS read `.github/copilot-instructions.md` BEFORE any change
   - Analyze architecture and dependencies
   - Verify ALL assumptions
   - Report issues BEFORE implementing fixes

### ALWAYS DO THIS:

1. **✅ Read pre-change protocol first**
   - File: `.github/copilot-instructions.md`
   - Map dependencies across modules
   - Verify assumptions (no guessing!)
   - Report architectural issues BEFORE fixing

2. **✅ Explicit cleanup**
   ```python
   async def cleanup(self):
       self.cache.clear()
       self.subscriptions.clear()
       await self.connection.close()
   ```

3. **✅ Use EventBus for communication**
   ```python
   # Instead of direct calls
   await self.event_bus.publish("indicator_updated", data)
   ```

4. **✅ Add max sizes to collections**
   ```python
   self.buffer: Deque = deque(maxlen=1000)
   self.cache_ttl = 3600  # 1 hour
   ```

## 📊 Testing

### Running Tests

```bash
# All tests
pytest

# Specific layer (mirrors src/)
pytest tests/domain/
pytest tests/api/
pytest tests/infrastructure/

# Specific type
pytest -m unit          # Fast tests (<1s)
pytest -m integration   # Integration tests (<10s)
pytest -m e2e           # End-to-end tests (>10s)
pytest -m slow          # Long-running tests

# With coverage
pytest --cov=src --cov-report=html
# Open: htmlcov/index.html
```

### Test Organization

```
tests/
├── unit/           # Fast unit tests
├── integration/    # Integration tests
├── e2e/            # End-to-end tests
├── api/            # Mirrors src/api/
├── domain/         # Mirrors src/domain/
├── infrastructure/ # Mirrors src/infrastructure/
├── core/           # Mirrors src/core/
└── fixtures/       # Shared test data
```

### Writing Tests

```python
import pytest
from tests.fixtures import sample_price_data


@pytest.mark.unit
def test_indicator_calculation(sample_price_data):
    """Test RSI calculation"""
    indicator = RSIIndicator(period=14)
    result = indicator.calculate(sample_price_data)
    assert 0 <= result <= 100


@pytest.mark.integration
async def test_data_flow():
    """Test complete data collection flow"""
    # Integration test
    pass
```

## 🗄️ Database (QuestDB)

### Connection Details

- **Web UI**: http://127.0.0.1:9000
- **PostgreSQL**: localhost:8812 (admin/quest)
- **InfluxDB Line Protocol**: localhost:9009 (fast writes)
- **REST API**: http://127.0.0.1:9000/exec

### Key Tables

```sql
-- tick_prices: Market data (time-series, partitioned by day)
SELECT * FROM tick_prices WHERE symbol = 'BTC_USDT' AND timestamp > now() - interval '1' hour;

-- indicators: Calculated indicators (time-series)
SELECT * FROM indicators WHERE symbol = 'BTC_USDT' LATEST BY symbol, indicator_id;

-- data_collection_sessions: Session metadata (relational)
SELECT * FROM data_collection_sessions WHERE status = 'running';
```

### IMPORTANT Database Rules

1. **CSV storage is DEPRECATED** - Use QuestDB only
2. **QuestDB is single source of truth** - No dual storage
3. **Use ILP for writes** - Fast bulk inserts (1M+ rows/sec)
   ```python
   from questdb.ingress import Sender, Protocol

   with Sender(Protocol.Tcp, 'localhost', 9009) as sender:
       sender.row('tick_prices', ...)
   ```
4. **Use PostgreSQL protocol for queries**
   ```python
   import asyncpg

   pool = await asyncpg.create_pool(host='localhost', port=8812, ...)
   ```

### Common Queries

```sql
-- Get latest indicator values
SELECT * FROM indicators
WHERE symbol = 'BTC_USDT'
LATEST BY symbol, indicator_id;

-- Get hourly candles (sampled)
SELECT timestamp, avg(price) as price
FROM tick_prices
WHERE symbol = 'BTC_USDT'
  AND timestamp > now() - interval '24' hour
SAMPLE BY 1h;
```

## 🔧 Common Issues

### "QuestDB connection failed"

1. Check if running: `netstat -an | findstr "9000"`
2. Check logs: `<questdb_root>/log/questdb.log`
3. Restart: `python database/questdb/install_questdb.py`
4. Verify port: QuestDB Web UI should open at http://127.0.0.1:9000

### "Import error: No module named 'src'"

- **Python**: Add project root to PYTHONPATH
  ```bash
  set PYTHONPATH=%CD%  # Windows
  export PYTHONPATH=$(pwd)  # Linux/Mac
  ```
- **VSCode**: Check `settings.json`:
  ```json
  {
    "python.analysis.extraPaths": ["${workspaceFolder}"]
  }
  ```

### "EventBus not receiving events"

1. Check subscription: `await event_bus.subscribe("topic", handler)`
2. Check publishing: `await event_bus.publish("topic", data)`
3. Check handler signature: `async def handler(data: Dict)`
4. Check if handler is async (required!)

### "TypeError: Sender.__init__() takes 3 arguments (2 given)"

- **Fixed**: QuestDB v4.0.0+ requires Protocol parameter
- **Solution**: `Sender(Protocol.Tcp, host, port)` not `Sender(host, port)`
- **See**: `requirements.txt` (questdb>=4.0.0,<5.0.0)

### "Memory usage growing unboundedly"

1. Check for defaultdict in long-lived objects
2. Add max sizes: `deque(maxlen=N)`
3. Add TTLs for caches
4. Review session cleanup in execution_controller.py

## 📚 Deep Dives

For detailed architectural understanding:

- **Full architecture**: `docs/architecture/OVERVIEW.md`
- **Coding standards**: `docs/development/CODING_STANDARDS.md`
- **API specs**: `docs/api/REST.md`, `docs/api/WEBSOCKET.md`
- **Trading domain**: `docs/trading/INDICATORS.md`
- **QuestDB setup**: `docs/database/QUESTDB.md`
- **Memory management**: `docs/development/MEMORY_MANAGEMENT.md`
- **Error handling**: `docs/development/ERROR_HANDLING.md`

**Complete documentation map**: `docs/INDEX.md`

## 🎯 Current Sprint Focus

**Sprint 16 - Indicator System Consolidation**

**Goal**: Consolidate to StreamingIndicatorEngine as single source for indicator calculation.

**What this means**:
- **Primary engine**: Use `StreamingIndicatorEngine` for all indicators
- **Avoid**: Creating new indicator engines (we have 3, need to consolidate to 1)
- **CSV deprecated**: All data goes through QuestDB
- **Factory contracts**: Ensure factories respect interface contracts

**If working on indicators**: Coordinate with consolidation effort. Check `docs/STATUS.md` for current tasks.

## 🔑 Key Files to Know

**MUST READ before ANY changes**:
- `.github/copilot-instructions.md` - Mandatory pre-change protocol
- `CLAUDE.md` - Development guidelines
- `docs/STATUS.md` - Current sprint status

**Frequently referenced**:
- `src/infrastructure/container.py` - DI composition root
- `src/core/event_bus.py` - Event system
- `src/application/controllers/execution_controller.py` - State machine
- `src/domain/services/streaming_indicator_engine.py` - Primary indicator engine
- `src/api/unified_server.py` - Single FastAPI app
- `docs/development/CODING_STANDARDS.md` - Code quality rules

## 💡 Pro Tips

1. **Use git grep**: Faster than Grep tool for simple searches
   ```bash
   git grep "ClassName" -- "*.py"
   ```

2. **Check recent changes**: Understand context
   ```bash
   git log --oneline -10
   git show HEAD
   ```

3. **Verify assumptions**: Use Read tool to check files before changing

4. **Test incrementally**: Don't batch changes, test each one

5. **Update docs**: Change code = update relevant docs

---

**This is your single source of truth. When in doubt, refer to this file first.**

**Last Updated**: 2025-10-28
**Project**: FX Cryptocurrency Trading System
**Sprint**: 16 - Indicator System Consolidation
