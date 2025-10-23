---
description: "Smart sprint closure with automated verification"
---

# /end_sprint - Close Sprint with Anti-False-Success

**Purpose**: Close sprint with streamlined but effective verification

**Usage**: `/end_sprint`

## Smart Sprint Closure Process

### 1. Load Sprint Context
- Read `docs/sprints/SPRINT_[N]_PLAN.md` → planned goals
- Read `SPRINT_BACKLOG.md` → task status

### 2. Automated Task Verification Pipeline

#### **For Each Task Marked DONE:**
```bash
# Run automated verification pipeline
python scripts/verify_evidence.py [task_id] "[task_description]"

# Pipeline results:
# ✅ VERIFICATION_PASSED → Task confirmed DONE
# 🔍 ENHANCED_VERIFICATION_REQUIRED → Manual review needed  
# ❌ VERIFICATION_FAILED → Move task back to IN_PROGRESS
```

#### **Verification Status Matrix:**
```markdown
Task Status Rules:
- VERIFICATION_PASSED → ✅ DONE (confirmed)
- ENHANCED_VERIFICATION_REQUIRED → 🔍 MANUAL_REVIEW 
- VERIFICATION_FAILED → ⚠️ IN_PROGRESS (needs work)

Sprint closes ONLY when all tasks are ✅ or 🔍
```

### 3. Enhanced Verification Queue (10% of tasks)

#### **For Tasks Requiring Manual Review:**
```markdown
Enhanced verification checklist:
- [ ] Video evidence reviewed
- [ ] Manual browser testing verified
- [ ] Cross-reference git commits with claimed implementation
- [ ] Integration testing confirmed
- [ ] Red flag investigation completed

Manual reviewer: [human/senior agent]
Review date: [timestamp]
Result: APPROVED/REJECTED/NEEDS_WORK
```

### 4. Sprint Quality Assessment

#### **Goal Achievement Check:**
```markdown
Original Goal: [from SPRINT_PLAN.md]
Tasks Completed: [X/Y] (only count ✅ verified tasks)
Goal Achievement: [FULL/PARTIAL/MINIMAL]

User Value Delivered:
- [What user can now do that they couldn't before]
- [Key workflows enabled]
- [Business value created]
```

#### **Quality Metrics:**
```markdown
Sprint Quality Score:
- Verification Pass Rate: [X%] (target: >90%)
- False Positive Detection: [Y red flags found]
- Rework Required: [Z tasks failed verification]
- Enhanced Reviews: [A tasks required manual verification]
```

### 5. Anti-Deception Report

#### **Automated Analysis Results:**
```markdown
Red Flags Detected:
- Generic task descriptions: [count]
- Evidence inconsistencies: [count]  
- Suspicious patterns: [count]
- Perfect scores for complex tasks: [count]

Agent Reliability Metrics:
- Tasks passed automated verification: [X%]
- Tasks required enhanced verification: [Y%]
- Tasks failed verification: [Z%]
```

### 6. Sprint Closure Decision

#### **SPRINT_COMPLETE (All criteria met):**
- [ ] All planned tasks verified (✅ or 🔍 approved)
- [ ] Goal achievement acceptable (FULL or PARTIAL)
- [ ] No critical red flags unresolved
- [ ] Quality metrics meet thresholds

#### **SPRINT_INCOMPLETE (Issues found):**
```markdown
Blockers preventing closure:
- [X] tasks failed verification
- [Y] tasks pending enhanced review
- [Z] critical red flags unresolved

Actions required:
1. Fix failed verification tasks
2. Complete enhanced reviews
3. Investigate red flags
4. Re-run verification pipeline
```

### 7. Sprint Documentation

#### **Sprint Report Generation:**
```markdown
# Sprint [N] Report

## Goal Achievement
Original Goal: [goal]
Status: [ACHIEVED/PARTIALLY_ACHIEVED/NOT_ACHIEVED]
User Value: [what was delivered]

## Task Summary
Total Tasks: [X]
Verified Complete: [Y] ✅
Manual Review: [Z] 🔍
Failed Verification: [W] ❌

## Quality Assessment
Verification Success Rate: [X%]
Red Flags Detected: [Y]
Enhanced Reviews Required: [Z%]

## Lessons Learned
- What worked well
- What caused false positives
- Process improvements needed

## Next Sprint Recommendations
- Carry-over tasks: [list]
- Process adjustments: [list]
- Quality focus areas: [list]
```

## Integration with Verification Pipeline

