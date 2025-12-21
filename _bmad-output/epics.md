---
stepsCompleted: [1, 2]
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

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 3 | Create pump detection strategy |
| FR2 | Epic 3 | Configure S1 conditions |
| FR3 | Epic 3 | Configure O1 conditions |
| FR4 | Epic 3 | Configure Z1 conditions |
| FR5 | Epic 3 | Configure ZE1 conditions |
| FR6 | Epic 3 | Configure E1 conditions |
| FR7 | Epic 3 | Select indicators for conditions |
| FR8 | Epic 3 | Save and load strategies |
| FR9 | Epic 3 | View strategy configuration |
| FR10 | Epic 1 | Evaluate conditions against market data |
| FR11 | Epic 1 | Generate S1 signals |
| FR12 | Epic 1 | Generate O1 signals |
| FR13 | Epic 1 | Generate Z1 signals |
| FR14 | Epic 1 | Generate ZE1 signals |
| FR15 | Epic 1 | Generate E1 signals |
| FR16 | Epic 1 | Calculate MVP indicator values |
| FR17 | Epic 1 | Track state machine transitions |
| FR18 | Epic 2 | View signals on chart |
| FR19 | Epic 2 | View current state machine state |
| FR20 | Epic 2 | View real-time indicator values |
| FR21 | Epic 2 | View signal history |
| FR22 | Epic 2 | Distinguish signal types visually |
| FR23 | Epic 2 | View state machine transition history |
| FR24 | Epic 1 | View connection status |
| FR25 | Epic 4 | Start backtest session |
| FR26 | Epic 4 | Select historical data period |
| FR27 | Epic 4 | Select symbol for backtesting |
| FR28 | Epic 4 | Simulate trading execution |
| FR29 | Epic 4 | View backtest progress |
| FR30 | Epic 4 | View backtest results (P&L) |
| FR31 | Epic 4 | Stop running backtest |
| FR32 | Epic 5 | "Why No Signal" diagnostics |
| FR33 | Epic 5 | View indicator values continuously |
| FR34 | Epic 5 | Debug panel (raw WebSocket) |
| FR35 | Epic 5 | Display condition pass/fail |
| FR36 | Epic 5 | Trace signal/transition reasons |
| FR37 | Epic 6 | Validate strategy schema on save |
| FR38 | Epic 6 | Validate strategy on backend receive |
| FR39 | Epic 6 | Pre-flight check before backtest |
| FR40 | Epic 6 | Display errors with context |
| FR41 | Epic 6 | Auto-reconnect on disconnect |
| FR42 | Epic 6 | Recovery options on error |

## Epic List

### Epic 1: Signal Pipeline Integration (Critical Fix)
**Goal:** Signals generated by backend reach frontend and are visible - unblocks entire system.

**FRs covered:** FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR24
**ARCH covered:** ARCH-1 (EventBridge fix), ARCH-7, ARCH-8, ARCH-9

**Priority:** P0 - Must be done first

#### Story 1.1: Fix EventBridge Signal Subscription

As a trader,
I want backend signals to be forwarded to WebSocket clients,
So that I can see trading signals on my dashboard.

**Acceptance Criteria:**

**Given** the backend StrategyManager publishes a "signal_generated" event
**When** the EventBridge receives this event
**Then** it forwards the signal to all subscribed WebSocket clients
**And** the message includes signal type (S1/O1/Z1/ZE1/E1), symbol, timestamp, and indicator values

**Technical Notes:**
- File: `/src/api/event_bridge.py:631`
- Change: Subscribe to "signal_generated" instead of "signal.flash_pump_detected"

---

#### Story 1.2: Verify Backend Signal Generation

As a trader,
I want the system to generate signals for all 5 state machine sections,
So that I receive notifications for pump detection, cancellation, entry, exit, and emergency.

**Acceptance Criteria:**

**Given** market data meets S1 conditions (pump_magnitude > threshold)
**When** the StrategyManager evaluates the strategy
**Then** it publishes "signal_generated" event with type "S1"
**And** the event includes all indicator values that triggered the signal

**Given** a position is active and ZE1 conditions are met
**When** the StrategyManager evaluates exit conditions
**Then** it publishes "signal_generated" event with type "ZE1"
**And** the event includes unrealized P&L percentage

---

#### Story 1.3: Verify Frontend Signal Reception

As a trader,
I want my dashboard to receive signals from the backend,
So that I see updates in real-time without page refresh.

**Acceptance Criteria:**

**Given** the WebSocket connection is established
**When** a signal is received from the backend
**Then** the Zustand dashboardStore updates with the new signal
**And** the signal appears in the store within 500ms of backend generation (NFR1)

**Given** the dashboard is open
**When** a signal arrives via WebSocket
**Then** React components re-render with the new signal data

---

#### Story 1.4: Display Connection Status

As a trader,
I want to see the WebSocket connection status,
So that I know if my dashboard is receiving real-time data.

**Acceptance Criteria:**

**Given** I am on the dashboard page
**When** WebSocket is connected
**Then** I see a green indicator showing "Connected"

**Given** WebSocket connection is lost
**When** the dashboard detects disconnection
**Then** I see a red indicator showing "Disconnected"
**And** the system attempts auto-reconnect within 2 seconds (NFR2)

---

#### Story 1.5: End-to-End Signal Flow Verification

As a trader,
I want confidence that the entire signal pipeline works,
So that I can trust the system before live trading.

**Acceptance Criteria:**

**Given** a strategy is configured and active
**When** market data triggers S1 conditions
**Then** I see the S1 signal on my dashboard within 500ms
**And** I can trace the signal from backend log to frontend display

