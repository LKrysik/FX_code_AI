---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - "_bmad-output/prd.md"
  - "_bmad-output/architecture.md"
  - "_bmad-output/ux-design-specification.md"
workflowType: 'epics-and-stories'
lastStep: 1
project_name: 'FX Agent AI'
user_name: 'Mr Lu'
date: '2025-12-21'
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

#### From UX Design Specification (2025-12-20)

**Core Custom Components (Must Implement):**
- UX-1: **StatusHero Component** - Combined state + P&L display (largest element on screen when position active)
- UX-2: **JourneyBar Navigation** - Visual trading flow progress (Watch -> Found -> Enter -> Monitor -> Exit)
- UX-3: **ConditionProgress Component** - Visual progress bars for condition evaluation with countdown
- UX-4: **DeltaDisplay** - "+$X to target" formatted metrics with trend arrows
- UX-5: **TransitionBadge** - Inline "why" explanations for every state transition
- UX-6: **NowPlayingBar** - Persistent footer when position is active (Spotify-style)

**Human Vocabulary Transformation (Critical):**
- UX-7: Replace S1 with "Found!" (icon: fire emoji)
- UX-8: Replace O1 with "False Alarm" (icon: X)
- UX-9: Replace Z1 with "Entering" (icon: target)
- UX-10: Replace ZE1 with "Taking Profit" (icon: money bag)
- UX-11: Replace E1 with "Stopping Loss" (icon: stop sign)
- UX-12: Replace MONITORING with "Watching" (icon: eyes)
- UX-13: Replace POSITION_ACTIVE with "Monitoring" (icon: chart)

**State-Driven Information Density:**
- UX-14: MONITORING state = Minimal Focus layout (calm, 3-4 key metrics)
- UX-15: SIGNAL_DETECTED state = Command Center layout (maximum information)
- UX-16: POSITION_ACTIVE state = Split Focus layout (P&L hero with context)