### Workflow Summary:
1. Agent completes task → `/work` with automated verification
2. Task verified → `/verify_implementation` with smart checks
3. Sprint closure → `/end_sprint` with pipeline verification
4. Enhanced reviews for flagged tasks
5. Sprint closes only when quality thresholds met

### Protection Level: **Phase 1 = 50-70% false positive reduction**
- Automated verification catches obvious issues
- Smart red flag detection identifies suspicious patterns
- Enhanced verification for high-risk tasks
- Quality metrics prevent systematic gaming

**BLOCKING CONDITIONS - Sprint cannot close if ANY found:**
- Task marked DONE but manual testing fails
- UI components render but don't function
- API returns data but UI doesn't update
- Tests pass but user workflow broken
- Feature works in isolation but breaks integration
- No evidence provided for manual testing

**False Positive Detection:**
```bash
# Run these checks for EVERY completed task:
# 1. Manual browser test of UI features
# 2. API testing with real requests
# 3. End-to-end user workflow testing
# 4. Integration testing with existing features
# 5. Evidence review (screenshots, logs)
```

### 3. Run Basic Tests
- Run core test suites to make sure nothing is broken
- Frontend: `pytest --playwright tests/frontend/ -x` (stop on first failure)
- Backend: `pytest tests/backend/ -x` (stop on first failure)
- If major test failures → mark sprint as incomplete

### 4. Summarize Results
Create `docs/sprints/SPRINT_[N]_REPORT.md`:

```markdown
# Sprint [N] Report

## Goal
[Copy goal from plan]

## Completed Tasks
- [List tasks that are DONE and verified]

## Incomplete Tasks  
- [List tasks that are IN_PROGRESS or NOT_STARTED]
- [Brief reason why not finished]

## What Works Now
[Simple description of new user functionality]

## Issues Found
[Any bugs or problems discovered]

## Next Sprint Focus
[What should be prioritized next]
```

### 5. Update Status
- Update `docs/STATUS.md` → SPRINT_COMPLETE
- Move incomplete tasks to next sprint in `SPRINT_BACKLOG.md`
- Note any blockers that need attention

## Success Criteria
- All DONE tasks are verified working
- Core functionality still works (tests pass)
- Team knows what was accomplished
- Next steps are clear

## Keep It Simple
- Don't require perfect documentation - require working features
- Don't block on minor issues - focus on user value delivered
- Don't over-analyze - summarize and move forward
- Don't demand 100% completion - some carryover is normal

## Output

### Files Modified
- `docs/sprints/SPRINT_[N]_REPORT.md`: Sprint summary created
- `SPRINT_BACKLOG.md`: Updated with final task status
- `docs/STATUS.md`: Sprint marked complete

### What Happens Next
- Review sprint report to understand progress
- Plan next sprint based on incomplete tasks and new priorities
- Continue development with `/start_sprint` for next goal

    # Check TASKS → VERIFICATION completion
    for task in goal.tasks:
        if task.status == "DONE" and not task.verification_report:
            BLOCK_CLOSURE: f"Task {task.id} DONE without verification"

    # Check business value delivery
    if not goal.success_metrics_achieved:
        BLOCK_CLOSURE: f"GOAL_{goal_id} success metrics not met"

# Validate QA framework coverage
qa_coverage = validate_qa_coverage(sprint_work)
if not qa_coverage.business_logic_100pct:
    BLOCK_CLOSURE: "Business logic tests <100% coverage"
if not qa_coverage.frontend_actions_100pct:
    BLOCK_CLOSURE: "Frontend action coverage <100%"
if not qa_coverage.data_integrity_complete:
    BLOCK_CLOSURE: "Data integrity tests incomplete"
```

**Generate Enhanced Fulfillment Report**:
```markdown
## Requirement Fulfillment Audit (Complete Traceability)

### Framework Health Check
- BUSINESS_GOALS.md: [✓ Complete / ✗ Incomplete]
- ADR Compliance: [✓ All decisions documented / ⚠️ Missing entries]
- Traceability Coverage: [X%] (USER_REC → GOAL → TASKS → VERIFICATION)

### Goal Achievement Assessment
Total Sprint Goals: [count]
Achieved Goals: [count] (✓)
Partially Achieved: [count] (⚠️)
Not Achieved: [count] (✗)

#### ✅ ACHIEVED GOALS
- **GOAL_[ID]**: [description]
  - USER_REC Source: [USER_REC_01/02]
  - Success Metrics: [X/Y achieved]
  - Verification: [docs/verification/task_ids]
  - Business Value: [delivered/not delivered]

