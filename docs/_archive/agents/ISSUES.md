# Issues & Blockers - Multi-Agent Implementation

**Purpose:** Track and escalate blocking issues that require Agent 0 intervention
**When to Use:** Interface conflicts, architectural questions, blockers, breaking changes
**Response Time:** Agent 0 will respond to CRITICAL issues within 4 hours

---

## Instructions for Agents

**When to create an issue:**
- You need to change an interface that affects other agents
- You discover a blocking dependency
- You find a conflict between your code and another agent's code
- You need architectural guidance
- You discover a bug in another agent's code
- You have a question that blocks your progress

**Issue Format:**
```markdown
## Issue #XXX: [Brief Title]

**Reported by:** Agent N (Role)
**Severity:** CRITICAL | HIGH | MEDIUM | LOW
**Status:** OPEN | IN_PROGRESS | RESOLVED | CLOSED
**Assigned to:** [Agent N or Agent 0]
**Date Opened:** YYYY-MM-DD
**Date Resolved:** YYYY-MM-DD (if resolved)

**Description:**
[Clear description of the issue]

**Impact:**
- Blocks: [Which agents/tasks are blocked]
- Affects: [Which components/interfaces are affected]

**Proposed Solution:**
[Your suggested fix]

**Decision Required From:** Agent 0 (or specific agent)

**Resolution:**
[How was this resolved? - Filled by Agent 0 or assigned agent]

**ETA:** [Estimated time to resolve]
```

**Severity Levels:**
- **CRITICAL:** Blocks multiple agents, requires immediate attention
- **HIGH:** Blocks one agent or critical path task
- **MEDIUM:** Doesn't block progress but needs resolution
- **LOW:** Nice to have, can be deferred

---

## Issue Template

Copy this when creating a new issue:

```markdown
## Issue #XXX: [Title]

**Reported by:** Agent N
**Severity:** CRITICAL
**Status:** OPEN
**Assigned to:** Agent 0
**Date Opened:** YYYY-MM-DD

**Description:**


**Impact:**
- Blocks:
- Affects:

**Proposed Solution:**


**Decision Required From:** Agent 0

**Resolution:**
(To be filled when resolved)

**ETA:**

---
```

---

## Active Issues

### OPEN Issues

(No open issues yet - project just starting)

---

### RESOLVED Issues

(No resolved issues yet)

---

## Example Issues (For Reference)

### Example 1: Interface Breaking Change

```markdown
## Issue #001: EventBus Topic Naming Convention Conflict

**Reported by:** Agent 3 (Live Trading Core)
**Severity:** HIGH
**Status:** RESOLVED
**Assigned to:** Agent 1
**Date Opened:** 2025-11-08
**Date Resolved:** 2025-11-08

**Description:**
Agent 1's EventBus uses dot notation for topics (e.g., "order.created")
Agent 3's LiveOrderManager expects underscore notation (e.g., "order_created")
INTERFACE_CONTRACTS.md specifies underscore notation.

**Impact:**
- Blocks: Integration between LiveOrderManager and EventBus
- Affects: Agent 6 (EventBridge) will also be affected

**Proposed Solution:**
Standardize on underscore notation (matches Python convention and INTERFACE_CONTRACTS.md)
Agent 1 to update EventBus TOPICS constant to use underscores.

**Decision Required From:** Agent 0

**Resolution:**
Agent 0 decided: Use underscore notation (Python standard)
Agent 1 updated EventBus to use "order_created", "market_data", etc.
INTERFACE_CONTRACTS.md updated to v1.1 with this clarification.
All agents notified.

**ETA:** 1h (COMPLETED)
```

### Example 2: Architectural Question