**Visual Design Requirements:**
- UX-17: Color system: Slate (#64748B) monitoring, Amber (#F59E0B) signal, Blue (#3B82F6) position, Green (#10B981) profit, Red (#EF4444) loss
- UX-18: Typography: Inter for UI text, JetBrains Mono for numbers/prices
- UX-19: Hero metric size: 48-64px for P&L display
- UX-20: 2-second comprehension rule - understand situation in 2 seconds

**Interaction Patterns:**
- UX-21: Keyboard shortcuts: Esc = emergency close, Space = pause/resume, D = dashboard, H = history, S = settings
- UX-22: Emergency close must be < 1 second to execute
- UX-23: Sound alerts for state changes (optional, configurable)
- UX-24: Celebration animation on profitable exit (confetti)
- UX-25: No blame language on losses - neutral explanation only

**Responsive & Accessibility:**
- UX-26: Desktop-first design (>=1280px full features, <1280px emergency only)
- UX-27: WCAG 2.1 AA accessibility compliance
- UX-28: Color-blind support: icons supplement colors (arrows for profit/loss)
- UX-29: Focus indicators: 2px solid ring on all interactive elements

**Error Handling UX:**
- UX-30: Error states must be impossible to miss (full-screen if critical)
- UX-31: Connection status always visible when unhealthy
- UX-32: Auto-reconnect with visible status (banner for 3-10s disconnects)
- UX-33: Recovery options always available (resume/restart)

**Critical Success Moments:**
- UX-34: First Signal Detection - celebratory, clear, exciting
- UX-35: First Profitable Exit - celebration animation, clear summary
- UX-36: Understanding "Why" - every transition has visible reason
- UX-37: Error Recovery - visible status, auto-reconnect, clear recovery path

### FR Coverage Map (First Principles + Pre-mortem)

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 2 | Create pump detection strategy |
| FR2 | Epic 2 | Configure S1 conditions |
| FR3 | Epic 2 | Configure O1 conditions |
| FR4 | Epic 2 | Configure Z1 conditions |
| FR5 | Epic 2 | Configure ZE1 conditions |
| FR6 | Epic 2 | Configure E1 conditions |
| FR7 | Epic 2 | Select indicators for conditions |
| FR8 | Epic 0 | Save and load strategies (audit existing) |
| FR9 | Epic 2 | View strategy configuration |
| FR10 | Epic 4 | Evaluate conditions against market data |
| FR11 | Epic 4 | Generate S1 signals |
| FR12 | Epic 4 | Generate O1 signals |
| FR13 | Epic 4 | Generate Z1 signals |
| FR14 | Epic 4 | Generate ZE1 signals |
| FR15 | Epic 4 | Generate E1 signals |
| FR16 | Epic 4 | Calculate MVP indicator values |
| FR17 | Epic 4 | Track state machine transitions |
| FR18 | Epic 1A | View signals on chart |
| FR19 | Epic 1A | View current state machine state |
| FR20 | Epic 1A | View real-time indicator values |
| FR21 | Epic 3 | View signal history |
| FR22 | Epic 1A | Distinguish signal types visually |
| FR23 | Epic 3 | View state machine transition history |
| FR24 | Epic 0 | View connection status (foundation) |
| FR25 | Epic 1B | Start backtest session |
| FR26 | Epic 1B | Select historical data period |
| FR27 | Epic 1B | Select symbol for backtesting |
| FR28 | Epic 1B | Simulate trading execution |
| FR29 | Epic 1B | View backtest progress |
| FR30 | Epic 1B | View backtest results (P&L) |
| FR31 | Epic 4 | Stop running backtest |
| FR32 | Epic 3 | "Why No Signal" diagnostics |
| FR33 | Epic 3 | View indicator values continuously |
| FR34 | Epic 0 | Debug panel (development visibility) |
| FR35 | Epic 3 | Display condition pass/fail |
| FR36 | Epic 3 | Trace signal/transition reasons |
| FR37 | Epic 2 | Validate strategy schema on save |
| FR38 | Epic 2 | Validate strategy on backend receive |
| FR39 | Epic 4 | Pre-flight check before backtest |
| FR40 | Epic 0 | Display errors with context (foundation) |
| FR41 | Epic 4 | Auto-reconnect on disconnect |
| FR42 | Epic 4 | Recovery options on error |

---

## Epic List (First Principles + Pre-mortem Hardened)

**Design Philosophy:** Organized by USER VALUE (when the user achieves something), not technical layers.

**Pre-mortem Insights Applied:**
- Epic 0 expanded to include verification and foundational features
- Epic 1 split into 1A (visibility) and 1B (backtest) for smaller wins
- Debug panel moved early for development velocity
- Core UX moved into Epic 1A (not optional polish)
- **[2025-12-25 Pre-mortem]** Epic 0 success criteria strengthened from "console visible" to "dashboard visible"
- **[2025-12-25 Pre-mortem]** Added Signal Contract Validation story to prevent payload mismatch
- **[2025-12-25 Pre-mortem]** Added explicit Zustand Store verification story
- **[2025-12-25 Pre-mortem]** Clarified Human Vocabulary is UI-only (data contracts unchanged)

---

### Epic 0: Foundation & Pipeline Unblock
**Goal:** Establish a solid foundation with verified signal flow, development visibility, and error patterns.

**User Value:** "The plumbing works - I can see signals flowing and errors appearing."

**This is a FOUNDATION epic** - it sets up everything needed for rapid development of user-facing features.

**FRs covered:** FR8 (audit), FR24 (connection status), FR34 (debug panel), FR40 (error display)
**ARCH covered:** ARCH-1 (EventBridge fix), ARCH-7, ARCH-8, ARCH-9

**Stories:**
1. **Fix EventBridge Signal Subscription** - Change subscription to "signal_generated"
2. **E2E Signal Flow Verification** - Visual proof: signal appears in StatusHero component on dashboard (not just console)
3. **Signal Contract Validation** - Verify backend Pydantic payload matches frontend TypeScript types (prevents payload mismatch)
4. **Verify Zustand Store Updates** - Signal arrives → store updates → component re-renders (use React DevTools to confirm)
5. **Strategy Builder Audit** - Verify FR8 (save/load) actually works
6. **Debug Panel Foundation** - Raw WebSocket message viewer for development
7. **Error Display Pattern** - Establish "no silent failures" from day 1
8. **Connection Status Indicator** - Green/red WebSocket health display

**Success Criteria:**
- Signal visible in StatusHero component on dashboard within 500ms of backend generation
- Zustand store updates verified with React DevTools
- Signal payload contract validated between backend and frontend
- At least one strategy can be loaded from existing data
- Errors display in UI (not just console)
- Debug panel shows raw messages

**Priority:** P0 - Complete before any other epic

---

### Epic 1A: First Signal Visible
**Goal:** Trader sees their FIRST signal appear on the dashboard - the "aha!" moment.

**User Value:** "I can see a signal! The system detected something and showed it to me!"

**This is the SMALLEST possible win** - proving signals reach the UI.

**FRs covered:** FR18 (signals on chart), FR19 (state machine state), FR20 (indicator values), FR22 (signal types visual)
**UX covered:**
- UX-1 (StatusHero basic) - state + P&L display
- UX-7 through UX-11 (Human vocabulary) - "Found!" instead of "S1"
- UX-17 (Color system) - Amber for signal, Green for profit, etc.

**Stories:**
1. **Signal Display on Dashboard** - When signal arrives, show it prominently
2. **State Machine State Badge** - Large, colored badge showing current state
3. **Indicator Values Panel** - Show current values for MVP indicators
4. **Human Vocabulary Labels** - Replace S1/O1/Z1/ZE1/E1 with human words in UI only (data contracts remain unchanged: signal_type still uses 'S1', 'Z1', etc.)
5. **StatusHero Component** - Combined state + basic metrics display
6. **Signal Type Color Coding** - Visual distinction between signal types
7. **First-Visit Onboarding Tooltip** - Simple welcome explaining "This is your dashboard where signals appear" *(Trader A)*
8. **Quick Start Option** - Button to load default/template strategy for immediate testing *(Trader A)*

**Success Criteria:**
- Signal appears on dashboard within 500ms of backend generation
- State shows as "Found!" (not "S1") with fire emoji
- Indicator values visible and updating
- Colors match UX spec (Amber for signal, etc.)
- First-time user sees helpful tooltip
- Can start with template strategy without configuration

**Priority:** P0 - First user-facing epic

**Why split from 1B:** Smaller scope = faster first win. Proves visibility before adding backtest complexity.

---

### Epic 1B: First Successful Backtest
**Goal:** Trader runs a complete backtest and sees P&L results.

**User Value:** "I ran a backtest and made a (simulated) profit! The whole cycle works!"

**Builds on Epic 1A** - signals are already visible, now add backtest execution.

**FRs covered:** FR25 (start backtest), FR26 (select period), FR27 (select symbol), FR28 (simulate execution), FR29 (progress), FR30 (P&L results), FR31 (stop backtest)
**UX covered:**
- UX-2 (JourneyBar) - Visual progress through trading flow
- UX-3 (ConditionProgress) - Progress bars for condition evaluation
- UX-21 (partial) - Esc keyboard shortcut for emergency stop
- UX-22 - Emergency close < 1 second

**Stories:**
1. **Backtest Session Setup** - Select strategy, symbol, and date range
2. **Backtest Execution** - Run simulation on historical data
3. **Progress Display** - Show backtest progress (% complete, current time)
4. **P&L Summary** - Display final profit/loss after backtest completes
5. **JourneyBar Component** - Visual flow: Watch → Found → Enter → Monitor → Exit
6. **Signal Timeline on Chart** - Markers showing where signals occurred
7. **State Overview Table** - Monitor multiple symbols with current state per instance *(Trader B)*
8. **Emergency Stop Button + Esc Shortcut** - Immediately halt backtest/trading with prominent button AND Esc key *(Trader B, C)*
9. **Multi-Symbol Session Support** - Run backtest on 1-3 symbols simultaneously *(Trader B)*

**Success Criteria:**
- Can start backtest with existing strategy
- Progress visible during execution
- P&L displayed at end
- Journey bar shows progression through states
- At least one complete cycle: S1 → Z1 → ZE1 with profit visible
- Can monitor multiple symbols in state overview table
- Esc key stops backtest within 1 second
- Emergency stop button is always visible and prominent

**Priority:** P0 - Completes MVP vertical slice

---

### Epic 2: Complete Strategy Configuration
**Goal:** Trader can create, customize, and save their own pump detection strategies with all 5 sections.

**User Value:** "I can build exactly the strategy I want - my conditions, my thresholds, my rules."

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR9, FR37, FR38

**Stories:**
1. **Create New Strategy** - Start fresh with empty strategy (FR1)
2. **Configure S1 (Signal Detection)** - Set pump detection thresholds (FR2)
3. **Configure O1 (Cancellation)** - Set false signal filter conditions (FR3)
4. **Configure Z1 (Entry Confirmation)** - Set entry conditions (FR4)
5. **Configure ZE1 (Exit with Profit)** - Set profit-taking conditions (FR5)
6. **Configure E1 (Emergency Exit)** - Set stop-loss conditions (FR6)
7. **Indicator Selection** - Choose which indicators to use in conditions (FR7)
8. **View Strategy Configuration** - Readable display of current strategy (FR9)
9. **Strategy Validation** - Validate schema before save and on backend receive (FR37, FR38)
10. **Starter Strategy Templates** - Pre-built templates: Conservative, Moderate, Aggressive *(Trader A)*
11. **Expert Mode Toggle** - Option to show S1/Z1/E1 labels instead of human vocabulary *(Trader C)*

**Success Criteria:**
- Can create strategy from scratch with all 5 sections
- Can start from template and customize
- Validation prevents invalid strategies from saving
- Expert mode toggle persists in user preferences
- Templates have sensible defaults for different risk tolerances

**Priority:** P1 - After MVP proves system works

**Why standalone:** Strategy Builder exists but may need completion/verification. After this epic, any strategy can be created and saved.

---

### Epic 3: Transparency & Diagnostics
**Goal:** Trader understands WHY every signal fired or didn't fire - complete transparency into system decisions.

**User Value:** "I understand exactly what the system sees. When nothing triggers, I know why. When something triggers, I can trace the reason."

**FRs covered:** FR21, FR23, FR32, FR33, FR35, FR36
**UX covered:** UX-5 (TransitionBadge), UX-3 (ConditionProgress enhanced), UX-8 (O1 "False Alarm" explanation)

**Note:** FR34 (debug panel) moved to Epic 0 for development velocity.

**Stories:**
1. **Signal History Panel** - Chronological list of all signals during session (FR21)
2. **State Machine Transition History** - Log of all state changes with triggers (FR23)
3. **"Why No Signal" Diagnostics** - Show closest threshold approach when no signal fires (FR32)
4. **Continuous Indicator Values** - Display indicator values even when no signals (FR33)
5. **Condition Pass/Fail Display** - Show which conditions passed/failed during evaluation (FR35)
6. **Transition Tracing** - Trace why each signal/transition occurred with indicator values (FR36)
7. **TransitionBadge Component** - Inline "why" explanation for every state change (UX-5)
8. **Enhanced ConditionProgress** - Visual progress toward each threshold with percentage (UX-3)
9. **Raw Data Export (CSV)** - Export trade history and signals to CSV for external analysis *(Trader C)*

**Success Criteria:**
- Every transition shows WHY it happened
- "Why No Signal" shows how close each condition was to triggering
- Signal history includes all relevant indicator values
- CSV export includes: timestamp, signal type, indicator values, P&L
- Trader C can import data into their own analysis tools

**Priority:** P1 - Critical for trust and debugging

**Why standalone:** Diagnostics are CORE to the trader experience (per PRD User Journey 2), not an afterthought. This epic builds trust.

---

### Epic 4: Production Reliability
**Goal:** System is production-ready with no silent failures, proper error handling, and graceful recovery.

**User Value:** "I can trust this system with real money. It tells me when something's wrong and helps me recover."

**FRs covered:** FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR39, FR41, FR42
**NFRs addressed:** NFR7 (no silent failures), NFR8 (auto-reconnect), NFR9 (resumable), NFR10 (persist config), NFR11 (graceful degradation)
**UX covered:** UX-30, UX-31, UX-32, UX-33 (error handling UX)

**Note:** FR24 (connection status) and FR40 (error display) moved to Epic 0 as foundation.
**Note:** FR31 (stop backtest) moved to Epic 1B with emergency stop.

**IMPORTANT CLARIFICATION (from Trader B feedback):**
FR10-FR17 (Signal Generation) are **VERIFICATION** of existing functionality, NOT new implementation. The StrategyManager and signal generation code already exist. This epic verifies they work correctly for all 5 signal types and adds comprehensive tests.

**Stories:**
1. **Verify S1 Signal Generation** - Test pump detection signals generate correctly (FR11)
2. **Verify O1 Signal Generation** - Test cancellation signals generate correctly (FR12)
3. **Verify Z1 Signal Generation** - Test entry signals generate correctly (FR13)
4. **Verify ZE1 Signal Generation** - Test exit signals generate correctly (FR14)
5. **Verify E1 Signal Generation** - Test emergency signals generate correctly (FR15)
6. **Verify Indicator Calculations** - Test all MVP indicators calculate accurately (FR16)
7. **Verify State Machine Transitions** - Test all state transitions follow correct logic (FR17)
8. **Condition Evaluation Testing** - Comprehensive tests for FR10
9. **Pre-flight Check Before Backtest** - Verify data requirements, connection before start (FR39)
10. **Auto-reconnect on Disconnect** - WebSocket reconnects within 2 seconds (FR41, NFR8)
11. **Recovery Options on Error** - User can resume/restart after error (FR42)
12. **Full-Screen Critical Errors** - Errors impossible to miss (UX-30)
13. **Reconnect Banner** - Visible auto-reconnect status (UX-32)

**Success Criteria:**
- All 5 signal types generate correctly (verified by tests)
- Indicator calculations match expected values
- State machine follows correct transition logic
- Auto-reconnect works within 2 seconds
- Recovery options always available
- Critical errors are impossible to miss

**Priority:** P2 - Required before live trading
**Priority Note (Trader B):** If 3-month live trading timeline is firm, consider elevating to P1 or starting early in parallel with Epic 2/3.

**Why standalone:** Includes signal generation verification and all reliability features. After this epic, the system is ready for paper/live trading.

---

### Epic 5: Dashboard Experience Polish
**Goal:** Beautiful, state-driven UI with custom components that create confidence and delight.

**User Value:** "The dashboard is intuitive and delightful. I understand everything at a glance. Wins feel great, and I learn from losses."

**UX covered:**
- State-driven layouts (UX-14, UX-15, UX-16)
- Visual design polish (UX-18 through UX-20)
- Keyboard shortcuts (UX-21, UX-22)
- Sound alerts & celebrations (UX-23, UX-24, UX-25)
- Accessibility (UX-26 through UX-29)
- Success moments (UX-34, UX-35, UX-36, UX-37)
- NowPlayingBar, DeltaDisplay (UX-4, UX-6)

**Note:** Core UX (StatusHero, human vocabulary, colors) moved to Epic 1A.

**Priority:** P3 - Polish after core functionality works

**Why standalone:** UX polish enhances experience but core functionality works without it.

---

## Epic Summary (First Principles + Pre-mortem + Focus Group)

| Epic | Name | Stories | Priority | User Value |
|------|------|---------|----------|------------|
| 0 | Foundation & Pipeline Unblock | 8 | P0 (foundation) | "Plumbing works, I can debug" |
| 1A | First Signal Visible | 8 | P0 | "I see a signal!" |
| 1B | First Successful Backtest | 9 | P0 | "I made simulated profit!" |
| 2 | Complete Strategy Configuration | 11 | P1 | "I can build my strategy" |
| 3 | Transparency & Diagnostics | 9 | P1 | "I understand why" |
| 4 | Production Reliability | 13 | P2* | "I can trust it" |
| 5 | Dashboard Experience Polish | UX | P3 | "It's beautiful & intuitive" |

**Total:** 42 FRs + 37 UX requirements covered across 6 epics + 1 foundation

*\* P2 but consider P1 if 3-month live trading timeline is firm (Trader B feedback)*

**Pre-mortem Protections Built In:**
- Epic 0 includes verification (not just "fix applied")
- Epic 1 split for faster first win
- Debug panel early for development velocity
- Core UX in Epic 1A (not deferred)
- Error display pattern from day 1

**Focus Group Additions:**
- Trader A: Onboarding tooltip, quick start, starter templates
- Trader B: State overview table, emergency stop + Esc, multi-symbol, priority note for Epic 4
- Trader C: Expert mode toggle, CSV export, Esc shortcut

---

## Future Roadmap (Post-MVP)

Based on User Persona Focus Group feedback, these features are valuable but not required for MVP:

### Phase 2: Advanced Features (Trader C Requests)
| Feature | Persona | Description |
|---------|---------|-------------|
| **REST API Access** | Trader C | API endpoints for scripting and external tools |
| **Multi-Strategy Execution** | Trader C | Run 3-5 strategies simultaneously on different symbols |
| **Advanced Data Export** | Trader C | JSON export, webhook integration for real-time data |
| **Custom Indicator Support** | Trader C | Define custom indicators beyond MVP set |

### Phase 3: Enhanced Experience (All Personas)
| Feature | Persona | Description |
|---------|---------|-------------|
| **Full Onboarding Wizard** | Trader A | Step-by-step tutorial for new users |
| **Strategy Sharing** | All | Export/import strategies, community templates |
| **Session History & Analytics** | Trader B | Browse past sessions, performance analysis |
| **Replay Mode** | All | Step through historical sessions to learn |
| **Mobile Emergency Access** | Trader B | Emergency close from mobile device |

### Phase 4: Ecosystem (Future Vision)
| Feature | Description |
|---------|-------------|
| **Strategy Marketplace** | Share and discover community strategies |
| **Backtesting as a Service** | Cloud-based backtesting for larger datasets |
| **Real-Time Alerts** | Push notifications for signals and P&L thresholds |
| **Multi-Exchange Support** | Beyond MEXC to Binance, Bybit, etc. |

---

## Detailed Epic Breakdown with Stories

<!-- Stories generated with full acceptance criteria -->

## Epic 0: Foundation & Pipeline Unblock

**Goal:** Establish a solid foundation with verified signal flow, development visibility, and error patterns.

### Story 0.1: Fix EventBridge Signal Subscription

**As a** developer,
**I want** the EventBridge to subscribe to the correct "signal_generated" event,
**So that** signals from StrategyManager reach the WebSocket clients.

**Acceptance Criteria:**

**Given** the backend is running with StrategyManager active
**When** StrategyManager publishes a "signal_generated" event
**Then** EventBridge receives the event and forwards it to WebSocket clients
**And** the WebSocket message contains: type, stream, data, timestamp fields

**Given** the current EventBridge code at `/src/api/event_bridge.py:631`
**When** the subscription is changed from "signal.flash_pump_detected" to "signal_generated"
**Then** the existing 596 backend tests still pass
**And** no other event subscriptions are broken

**Technical Notes:**
- Single file change: `/src/api/event_bridge.py`
- Reference Architecture Decision 3 for exact fix code

---

### Story 0.2: E2E Signal Flow Verification

**As a** developer,
**I want** visual proof that signals flow from backend to the StatusHero component on the dashboard,
**So that** I can confirm the pipeline is working before building more features.

**Acceptance Criteria:**

**Given** Story 0.1 (EventBridge fix) is complete
**When** I trigger a test signal from the backend (via backtest or manual trigger)
**Then** the signal appears in the StatusHero component on the dashboard within 500ms
**And** the signal shows the correct state (e.g., "Found!" with fire emoji)

**Given** browser DevTools Network tab open on WebSocket connection
**When** a signal is generated by StrategyManager
**Then** the WebSocket message is visible in the Network tab
**And** the message payload matches the expected contract (type, stream, data, timestamp)

**Given** React DevTools installed
**When** a signal arrives via WebSocket
**Then** the dashboardStore (or relevant Zustand store) shows the updated signal data
**And** StatusHero component re-renders with new state

**Technical Notes:**
- This is a VERIFICATION story, not a feature story
- Success = screenshot/recording showing signal on dashboard
- Blocks all Epic 1A stories until verified

---

### Story 0.3: Signal Contract Validation

**As a** developer,
**I want** the backend signal payload to match the frontend TypeScript types exactly,
**So that** signals are correctly parsed and displayed without runtime errors.

**Acceptance Criteria:**

**Given** the backend Pydantic model for signal events in `/src/domain/models/signals.py`
**When** I compare it to the frontend TypeScript interface in `/frontend/src/types/`
**Then** all field names match exactly (snake_case in both)
**And** all field types are compatible (string↔string, number↔float/int, etc.)

**Given** a signal_generated event is published by StrategyManager
**When** the frontend receives it via WebSocket
**Then** TypeScript can parse it without type errors
**And** no `undefined` values appear for expected fields

**Given** the signal contract includes these required fields:
- `signal_type`: string (S1, O1, Z1, ZE1, E1)
- `symbol`: string
- `timestamp`: ISO8601 string
- `indicator_values`: object with MVP indicators
- `state_machine_state`: string
**When** any field is missing or malformed
**Then** the frontend logs a contract violation error (not silent failure)

**Technical Notes:**
- Create or update `/docs/api/signal-contract.md` documenting the contract
- Consider adding runtime validation with zod or similar on frontend
- This prevents the "payload mismatch" failure mode from pre-mortem

---

### Story 0.4: Verify Zustand Store Updates

**As a** developer,
**I want** to confirm that WebSocket signals update the Zustand store correctly,
**So that** React components re-render when new signals arrive.

**Acceptance Criteria:**

**Given** the WebSocket service receives a signal message
**When** the message is parsed successfully
**Then** the appropriate Zustand store action is called (e.g., `addSignal`, `updateState`)
**And** the store state reflects the new signal data

**Given** React DevTools with Zustand devtools middleware enabled
**When** a signal arrives via WebSocket
**Then** I can see the state change in the Redux/Zustand DevTools panel
**And** the action name and payload are visible for debugging

**Given** a component subscribed to the signal store (e.g., StatusHero)
**When** the store updates with a new signal
**Then** the component re-renders within 100ms
**And** the new signal data is displayed correctly

**Given** multiple rapid signals arrive (simulating pump detection)
**When** signals arrive faster than 100ms apart
**Then** all signals are processed without dropping any
**And** the UI updates show the latest state (no flickering or stale data)

**Technical Notes:**
- Verify store location: `/frontend/src/stores/dashboardStore.ts` or similar
- Ensure devtools middleware is enabled for debugging
- Test with React DevTools Profiler to confirm re-renders

---

### Story 0.5: Strategy Builder Audit

**As a** trader,
**I want** to verify that saving and loading strategies works correctly,
**So that** I can trust my configurations persist between sessions.

**Acceptance Criteria:**

**Given** the Strategy Builder page is loaded
**When** I create a new strategy with at least one condition configured
**Then** I can save the strategy with a name
**And** a success message confirms the save

**Given** a previously saved strategy exists
**When** I navigate to the Strategy Builder and select "Load Strategy"
**Then** the saved strategy appears in the list
**And** I can load it into the builder

**Given** a loaded strategy in the Strategy Builder
**When** I compare the loaded configuration to the original
**Then** all fields match exactly (thresholds, indicators, conditions)
**And** no data is lost or corrupted during save/load cycle

**Given** the backend API endpoint for strategies
**When** I save a strategy from the frontend
**Then** the strategy is persisted to the backend storage
**And** it survives a browser refresh and backend restart

**Given** an invalid strategy configuration (e.g., missing required fields)
**When** I attempt to save it
**Then** validation errors are displayed to the user
**And** the save is prevented until errors are corrected

**Technical Notes:**
- This audits existing FR8 functionality
- Check: `/src/api/strategy_routes.py` for backend endpoints
- Check: `/frontend/src/components/strategy-builder/` for frontend
- Document any bugs found for immediate fixing

---

### Story 0.6: Debug Panel Foundation

**As a** developer,
**I want** a debug panel that shows raw WebSocket messages,
**So that** I can troubleshoot signal flow issues during development.

**Acceptance Criteria:**

**Given** the application is running in development mode
**When** I access the debug panel (via keyboard shortcut or menu)
**Then** a panel opens showing real-time WebSocket messages
**And** messages are displayed with timestamp, type, and payload

**Given** the debug panel is open
**When** a WebSocket message arrives
**Then** it appears at the top of the message list (newest first)
**And** the message is color-coded by type (signal=amber, error=red, data=blue)

**Given** the debug panel contains messages
**When** I click on a message row
**Then** the full payload is expanded in a formatted JSON view
**And** I can copy the payload to clipboard

**Given** the debug panel is active
**When** I type in the filter input
**Then** messages are filtered by type or content
**And** I can filter to show only "signal" type messages

**Given** I am in production mode (NODE_ENV=production)
**When** I try to access the debug panel
**Then** it is not available (hidden or disabled)
**And** no debug information is exposed to end users

**Technical Notes:**
- Keyboard shortcut suggestion: Ctrl+Shift+D or backtick (`)
- Store last 100 messages in memory (configurable)
- Consider using existing MUI Drawer component
- FR34 requirement

---

### Story 0.7: Error Display Pattern

**As a** trader,
**I want** all errors to be clearly visible in the UI,
**So that** I never miss critical issues that could affect my trading.

**Acceptance Criteria:**

**Given** any error occurs in the application (API, WebSocket, validation)
**When** the error is caught
**Then** it is displayed in the UI using a consistent error pattern
**And** it is NOT silently logged only to console

**Given** a non-critical error occurs (e.g., failed to load optional data)
**When** the error is displayed
**Then** it appears as a dismissible toast/snackbar (MUI Snackbar)
**And** the error message is human-readable (not stack trace)
**And** it auto-dismisses after 5 seconds

**Given** a critical error occurs (e.g., WebSocket disconnected, backend unreachable)
**When** the error is displayed
**Then** it appears as a persistent banner at the top of the screen
**And** it does NOT auto-dismiss
**And** it includes a recovery action button (e.g., "Retry", "Reconnect")

**Given** an error occurs during a trading session
**When** the error is displayed
**Then** the error includes context (what operation failed, when)
**And** position-related errors are highlighted with red background
**And** sound alert plays for critical errors (if sound enabled)

**Given** the error display system is implemented
**When** I search the codebase for `console.error` without UI display
**Then** no instances are found in user-facing code paths
**And** all error paths route through the central error handler

**Technical Notes:**
- Create `/frontend/src/utils/errorHandler.ts` or similar
- Use MUI Snackbar for non-critical, Alert for critical
- FR40, NFR7 requirements
- Pattern: `handleError(error, { critical: boolean, context: string })`

---

### Story 0.8: Connection Status Indicator

**As a** trader,
**I want** to see the WebSocket connection status at all times,
**So that** I know immediately if I'm disconnected from the trading system.

**Acceptance Criteria:**

**Given** the application is loaded
**When** the WebSocket connection is healthy
**Then** a green indicator (dot or icon) is visible in the header/status bar
**And** hovering shows "Connected" with connection duration

**Given** the WebSocket connection drops
**When** the connection status changes to disconnected
**Then** the indicator turns red immediately (within 1 second)
**And** a tooltip or label shows "Disconnected - Reconnecting..."
**And** if a position is active, a warning banner also appears

**Given** the WebSocket is reconnecting
**When** reconnection attempts are in progress
**Then** the indicator shows amber/yellow with a pulsing animation
**And** the tooltip shows "Reconnecting... (attempt X of Y)"

**Given** the WebSocket successfully reconnects
**When** the connection is restored
**Then** the indicator returns to green
**And** a brief success toast confirms "Connection restored"
**And** the system resumes receiving signals automatically

**Given** reconnection fails after maximum attempts
**When** the connection cannot be restored
**Then** the indicator stays red
**And** a persistent error banner shows "Connection failed - Click to retry"
**And** manual retry button is available

**Technical Notes:**
- Position in header: top-right near user menu
- Use existing WebSocket service connection state
- FR24, NFR8 requirements
- Consider: small dot for minimal mode, expanded for trading session

---

### Epic 0 Summary

| Story | Title | Type | FRs/ARCH |
|-------|-------|------|----------|
| 0.1 | Fix EventBridge Signal Subscription | Fix | ARCH-1 |
| 0.2 | E2E Signal Flow Verification | Verification | ARCH-7,8,9 |
| 0.3 | Signal Contract Validation | Verification | - |
| 0.4 | Verify Zustand Store Updates | Verification | - |
| 0.5 | Strategy Builder Audit | Audit | FR8 |
| 0.6 | Debug Panel Foundation | Feature | FR34 |
| 0.7 | Error Display Pattern | Pattern | FR40, NFR7 |
| 0.8 | Connection Status Indicator | Feature | FR24, NFR8 |

**Total: 8 stories** | **Epic 0 Complete**

---

## Epic 1A: First Signal Visible

**Goal:** Trader sees their FIRST signal appear on the dashboard - the "aha!" moment.

### Story 1A.1: Signal Display on Dashboard

**As a** trader,
**I want** to see signals displayed prominently on my dashboard when they are detected,
**So that** I know immediately when a trading opportunity arises.

**Acceptance Criteria:**

**Given** the dashboard is open and connected to WebSocket
**When** a signal (S1/O1/Z1/ZE1/E1) is generated by the backend
**Then** the signal appears on the dashboard within 500ms
**And** the signal is displayed in a prominent, visible location

**Given** a signal is displayed on the dashboard
**When** I look at the signal element
**Then** I can see the signal type, symbol, and timestamp
**And** the signal is visually distinct from other dashboard elements

**Given** multiple signals arrive in sequence
**When** a new signal arrives
**Then** it is displayed as the current/active signal
**And** the previous signal moves to signal history (if implemented)

**Given** the dashboard is showing a signal
**When** I hover over the signal element
**Then** I see additional details (indicator values that triggered it)

**Technical Notes:**
- Build on Epic 0 verified signal flow
- Use dashboardStore for signal state
- FR18 requirement
- Position: prominent area, visible without scrolling

---

### Story 1A.2: State Machine State Badge

**As a** trader,
**I want** to see the current state machine state displayed as a prominent badge,
**So that** I always know which phase of the trading cycle I'm in.

**Acceptance Criteria:**

**Given** the dashboard is loaded
**When** the state machine is in MONITORING state
**Then** a large badge displays "Watching" with 👀 icon
**And** the badge background is slate/muted color (#64748B)

**Given** the state machine transitions to SIGNAL_DETECTED (S1)
**When** the state changes
**Then** the badge updates to "Found!" with 🔥 icon
**And** the badge background changes to amber (#F59E0B)
**And** the transition happens within 100ms

**Given** the state machine is in any state
**When** I look at the state badge
**Then** the badge is at least 24px font size (prominent)
**And** the badge position is consistent (same location regardless of state)
**And** the icon and text are clearly readable

**Given** the following state-to-display mappings:
- MONITORING → "Watching" 👀 (slate)
- S1/SIGNAL_DETECTED → "Found!" 🔥 (amber)
- O1/CANCELLED → "False Alarm" ❌ (gray)
- Z1/ENTRY → "Entering" 🎯 (blue)
- POSITION_ACTIVE → "Monitoring" 📈 (blue)
- ZE1/EXIT_PROFIT → "Taking Profit" 💰 (green)
- E1/EXIT_LOSS → "Stopping Loss" 🛑 (red)
**When** the state machine is in that state
**Then** the badge shows the corresponding display

**Technical Notes:**
- FR19 requirement
- UX-7 through UX-13 vocabulary transformation
- UX-17 color system
- Component: StateBadge or part of StatusHero

---

### Story 1A.3: Indicator Values Panel

**As a** trader,
**I want** to see real-time indicator values on the dashboard,
**So that** I understand the market conditions driving signal detection.

**Acceptance Criteria:**

**Given** the dashboard is loaded during a trading/backtest session
**When** indicator values are received via WebSocket
**Then** the indicator panel displays current values for all MVP indicators
**And** values update in real-time as new data arrives

**Given** the MVP indicator set includes:
- TWPA (Time-Weighted Price Average)
- pump_magnitude_pct
- volume_surge_ratio
- price_velocity
- spread_pct
- unrealized_pnl_pct (when position active)
**When** viewing the indicator panel
**Then** each indicator is displayed with its name and current value
**And** values are formatted appropriately (% for percentages, decimals for ratios)

**Given** an indicator value changes
**When** the new value is significantly different (>5% change)
**Then** the value briefly highlights (flash or color change)
**And** the display updates smoothly without flicker

**Given** the indicator panel is displayed
**When** I look at an indicator
**Then** I can see a trend arrow (↑↓→) showing direction
**And** the arrow color indicates bullish (green) / bearish (red) / neutral (gray)

**Given** indicator values are not yet available (session starting)
**When** the indicator panel is displayed
**Then** it shows placeholder text "Waiting for data..."
**And** no stale or zero values are displayed

**Technical Notes:**
- FR20 requirement
- Use monospace font (JetBrains Mono) for numeric values
- Consider compact vs expanded view modes
- Location: side panel or below StatusHero

---

### Story 1A.4: Human Vocabulary Labels

**As a** trader,
**I want** to see human-readable labels instead of technical codes like S1/Z1/E1,
**So that** I can understand the system without memorizing abbreviations.

**Acceptance Criteria:**

**Given** the UI displays any state machine state or signal type
**When** the data contains technical codes (S1, O1, Z1, ZE1, E1)
**Then** the UI displays human labels instead:
- S1 → "Found!" or "Signal Detected"
- O1 → "False Alarm" or "Cancelled"
- Z1 → "Entering" or "Entry Confirmed"
- ZE1 → "Taking Profit" or "Exit - Profit"
- E1 → "Stopping Loss" or "Exit - Emergency"
- MONITORING → "Watching"
- POSITION_ACTIVE → "Monitoring Position"

**Given** the data contract uses technical codes (signal_type: "S1")
**When** the frontend receives and processes this data
**Then** the technical code is preserved in data/state
**And** only the UI display layer transforms to human vocabulary
**And** no data corruption occurs from the transformation

**Given** a vocabulary mapping utility exists
**When** I need to display any signal type
**Then** I can call `getHumanLabel(technicalCode)` to get the display text
**And** I can call `getIcon(technicalCode)` to get the emoji/icon
**And** I can call `getColor(technicalCode)` to get the theme color

**Given** a future "Expert Mode" toggle is planned
**When** implementing the vocabulary transformation
**Then** the transformation is centralized in one utility file
**And** it can be easily bypassed when Expert Mode is enabled

**Technical Notes:**
- UX-7 through UX-13 requirements
- Create: `/frontend/src/utils/vocabulary.ts`
- Data contracts remain unchanged (per pre-mortem clarification)
- UI-only transformation, not data transformation

---

### Story 1A.5: StatusHero Component

**As a** trader,
**I want** a prominent combined display showing current state and key metrics,
**So that** I can understand my trading situation at a glance.

**Acceptance Criteria:**

**Given** the dashboard is loaded
**When** no trading session is active
**Then** StatusHero displays "Ready to Trade" in a calm/neutral state
**And** it shows connection status and last update time

**Given** a trading/backtest session is active
**When** in MONITORING state
**Then** StatusHero displays the state badge ("Watching" 👀)
**And** shows the active symbol and strategy name
**And** uses minimal/calm visual styling (slate colors)

**Given** a signal is detected (S1)
**When** StatusHero updates
**Then** the component expands to "Command Center" mode
**And** displays: state badge, signal type, symbol, timestamp
**And** uses prominent/alert visual styling (amber background)
**And** the transition animates smoothly (300ms)

**Given** a position is active
**When** StatusHero displays position information
**Then** P&L is shown in large text (48-64px per UX spec)
**And** P&L is color-coded: green for profit, red for loss
**And** shows unrealized P&L with +/- prefix and $ symbol

**Given** StatusHero is the primary dashboard element
**When** I view it from normal reading distance
**Then** I can understand the current situation within 2 seconds
**And** the most important information has visual hierarchy (largest = most important)

**Technical Notes:**
- UX-1 requirement (StatusHero Component)
- UX-14, 15, 16 (state-driven information density)
- UX-19 (hero metric size 48-64px)
- UX-20 (2-second comprehension rule)
- This is the CORE UI component - all other elements support it

---

### Story 1A.6: Signal Type Color Coding

**As a** trader,
**I want** different signal types to have distinct visual colors,
**So that** I can immediately identify the type of signal without reading text.

**Acceptance Criteria:**

**Given** the UX color system defines:
- Slate (#64748B) = Monitoring/Watching
- Amber (#F59E0B) = Signal Detected (S1)
- Blue (#3B82F6) = Position Active / Entry (Z1)
- Green (#10B981) = Profit / Exit with Profit (ZE1)
- Red (#EF4444) = Loss / Emergency Exit (E1)
- Gray (#6B7280) = Cancelled / False Alarm (O1)
**When** any signal or state is displayed
**Then** the corresponding color is applied to backgrounds, badges, and icons

**Given** a signal is displayed on the dashboard
**When** I view the signal element
**Then** the background or border uses the signal type color
**And** the color contrast meets WCAG 2.1 AA standards (4.5:1 for text)

**Given** the color coding is applied
**When** viewed by a color-blind user
**Then** icons/shapes supplement the colors (per UX-28)
**And** profit uses upward arrow (↑), loss uses downward arrow (↓)
**And** the meaning is clear without relying solely on color

**Given** multiple signals are displayed (e.g., in history)
**When** I scan the signal list
**Then** different signal types are visually distinguishable by color
**And** I can identify patterns (e.g., "lots of red = many false alarms")

**Given** dark mode is enabled
**When** colors are displayed
**Then** the colors remain distinguishable and accessible
**And** the palette adjusts for dark backgrounds (lighter tints if needed)

**Technical Notes:**
- FR22 requirement
- UX-17 color system
- UX-28 color-blind support
- Create: `/frontend/src/theme/signalColors.ts` or extend MUI theme

---

### Story 1A.7: First-Visit Onboarding Tooltip

**As a** new trader (Trader A persona),
**I want** a helpful tooltip explaining the dashboard when I first visit,
**So that** I understand what I'm looking at without reading documentation.

**Acceptance Criteria:**

**Given** a user visits the dashboard for the first time
**When** the dashboard loads
**Then** a friendly tooltip/popover appears near the StatusHero component
**And** the tooltip says something like: "Welcome! This is your trading dashboard. Signals will appear here when detected."

**Given** the onboarding tooltip is displayed
**When** I click "Got it" or click outside the tooltip
**Then** the tooltip dismisses
**And** a localStorage flag is set to prevent showing it again

**Given** the onboarding has been dismissed previously
**When** I return to the dashboard
**Then** the tooltip does NOT appear again
**And** the user experience is clean without repeated interruptions

**Given** the user wants to see the onboarding again
**When** they access Settings or Help menu
**Then** there is an option to "Reset Onboarding Tips"
**And** clicking it clears the localStorage flag

**Given** the tooltip is displayed
**When** viewing on different screen sizes
**Then** the tooltip is positioned appropriately (not off-screen)
**And** it does not overlap critical UI elements

**Technical Notes:**
- Trader A persona feature (first-time user experience)
- Use MUI Popover or Tooltip component
- localStorage key: `fx_agent_onboarding_seen`
- Keep text concise (max 2 sentences)
- Consider: future expansion to multi-step tour

---

### Story 1A.8: Quick Start Option

**As a** new trader (Trader A persona),
**I want** a button to quickly start with a default strategy,
**So that** I can see signals immediately without configuring everything first.

**Acceptance Criteria:**

**Given** I am on the dashboard with no active session
**When** I look for ways to start trading
**Then** I see a prominent "Quick Start" or "Try Demo" button
**And** the button is visible without scrolling

**Given** I click the "Quick Start" button
**When** the action is triggered
**Then** a default/template strategy is automatically loaded
**And** a backtest session starts with a pre-selected symbol (e.g., BTCUSDT)
**And** I do NOT need to configure anything manually

**Given** the Quick Start session begins
**When** the backtest runs
**Then** signals start appearing on the dashboard
**And** I can see the system working immediately
**And** a subtle indicator shows "Demo Mode" or "Quick Start Session"

**Given** I want to customize after Quick Start
**When** I access the Strategy Builder
**Then** the loaded template strategy is available for editing
**And** I can modify thresholds and save as my own strategy

**Given** no saved strategies exist for a new user
**When** I visit the dashboard for the first time
**Then** Quick Start is emphasized as the primary action
**And** secondary option "Create Custom Strategy" is also available

**Technical Notes:**
- Trader A persona feature
- Requires: at least one template strategy in the system
- Requires: default symbol with available historical data
- Consider: use the "Conservative" template from Epic 2
- Quick Start should work even before Epic 2 is complete (hardcoded template)

---

### Epic 1A Summary

| Story | Title | Type | FRs/UX |
|-------|-------|------|--------|
| 1A.1 | Signal Display on Dashboard | Feature | FR18 |
| 1A.2 | State Machine State Badge | Feature | FR19, UX-7-13 |
| 1A.3 | Indicator Values Panel | Feature | FR20 |
| 1A.4 | Human Vocabulary Labels | Feature | UX-7-13 |
| 1A.5 | StatusHero Component | Feature | UX-1, UX-14-16, UX-19-20 |
| 1A.6 | Signal Type Color Coding | Feature | FR22, UX-17, UX-28 |
| 1A.7 | First-Visit Onboarding Tooltip | Feature | Trader A |
| 1A.8 | Quick Start Option | Feature | Trader A |

**Total: 8 stories** | **Epic 1A Complete**

