---
stepsCompleted: [1, 2, 3, 4, 7, 8, 9, 10, 11]
inputDocuments:
  - "_bmad-output/analysis/brainstorming-session-2025-12-18.md"
  - "_bmad-output/index.md"
  - "_bmad-output/project-context.md"
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 1
  projectDocs: 2
workflowType: 'prd'
lastStep: 11
project_name: 'FX Agent AI'
user_name: 'Mr Lu'
date: '2025-12-18'
---

# Product Requirements Document - FX Agent AI

**Author:** Mr Lu
**Date:** 2025-12-18

## Executive Summary

FX Agent AI is an existing cryptocurrency trading platform with pump & dump detection capabilities. The platform has all core components built - visual strategy builder, 22+ custom indicators, dashboard, backtesting engine, and live trading integration - but the **end-to-end pipeline is disconnected**.

This PRD defines the **repair and integration work** required to connect the existing components into a functioning automated trading system.

### MVP Definition

> "Configure a strategy (even simple) and during a trading/backtesting session SEE on the dashboard: signals, state machine state, indicator values"

### What Makes This Special

**The Gap Being Filled:**
Pipeline disconnection → Full end-to-end automation. When repaired, the system will automatically execute the complete trading cycle without manual intervention.

**Core Insight: Vertical Slice First**
Rather than fixing everything at once, this PRD focuses on repairing ONE complete flow (backtest with pump detection) before expanding to other modes.

**Success Criteria:**
Backtest automatically: detect pump → enter position → exit position → display profit/loss

**Pump & Dump Edge:**
- **Speed:** Faster detection than manual monitoring
- **Early Warning:** Catch pumps in formation, not after the fact
- **Complete Exit Strategy:** 5-section state machine (S1→O1→Z1→ZE1→E1) manages the full position lifecycle
- This combination provides an edge that existing tools don't offer

## Project Classification

**Technical Type:** web_app (Full-stack: FastAPI + Next.js)
**Domain:** fintech (cryptocurrency trading)
**Complexity:** HIGH
**Project Context:** Brownfield - repairing and integrating existing system

### Technical Context

| Layer | Technology | Status |
|-------|------------|--------|
| Backend | Python 3.10+, FastAPI, Clean Architecture + DDD | Built, needs integration |
| Frontend | Next.js 14, TypeScript, MUI, ReactFlow, Zustand | Built, needs connection |
| Database | QuestDB (time-series) | Active |
| Real-time | WebSockets | Active |
| Cache | Redis | Unavailable (Windows, no Docker) |

### Root Causes (from brainstorming analysis)

1. **No reference pattern** - No clear picture of what working system looks like
2. **No MVP definition** - Never defined what minimum must work
3. **Build > Verify mindset** - Priority on building over verifying integration
4. **No E2E tests** - Unit tests pass but pipeline never tested as whole

## Success Criteria

### User Success

**The "Aha!" Moment:**
- Full cycle completion in backtest: S1→Z1→ZE1 with profit
- Visible signals for all state machine sections (S1/O1/Z1/ZE1/E1)
- Clear connection: MY configuration = SYSTEM behavior

**The "Worth It" Moment:**
- **Certainty:** System works exactly as configured
- **Transparency:** Can see WHY each decision was made
- **Trust:** Confidence sufficient for live trading

**Emotional Success:**
- **Relief:** "Finally it works"
- **Excitement:** "This gives me an edge"
- **Confidence:** "I can rely on this"

**One-Sentence Definition:**
> "Trader sees their strategy automatically detects pump, enters, exits with profit - and understands WHY each step happened."

### Business Success

**3-Month Milestones:**

| Month | Target |
|-------|--------|
| M1 | Backtest works end-to-end |
| M2 | Paper trading stable 24/7 |
| M3 | First live trade with real capital |

**Key Metric:**
- **Pipeline Completion Rate ≥ 90%** (signal → position → close)

**12-Month Vision:**
- Multiple strategies running simultaneously
- Personal use → Beta testers → SaaS launch preparation
- Specialization: Pump & Dump detection platform