#### ⚠️ PARTIALLY ACHIEVED GOALS (BLOCKS CLOSURE)
- **GOAL_[ID]**: [reason not fully achieved]
  - Missing: [specific success criteria not met]
  - Carryover: [what needs completion]

#### ✗ UNACHIEVED GOALS (BLOCKS CLOSURE)
- **GOAL_[ID]**: [reason not achieved]
  - Blocker: [root cause]
  - Decision: [defer/cancel/replan]

### QA Framework Validation
- **Business Logic Tests**: [X/X passed] ([Y%] coverage)
- **Frontend Action Coverage**: [X/X actions] ([Y%] coverage)
- **Data Integrity Tests**: [✓ Complete / ✗ Incomplete]
- **Performance Benchmarks**: [✓ Met / ✗ Not met]

### Traceability Gaps (BLOCKS CLOSURE)
- **Missing GOAL Translations**: [list USER_REC without GOAL mapping]
- **Incomplete Task Breakdown**: [list GOALs without task decomposition]
- **Unverified Tasks**: [list DONE tasks without verification reports]
- **ADR Documentation**: [list architectural changes without ADR entries]

### Business Value Delivery Evidence
- [GOAL_01]: [specific user workflow verified]
- [GOAL_02]: [specific functionality confirmed working]
- Evidence Links: [docs/verification/, docs/evidence/]
```

### 3. Run Required Test Suites

**Test Execution**:
```bash
# Reference: docs/TESTING_STANDARDS.md
# Full backend test suite
pytest tests/backend/ --cov=src --cov-report=html --cov-report=term

# Full frontend test suite (Playwright)
pytest --playwright tests/frontend/

# Integration tests
pytest tests/integration/ -v

# Capture output to docs/sprints/SPRINT_[N]_test_results.txt
```

**Acceptance Criteria**:
- All tests must pass (0 failures)
- Coverage must be ≥80% or match sprint target
- No skipped tests without documented justification
- Integration tests pass for completed features

### 4. Measure Sprint Goal Achievement

**Load Goal Definition**:
- Read `docs/sprints/SPRINT_[N]_PLAN.md` → Goal
- Read `docs/BUSINESS_GOALS.md` → related goal metrics

**Assess Achievement**:
- Did completed + verified tasks deliver sprint goal?
- Were success criteria from plan met?
- Collect evidence:
  - Test results
  - Verification reports
  - Deployed features (if applicable)
  - User feedback (if collected)

**Document Outcome**:
```markdown
## Sprint Goal Assessment

**Goal**: [from sprint plan]
**Status**: [✓ ACHIEVED / ⚠️ PARTIALLY / ✗ NOT ACHIEVED]

**Evidence**:
- Completed & Verified Tasks: [list]
- Test Results: docs/sprints/SPRINT_[N]_test_results.txt
- Verification Reports: [list paths]
- User Feedback: [summary or N/A]

**Metrics**:
[Goal-specific metrics from BUSINESS_GOALS.md]
- Metric 1: Target [X], Achieved [Y]
- Metric 2: Target [X], Achieved [Y]
```

### 5. Process Incomplete Work

**For Each NOT_STARTED or IN_PROGRESS Task**:
- Document reason incomplete
- Assess priority for next sprint
- Update estimate if needed
- Flag blockers

**Carryover Decision**:
```markdown
## Incomplete Work

### Carried to Next Sprint (P0)
- [Task]: [reason not completed] - [blocker if any]
  New Estimate: [adjusted if needed]

### Deferred (P1/P2)
- [Task]: [reason deferred]
  Target Sprint: [future sprint]

### Cancelled
- [Task]: [reason cancelled]
  Decision Reference: DECISIONS.md [date]
```

### 6. Update Documentation

**Decisions Log**:
- If goals or timelines changed: update `DECISIONS.md`
- If architectural patterns discovered: update `KNOWLEDGE_BANK.md`

**Roadmap Impact**:
- If sprint affects release timeline: update `ROADMAP.md`
- If goal status changed: update `docs/BUSINESS_GOALS.md`
- Document sprint outcome impact on releases

### 7. Collect User Feedback Summary

**Read**:
- `docs/STATUS.md` → User Feedback section
- Any feedback collected during sprint

**Summarize**:
```markdown
## User Feedback Received

**Sources**: [list sources]
**Summary**: [key insights]
**Action Items**: [prioritized follow-ups]

Impact on Backlog:
- [New feature request]: Added to backlog as [priority]
- [Bug report]: Created task [reference]
```

### 8. Create Sprint Report

Generate: `docs/sprints/SPRINT_[N]_REPORT.md`

```markdown
# Sprint [N] Completion Report

