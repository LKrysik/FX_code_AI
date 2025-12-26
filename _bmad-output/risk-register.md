# Risk Register - FX Agent AI

**Created:** 2025-12-26
**Updated:** 2025-12-26 (v1.1 - Paradox Verification Improvements)
**Owner:** PM (John)
**Review Cadence:** Weekly (during sprint review)
**Version:** 1.1

---

## Risk Scoring Matrix

### Probability (P)
| Score | Level | Description |
|-------|-------|-------------|
| 1 | Rare | < 10% chance |
| 2 | Unlikely | 10-30% chance |
| 3 | Possible | 30-50% chance |
| 4 | Likely | 50-70% chance |
| 5 | Almost Certain | > 70% chance |

### Impact (I)
| Score | Level | Description |
|-------|-------|-------------|
| 1 | Negligible | Minor inconvenience |
| 2 | Minor | Small delay or workaround needed |
| 3 | Moderate | Significant delay or quality impact |
| 4 | Major | Epic/milestone at risk |
| 5 | Critical | Project failure or financial loss |

### Risk Score = P x I
| Score | Level | Action Required |
|-------|-------|-----------------|
| 1-4 | Low | Monitor |
| 5-9 | Medium | Mitigation plan required |
| 10-15 | High | Immediate action required |
| 16-25 | Critical | Escalate, stop work if needed |

---

## Risk Categories

| Category | Description | Special Handling |
|----------|-------------|------------------|
| **FINANCIAL** | Direct money loss risk | NEVER accept without mitigation |
| Technical | Code/architecture issues | Standard process |
| Quality | Testing/reliability gaps | Standard process |
| Infrastructure | Environment/tooling | Standard process |
| Operational | Runtime/production | Requires runbook |
| External | Third-party dependencies | Monitor actively |
| Resource | People/time constraints | Standard process |
| Management | Process/scope issues | Standard process |

---

## Risk Correlations (WATCH LIST)

Risks that amplify each other when combined:

| Correlation ID | Risks | Combined Impact | Trigger Scenario |
|----------------|-------|-----------------|------------------|
| **CORR-01** | RISK-02 + RISK-04 + RISK-08 | CATASTROPHIC | No E2E tests + Strategy Builder bugs + Indicator errors = Wrong trades executed silently |
| **CORR-02** | RISK-03 + RISK-05 + RISK-09 | MAJOR | No Redis + WebSocket issues + DB slow = System unusable |
| **CORR-03** | RISK-06 + RISK-10 | HIGH | Solo dev + Scope creep = Burnout and project failure |
| **CORR-04** | RISK-11 + RISK-12 + RISK-05 | CATASTROPHIC | Position sizing error + Slippage + Disconnect = Major financial loss |

**Action:** When ANY risk in a correlation group increases, review ALL related risks.

---

## Mitigation Verification Protocol

For any risk marked "MITIGATED", require:

| Field | Required | Example |
|-------|----------|---------|
| **Verification Date** | Yes | 2025-12-25 |
| **Verification Method** | Yes | E2E test / Manual demo / Audit |
| **Evidence** | Yes | Screenshot / Test log / Recording |
| **Verified By** | Yes | Name or role |
| **Re-verification Schedule** | Yes | Monthly / Quarterly / One-time |

---

## Accepted Risk Protocol

For any risk marked "ACCEPTED":

| Requirement | Description |
|-------------|-------------|
| **Acceptance Reason** | Why is this acceptable? |
| **Acceptance Conditions** | Under what conditions does acceptance remain valid? |
| **Monitoring Signals** | What would indicate we need to re-evaluate? |
| **Expiry Date** | Max 3 months - then must re-evaluate |
| **Monthly Review** | MANDATORY even for accepted risks |

**RULE:** FINANCIAL category risks can NEVER be fully "ACCEPTED" - only "ACCEPTED WITH CONTROLS"

---

## Active Risks