**2-Year Vision:**
- Platform ready to share/sell

**Priority Principle:**
> "Working MVP for myself" > "SaaS vision"

### Technical Success

**Integration Success:**
- Strategy configuration → Backend processing: connected
- Backend signals → Frontend display: connected
- State machine transitions: visible in real-time

**Reliability:**
- No silent failures - if something breaks, system reports it
- Data consistency between backend calculations and dashboard display
- WebSocket connections stable during sessions

**Testability:**
- Pipeline can be verified without manual checking
- E2E test proves the complete flow works

### Measurable Outcomes

| Outcome | Metric | Target |
|---------|--------|--------|
| Pipeline Integration | Completion Rate | ≥ 90% |
| Signal Visibility | All 5 sections shown | 100% |
| Backtest Reliability | Sessions without crash | ≥ 95% |
| Config-Behavior Match | Config changes reflected | 100% |

## Product Scope

### MVP - Minimum Viable Product

**Core Vertical Slice:**
1. Configure pump detection strategy in Strategy Builder
2. Run backtest session
3. See on dashboard:
   - Generated signals (S1/O1/Z1/ZE1/E1)
   - State machine current state
   - Indicator values (TWPA, pump_magnitude, volume_surge, etc.)
4. Automatic execution: detect → enter → exit
5. View profit/loss result

**MVP Indicators:**
- TWPA (foundation)
- pump_magnitude_pct
- volume_surge_ratio
- price_velocity
- spread_pct
- unrealized_pnl_pct

**FORBIDDEN in MVP:** RSI, EMA, classic TA indicators

### Growth Features (Post-MVP)

- Paper trading mode (24/7 stability)
- Live trading integration
- Multiple simultaneous strategies
- Enhanced dashboard visualizations
- Performance analytics

### Vision (Future)

- Beta tester program
- SaaS platform launch
- Multi-exchange support (beyond MEXC)
- Advanced pump detection algorithms
- Community strategy sharing

## User Journeys

### User Type: Trader (MVP)

The primary user during MVP phase is the trader/owner who configures strategies, runs backtests, and monitors results. The goal is to validate that the pipeline works end-to-end before expanding to paper trading and live trading.

### Journey 1: First Successful Backtest

Mr Lu has been building FX Agent AI for months, but the pipeline has never worked end-to-end. Today, after the repair work, he opens the platform to test if everything finally connects.

He navigates to Strategy Builder and configures a simple pump detection strategy: S1 triggers when pump_magnitude exceeds 7% with volume_surge above 3.5x. Z1 confirms entry when spread is acceptable. ZE1 closes with profit at 15% unrealized P&L.

**Before starting, the system runs a pre-flight check:** validates that the selected historical data has enough candles for TWPA calculation, confirms the strategy config schema is valid, and verifies WebSocket connection is active.

He selects a historical period known to contain pump events and starts the backtest. The dashboard comes alive - for the first time, he sees the indicator panel updating with real TWPA values, pump_magnitude calculations, and volume ratios.

Then it happens. An S1 signal appears on the chart, marked clearly. The state machine panel shows "S1 → Active". Seconds later, Z1 confirms and a position opens. He watches the unrealized P&L climb. ZE1 triggers at 15% profit. The position closes.

The breakthrough moment: the P&L summary shows a profitable trade, and Mr Lu can trace exactly WHY each decision happened - the indicator values, the conditions met, the state transitions. "Finally, my configuration drives real behavior."

**Requirements Revealed:**
- Strategy Builder → Backend signal generation must be connected
- **Contract validation:** Strategy config validated on save AND backend receive
- **Pre-flight check:** Data requirements verified before backtest starts
- Dashboard must show: signals on chart, state machine panel, indicator values
- P&L summary after backtest completion
- Traceability: which conditions triggered which transitions

### Journey 2: Debugging No Signals

A week later, Mr Lu tests a new, more conservative strategy. He runs a backtest but no signals appear. Instead of frustration, he has the tools to diagnose.

