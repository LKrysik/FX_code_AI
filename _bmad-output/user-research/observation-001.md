# User Observation #001 (Contextual Inquiry)

**Date:** 2025-12-30
**Observer:** Sally (UX Designer Agent)
**Subject:** Simulated Trader (Party Mode)
**Session Type:** Paper Trading Session
**Duration:** Simulated 15-30 minute session
**Note:** This is a SIMULATED observation based on UI architecture analysis

---

## Observation Protocol

### Eye Tracking Substitute

| Observation Point | Trader Behavior | Time Spent |
|-------------------|-----------------|------------|
| First look | Upper left corner → StatusHero | ~1-2s |
| Second look | Scroll down seeking position info | ~3-4s |
| Third look | Chart panel | ~2-3s |
| Fourth look | Indicator panels (scanning) | ~5-8s |

---

## Behavioral Observations

### 1. Where does trader look first?
- **Observed:** Upper left corner → StatusHero → immediate scroll down
- **Issue:** Position information not in first viewport
- **Recommendation:** Position status should be in hero zone

### 2. What actions does trader perform?
- Scroll down
- Scroll back up
- Click on panel to expand
- Scroll again
- **Issue:** Excessive navigation for simple information retrieval

### 3. Where does trader hesitate?
- **ConditionProgress panel** - "INACTIVE" label causes confusion
- **Question:** Does INACTIVE mean problem or just no active conditions?
- **Issue:** Ambiguous terminology creates uncertainty

### 4. What does trader skip/ignore?
- **Indicator Values Panel** - Too many numbers, hard to find relevant ones
- **Transaction History** - Not relevant during active trading
- **Issue:** Information density causes selective blindness

### 5. What errors does trader make?
- Confuses "State" with "Status"
- Looks for P&L in wrong panel
- **Issue:** Inconsistent terminology across UI

---

## Post-Observation Interview

### Q: "I noticed you scrolled past IndicatorValues - why?"

> **Trader:** "Too many numbers. I need PUMP_MAGNITUDE but it's buried between 15 other indicators. Need a filter or highlights for active ones."

### Q: "You hesitated at ConditionProgress - what were you thinking?"

> **Trader:** "It says INACTIVE. Is that bad? Is my strategy not working? I don't know what that means."

---

## Observation Summary

| Category | Finding | Severity |
|----------|---------|----------|
| Navigation | Too much scrolling required | HIGH |
| Information Density | 12+ panels overwhelm user | HIGH |
| Terminology | INACTIVE meaning unclear | MEDIUM |
| Indicator Discovery | Key indicators hard to find | MEDIUM |
| Consistency | State vs Status confusion | LOW |

---

## Recommendations from Observation

1. **Reduce scroll dependency** - Critical data above fold
2. **Filter indicators** - Show only strategy-relevant indicators prominently
3. **Clarify terminology** - Replace INACTIVE with descriptive state
4. **Visual hierarchy** - Make important panels stand out

---

*Observation conducted by: Sally (UX Designer Agent)*
*BMAD Framework - FX Agent AI Project*
