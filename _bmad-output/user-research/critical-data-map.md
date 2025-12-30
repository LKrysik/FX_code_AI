# Critical Data Map

**Date:** [YYYY-MM-DD]
**Validated with:** [Trader alias]
**Context:** Aktywna pozycja LONG/SHORT

---

## Pytanie do tradera:

> "Wyobraź sobie że masz otwartą pozycję LONG na BTC.
> Które z tych informacji MUSISZ widzieć cały czas, bez klikania?"

---

## Data Elements Classification

### Position Data

| Element | Zawsze widoczny? | Można ukryć? | User Priority (1-5) | Notes |
|---------|------------------|--------------|---------------------|-------|
| Symbol (np. BTC_USDT) | [ ] | [ ] | | |
| Side (LONG/SHORT) | [ ] | [ ] | | |
| Entry price | [ ] | [ ] | | |
| Current price | [ ] | [ ] | | |
| Quantity | [ ] | [ ] | | |
| Unrealized P&L ($) | [ ] | [ ] | | |
| Unrealized P&L (%) | [ ] | [ ] | | |
| Margin ratio | [ ] | [ ] | | |
| Leverage | [ ] | [ ] | | |
| Liquidation price | [ ] | [ ] | | |
| Stop Loss | [ ] | [ ] | | |
| Take Profit | [ ] | [ ] | | |
| Time in position | [ ] | [ ] | | |

### Strategy/State Data

| Element | Zawsze widoczny? | Można ukryć? | User Priority (1-5) | Notes |
|---------|------------------|--------------|---------------------|-------|
| Current state (S1/Z1/etc) | [ ] | [ ] | | |
| State label (human) | [ ] | [ ] | | |
| Strategy name | [ ] | [ ] | | |
| Time in state | [ ] | [ ] | | |

### Indicator Data

| Element | Zawsze widoczny? | Można ukryć? | User Priority (1-5) | Notes |
|---------|------------------|--------------|---------------------|-------|
| PUMP_MAGNITUDE | [ ] | [ ] | | |
| PRICE_VELOCITY | [ ] | [ ] | | |
| VOLUME_SURGE_RATIO | [ ] | [ ] | | |
| TWPA | [ ] | [ ] | | |
| Spread % | [ ] | [ ] | | |

### Visual Elements

| Element | Zawsze widoczny? | Można ukryć? | User Priority (1-5) | Notes |
|---------|------------------|--------------|---------------------|-------|
| Candlestick chart | [ ] | [ ] | | |
| Equity curve | [ ] | [ ] | | |
| Drawdown chart | [ ] | [ ] | | |
| Condition progress bars | [ ] | [ ] | | |
| Recent signals list | [ ] | [ ] | | |
| Transaction history | [ ] | [ ] | | |

---

## Summary: Must-Have Elements (Always Visible)

Based on user feedback, these elements MUST be visible at all times during active position:

1. [ ]
2. [ ]
3. [ ]
4. [ ]
5. [ ]

---

## Summary: Nice-to-Have Elements (Can Be Collapsed)

These elements can be hidden behind progressive disclosure:

1. [ ]
2. [ ]
3. [ ]
4. [ ]
5. [ ]

---

## Progressive Disclosure Decision

Based on this mapping:

**Recommended approach:**
- [ ] Full progressive disclosure (hide most things)
- [ ] Partial progressive disclosure (hide only charts/history)
- [ ] No progressive disclosure (show everything)
- [ ] Context-dependent (different for active position vs monitoring)

**User's preference:**
> "[Cytat od usera]"

---

## Impact on UX Review Recommendations

| UX Review Issue | Still Valid? | Modification Needed |
|-----------------|--------------|---------------------|
| VH-1: Progressive disclosure | [ ] Yes [ ] No | |
| VH-2: StatusHero prominence | [ ] Yes [ ] No | |
| ID-2: Numbers without context | [ ] Yes [ ] No | |

---

*Validated by: [Name]*
