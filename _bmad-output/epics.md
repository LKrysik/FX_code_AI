---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - "_bmad-output/prd.md"
  - "_bmad-output/architecture.md"
  - "_bmad-output/ux-design-specification.md"
workflowType: 'epics-and-stories'
lastStep: 4
project_name: 'FX Agent AI'
user_name: 'Mr Lu'
date: '2025-12-21'
validation_date: '2025-12-26'
validation_status: 'PASSED'
mvp_story_count: 57
deferred_story_count: 14
total_story_count: 71
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
| SEC-0 | Critical Security Fixes | 3 | P0 | "System is secure" |
| 1A | First Signal Visible | 8 | P0 | "I see a signal!" |
| **BUG-003** | **Paper Trading Session Fixes** | **11** | **P0** | **"Paper trading works correctly"** |
| 1B | First Successful Backtest | 9 | P0 | "I made simulated profit!" |
| 2 | Complete Strategy Configuration | 11 | P1 | "I can build my strategy" |
| 3 | Transparency & Diagnostics | 9 | P1 | "I understand why" |
| 4 | Production Reliability | 13 | P2* | "I can trust it" |
| 5 | Dashboard Experience Polish | UX | P3 | "It's beautiful & intuitive" |

**Total:** 42 FRs + 37 UX requirements covered across 6 epics + 1 foundation + 2 bug fix epics

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

## Bug Fix Epics

### Epic SEC-0: Critical Security Fixes
**Goal:** Address critical security vulnerabilities before feature development.

**User Value:** "The system is secure and won't have race conditions or injection attacks."

**Status:** DONE (completed 2025-12-27)

**Stories:**
1. **Position Operation Locking** - PositionLockManager prevents race conditions (14 tests)
2. **Strategy JSON Validation** - Allowlist validation, security logging
3. **WebSocket State Reconciliation** - State desync fix for reliable connections

---

### Epic BUG-003: Paper Trading Session Critical Fixes
**Goal:** Fix critical bugs blocking Paper Trading session discovered 2025-12-27.

**User Value:** "When I start a Paper Trading session, it shows ONLY what I selected with real indicator values."

**Source:** `docs/bug_003.md` + `logs/frontend_error.log` + `logs/backend.log`

**Status:** BACKLOG - Priority P0

**Log Analysis Evidence:**
- Positions API 404: 249 occurrences (ActivePositionBanner.tsx:92)
- Pump Indicators API 500: 236 occurrences (PumpIndicatorsPanel.tsx:522)
- Live Indicators API 500: 95 occurrences (LiveIndicatorPanel.tsx:68)
- Backend OSError: Order persistence failure `[Errno 22] Invalid argument`
- active_count: 4 strategies running when 1 selected

**Stories:**
1. **Session Strategy Filtering** - Fix: Multiple strategies shown when 1 selected (P0)
2. **Session Symbol Filtering** - Fix: Wrong symbols (BTC_USDT instead of selected) (P0)
3. **Pump Indicators API 500** - Fix: API error 500 (236 occurrences) (P0)
4. **Indicator Values Missing** - Fix: Values show "--" not actual values (P0)
5. **Live Indicators Duplicates** - Fix: Duplicate AEVO_USDT entries (P1)
6. **Active Positions Display** - Fix: Oversized symbol, API 404 (249 occurrences) (P1)
7. **Page Refresh Flickering** - Fix: Severe UI flickering/jumping (P1)
8. **Condition Progress Collapse** - Fix: Auto-collapse on data refresh (P2)
9. **UX Designer Review** - Overall interface readability review (P2)
10. **E2E Test Coverage** - E2E tests for paper/live/backtest flows (P1)
11. **Order Persistence OSError** - Fix: Backend OSError on order save (P0)

**Full details:** `_bmad-output/stories/bug-003-epic.md`

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

### Story 1A.0: Create Shared Utilities

**As a** developer,
**I want** shared utility modules for vocabulary, colors, and formatters,
**So that** all dashboard components use consistent transformations.

**Acceptance Criteria:**

**Given** the vocabulary utility exists
**When** I import from `/frontend/src/utils/vocabulary.ts`
**Then** I can use: `getHumanLabel()`, `getIcon()`, `getTechnicalCode()`
**And** all signal types (S1, O1, Z1, ZE1, E1) are mapped

**Given** the colors utility exists
**When** I import from `/frontend/src/utils/signalColors.ts`
**Then** I can use: `getSignalColor()`, `getStateColor()`
**And** colors match UX spec (Amber, Blue, Green, Red, Slate)

**Given** the formatters utility exists
**When** I import from `/frontend/src/utils/formatters.ts`
**Then** I can use: `formatPnL()`, `formatPercent()`, `formatTimestamp()`
**And** formatting is consistent across all components

**Given** these utilities are created first
**When** other Epic 1A stories are implemented
**Then** they can import and use these shared utilities
**And** no circular dependencies exist

**Technical Notes:**
- Bootstrap Paradox resolution: Create shared deps FIRST
- These utilities enable Stories 1A.1-1A.8
- Export from index.ts for clean imports

---

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

### Story 1A.7: First-Visit Onboarding Tooltip [DEFERRED - POST-MVP]

**Status:** DEFERRED per Braess Paradox analysis - adds complexity for single-user MVP

**As a** new trader (Trader A persona),
**I want** a helpful tooltip explaining the dashboard when I first visit,
**So that** I understand what I'm looking at without reading documentation.

**Acceptance Criteria:**
- Tooltip appears on first visit near StatusHero
- Dismisses on click, persists preference in localStorage
- Can be reset from Settings

**Technical Notes:**
- DEFERRED: Developer is the user for MVP
- Move to Phase 2 when onboarding new users

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

| Story | Title | Type | FRs/UX | Status |
|-------|-------|------|--------|--------|
| 1A.0 | Create Shared Utilities | Foundation | - | MVP |
| 1A.1 | Signal Display on Dashboard | Feature | FR18 | MVP |
| 1A.2 | State Machine State Badge | Feature | FR19, UX-7-13 | MVP |
| 1A.3 | Indicator Values Panel | Feature | FR20 | MVP |
| 1A.4 | Human Vocabulary Labels | Feature | UX-7-13 | MVP |
| 1A.5 | StatusHero Component | Feature | UX-1, UX-14-16, UX-19-20 | MVP |
| 1A.6 | Signal Type Color Coding | Feature | FR22, UX-17, UX-28 | MVP |
| 1A.7 | First-Visit Onboarding Tooltip | Feature | Trader A | DEFERRED |
| 1A.8 | Quick Start Option | Feature | Trader A | MVP |

**Total: 9 stories (8 MVP + 1 Deferred)** | **Epic 1A Complete**

---

## Epic 1B: First Successful Backtest

**Goal:** Trader runs a complete backtest and sees P&L results.

### Story 1B.1: Backtest Session Setup

**As a** trader,
**I want** to configure and start a backtest session,
**So that** I can test my strategy against historical data.

**Acceptance Criteria:**

**Given** I navigate to the backtest setup page/modal
**When** I view the setup form
**Then** I can select a strategy from my saved strategies
**And** I can select a trading symbol (e.g., BTCUSDT, ETHUSDT)
**And** I can select a date range for historical data

**Given** I am selecting a date range
**When** I use the date picker
**Then** I can select start date and end date
**And** the system validates that historical data exists for that range
**And** a warning shows if data is incomplete or missing