### RISK-01: EventBridge Signal Disconnection (REALIZED → MITIGATED)
| Attribute | Value |
|-----------|-------|
| **ID** | RISK-01 |
| **Category** | Technical |
| **Status** | MITIGATED |
| **Probability** | 5 → 1 (post-fix) |
| **Impact** | 5 (blocked all signal flow) |
| **Score** | 25 → 5 |
| **Description** | EventBridge subscribed to wrong event name |
| **Detection Date** | 2025-12-23 |
| **Resolution** | Story 0-1 fix applied |
| **Lesson Learned** | Always verify event names match between publisher and subscriber |
| **Verification Date** | 2025-12-25 |
| **Verification Method** | E2E signal flow test |
| **Evidence** | Signal visible in browser console (story 0-2) |
| **Verified By** | Dev |
| **Re-verification** | After any EventBridge changes |

---

### RISK-02: No E2E Test Coverage
| Attribute | Value |
|-----------|-------|
| **ID** | RISK-02 |
| **Category** | Quality |
| **Status** | OPEN |
| **Probability** | 4 (Likely) |
| **Impact** | 4 (Major - undetected integration bugs) |
| **Score** | 16 (Critical) |
| **Description** | Zero E2E tests means integration bugs discovered in production |
| **Trigger** | Any deployment without manual testing |
| **Mitigation** | Epic 0 includes E2E signal flow verification story |
| **Owner** | TEA (Murat) |
| **Target Resolution** | End of Epic 0 |
| **Related Risks** | CORR-01 (with RISK-04, RISK-08) |

---

### RISK-03: Redis Unavailability
| Attribute | Value |
|-----------|-------|
| **ID** | RISK-03 |
| **Category** | Infrastructure |
| **Status** | ACCEPTED WITH CONTROLS |
| **Probability** | 5 (Certain - Windows without Docker) |
| **Impact** | 2 (Minor - degraded caching only) |
| **Score** | 10 (High) |
| **Description** | Redis not available on development environment |
| **Mitigation** | System designed to work without Redis (graceful degradation) |
| **Owner** | Architect (Winston) |
| **Acceptance Reason** | MVP works without Redis |
| **Acceptance Conditions** | Performance remains acceptable, no features require Redis |
| **Monitoring Signals** | Performance degradation, cache-dependent feature needed |
| **Expiry Date** | 2025-03-26 (re-evaluate) |
| **Related Risks** | CORR-02 |

---