**Sprint Duration**: [start date] - [end date]
**Sprint Goal**: [from plan]
**Related Goals**: [GOAL_IDs from BUSINESS_GOALS.md]

## Executive Summary
[2-3 sentences on outcome and key achievements]

## Goal Achievement
**Status**: [✓ ACHIEVED / ⚠️ PARTIAL / ✗ NOT ACHIEVED]
[Details from step 4]

## Work Completed

### Verified Tasks (DONE)
- [Task 1]: [brief description]
  - Verification: docs/verification/[id]_verification_report.md
  - Evidence: docs/evidence/[feature]/PHASE_[N]_EVIDENCE.md

### Tasks Moved to Done Without Verification (Issues Found)
- [Task X]: Verification failed - moved back to IN_PROGRESS
  - Issue: [description]
  - Verification Report: docs/verification/[id]_verification_report.md

## Work Incomplete
[Details from step 5]

## Test Results
**Test Suite Execution**: [timestamp]
**Results**: [pass/fail counts]
**Coverage**: [percentage]
**Details**: docs/sprints/SPRINT_[N]_test_results.txt

## User Feedback
[Summary from step 7]

## Decisions Made
[References to DECISIONS.md entries during sprint]

## Lessons Learned
**What Went Well**:
- [Item 1]

**What Needs Improvement**:
- [Item 1]

**Action Items for Next Sprint**:
- [ ] Action 1

## Updated MVP Capabilities
[List sections of docs/MVP.md affected by this sprint]

## References
- Sprint Plan: docs/sprints/SPRINT_[N]_PLAN.md
- Test Results: docs/sprints/SPRINT_[N]_test_results.txt
- Verification Reports: docs/verification/[list]
- Evidence: docs/evidence/[list]
```

### 9. Update Sprint Backlog

**Move Completed Items**:
```markdown
## DONE
- **[Task]**: [description]
  - Status: DONE
  - Verification: docs/verification/[id]_verification_report.md (✓ VERIFIED)
  - Evidence: docs/evidence/[feature]/PHASE_[N]_EVIDENCE.md
  - Completed: Sprint [N]
```

**Update Carried Items**:
- Change priority if needed
- Update estimates
- Add context from sprint learnings

### 10. Reset Active Sprint State

Update `docs/STATUS.md`:
```markdown
## ACTIVE SPRINT
**Status**: Sprint [N] Complete - Planning Sprint [N+1]
**Last Sprint Report**: docs/sprints/SPRINT_[N]_REPORT.md

## COMPLETED THIS WEEK
- **Sprint [N] Closure**: [brief summary]
  - Goal Achievement: [status]
  - Tasks Verified: [count]
  - Report: docs/sprints/SPRINT_[N]_REPORT.md

## NEXT SESSION
**Priority**: Sprint [N+1] Planning
**Preparation**:
- Review carryover items: [list]
- Assess backlog priorities
- Define next sprint goal aligned with BUSINESS_GOALS.md
- Run /start_sprint "[GOAL_ID]" when ready
```

## Output

### Files Modified
- `docs/sprints/SPRINT_[N]_REPORT.md`: **Created** with a comprehensive summary of the sprint's outcomes, including goal achievement, work completed, test results, and lessons learned.
- `docs/STATUS.md`: **Updated** to close the active sprint and set the context for the next sprint planning session.
- `SPRINT_BACKLOG.md`: **Updated** by moving completed items to a "DONE" section and carrying over incomplete items.
- `docs/sprints/SPRINT_[N]_test_results.txt`: **Created** with the raw output from the final test suite execution.
- `ROADMAP.md`, `BUSINESS_GOALS.md`: **Updated** if the sprint's outcome affects the broader project timeline or goal status.

### State Change Summary
- **Sprint [N] has been formally closed.**
- **Goal Achievement**: The sprint goal was **[✓ ACHIEVED / ⚠️ PARTIALLY ACHIEVED / ✗ NOT ACHIEVED]**.
- **Work Status**: [X] tasks were completed and verified. [Y] tasks will be carried over to the next sprint.
- **Quality Assurance**: All tests passed with [Z%] coverage, as documented in the sprint report.

### Next Steps
- Review the detailed sprint report: `docs/sprints/SPRINT_[N]_REPORT.md`.
- Begin planning for the next sprint by selecting a new goal and running `/start_sprint "[GOAL_ID]"`.

## When to Use
- At scheduled sprint end date
- When sprint goal achieved early
- Before starting new sprint
- For formal release checkpoints