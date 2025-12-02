# Command Reference - Complete Set

## Overview

This document contains the complete command set for autonomous project management with mandatory verification and code-documentation synchronization.

## Command Files

1. **verify_implementation.md** - Verify task completion in code
2. **feature_integrate.md** - Integrate features with conflict detection
3. **decide.md** - Resolve integration conflicts
4. **feature_integrate_resume.md** - Resume after conflict resolution
5. **work.md** - Context-aware task execution
6. **end_sprint.md** - Sprint closure with verification
7. **sync_docs.md** - Documentation-code reconciliation

## Command Flow Diagram

```
START
  │
  ├─> /sync_docs
  │   └─> Validates current state
  │       └─> Flags verification gaps
  │
  ├─> /feature_integrate "[specs]"
  │   ├─> Calls /sync_docs (pre-flight)
  │   ├─> Analyzes feature
  │   ├─> Detects conflicts
  │   │   ├─> [No conflicts] → Create design doc → Update all docs
  │   │   └─> [Conflicts found] → PAUSE
  │   │       └─> Generate conflict report
  │   │           └─> User runs /decide for each conflict
  │   │               └─> /decide "CONFLICT_ID" "option_X"
  │   │                   └─> Documents decision
  │   │                   └─> Creates tasks if needed
  │   │                   └─> [All resolved]
  │   │                       └─> /feature_integrate_resume
  │   │                           └─> Complete integration
  │
  ├─> /work
  │   ├─> Load context (full paths)
  │   ├─> Determine phase (Discovery/Validation/Production)
  │   ├─> Implement task
  │   ├─> Write tests (mandatory in Validation/Production)
  │   ├─> Capture evidence
  │   └─> [Task appears complete]
  │       └─> /verify_implementation "[task]"
  │           ├─> Check code exists
  │           ├─> Run tests
  │           ├─> Validate evidence
  │           ├─> Check documentation
  │           └─> Generate verification report
  │               ├─> [VERIFIED] → Mark DONE
  │               ├─> [PARTIAL] → Fix issues
  │               └─> [FAILED] → Back to IN_PROGRESS
  │
  └─> /end_sprint
      ├─> Verify ALL DONE tasks with /verify_implementation
      ├─> Run full test suites
      ├─> Measure goal achievement
      ├─> Process incomplete work
      ├─> Generate sprint report
      └─> Plan next sprint
```

## Core Principles

### 1. Mandatory Verification
- **No task is DONE without verification**
- `/verify_implementation` must be run before marking any task complete
- Verification checks: code existence, tests passing, evidence captured, documentation updated

### 2. Conflict Detection
- `/feature_integrate` detects conflicts before creating design documents
- Conflicts must be resolved via `/decide` before proceeding
- All decisions documented in `DECISIONS.md`

### 3. Full Path Specification
- All commands use complete paths: `docs/STATUS.md`, not `STATUS.md`
- All references to design docs use full paths: `docs/features/[feature].md`
- All evidence stored in structured folders: `docs/evidence/[feature]/`

### 4. Evidence-Based Completion
- Every completed task must have evidence in `docs/evidence/[feature]/PHASE_[N]_EVIDENCE.md`
- Evidence includes: test results, coverage reports, API tests, screenshots
- Verification reports stored in `docs/verification/[task_id]_verification_report.md`

### 5. Code-Documentation Synchronization
- `/sync_docs` reconciles code state with documentation
- Flags tasks marked DONE without code evidence
- Detects documentation drift (features documented but not implemented)

## Command Relationships

### Pre-Flight Commands
- `/sync_docs` - Always run before major operations

### Feature Integration Workflow
1. `/feature_integrate` - Start feature integration
2. `/decide` (multiple times) - Resolve conflicts if detected
3. `/feature_integrate_resume` - Complete integration after conflicts resolved

### Development Workflow
1. `/work` - Implement task
2. `/verify_implementation` - Verify completion before marking DONE
3. Repeat for next task

### Sprint Management
1. `/start_sprint` (existing) - Begin sprint
2. `/work` - Execute tasks
3. `/end_sprint` - Close sprint with mandatory verification

## File Structure Created by Commands

