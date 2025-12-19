# FX Agent AI - Product Backlog

> Source: Consolidated from docs/ROADMAP.md + docs/IDEAS.md
> Generated: 2025-12-19
> Format: BMAD-compatible for AI agent consumption

---

## Executive Summary

**Product Vision:** Building TOOLS for traders to create their own strategies, not ready-made solutions.

**Current State:** Brownfield project with core functionality partially working. Trading/backtesting needs fixes. UI has broken components.

**Tech Stack:** Python FastAPI + Next.js 14 + QuestDB

---

## Priority Matrix

| Priority | Category | Description |
|----------|----------|-------------|
| **P0** | Critical | Blocking core functionality |
| **P1** | High | High value + Low complexity |
| **P2** | Medium | High value + Higher complexity |
| **P3** | Low | Future consideration |
| **DONE** | Completed | Already implemented |

---

## P0: Critical - Core Functionality Fixes

### CORE-01: Fix Trading Engine
**Status:** NOT WORKING
**Problem:** Neither live nor backtesting functions properly
**Impact:** System is unusable for its primary purpose
**Components:**
- Backtest execution flow
- Paper trading execution
- Live trading on MEXC
**Dependencies:** Strategy evaluation, order execution, position management

### CORE-02: Fix Strategy Builder
**Status:** PARTIALLY BROKEN
**Problem:** Both frontend and backend may be faulty
**Components:**
- `StrategyBuilder5Section.tsx` - 5-section condition system
- Backend strategy evaluation engine
- DSL parsing and validation
**Dependencies:** Indicator engine, condition evaluation

### CORE-03: Fix UI Components
**Status:** BROKEN
**Problem:** Large parts of the interface don't work
**Areas:** Dashboard, session management, results display

---

## P1: High Priority - Indicators & Detection

### IND-01: Implement Real Indicator Calculations
**Status:** MOCKS EXIST
**Problem:** Many indicators (RSI, MACD) return hardcoded mock values
**Solution:** Replace mocks with real mathematical algorithms from `INDICATORS_TO_IMPLEMENT.md`
**Groups:**
- **GROUP A (Priority 1):** `max_price()`, `min_price()`, `first_price()`, `last_price()`, `sum_volume()`, `avg_volume()`, `count_deals()`, `TWPA()`, `VWAP()`
- **GROUP B (Priority 2):** `Velocity()`, `Volume_Surge()`, `Volume_Concentration()`
**Reference:** `docs/trading/INDICATORS_TO_IMPLEMENT.md`

### IND-02: Better Pump Detection Indicators (from IDEAS I1)
**Problem:** PRICE_VELOCITY is basic, need more signals
**New Indicators:**
- Volume anomaly detection (sudden volume spike)
- Bid/Ask imbalance (more buyers than sellers)
- Trade clustering (sudden transaction density)
**Value:** Earlier pump detection, fewer false alarms

### IND-03: Refactor `_calculate_parametric_measure`
**Problem:** One giant method, hard to test and modify
**Solution:** Split into dedicated functions: `_compute_twpa`, `_compute_velocity`, etc.
**Benefit:** Easier testing, maintenance, and extension

---

## P1: High Priority - User Experience

### UX-01: Alerting/Notifications (from IDEAS I2)
**Problem:** User must watch screen to see signals
**Solution:**
- Push notifications via Telegram/Discord
- Email alerts
- Browser sound alerts
**Value:** Trader won't miss opportunities

### UX-02: Real-time Signals Dashboard (from IDEAS I3)
**Problem:** No "what's happening now" market view
**Solution:**
- Active signals list
- Symbol ranking by "pump probability"
- Activity heatmap
**Value:** Faster trader decisions

### UX-03: Strategy Templates (from IDEAS I4)
**Problem:** User doesn't know how to start
**Solution:**
- "Flash Pump Strategy" - ready template
- "Conservative Long" - safe strategy
- Clone and modify capability
**Value:** Lower entry barrier

---

## P2: Medium Priority - Architecture & Performance

### ARCH-01: Refactor WebSocketAPIServer
**Problem:** Monolithic class doing everything
**Solution:** Split into specialized services:
- `SessionManager` - session lifecycle (start, stop)
- `StrategyManager` - strategy configurations (CRUD)
- `ResultsProvider` - results and statistics
**Benefit:** Simpler code, independent development

### ARCH-02: State Management & Persistence
**Problem:** Server restart loses all session data
**Solution:**
- State persistence with Redis (in-memory DB)
- Store active sessions and temporary states (e.g., `duration` conditions)
- Multi-tenant isolation (separate namespaces per user)
**Constraint:** Redis currently unavailable on Windows without Docker

### ARCH-03: Fix Concurrency Issues
**Problem:** Race conditions in EventBus and ConnectionManager
**Solution:** Audit code, introduce `asyncio.Lock` in critical sections
**Risk:** Unpredictable behavior, data corruption

### ARCH-04: Async I/O Operations
**Problem:** Synchronous I/O blocks the application
**Solution:** Replace with async equivalents (`aiofiles`)
**Benefit:** System stays responsive under load

