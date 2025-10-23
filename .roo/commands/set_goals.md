---
description: "Turn MVP requirements into simple business goals"
---

# /set_goals - Create Business Goals from MVP

**Purpose**: Turn MVP user requirements into clear business goals that can guide sprints

**Usage**: /set_goals

## Simple Process

### 1. Read MVP Requirements
- Open `docs/MVP.md`
- Find all USER_REC sections (USER_REC_01, USER_REC_02, etc.)
- Extract the main user-facing functionality from each

### 2. Turn Requirements into Goals
For each USER_REC:
- Write a simple goal that describes what user value will be delivered
- Include basic success criteria (how you know it's done)
- Estimate complexity (Simple/Medium/Complex)

Example:
```
USER_REC_01: "Strategy Builder ma dwie zakładki..."

Becomes:

GOAL_01: Strategy Builder Implementation
- User can create, edit, and manage trading strategies through a web interface
- Success: User can create strategy, save it, edit it, and see it in list
- Complexity: Complex (multiple UI components, API, file storage)
```

### 3. Create Goals Document
Update `docs/goals/BUSINESS_GOALS.md`:

```markdown
# Business Goals

## GOAL_01: [Goal Name]
**Source**: USER_REC_01 (docs/MVP.md)
**User Value**: [What user can accomplish]
**Success Criteria**: 
- [Specific things that must work]
- [Basic acceptance criteria]

**Complexity**: [Simple/Medium/Complex]
**Dependencies**: [What needs to be done first, if anything]

## GOAL_02: [Next Goal]
[... same format]
```

### 4. Prioritize Goals
- Order goals by user value and dependencies
- Mark any goals that depend on others
- Note which goal should be tackled first

### 5. Update Planning Docs
- Add goal references to `SPRINT_BACKLOG.md`
- Update `docs/STATUS.md` with next goal to work on

## Keep It Simple
- Don't over-analyze - extract main user functionality
- Don't create 20 goals - aim for 3-7 main goals
- Don't worry about perfect requirements - goals will be refined during sprint planning
- Don't add features not requested in USER_REC

## Output

### Files Modified
- `docs/goals/BUSINESS_GOALS.md`: Goals created from MVP requirements
- `docs/STATUS.md`: Updated with goal priorities

### What Happens Next
- Team can start sprint with `/start_sprint "GOAL_01"`
- Goals provide clear user value focus
- Sprint planning can break goals into tasks
- After docs/MVP.md changes or new reality checks.
- Before planning a new sprint or release.
- When stakeholders adjust business priorities but keep MVP as primary contract.
