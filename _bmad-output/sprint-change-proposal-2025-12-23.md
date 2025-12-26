# Sprint Change Proposal - FX Agent AI

**Date:** 2025-12-23
**Author:** PM Agent (John)
**Status:** ✅ APPROVED
**Approved By:** Lukasz.krysik
**Approval Date:** 2025-12-23
**Change Scope:** MODERATE

---

## 1. Issue Summary

### Problem Statement

Wprowadzenie testów E2E edge cases (30 testów dla Trading Session i Strategy Builder) ujawniło oczekiwane zachowania UI, które nie zostały jeszcze zdefiniowane jako formalne Acceptance Criteria w Stories. Dodatkowo, sesja brainstormingowa o AI anti-evasion zidentyfikowała potrzebę wzmocnienia procesu BMAD.

### Triggering Events

| Trigger | Source | Date |
|---------|--------|------|
| E2E Tests Added | `frontend/tests/e2e/components/*.spec.ts` | 2025-12-22 |
| Brainstorming Session | `_bmad-output/analysis/brainstorming-session-2025-12-21.md` | 2025-12-21 |

### Issue Classification

- **Type A (E2E Tests):** Technical refinement - edge cases defining expected UI behaviors
- **Type B (Anti-Evasion):** Process improvement - BMAD methodology enhancement

### Evidence

- 15 Trading Session edge case tests (`EDGE-TS01` through `EDGE-TS15`)
- 15 Strategy Builder edge case tests (`EDGE-SB01` through `EDGE-SB15`)
- 45 AI evasion tactics identified in brainstorming session
- Key finding: "Presence-based detection is gameable"

---

## 2. Impact Analysis

### Epic Impact

| Epic | Impact Level | Required Changes |
|------|--------------|------------------|
| Epic 0 (Foundation) | 🟡 Moderate | Add AC for error handling patterns |
| Epic 1A (First Signal) | 🟡 Moderate | State machine visualization requirements |
| Epic 1B (First Backtest) | 🟡 Moderate | Mode exclusivity, Live mode warnings |
| Epic 2 (Strategy Config) | 🟡 Moderate | Condition block validation, empty states |
| Epic 3 (Diagnostics) | 🟢 Minimal | No significant changes |
| Epic 4 (Reliability) | 🟡 Moderate | Input validation bounds |
| Epic 5 (Polish) | 🟢 Minimal | No significant changes |

### Artifact Impact

| Artifact | Conflict | Required Action |
|----------|----------|-----------------|
| PRD | ❌ None | Optional: Add edge case section |
| Architecture | ❌ None | Verify form state management |
| UX Design | ⚠️ Minor | **Add 4 new UX requirements** |
| Epics | ⚠️ Minor | Extend Stories with test-based AC |

### New UX Requirements from Tests

| ID | Requirement | Source Test |
|----|-------------|-------------|
| UX-NEW-01 | Live mode must show warning/confirmation dialog | EDGE-TS02 |
| UX-NEW-02 | Strategy list must have Select All / Deselect All | EDGE-TS06 |
| UX-NEW-03 | Empty sections must show helpful placeholder | EDGE-SB03 |
| UX-NEW-04 | State machine diagram must have zoom/pan controls | EDGE-SB12 |

---

## 3. Recommended Approach

### Selected Path: ✅ DIRECT ADJUSTMENT

Modify existing Epic Stories to include Acceptance Criteria derived from E2E tests.

### Rationale

| Factor | Assessment |
|--------|------------|
| Implementation Effort | 🟢 Low - mapping tests to ACs |
| Timeline Impact | 🟢 Minimal - no delays |
| Technical Risk | 🟢 Low - tests strengthen, don't change architecture |
| Team Morale | 🟢 Positive - clearer definitions |
| Long-term Value | 🟢 High - E2E tests as regression baseline |
| Business Value | 🟢 High - built-in quality assurance |

### Alternatives Considered

| Option | Verdict | Reason |
|--------|---------|--------|
| Ignore tests | ❌ Rejected | Lost quality assurance |
| Rollback changes | ❌ Not viable | Nothing to roll back (Solutioning phase) |
| Redefine MVP | ❌ Not needed | MVP unchanged |
| **Extend AC** | ✅ Selected | Balanced effort/value |

---

## 4. Detailed Change Proposals

### 4.1 UX Design Specification Updates

**File:** `_bmad-output/ux-design-specification.md`

**Changes:**

```markdown
## New Requirements (from E2E Test Analysis)

### Live Mode Safety (UX-NEW-01)
- Live trading mode MUST display warning dialog before activation
- Warning must mention "real money" implications
- Confirmation required before proceeding

### Strategy Selection UX (UX-NEW-02)
- Strategy list MUST include "Select All" and "Deselect All" buttons
- Button state should reflect current selection (disabled if all selected/none selected)

### Empty State Guidance (UX-NEW-03)
- Empty sections (S1, O1, Z1, ZE1, E1) MUST show placeholder message
- Message should include: icon, explanation, call-to-action ("Add Condition")
- Example: "No conditions yet. Click + to add your first condition."

### State Machine Diagram Controls (UX-NEW-04)
- State machine visualization MUST include zoom controls (+/-)
- MUST include reset/fit-to-view button
- SHOULD support mouse wheel zoom
- SHOULD support pan via drag
```