He opens the indicator panel and watches the values during the backtest replay. pump_magnitude reaches 4.5%, 5.2%, 6.1% - but never hits his 7% threshold. **The "Why No Signal" panel shows:** "S1 closest approach: pump_magnitude reached 6.1% (threshold: 7%) - missed by 0.9%"

Now he understands: the conditions are too strict for this dataset. He adjusts S1 to 5% pump_magnitude and 2.5x volume_surge. Re-runs the backtest. Signals appear.

The key insight: even when nothing triggers, he can see WHY nothing triggered. The system is transparent.

**Requirements Revealed:**
- Indicator values must display continuously, not just when signals fire
- **"Why No Signal" diagnostics:** Show closest values to thresholds
- Condition evaluation visibility (which conditions passed/failed)
- Easy strategy adjustment and re-run workflow
- Historical indicator replay during backtest

### Journey 3: Handling Errors (Pre-mortem Driven)

Mr Lu starts a backtest but something goes wrong. Instead of a blank screen with no explanation, **the error panel immediately shows:** "WebSocket disconnected during backtest. Last received: tick #1,847. Reconnecting..."

The system auto-reconnects and offers: "Resume from tick #1,847 or restart?"

He chooses resume. The backtest continues. Later, he checks the **debug panel (dev mode)** and sees the raw WebSocket messages - confirming data flow is working correctly.

**Requirements Revealed:**
- **No silent failures:** Every error surfaces to UI with context
- **Error recovery:** Graceful handling with user options
- **Debug panel:** Raw message viewer for troubleshooting (dev mode)
- **Connection status:** Always visible during active sessions

### Journey Requirements Summary

| Journey | Key Capabilities Required |
|---------|---------------------------|
| Success Path | Signal generation, dashboard display, state machine visibility, P&L tracking, **pre-flight validation** |
| Debugging Path | Continuous indicator display, **"Why No Signal" diagnostics**, condition transparency, quick iteration |
| Error Handling | **Error visibility**, recovery options, **debug panel**, connection monitoring |

**Core Requirement Theme:**
Both journeys emphasize **VISIBILITY and TRANSPARENCY** - the trader must always understand what the system is doing and why. **No silent failures allowed.**

### Pre-mortem Prevention Checklist

| Failure Point | Prevention Mechanism | Journey Coverage |
|---------------|---------------------|------------------|
| Config disconnect | Contract validation on both ends | Journey 1 |
| Signals not displayed | WebSocket E2E verification | Journey 3 |
| Silent failures | Error panel, no swallowed exceptions | Journey 3 |
| Data requirements | Pre-flight check | Journey 1 |
| Threshold mismatch | "Why No Signal" diagnostics | Journey 2 |

## Web Application Specific Requirements

### Project-Type Overview

FX Agent AI is a full-stack web application built with FastAPI (backend) and Next.js 14 (frontend). The architecture follows a real-time trading dashboard pattern with WebSocket-based data streaming.

**Project Context:** Brownfield repair - architecture exists, focus is on integration and pipeline repair.

### Technical Architecture (Existing)

| Layer | Technology | Status |
|-------|------------|--------|
| Frontend | Next.js 14 (App Router), TypeScript | Exists |
| UI Framework | MUI v5, ReactFlow | Exists |
| State Management | Zustand | Exists |
| Real-time | WebSockets (Socket.io-client) | Exists, needs verification |
| Backend | FastAPI, Python 3.10+ | Exists |
| Database | QuestDB (time-series) | Active |

### Performance Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| Signal Display Latency | < 500ms | From backend detection to dashboard display |
| WebSocket Reconnection | < 2s | Auto-reconnect on connection loss |
| Indicator Update Rate | Real-time | Many concurrent indicators updating |
| Backtest Processing | Background | Non-blocking UI during computation |

### Browser Support

