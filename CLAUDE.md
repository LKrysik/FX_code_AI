# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

### Running the Application

**Backend (Python/FastAPI):**
```bash
# Activate virtual environment (if needed)
.venv\Scripts\activate

# Start unified server (REST + WebSocket on port 8080)
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload
```

**Frontend (Next.js 14):**
```bash
cd frontend
npm run dev  # Runs on port 3000
```

**Full Stack (PowerShell script):**
```powershell
.\start_all.ps1  # Starts QuestDB, backend, and frontend
```

### Database Setup

**QuestDB (Primary Time-Series Database):**
```bash
# Install and configure
python database/questdb/install_questdb.py

# Connection details:
# - Web UI: http://127.0.0.1:9000
# - PostgreSQL: localhost:8812 (user: admin, password: quest)
# - InfluxDB Line Protocol: localhost:9009 (fast writes)
# - REST API: http://127.0.0.1:9000/exec
```

**Why QuestDB?** 10x faster ingestion than TimescaleDB (1M+ rows/sec), 4x less memory, native Windows support, no Docker/WSL2 required.

### Environment Configuration

**Frontend (.env.local):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8080/ws
```

**Backend:** Uses `src/infrastructure/config/settings.py` (Pydantic settings) with environment variable overrides or `config.json`.

## Architecture Overview

### High-Level Design

This is a **layered, event-driven architecture** for cryptocurrency trading:

```
┌─────────────────────────────────────┐
│    API Layer (FastAPI + WebSocket)  │ ← unified_server.py (single server)
├─────────────────────────────────────┤
│  Application Layer (Controllers)    │ ← execution_controller.py (state machine)
├─────────────────────────────────────┤
│   Domain Layer (Business Logic)     │ ← StreamingIndicatorEngine, StrategyManager
├─────────────────────────────────────┤
│ Infrastructure (Adapters, DB, APIs) │ ← QuestDB, MEXC, Container (DI)
├─────────────────────────────────────┤
│   Core (EventBus, Logger, Config)   │ ← Central async event bus
└─────────────────────────────────────┘
```

**Communication:** Components communicate via **EventBus** (publish/subscribe pattern) to maintain loose coupling. Example: market data arrives → EventBus publishes "market_data" → Indicator Engine subscribes → calculates indicators → publishes "indicator_updated" → Strategy Manager subscribes → evaluates signals.

### Key Patterns

1. **Dependency Injection Container** (`src/infrastructure/container.py`)
   - Pure composition root - NO global access, NO service locator
   - Constructor injection only
   - Factories for conditional object creation
   - CRITICAL: Never add business logic to Container

2. **Event-Driven Architecture** (`src/core/event_bus.py`)
   - Central async event bus for component communication
   - Topics: market_data, indicator_updated, signal_generated, order_created, etc.
   - Used everywhere: data collection, backtesting, live trading

3. **State Machine** (`src/application/controllers/execution_controller.py`)
   - States: IDLE → STARTING → RUNNING → STOPPING → STOPPED
   - Manages execution lifecycle for backtest/live/collect modes
   - Clear state transitions with validation

4. **Strategy Pattern**
   - Interchangeable data providers: `IMarketDataProvider` (live vs historical)
   - Interchangeable execution modes: `IExecutionDataSource`

## Critical Components

### API Layer

**Unified Server** (`src/api/unified_server.py`)
- Single FastAPI application combining REST and WebSocket
- Factory function: `create_unified_app()` with lifespan management
- Port 8080, handles CORS, serves both protocols

**WebSocket Server** (`src/api/websocket_server.py`)
- `ConnectionManager` - tracks active connections
- `MessageRouter` - routes by message type
- `AuthHandler` - JWT authentication (access + refresh tokens)
- `SubscriptionManager` - client subscriptions to data streams
- `EventBridge` - bridges EventBus to WebSocket broadcasts

### Application Layer

**ExecutionController** (`src/application/controllers/execution_controller.py`)
- Core state machine managing execution lifecycle
- Modes: backtest, live trading, paper trading, data collection
- Handles session creation, data flow, cleanup
- CRITICAL: Memory leak prevention - explicit cleanup of all structures

**UnifiedTradingController** (`src/application/controllers/unified_trading_controller.py`)
- High-level orchestration layer
- Coordinates between execution controller, strategy manager, risk manager
- Manages wallet and position tracking

### Domain Layer

**StreamingIndicatorEngine** (`src/domain/services/streaming_indicator_engine.py`)
- **Most critical component** for real-time indicator calculation
- Incremental calculation (O(1) for most indicators)
- Ring buffer per symbol for windowed calculations
- Indicator variants: same base indicator with different parameters
- Shared instances across strategies (reduces duplicate calculations)
- Publishes to EventBus: "indicator_updated" events

**Key Indicators:**
- **TWPA** (Time-Weighted Price Average) - Core price aggregation
- **Velocity** - Price change rate between windows
- **Volume_Surge** - Volume anomaly detection
- All use **(t1, t2)** window semantics where t1 > t2 (e.g., `(300, 0)` = "last 5 minutes")

**StrategyManager** (`src/domain/services/strategy_manager.py`)
- Strategy lifecycle and activation
- Evaluates conditions, generates signals
- Integrates with indicator engine

**RiskManager** (`src/domain/services/risk_manager.py`)
- Budget allocation per symbol
- Risk assessment before order creation
- Position size limits

### Data Flow Patterns

#### Data Collection
```
User starts collection → POST /sessions/start
  → UnifiedTradingController.start_data_collection()
  → Creates session in QuestDB (data_collection_sessions)
  → Initializes MarketDataProviderAdapter
  → Streams market data via EventBus ("market_data" events)
  → DataCollectionPersistenceService subscribes
  → Writes batches to QuestDB (tick_prices table)
  → WebSocket broadcasts progress to UI
  → POST /sessions/stop finalizes session
