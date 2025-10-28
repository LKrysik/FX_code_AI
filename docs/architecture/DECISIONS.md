# Architecture Decision Records (ADR)

This document contains all architectural decisions made for the FX Crypto Trading System. Each decision includes context, options considered, and consequences.

## ADR Template

**ADR-[NUMBER]: [TITLE]**
**Date**: YYYY-MM-DD
**Status**: PROPOSED / ACCEPTED / DEPRECATED / SUPERSEDED

### Context
[Describe the context and problem being solved]

### Decision
[What was decided and why]

### Options Considered
- **Option 1**: [Description and why rejected]
- **Option 2**: [Description and why rejected]
- **Chosen Option**: [Why this was selected]

### Consequences
**Positive:**
- [List benefits]

**Negative:**
- [List drawbacks]

**Risks:**
- [List potential risks and mitigation]

---

## ADR-001: 5-Section Strategy State Machine Architecture
**Date**: 2025-01-15
**Status**: ACCEPTED

### Context
The system needs to implement complex trading strategy execution with 5 distinct sections (S1/Z1/O1/ZE1/E1) that must work in an event-driven manner with parallel processing capabilities. The state machine must handle emergency overrides and maintain data integrity throughout the execution lifecycle.

### Decision
Implement a finite state machine with the following states and transitions:
- **IDLE**: Waiting for market data
- **SIGNAL_DETECTED**: S1 conditions met, strategy activated
- **POSITION_OPEN**: Order executed, monitoring for exit conditions
- **COMPLETED**: Strategy finished (profit/loss taken or emergency exit)

Emergency conditions (E1) can interrupt from any state with highest priority.

### Options Considered
- **Event Sourcing**: Complex event replay capabilities but overkill for trading logic
- **Simple Conditional Logic**: Easy to implement but hard to maintain for complex workflows
- **Chosen: Finite State Machine**: Clear state transitions, easy to test and debug

### Consequences
**Positive:**
- Clear separation of concerns between strategy sections
- Easy to implement parallel execution (ZE1/TP/SL simultaneous)
- Emergency override logic is explicit and testable
- State transitions are logged for debugging

**Negative:**
- Increased complexity in state management code
- More boilerplate code for state transitions
- Learning curve for new developers

**Risks:**
- Race conditions in parallel execution (mitigated by proper locking)
- State corruption on system crashes (mitigated by state persistence)

---

## ADR-002: File-Based Configuration Storage
**Date**: 2025-01-16
**Status**: ACCEPTED

### Context
The system needs persistent storage for trading strategies and indicator variants. Data must be human-readable, version controllable, and survive system restarts.

### Decision
Use JSON files stored in directory structure:
- `config/strategies/` - Trading strategies
- `config/indicators/` - Indicator variants organized by type

Each entity gets a UUID for unique identification.

### Options Considered
- **Database (PostgreSQL)**: ACID compliance but adds complexity and dependencies
- **YAML Files**: Human-readable but less structured than JSON
- **Chosen: JSON Files**: Balance of human readability, structure, and simplicity

### Consequences
**Positive:**
- No database dependency reduces operational complexity
- Files can be version controlled and diffed
- Easy backup and restore procedures
- Human-readable configuration

**Negative:**
- File system operations slower than database queries
- Potential concurrency issues with multiple processes
- No built-in transactions or rollback

**Risks:**
- File corruption (mitigated by validation on load)
- Concurrent access conflicts (mitigated by file locking)

---

## ADR-003: Comprehensive Quality Assurance Framework
**Date**: 2025-01-17
**Status**: ACCEPTED

### Context
Critical trading system bugs have caused functionality to appear working in tests but fail in real usage. Need systematic approach to ensure business logic correctness and prevent regressions.

### Decision
Implement 4-layer testing strategy:
1. **Business Logic Tests**: End-to-end workflow validation
2. **Frontend Action Tests**: 100% coverage of money-related UI actions
3. **Data Integrity Tests**: File corruption and concurrent access validation
4. **Performance Tests**: Benchmarks for critical operations

All tests must pass before deployment with evidence documentation.

### Options Considered
- **Minimal Unit Testing**: Fast but misses integration issues
- **Full E2E Only**: Catches real issues but slow and brittle
- **Chosen: Layered Approach**: Balances speed, coverage, and reliability

### Consequences
**Positive:**
- Catches business logic errors missed by unit tests
- Prevents UI bugs that cost real money
- Provides confidence in system reliability
- Creates audit trail for compliance

**Negative:**
- Increases development time (30-40% overhead)
- Requires test maintenance with code changes
- CI/CD pipeline becomes more complex

**Risks:**
- Test suite becomes too slow (mitigated by parallel execution)
- False confidence from passing tests (mitigated by business logic focus)

---

## ADR-004: Requirements Engineering Framework
**Date**: 2025-01-18
**Status**: ACCEPTED

### Context
User requirements (USER_REC_01, USER_REC_02) need systematic translation into implementable tasks with full traceability and validation.

### Decision
Implement 3-layer requirements framework:
1. **BUSINESS_GOALS.md**: Translation of USER_REC into business objectives
2. **REQUIREMENT_TRACEABILITY.md**: Mapping requirements to tasks and tests
3. **Quality Gates**: Validation that requirements are fully implemented

### Options Considered
- **Direct Implementation**: Fast but loses requirement context
- **Heavy Documentation**: Complete traceability but slows development
- **Chosen: Balanced Framework**: Essential traceability without overhead

### Consequences
**Positive:**
- Clear mapping from requirements to implementation
- Gap analysis prevents missed features
- Business value tracking throughout development

**Negative:**
- Additional documentation maintenance
- Potential resistance from development team

**Risks:**
- Framework becomes too rigid (mitigated by lightweight approach)
- Documentation drifts from code (mitigated by automated validation)

---

## ADR-005: Indicator Calculation Cache Strategy
**Date**: 2025-01-19
**Status**: ACCEPTED

### Context
Indicator calculations are computationally expensive and may be requested multiple times for the same market data. System must handle high-frequency trading scenarios.

### Decision
Implement Redis-based cache with:
- Time-bucketed keys (60-second granularity)
- TTL based on indicator type (short-term for volatile, longer for stable)
- Cache warming for frequently used indicators

### Options Considered
- **In-Memory Cache**: Fast but lost on restart
- **File-Based Cache**: Persistent but slow I/O
- **Chosen: Redis Cache**: Performance, persistence, and scalability

### Consequences
**Positive:**
- Significant performance improvement for repeated calculations
- Scales horizontally with Redis cluster
- Reduces computational load on strategy execution

**Negative:**
- Additional infrastructure dependency
- Cache invalidation complexity
- Memory usage for cache storage

**Risks:**
- Cache inconsistency (mitigated by proper invalidation)
- Redis failure impact (mitigated by fallback to direct calculation)