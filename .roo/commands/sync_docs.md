---
description: "Align documentation with current code state and flag verification gaps"
---

# /sync_docs - Align Documentation with Code Reality

**Purpose**: Audit repository, reconcile code state with documentation, flag unverified tasks, update all planning artifacts.

**Usage**: `/sync_docs`

## Phase-Aware Inputs

### 1. Determine Phase
- Read `docs/STATUS.md` → ACTIVE SPRINT
- Read `docs/ROADMAP.md` → metrics
- Set validation strictness based on phase

### 2. Collect Baseline Data
- Git: `git status`, `git log --oneline -20`, open branches
- Tests: Run required suite for current phase
- Runtime: Check logs in deployment environment (if Production)

### 3. Load Documentation (Full Paths)
- Primary: `docs/MVP.md`
- Goals: `docs/goals/BUSINESS_GOALS.md`
- Sprint: `docs/sprints/SPRINT_[N]_PLAN.md`, `docs/sprints/SPRINT_[N]_REPORT.md`
- Status: `docs/STATUS.md`
- Backlog: `SPRINT_BACKLOG.md`
- Decisions: `DECISIONS.md`
- Patterns: `KNOWLEDGE_BANK.md`
- Roadmap: `ROADMAP.md`

## Core Workflow

### 1. Inventory Current Work

**Code Changes**:
```bash
# Get modified files
git diff --name-status main..HEAD

# Get recent commits
git log main..HEAD --oneline

# Find TODO/FIXME
grep -r "TODO\|FIXME" src/ frontend/src/ --include="*.py" --include="*.ts" --include="*.tsx"
```

**Map to Backlog**:
- For each changed file, find related task in `SPRINT_BACKLOG.md`
- Document untracked changes (files changed without backlog task)

### 2. Verify Task Statuses

**For Each Task in SPRINT_BACKLOG.md Marked DONE**:

```python
Check verification:
- Does docs/verification/[task]_verification_report.md exist?
- If YES: Is status VERIFIED?
- If NO: Run /verify_implementation "[task]"

Flag issues:
- DONE without verification report: CRITICAL
- DONE with FAILED verification: CRITICAL
- DONE with PARTIAL verification: WARNING
```

**Generate Verification Gap Report**:
```markdown
## Verification Gaps Found

### CRITICAL: Tasks Marked DONE Without Verification
- [Task 1]: No verification report found
  Action: Run /verify_implementation "[task_1]"

### CRITICAL: Tasks with Failed Verification
- [Task 2]: Verification FAILED
  Report: docs/verification/[task_2]_verification_report.md
  Action: Address issues and re-verify

### WARNING: Tasks with Partial Verification
- [Task 3]: Verification PARTIAL
  Report: docs/verification/[task_3]_verification_report.md
  Action: Complete missing evidence
```

### 3. Validate Quality Gates

**Run Test Suites**:
```bash
# Backend
pytest tests/ -v --cov=src --cov-report=term-missing

# Frontend
cd frontend && npm test -- --coverage --watchAll=false

# Integration
pytest tests/integration/ -v
```

**Capture Results**:
- Save output to `docs/sync/[timestamp]_test_results.txt`
- Extract: pass/fail counts, coverage percentage, failed test names

**Document in docs/STATUS.md**:
```markdown
## Quality Metrics
**Last Validation**: [timestamp]
**Backend Tests**: [X passed / Y total] - Coverage: [Z%]
**Frontend Tests**: [X passed / Y total] - Coverage: [Z%]
**Integration Tests**: [X passed / Y total]
**Results**: docs/sync/[timestamp]_test_results.txt

**Issues Found**: [count]
- [Failed test name]: [brief description]
```

### 4. Reconcile Documentation with Code

**Check docs/MVP.md**:
- For each feature listed as "working":
  - Verify code exists
  - Verify tests pass
  - If not: flag as documentation drift

**Check SPRINT_BACKLOG.md**:
- Tasks marked DONE: verify code exists
- Tasks marked IN_PROGRESS: verify code partially exists
- Tasks marked NOT_STARTED: verify no code exists

**Check docs/goals/BUSINESS_GOALS.md**:
- Goals marked COMPLETED: verify all related tasks DONE and verified
- Goals IN_PROGRESS: verify task progress aligns

**Generate Discrepancy Report**:
```markdown
## Documentation vs Code Discrepancies

### Features Listed as Working But Missing in Code
- Feature X (docs/MVP.md § 3.2):
  Expected: src/[path]/[file].py
  Found: No
  Action: Update docs/MVP.md or implement feature

### Tasks Marked DONE Without Code Evidence
- Task Y (SPRINT_BACKLOG.md):
  Expected: src/[path]/[file].py
  Found: No
  Action: Verify task actually complete or revert status

### Code Without Documentation
- File: src/[path]/new_feature.py
  Not Documented In: docs/MVP.md, SPRINT_BACKLOG.md
  Action: Document feature or remove code if experimental
```