```markdown
## Issue #002: Should RiskManager Subscribe to EventBus or Be Called Directly?

**Reported by:** Agent 2 (Risk Management)
**Severity:** MEDIUM
**Status:** RESOLVED
**Assigned to:** Agent 0
**Date Opened:** 2025-11-09

**Description:**
Two possible architectures for RiskManager:

Option A: LiveOrderManager calls RiskManager directly
- Signal → LiveOrderManager → RiskManager.validate() → Order

Option B: RiskManager subscribes to signal_generated events
- Signal → EventBus → RiskManager (validator) → EventBus → LiveOrderManager

Which approach should I use?

**Impact:**
- Affects: Agent 3 (LiveOrderManager) integration
- Affects: INTERFACE_CONTRACTS.md (need to update)

**Proposed Solution:**
I prefer Option A (direct call) because:
1. Clearer error handling
2. Synchronous validation before order submission
3. Simpler to test

**Decision Required From:** Agent 0

**Resolution:**
Agent 0 decided: Option A (direct call)
Reasoning: Risk validation is a synchronous gate, not an event listener.
EventBus should only be used for broadcasting events, not for request-response patterns.

INTERFACE_CONTRACTS.md already reflects this (LiveOrderManager calls RiskManager.validate_order())
No changes needed.

**ETA:** N/A (no code change required)
```

### Example 3: Dependency Blocker

```markdown
## Issue #003: Agent 3 Blocked by Agent 1 Delay

**Reported by:** Agent 3 (Live Trading Core)
**Severity:** CRITICAL
**Status:** RESOLVED
**Assigned to:** Agent 0
**Date Opened:** 2025-11-10

**Description:**
Agent 1 was scheduled to complete EventBus + Circuit Breaker by end of Week 1.
It's now Day 5 and EventBus is only 60% done, Circuit Breaker not started.

Agent 3 cannot start LiveOrderManager implementation without these dependencies.

**Impact:**
- Blocks: Agent 3 (all tasks)
- Risk: M1 milestone delay

**Proposed Solution:**
Option A: Wait for Agent 1 (accept 2-day delay)
Option B: Agent 3 creates mock EventBus + Circuit Breaker for development

**Decision Required From:** Agent 0

**Resolution:**
Agent 0 decided: Option B (create mocks)

Action Plan:
1. Agent 0 provides mock specifications
2. Agent 3 develops LiveOrderManager against mocks
3. Agent 1 continues real implementation (no pressure)
4. Agent 3 swaps mocks for real implementation when ready
5. Integration testing in Week 3

Mock specs provided in INTERFACE_CONTRACTS.md under "Testing Mocks" section.

**ETA:** Agent 3 can resume work immediately
```

### Example 4: Bug in Another Agent's Code

```markdown
## Issue #004: Circuit Breaker Not Resetting After HALF_OPEN Success

**Reported by:** Agent 3 (Live Trading Core)
**Severity:** HIGH
**Status:** OPEN
**Assigned to:** Agent 1
**Date Opened:** 2025-11-12

**Description:**
While testing LiveOrderManager integration, I discovered that Circuit Breaker
is not transitioning from HALF_OPEN → CLOSED after a successful call.

According to INTERFACE_CONTRACTS.md:
"HALF_OPEN → CLOSED: After 1 successful call"

But in practice, it stays in HALF_OPEN indefinitely.

**Impact:**
- Blocks: LiveOrderManager integration tests
- Affects: Production reliability (circuit will never close)

**Proposed Solution:**
Agent 1 to review Circuit Breaker state transition logic in _execute() method.
Likely missing state update after successful call in HALF_OPEN state.

**Decision Required From:** Agent 1 (to fix)

**Resolution:**
(To be filled by Agent 1)

**ETA:** 2h (requested)
```

---

## Issue Assignment Rules

1. **Interface conflicts:** Agent 0 decides, assigns to affected agents
2. **Architectural questions:** Agent 0 decides
3. **Bugs in code:** Assigned to code owner (agent that wrote it)
4. **Dependency blockers:** Agent 0 evaluates options (wait vs. mock)
5. **Configuration questions:** Agent 0 decides

---

## Escalation to User (LKrysik)

Agent 0 will escalate to user if:
- Multiple CRITICAL issues open for > 24 hours
- Milestone at risk of > 1 week delay
- Architectural conflict cannot be resolved by Agent 0
- Resource allocation question (need more agents?)

**Escalation Format:**
- Summary of issue
- Impact on timeline/milestone
- Options evaluated
- Recommended decision