**Given** I enable debug mode
**When** signals flow through the system
**Then** I can see raw WebSocket messages in the debug panel

---

### Epic 2: Dashboard State Machine Visibility
**Goal:** Trader sees current state machine state, signals, and indicators in real-time.

**FRs covered:** FR18, FR19, FR20, FR21, FR22, FR23
**UX covered:** UX-12, UX-13, UX-14, UX-15, UX-17, UX-19

**Priority:** P1 - Core MVP visibility

#### Story 2.1: State Machine Overview Table

As a trader,
I want to see all active strategy instances with their current states,
So that I can monitor multiple symbols at once.

**Acceptance Criteria:**

**Given** I have a trading session with 3 symbols (BTC, ETH, SOL)
**When** I open the dashboard
**Then** I see a table with columns: Strategy, Symbol, STATE, Time in State, Action
**And** each row shows the current state (MONITORING/SIGNAL_DETECTED/POSITION_ACTIVE)

**Given** an instance transitions from MONITORING to SIGNAL_DETECTED
**When** the transition occurs
**Then** the table updates in real-time without page refresh
**And** the state cell changes color (green=MONITORING, yellow=SIGNAL, red=POSITION)

---

#### Story 2.2: Current State Display

As a trader,
I want to see the current state of a selected instance prominently,
So that I immediately know what the system is doing.

**Acceptance Criteria:**

**Given** I select an instance from the overview table
**When** the instance is in POSITION_ACTIVE state
**Then** I see a large, colored badge showing "POSITION_ACTIVE"
**And** I see the time elapsed in this state (e.g., "5m 12s")

**Given** a state transition occurs
**When** the system moves from one state to another
**Then** the display updates within 500ms
**And** I see which trigger caused the transition (S1, Z1, ZE1, etc.)

---

#### Story 2.3: Real-time Indicator Panel

As a trader,
I want to see current indicator values updating in real-time,
So that I understand market conditions driving my strategy.

**Acceptance Criteria:**

**Given** I am viewing an active trading instance
**When** indicator values update from backend
**Then** I see a panel with current values for:
- PUMP_MAGNITUDE_PCT (with progress bar)
- PRICE_VELOCITY (with progress bar)
- VOLUME_SURGE_RATIO (with progress bar)
- MOMENTUM_REVERSAL_INDEX (with progress bar)

**Given** an indicator value approaches its threshold
**When** value is within 20% of threshold
**Then** the indicator row highlights to show "approaching trigger"

---

#### Story 2.4: Signal Markers on Chart

As a trader,
I want to see where signals occurred on the price chart,
So that I can visually correlate signals with price action.

**Acceptance Criteria:**

**Given** I am viewing a price chart during a session
**When** an S1 signal was generated at timestamp T
**Then** I see a marker on the chart at that point labeled "S1"
**And** the marker is colored distinctly (e.g., blue for S1)

**Given** multiple signal types occurred
**When** I view the chart
**Then** I can distinguish S1 (blue), Z1 (green), ZE1 (purple), O1 (gray), E1 (red)
**And** clicking a marker shows tooltip with signal details

---

#### Story 2.5: Signal History Panel

As a trader,
I want to see a history of signals during my session,
So that I can review what happened chronologically.

**Acceptance Criteria:**

**Given** signals have occurred during a session
**When** I view the signal history panel
**Then** I see a chronological list with: Time, Type, Symbol, Key Values
**And** each signal type has a distinct icon/color

**Given** a new signal arrives
**When** I am viewing the signal history
**Then** the new signal appears at the top of the list
**And** older signals scroll down

---

#### Story 2.6: Transition Log

As a trader,
I want to see a detailed log of state machine transitions,
So that I understand the full lifecycle of each trade attempt.

**Acceptance Criteria:**

**Given** state transitions have occurred
**When** I view the transition log
**Then** I see entries like: "12:34:12 | MONITORING → SIGNAL_DETECTED | S1: pump=7.2%, vel=0.42"
**And** each entry shows from_state, to_state, trigger, and key condition values

**Given** a position was opened
**When** I view the transition log
**Then** I see the entry: "12:34:57 | SHORT opened @ $142.50 | SL=$146.77, TP=$135.37"

---

### Epic 3: Strategy Configuration & Builder
**Goal:** Trader can create complete pump detection strategy with 5 sections (S1/O1/Z1/ZE1/E1).

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9
**UX covered:** UX-5, UX-6, UX-7, UX-8

**Priority:** P1 - Core MVP configuration

---

### Epic 4: Backtest Execution
**Goal:** Trader can run backtest on historical data and see P&L results.

**FRs covered:** FR25, FR26, FR27, FR28, FR29, FR30, FR31
**UX covered:** UX-6 (Quick backtest)

**Priority:** P1 - Core MVP validation

---

### Epic 5: Diagnostics & Transparency
**Goal:** Trader understands WHY the system made each decision (signal, no signal).

**FRs covered:** FR32, FR33, FR34, FR35, FR36
**UX covered:** UX-14, UX-19, UX-23

**Priority:** P2 - Enhanced MVP

---

### Epic 6: System Reliability & Error Handling
**Goal:** System is reliable - no silent failures, auto-reconnect, recovery options.

**FRs covered:** FR37, FR38, FR39, FR40, FR41, FR42
**NFRs covered:** NFR7-NFR11, NFR12-NFR15

**Priority:** P2 - Production readiness

---

### Epic 7: Session History & Analytics (Post-MVP)
**Goal:** Trader can browse historical sessions, analyze performance, replay sessions.

**UX covered:** UX-20, UX-21, UX-22, UX-23, UX-24, UX-25, UX-26

**Priority:** P3 - Post-MVP enhancement

