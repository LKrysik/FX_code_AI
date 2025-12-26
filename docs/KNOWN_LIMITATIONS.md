# Known Limitations

**Last Updated:** 2025-12-25

This document provides an honest assessment of what works, what doesn't, and what's planned. Read this before building features or integrating with the system.

---

## Status Legend

| Status | Meaning |
|--------|---------|
| :white_check_mark: **WORKING** | Tested and functional |
| :warning: **PARTIAL** | Some functionality works, known issues |
| :x: **NOT WORKING** | Does not function as documented |
| :construction: **IN PROGRESS** | Currently being developed |
| :grey_question: **MOCK** | Returns fake/hardcoded data |

---

## Core Features Status

### Trading Engine

| Feature | Status | Notes |
|---------|--------|-------|
| Live Trading (MEXC) | :x: **NOT WORKING** | Order execution broken |
| Paper Trading | :x: **NOT WORKING** | Execution flow incomplete |
| Backtesting | :x: **NOT WORKING** | Strategy evaluation broken |
| Session Management | :warning: **PARTIAL** | Start/stop works, results don't |

**Impact:** The primary purpose of this system (trading) is currently non-functional.

---

### Strategy Builder

| Feature | Status | Notes |
|---------|--------|-------|
| Visual Canvas | :white_check_mark: **WORKING** | Drag-drop, connect nodes |
| Node Library | :white_check_mark: **WORKING** | All node types available |
| Save/Load Blueprints | :white_check_mark: **WORKING** | Via API to storage |
| Validation | :warning: **PARTIAL** | Structure validation works, logic validation incomplete |
| **Run Button** | :x: **NOT WORKING** | Only logs to console, no execution |
| Real-time Indicators | :x: **NOT WORKING** | Displays mock values |

**What you CAN do:** Design and save strategy diagrams.
**What you CANNOT do:** Execute strategies, see live indicator values.

---

### Indicators

| Indicator | Status | Notes |
|-----------|--------|-------|
| VWAP | :grey_question: **MOCK** | Returns hardcoded values |
| TWPA | :grey_question: **MOCK** | Returns hardcoded values |
| RSI | :grey_question: **MOCK** | Returns hardcoded values |
| MACD | :grey_question: **MOCK** | Returns hardcoded values |
| Volume Surge | :grey_question: **MOCK** | Returns hardcoded values |
| Price Velocity | :warning: **PARTIAL** | Basic calculation exists |
| max_price/min_price | :white_check_mark: **WORKING** | Aggregation functions work |
| sum_volume/avg_volume | :white_check_mark: **WORKING** | Aggregation functions work |

**Critical:** Documentation describes indicators as if they work. They don't. Most return mock data.

---

### UI Components

| Component | Status | Notes |
|-----------|--------|-------|
| Dashboard | :warning: **PARTIAL** | Layout works, data population broken |
| Strategy Builder | :warning: **PARTIAL** | See above section |
| Session Controls | :warning: **PARTIAL** | UI works, backend integration broken |
| Results Display | :x: **NOT WORKING** | No results to display |
| Trading History | :x: **NOT WORKING** | No trades executed |

---

### API Endpoints

| Endpoint | Status | Notes |
|----------|--------|-------|
| `/health` | :white_check_mark: **WORKING** | Health check |
| `/auth/login` | :white_check_mark: **WORKING** | JWT authentication |
| `/api/strategies` | :white_check_mark: **WORKING** | CRUD operations |
| `/api/sessions` | :warning: **PARTIAL** | Create works, results don't |
| WebSocket subscriptions | :warning: **PARTIAL** | Connection works, data is mock |

---

## Infrastructure Status

### Database (QuestDB)

| Feature | Status | Notes |
|---------|--------|-------|
| Connection | :white_check_mark: **WORKING** | Connection pooling works |
| Schema | :white_check_mark: **WORKING** | Tables exist |
| Data Ingestion | :warning: **PARTIAL** | Some data types work |
| Query Performance | :grey_question: **UNTESTED** | No real load testing |

---

### External Integrations

| Integration | Status | Notes |
|-------------|--------|-------|
| MEXC WebSocket | :warning: **PARTIAL** | Connects, data parsing issues |
| MEXC REST API | :warning: **PARTIAL** | Auth works, trading endpoints untested |
| Redis | :x: **UNAVAILABLE** | Not available on Windows without Docker |

**Redis Impact:** Without Redis:
- No computation caching (performance impact)
- No session persistence (restart = lose all sessions)
- No multi-instance coordination

---

## Known Bugs

### Critical

1. **Trading engine does not execute trades** - All trading modes (live, paper, backtest) are non-functional.

2. **Indicators return mock values** - RSI, MACD, VWAP documented as functional but return hardcoded data.

3. **Session results not persisted** - Completing a session loses all results.

### High Priority

4. **Race conditions in EventBus** - Concurrent operations can cause unpredictable behavior.

5. **WebSocket reconnection loses state** - No message deduplication or recovery.

6. **Strategy evaluation incomplete** - AND/OR conditions, duration modifiers not fully implemented.

### Medium Priority

7. **Frontend test failures** - Multiple E2E tests failing (see `frontend/test-results/`).

8. **Encoding issues in docs** - Some files had character corruption (fixed 2025-12-25).

---

## Platform Constraints

| Constraint | Impact | Workaround |
|------------|--------|------------|
| Windows without Docker | No Redis available | Use degraded mode (no caching) |
| MEXC only | Single exchange | Multi-exchange planned (P2) |
| No mobile support | Desktop only | Responsive design planned |

---

## What's Actually Usable Today

### YES - You CAN:
- Set up the development environment
- Login with JWT authentication
- Design strategies visually in Strategy Builder
- Save/load strategy blueprints
- View the dashboard layout
- Connect to MEXC WebSocket (receive raw data)

### NO - You CANNOT:
- Execute any trading (live, paper, or backtest)
- See real indicator calculations
- Get trading signals
- View trading results
- Use Redis-dependent features on Windows

---

## Planned Fixes (Priority Order)

1. **P0: Fix Trading Engine** - Enable at least paper trading
2. **P0: Fix Strategy Evaluation** - Make conditions actually evaluate
3. **P1: Replace Mock Indicators** - Implement real VWAP, RSI, MACD
4. **P1: Fix UI Components** - Connect frontend to working backend
5. **P2: Add Redis Support** - Enable caching and persistence

---

## How to Report Issues

When reporting bugs, include:
1. Steps to reproduce
2. Expected vs actual behavior
3. Console/log output
4. Environment (OS, Python version, Node version)

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-25 | Initial document created |

---

*This document is updated when significant bugs are found or fixed. Check git history for changes.*
