---
stepsCompleted: [1]
inputDocuments:
  - "_bmad-output/prd.md"
  - "_bmad-output/architecture.md"
  - "docs/UI_INTERFACE_SPECIFICATION.md"
workflowType: 'epics-and-stories'
lastStep: 1
project_name: 'FX Agent AI'
user_name: 'Mr Lu'
date: '2025-12-20'
---

# FX Agent AI - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for FX Agent AI, decomposing the requirements from the PRD, Architecture, and UX/UI Specification into implementable stories.

**Project Context:** Brownfield repair - connecting existing components into functioning automated trading system.

**MVP Definition:** "Configure a strategy (even simple) and during a trading/backtesting session SEE on the dashboard: signals, state machine state, indicator values"

## Requirements Inventory

### Functional Requirements

#### Strategy Configuration (FR1-FR9)
- FR1: Trader can create a new pump detection strategy
- FR2: Trader can configure S1 (Signal Detection) conditions with indicator thresholds
- FR3: Trader can configure O1 (Cancellation) conditions for false signal filtering
- FR4: Trader can configure Z1 (Entry Confirmation) conditions
- FR5: Trader can configure ZE1 (Exit with Profit) conditions
- FR6: Trader can configure E1 (Emergency Exit) conditions
- FR7: Trader can select which indicators to use in conditions (from MVP indicator set)
- FR8: Trader can save and load strategy configurations
- FR9: Trader can view the current strategy configuration in a readable format

#### Signal Generation (FR10-FR17)
- FR10: System can evaluate strategy conditions against market data
- FR11: System can generate S1 signals when detection conditions are met
- FR12: System can generate O1 signals when cancellation conditions are met
- FR13: System can generate Z1 signals when entry conditions are met
- FR14: System can generate ZE1 signals when profit exit conditions are met
- FR15: System can generate E1 signals when emergency exit conditions are met
- FR16: System can calculate MVP indicator values (TWPA, pump_magnitude_pct, volume_surge_ratio, price_velocity, spread_pct, unrealized_pnl_pct)
- FR17: System can track state machine transitions (S1→O1→Z1→ZE1→E1)

#### Dashboard Display (FR18-FR24)
- FR18: Trader can view generated signals on the price chart
- FR19: Trader can view current state machine state (which section is active)
- FR20: Trader can view real-time indicator values
- FR21: Trader can view signal history during a session
- FR22: Trader can distinguish between different signal types (S1/O1/Z1/ZE1/E1) visually
- FR23: Trader can view state machine transition history
- FR24: Trader can view connection status (WebSocket health)

#### Backtest Execution (FR25-FR31)
- FR25: Trader can start a backtest session with a selected strategy
- FR26: Trader can select historical data period for backtesting
- FR27: Trader can select symbol for backtesting
- FR28: System can simulate trading execution during backtest
- FR29: Trader can view backtest progress
- FR30: Trader can view backtest results (P&L summary)
- FR31: Trader can stop a running backtest

#### Diagnostics & Debugging (FR32-FR36)
- FR32: Trader can view "Why No Signal" diagnostics showing closest threshold approach
- FR33: Trader can view indicator values continuously (even when no signals fire)
- FR34: Trader can access debug panel showing raw WebSocket messages (dev mode)
- FR35: System displays which conditions passed/failed during evaluation
- FR36: Trader can trace why each signal/transition occurred

#### System Reliability (FR37-FR42)
- FR37: System validates strategy configuration schema before saving
- FR38: System validates strategy configuration when received by backend
- FR39: System performs pre-flight check before starting backtest (data requirements, connection)
- FR40: System displays errors with context (no silent failures)
- FR41: System attempts auto-reconnect on WebSocket disconnection
- FR42: System offers recovery options when errors occur (resume/restart)

### Non-Functional Requirements

#### Performance (NFR1-NFR6)
- NFR1: Signal display latency must be < 500ms from backend generation to dashboard render
- NFR2: WebSocket reconnection must complete within 2 seconds
- NFR3: Indicator calculations must not block UI rendering
- NFR4: Backtest must process at least 10x faster than real-time (1 hour of data in < 6 minutes)
- NFR5: Dashboard must remain responsive during backtest execution
- NFR6: Multiple concurrent indicator updates must not cause UI lag

#### Reliability (NFR7-NFR11)
- NFR7: System must not have silent failures - all errors must surface to UI
- NFR8: WebSocket connection must auto-reconnect on disconnection
- NFR9: Backtest session must be resumable after error recovery
- NFR10: Strategy configuration must not be lost on browser refresh (persist to backend)
- NFR11: System must gracefully degrade when optional services unavailable (e.g., Redis)

