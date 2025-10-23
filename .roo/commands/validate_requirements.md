---
description: "Validate complete requirement traceability and QA framework compliance"
---

# /validate_requirements - Complete Requirements & QA Validation

**Purpose**: Perform comprehensive validation of requirement traceability (USER_REC → GOAL → TASKS → VERIFICATION) and QA framework compliance before sprint operations.

**Usage**: /validate_requirements

## Steps

### 1. Load Requirements Framework
- Read `docs/MVP.md` → USER_REC_01, USER_REC_02
- Read `docs/goals/BUSINESS_GOALS.md` → GOAL_01, GOAL_02, GOAL_03
- Read `docs/DECISIONS.md` → ADR framework compliance
- Read `SPRINT_BACKLOG.md` → current task status

### 2. Validate Requirements Engineering Framework

**Traceability Validation**:
```python
# Check USER_REC → GOAL mapping
for user_rec in ['USER_REC_01', 'USER_REC_02']:
    if not business_goals.has_goal_for(user_rec):
        BLOCK: f"Missing BUSINESS_GOAL for {user_rec}"

# Check GOAL completeness
for goal in business_goals:
    if not goal.has_success_metrics:
        BLOCK: f"GOAL_{goal.id} missing success metrics"
    if not goal.has_technical_requirements:
        BLOCK: f"GOAL_{goal.id} missing technical requirements"
```

**Framework Health Report**:
```markdown
## Requirements Framework Status

### Traceability Coverage
- USER_REC → GOAL: [X/X complete] ([Y%])
- GOAL Completeness: [X/X have metrics] ([Y%])
- GOAL Requirements: [X/X detailed] ([Y%])

### Missing Elements
- Unmapped USER_REC: [list]
- Incomplete GOALs: [list with reasons]
- Missing Dependencies: [cross-goal dependencies not documented]
```

### 3. Validate QA Framework Readiness

**Test Structure Validation**:
```python
# Check test directory structure exists
test_dirs = [
    'tests/business/',      # Business logic tests
    'tests/frontend/actions/',  # Frontend action coverage
    'tests/critical/data_integrity/',  # Data integrity tests
    'tests/critical/performance/'  # Performance tests
]

for test_dir in test_dirs:
    if not os.path.exists(test_dir):
        BLOCK: f"Missing test directory: {test_dir}"

# Check test framework configuration
if not os.path.exists('pytest.ini'):
    BLOCK: "Missing pytest.ini configuration"
```

**QA Framework Report**:
```markdown
## QA Framework Status

### Test Structure
- Business Logic Tests: [✓ Exists / ✗ Missing]
- Frontend Action Tests: [✓ Exists / ✗ Missing]
- Data Integrity Tests: [✓ Exists / ✗ Missing]
- Performance Tests: [✓ Exists / ✗ Missing]

### Configuration
- pytest.ini: [✓ Configured / ✗ Missing]
- Coverage Requirements: [✓ Set / ✗ Missing]
- CI/CD Integration: [✓ Ready / ✗ Missing]

### Coverage Targets (ADR-003)
- Backend: 85% minimum
- Critical Frontend: 100% required
- Business Logic: 100% required
- Data Integrity: 100% required
```

### 4. Validate Sprint Readiness

**Task Mapping Validation**:
```python
# Check TASKS → GOAL traceability
for task in sprint_backlog.tasks:
    if not task.has_goal_reference:
        BLOCK: f"Task {task.id} not mapped to BUSINESS_GOAL"

# Check VERIFICATION readiness
for task in sprint_backlog.done_tasks:
    if not task.has_verification_report:
        BLOCK: f"DONE task {task.id} missing verification report"
```

**Sprint Readiness Report**:
```markdown
## Sprint Readiness Status

### Task Mapping
- Tasks with GOAL reference: [X/X] ([Y%])
- DONE tasks verified: [X/X] ([Y%])

### Blockers Found
- Unmapped tasks: [list]
- Unverified DONE tasks: [list]
- Missing verification reports: [list]
```

### 5. Generate Comprehensive Validation Report

## Output

```
🔍 REQUIREMENTS & QA VALIDATION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 REQUIREMENTS FRAMEWORK
USER_REC → GOAL → TASKS → VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Traceability Coverage: [X/X] ([Y%])
- USER_REC_01 → GOAL_01: [✓ Complete / ✗ Incomplete]
- USER_REC_02 → GOAL_02: [✓ Complete / ✗ Incomplete]

✅ GOAL Completeness: [X/X] ([Y%])
- Success Metrics: [X/X defined]
- Technical Requirements: [X/X detailed]
- Dependencies: [X/X documented]

📊 QA FRAMEWORK COMPLIANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Test Structure: [X/X directories] ([Y%])
- Business Logic: [✓ Ready / ✗ Missing]
- Frontend Actions: [✓ Ready / ✗ Missing]
- Data Integrity: [✓ Ready / ✗ Missing]
- Performance: [✓ Ready / ✗ Missing]

✅ Configuration: [X/X files] ([Y%])
- pytest.ini: [✓ Configured]
- Coverage settings: [✓ Set]

🎯 SPRINT READINESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Task Mapping: [X/X tasks] ([Y%])
✅ Verification Status: [X/X DONE tasks] ([Y%])

🎯 FRAMEWORK VALIDATION RESULTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ REQUIREMENTS FRAMEWORK STATUS
- [Issue 1]: [description] - [impact]
- [Issue 2]: [description] - [impact]

✅ QA FRAMEWORK STATUS
- [Issue 1]: [description] - [impact]
- [Issue 2]: [description] - [impact]

✅ SPRINT READINESS STATUS
- [Issue 1]: [description] - [impact]
- [Issue 2]: [description] - [impact]

📈 OVERALL READINESS SCORE: [X/100]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMMENDATIONS:
1. [Priority 1 fix] - Why: [business impact]
2. [Priority 2 fix] - Why: [business impact]
3. [Priority 3 fix] - Why: [business impact]

REQUIRED ACTIONS BEFORE SPRINT OPERATIONS:
- [Actions will be listed here if any issues are found]

Next: /start_sprint "[GOAL_ID]" (framework ready for sprint operations)
```

## When to Use
- Before `/start_sprint` - validate framework completeness
- Before `/work` - ensure QA framework ready
- Before `/end_sprint` - confirm all validations passed
- When concerned about requirement traceability
- After framework changes to verify integrity

## Integration with Other Commands
- `/start_sprint`: Use this first to validate before planning
- `/work`: Use this to check QA readiness before implementation
- `/requirement_status`: Use this for detailed status after validation
- `/end_sprint`: Use this to ensure closure requirements met