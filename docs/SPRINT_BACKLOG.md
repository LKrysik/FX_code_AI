# Sprint Backlog

## Active Sprint: Sprint 16 - USER_REC_16 Indicator System Architectural Consolidation
Goals: GOAL_09 (Indicator System Architectural Consolidation) - Eliminate duplicate calculation engines and architectural flaws (Reference: docs/sprints/SPRINT_16_PLAN.md)

## Tasks for USER_REC_16: Indicator System Architectural Consolidation
1. [DONE] Create Backup and Audit Dependencies - Safety measures and comprehensive dependency analysis [backend-pytest] (Source: USER_REC_16.1) ✅ Evidence: docs/evidence/user_rec_16/
2. [WORKING ON] Consolidate IndicatorCalculator Logic - Move calculations to shared calculator, remove duplicates [backend-pytest] (Source: USER_REC_16.7)
3. [TODO] Implement Factory Consolidation - Remove duplicate factory, add caching, fix return types [backend-pytest] (Source: USER_REC_16.1)
4. [TODO] Separate Persistence Responsibilities - Remove CSV writing from engines, implement file locking [backend-pytest] (Source: USER_REC_16.10)
5. [TODO] Remove Orphaned Components - Delete UnifiedIndicatorEngine and StreamingIndicatorEngineAdapter [backend-pytest] (Source: USER_REC_16.8, USER_REC_16.9)
6. [TODO] Fix API Dependency Injection - Replace mocks with proper application context [backend-pytest] (Source: USER_REC_16.3)
7. [TODO] Comprehensive Integration Testing - Cross-engine validation and performance testing [backend-pytest] (Source: USER_REC_16.6)
8. [TODO] Final Validation and Documentation - Evidence package and architecture documentation [backend-pytest] (Source: USER_REC_16.12)

## Previous Sprint: Sprint 15 - USER_REC_15 Indicator System Consolidation
1. [DONE] Create Backup and Audit Dependencies - Safety measures and dependency analysis [backend-pytest] (Source: USER_REC_15.1) ✅ Evidence: docs/evidence/sprint_15_task_1/
2. [WORKING ON] Add Public API Methods to StreamingIndicatorEngine - Replace private field access [backend-pytest] (Source: USER_REC_15.5)
3. [TODO] Add Session Management to StreamingIndicatorEngine - Migrate orchestration from Service [backend-pytest] (Source: USER_REC_15.2)
4. [TODO] Add Time Simulation to StreamingIndicatorEngine - Migrate simulation functionality [backend-pytest] (Source: USER_REC_15.4)
5. [TODO] Create IndicatorPersistenceService - Event-driven CSV operations [backend-pytest] (Source: USER_REC_15.3)
6. [TODO] Update API Routes and Dependencies - Remove UnifiedIndicatorService [backend-pytest] (Source: USER_REC_15.1)
7. [TODO] Migrate Tests and Remove Old Components - Complete cleanup [backend-pytest] (Source: USER_REC_15.6)
8. [TODO] Integration Testing and Performance Validation - Comprehensive validation [backend-pytest] (Source: USER_REC_15.7)

## Previous Sprint: Sprint 14 - USER_REC_14 Time Unit Standardization
Goals: GOAL_08 (Time Unit Standardization & Calculation Interval Fix) - Fix timestamp format inconsistencies and calculation intervals (Reference: docs/goals/BUSINESS_GOALS.md, docs/sprints/SPRINT_14_PLAN.md)

## Tasks for USER_REC_14: Time Unit Standardization  
1. [DONE] Fix Indicator Calculation Scheduling - Modified scheduling to respect refresh_interval_seconds [backend-pytest] (Source: USER_REC_14.1)
2. [DONE] Standardize Timestamp Format Across System - Implemented consistent seconds.decimal format [backend-pytest] (Source: USER_REC_14.2)  
3. [DONE] Validate TWPA Parameter Unit Interpretation - Ensured t1, t2 treated as seconds [backend-pytest] (Source: USER_REC_14.3)
4. [DONE] Add Time Format Validation and Normalization - Created centralized time normalization module [backend-pytest] (Source: USER_REC_14.4)

## Previous Sprint: Sprint 13 - USER_REC_13 Frontend Chart Data Fix
Goals: Fix chart data display mismatch (Reference: docs/goals/BUSINESS_GOALS.md)

## Tasks for USER_REC_13: Frontend Chart Data Fix
1. [DONE] Fix Chart API Endpoint Construction - Correct field ID mapping in history API calls (Evidence: docs/evidence/user_rec_13_task_1/)
2. [WORKING ON] Add Debug Logging for API Endpoint Validation - Enhanced logging for endpoint construction  
3. [TODO] Validate Data Consistency Between API and Chart - Ensure response data flows correctly to display
4. [TODO] Implement frontend test suite [frontend-playwright] - Chart interaction and API validation tests
5. [TODO] Implement backend API validation tests [backend-pytest] - Endpoint response and data accuracy tests
6. [TODO] Generate evidence package with before/after validation

