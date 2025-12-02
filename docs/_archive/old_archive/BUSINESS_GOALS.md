# Business Goals

## GOAL_01: Indicator Calculation File Creation
**Source**: USER_REC_08 (docs/MVP.md)  
**User Value**: Generate CSV files with indicator values for analysis and verification.

**Success Criteria**:
- Files created in correct directory structure (`data/session/SYMBOL/indicators/[type]_[variant_id].csv`).
- Each file contains timestamp and value columns matching the indicator algorithm.
- Files generated during backtest and chart viewing.

**Complexity**: Medium  
**Dependencies**: Unified indicator engine.

## GOAL_02: Frontend-Backend Integration for Calculation
**Source**: USER_REC_08 (docs/MVP.md)  
**User Value**: Dynamic calculation and display of indicators without page refresh.

**Success Criteria**:
- Frontend sends calculation request to backend on selection.
- Backend computes and saves file, returns results to frontend.
- Indicators displayed on chart correctly.

**Complexity**: Medium  
**Dependencies**: GOAL_01.

## GOAL_03: Recalculation on Demand or Config Change
**Source**: USER_REC_08 (docs/MVP.md)  
**User Value**: Update indicator files and display when configurations change.

**Success Criteria**:
- Recalculation triggered on config updates or manual request.
- Existing files overwritten with new calculations.
- Updated data reflected in frontend without refresh.

**Complexity**: Simple  
**Dependencies**: GOAL_02.

## GOAL_04: Testing and Verification
**Source**: USER_REC_08 (docs/MVP.md)  
**User Value**: Ensure correctness of file creation and display.

**Success Criteria**:
- Tests verify file existence, content accuracy, and frontend display.
- Cover scenarios like initial calculation, recalculation, and config changes.

**Complexity**: Medium  
**Dependencies**: GOAL_01, GOAL_02, GOAL_03.

## GOAL_05: System Indicator Validation & Optimization
**Source**: USER_REC_09 (docs/MVP.md)  
**User Value**: Guarantee every system indicator variant delivers mathematically correct and performant outputs that align with trading strategies.

**Success Criteria**:
- All implemented system indicator algorithms match reference calculations on session `code_ai/data/session_exec_20251007_144857_657c2dd6`.
- Automated regression suites (backend, integration, frontend) cover general/risk/price/stop_loss/take_profit/close_order categories with documented evidence.
- Performance benchmarks for high-cost indicators stay within agreed thresholds and regressions trigger alerts.
- Validation report captures detected defects, fixes, and residual risks in `docs/evidence/user_rec_09/`.

**Complexity**: Complex  
**Dependencies**: GOAL_01, GOAL_02, GOAL_03, GOAL_04.

## GOAL_06: Real-Time TWPA Engine Compliance
**Source**: USER_REC_10 (docs/MVP.md)  
**User Value**: Deliver continuously refreshed, numerically accurate TWPA metrics that strategies, charting, and backtesting workflows can trust even when markets are idle.

**Success Criteria**:
- Dedicated TWPA indicator module matches a NumPy reference within 1e-6 on dataset `code_ai/data/session_exec_20251007_144857_657c2dd6` across all configured windows.
- Scheduler honours specification: ≤1 s refresh for windows touching `t2 = 0`, adaptive cadence (≥10 s) for far-back windows, with configuration overrides.
- Registry exposes TWPA metadata from the new module; indicator variants persist and reload without regression.
- Backend `[backend-pytest]` suites cover multi-window and empty-window scenarios, adaptive cadence logic, and dataset parity; evidence stored under `docs/evidence/user_rec_10/`.

**Complexity**: Medium  
**Dependencies**: GOAL_01, GOAL_02, GOAL_03, GOAL_04, GOAL_05.

## GOAL_07: Indicator Registry Cleanup
**Source**: USER_REC_11 (docs/MVP.md)  
**User Value**: Simplify the system indicator surface by keeping only algorithms with real implementations, reducing confusion and maintenance risk.