```

#### Backtesting
```
User selects historical session → GET /api/data-collection/sessions
  → POST /sessions/start with session_id
  → Queries QuestDB: tick_prices WHERE session_id = 'X'
  → Streams data with acceleration_factor for timing
  → Indicators calculate incrementally
  → Strategy evaluates, generates signals
  → Orders tracked (simulated)
  → Results saved to backtest_results/
```

#### Live Trading
```
User starts live trading → POST /sessions/start
  → MEXC adapter connects to exchange
  → Real-time market data via WebSocket
  → Indicators update incrementally
  → Strategy evaluates conditions
  → Signals → RiskManager → OrderManager
  → Orders submitted to MEXC
  → Position tracking in real-time
```

## Database Architecture

### QuestDB as Single Source of Truth

**CRITICAL ARCHITECTURAL DECISION:** CSV/file storage is being phased out. QuestDB is now the primary database:
- Data collection writes **directly** to QuestDB (no CSV fallback)
- Backtests read **exclusively** from QuestDB
- Session metadata only in QuestDB
- **Strategy storage (2025-11-05):** QuestDB only (file-based fallback removed)

**Why this matters:** Do not add CSV/file-related code. The system is moving away from dual-storage complexity.

### Key Tables

**tick_prices** (time-series data):
```sql
CREATE TABLE tick_prices (
    session_id SYMBOL,
    symbol SYMBOL,
    timestamp TIMESTAMP,
    price DOUBLE,
    volume DOUBLE,
    quote_volume DOUBLE
) timestamp(timestamp) PARTITION BY DAY WAL;
```

**indicators** (calculated indicators):
```sql
CREATE TABLE indicators (
    symbol SYMBOL,
    indicator_id SYMBOL,
    timestamp TIMESTAMP,
    value DOUBLE,
    confidence DOUBLE,
    metadata STRING
) timestamp(timestamp) PARTITION BY DAY WAL;
```

**data_collection_sessions** (session metadata):
```sql
CREATE TABLE data_collection_sessions (
    session_id STRING,
    symbols STRING,
    data_types STRING,
    status STRING,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    records_collected INT,
    prices_count INT,
    orderbook_count INT
);
```

**strategies** (trading strategy configuration):
```sql
CREATE TABLE strategies (
    id STRING,
    strategy_name STRING,
    description STRING,
    direction STRING,
    enabled BOOLEAN,
    strategy_json STRING,
    author STRING,
    category STRING,
    tags STRING,
    template_id STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_activated_at TIMESTAMP,
    is_deleted BOOLEAN,
    deleted_at TIMESTAMP
);
```

**Migration:** Use `scripts/migrate_strategy_json_to_questdb.py` to migrate from legacy JSON files.

### Accessing QuestDB

**Fast Writes (InfluxDB Line Protocol):**
```python
from questdb.ingress import Sender, Protocol

with Sender(Protocol.Tcp, 'localhost', 9009) as sender:
    sender.row('tick_prices',
               symbols={'session_id': 'session_123', 'symbol': 'BTC_USDT'},
               columns={'price': 50000, 'volume': 1000},
               at=TimestampNanos(timestamp_ns))
```

**Queries (PostgreSQL Protocol):**
```python
import asyncpg

pool = await asyncpg.create_pool(host='localhost', port=8812,
                                 user='admin', password='quest', database='qdb')
async with pool.acquire() as conn:
    rows = await conn.fetch("SELECT * FROM tick_prices WHERE symbol = $1", 'BTC_USDT')