```
project/
├── docs/
│   ├── MVP.md
│   ├── STATUS.md
│   ├── goals/
│   │   └── BUSINESS_GOALS.md
│   ├── sprints/
│   │   ├── SPRINT_[N]_PLAN.md
│   │   ├── SPRINT_[N]_REPORT.md
│   │   └── SPRINT_[N]_test_results.txt
│   ├── features/
│   │   └── [feature_name].md           # Created by /feature_integrate
│   ├── evidence/
│   │   └── [feature_name]/
│   │       ├── PHASE_1_EVIDENCE.md
│   │       ├── PHASE_2_EVIDENCE.md
│   │       ├── INTEGRATION_TEST_RESULTS.md
│   │       └── PERFORMANCE_BENCHMARKS.md
│   ├── verification/
│   │   └── [task_id]_verification_report.md  # Created by /verify_implementation
│   ├── conflicts/
│   │   └── [feature_name]_conflicts.md       # Created by /feature_integrate
│   └── sync/
│       ├── [timestamp]_sync_report.md        # Created by /sync_docs
│       └── [timestamp]_test_results.txt
├── SPRINT_BACKLOG.md
├── ROADMAP.md
├── DECISIONS.md
└── KNOWLEDGE_BANK.md
```

## Usage Examples

### Example 1: Integrate New Feature (No Conflicts)

```bash
# Step 1: Integrate feature
/feature_integrate "docs/specs/PAYMENT_GATEWAY.md"

# Output: No conflicts detected, design created
# Files created:
# - docs/features/payment_gateway.md
# - Updated: docs/MVP.md, ROADMAP.md, SPRINT_BACKLOG.md

# Step 2: Start implementation
/work

# Step 3: When task complete, verify
/verify_implementation "Payment Gateway - API Integration"

# Output: VERIFIED
# Files created:
# - docs/verification/payment_gateway_api_verification_report.md
# - Updated: SPRINT_BACKLOG.md (task marked DONE)
```

### Example 2: Integrate Feature with Conflicts

```bash
# Step 1: Integrate feature
/feature_integrate "docs/specs/REAL_TIME_ANALYTICS.md"

# Output: 2 conflicts detected
# - CONFLICT_ARCH_001: Requires event streaming infrastructure
# - CONFLICT_SPRINT_001: Exceeds sprint capacity
# Files created:
# - docs/conflicts/real_time_analytics_conflicts.md

# Step 2: Resolve conflicts
/decide "CONFLICT_ARCH_001" "option_a" "Build Kafka infrastructure first"
/decide "CONFLICT_SPRINT_001" "option_b" "Split across 2 sprints"

# Step 3: Resume integration
/feature_integrate_resume "real_time_analytics"

# Output: Integration complete with resolutions applied
# Files created:
# - docs/features/real_time_analytics.md (with conflict resolutions)
# - Updated: all documentation + prerequisite tasks created
```

### Example 3: Sprint Closure with Verification

```bash
# End sprint
/end_sprint

# Process:
# 1. Verifies all DONE tasks (runs /verify_implementation for each)
# 2. Runs full test suite
# 3. Measures goal achievement
# 4. Generates sprint report

# Output:
# - Tasks verified: 8/10 (2 failed verification, moved back to IN_PROGRESS)
# - Sprint goal: ACHIEVED
# - Files created:
#   - docs/sprints/SPRINT_8_REPORT.md
#   - docs/sprints/SPRINT_8_test_results.txt
```

### Example 4: Daily Sync Check

```bash
# Check documentation sync
/sync_docs

# Output:
# Status: ⚠️ WARNINGS
# - 3 tasks marked DONE without verification reports
# - 1 feature documented but not implemented
# - 2 files modified without backlog tasks
# Files created:
# - docs/sync/2025-09-29_sync_report.md
# - docs/sync/2025-09-29_test_results.txt

# Actions required:
# 1. Run /verify_implementation for unverified tasks
# 2. Update docs/MVP.md or implement missing feature
# 3. Document untracked changes in SPRINT_BACKLOG.md
```

## Verification Checklist

Before marking any task as DONE:

- [ ] Code exists at expected paths (backend: `src/`, frontend: `frontend/src/`)
- [ ] All tests pass (`pytest tests/` and `npm test`)
- [ ] Test coverage meets target (typically >80%)
- [ ] Evidence captured in `docs/evidence/[feature]/PHASE_[N]_EVIDENCE.md`
- [ ] API endpoints tested (if applicable)
- [ ] Documentation updated (`docs/MVP.md`, `KNOWLEDGE_BANK.md`)
- [ ] `/verify_implementation` run and status is VERIFIED
- [ ] Verification report exists: `docs/verification/[task_id]_verification_report.md`

## Common Pitfalls to Avoid

### 1. Marking Tasks DONE Without Verification
**Problem**: Task status changed to DONE without running `/verify_implementation`
**Solution**: Always run `/verify_implementation` before changing status
**Detection**: `/sync_docs` will flag these as CRITICAL issues

### 2. Implementing Without Design Document
**Problem**: Starting implementation before `/feature_integrate` completes
**Solution**: Always complete feature integration workflow first
**Detection**: `/work` should check for design document reference

### 3. Ignoring Conflicts
**Problem**: Proceeding with feature despite conflicts
**Solution**: Resolve all conflicts via `/decide` before resuming
**Detection**: `/feature_integrate` blocks until conflicts resolved

### 4. Missing Evidence
**Problem**: Task marked DONE but no evidence files
**Solution**: Capture evidence during implementation in `docs/evidence/`
**Detection**: `/verify_implementation` will mark as PARTIAL or FAILED

### 5. Documentation Drift
**Problem**: Documentation says feature is working but code doesn't exist
**Solution**: Regular `/sync_docs` runs to catch drift early
**Detection**: `/sync_docs` generates discrepancy report

## Integration with Existing Commands

These new commands enhance (not replace) existing commands:

- `/start_sprint` - Works with `/feature_integrate` to plan sprints
- `/replan` - Can be called after `/decide` if conflicts require rescoping
- `/set_goals_feature` - Called by `/feature_integrate` for new goals
- `/review_roadmap` - Called by `/feature_integrate` for major impact
- `/emergency` - Escalation path if conflicts unresolvable
- `/pivot` - Discovery mode alternative in `/work`

## Quick Reference

| Command | When to Use | Output |
|---------|-------------|--------|
| `/sync_docs` | Daily, before major operations | Sync report, verification gaps |
| `/feature_integrate` | Before implementing features | Design doc, updated docs, conflict report |
| `/decide` | After conflicts detected | Decision recorded, tasks created |
| `/feature_integrate_resume` | After all conflicts resolved | Completed integration |
| `/work` | During task implementation | Progress updates, evidence |
| `/verify_implementation` | Before marking task DONE | Verification report (VERIFIED/PARTIAL/FAILED) |
| `/end_sprint` | Sprint completion | Sprint report, verified tasks |

## Success Criteria

A task is truly complete when:
1. ✅ Code exists and matches design specification
2. ✅ All tests pass with adequate coverage
3. ✅ Evidence documented with timestamps
4. ✅ Documentation updated
5. ✅ `/verify_implementation` status is VERIFIED
6. ✅ Verification report exists and shows no issues

A sprint is successfully closed when:
1. ✅ All DONE tasks have verification reports with VERIFIED status
2. ✅ Full test suite passes
3. ✅ Sprint goal achieved or documented why not
4. ✅ Sprint report generated
5. ✅ Incomplete work documented and prioritized

A feature is properly integrated when:
1. ✅ Conflicts detected and resolved via `/decide`
2. ✅ Design document created at `docs/features/[feature].md`
3. ✅ All documentation updated (MVP, Roadmap, Backlog, Goals)
4. ✅ Evidence folder structure created
5. ✅ Tasks created in backlog with proper priorities

---

## Installation

Copy all command `.md` files to your project documentation:

```bash
mkdir -p docs/commands/
cp verify_implementation.md docs/commands/
cp feature_integrate.md docs/commands/
cp decide.md docs/commands/
cp feature_integrate_resume.md docs/commands/
cp work.md docs/commands/
cp end_sprint.md docs/commands/
cp sync_docs.md docs/commands/
```

## Support

For issues or questions about command usage:
1. Review this README
2. Check relevant command `.md` file for detailed steps
3. Run `/sync_docs` to identify current state issues
4. Review recent `DECISIONS.md` entries for context