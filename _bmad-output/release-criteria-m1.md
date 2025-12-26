# M1 Release Criteria - FX Agent AI

**Milestone:** M1 - "Backtest Works End-to-End"
**Target:** Month 1 (from PRD 3-Month Milestones)
**Created:** 2025-12-26
**Updated:** 2025-12-26 (v1.1 - Paradox Verification Improvements)
**Owner:** PM (John)
**Version:** 1.1

---

## Milestone Definition

> **M1 Success Statement:** "Trader can configure a strategy, run a backtest on historical data, and see the complete trading cycle (signal detection → entry → exit) with P&L results on the dashboard."

---

## M1 CORE Criteria (MUST PASS)

These 3 criteria define the ESSENCE of M1. If these pass, M1 is achieved.

| ID | Criterion | Why Critical | Verification |
|----|-----------|--------------|--------------|
| **M1-CORE-1** | Signal flows from backend to dashboard | Pipeline works | Signal visible in browser within 500ms |
| **M1-CORE-2** | Complete trading cycle: S1→Z1→ZE1 | System makes decisions | Signal history shows full cycle with entry and exit |
| **M1-CORE-3** | P&L displayed after backtest | Value delivered | Final P&L number visible and correct |

**RULE:** If M1-CORE criteria pass, M1 is ACHIEVED regardless of supporting criteria status.

---

## Tiered Release Option

If blocked on full M1, can release in tiers:

### M1a: Signal Visibility (Epic 0 + 1A)
**Criteria:**
- M1-CORE-1: Signal flows to dashboard
- State machine state visible
- Indicator values visible

**Value:** "I can see the system detecting pumps in real-time"

**Release if:** Epic 1B blocked but 0+1A working

### M1b: Backtest Complete (Epic 1B)
**Criteria:**
- M1-CORE-2: Complete cycle works
- M1-CORE-3: P&L displayed
- Can start/stop backtest

**Value:** "I can test strategies on historical data"

### M1 Complete = M1a + M1b

---

## Supporting Criteria (SHOULD PASS)

These improve quality but don't block M1 release.

### Epic 0: Foundation
| ID | Criterion | Priority | Status |
|----|-----------|----------|--------|
| M1-S01 | Strategy can be loaded from existing data | High | Pending |
| M1-S02 | WebSocket connection status visible | Medium | Pending |
| M1-S03 | Errors display in UI (not just console) | High | Pending |
| M1-S04 | Debug panel shows raw WS messages | Low (dev tool) | Pending |

### Epic 1A: Signal Display
| ID | Criterion | Priority | Status |
|----|-----------|----------|--------|
| M1-S05 | Signal displays within 500ms latency | High | Pending |
| M1-S06 | State machine state visible as badge | High | Pending |
| M1-S07 | Indicator values panel shows MVP indicators | High | Pending |
| M1-S08 | Human vocabulary labels ("Found!" not "S1") | Low (polish) | Pending |
| M1-S09 | StatusHero component renders | Medium | Pending |

### Epic 1B: Backtest
| ID | Criterion | Priority | Status |
|----|-----------|----------|--------|
| M1-S10 | Can start backtest with strategy | High | Pending |
| M1-S11 | Can select historical data period | Medium | Pending |
| M1-S12 | Backtest progress visible | Medium | Pending |
| M1-S13 | Emergency stop works (Esc key) | High (safety) | Pending |

---

## Nice to Have (OPTIONAL)

These are explicitly deferred to M2 if time-constrained:

| ID | Feature | Defer Reason |
|----|---------|--------------|
| M1-OPT-01 | JourneyBar component | UX polish |
| M1-OPT-02 | Signal timeline on chart | Visualization |
| M1-OPT-03 | Multi-symbol support | Complexity |
| M1-OPT-04 | Sound alerts | UX polish |
| M1-OPT-05 | Color-coded signal types | UX polish |

---

## Quality Gates

| Gate | Requirement | Status |
|------|-------------|--------|
| QG-01 | All 3 M1-CORE criteria verified with evidence | Pending |
| QG-02 | No critical bugs open | Pending |
| QG-03 | High-priority supporting criteria verified | Pending |
| QG-04 | Epic 0, 1A, 1B stories marked DONE | Pending |
| QG-05 | Risk Register reviewed, no critical blockers | Pending |

---

## Verification Evidence Protocol

For each criterion marked "Verified", require:

| Field | Required | Example |
|-------|----------|---------|
| **Verified By** | Yes | Mr Lu / Dev |
| **Verified Date** | Yes | 2025-01-15 |
| **Method** | Yes | Manual demo / Automated test / Screenshot |
| **Evidence** | Yes | Link to recording, screenshot, or test log |
| **Environment** | Yes | Dev / Local |