```

## Development Protocols

### MANDATORY Pre-Change Protocol

From `.github/copilot-instructions.md` - **MUST follow for ALL code changes:**

1. **Detailed Architecture Analysis**
   - Read all relevant source files
   - Document system design and architectural principles
   - Identify layers and responsibilities

2. **Impact Assessment**
   - Analyze effects on entire program
   - Trace dependencies across modules
   - Map related objects and data flow

3. **Assumption Verification**
   - **NEVER assume without validation**
   - Challenge every premise
   - Document verification steps

4. **Proposal Development**
   - Justify changes in full system context
   - **Eliminate code duplication** (single source of truth)
   - **NO backward compatibility workarounds** - create correct solution immediately
   - Avoid alternative methods that do the same thing

5. **Issue Discovery & Reporting**
   - Report architectural flaws, inconsistencies, problems BEFORE implementing
   - Wait for user acknowledgment
   - Provide detailed justification in program context

6. **Implementation**
   - Targeted, well-reasoned changes
   - Ensure architectural coherence
   - Test each change individually

### Critical Anti-Patterns

**Memory Leak Prevention (CRITICAL):**
- **NEVER use defaultdict** for long-lived structures (causes unbounded growth)
- Explicit cache creation with business logic control
- Add max sizes and TTLs to ALL dicts and queues
- Use WeakReferences for event handlers where appropriate
- Explicit cleanup in session lifecycle

**Architecture Violations:**
- **NO global Container access** - dependency injection only, pass through constructors
- **NO business logic in Container** - pure assembly of objects only
- **NO hardcoded values** - all parameters from configuration
- **NO code duplication** - extract to shared functions/classes
- **NO backward compatibility hacks** - fix the root cause

**Testing:**
- **Use unified E2E test suite** - 224 automated tests (213 API + 9 Frontend + 2 Integration)
- **Single test launcher**: `python run_tests.py` (see `README_TESTS.md` and `QUICK_START_TESTS.md`)
- **Test structure**: `tests_e2e/` directory with API, frontend (Playwright), and integration tests
- **Prerequisites**: Backend and frontend must be running (use `.\start_all.ps1`)
- **Options**: `--api`, `--frontend`, `--integration`, `--fast`, `--coverage`, `--html-report`, `--verbose`
- **Complete documentation**: `README_TESTS.md` (full guide) and `QUICK_START_TESTS.md` (3-minute setup)

## Current Sprint Status

**Sprint 16 - Indicator System Consolidation** (In Progress as of 2025-11-02)

**Critical Issues Being Addressed:**
1. Duplicate calculation logic across indicator engines
2. ✅ **COMPLETED**: UnifiedIndicatorEngine code (2,000+ lines) has been removed from codebase
3. CSV/Database migration to QuestDB (tick_prices, data_collection_sessions)
4. Factory contract violations
5. Memory leak risks in long-lived caches

**What This Means:**
- Focus is on **consolidating** to StreamingIndicatorEngine as single source
- Removing duplicate code paths ✅ (UnifiedIndicatorEngine deleted)
- Migrating from CSV to QuestDB for data storage
- If working on indicators, coordinate with consolidation effort

**Recent Completions:**
- ✅ UnifiedIndicatorEngine and StreamingIndicatorEngineAdapter removed
- ✅ Migration 003 implemented (tick_prices, tick_orderbook, data_collection_sessions, aggregated_ohlcv)
- ✅ Documentation updated to reflect current database schema

## Exchange Integration

**MEXC Adapter** (`src/infrastructure/adapters/mexc_adapter.py`)
- Real trading on MEXC futures
- Uses deals API and order book (NOT tickers)
- Paper trading variant: `mexc_paper_adapter.py`

**Important:** Exchange connections go through adapter pattern. Never call exchange APIs directly from domain layer.

## Common Development Tasks

### Adding a New Indicator

1. **Create indicator implementation** in `src/domain/services/indicators/`
2. **Register in IndicatorCalculator** (`src/domain/calculators/indicator_calculator.py`)
3. **Add to indicator catalog** (`docs/trading/INDICATORS.md`)
4. **Use via StreamingIndicatorEngine** - create variant:
   ```python
   streaming_engine.create_variant(
       name="MyIndicator_5min",
       base_indicator_type="MyIndicator",
       variant_type="price",
       parameters={"t1": 300, "t2": 0},
       created_by="user"
   )
   ```

### Adding a New REST Endpoint

1. **Create route handler** in appropriate file in `src/api/` (e.g., `indicators_routes.py`)
2. **Register in unified_server.py**:
   ```python
   app.include_router(my_router, prefix="/api/myfeature", tags=["My Feature"])
   ```
3. **Update API documentation** in `docs/api/REST.md`

### Adding a New WebSocket Message Type

1. **Add handler** in `src/api/message_router.py`:
   ```python
   async def handle_my_message(self, client_id: str, message: Dict[str, Any]):
       # Implementation
   ```
2. **Register in route mapping** in MessageRouter
3. **Document in** `docs/api/WEBSOCKET.md`

## Support and Documentation

**Key Documentation Files:**
- `docs/INDEX.md` - Complete documentation map
- `docs/STATUS.md` - Current sprint status and priorities
- `docs/ROADMAP.md` - Feature roadmap
- `docs/development/CODING_STANDARDS.md` - Code quality standards
- `docs/architecture/CONTAINER.md` - DI patterns
- `docs/database/QUESTDB.md` - Complete QuestDB guide
- `docs/api/REST.md` - REST API specification
- `docs/api/WEBSOCKET.md` - WebSocket protocol
- `docs/trading/INDICATORS.md` - Indicator catalog

**Getting Help:**
- Check existing documentation first
- Review copilot-instructions.md for protocols
- Examine similar existing implementations
- Trace data flow through EventBus subscriptions