#### Data Integrity (NFR12-NFR15)
- NFR12: Strategy configuration must be validated before saving
- NFR13: Signal data must be consistent between backend and frontend
- NFR14: Backtest results must be deterministic (same inputs = same outputs)
- NFR15: Historical data must not be corrupted during backtest processing

#### Security (NFR16-NFR18)
- NFR16: MEXC API keys must be stored securely (not in frontend code)
- NFR17: API keys must not be exposed in browser developer tools
- NFR18: Backend must validate requests come from authorized frontend

#### Observability (NFR19-NFR22)
- NFR19: System must log all state machine transitions
- NFR20: System must log all errors with context for debugging
- NFR21: Debug panel must show raw WebSocket messages (dev mode)
- NFR22: System must track and display connection status

#### Constraints (NFR23-NFR25)
- NFR23: Must work on Windows without Docker (no Redis dependency for MVP)
- NFR24: Must work with QuestDB as primary data store
- NFR25: Desktop browsers only (Chrome, Firefox, Edge)

### Additional Requirements

#### From Architecture Document

**Critical Fix (P0):**
- ARCH-1: Fix EventBridge subscription - change from "signal.flash_pump_detected" to "signal_generated" in `/src/api/event_bridge.py:631`

**Implementation Patterns (MUST follow):**
- ARCH-2: Use `snake_case` for all Python, TypeScript API fields, and database columns
- ARCH-3: Use response envelope wrapper for ALL API responses
- ARCH-4: Subscribe to correct EventBus event names (check `core/events.py`)
- ARCH-5: Follow Clean Architecture layer boundaries
- ARCH-6: Use existing Zustand store patterns with devtools middleware

**Verification Required:**
- ARCH-7: Verify Zustand store signal handler after EventBridge fix
- ARCH-8: Verify Dashboard components display signals correctly
- ARCH-9: Verify StateDisplay.tsx renders state machine state

#### From UX/UI Specification

**Phase 1: Configuration - Indicator Variants (`/indicators`):**
- UX-1: Preview variant on chart (how it reacts to pump) - STATUS: MISSING
- UX-2: Compare variants (Fast vs Medium) - STATUS: MISSING
- UX-3: Parameter descriptions (what does t1, t3, d mean?) - STATUS: MISSING
- UX-4: Signal count prediction (test on history) - STATUS: MISSING

**Phase 1: Configuration - Strategy Builder (`/strategy-builder`):**
- UX-5: State machine diagram visualization - STATUS: MISSING
- UX-6: Quick backtest preview (pumps detected, peaks hit) - STATUS: MISSING
- UX-7: "Where would S1 trigger" chart markers - STATUS: MISSING
- UX-8: Tooltip on variant dropdown - STATUS: MISSING
- Current rating: 5/10

**Phase 2: Monitoring - Trading Session (`/trading-session`):**
- UX-9: Strategy preview (S1/Z1 conditions visible) - STATUS: MISSING
- UX-10: Symbol recommendation (high volume symbols) - STATUS: MISSING
- UX-11: Session matrix (strategy × symbols = instances) - STATUS: MISSING

**Phase 2: Monitoring - Dashboard (`/dashboard`):**
- UX-12: State overview table (all instances) - STATUS: MISSING
- UX-13: Current state display (MONITORING/SIGNAL/POSITION) - STATUS: MISSING
- UX-14: Condition progress (which ZE1/E1 conditions met) - STATUS: MISSING
- UX-15: Chart S1/Z1/ZE1 markers - STATUS: MISSING
- UX-16: Chart zoom/scroll - STATUS: MISSING
- UX-17: Position panel (entry, P&L, SL/TP, time) - STATUS: MISSING
- UX-18: Emergency close button - STATUS: MISSING
- UX-19: Transition log - STATUS: MISSING
- Current rating: 3/10

**Phase 3: Historical Review - Session History (`/session-history`):**
- UX-20: Session list page - STATUS: MISSING (NEW PAGE)
- UX-21: Session summary stats (S1, Z1, O1, E1 counts, accuracy) - STATUS: MISSING
- UX-22: Transition timeline visualization - STATUS: MISSING
- UX-23: Transition details (indicator values at trigger) - STATUS: MISSING
- UX-24: Chart with S1/Z1/ZE1 markers - STATUS: MISSING
- UX-25: Per-trade breakdown table - STATUS: MISSING
- UX-26: Replay mode - STATUS: MISSING

**Data Requirements for State Machine:**
- UX-27: Save transitions with conditions and market snapshot
- UX-28: Save trades with entry/exit details and P&L
- UX-29: Calculate session summary (s1_count, z1_count, accuracy, etc.)

### FR Coverage Map

_To be populated in Step 2 after epic design_

## Epic List

_To be populated in Step 2 after epic design_

