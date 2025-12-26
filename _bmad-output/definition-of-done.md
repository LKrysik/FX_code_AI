# Definition of Done (DoD) - FX Agent AI

**Created:** 2025-12-26
**Updated:** 2025-12-26 (v1.1 - Paradox Verification Improvements)
**Owner:** PM (John) + SM (Bob)
**Version:** 1.1

---

## Purpose

This document defines when a story, epic, or release is considered "done". Without clear DoD, work remains perpetually "in progress" and quality becomes inconsistent.

---

## Story Definition of Done (Base)

A story is **DONE** when ALL of the following are true:

### 1. Code Complete
- [ ] All tasks and subtasks in story file marked complete
- [ ] Code compiles without errors
- [ ] No new linter warnings introduced
- [ ] Code follows project conventions (snake_case, response envelope, etc.)

### 2. Tests Pass
- [ ] All existing tests pass (no regressions)
- [ ] New unit tests written for new code (see coverage targets by category below)
- [ ] Integration tests pass (if applicable)
- [ ] Manual smoke test performed

**Test Quality Requirements (Anti-Gaming):**
- [ ] Tests include at least 1 happy path per function
- [ ] Tests include at least 1 edge case per function
- [ ] No test is just "assert true" or trivial
- [ ] Critical path tests are marked with `@critical` decorator

### 3. Code Review
- [ ] Code reviewed using ONE of these methods:
  - AI reviewer (code-review workflow) - RECOMMENDED
  - Self-review with checklist (for trivial changes only)
  - "Rubber duck" walkthrough: explain code out loud, record issues
- [ ] All review findings addressed or deferred with justification
- [ ] No critical or high-severity issues remaining
- [ ] Re-review required only for critical findings (not minor style issues)

**Minimum Review Time:**
| Story Size | Min Review Time |
|------------|-----------------|
| XS | 10 min |
| S | 15 min |
| M | 30 min |
| L | 60 min |

### 4. Documentation
- [ ] Code comments added where logic is not self-evident
- [ ] API changes documented (if applicable)
- [ ] Story file updated with completion notes

### 5. Acceptance Criteria (EXPANDED)
- [ ] Each AC individually tested
- [ ] AC test results documented (pass/fail with evidence)
- [ ] Edge cases for each AC considered
- [ ] Stakeholder demo if AC is user-facing
- [ ] No AC marked "N/A" without PM approval

### 6. Technical Debt
- [ ] No new TODO/FIXME/HACK comments without linked issue
- [ ] If technical debt introduced, documented in KNOWN_ISSUES.md

---

## DoD by Code Category

Different code types have different quality requirements.

### Trading/Financial Logic (STRICT)
**Coverage Target: 90%+**

ADDITIONAL requirements beyond base DoD:
- [ ] Numerical precision verified (Decimal handling, not float)
- [ ] Unit tests cover boundary values (0, negative, max, min)
- [ ] Edge cases: empty data, single data point, extreme values
- [ ] Code reviewed by someone with domain knowledge (or AI with context)
- [ ] Manual test with real/realistic market data
- [ ] All calculations have reference/expected values documented

**Examples:** Indicators (TWPA, pump_magnitude), Position sizing, P&L calculation, Order execution

### Infrastructure/Backend (STANDARD)
**Coverage Target: 80%**

ADDITIONAL requirements:
- [ ] Error handling tested (what happens on failure?)
- [ ] Logging adequate for debugging
- [ ] Performance acceptable (no obvious bottlenecks)
- [ ] Failure scenario tested (disconnect, timeout, etc.)

**Examples:** WebSocket handlers, API endpoints, Database queries, Event handlers

### UI Components (RELAXED)
**Coverage Target: 60%**

MODIFIED requirements:
- [ ] Visual regression test OR screenshot comparison (manual OK)
- [ ] Renders without console errors
- [ ] Responsive behavior verified (if applicable)
- [ ] Accessibility basics: keyboard nav, focus visible

**Examples:** Dashboard widgets, Charts, Form components, Status displays

### Configuration/Scripts (MINIMAL)
**Coverage Target: N/A (manual verification)**

SIMPLIFIED requirements:
- [ ] Works as intended (manual test)
- [ ] No sensitive data exposed
- [ ] Documented if non-obvious

**Examples:** Config files, Build scripts, Migration scripts

---

## Minimum Time Investment

To prevent rushing through DoD checkboxes:

| Story Size | Total Time | Min Test Time | Min Review Time |
|------------|------------|---------------|-----------------|
| XS | 30 min | 10 min | 10 min |
| S | 2h | 30 min | 15 min |
| M | 4h | 1h | 30 min |
| L | 8h | 2h | 60 min |

If story completed significantly faster, verify quality before marking done.

---

## Epic Definition of Done

An epic is **DONE** when ALL of the following are true:

- [ ] All stories in epic are DONE (per story DoD above)
- [ ] Epic goal achieved (from epic description)
- [ ] Integration between stories verified
- [ ] Epic retrospective completed (REQUIRED, not optional)
- [ ] sprint-status.yaml updated to show epic as "done"

---

## Release Definition of Done (Milestone)

A release/milestone is **DONE** when:

- [ ] All planned epics are DONE
- [ ] Release criteria document satisfied (see release-criteria-m1.md etc.)
- [ ] No critical or high-severity bugs open
- [ ] Rollback plan tested (for production releases)
- [ ] Key learnings documented

---

## Exception Process

When a story cannot meet DoD:

1. **Document exception** - Why can't DoD be met?
2. **Get approval** - PM/Tech Lead approval required
3. **Create follow-up** - Technical debt story created
4. **Mark explicitly** - Story marked as "done-with-exceptions"

### Exception Limits (Anti-Abuse)

| Story Size | Max Exceptions Allowed |
|------------|------------------------|
| XS/S | NO exceptions allowed |
| M | Max 1 exception per story |
| L | Max 2 exceptions, PM approval required |

**Sprint Total:** Max 3 exceptions per sprint. More requires escalation.

**Exception Expiry:** All exceptions must be resolved within 2 sprints or converted to tech debt stories.

---

## DoD Checklist Templates

### Quick Checklist (Copy-Paste for Stories)
```markdown
## DoD Checklist
- [ ] All tasks/subtasks complete
- [ ] Code compiles, no new warnings
- [ ] Follows project conventions
- [ ] Existing tests pass
- [ ] New tests written (coverage per category)
- [ ] Code reviewed (min time met)
- [ ] Review findings addressed
- [ ] Each AC individually verified with evidence
- [ ] No critical bugs
- [ ] No undocumented tech debt
```

### Trading Logic Checklist (For Financial Code)
```markdown
## Trading Logic DoD
- [ ] Base DoD complete
- [ ] Coverage >= 90%
- [ ] Decimal precision verified (not float)
- [ ] Boundary values tested (0, negative, max)
- [ ] Edge cases: empty, single, extreme
- [ ] Manual test with real market data
- [ ] Calculations have reference values documented
```

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-26 | PM/SM | Initial version |
| 1.1 | 2025-12-26 | PM/SM | Added: Category variants, exception limits, time requirements, test quality gates, expanded AC |

---

*This document is a living artifact. Update as team learns what "done" truly means.*
