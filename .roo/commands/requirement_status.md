---
description: "Check status of requirement translation and fulfillment across the project"
---

# /requirement_status - Requirement Translation & Fulfillment Status

**Purpose**: Check the status of requirement translation and fulfillment across the entire project to ensure all user requirements are properly implemented and tested.

**Usage**: /requirement_status

## Steps

### 1. Load All Requirements Sources
- Read `docs/MVP.md` for primary user requirements (USER_REC_01, USER_REC_02)
- Read `docs/goals/BUSINESS_GOALS.md` for business goal translations (GOAL_01, GOAL_02, GOAL_03)
- Read `docs/user_feedback.md` and `docs/user_feedback_1.md` for additional requirements
- Extract all user-facing functionality statements

### 2. Analyze Requirements Engineering Framework
**Traceability Analysis**:
- Check if all USER_REC have corresponding GOAL translations in BUSINESS_GOALS.md
- Validate that GOALs have clear success metrics and technical requirements
- Verify cross-goal dependencies are documented

**Framework Health Metrics**:
```python
user_requirements = count(USER_REC_in_mvp)
business_goals = count(GOAL_in_business_goals)
goals_with_metrics = count(goals_with_success_metrics)
goals_with_requirements = count(goals_with_technical_requirements)

traceability_coverage = (business_goals / user_requirements) * 100
goal_completeness = (goals_with_metrics / business_goals) * 100
requirement_detail = (goals_with_requirements / business_goals) * 100
```

### 3. Analyze Translation Status
**For Each Business Goal**:
- Check if GOAL has been broken down into specific technical requirements
- Check if technical requirements have acceptance criteria
- Check if requirements are prioritized and estimated
- Check if implementation tasks exist in `SPRINT_BACKLOG.md`

**Translation Metrics**:
```python
total_goals = count(GOAL_definitions)
goals_with_requirements = count(goals_with_technical_breakdown)
goals_with_acceptance = count(goals_with_acceptance_criteria)
goals_with_tasks = count(goals_with_sprint_backlog_tasks)

translation_coverage = (goals_with_requirements / total_goals) * 100
acceptance_coverage = (goals_with_acceptance / total_goals) * 100
task_coverage = (goals_with_tasks / total_goals) * 100
```

### 3. Analyze Implementation Status
**For Each Translated Requirement**:
- Check if implementation tasks are marked DONE
- Check if DONE tasks have verification reports
- Check if verification reports show VERIFIED status

**Implementation Metrics**:
```python
implemented_requirements = count(requirements_with_done_tasks)
verified_implementations = count(requirements_with_verified_reports)
failed_verifications = count(requirements_with_failed_reports)
```

### 4. Analyze Testing Status
**For Each Requirement**:
- Check if test scenarios were generated during planning
- Check if tests are implemented and passing
- Check frontend action coverage (100% required for UI features)

**Testing Metrics**:
```python
test_scenarios_defined = count(requirements_with_test_scenarios)
tests_implemented = count(requirements_with_implemented_tests)
tests_passing = count(requirements_with_passing_tests)
frontend_coverage_complete = count(requirements_with_100pct_ui_coverage)
```

### 5. Analyze End-to-End Fulfillment
**For Each Requirement**:
- Check if user can actually perform the required workflow
- Check if business value is delivered
- Check integration between frontend and backend

**Fulfillment Metrics**:
```python
end_to_end_verified = count(requirements_verified_end_to_end)
user_workflows_tested = count(requirements_with_user_workflow_tests)
business_value_delivered = count(requirements_delivering_business_value)
```

### 6. Generate Comprehensive Status Report

## Output

```
🔍 REQUIREMENT STATUS REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 TRANSLATION STATUS
Requirements Found: [X]
Translated to Technical Specs: [Y/Y] ([Z]%)
Broken Down to Tasks: [Y/Y] ([Z]%)

📊 IMPLEMENTATION STATUS
Tasks Implemented: [Y/Y] ([Z]%)
Verifications Complete: [Y/Y] ([Z]%)
Failed Verifications: [X] (BLOCKERS)

📊 TESTING STATUS
Test Scenarios Defined: [Y/Y] ([Z]%)
Tests Implemented: [Y/Y] ([Z]%)
Tests Passing: [Y/Y] ([Z]%)
Frontend Action Coverage: [Y/Y] ([Z]%)

📊 FULFILLMENT STATUS
End-to-End Verified: [Y/Y] ([Z]%)
User Workflows Tested: [Y/Y] ([Z]%)
Business Value Delivered: [Y/Y] ([Z]%)

🚨 CRITICAL ISSUES (BLOCKS PROGRESS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ UNTRANSLATED REQUIREMENTS
[X] requirements not translated to technical specifications:
- [Requirement 1]: docs/MVP.md § X.Y
- [Requirement 2]: docs/user_feedback.md § X.Y

❌ UNIMPLEMENTED REQUIREMENTS
[X] requirements without implemented tasks:
- [Requirement]: No tasks found in SPRINT_BACKLOG.md

❌ UNVERIFIED IMPLEMENTATIONS
[X] requirements with failed verification:
- [Requirement]: docs/verification/[id]_verification_report.md (FAILED)

❌ MISSING TESTS
[X] requirements without test coverage:
- [Requirement]: No test scenarios defined

❌ INCOMPLETE UI COVERAGE
[X] UI requirements with <100% action coverage:
- [Requirement]: Missing [X] frontend actions

❌ UNFULFILLED REQUIREMENTS
[X] requirements not delivering business value:
- [Requirement]: End-to-end verification failed

📈 OVERALL HEALTH SCORE: [X/100]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMMENDATIONS:
1. [Priority 1 action]
2. [Priority 2 action]
3. [Priority 3 action]

NEXT STEPS:
- Run /start_sprint to translate missing requirements
- Run /verify_implementation for failed verifications
- Implement missing test scenarios
- Complete frontend action coverage
```

## When to Use
- Before starting any sprint planning
- During sprint execution to check progress
- Before marking tasks as DONE
- During sprint reviews
- Before sprint closure
- When concerned about requirement fulfillment

## Integration with Other Commands
- `/start_sprint`: Use this to check translation status before planning
- `/work`: Use this to verify implementation progress
- `/verify_implementation`: Use this to check verification status
- `/end_sprint`: Use this to validate overall fulfillment before closure