### Example Verification Record:
```markdown
### M1-CORE-2: Complete cycle S1→Z1→ZE1
| Field | Value |
|-------|-------|
| Status | VERIFIED |
| Verified By | Mr Lu |
| Date | 2025-01-15 |
| Method | Manual backtest demo |
| Evidence | Recording: demos/m1-core-2-cycle.mp4 |
| Environment | Local dev |
| Notes | BTC_USDT, 2025-01-01 to 2025-01-15, detected 3 cycles |
```

---

## Primary Acceptance Scenario

The ONE scenario that must pass for M1:

```gherkin
Scenario: Complete Backtest Cycle (M1 CORE)

GIVEN a trader has configured a pump detection strategy
  AND historical data exists for BTC_USDT with known pump events

WHEN the trader starts a backtest

THEN the dashboard shows:
  - Connection status: GREEN (or indicator visible)
  - At least ONE S1 signal appears (pump detected)
  - State transitions through Z1 (entry confirmed)
  - Position is opened
  - State transitions to ZE1 (profit target)
  - Position is closed
  - Final P&L is displayed (positive or negative)

AND the trader can trace WHY each transition happened
AND the complete cycle runs without crash or silent failure
```

**Verification:** Record demo of this scenario passing.

---

## Edge Case Scenarios (Optional for M1)

These are good to verify but don't block M1:

### Scenario: No Signals Detected
```gherkin
GIVEN a strategy with strict thresholds
WHEN backtest runs on data with no matching pumps
THEN "No signals detected" message appears
  AND no crash occurs
```

### Scenario: Error Recovery
```gherkin
GIVEN a backtest is running
WHEN WebSocket disconnects
THEN connection status shows RED
  AND reconnect is attempted
  AND user can restart
```

### Scenario: Emergency Stop
```gherkin
GIVEN a backtest is running
WHEN user presses Esc
THEN backtest stops within 1 second
  AND partial state is preserved
```

---

## Definition of Done for M1

### M1 CORE (Required)
- [ ] M1-CORE-1 verified with evidence
- [ ] M1-CORE-2 verified with evidence
- [ ] M1-CORE-3 verified with evidence
- [ ] Primary acceptance scenario recorded

### Quality (Required)
- [ ] No critical bugs open
- [ ] Risk Register reviewed

### Supporting (Best Effort)
- [ ] High-priority supporting criteria verified
- [ ] All epic stories marked DONE in sprint-status.yaml

### Documentation (Simplified for Solo)
- [ ] Demo recording exists
- [ ] Commit tagged as "v0.1.0-m1"

**REMOVED for Solo MVP:**
- ~~Release notes~~ (nobody reads for personal MVP)
- ~~Sign-off table~~ (signing with yourself)
- ~~Detailed rollback plan~~ (git revert is enough)

---

## Timeline

> ⚠️ **DISCLAIMER:** This timeline is an ESTIMATE. Revise after Sprint 1 velocity is measured.

| Week | Focus | Expected Completion |
|------|-------|---------------------|
| Week 1 | Epic 0 completion | Stories 0-1 to 0-6 DONE |
| Week 2 | Epic 1A | All Epic 1A stories DONE |
| Week 3 | Epic 1B (core) | M1-CORE criteria met |
| Week 4 | M1B completion + verification | M1 VERIFIED + TAGGED |

**Buffer:** 1 week for unexpected issues.

**After Sprint 1:** Measure velocity. If 50% of expected:
- M1 extends to 6-8 weeks, OR
- Reduce to M1a (Signal Visibility) first

---

## Dependencies

| Dependency | Status | Impact if Not Met |
|------------|--------|-------------------|
| EventBridge fix (RISK-01) | MITIGATED | Blocks M1-CORE-1 |
| QuestDB running | AVAILABLE | Blocks backtesting |
| Historical data exists | AVAILABLE | Blocks backtesting |
| Strategy Builder functional | VERIFYING | Blocks strategy config |

---

## Rollback Plan (Simplified)

For personal MVP, rollback = git operations:

```bash
# If M1 causes issues:
git revert HEAD~N  # Revert problematic commits
# OR
git checkout v0.0.X  # Return to known good state
```

Full rollback procedures needed for M2/M3 (production).

---

## Hard Deadlines (Optional)

If time-boxing is desired:

| Option | Deadline | Action |
|--------|----------|--------|
| **Flexible** | None | Ship when M1-CORE passes |
| **Soft deadline** | 6 weeks | Review and adjust scope |
| **Hard deadline** | 8 weeks | Ship M1a if M1b incomplete |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-26 | PM | Initial version (16 criteria) |
| 1.1 | 2025-12-26 | PM | Simplified: 3 CORE + supporting, tiered release, evidence protocol, removed release notes |

---

*M1 is the FIRST proof that the system works. Quality over speed. Ship M1-CORE, iterate on polish.*