### RISK-04: Strategy Builder Silent Failures
| Attribute | Value |
|-----------|-------|
| **ID** | RISK-04 |
| **Category** | Technical |
| **Status** | INVESTIGATING |
| **Probability** | 3 (Possible) |
| **Impact** | 4 (Major - user thinks config saved but isn't) |
| **Score** | 12 (High) |
| **Description** | Strategy Builder may have bugs where save appears successful but data is corrupted |
| **Trigger** | Complex strategy configurations |
| **Mitigation** | Story 0-3 Strategy Builder Audit |
| **Owner** | Dev (Amelia) |
| **Target Resolution** | End of Epic 0 |
| **Related Risks** | CORR-01 (with RISK-02, RISK-08) |

---

### RISK-05: WebSocket Disconnection During Live Trading
| Attribute | Value |
|-----------|-------|
| **ID** | RISK-05 |
| **Category** | Operational |
| **Status** | OPEN |
| **Probability** | 3 (Possible) |
| **Impact** | 5 (Critical - financial loss possible) |
| **Score** | 15 (High) |
| **Description** | If WebSocket disconnects during active position, user may not see signals |
| **Trigger** | Network instability, server restart |
| **Mitigation** | Epic 4 includes auto-reconnect (FR41) and recovery options (FR42) |
| **Owner** | Dev (Amelia) |
| **Target Resolution** | Before live trading (Epic 4) |
| **Related Risks** | CORR-02, CORR-04 |

---

### RISK-06: Single Point of Failure (Solo Developer)
| Attribute | Value |
|-----------|-------|
| **ID** | RISK-06 |
| **Category** | Resource |
| **Status** | ACCEPTED WITH CONTROLS |
| **Probability** | 2 (Unlikely short-term) |
| **Impact** | 5 (Critical - project stops) |
| **Score** | 10 (High) |
| **Description** | Only one developer (Mr Lu) - illness/vacation stops all progress |
| **Mitigation** | Comprehensive documentation, AI-assistable codebase |
| **Owner** | PM (John) |
| **Acceptance Reason** | MVP phase, resource constraint |
| **Acceptance Conditions** | Developer remains healthy and available |
| **Monitoring Signals** | > 3 consecutive days without commit |
| **Expiry Date** | 2025-03-26 (re-evaluate for Phase 2) |
| **Related Risks** | CORR-03 |

---

### RISK-07: MEXC API Changes
| Attribute | Value |
|-----------|-------|
| **ID** | RISK-07 |
| **Category** | External |
| **Status** | MONITORING |
| **Probability** | 2 (Unlikely in 3 months) |
| **Impact** | 4 (Major - trading breaks) |
| **Score** | 8 (Medium) |
| **Description** | MEXC may change API without notice, breaking integration |
| **Trigger** | MEXC API update |
| **Mitigation** | Abstract exchange interface exists (adapter pattern) |
| **Owner** | Architect (Winston) |
| **Monitoring** | Check MEXC changelog monthly |

---

### RISK-08: Indicator Calculation Errors
| Attribute | Value |
|-----------|-------|
| **ID** | RISK-08 |
| **Category** | Quality |
| **Status** | OPEN |
| **Probability** | 3 (Possible) |
| **Impact** | 4 (Major - wrong trading decisions) |
| **Score** | 12 (High) |
| **Description** | Custom indicators (TWPA, pump_magnitude, etc.) may have calculation bugs |
| **Trigger** | Edge cases in market data |
| **Mitigation** | Epic 4 includes indicator verification stories |
| **Owner** | TEA (Murat) |
| **Target Resolution** | Before live trading |
| **Related Risks** | CORR-01 (with RISK-02, RISK-04) |

---

### RISK-09: QuestDB Performance Degradation
| Attribute | Value |
|-----------|-------|
| **ID** | RISK-09 |
| **Category** | Infrastructure |
| **Status** | MONITORING |
| **Probability** | 2 (Unlikely) |
| **Impact** | 3 (Moderate - slow backtests) |
| **Score** | 6 (Medium) |
| **Description** | As data grows, QuestDB may slow down |
| **Trigger** | > 100M rows or > 6 months data |
| **Mitigation** | Data retention policy, partitioning strategy |
| **Owner** | Architect (Winston) |
| **Monitoring** | Track query times monthly |
| **Related Risks** | CORR-02 |

---

### RISK-10: Scope Creep
| Attribute | Value |
|-----------|-------|
| **ID** | RISK-10 |
| **Category** | Management |
| **Status** | MONITORING |
| **Probability** | 4 (Likely) |
| **Impact** | 3 (Moderate - delays MVP) |
| **Score** | 12 (High) |
| **Description** | Adding features before MVP complete |
| **Trigger** | "Quick" feature requests |
| **Mitigation** | Strict MVP definition, PRD as contract |
| **Owner** | PM (John) |
| **Rule** | NO new features until Pipeline Completion Rate >= 90% |
| **Related Risks** | CORR-03 |

---

## Financial Risks (NEW CATEGORY)

### RISK-11: Incorrect Position Sizing
| Attribute | Value |
|-----------|-------|
| **ID** | RISK-11 |
| **Category** | **FINANCIAL** |
| **Status** | OPEN |
| **Probability** | 2 (Unlikely if tested) |
| **Impact** | 5 (Critical - direct money loss) |
| **Score** | 10 (High) |
| **Financial Exposure** | Up to 100% of position size |
| **Description** | Position size calculated incorrectly (e.g., decimal error, leverage miscalculation) |
| **Trigger** | Edge cases in position sizing logic |
| **Mitigation** | Unit tests with boundary values, manual verification before live |
| **Owner** | Dev (Amelia) |
| **Target Resolution** | Before live trading |
| **Related Risks** | CORR-04 |
| **HARD RULE** | NO live trading until position sizing verified with paper trading |

---

### RISK-12: Slippage Beyond Expected
| Attribute | Value |
|-----------|-------|
| **ID** | RISK-12 |
| **Category** | **FINANCIAL** |
| **Status** | MONITORING |
| **Probability** | 3 (Possible in volatile markets) |
| **Impact** | 3 (Moderate - 1-5% per trade) |
| **Score** | 9 (Medium) |
| **Financial Exposure** | 1-5% per trade |
| **Description** | Market moves faster than execution, actual price differs from expected |
| **Trigger** | High volatility, low liquidity, large orders |
| **Mitigation** | Limit orders where possible, small position sizes, slippage tolerance setting |
| **Owner** | Architect (Winston) |
| **Monitoring** | Track actual vs expected fill prices |
| **Related Risks** | CORR-04 |

---

### RISK-13: Exchange Account Restrictions
| Attribute | Value |
|-----------|-------|
| **ID** | RISK-13 |
| **Category** | **FINANCIAL** |
| **Status** | MONITORING |
| **Probability** | 2 (Unlikely) |
| **Impact** | 5 (Critical - cannot trade) |
| **Score** | 10 (High) |
| **Financial Exposure** | Locked funds |
| **Description** | MEXC restricts or closes account due to automated trading detection or compliance |
| **Trigger** | High-frequency trading patterns, KYC issues |
| **Mitigation** | Rate limiting, human-like trading patterns, complete KYC |
| **Owner** | PM (John) |
| **Monitoring** | Watch for account warnings |

---

## Risk Summary Dashboard

| Score Range | Count | Risks |
|-------------|-------|-------|
| Critical (16-25) | 1 | RISK-02 |
| High (10-15) | 7 | RISK-03, RISK-04, RISK-05, RISK-06, RISK-08, RISK-10, RISK-11, RISK-13 |
| Medium (5-9) | 3 | RISK-07, RISK-09, RISK-12 |
| Low (1-4) | 0 | - |
| Mitigated | 1 | RISK-01 |

### Financial Risk Summary
| Risk | Exposure | Status |
|------|----------|--------|
| RISK-11 | Up to 100% position | OPEN - Block live trading |
| RISK-12 | 1-5% per trade | MONITORING |
| RISK-13 | Locked funds | MONITORING |

---

## Escalation Path

| Trigger | Action | Who |
|---------|--------|-----|
| Any risk score increases to 16+ | Stop current sprint, address immediately | PM + Dev |
| Financial risk materializes | Stop all trading, assess damage | PM |
| Owner doesn't update risk in 2 weeks | Escalate to PM | SM |
| Accepted risk conditions violated | Re-open risk, re-evaluate | PM |
| Correlation trigger activated | Review all related risks | PM + Team |

---

## Risk Review Log

| Date | Reviewer | Changes |
|------|----------|---------|
| 2025-12-26 | PM | Initial creation |
| 2025-12-26 | PM | v1.1: Added Financial category, correlations, verification protocol, accepted risk protocol |

---

## New Risk Template

```markdown
### RISK-XX: [Title]
| Attribute | Value |
|-----------|-------|
| **ID** | RISK-XX |
| **Category** | FINANCIAL / Technical / Quality / Infrastructure / Operational / External / Resource / Management |
| **Status** | OPEN / INVESTIGATING / MITIGATED / ACCEPTED WITH CONTROLS / CLOSED |
| **Probability** | 1-5 |
| **Impact** | 1-5 |
| **Score** | P x I |
| **Financial Exposure** | (if FINANCIAL category) |
| **Description** | What could go wrong? |
| **Trigger** | What causes this risk to materialize? |
| **Mitigation** | How to prevent or reduce? |
| **Owner** | Who is responsible? |
| **Target Resolution** | When should this be addressed? |
| **Related Risks** | Which correlation group? |
```

---

*Review this register weekly. Add new risks as discovered. Update status as work progresses. FINANCIAL risks require extra scrutiny.*