| Browser | Support Level |
|---------|---------------|
| Chrome (latest) | Primary |
| Firefox (latest) | Supported |
| Edge (latest) | Supported |
| Safari | Not tested |
| Mobile browsers | Not supported (future phase) |

**Desktop-First Design:**
- Optimized for 1920x1080+ displays
- Multi-panel dashboard layout
- Mouse/keyboard interactions
- No touch optimization needed for MVP

### Real-time Architecture Requirements

**WebSocket Channels (MVP):**
- Signal events (S1/O1/Z1/ZE1/E1)
- State machine transitions
- Indicator value updates
- Position status changes
- Error/status notifications

**Data Flow:**
```
Backend Signal Generator
        ↓
   WebSocket Server
        ↓
   Frontend Store (Zustand)
        ↓
   Dashboard Components
```

**Concurrent Updates:**
- Multiple indicators updating simultaneously
- Multiple symbols (if multi-symbol strategy)
- State machine + signals + indicators in parallel

### Implementation Considerations

**What Exists (leverage):**
- Component library (85+ React components)
- Store structure (Zustand stores)
- WebSocket infrastructure
- Chart components (Lightweight Charts, uPlot)

**What Needs Repair (MVP focus):**
- WebSocket message routing to correct components
- Store updates triggering re-renders
- Signal data format consistency
- Error propagation to UI

**Skip for MVP:**
- Mobile responsiveness
- SEO optimization
- Accessibility compliance
- Offline support
- PWA features

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-Solving Repair MVP
- Focus on fixing one complete vertical slice
- No new features until pipeline works
- Success = E2E backtest with visible signals

**Resource Requirement:** Solo developer (Mr Lu)
**Constraint:** Windows without Docker (no Redis)

### MVP Scope Boundaries

**IN SCOPE (MVP):**
- Strategy config → Backend signal generation
- Dashboard signal display
- Dashboard state machine display
- Dashboard indicator values
- Backtest E2E flow
- Pre-flight validation
- Error visibility
- "Why No Signal" diagnostics

**OUT OF SCOPE (MVP):**
- Paper trading mode
- Live trading integration
- Multiple simultaneous strategies
- Mobile responsiveness
- New indicators
- Strategy optimization tools
- Performance analytics

### Phased Development Roadmap

**Phase 1: MVP Repair (Month 1)**
- Goal: One working backtest with pump detection
- Success: Pipeline Completion Rate ≥ 90%
- Deliverable: Can configure strategy → run backtest → see signals

**Phase 2: Stability (Month 2)**
- Goal: Paper trading 24/7 stable
- Build on: MVP foundation
- Add: Real-time market data, position management

**Phase 3: Production (Month 3)**
- Goal: First live trade
- Build on: Paper trading validation
- Add: MEXC integration, risk controls

**Future Phases:**
- Multiple strategies
- Beta testers
- SaaS preparation

### Risk Mitigation Strategy

**Technical Risk: Integration Complexity**
- Mitigation: Start with simplest case (1 indicator, 1 condition)
- Fallback: Manual verification before automation

**Technical Risk: Data Format Mismatches**
- Mitigation: Contract validation on both ends
- Fallback: Debug panel for raw message inspection

**Technical Risk: Silent Failures**
- Mitigation: Error visibility requirement (no swallowed exceptions)
- Fallback: Logging to console if UI fails

**Resource Risk: Scope Creep**
- Mitigation: Strict MVP definition document
- Rule: No new features until pipeline works

## Functional Requirements

### Strategy Configuration

- FR1: Trader can create a new pump detection strategy
- FR2: Trader can configure S1 (Signal Detection) conditions with indicator thresholds
- FR3: Trader can configure O1 (Cancellation) conditions for false signal filtering
- FR4: Trader can configure Z1 (Entry Confirmation) conditions
- FR5: Trader can configure ZE1 (Exit with Profit) conditions
- FR6: Trader can configure E1 (Emergency Exit) conditions
- FR7: Trader can select which indicators to use in conditions (from MVP indicator set)
- FR8: Trader can save and load strategy configurations
- FR9: Trader can view the current strategy configuration in a readable format

