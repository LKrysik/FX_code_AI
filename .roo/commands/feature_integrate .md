---
description: "Analyze feature documentation, detect conflicts, create comprehensive technical design, and propagate changes across all project artifacts. feature_integrate [path_to_feature_spec_1] [path_to_feature_spec_2] ... [goal_id_optional].
---

# /feature_integrate - Integrate Feature Specifications into Architecture

**Purpose**: Analyze feature documentation, detect conflicts, create comprehensive technical design, and propagate changes across all project artifacts.

**Usage**: /feature_integrate "[path_to_feature_spec_1]" "[path_to_feature_spec_2]" ... "[goal_id_optional]" [--resume]

## Steps

### Resume Mode (--resume flag)

If --resume flag provided:

1. **Validate Preconditions**
   - Verify `docs/features/[feature_name].md` does NOT exist yet
   - Load `docs/conflicts/[feature_name]_conflicts.md`
   - Verify ALL conflicts marked as resolved
   - If unresolved: abort with pending conflict list

2. **Load Conflict Decisions**
   - Read decision entries from `docs/DECISIONS.md` for this feature
   - Extract: selected options, rationales, implementation constraints, prerequisites

3. **Continue Integration**
   - Jump to Step 6 (Design Document Creation) below
   - Include "Conflict Resolutions Applied" section in design document
   - Reference decision log entries
   - Adjust implementation plan based on conflict resolutions

### Normal Mode

1. **Pre-Flight Check**
   - Run /sync_docs to ensure current state
   - Load `docs/STATUS.md`, `docs/SPRINT_BACKLOG.md`, `docs/ROADMAP.md`, `docs/sprints/SPRINT_[N]_PLAN.md`, `docs/KNOWLEDGE_BANK.md`, `docs/DECISIONS.md`

2. **Feature Analysis**
   - Read all feature specification documents
   - Extract: requirements, dependencies, integration points, API changes, testing needs, effort estimates
   - Step-by-Step Reasoning when creating artifacts 

3. **Conflict Detection**
   - Check Architecture: Container/DI conflicts, circular dependencies, async/await violations, API contract breaks, schema conflicts
   - Check Sprint: Capacity exceeded, task conflicts, resource allocation issues, invalidates completed work
   - Check Roadmap: Timeline conflicts, missing prerequisites, goal scope changes
   - Check Technical Debt: Debt increase, deprecated patterns, prevents refactoring
   - Check Testing: Missing infrastructure, broken assumptions, lacking capabilities
   - Step-by-Step Reasoning why this conflict is important 

4. **Generate Conflict Report** (if conflicts detected)
   - Create `docs/conflicts/[feature_name]_conflicts.md`
   - For each conflict: severity, description, impact, options with effort/risk/benefit
   - Provide /decide commands for each conflict
   - PAUSE integration - output conflict summary
   - Step-by-Step Reasoning when creating conflict. 

5. **If No Conflicts**: Proceed to Design Document Creation

6. **Design Document Creation**
   - Create `docs/features/[feature_name].md` with:
     - Executive Summary
     - Functional Requirements (capabilities, user stories)
     - Technical Architecture (components, data model, API changes, integration points)
     - Implementation Plan (phases with tasks, criteria, estimates, dependencies, risks)
     - Code Changes (new/modified/removed files)
     - Testing Strategy (unit/integration/performance/security)
     - Migration & Deployment
     - Conflict Resolutions Applied (if any)
     - Risks & Mitigation
     - Success Metrics
     - Documentation Updates
     - Dependencies & Blockers
     - References
      Step-by-Step Reasoning during desing solution

7. **Update Business Goals**
   - If new capability: call /set_goals_feature "docs/features/[feature_name].md"
   - If extends existing: update goal with design doc reference
   - Step-by-Step Reasoning when updating goals

8. **Update `docs/MVP.md`**
   - Add feature section with functionality, implementation, UX, integration points, metrics
   - Update "Current Implementation Snapshot"
   - Update "Critical Problems" if addresses issues
   - Step-by-Step Reasoning when updating  MVP

9. **Update Roadmap**
   - Call /review_roadmap if major impact
   - Otherwise update `docs/ROADMAP.md`: add to release, update risks, capability checklist, metrics
   - Step-by-Step Reasoning when updating Roadmap

10. **Update Sprint Backlog**
    - Extract Phase 1 tasks from design doc
    - Add to `docs/SPRINT_BACKLOG.md` with priority, user story, goal, criteria, tests, estimates, status, design reference
    - Add prerequisite tasks if conflicts resolved
    - Step-by-Step Reasoning when updating Backlog

11. **Update Current Sprint Plan**
    - If active sprint and feature fits: add to `docs/sprints/SPRINT_[N]_PLAN.md`
    - If doesn't fit: mark for next sprint
    - Recommend /replan if significant changes
    - Step-by-Step Reasoning Sprint Plan

12. **Update `docs/STATUS.md`**
    - Document completion in COMPLETED THIS WEEK
    - Add to TECHNICAL DECISIONS
    - Set NEXT SESSION priority
    - Step-by-Step Reasoning when updating Status

13. **Create Evidence Folder**
    - Create `docs/evidence/[feature_name]/`
    - Add placeholder in folder: `PHASE_1_EVIDENCE.md`, `INTEGRATION_TEST_RESULTS.md`, `PERFORMANCE_BENCHMARKS.md`

14. **Final Output**
    - Summary of integration completion
    - List updated files
    - Show task counts by priority
    - Provide next steps and Step-by-Step Reasoning why next steps 

## Output
- Design document: `docs/features/[feature_name].md`
- Updated: `docs/MVP.md`, `docs/BUSINESS_GOALS.md`, `docs/ROADMAP.md`, `docs/SPRINT_BACKLOG.md`, sprint plan, `docs/STATUS.md`
- Evidence folder: `docs/evidence/[feature_name]/`
- Next steps based on conflicts/prerequisites

## When to Use
- After creating detailed feature specifications
- Before starting major capability implementation
- When integrating external requirements
- To ensure documentation synchronization