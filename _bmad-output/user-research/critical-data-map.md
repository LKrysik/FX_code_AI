# Critical Data Map

**Date:** 2025-12-30
**Validated with:** Mr Lu (Primary User)
**Context:** Aktywna pozycja LONG/SHORT
**Source:** Interview #001

---

## User's Answer to Critical Data Question:

> "Które elementy MUSZĄ być widoczne CAŁY CZAS podczas aktywnej pozycji?"

**User selected ALL options:**
- Stan strategii + warunki
- Wykres cenowy
- Stop Loss / Take Profit
- P&L i Margin Ratio

---

## Data Elements Classification (Based on Interview)

### Position Data

| Element | Must be visible? | User Priority | Notes |
|---------|------------------|---------------|-------|
| Symbol (np. BTC_USDT) | ✅ YES | HIGH | Part of position context |
| Side (LONG/SHORT) | ✅ YES | HIGH | Critical for understanding |
| Entry price | ✅ YES | MEDIUM | Reference point |
| Current price | ✅ YES | HIGH | Real-time needed |
| Unrealized P&L ($) | ✅ YES | HIGH | User selected "P&L" |
| Unrealized P&L (%) | ✅ YES | HIGH | User selected "P&L" |
| Margin ratio | ✅ YES | HIGH | User selected "Margin Ratio" |
| Liquidation price | ✅ YES | HIGH | Risk indicator |
| Stop Loss | ✅ YES | HIGH | User selected "SL/TP" |
| Take Profit | ✅ YES | HIGH | User selected "SL/TP" |

### Strategy/State Data

| Element | Must be visible? | User Priority | Notes |
|---------|------------------|---------------|-------|
| Current state (S1/Z1/etc) | ✅ YES | HIGH | User selected "Stan strategii" |
| Strategy name | ✅ YES | MEDIUM | Context |
| Conditions status | ✅ YES | HIGH | User selected "warunki" |

### Indicator Data

| Element | Must be visible? | User Priority | Notes |
|---------|------------------|---------------|-------|
| PUMP_MAGNITUDE | ⚠️ DEPENDS | MEDIUM | Part of conditions |
| PRICE_VELOCITY | ⚠️ DEPENDS | MEDIUM | Part of conditions |
| Other indicators | ⚠️ DEPENDS | LOW | Can be in details |

### Visual Elements

| Element | Must be visible? | User Priority | Notes |
|---------|------------------|---------------|-------|
| Candlestick chart | ✅ YES | HIGH | User selected "Wykres cenowy" |
| Condition progress | ✅ YES | HIGH | User selected "warunki" |

---

## Summary: Must-Have Elements (Always Visible)

Based on user interview, these elements MUST be visible at all times during active position:

1. ✅ P&L ($ and %)
2. ✅ Margin Ratio
3. ✅ Stop Loss / Take Profit
4. ✅ Current State (S1/Z1/etc)
5. ✅ Condition Status
6. ✅ Price Chart
7. ✅ Current Price

---

## Summary: Can Be in Secondary View

These elements can be accessed with one click:

1. Transaction history
2. Signal history
3. Detailed indicator values
4. Equity curve (long-term)

---

## Progressive Disclosure Decision

Based on interview:

**User's explicit preference:**
> "Zależy od sytuacji" + selected ALL critical elements

**Recommended approach:**
- [x] **Context-dependent layout** (different for active position vs monitoring)
- [ ] ~~Full progressive disclosure~~ - REJECTED
- [ ] ~~Partial progressive disclosure~~ - REJECTED for active position
- [ ] ~~No progressive disclosure~~ - May work for active position

### Context-Dependent Rules:

| Context | Layout | Reason |
|---------|--------|--------|
| No session | Simplified | Less noise |
| Monitoring (no position) | Medium | Watching for signals |
| Active Position | FULL | User wants everything |

---

## Critical Finding: Data Quality > Layout

**From interview Q5:**
> User said data was wrong for: Indicators, State, Positions, Signals

**Impact:** Even perfect layout is useless if data is wrong!

**New Priority:**
1. 🔴 P0: Fix data synchronization (BUG-004-3,4,5,6)
2. 🟡 P1: Context-dependent UI
3. 🟢 P2: Visual polish (colors, etc)

---

## Connection to Existing Bugs

| User Complaint | Matching Bug | Status |
|----------------|--------------|--------|
| "Stan strategii błędny" | BUG-004-3, BUG-004-6 | backlog |
| "Wskaźniki błędne" | BUG-004-5 | backlog |
| "Dane pozycji błędne" | BUG-004-3 | backlog |
| "Sygnały błędne" | BUG-004-3 | backlog |

**Recommendation:** Prioritize BUG-004 backlog items BEFORE any UX changes!

---

*Validated by: Sally (UX Designer Agent)*
*Date: 2025-12-30*