### 4.2 Epic Story AC Extensions

**Mapping E2E Tests to Story Acceptance Criteria:**

#### Epic 0: Foundation

| Story | New AC from Tests |
|-------|-------------------|
| Error Display Pattern | AC: Validation errors must be visible (`EDGE-TS10`, `EDGE-SB05`) |
| Connection Status | AC: Connection status always visible when unhealthy (`EDGE-TS15`) |

#### Epic 1A: First Signal Visible

| Story | New AC from Tests |
|-------|-------------------|
| State Machine Display | AC: Diagram updates when conditions change (`EDGE-SB10`) |
| State Machine Display | AC: Diagram supports zoom/pan (`EDGE-SB12`) |

#### Epic 1B: First Successful Backtest

| Story | New AC from Tests |
|-------|-------------------|
| Backtest Session Setup | AC: Only one mode selected at a time (`EDGE-TS01`) |
| Backtest Session Setup | AC: Live mode shows warning (`EDGE-TS02`) |
| Backtest Session Setup | AC: Double-click doesn't break UI (`EDGE-TS03`) |

#### Epic 2: Complete Strategy Configuration

| Story | New AC from Tests |
|-------|-------------------|
| Create New Strategy | AC: Name validates special characters (`EDGE-SB13`) |
| Configure Sections | AC: Section content persists when switching tabs (`EDGE-SB02`) |
| Configure Sections | AC: Empty sections show placeholder (`EDGE-SB03`) |
| Condition Blocks | AC: Blocks can be reordered via drag-drop (`EDGE-SB04`) |
| Condition Blocks | AC: Missing indicator shows validation error (`EDGE-SB05`) |
| Condition Blocks | AC: Deletion requires confirmation (`EDGE-SB06`) |
| Indicator/Operator | AC: Value input validates numeric bounds (`EDGE-SB08`) |

#### Epic 4: Production Reliability

| Story | New AC from Tests |
|-------|-------------------|
| Input Validation | AC: Risk percent validates 0-100 range (`EDGE-TS10`) |
| Input Validation | AC: Position size accepts decimals (`EDGE-TS11`) |
| Input Validation | AC: Numeric inputs reject text/scripts (`EDGE-TS12`) |

---

## 5. Implementation Handoff

### Change Scope Classification: 🟡 MODERATE

### Handoff Plan

| Role | Responsibility | Priority |
|------|----------------|----------|
| **PM (Current Session)** | Update UX Design with 4 new requirements | P1 |
| **PM** | Finalize Epic Stories with extended AC | P1 |
| **Architect** | Verify form state management patterns | P2 |
| **Dev Team** | Implement Stories with new AC | P1 (during Implementation) |
| **BMAD Master** | (Separate track) Implement anti-evasion CHECKs | P2 |

### Action Items

| # | Action | Owner | Due | Status |
|---|--------|-------|-----|--------|
| 1 | Update UX Design Specification | PM | Immediate | ⏳ Pending |
| 2 | Create Test→AC mapping table | PM | Immediate | ⏳ Pending |
| 3 | Finalize create-epics-and-stories workflow | PM | Next session | ⏳ Pending |
| 4 | Run implementation-readiness check | PM/Architect | After #3 | ⏳ Pending |
| 5 | Document anti-evasion improvements | BMAD Master | Separate track | ⏳ Pending |

### Success Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| UX Design Updated | New requirements added | 4/4 |
| Test→AC Mapping | Tests mapped to Stories | 30/30 |
| Stories Finalized | Stories with extended AC | All Epic Stories |
| Implementation Readiness | Check result | PASS |

---

## 6. Anti-Evasion Track (Separate)

### Summary

The brainstorming session identified that AI agents can game sanity-checks through 45 different evasion tactics. This affects the BMAD methodology, not the FX Agent AI product directly.

### Key Recommendations

1. **CHECK 8: Shadow Audit** - Detect avoided work patterns
2. **Challenge-Response Protocol** - Follow-up verification
3. **Substance-based Detection** - Move from presence to substance
4. **Forced Self-Criticism** - Required negative content

### Implementation Path

This is tracked separately in:
- `docs/sanity-check-repair-process-v7-bmad.md`
- Future BMAD methodology updates

**NOT a blocker for FX Agent AI development.**

---

## 7. Approval

### Proposal Status: ✅ APPROVED

**Approved By:** Lukasz.krysik
**Approval Date:** 2025-12-23
**Decision:** APPROVE - Proceed with implementation

### Next Steps

1. ⏳ Update UX Design Specification with 4 new requirements
2. ⏳ Create Test→AC mapping table
3. ⏳ Finalize create-epics-and-stories workflow
4. ⏳ Run implementation-readiness check
5. ⏳ (Separate track) Document anti-evasion improvements

---

*Generated by Correct Course Workflow*
*🤖 Generated with [Claude Code](https://claude.com/claude-code)*