## Previous Sprint: Sprint 12 - USER_REC_12 TWPA Calculation Fix
## Previous Sprint: Sprint 12 - USER_REC_12 TWPA Calculation Fix
Goals: GOAL_06 (Real-Time TWPA Engine Compliance) - Critical Bug Fix (Reference: docs/goals/BUSINESS_GOALS.md)

## Tasks for USER_REC_12: TWPA Calculation Fix
1. [TODO] Fix variant configuration mismatch (t1=30, t2=5)
2. [TODO] Debug calculation frequency issue (1-second intervals)
3. [TODO] Validate TWPA algorithm implementation
4. [TODO] Implement TWPA accuracy test suite [backend-pytest]
5. [TODO] Fix scheduler time-driven updates
6. [TODO] Regenerate and verify evidence files

## Previous Sprint: Sprint 8 - USER_REC_08 Implementation
Goals: GOAL_01, GOAL_02, GOAL_03, GOAL_04 (Reference: docs/goals/BUSINESS_GOALS.md)

## Tasks for GOAL_01: Indicator Calculation File Creation
1. [DONE] Modify unified indicator engine to generate CSV files during calculations
2. [DONE] Implement directory structure creation (data/session/SYMBOL/indicators/)
3. [DONE] Add timestamp/value schema normalization (include metadata column)
4. [DONE] Handle file writing for both backtest batch mode and live chart mode

## Tasks for GOAL_02: Frontend-Backend Integration for Calculation
5. [DONE] Create API endpoint for triggering indicator calculation and file generation (status + file metadata)
6. [DONE] Update frontend to send requests on indicator selection without page refresh (progress indicator + polling)
7. [DONE] Implement real-time result fetching and chart updating in frontend (polling replaces timeout)
8. [IN PROGRESS] Add error handling for calculation failures (status UI added, needs test coverage)

## Tasks for GOAL_03: Recalculation on Demand or Config Change
9. [IN PROGRESS] Add recalculation trigger in backend for config updates (force recalculation helper implemented, API wiring pending)
10. [TODO] Implement file overwriting logic for updated calculations
11. [TODO] Update frontend to handle recalculation requests and refresh display

## Tasks for GOAL_04: Testing and Verification
12. [IN PROGRESS] Write unit tests for CSV file generation and content accuracy (updated persistence tests; execution blocked by missing pytest)
13. [TODO] Create integration tests for frontend-backend communication
14. [TODO] Develop end-to-end tests using test session data
15. [TODO] Verify recalculation scenarios and config change handling
16. [TODO] Perform manual verification with specified test session

## Tasks for GOAL_05: System Indicator Validation & Optimization
17. [IN PROGRESS] Replace legacy streaming indicator placeholders with unified engine hooks and document architecture impact (TWPA/VWAP/MAX/MIN now delegate to window helpers; architecture note pending)
18. [IN PROGRESS] Validate Group A fundamental measures against reference calculations using session `code_ai/data/session_exec_20251007_144857_657c2dd6` (TWPA/VWAP/FIRST/LAST/MAX/MIN harness + dataset regression in place)
19. [IN PROGRESS] Implement and verify velocity/momentum algorithms (Group B) including edge-case test coverage (velocity + cascade + momentum streak/consistency validated via dataset harness; velocity acceleration xfailed pending engine fix)
20. [TODO] Audit order-book and volume metrics (Groups C–E) with synthetic and historical datasets, handling missing depth data gracefully
21. [TODO] Finalize composite/predictive indicator calculations (Groups F–H) and ensure performance stays within thresholds
22. [TODO] Build automated regression & performance suites (backend/integration/frontend) with evidence collection pipeline
23. [TODO] Compile validation summary report with detected issues, fixes, benchmarks, and recommendations in `docs/evidence/user_rec_09/`

## Tasks for GOAL_06: Real-Time TWPA Engine Compliance
24. [TODO] Extract TWPA algorithm into dedicated module and expose registry metadata
25. [TODO] Implement adaptive time-driven scheduler so TWPA refreshes even without new ticks, with configurable cadence
26. [TODO] Adjust caching/key strategy for TWPA to respect sub-minute refresh intervals
27. [TODO] Add `[backend-pytest]` coverage for multi-window TWPA scenarios, scheduler cadence, and dataset parity (evidence in `docs/evidence/user_rec_10/`)
28. [TODO] Document refresh policy and configuration knobs for TWPA, update STATUS to Sprint 10, and publish validation artefacts

## Tasks for GOAL_07: Indicator Registry Cleanup
29. [DONE] Inventory registered system indicators vs. modules in `src/domain/services/indicators/`
30. [DONE] Remove non-TWPA indicator registrations, metadata, and API exposure from streaming indicator engine
31. [DONE] Purge configuration variants/files referencing removed indicators and update validation logic
32. [DONE] Update frontend/backtest surfaces to list only TWPA and ensure UX remains stable
33. [DONE] Refresh documentation/tests and capture evidence under `docs/evidence/user_rec_11/`