**Success Criteria**:
- All non-TWPA system indicators are removed from backend registries, API responses, and configuration options; TWPA remains fully functional.
- Any frontend or backtest components that list system indicators show only TWPA and behave correctly.
- Configuration files, variants, and tests referencing removed indicators are deleted or updated; the system starts cleanly without warnings.
- Evidence (API responses / variant loads) stored in `docs/evidence/user_rec_11/` confirms the registry now exposes only TWPA.

**Complexity**: Low  
**Dependencies**: GOAL_01, GOAL_02, GOAL_03 (for file I/O), GOAL_04 (tests), GOAL_05, GOAL_06.

## GOAL_08: Time Unit Standardization & Calculation Interval Fix
**Source**: USER_REC_14 (docs/MVP.md)  
**User Value**: Ensure accurate technical indicator calculations by standardizing time units and fixing calculation intervals to respect refresh_interval_seconds.

**Technical Requirements Breakdown**:
1. **Time Format Standardization**: All timestamps stored as seconds.decimal format (1759841342.561) consistently across price data and indicators
2. **Calculation Interval Compliance**: Indicator values generated according to refresh_interval_seconds setting instead of millisecond intervals
3. **Parameter Unit Validation**: TWPA parameters (t1, t2) properly interpreted as seconds, not milliseconds
4. **API Format Consistency**: All API responses use standardized timestamp format without conversion complications

**Success Criteria**:
- TWPA indicators generate values every refresh_interval_seconds (e.g., 1 value per second for refresh_interval_seconds=1.0)
- All timestamps stored in consistent seconds.decimal format across price data and indicator files
- Frontend-backend timestamp matching works without tolerance fallback mechanisms
- TWPA parameter windows calculated correctly using second-based time units
- Performance optimized: ~1,800 values for 30-minute session instead of 41,926+ millisecond-interval values

**Complexity**: Medium  
**Dependencies**: GOAL_01, GOAL_02, GOAL_06 (TWPA engine).

## GOAL_09: Indicator System Architectural Consolidation
**Source**: USER_REC_16 (docs/MVP.md)  
**User Value**: Eliminate critical architectural flaws causing duplicate logic, orphaned code, and data corruption risks in the indicator calculation system.

**Technical Requirements Breakdown**:
1. **Single Source of Truth for Calculations**: Consolidate three duplicate implementations (StreamingIndicatorEngine, UnifiedIndicatorEngine, IndicatorCalculator) into one shared IndicatorCalculator
2. **Factory Pattern Correction**: Fix duplicate IndicatorEngineFactory classes and ensure proper type contracts between factory and API consumers
3. **Persistence Layer Separation**: Remove CSV writing from calculation engines and implement dedicated IndicatorPersistenceService with event-driven architecture
4. **Code Cleanup**: Remove 2000+ lines of orphaned UnifiedIndicatorCalculationEngine code that's never instantiated
5. **Adapter Pattern Elimination**: Remove StreamingIndicatorEngineAdapter that only forwards calls without providing adaptation value
6. **Dependency Injection Fix**: Implement proper dependency injection in API routes with application context
7. **Engine Lifecycle Management**: Add thread-safe engine creation, caching, and cleanup with health monitoring

**Success Criteria**:
- Single IndicatorCalculator class used by all engines (live, historical, backtest) with identical calculation results
- Zero duplicate calculation implementations across codebase
- Factory returns correct types matching API contracts without adapter layer
- Single IndicatorPersistenceService handles all CSV operations with file locking to prevent race conditions  
- Codebase reduced by removing orphaned classes while maintaining all functionality
- All engines implement IIndicatorEngine protocol with proper dependency injection
- Thread-safe engine lifecycle management with health monitoring capabilities
- Performance maintained or improved after consolidation

**Complexity**: Complex  
**Dependencies**: GOAL_05 (System Indicator Validation), current Sprint 15 completion.

## Prioritization
- Order by dependencies: GOAL_01 -> GOAL_02 -> GOAL_03 -> GOAL_04 -> GOAL_05 -> GOAL_06 -> GOAL_07 -> GOAL_08 -> GOAL_09.
- Mark dependencies in goals.
