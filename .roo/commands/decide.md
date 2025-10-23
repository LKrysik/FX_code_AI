---
description: "Resolve feature integration conflicts detected by /feature_integrate"
---

# /decide - Resolve Feature Integration Conflicts

**Purpose**: Make binding decisions on feature integration conflicts detected by /feature_integrate

**Usage**: /decide "[conflict_id]" "[option]" "[justification_optional]"

## Steps

1. **Validate Decision**
   - Verify conflict_id exists in `docs/conflicts/[feature_name]_conflicts.md`
   - Verify option is valid (option_a, option_b, option_c, etc.)
   - Load conflict details

2. **Execute Decision Based on Option**

   **Option A (Refactor/Extend/Defer)**:
   - Update `docs/ROADMAP.md`: dependencies, timeline, release notes
   - Create prerequisite tasks in `docs/SPRINT_BACKLOG.md` with P0 priority
   - Update feature design doc: add Prerequisites section, document dependency

   **Option B (Workaround/Split/Mock)**:
   - Create workaround tasks in `docs/SPRINT_BACKLOG.md` with P0 priority
   - Add technical debt entry with origin, impact, target sprint
   - Update feature design doc: add Workarounds section, document debt

   **Option C (Descope/Resequence)**:
   - Modify `docs/features/[feature_name].md`: reduce scope, document deferred functionality
   - Update `docs/ROADMAP.md`: move to different release if resequencing
   - Adjust estimates in design doc and sprint backlog

   **Option D (Pause/Reprioritize)**:
   - Update `docs/sprints/SPRINT_[N]_PLAN.md`: move paused tasks
   - Update `docs/STATUS.md` WORKING ON: document reprioritization
   - Add stakeholder note to NEXT SESSION

3. **Document Decision**
   - Add to `docs/DECISIONS.md`:
     - Conflict ID and description
     - Option selected with rationale
     - Impact on sprint/roadmap/goals/architecture
     - Follow-up actions
     - Review date

4. **Update Conflict Report**
   - Mark conflict as resolved in `docs/conflicts/[feature_name]_conflicts.md`
   - Add resolution date, option, rationale, implementation references

5. **Check All Conflicts Resolved**
   - Count resolved vs total
   - If all resolved: mark "Ready to resume integration" with /feature_integrate_resume command
   - If remaining: list pending conflicts

6. **Output**
   - Decision summary
   - Actions created
   - Updated files
   - Next steps (resume or continue deciding)

## Output
- Updated `docs/DECISIONS.md`
- Updated `docs/SPRINT_BACKLOG.md` (tasks added)
- Updated conflict report
- Clear next action

## When to Use
- After /feature_integrate detects conflicts
- Before resuming feature integration
- When explicit decision needed on implementation approach