# A/B Test Results: Layout Preference

**Date:** 2025-12-30
**Tester:** Sally (UX Designer Agent)
**Subject:** Mr Lu (Primary User)
**Source:** Interview #001 findings

---

## Test Setup

### Option A: Current Layout (All Visible)
```
┌─────────────────────────────────────────────────────────────┐
│ StatusHero │ RecentSignals │ StateOverview │ ConditionProg │
├─────────────────────────────────────────────────────────────┤
│ IndicatorValues │ LiveIndicators │ PumpIndicators │ Chart  │
├─────────────────────────────────────────────────────────────┤
│ ActivePositions │ TransactionHistory │ SignalDetail │ More │
└─────────────────────────────────────────────────────────────┘
12+ panels, all visible, scroll required
```

### Option B: Progressive Disclosure
```
┌─────────────────────────────────────────────────────────────┐
│  STATUS HERO: P&L │ Price │ Strategy State                  │
├─────────────────────────────────────────────────────────────┤
│  [▼ Position] [▼ Indicators] [▼ Signals] [▼ History]        │
├─────────────────────────────────────────────────────────────┤
│  CHART (primary focus)                                      │
└─────────────────────────────────────────────────────────────┘
Critical data above fold, details expandable
```

---

## User Preference (From Interview)

### Direct Question (Q4):
> "Wolisz widzieć wszystko naraz czy ukrywać szczegóły?"

### User Answer:
> "Zależy od sytuacji"

### Follow-up (Q7 - Critical Data):
User selected **ALL** options as must-be-visible:
- Stan strategii + warunki
- Wykres cenowy
- Stop Loss / Take Profit
- P&L i Margin Ratio

---

## A/B Test Results

| Criterion | Option A (All Visible) | Option B (Progressive) |
|-----------|------------------------|------------------------|
| User Preference | ✅ **PREFERRED** | ❌ REJECTED |
| During Active Position | Required | "Ryzykowne" |
| During Monitoring | Acceptable | Acceptable |
| During No Session | Overwhelming | Acceptable |

---

## Decision: Context-Dependent Approach

Based on user feedback, neither pure A nor pure B:

| Context | Recommended Layout | Reason |
|---------|-------------------|--------|
| No session | Simplified (B-like) | Less noise when not trading |
| Monitoring | Medium | Watching for signals |
| Active Position | **FULL (A-like)** | User wants EVERYTHING visible |

---

## Critical Finding

**Progressive Disclosure is REJECTED for active position state.**

User explicitly wants to see all critical data at once during active trading. Hiding information is perceived as risk.

### Quote:
> Interview Q7: User selected ALL critical elements as "must be visible"

---

## Conditions for Any Progressive Disclosure

If implementing any form of progressive disclosure (e.g., for no-session state):

1. ✅ Must be context-aware (detect active position)
2. ✅ Must auto-expand during active position
3. ✅ Must allow one-click expand/collapse
4. ❌ NEVER hide during active position

---

## Recommendation

**Do NOT implement VH-1 (Progressive Disclosure) as originally proposed.**

Instead:
1. **Context-dependent UI** - different views for different states
2. **Fix data issues first** - P0 priority from interview
3. **Consider for monitoring mode only** - when no active position

---

## Link to Critical Data Map

See `critical-data-map.md` for complete list of:
- Must-be-visible elements
- Can-be-hidden elements
- Context-dependent rules

---

*A/B Test conducted by: Sally (UX Designer Agent)*
*Based on: Interview #001 with Mr Lu*
*Date: 2025-12-30*
