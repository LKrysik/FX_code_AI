---
mode: agent
---


# /work - Deliver Task End to End

**Purpose**: Drive a backlog item from analysis to verified completion without gaps or "false success".  
**Usage**: `/work`

## Workflow Overview
1. **Load Sprint Context**  
   - `docs/STATUS.md` -> active sprint and current task.  
   - `SPRINT_BACKLOG.md` -> task entry, acceptance criteria, traceability.  
   - `docs/sprints/SPRINT_[N]_PLAN.md` -> sprint goal and Test Matrix row for this task.  
   - `docs/MVP.md` and `docs/goals/BUSINESS_GOALS.md` -> originating USER_REC and GOAL_xx references.
2. **Confirm Scope and Traceability**  
   - Map the task to the USER_REC and GOAL_xx cited in backlog.  
   - Pull any extra constraints from `docs/features/[feature].md` if it exists.  
   - Misalignment or missing requirements? Record a blocker in `docs/STATUS.md` and stop.
3. **Implement Using Established Patterns**  
   - Follow `docs/KNOWLEDGE_BANK.md` conventions and similar code.  
   - Keep changes minimal, testable, and consistent with the sprint plan.
4. **Execute the Verification Pipeline**  
   - Run every build, test, and manual check defined for this task in the sprint Test Matrix.  
   - Collect evidence, update documentation, and run automated verification before claiming DONE.

## Detailed Steps

### 1. Load Context
- Review the documents above and note task id, definition of done, dependencies, and required evidence.

### 2. Understand Acceptance Scope
- Restate the objective with explicit USER_REC sentences and GOAL success metrics.  
- Read the Test Matrix row in the sprint plan: it lists the full suite (backend, frontend, integration, performance, manual) that must pass.  
- Fold in design docs, ADRs in `docs/DECISIONS.md`, and directives from `docs/TESTING_STANDARDS.md`.

### 3. Implement the Change
- Apply patterns from the existing codebase.  
- Add or update tests alongside code so the Test Matrix scenarios are covered.  
- Log noteworthy decisions. If architecture changes, update the relevant design doc or add a note in `docs/DECISIONS.md`.

### 4. Run the Verification Pipeline

#### 4.1 Execute Planned Tests
- For each scenario in the Test Matrix:
  1. Note the scenario id and linked USER_REC/GOAL.  
  2. Run the stated command (for example `npm run build`, `pytest tests/backend --cov=src`, Playwright suites, performance checks).  
  3. Save the full output.  
- Carry out manual or exploratory testing when the plan calls for it. Capture screenshots or screen recordings as evidence.  
- Any failure means the pipeline stops: fix the issue and rerun the entire matrix. Partial success never qualifies the task for DONE.

#### 4.2 Capture the Evidence Package
Store artefacts under `docs/evidence/[task_id]/`:
- `git_changes.txt` with `git diff --stat`.  
- `build_output.txt`, `test_results_[suite].txt`, performance logs, and similar outputs.  
- Manual assets such as screenshots, console logs, or recordings.  
- `requirement_mapping.md` summarising requirement sentences, code locations, and tests.  
- `completion_checklist.md` ticking every scenario and pointing to its evidence file.

#### 4.3 Automated Verification Gate
- Run `/verify_implementation "[task_description]"` or the scripted equivalent.  
- Resolve every issue until the result is VERIFIED.  
- If the sprint plan or backlog marks the task for enhanced review, complete those checks (for example peer review or audit checklist) before moving on.

### 5. Update Repository Documentation
- `SPRINT_BACKLOG.md`: update status, verification reference, remaining notes.  
- `docs/STATUS.md`: log progress in ACTIVE SPRINT and NEXT SESSION, including test outcomes and evidence paths.  
- `docs/sprints/SPRINT_[N]_PLAN.md`: add lessons, risks, or coverage updates discovered during work.  
- Refresh any affected design docs, ADRs, or knowledge base entries so documentation stays consistent.

### 6. Prepare the Completion Report
Report back with:
- **Task Status**: DONE / IN_PROGRESS / BLOCKED.  
- **Verification Results**:  
  - `Pass/Fail Git Changes - [files touched summary]`  
  - `Pass/Fail Build - [command and outcome]`  
  - `Pass/Fail Tests - [scenario id -> result]`  
  - `Pass/Fail Requirements - [USER_REC and GOAL confirmed]`  
  - `Pass/Fail Manual or Exploratory - [notes if applicable]`
- **Implementation Summary**: modules touched and user-impact.  
- **Evidence**: highlight files inside `docs/evidence/[task_id]/`.  
- **Documentation Updates**: list updated files such as `docs/STATUS.md`, the sprint plan, or design docs.  
- **Next Steps**: follow-up tasks, open questions, or blockers.

## Anti-False-Success Safeguards
- No completion without executing the full Test Matrix and saving artefacts.  
- Verification must return VERIFIED before marking DONE.  
- Evidence is location-stamped and cross-checked with git history.  
- Manual testing is mandatory whenever the plan specifies it.  
- Deviations from scope require written agreement in the sprint documentation.

## When to Use
- At the start of any backlog task implementation.  
- When resuming work after clearing a blocker.  
- Before handing off or closing work that affects the sprint goal.