**Given** I have configured all required fields
**When** I click "Start Backtest"
**Then** the backtest session begins
**And** I am redirected to the dashboard to watch progress
**And** the setup form validates all fields before starting

**Given** required fields are missing
**When** I try to start the backtest
**Then** validation errors highlight the missing fields
**And** the start button is disabled until all required fields are filled

**Technical Notes:**
- FR25 (start backtest), FR26 (select period), FR27 (select symbol)
- Use MUI DatePicker for date range selection
- API: POST /api/backtest/start with strategy_id, symbol, start_date, end_date

---

### Story 1B.2: Backtest Execution

**As a** trader,
**I want** the system to simulate trading on historical data,
**So that** I can see how my strategy would have performed.

**Acceptance Criteria:**

**Given** a backtest session has been started
**When** the backend processes historical data
**Then** the StrategyManager evaluates conditions against each data point
**And** signals are generated when conditions are met
**And** simulated trades are executed based on signals

**Given** the backtest is running
**When** a simulated trade is executed
**Then** entry price, exit price, and P&L are recorded
**And** the trade is added to the session's trade history

**Given** the backtest encounters an error
**When** the error is non-fatal (e.g., missing data point)
**Then** the backtest continues with a warning logged
**And** the error is reported in the final summary

**Given** the backtest encounters a fatal error
**When** the error prevents continuation
**Then** the backtest stops gracefully
**And** partial results are preserved
**And** the error is displayed to the user

**Technical Notes:**
- FR28 (simulate trading execution)
- Backend: BacktestEngine processes data in batches
- Signals sent via WebSocket to frontend for real-time display
- NFR4: Must process 10x faster than real-time

---

### Story 1B.3: Progress Display

**As a** trader,
**I want** to see the backtest progress in real-time,
**So that** I know how much longer it will take and can follow along.

**Acceptance Criteria:**

**Given** a backtest is running
**When** I view the dashboard
**Then** I see a progress indicator (percentage or progress bar)
**And** I see the current simulation timestamp
**And** I see estimated time remaining

**Given** the backtest is processing data
**When** progress updates are received via WebSocket
**Then** the progress bar updates smoothly
**And** updates occur at least every 1 second

**Given** the backtest progress is displayed
**When** I look at the progress section
**Then** I see: X% complete, current date being processed, signals found so far
**And** the display is compact but informative

**Given** the backtest completes
**When** 100% is reached
**Then** the progress indicator shows "Complete"
**And** the P&L summary automatically appears

**Technical Notes:**
- FR29 (view backtest progress)
- WebSocket message: { type: "backtest_progress", percent: 45, current_time: "2024-01-15T10:30:00" }
- Use MUI LinearProgress component

---

### Story 1B.4: P&L Summary

**As a** trader,
**I want** to see a clear summary of my backtest results,
**So that** I can evaluate my strategy's performance.

**Acceptance Criteria:**

**Given** a backtest has completed
**When** the results are displayed
**Then** I see total P&L (profit or loss) prominently displayed
**And** P&L is color-coded (green for profit, red for loss)
**And** P&L shows both absolute value ($) and percentage (%)

**Given** the P&L summary is displayed
**When** I review the statistics
**Then** I see: total trades, winning trades, losing trades, win rate
**And** I see: largest win, largest loss, average trade
**And** I see: total signals generated per type (S1, Z1, ZE1, E1)

**Given** I want more details
**When** I click "View Trade History"
**Then** I see a table of all simulated trades
**And** each trade shows: timestamp, signal type, entry price, exit price, P&L

**Given** the backtest had no trades
**When** results are displayed
**Then** a message explains "No trades executed - consider adjusting thresholds"
**And** diagnostic info shows closest threshold approaches

**Technical Notes:**
- FR30 (view backtest results P&L)
- Hero P&L display: 48-64px font size per UX spec
- Consider: export to CSV option (deferred to Epic 3)

---

### Story 1B.5: JourneyBar Component

**As a** trader,
**I want** to see a visual representation of the trading flow,
**So that** I can understand where I am in the trading cycle.

**Acceptance Criteria:**

**Given** the JourneyBar is displayed on the dashboard
**When** I view it
**Then** I see the trading flow as connected steps: Watch → Found → Enter → Monitor → Exit
**And** each step is represented by an icon and label

**Given** the state machine is in a specific state
**When** that state corresponds to a journey step
**Then** the current step is highlighted (bold, colored, or glowing)
**And** completed steps show a checkmark
**And** future steps are dimmed/grayed

**Given** the state machine transitions
**When** a new state is entered
**Then** the JourneyBar animates to the new position
**And** the animation is smooth (300ms transition)

**Given** the journey has multiple possible outcomes
**When** displaying exit states
**Then** "Exit" step shows the specific outcome (Profit/Loss)
**And** color reflects outcome (green for profit, red for loss)

**Technical Notes:**
- UX-2 (JourneyBar Navigation)
- Horizontal layout for desktop, consider vertical for mobile
- Use MUI Stepper component as base, customize styling

---

### Story 1B.6: Signal Timeline on Chart

**As a** trader,
**I want** to see where signals occurred on a price chart,
**So that** I can visualize the strategy's behavior over time.

**Acceptance Criteria:**

**Given** a backtest has completed or is running
**When** I view the chart section
**Then** the price chart shows the historical price data
**And** signal markers appear at the corresponding timestamps

**Given** signals are displayed on the chart
**When** I look at a marker
**Then** each signal type has a distinct icon/color
**And** S1 signals show as amber diamonds
**And** Z1 (entry) shows as blue arrows pointing up
**And** ZE1/E1 (exit) shows as green/red arrows pointing down

**Given** I hover over a signal marker
**When** the tooltip appears
**Then** I see: signal type, timestamp, indicator values at that moment
**And** for exits: entry price, exit price, P&L

**Given** multiple signals are close together
**When** zoomed out on the chart
**Then** signals cluster visually without overlapping
**And** I can zoom in to see individual signals

**Technical Notes:**
- Consider: lightweight-charts library or existing chart component
- Markers overlay on price candles
- Performance: limit to 1000 markers visible at once

---

### Story 1B.7: State Overview Table

**As a** trader running multiple symbols (Trader B),
**I want** to see all active sessions in a single table view,
**So that** I can monitor multiple instruments at once.

**Acceptance Criteria:**

**Given** I have one or more active sessions
**When** I view the State Overview Table
**Then** I see a row for each active symbol/session
**And** each row shows: symbol, current state, last signal, P&L

**Given** a session updates
**When** new data arrives via WebSocket
**Then** the corresponding row updates in real-time
**And** changed values briefly highlight

**Given** I want to focus on one session
**When** I click on a row
**Then** the main dashboard focuses on that session
**And** StatusHero and other components show that session's details

**Given** no sessions are active
**When** I view the table
**Then** an empty state message appears: "No active sessions. Start a backtest to begin."

**Technical Notes:**
- Trader B persona feature
- Use MUI DataGrid or Table component
- Support 1-10 simultaneous sessions
- Consider: collapsible when single session active

---

### Story 1B.8: Emergency Stop Button + Esc Shortcut

**As a** trader,
**I want** to immediately stop any running backtest or trading session,
**So that** I can halt operations quickly in an emergency.

**Acceptance Criteria:**