### 5. Check File Structure Integrity

**Verify Required Directories Exist**:
```bash
docs/
docs/goals/
docs/sprints/
docs/features/
docs/evidence/
docs/verification/
docs/conflicts/
docs/sync/
```

**Verify Required Files Exist**:
```bash
docs/MVP.md
docs/STATUS.md
docs/goals/BUSINESS_GOALS.md
SPRINT_BACKLOG.md
ROADMAP.md
DECISIONS.md
KNOWLEDGE_BANK.md
```

**Create Missing Structure**:
- If missing: create directories
- If missing: flag critical files in output

### 6. Update STATUS.md with Sync Results

```markdown
## LAST SYNC
**Date**: [timestamp]
**Status**: [✓ CLEAN / ⚠️ WARNINGS / ✗ ERRORS]

**Summary**:
- Verification Gaps: [count]
- Documentation Drift: [count]
- Test Failures: [count]
- Untracked Changes: [count]

**Critical Issues**:
[List CRITICAL issues from reports]

**Action Required**:
[List immediate actions needed]

**Details**: docs/sync/[timestamp]_sync_report.md
```

### 7. Generate Comprehensive Sync Report

Create `docs/sync/[timestamp]_sync_report.md`:

```markdown
# Repository Sync Report

**Date**: [timestamp]
**Phase**: [Discovery/Validation/Production]
**Branch**: [current branch]
**Last Commit**: [commit hash and message]

## Executive Summary
**Overall Status**: [✓ CLEAN / ⚠️ WARNINGS / ✗ ERRORS]
[Brief summary of findings]

## Verification Gaps
[Content from step 2]

## Test Results
[Content from step 3]

## Documentation Discrepancies
[Content from step 4]

## File Structure
[Content from step 5]

## Git Status
**Modified Files**: [count]
**Untracked Files**: [count]
**Open Branches**: [count]

### Recent Commits
[Last 10 commits with hash and message]

### Modified Files Not in Backlog
- src/[path]/[file].py: [last modified date]
  No related task in SPRINT_BACKLOG.md

## Code Quality Issues
**TODO Comments**: [count]
**FIXME Comments**: [count]
**Locations**: [list]

## Recommendations

### Immediate Actions (P0)
- [ ] Action 1: [description]
- [ ] Action 2: [description]

### Short-term Actions (P1)
- [ ] Action 1: [description]

### Long-term Actions (P2)
- [ ] Action 1: [description]

## Artifact Updates Required
- [ ] docs/MVP.md: [required updates]
- [ ] SPRINT_BACKLOG.md: [required updates]
- [ ] docs/STATUS.md: [required updates]
- [ ] Other: [list]
```

### 8. Auto-Fix Simple Issues (Optional)

**If Phase is Discovery or Validation**:
- Update `docs/STATUS.md` with sync results
- Create missing evidence folders
- Add TODO items to `SPRINT_BACKLOG.md` for untracked changes

**If Phase is Production**:
- Only report issues, don't auto-fix
- Require manual review and approval

## Output

```
✅ Documentation Sync Complete

Status: [✓ CLEAN / ⚠️ WARNINGS / ✗ ERRORS]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary:
- Verification Gaps: [count] ([X] CRITICAL, [Y] WARNING)
- Test Results: [X passed / Y total] - Coverage: [Z%]
- Documentation Drift: [count] items
- Untracked Changes: [count] files
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Reports Generated:
- Sync Report: docs/sync/[timestamp]_sync_report.md
- Test Results: docs/sync/[timestamp]_test_results.txt
- Updated: docs/STATUS.md

[If CLEAN]
✓ No issues found - documentation in sync with code

[If WARNINGS]
⚠️ Warnings found - review recommended
Priority Actions: [list top 3]

[If ERRORS]
✗ Critical errors found - immediate action required
CRITICAL: [list critical issues]

Next Steps:
[Based on findings]
- Run /verify_implementation for tasks without verification
- Update documentation for drifted features
- Fix failing tests
- Document untracked changes
```

## When to Use
- Before starting work sessions
- Before `/feature_integrate` (pre-flight check)
- After major changes
- During sprint reviews
- When documentation feels out of sync
- Before releases

## Integration with Other Commands
- `/feature_integrate`: Calls `/sync_docs` in pre-flight
- `/end_sprint`: Uses sync data for sprint report
- `/work`: Can call `/sync_docs` if context unclear
- `/verify_implementation`: Validates findings from `/sync_docs`