### PERF-01: Computation Cache Layer
**Problem:** Expensive indicator calculations repeated
**Example:** 10 strategies using `RSI(14)` for `BTC_USDT` = 10x computation
**Solution:** Redis cache layer for calculation results
**Key Format:** `"TWPA:BTC_USDT:1m:300:0:{timestamp_bucket}"`

---

## P2: Medium Priority - Features

### FEAT-01: Multi-Exchange Support (from IDEAS I5)
**Current:** MEXC only
**Target:** Binance, Bybit, OKX
**Complexity:** Different APIs, different data formats
**Value:** More opportunities, cross-exchange arbitrage

### FEAT-02: Backtesting Visualization (from IDEAS I6)
**Problem:** Backtest results are just numbers
**Solution:**
- Equity curve chart
- Entry/exit markers on price chart
- Drawdown analysis
**Value:** Better strategy understanding

### FEAT-03: Position Sizing Based on Conviction (from IDEAS I7)
**Problem:** Fixed position size
**Solution:**
- Larger position when signal stronger
- Volatility-based scaling
**Value:** Better capital utilization

### FEAT-04: Trailing Stop-Loss (from IDEAS I8)
**Problem:** Only fixed stop-loss
**Solution:**
- Stop follows price
- ATR-based trailing
**Value:** Profit protection in trends

### FEAT-05: Strategy Performance Analytics (from IDEAS I9)
**Problem:** No "which strategy works better" analysis
**Solution:**
- Sharpe ratio, Sortino ratio
- Win rate per symbol
- Market correlation
**Value:** Strategy portfolio optimization

---

## P2: Medium Priority - Security & Reliability

### SEC-01: JWT Authentication
**Status:** Partially implemented
**Requirement:** Token-based access to API
**Components:** PyJWT, bcrypt (already in stack)

### SEC-02: Secrets Management (Vault)
**Problem:** API keys in config files
**Solution:** HashiCorp Vault for secure storage
**Priority:** Required for production

### REL-01: Monitoring & Observability
**Solution:**
- Prometheus integration for metrics
- Distributed tracing for request tracking
**Metrics:** Graph engine performance, cache-ratio, latencies

---

## P3: Low Priority - Future Consideration

### FUTURE-01: Machine Learning Signals (from IDEAS I10)
**Complexity:** HIGH
**Risk:** Overfitting, hard to explain
**Consider when:** Basic indicators prove insufficient

### FUTURE-02: Social/Copy Trading (from IDEAS I11)
**Complexity:** HIGH (requires users, UI, business model)
**Consider when:** Product has stable user base

### FUTURE-03: API for External Bots (from IDEAS I12)
**Complexity:** MEDIUM
**Consider when:** Users with their own systems exist

### FUTURE-04: Mobile App (from IDEAS I13)
**Complexity:** HIGH
**Consider when:** Web app is stable, demand exists

---

## DONE: Completed Items

### DONE-01: Time Window Semantics (Sprint 14)
**Problem:** `(t1, t2)` system was confusing
**Solution:** Standardized to `t1` = seconds back for start, `t2` for end
**Example:** `TWPA(300, 0)` = "from 5 minutes ago to now"
**Docs:** `docs/trading/INDICATORS.md`, `CLAUDE.md`

### DONE-02: DAG Dependency Risks
**Solution:** Circuit breaker pattern with 5s timeout, graceful degradation, fallback mechanisms

### DONE-03: Time-Bucketed Cache Keys
**Solution:** 60s granularity timestamp buckets
**Format:** `"TWPA:BTC_USDT:1m:300:0:1727209200"`

---

## Rejected Ideas

### X1: Blockchain/DEX Integration
**Reason:** Complicates architecture, CEX (MEXC) sufficient for MVP
**May return:** When CEX lose popularity

### X2: On-Premise Deployment
**Reason:** Cloud-first allows faster iterations
**May return:** When enterprise clients exist

---

## Known Constraints

| Constraint | Impact | Workaround |
|------------|--------|------------|
| No Docker on Windows | Redis unavailable | Degraded state persistence |
| MEXC only | Single exchange | Plan multi-exchange (P2) |
| No E2E tests | Quality risk | Manual testing |

---

## References

| Document | Purpose |
|----------|---------|
| `docs/trading/INDICATORS.md` | Indicator specifications |
| `docs/trading/INDICATORS_TO_IMPLEMENT.md` | Implementation details |
| `docs/architecture/DECISIONS.md` | Architecture decisions |
| `docs/development/CODING_STANDARDS.md` | Code standards |
| `_bmad-output/project-context.md` | Full project context |

---

## For AI Agents

When working on this project:
1. **Always check this backlog** before starting new work
2. **P0 items are blocking** - prioritize fixes over new features
3. **Reference the constraints** - especially Redis unavailability
4. **Update status** when completing items
5. **Link PRs** to backlog items

---

*Last updated: 2025-12-19 by BMAD Document Project Workflow*