**Given** a session is running (backtest or live)
**When** I look for the stop control
**Then** a prominent red "STOP" button is always visible
**And** the button is labeled clearly (not just an icon)

**Given** I press the Esc key
**When** a session is active
**Then** a confirmation dialog appears: "Stop session? This cannot be undone."
**And** I can confirm with Enter or cancel with Esc again

**Given** I click the STOP button or confirm the dialog
**When** the stop command is sent
**Then** the session stops within 1 second
**And** any open simulated positions are closed at current price
**And** the final P&L is calculated and displayed

**Given** the session has stopped
**When** viewing the dashboard
**Then** the status shows "Stopped by user"
**And** partial results are preserved and viewable

**Given** I want to disable the Esc shortcut
**When** I access Settings
**Then** I can toggle "Esc to stop session" on/off

**Technical Notes:**
- FR31 (stop running backtest)
- UX-21 (Esc keyboard shortcut)
- UX-22 (emergency close < 1 second)
- Trader B, C persona features
- API: POST /api/session/stop

---

### Story 1B.9: Multi-Symbol Session Support [DEFERRED - POST-MVP]

**Status:** DEFERRED per Braess Paradox analysis - adds WebSocket routing complexity

**As a** trader (Trader B),
**I want** to run backtests on multiple symbols simultaneously,
**So that** I can test my strategy across different markets.

**Acceptance Criteria:**
- Select 1-3 symbols for simultaneous backtesting
- State Overview Table shows all active sessions
- WebSocket handles messages for all sessions

**Technical Notes:**
- DEFERRED: Start with single symbol for MVP
- Adds session_id routing complexity
- Move to Phase 2 after single-symbol is stable

---

### Epic 1B Summary

| Story | Title | Type | FRs/UX | Status |
|-------|-------|------|--------|--------|
| 1B.1 | Backtest Session Setup | Feature | FR25, FR26, FR27 | MVP |
| 1B.2 | Backtest Execution | Feature | FR28 | MVP |
| 1B.3 | Progress Display | Feature | FR29 | MVP |
| 1B.4 | P&L Summary | Feature | FR30 | MVP |
| 1B.5 | JourneyBar Component | Feature | UX-2 | MVP |
| 1B.6 | Signal Timeline on Chart | Feature | - | MVP |
| 1B.7 | State Overview Table | Feature | Trader B | MVP |
| 1B.8 | Emergency Stop Button + Esc | Feature | FR31, UX-21, UX-22 | MVP |
| 1B.9 | Multi-Symbol Session Support | Feature | Trader B | DEFERRED |

**Total: 9 stories (8 MVP + 1 Deferred)** | **Epic 1B Complete**

---

## Epic 2: Complete Strategy Configuration

**Goal:** Trader can create, customize, and save their own pump detection strategies with all 5 sections.

### Story 2.1: Create New Strategy

**As a** trader,
**I want** to create a new strategy from scratch,
**So that** I can build a custom trading approach tailored to my needs.

**Acceptance Criteria:**

**Given** I navigate to the Strategy Builder
**When** I click "Create New Strategy"
**Then** a new empty strategy is initialized
**And** I am prompted to enter a strategy name
**And** all 5 sections (S1, O1, Z1, ZE1, E1) are shown as unconfigured

**Given** I am creating a new strategy
**When** I enter a name and click "Create"
**Then** the strategy is created with default/empty conditions
**And** I can immediately begin configuring sections

**Given** a strategy with that name already exists
**When** I try to create with a duplicate name
**Then** a validation error shows "Strategy name already exists"
**And** I must choose a different name

**Technical Notes:**
- FR1 requirement
- API: POST /api/strategies with { name, sections: {} }
- Default state: all sections empty, strategy not yet valid

---

### Story 2.2: Configure S1 (Signal Detection)

**As a** trader,
**I want** to configure the S1 (Signal Detection) section,
**So that** I can define when a pump is initially detected.

**Acceptance Criteria:**

**Given** I am editing a strategy's S1 section
**When** I view the configuration form
**Then** I see available indicators (TWPA, pump_magnitude_pct, volume_surge_ratio, price_velocity, spread_pct)
**And** I can set threshold values for each indicator
**And** I can set comparison operators (>, <, >=, <=, ==)

**Given** I am configuring a condition
**When** I set an indicator and threshold
**Then** I can combine multiple conditions with AND/OR logic
**And** the UI shows a visual representation of the condition tree

**Given** I have configured S1 conditions
**When** I save the section
**Then** the conditions are validated for completeness
**And** invalid conditions show specific error messages
**And** valid conditions are persisted to the strategy

**Technical Notes:**
- FR2 requirement
- S1 triggers transition from MONITORING to SIGNAL_DETECTED
- UI: condition builder with drag-drop or form-based approach

---

### Story 2.3: Configure O1 (Cancellation)

**As a** trader,
**I want** to configure the O1 (Cancellation) section,
**So that** I can filter out false signals before entering a position.

**Acceptance Criteria:**

**Given** I am editing a strategy's O1 section
**When** I view the configuration form
**Then** I see the same indicators available as S1
**And** I can define conditions that would cancel the signal

**Given** O1 conditions are configured
**When** a signal is detected (S1 fires)
**Then** O1 conditions are evaluated
**And** if O1 triggers, the signal is cancelled (False Alarm)
**And** the state returns to MONITORING

**Given** O1 is optional
**When** I leave O1 unconfigured
**Then** the strategy is still valid
**And** signals proceed directly from S1 to Z1 evaluation

**Technical Notes:**
- FR3 requirement
- O1 is optional - strategies work without it
- O1 triggers transition from SIGNAL_DETECTED back to MONITORING

---

### Story 2.4: Configure Z1 (Entry Confirmation)

**As a** trader,
**I want** to configure the Z1 (Entry Confirmation) section,
**So that** I can define when to actually enter a position.

**Acceptance Criteria:**