### Signal Generation

- FR10: System can evaluate strategy conditions against market data
- FR11: System can generate S1 signals when detection conditions are met
- FR12: System can generate O1 signals when cancellation conditions are met
- FR13: System can generate Z1 signals when entry conditions are met
- FR14: System can generate ZE1 signals when profit exit conditions are met
- FR15: System can generate E1 signals when emergency exit conditions are met
- FR16: System can calculate MVP indicator values (TWPA, pump_magnitude_pct, volume_surge_ratio, price_velocity, spread_pct, unrealized_pnl_pct)
- FR17: System can track state machine transitions (S1→O1→Z1→ZE1→E1)

### Dashboard Display

- FR18: Trader can view generated signals on the price chart
- FR19: Trader can view current state machine state (which section is active)
- FR20: Trader can view real-time indicator values
- FR21: Trader can view signal history during a session
- FR22: Trader can distinguish between different signal types (S1/O1/Z1/ZE1/E1) visually
- FR23: Trader can view state machine transition history
- FR24: Trader can view connection status (WebSocket health)

### Backtest Execution

- FR25: Trader can start a backtest session with a selected strategy
- FR26: Trader can select historical data period for backtesting
- FR27: Trader can select symbol for backtesting
- FR28: System can simulate trading execution during backtest
- FR29: Trader can view backtest progress
- FR30: Trader can view backtest results (P&L summary)
- FR31: Trader can stop a running backtest

### Diagnostics & Debugging

- FR32: Trader can view "Why No Signal" diagnostics showing closest threshold approach
- FR33: Trader can view indicator values continuously (even when no signals fire)
- FR34: Trader can access debug panel showing raw WebSocket messages (dev mode)
- FR35: System displays which conditions passed/failed during evaluation
- FR36: Trader can trace why each signal/transition occurred

### System Reliability

- FR37: System validates strategy configuration schema before saving
- FR38: System validates strategy configuration when received by backend
- FR39: System performs pre-flight check before starting backtest (data requirements, connection)
- FR40: System displays errors with context (no silent failures)
- FR41: System attempts auto-reconnect on WebSocket disconnection
- FR42: System offers recovery options when errors occur (resume/restart)

## Non-Functional Requirements

### Performance

- NFR1: Signal display latency must be < 500ms from backend generation to dashboard render
- NFR2: WebSocket reconnection must complete within 2 seconds
- NFR3: Indicator calculations must not block UI rendering
- NFR4: Backtest must process at least 10x faster than real-time (1 hour of data in < 6 minutes)
- NFR5: Dashboard must remain responsive during backtest execution
- NFR6: Multiple concurrent indicator updates must not cause UI lag

### Reliability

- NFR7: System must not have silent failures - all errors must surface to UI
- NFR8: WebSocket connection must auto-reconnect on disconnection
- NFR9: Backtest session must be resumable after error recovery
- NFR10: Strategy configuration must not be lost on browser refresh (persist to backend)
- NFR11: System must gracefully degrade when optional services unavailable (e.g., Redis)

### Data Integrity

- NFR12: Strategy configuration must be validated before saving
- NFR13: Signal data must be consistent between backend and frontend
- NFR14: Backtest results must be deterministic (same inputs = same outputs)
- NFR15: Historical data must not be corrupted during backtest processing

### Security (MVP - Personal Use)

- NFR16: MEXC API keys must be stored securely (not in frontend code)
- NFR17: API keys must not be exposed in browser developer tools
- NFR18: Backend must validate requests come from authorized frontend

### Observability

- NFR19: System must log all state machine transitions
- NFR20: System must log all errors with context for debugging
- NFR21: Debug panel must show raw WebSocket messages (dev mode)
- NFR22: System must track and display connection status

### Constraints

- NFR23: Must work on Windows without Docker (no Redis dependency for MVP)
- NFR24: Must work with QuestDB as primary data store
- NFR25: Desktop browsers only (Chrome, Firefox, Edge)

