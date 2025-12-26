# Story 1A.8: Quick Start Option

Status: ready-for-dev

## Story

As a **new trader (Trader A)**,
I want **a button to quickly load a default/template strategy**,
so that **I can start seeing signals immediately without complex configuration**.

## Acceptance Criteria

1. **AC1:** "Quick Start" button visible on dashboard when no strategy is active
2. **AC2:** Clicking loads a pre-configured pump detection strategy
3. **AC3:** Strategy uses sensible defaults (7% pump, 3x volume, etc.)
4. **AC4:** After loading, user sees confirmation and can start a session
5. **AC5:** Quick Start is non-destructive (doesn't overwrite user's strategies)

## Tasks / Subtasks

- [ ] **Task 1: Create Quick Start Button** (AC: 1)
  - [ ] 1.1 Add prominent button to dashboard
  - [ ] 1.2 Show only when no active strategy/session
  - [ ] 1.3 Use friendly label: "Quick Start" or "Try Demo"
  - [ ] 1.4 Style as primary action (filled button)

- [ ] **Task 2: Define Template Strategy** (AC: 2, 3)
  - [ ] 2.1 Create default pump detection config
  - [ ] 2.2 S1: pump_magnitude > 7%, volume_surge > 3x
  - [ ] 2.3 Z1: spread < 0.5%
  - [ ] 2.4 ZE1: unrealized_pnl > 5%
  - [ ] 2.5 Store as JSON template

- [ ] **Task 3: Load Strategy Flow** (AC: 4)
  - [ ] 3.1 On click, load template strategy
  - [ ] 3.2 Apply to current session
  - [ ] 3.3 Show success toast/confirmation
  - [ ] 3.4 Update dashboard to show strategy is active

- [ ] **Task 4: Non-Destructive Behavior** (AC: 5)
  - [ ] 4.1 Don't save to user's strategy list automatically
  - [ ] 4.2 Label as "Demo Strategy" or "Quick Start Template"
  - [ ] 4.3 Offer "Save as my strategy" option after use

## Dev Notes

### Trader A Requirement

From Epics: "Quick Start Option - Button to load default/template strategy for immediate testing (Trader A)"

Purpose: Remove friction for new users. Let them see signals immediately without understanding all configuration.

### Default Strategy Template

```json
{
  "strategy_name": "Quick Start - Pump Detection",
  "version": "1.0",
  "is_template": true,
  "sections": {
    "S1": {
      "name": "Signal Detection",
      "conditions": [
        { "indicator": "pump_magnitude_pct", "operator": ">", "value": 7 },
        { "indicator": "volume_surge_ratio", "operator": ">", "value": 3 }
      ]
    },
    "O1": {
      "name": "Cancellation",
      "conditions": [
        { "indicator": "pump_magnitude_pct", "operator": "<", "value": 3 }
      ]
    },
    "Z1": {
      "name": "Entry Confirmation",
      "conditions": [
        { "indicator": "spread_pct", "operator": "<", "value": 0.5 }
      ]
    },
    "ZE1": {
      "name": "Exit with Profit",
      "conditions": [
        { "indicator": "unrealized_pnl_pct", "operator": ">", "value": 5 }
      ]
    },
    "E1": {
      "name": "Emergency Exit",
      "conditions": [
        { "indicator": "unrealized_pnl_pct", "operator": "<", "value": -3 }
      ]
    }
  }
}
```

### UI Flow

```
Dashboard (no active strategy)
    ↓
┌─────────────────────────────────────┐
│  No active strategy                 │
│                                     │
│  [🚀 Quick Start]  [Create New]     │
│                                     │
└─────────────────────────────────────┘
    ↓ Click Quick Start
Toast: "Demo strategy loaded! Ready to start backtest."
    ↓
Dashboard shows strategy active
```

### Button Placement

Position prominently when dashboard is "empty":
- Center of screen OR
- Next to StatusHero OR
- In empty state of signal list

### Related to Story 0-3

This depends on Strategy Builder Audit (0-3) confirming save/load works.

### References

- [Source: _bmad-output/epics.md#Epic 1A Story 8]
- [Source: _bmad-output/ux-design-specification.md#Trader A Persona]
- [Source: _bmad-output/epics.md#Starter Strategy Templates (Epic 2)]

## Dev Agent Record

### Agent Model Used
{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