**Given** I am editing a strategy's Z1 section
**When** I view the configuration form
**Then** I can set entry confirmation conditions
**And** these conditions must be met after S1 fires (and O1 doesn't cancel)

**Given** Z1 conditions are configured
**When** S1 fires and O1 doesn't cancel
**Then** Z1 conditions are continuously evaluated
**And** when Z1 triggers, a position is entered
**And** the state transitions to POSITION_ACTIVE

**Given** Z1 conditions include timing
**When** configuring Z1
**Then** I can set a timeout (e.g., "confirm within 30 seconds of S1")
**And** if timeout expires without Z1, signal is cancelled

**Technical Notes:**
- FR4 requirement
- Z1 triggers position entry
- Consider: position sizing configuration (future epic)

---

### Story 2.5: Configure ZE1 (Exit with Profit)

**As a** trader,
**I want** to configure the ZE1 (Exit with Profit) section,
**So that** I can define my profit-taking conditions.

**Acceptance Criteria:**

**Given** I am editing a strategy's ZE1 section
**When** I view the configuration form
**Then** I can set profit target conditions
**And** I can use unrealized_pnl_pct as an indicator
**And** I can set absolute profit targets (e.g., +5%)

**Given** ZE1 conditions are configured
**When** a position is active
**Then** ZE1 conditions are continuously evaluated
**And** when ZE1 triggers, the position is closed with profit
**And** the state transitions to exit and then MONITORING

**Given** I want multiple profit targets
**When** configuring ZE1
**Then** I can set tiered targets (e.g., 50% at +3%, rest at +5%)
**And** partial exits are supported (future enhancement flag)

**Technical Notes:**
- FR5 requirement
- ZE1 = happy path exit
- Consider: trailing stop configuration (future)

---

### Story 2.6: Configure E1 (Emergency Exit)

**As a** trader,
**I want** to configure the E1 (Emergency Exit) section,
**So that** I can define stop-loss and emergency exit conditions.

**Acceptance Criteria:**

**Given** I am editing a strategy's E1 section
**When** I view the configuration form
**Then** I can set stop-loss conditions
**And** I can use unrealized_pnl_pct (negative) as an indicator
**And** I can set absolute loss limits (e.g., -3%)

**Given** E1 conditions are configured
**When** a position is active
**Then** E1 conditions are continuously evaluated
**And** when E1 triggers, the position is closed immediately
**And** the state transitions to exit and then MONITORING

**Given** E1 is critical for risk management
**When** a strategy has no E1 configured
**Then** a warning is shown: "No stop-loss configured - high risk"
**And** the user must acknowledge the warning to save

**Technical Notes:**
- FR6 requirement
- E1 = unhappy path exit (stop loss)
- E1 should be evaluated with highest priority

---

### Story 2.7: Indicator Selection

**As a** trader,
**I want** to select which indicators to use in my conditions,
**So that** I can build conditions using relevant market data.

**Acceptance Criteria:**

**Given** I am building a condition in any section
**When** I need to select an indicator
**Then** I see a list of available MVP indicators:
- TWPA (Time-Weighted Price Average)
- pump_magnitude_pct
- volume_surge_ratio
- price_velocity
- spread_pct
- unrealized_pnl_pct (only in ZE1/E1 when position active)

**Given** I select an indicator
**When** viewing its details
**Then** I see a description of what the indicator measures
**And** I see typical value ranges
**And** I see suggested thresholds for common strategies

**Given** an indicator is not applicable to a section
**When** viewing indicator options
**Then** the indicator is disabled or hidden
**And** a tooltip explains why it's not available

**Technical Notes:**
- FR7 requirement
- unrealized_pnl_pct only available when position exists
- Consider: indicator preview showing current/recent values

---

### Story 2.8: View Strategy Configuration

**As a** trader,
**I want** to view my strategy configuration in a readable format,
**So that** I can review and understand my complete strategy.

**Acceptance Criteria:**

**Given** I have a configured strategy
**When** I view the strategy summary
**Then** I see all 5 sections displayed clearly
**And** each section shows its conditions in human-readable format

**Given** the strategy summary is displayed
**When** I review a section
**Then** conditions read like sentences (e.g., "When pump_magnitude_pct > 5%")
**And** AND/OR logic is clearly shown
**And** empty sections are marked as "Not configured"

**Given** I want a quick overview
**When** I view the strategy card/tile
**Then** I see: strategy name, creation date, last modified
**And** I see a summary badge showing configured sections (e.g., "S1 ✓ O1 ✓ Z1 ✓ ZE1 ✓ E1 ✓")

**Technical Notes:**
- FR9 requirement
- Consider: export strategy as JSON/YAML for backup
- Human-readable format uses vocabulary transformation

---

### Story 2.9: Strategy Validation

**As a** trader,
**I want** my strategy to be validated before saving,
**So that** I don't accidentally create an invalid or broken strategy.

**Acceptance Criteria:**

**Given** I attempt to save a strategy
**When** validation runs
**Then** all sections are checked for completeness
**And** condition logic is verified (no circular references, valid operators)
**And** indicator references are verified (indicators exist)

**Given** validation fails
**When** errors are found
**Then** specific error messages indicate what's wrong
**And** the problematic section/field is highlighted
**And** the save is prevented until errors are fixed

**Given** validation passes on frontend
**When** the strategy is sent to backend
**Then** the backend re-validates before persisting
**And** any backend validation errors are returned to frontend
**And** consistency between frontend and backend validation is maintained

**Given** a strategy lacks minimum requirements
**When** I try to save
**Then** I'm warned: "At least S1 and one exit (ZE1 or E1) must be configured"

**Technical Notes:**
- FR37 (frontend validation), FR38 (backend validation)
- Validation schema shared between frontend and backend
- Consider: JSON Schema for strategy definition

---

### Story 2.10: Starter Strategy Template (Simplified)

**As a** new trader (Trader A),
**I want** a pre-built strategy template,
**So that** I can start with a proven configuration and customize from there.

**Acceptance Criteria:**

**Given** I access the Strategy Builder
**When** I choose to create from template
**Then** I see one "Default Template" option (balanced/moderate settings)

**Given** I select the template
**When** the template loads
**Then** all 5 sections are pre-configured with sensible defaults:
- S1: pump_magnitude_pct > 3%, volume_surge_ratio > 2.0
- O1: (optional, not configured by default)
- Z1: price_velocity > 0.5%
- ZE1: unrealized_pnl_pct > 5%
- E1: unrealized_pnl_pct < -3%
**And** I can immediately use the strategy or customize it

**Given** I want to customize the template
**When** I modify any section
**Then** changes are applied to my copy
**And** the original template remains unchanged

**Technical Notes:**
- SIMPLIFIED per Braess Paradox: One template instead of three
- Template stored as JSON in /data/templates/default.json
- Conservative/Aggressive templates deferred to Phase 2

---

### Story 2.11: Expert Mode Toggle

**As an** experienced trader (Trader C),
**I want** to see technical signal names (S1/Z1/E1) instead of human labels,
**So that** I can work with the system using precise technical terminology.

**Acceptance Criteria:**

**Given** Expert Mode is disabled (default)
**When** viewing signals and states
**Then** human vocabulary is used ("Found!", "Taking Profit", etc.)

**Given** I enable Expert Mode in settings
**When** viewing signals and states
**Then** technical codes are shown (S1, O1, Z1, ZE1, E1)
**And** the UI layout remains the same (only labels change)

**Given** Expert Mode preference is set
**When** I close and reopen the application
**Then** my preference is persisted
**And** the chosen vocabulary mode is applied immediately

**Given** I'm in a mixed team environment
**When** sharing screenshots
**Then** I can quickly toggle between modes for communication

**Technical Notes:**
- Trader C persona feature
- localStorage: `fx_agent_expert_mode: boolean`
- Toggle in Settings page or quick-access menu

---

### Epic 2 Summary

| Story | Title | Type | FRs |
|-------|-------|------|-----|
| 2.1 | Create New Strategy | Feature | FR1 |
| 2.2 | Configure S1 (Signal Detection) | Feature | FR2 |
| 2.3 | Configure O1 (Cancellation) | Feature | FR3 |
| 2.4 | Configure Z1 (Entry Confirmation) | Feature | FR4 |
| 2.5 | Configure ZE1 (Exit with Profit) | Feature | FR5 |
| 2.6 | Configure E1 (Emergency Exit) | Feature | FR6 |
| 2.7 | Indicator Selection | Feature | FR7 |
| 2.8 | View Strategy Configuration | Feature | FR9 |
| 2.9 | Strategy Validation | Feature | FR37, FR38 |
| 2.10 | Starter Strategy Templates | Feature | Trader A |
| 2.11 | Expert Mode Toggle | Feature | Trader C |

**Total: 11 stories** | **Epic 2 Complete**

---

## Epic 3: Transparency & Diagnostics

**Goal:** Trader understands WHY every signal fired or didn't fire - complete transparency into system decisions.

### Story 3.1: Signal History Panel

**As a** trader,
**I want** to see a chronological list of all signals during my session,
**So that** I can review what happened and when.

**Acceptance Criteria:**

**Given** a session is active or completed
**When** I view the Signal History Panel
**Then** I see all signals in reverse chronological order (newest first)
**And** each entry shows: timestamp, signal type (human vocab), symbol

**Given** signals are displayed
**When** I click on a signal entry
**Then** I see expanded details: indicator values at that moment, trigger reason

**Given** the session has many signals
**When** viewing the history
**Then** the list is scrollable and paginated (or virtual scroll)
**And** I can filter by signal type (S1 only, exits only, etc.)

**Technical Notes:**
- FR21 requirement
- Store signals in session store, limit to last 1000
- Consider: grouping by trade cycle (S1→Z1→exit as one group)

---

### Story 3.2: State Machine Transition History

**As a** trader,
**I want** to see a log of all state changes with their triggers,
**So that** I can understand the complete state machine journey.

**Acceptance Criteria:**

**Given** I access the Transition History
**When** viewing the log
**Then** I see all state transitions: from_state → to_state, timestamp, trigger

**Given** a transition entry is displayed
**When** I look at the trigger
**Then** I see which signal or condition caused the transition
**And** for timeouts/cancellations, the reason is shown

**Given** I want to trace a specific journey
**When** I filter by trade cycle
**Then** I see only transitions for that cycle (S1→...→exit)
**And** the complete path is visible as a connected sequence

**Technical Notes:**
- FR23 requirement
- Log format: { from, to, trigger, timestamp, details }
- Consider: visual timeline view (like git log)

---

### Story 3.3: "Why No Signal" Diagnostics

**As a** trader,
**I want** to see why no signal is firing when I expect one,
**So that** I can debug my strategy thresholds.

**Acceptance Criteria:**

**Given** the system is monitoring but no S1 has fired
**When** I access "Why No Signal" diagnostics
**Then** I see each S1 condition and its current progress
**And** progress shows: current_value vs threshold, percentage to trigger

**Given** the diagnostics are displayed
**When** viewing a condition's progress
**Then** I see: "pump_magnitude_pct: 3.2% (64% of 5% threshold)"
**And** the closest-to-triggering condition is highlighted

**Given** conditions use AND logic
**When** some conditions pass but others don't
**Then** passing conditions show ✓ green
**And** blocking conditions show ✗ red with gap amount

**Given** I want real-time updates
**When** market data changes
**Then** the diagnostics update in real-time
**And** I can watch conditions approach thresholds

**Technical Notes:**
- FR32 requirement
- Calculate: (current_value / threshold) * 100 for progress
- For > comparisons: show % of way there
- For < comparisons: show how far below

---

### Story 3.4: Continuous Indicator Values

**As a** trader,
**I want** to see indicator values even when no signals are firing,
**So that** I can monitor market conditions continuously.

**Acceptance Criteria:**

**Given** a session is active
**When** I view the indicator panel
**Then** all MVP indicators show current values at all times
**And** values update in real-time (every tick or every second)

**Given** indicators are updating
**When** a value changes significantly
**Then** the change is visually indicated (brief highlight)
**And** I can see trend direction (↑↓→)

**Given** no signals are firing
**When** I monitor indicators
**Then** I can still see all values and trends
**And** the display is not blank or hidden

**Given** historical context is useful
**When** viewing an indicator
**Then** I can see a mini sparkline showing recent values
**And** sparkline covers last 1-5 minutes (configurable)

**Technical Notes:**
- FR33 requirement
- WebSocket: continuous indicator stream, not just signal-triggered
- Consider: throttle updates to prevent UI lag (max 10/second)

---

### Story 3.5: Condition Pass/Fail Display

**As a** trader,
**I want** to see which conditions passed or failed during signal evaluation,
**So that** I can understand exactly why a signal did or didn't fire.

**Acceptance Criteria:**

**Given** a signal is being evaluated
**When** I view the condition status
**Then** each condition in the section shows pass ✓ or fail ✗
**And** the overall result (AND/OR logic) is shown

**Given** a condition fails
**When** viewing the fail details
**Then** I see: condition definition, current value, threshold, gap
**And** the display is color-coded (green=pass, red=fail)

**Given** a signal fires
**When** I view why it fired
**Then** I see all conditions that were evaluated
**And** I can see which conditions were critical (AND) vs optional (OR)

**Technical Notes:**
- FR35 requirement
- Display alongside signal in history and real-time
- Consider: collapsible section for condition details

---

### Story 3.6: Transition Tracing

**As a** trader,
**I want** to trace exactly why each signal or transition occurred,
**So that** I can fully understand my strategy's behavior.

**Acceptance Criteria:**

**Given** a state transition has occurred
**When** I click "Why?" on the transition
**Then** I see a detailed breakdown:
- Which conditions triggered
- Exact indicator values at trigger time
- Time elapsed since previous state

**Given** a signal led to a trade
**When** I trace the complete journey
**Then** I see the chain: S1 trigger → Z1 confirm → entry → ZE1/E1 exit
**And** each step shows its trigger conditions

**Given** I want to compare to expectations
**When** viewing a trace
**Then** I can see threshold vs actual for each condition
**And** I can identify if the trigger was marginal or strong

**Technical Notes:**
- FR36 requirement
- Store indicator snapshots at each transition
- Consider: export trace as JSON for offline analysis

---

### Story 3.7: TransitionBadge Component

**As a** trader,
**I want** to see inline explanations for every state change,
**So that** transitions are self-documenting and understandable.

**Acceptance Criteria:**

**Given** a state transition occurs on the dashboard
**When** the transition is displayed
**Then** a TransitionBadge appears showing "Why: [reason]"
**And** the badge is positioned near the state indicator

**Given** the TransitionBadge is displayed
**When** I read the reason
**Then** it's human-readable (e.g., "Why: pump_magnitude exceeded 5%")
**And** technical details are available on hover/click

**Given** multiple transitions happen quickly
**When** badges would overlap
**Then** only the most recent badge is shown prominently
**And** older transitions are available in history

**Technical Notes:**
- UX-5 requirement
- Badge auto-dismisses after 5 seconds or on next transition
- Use MUI Chip or custom badge component

---

### Story 3.8: Enhanced ConditionProgress

**As a** trader,
**I want** to see visual progress bars for each condition,
**So that** I can quickly gauge how close conditions are to triggering.

**Acceptance Criteria:**

**Given** the dashboard shows condition progress
**When** I view a condition
**Then** I see a horizontal progress bar
**And** the bar shows current value as percentage of threshold

**Given** a condition is close to triggering (>80%)
**When** viewing the progress bar
**Then** the bar color changes to amber/warning
**And** a subtle pulse animation indicates "almost there"

**Given** a condition triggers (100%)
**When** the threshold is crossed
**Then** the bar fills completely and flashes green
**And** the transition occurs

**Given** conditions are displayed
**When** I want to see details
**Then** hovering shows: current value, threshold, percentage
**And** click expands to show historical trend

**Technical Notes:**
- UX-3 (ConditionProgress enhanced)
- Progress = min(current/threshold * 100, 100)
- Handle inverse conditions (< threshold) appropriately

---

### Story 3.9: Raw Data Export (CSV)

**As an** experienced trader (Trader C),
**I want** to export my trade history and signals to CSV,
**So that** I can analyze data in my own tools (Excel, Python, etc.).

**Acceptance Criteria:**

**Given** a session has completed
**When** I click "Export to CSV"
**Then** a CSV file is generated and downloaded
**And** the filename includes session date and symbol

**Given** the CSV export
**When** I open it
**Then** it contains columns: timestamp, signal_type, symbol, indicator values, P&L
**And** each row is a signal or trade event

**Given** I want to export trade history
**When** I select "Trades Only" option
**Then** the CSV contains only completed trades
**And** each trade shows: entry_time, exit_time, entry_price, exit_price, P&L

**Given** I want raw signal data
**When** I select "All Signals" option
**Then** the CSV contains every signal including cancelled ones
**And** O1 cancellations are marked with reason

**Technical Notes:**
- Trader C persona feature (CSV export)
- Use browser download API
- Consider: JSON export option for programmatic access

---

### Epic 3 Summary

| Story | Title | Type | FRs/UX |
|-------|-------|------|--------|
| 3.1 | Signal History Panel | Feature | FR21 |
| 3.2 | State Machine Transition History | Feature | FR23 |
| 3.3 | "Why No Signal" Diagnostics | Feature | FR32 |
| 3.4 | Continuous Indicator Values | Feature | FR33 |
| 3.5 | Condition Pass/Fail Display | Feature | FR35 |
| 3.6 | Transition Tracing | Feature | FR36 |
| 3.7 | TransitionBadge Component | Feature | UX-5 |
| 3.8 | Enhanced ConditionProgress | Feature | UX-3 |
| 3.9 | Raw Data Export (CSV) | Feature | Trader C |

**Total: 9 stories** | **Epic 3 Complete**

---

## Epic 4: Production Reliability

**Goal:** System is production-ready with verified signal generation, proper error handling, and graceful recovery.

### Story 4.1: Verify S1 Signal Generation

**As a** developer,
**I want** comprehensive tests verifying S1 signals generate correctly,
**So that** pump detection works reliably in production.

**Acceptance Criteria:**

**Given** the StrategyManager evaluates S1 conditions
**When** all S1 conditions are met
**Then** an S1 signal is generated with correct payload
**And** the signal includes: type, timestamp, symbol, indicator_values

**Given** S1 conditions are partially met
**When** evaluation runs
**Then** no S1 signal is generated
**And** diagnostics show which conditions failed

**Given** edge cases exist (boundary values)
**When** values are exactly at threshold
**Then** >= and > operators behave correctly
**And** tests verify boundary behavior

**Technical Notes:**
- FR11 requirement (verification)
- Create: /tests/unit/test_s1_signal_generation.py
- Test cases: all pass, some pass, none pass, edge cases

---

### Story 4.2: Verify O1 Signal Generation

**As a** developer,
**I want** tests verifying O1 cancellation signals work correctly,
**So that** false signal filtering is reliable.

**Acceptance Criteria:**

**Given** S1 has fired and O1 is configured
**When** O1 conditions are met
**Then** an O1 signal is generated
**And** the state returns to MONITORING
**And** the S1 signal is marked as cancelled

**Given** O1 conditions are not met
**When** evaluation continues
**Then** no O1 fires
**And** Z1 evaluation proceeds

**Given** O1 is not configured
**When** S1 fires
**Then** O1 evaluation is skipped
**And** processing proceeds to Z1 directly

**Technical Notes:**
- FR12 requirement (verification)
- Create: /tests/unit/test_o1_signal_generation.py

---

### Story 4.3: Verify Z1 Signal Generation

**As a** developer,
**I want** tests verifying Z1 entry signals work correctly,
**So that** position entries are reliable.

**Acceptance Criteria:**

**Given** S1 has fired and O1 hasn't cancelled
**When** Z1 conditions are met
**Then** a Z1 signal is generated
**And** a position entry is triggered
**And** the state transitions to POSITION_ACTIVE

**Given** Z1 has a timeout configured
**When** timeout expires without Z1 triggering
**Then** the signal is cancelled
**And** the state returns to MONITORING

**Technical Notes:**
- FR13 requirement (verification)
- Create: /tests/unit/test_z1_signal_generation.py
- Test: timeout scenarios, rapid confirmation

---

### Story 4.4: Verify ZE1 Signal Generation

**As a** developer,
**I want** tests verifying ZE1 exit signals work correctly,
**So that** profit-taking is reliable.

**Acceptance Criteria:**

**Given** a position is active
**When** ZE1 conditions are met (profit target reached)
**Then** a ZE1 signal is generated
**And** the position is closed
**And** P&L is calculated and recorded

**Given** ZE1 uses unrealized_pnl_pct
**When** calculating P&L percentage
**Then** the calculation is accurate to 2 decimal places
**And** matches expected values in test cases

**Technical Notes:**
- FR14 requirement (verification)
- Create: /tests/unit/test_ze1_signal_generation.py
- Test: various profit levels, edge cases

---

### Story 4.5: Verify E1 Signal Generation

**As a** developer,
**I want** tests verifying E1 emergency exit signals work correctly,
**So that** stop-losses are reliable.

**Acceptance Criteria:**

**Given** a position is active
**When** E1 conditions are met (stop-loss triggered)
**Then** an E1 signal is generated immediately
**And** the position is closed
**And** P&L (negative) is calculated and recorded

**Given** both ZE1 and E1 could trigger
**When** evaluating exit conditions
**Then** E1 is evaluated with higher priority
**And** if both trigger simultaneously, E1 takes precedence

**Technical Notes:**
- FR15 requirement (verification)
- Create: /tests/unit/test_e1_signal_generation.py
- Test: E1 priority over ZE1

---

### Story 4.6: Verify Indicator Calculations

**As a** developer,
**I want** tests verifying all MVP indicators calculate accurately,
**So that** strategy conditions use correct values.

**Acceptance Criteria:**

**Given** market data input
**When** TWPA is calculated
**Then** the result matches expected time-weighted average
**And** calculation handles edge cases (missing data, gaps)

**Given** market data input
**When** all MVP indicators are calculated
**Then** each indicator produces accurate results:
- pump_magnitude_pct: actual vs baseline price change
- volume_surge_ratio: current vs average volume
- price_velocity: rate of price change
- spread_pct: bid-ask spread percentage
- unrealized_pnl_pct: position P&L percentage

**Technical Notes:**
- FR16 requirement (verification)
- Create: /tests/unit/test_indicator_calculations.py
- Use known test data with pre-calculated expected results

---

### Story 4.7: Verify State Machine Transitions

**As a** developer,
**I want** tests verifying all state transitions follow correct logic,
**So that** the trading workflow is reliable.

**Acceptance Criteria:**

**Given** the state machine is in any state
**When** a valid transition trigger occurs
**Then** the state transitions correctly
**And** the transition is logged with details

**Given** an invalid transition is attempted
**When** (e.g., ZE1 from MONITORING)
**Then** the transition is rejected
**And** an error is logged (but not user-facing)

**Given** the complete happy path
**When** MONITORING → S1 → Z1 → POSITION_ACTIVE → ZE1 → MONITORING
**Then** all transitions occur correctly in sequence
**And** P&L is positive and recorded

**Technical Notes:**
- FR17 requirement (verification)
- Create: /tests/unit/test_state_machine.py
- Test: all valid paths, invalid transitions, edge cases

---

### Story 4.8: Condition Evaluation Testing

**As a** developer,
**I want** comprehensive tests for condition evaluation,
**So that** strategy conditions behave predictably.

**Acceptance Criteria:**

**Given** conditions with various operators (>, <, >=, <=, ==)
**When** evaluated against test data
**Then** each operator produces correct boolean result

**Given** conditions with AND logic
**When** all conditions pass
**Then** the overall result is TRUE
**And** if any condition fails, the result is FALSE

**Given** conditions with OR logic
**When** any condition passes
**Then** the overall result is TRUE
**And** only if all fail is the result FALSE

**Given** nested logic (AND + OR combinations)
**When** evaluated
**Then** the logic tree is processed correctly
**And** results match expected outcomes

**Technical Notes:**
- FR10 requirement (comprehensive testing)
- Create: /tests/unit/test_condition_evaluation.py

---

### Story 4.9: Pre-flight Check Before Backtest

**As a** trader,
**I want** the system to verify readiness before starting a backtest,
**So that** I don't waste time on a backtest that will fail.

**Acceptance Criteria:**

**Given** I start a backtest
**When** the pre-flight check runs
**Then** it verifies: historical data exists, strategy is valid, connection is healthy

**Given** historical data is missing
**When** pre-flight check runs
**Then** a clear error shows: "Missing data for [date range]"
**And** the backtest does not start

**Given** the strategy is invalid
**When** pre-flight check runs
**Then** validation errors are shown
**And** the user is directed to fix the strategy

**Given** all checks pass
**When** pre-flight completes
**Then** a brief "Ready to start" confirmation is shown
**And** the backtest begins

**Technical Notes:**
- FR39 requirement
- API: GET /api/backtest/preflight with strategy_id, symbol, date_range
- Return: { ready: boolean, issues: [] }

---

### Story 4.10: Auto-reconnect on Disconnect

**As a** trader,
**I want** the WebSocket to automatically reconnect if disconnected,
**So that** I don't lose signal updates during temporary network issues.

**Acceptance Criteria:**

**Given** the WebSocket connection drops
**When** the disconnect is detected
**Then** reconnection attempts begin immediately
**And** the connection status shows "Reconnecting..."

**Given** reconnection is in progress
**When** attempts are made
**Then** exponential backoff is used (1s, 2s, 4s, max 30s)
**And** attempt count is shown to user

**Given** reconnection succeeds
**When** connection is restored
**Then** the status returns to "Connected"
**And** a success toast confirms "Connection restored"
**And** any missed signals are requested (if supported)

**Given** reconnection fails after max attempts
**When** 10 attempts have failed
**Then** a persistent error banner appears
**And** manual retry button is available

**Technical Notes:**
- FR41, NFR8 requirements
- Use existing WebSocket service reconnect logic
- Target: reconnect within 2 seconds for brief disconnects

---

### Story 4.11: Recovery Options on Error

**As a** trader,
**I want** clear recovery options when errors occur,
**So that** I can resume trading without losing progress.

**Acceptance Criteria:**

**Given** a recoverable error occurs (e.g., network timeout)
**When** the error is displayed
**Then** recovery options are shown: "Retry", "Resume", "Restart"
**And** the most appropriate option is highlighted

**Given** a backtest was interrupted
**When** I return to the application
**Then** I see: "Previous session was interrupted. Resume?"
**And** I can choose to resume from last known state or start over

**Given** I choose to resume
**When** the session restarts
**Then** it continues from the last saved checkpoint
**And** no signals or trades are duplicated or lost

**Given** resume is not possible
**When** data is corrupted or incompatible
**Then** a clear message explains why
**And** only "Start Fresh" option is available

**Technical Notes:**
- FR42 requirement
- Checkpoint storage: save state every N signals or M seconds
- Consider: localStorage for client state, backend for session state

---

### Story 4.12: Full-Screen Critical Errors

**As a** trader,
**I want** critical errors to be impossible to miss,
**So that** I never accidentally trade with a broken system.

**Acceptance Criteria:**

**Given** a critical error occurs (connection lost during active position)
**When** the error is displayed
**Then** a full-screen overlay appears
**And** the error message is large and clear
**And** all other interactions are blocked

**Given** the full-screen error is shown
**When** I read the message
**Then** it explains: what happened, what it means, what to do
**And** action buttons are prominent (e.g., "Reconnect Now")

**Given** the error is resolved
**When** I take the recovery action
**Then** the overlay dismisses
**And** normal operation resumes

**Given** sound is enabled
**When** a critical error occurs
**Then** an alert sound plays
**And** the sound is attention-grabbing but not jarring

**Technical Notes:**
- UX-30 requirement
- Use MUI Dialog with disableEscapeKeyDown
- Critical errors: connection lost during trade, backend crash

---

### Story 4.13: Reconnect Banner

**As a** trader,
**I want** to see a visible status during reconnection,
**So that** I know the system is trying to restore connection.

**Acceptance Criteria:**

**Given** the WebSocket is reconnecting
**When** the status is displayed
**Then** a non-intrusive banner appears at the top of the screen
**And** the banner shows: "Reconnecting... Attempt X"

**Given** the banner is shown
**When** reconnection is in progress
**Then** a spinner or pulsing indicator shows activity
**And** the banner is amber/yellow colored

**Given** reconnection takes longer than 3 seconds
**When** the banner is still visible
**Then** estimated time or "This may take a moment" is shown

**Given** reconnection succeeds
**When** connection is restored
**Then** the banner briefly shows "Connected!" in green
**And** auto-dismisses after 2 seconds

**Technical Notes:**
- UX-32 requirement
- Banner position: fixed to top, below header
- Should not block critical UI elements

---

### Epic 4 Summary

| Story | Title | Type | FRs/NFRs |
|-------|-------|------|----------|
| 4.1 | Verify S1 Signal Generation | Verification | FR11 |
| 4.2 | Verify O1 Signal Generation | Verification | FR12 |
| 4.3 | Verify Z1 Signal Generation | Verification | FR13 |
| 4.4 | Verify ZE1 Signal Generation | Verification | FR14 |
| 4.5 | Verify E1 Signal Generation | Verification | FR15 |
| 4.6 | Verify Indicator Calculations | Verification | FR16 |
| 4.7 | Verify State Machine Transitions | Verification | FR17 |
| 4.8 | Condition Evaluation Testing | Verification | FR10 |
| 4.9 | Pre-flight Check Before Backtest | Feature | FR39 |
| 4.10 | Auto-reconnect on Disconnect | Feature | FR41, NFR8 |
| 4.11 | Recovery Options on Error | Feature | FR42 |
| 4.12 | Full-Screen Critical Errors | Feature | UX-30 |
| 4.13 | Reconnect Banner | Feature | UX-32 |

**Total: 13 stories** | **Epic 4 Complete**

---

## Epic 5: Dashboard Experience Polish [DEFERRED - POST-MVP]

**Status:** ENTIRE EPIC DEFERRED per Theseus Paradox - not core to MVP definition

**Goal:** Beautiful, state-driven UI with custom components that create confidence and delight.

*Note: All 12 stories in this epic are deferred to Phase 2. Core functionality works without polish.*

### Story 5.1: State-Driven Layout - Minimal Focus (MONITORING)

**As a** trader in monitoring state,
**I want** a calm, minimal dashboard layout,
**So that** I'm not distracted while waiting for signals.

**Acceptance Criteria:**
- When in MONITORING state, layout shows only 3-4 key metrics
- Large empty space with subtle "Watching..." indicator
- Colors are muted (slate/gray tones)
- Layout transitions smoothly when state changes

**Technical Notes:** UX-14 requirement

---

### Story 5.2: State-Driven Layout - Command Center (SIGNAL_DETECTED)

**As a** trader when a signal is detected,
**I want** maximum information density,
**So that** I can quickly assess the situation.

**Acceptance Criteria:**
- When in SIGNAL_DETECTED, layout expands to show all relevant data
- Indicator panel, condition progress, signal details all visible
- Colors shift to alert mode (amber background)
- Information hierarchy guides eye to most important elements

**Technical Notes:** UX-15 requirement

---

### Story 5.3: State-Driven Layout - Split Focus (POSITION_ACTIVE)

**As a** trader with an active position,
**I want** P&L prominently displayed with supporting context,
**So that** I can monitor my position without hunting for information.

**Acceptance Criteria:**
- When in POSITION_ACTIVE, P&L is hero element (largest)
- Supporting info (entry price, duration, exit conditions) visible
- Color reflects profit/loss state (green/red)
- Less visual noise than Command Center mode

**Technical Notes:** UX-16 requirement

---

### Story 5.4: Typography System Implementation

**As a** trader,
**I want** consistent, readable typography,
**So that** information is easy to scan and understand.

**Acceptance Criteria:**
- Inter font for UI text (labels, descriptions)
- JetBrains Mono for numbers/prices
- Hero metrics at 48-64px
- Proper font weight hierarchy

**Technical Notes:** UX-18 requirement

---

### Story 5.5: Keyboard Shortcuts (Full Set)

**As a** power user,
**I want** keyboard shortcuts for common actions,
**So that** I can navigate and act quickly.

**Acceptance Criteria:**
- Esc = emergency close (already in 1B.8)
- Space = pause/resume session
- D = focus dashboard
- H = open history
- S = open settings
- Shortcuts displayed in help menu

**Technical Notes:** UX-21 requirement (full implementation)

---

### Story 5.6: Sound Alerts for State Changes

**As a** trader multitasking,
**I want** optional sound alerts for important events,
**So that** I can be notified even when not looking at the screen.

**Acceptance Criteria:**
- Sound plays on: S1 detected, position entered, exit (profit or loss)
- Different sounds for different events
- Volume and enable/disable in settings
- Muted by default (opt-in)

**Technical Notes:** UX-23 requirement

---

### Story 5.7: Celebration Animation on Profitable Exit

**As a** trader,
**I want** a celebration when I exit with profit,
**So that** wins feel rewarding and memorable.

**Acceptance Criteria:**
- Confetti animation on ZE1 exit
- P&L displayed in celebratory style (larger, animated)
- Sound effect (if sound enabled)
- Animation is brief (2-3 seconds) and dismissible

**Technical Notes:** UX-24 requirement

---

### Story 5.8: No-Blame Loss Display

**As a** trader who just took a loss,
**I want** neutral, objective loss explanations,
**So that** I can learn without feeling blamed.

**Acceptance Criteria:**
- Losses displayed neutrally: "Position closed at -X%"
- No red alarm styling (subdued red or gray)
- Explanation shows what triggered E1
- Focus on learning: "Market moved X% against position"

**Technical Notes:** UX-25 requirement

---

### Story 5.9: Dark Mode Support

**As a** trader working at night,
**I want** a dark mode option,
**So that** I can reduce eye strain.

**Acceptance Criteria:**
- Dark mode toggle in settings
- All components support dark theme
- Colors adjusted for dark backgrounds
- Preference persisted

**Technical Notes:** UX requirement (dark mode support)

---

### Story 5.10: Accessibility Compliance

**As a** user with accessibility needs,
**I want** the application to be accessible,
**So that** I can use it effectively.

**Acceptance Criteria:**
- WCAG 2.1 AA compliance
- Focus indicators on all interactive elements (2px solid ring)
- Screen reader compatible labels
- Keyboard navigation works throughout

**Technical Notes:** UX-27, UX-29 requirements

---

### Story 5.11: NowPlayingBar Component

**As a** trader with an active position,
**I want** a persistent footer showing position status,
**So that** I can see my position from any page.

**Acceptance Criteria:**
- When position is active, footer bar appears (Spotify-style)
- Shows: symbol, P&L, duration, state
- Persists even when navigating to other pages
- Click expands to full dashboard

**Technical Notes:** UX-6 requirement

---

### Story 5.12: DeltaDisplay Component

**As a** trader,
**I want** "+$X to target" formatted metrics,
**So that** I can quickly see distance to goals.

**Acceptance Criteria:**
- DeltaDisplay shows: current value, target value, delta
- Formatted as "+$123 to target" or "-2.3% to stop"
- Trend arrows show direction
- Color reflects positive (green) or negative (red) delta

**Technical Notes:** UX-4 requirement

---

### Epic 5 Summary

| Story | Title | Type | UX Req |
|-------|-------|------|--------|
| 5.1 | State-Driven Layout - Minimal | Polish | UX-14 |
| 5.2 | State-Driven Layout - Command Center | Polish | UX-15 |
| 5.3 | State-Driven Layout - Split Focus | Polish | UX-16 |
| 5.4 | Typography System | Polish | UX-18 |
| 5.5 | Keyboard Shortcuts (Full) | Polish | UX-21 |
| 5.6 | Sound Alerts | Polish | UX-23 |
| 5.7 | Celebration Animation | Polish | UX-24 |
| 5.8 | No-Blame Loss Display | Polish | UX-25 |
| 5.9 | Dark Mode Support | Polish | - |
| 5.10 | Accessibility Compliance | Polish | UX-27, UX-29 |
| 5.11 | NowPlayingBar Component | Polish | UX-6 |
| 5.12 | DeltaDisplay Component | Polish | UX-4 |

**Total: 12 stories** | **Epic 5 Complete**

---

## Final Story Count Summary

| Epic | Name | MVP Stories | Deferred | Total |
|------|------|-------------|----------|-------|
| 0 | Foundation & Pipeline Unblock | 8 | 0 | 8 |
| 1A | First Signal Visible | 8 | 1 | 9 |
| 1B | First Successful Backtest | 8 | 1 | 9 |
| 2 | Complete Strategy Configuration | 11 | 0 | 11 |
| 3 | Transparency & Diagnostics | 9 | 0 | 9 |
| 4 | Production Reliability | 13 | 0 | 13 |
| 5 | Dashboard Experience Polish | 0 | 12 | 12 |

**MVP Total: 57 stories** | **Deferred: 14 stories** | **Grand Total: 71 stories**

### Deferred Stories (Post-MVP)

| Story | Title | Reason |
|-------|-------|--------|
| 1A.7 | First-Visit Onboarding Tooltip | Complexity vs MVP value |
| 1B.9 | Multi-Symbol Session Support | Requires session_id routing complexity |
| 5.1-5.12 | All Epic 5 stories | Polish features after core functionality stable |

