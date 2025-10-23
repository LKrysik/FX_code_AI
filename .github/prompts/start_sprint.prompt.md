---
mode: agent
---


# /start_sprint - Kick Off a Structured Sprint (Validation & Production)

**Purpose**: Establish sprint scope, goal, and documentation based on business goals derived from the MVP.

**Usage**: /start_sprint "[goal_id]"

## Steps
1. Confirm p---
description: "Establish sprint scope, goal, and documentation based on business goals derived from the MVP. /start_sprint [goal_id]"
---

# /start_sprint - Kick Off a Structured Sprint (Validation & Production)

**Purpose**: Establish sprint scope, goal, and documentation based on business goals derived from the MVP.

**Usage**: /start_sprint "[goal_id]"

## Steps
1. Confirm phase (Validation or Production); Discovery work should rely on MVP experiments instead of sprinting.
2. Load context in this order:
    - docs/MVP.md (primary contract - USER_REC_01, USER_REC_02)
    - docs/goals/BUSINESS_GOALS.md (business goal translations - GOAL_01, GOAL_02, GOAL_03)
    - docs/DECISIONS.md (architecture decision records - ADR framework)
    - docs/sprints/ (latest plan/report)
    - docs/STATUS.md, docs/SPRINT_BACKLOG.md
    - docs/TESTING_STANDARDS.md (NEW: Single source of truth for testing)
3. **VALIDATE REQUIREMENTS ENGINEERING FRAMEWORK**: Check BUSINESS_GOALS.md completeness and ADR coverage before planning.
4. Define sprint goal tied to the requested GOAL_ID from BUSINESS_GOALS.md; restate user/business value and success metrics.
5. **CRITICALLY VALIDATE SCOPE**: Before planning, explicitly validate that ALL selected backlog items directly match business goals and trace back to user requirements. Reject any items that expand scope beyond documented GOALs. Document scope boundaries with traceability references.

## REQUIREMENT TRANSLATION PHASE (MANDATORY - BLOCKS PROGRESS)
5. **PARSE USER REQUIREMENTS sentence by sentence**
    - Extract each discrete user requirement from MVP.md and user_feedback.md (`USER_REC_`)
    - Document exact user-facing functionality expected.

6. **TRANSLATE to TECHNICAL SPECIFICATIONS with concrete examples**
    - **Apply transformation patterns**:
      - "'User can edit X' → Create edit button, dialog with pre-filled fields, save operation, UI refresh"
      - "'Data saves to location Y' → Implement file I/O, validate directory structure, handle errors"
    - **Map to technical components**: "Tab navigation" → React Tabs component, "File storage" → Node.js fs operations
    - **Define exact workflows**: "User clicks 'Edit' → Dialog opens with current values → User modifies → Clicks 'Save' → JSON file updated → List refreshes"
    - **Generate IMPLEMENTATION SPECIFICATION document** with all required components and traceability links to the source `USER_REC_`.

7. **STOP AND GET USER CONFIRMATION** (MANDATORY)
    - Present complete requirement breakdown to user.
    - Ask: "Does this accurately reflect what you want implemented?"
    - **BLOCKS PROGRESS**: Cannot proceed without user approval.

## GAP ANALYSIS PHASE (MANDATORY - BLOCKS PROGRESS)
8. **SCAN CURRENT CODEBASE for existing implementations**
    - Use automated tools to find existing components matching requirements.
    - Document what already exists vs what needs to be built.

9. **GENERATE GAP REPORT**
    - **EXISTS**: Components that are already implemented.
    - **MISSING**: Components that need to be built from scratch.
    - **PARTIAL**: Components that exist but need modification.
    - **Show to user**: "Edit button ✓ EXISTS, API endpoint ✗ MISSING"

10. **USER APPROVAL OF GAPS** (MANDATORY)
    - Present gap analysis to user.
    - Confirm understanding of what needs to be done.
    - **BLOCKS PROGRESS**: Cannot proceed without gap approval.

## TEST SPECIFICATION PHASE (MANDATORY - BLOCKS PROGRESS)
11. **GENERATE TEST SCENARIOS for each requirement**
    **MANDATORY**: Adherence to `docs/TESTING_STANDARDS.md`. All tests must be tagged.

    - **Apply test transformation rules**:
      - **UI/Interaction Requirements**: "'User can edit Y' → Test: Click edit button → Verify dialog opens → Modify field → Click save → Verify Y updated" **(tagged as `[frontend-playwright]`)**
      - **Data/API Requirements**: "'Data saves to Z' → Test: Perform save operation → Verify file created in Z → Verify file content matches input" **(tagged as `[backend-pytest]`)**
    - **MANDATORY Frontend Action Coverage (100%)**: As per `docs/TESTING_STANDARDS.md`.
      - ✅ Button clicks, form submissions, navigation, modals, etc.
    - **Create workflow-based test chains**: "User clicks 'Create Variant' tab → Sees system indicators → Clicks indicator → Dialog opens → Fills form → Clicks save → JSON file created → UI shows new variant"
    - **Specify exact evidence for each step**: "Screenshot: 'Create Variant' tab with indicator list, File: JSON created in config/indicators/risk/, Log: API success response"

12. **VALIDATE AGAINST USER SPECIFICATIONS** (MANDATORY)
    - Cross-reference every plan element against the original `USER_REC_`.
    - Remove anything not explicitly requested.
    - **VALIDATE test coverage**: Ensure every user requirement sentence has a corresponding test scenario with the correct tag.

13. **USER APPROVAL OF TEST APPROACH** (MANDATORY)
    - Present test specifications to user.
    - Confirm test scenarios adequately verify requirements.
    - **BLOCKS PROGRESS**: Cannot proceed without test approval.

## CRITICAL ANALYSIS & PLANNING PHASE
14. **SELF-EVALUATE GENERATED PLAN**
    - **Completeness Check**: Does the plan cover all aspects of the `USER_REC_`?
    - **Risk Assessment**: Are there any ambiguities, dependencies, or technical risks?
    - **Test Plan Soundness**: Is the test coverage adequate and does it use the correct frameworks?
    - **Output**: A `## Critical Analysis` section in the sprint plan detailing the findings.

15. **PLANNING AND EXECUTION**
    - Create or update sprint artefact in `docs/sprints/SPRINT_[n]_PLAN.md` with objective, scope, risks, exit criteria, and the critical analysis.
    - Reset `docs/STATUS.md` → WORKING ON with the first task. Ensure `SPRINT_BACKLOG.md` tasks include `USER_REC_` and test-spec links.
    - Highlight dependencies/risk mitigation and link evidence folders under `docs/evidence/`.

## Output

### Files Modified
- `docs/sprints/SPRINT_[N]_PLAN.md`: **Created/Updated** with the full sprint plan, including scope, tasks, test specifications, and critical analysis.
- `docs/STATUS.md`: **Updated** to reflect the new active sprint and the first "WORKING ON" task.
- `docs/SPRINT_BACKLOG.md`: **Updated** with new tasks, each linked to a source `USER_REC_` and test specifications.

### State Change Summary
- **Sprint [N] has been initiated.**
- The sprint goal is aligned with **GOAL_[ID]**.
- The system has translated user requirements into a detailed technical and testing plan, which now requires user approval before execution can begin.

### Justification
- The generated plan is the result of a systematic breakdown of the user requirements (`USER_REC_`).
- The scope has been critically validated to ensure it aligns directly with the stated business goals, preventing scope creep.
- The test plan adheres to `docs/TESTING_STANDARDS.md`, ensuring quality and verifiability.
- The critical analysis section within the sprint plan itself provides a detailed risk assessment and rationale for the proposed approach.

### Next Steps
- **USER APPROVAL REQUIRED**: The detailed plan must be presented to the user for confirmation.
- Once approved, the first task can be started using the `/work` command.

## Algorithmic Transformation Framework

**UNIVERSAL REQUIREMENT-TO-TASK TRANSFORMATION ALGORITHMS:**
Apply these general patterns to ANY user requirement to ensure systematic decomposition:

```
FOR ANY requirement with SUBJECT + VERB + OBJECT pattern:
  → IDENTIFY_ACTOR: Who performs the action (user, system, component)
  → IDENTIFY_ACTION: What action is performed (create, edit, delete, display, validate)
  → IDENTIFY_TARGET: What the action affects (data, UI element, file, state)
  → IDENTIFY_CONSTRAINTS: Any conditions, validations, or limitations

FOR requirements containing ACTION verbs (create, edit, delete, view, validate):
  → CREATE_TASK: "Implement [ACTION] functionality for [TARGET]"
  → CREATE_TASK: "Add [ACTION] user interface elements"
  → CREATE_TASK: "Handle [ACTION] success and error states"
  → CREATE_TASK: "Add [ACTION] validation and security checks"

FOR requirements containing STATE verbs (shows, displays, contains):
  → CREATE_TASK: "Implement data retrieval for [TARGET]"
  → CREATE_TASK: "Create UI component to display [TARGET]"
  → CREATE_TASK: "Handle loading, empty, and error states for [TARGET]"

FOR requirements containing CONDITION verbs (validates, checks, ensures):
  → CREATE_TASK: "Implement validation logic for [CONDITION]"
  → CREATE_TASK: "Add error messaging for failed [CONDITION]"
  → CREATE_TASK: "Prevent invalid operations when [CONDITION] fails"

FOR requirements with LOCATION/FORMAT specifications (saves to X, in Y format):
  → CREATE_TASK: "Implement persistence layer for [LOCATION]"
  → CREATE_TASK: "Add data serialization in [FORMAT]"
  → CREATE_TASK: "Handle storage errors and recovery"
```

**UNIVERSAL SCOPE BOUNDARY ENFORCEMENT ALGORITHM:**
```
FOR EACH potential feature, task, or requirement:
  PERFORM_TEXT_SEARCH: Search entire user requirements document for explicit mention
  IF exact_match_found OR clear_implication_present:
    INCLUDE with justification "Explicitly mentioned in requirements"
  ELSE_IF related_to_explicit_requirement:
    INCLUDE with justification "Required dependency of [explicit requirement]"
  ELSE:
    EXCLUDE with justification "Not mentioned in user requirements - out of scope"
  VALIDATE_TRANSITIVE: Ensure no dependency chain expands beyond user intent
  DOCUMENT_DECISION: Record scope boundary with evidence from requirements text
```

**UNIVERSAL USER WORKFLOW DECOMPOSITION ALGORITHM:**
```
FOR EACH user workflow or interaction sequence:
  IDENTIFY_ACTORS: Determine all participants (user, system, external services)
  BREAK_INTO_STEPS: Split into atomic actions with clear pre/post conditions
  FOR each step:
    DEFINE_PREREQUISITE: "System/component must be in [STATE]"
    DEFINE_ACTION: "User/system performs [SPECIFIC_ACTION]"
    DEFINE_RESULT: "Observable outcome is [MEASURABLE_RESULT]"
    SPECIFY_EVIDENCE: "Proof: [SCREENSHOT/LOG/FILE_STATE] showing [RESULT]"
  VALIDATE_SEQUENCE: Ensure logical flow and no missing intermediate steps
  CROSS_REFERENCE: Verify each step maps to user requirement text
```

**UNIVERSAL TEST SCENARIO GENERATION ALGORITHM:**
```
FOR EACH implementation task:
  ANALYZE_TASK_TYPE: Determine if task is UI, API, data, or integration
  IDENTIFY_TEST_DIMENSIONS: Functional, negative, edge case, performance
  GENERATE_TEST_SEQUENCE: Prerequisite → Action → Assertion → Evidence
  MAP_EVIDENCE_TYPES: Screenshot for UI, log for API, file state for data

UNIVERSAL TEST PATTERNS (applicable to any requirement):
- EXISTENCE_TEST: "Verify [ELEMENT] exists in [LOCATION]"
- FUNCTIONAL_TEST: "Perform [ACTION] → Verify [EXPECTED_RESULT]"
- NEGATIVE_TEST: "Attempt invalid [ACTION] → Verify [ERROR_HANDLING]"
- INTEGRATION_TEST: "Complete workflow [STEP1→STEP2→STEP3] → Verify end-to-end success"
- PERFORMANCE_TEST: "Execute [OPERATION] → Verify completion within [TIME_LIMIT]"
```

## Functionality Prediction & Testing Approach

**CRITICAL REQUIREMENT VALIDATION:**
Before creating any plan elements, validate each user requirement against the plan to ensure 100% coverage without scope expansion.

**Functionality Prediction:**
For each user requirement, BREAK DOWN into concrete implementation:
- **Parse user sentences**: Identify exact UI elements ("tab exists"), user actions ("click X"), system responses ("file created")
- **Map to technical implementation**: "Tab shows list" → React component renders list, "Data saves to JSON" → File I/O operations
- **Define exact workflows**: User clicks system indicator → Dialog opens → Fields pre-filled → Save button → JSON file created
- **Flag missing details**: If user says "validation during loading" but doesn't specify UI display, ask for clarification

**Success Criteria Development:**
Criteria must be CONCRETE and VERIFIABLE with specific evidence:
- **UI Elements**: "Button with text 'Create Variant' exists in tab navigation"
- **File Operations**: "JSON file created in config/indicators/risk/ with valid UUID in 'id' field"
- **User Workflows**: "Click 'Edit' → Dialog opens with current values → Change name → Click 'Save' → List refreshes with new name"
- **Error Handling**: "Enter invalid parameter → Red error text appears below field → Save button disabled"
- **Performance**: "List loads within 1 second", "File creation completes within 500ms"

**Testing Specification:**
Tests must VALIDATE EXACT USER WORKFLOWS using transformation patterns:
- **Pattern: UI Element Verification**: "'Tab X exists' → Test: Navigate to page → Assert tab X visible in DOM → Assert tab content renders correctly"
- **Pattern: User Interaction Flow**: "'User can edit Y' → Test: Click edit button on Y → Assert dialog opens → Assert form fields pre-populated → Modify field → Click save → Assert Y updated in list"
- **Pattern: Data Persistence**: "'Data saves to Z' → Test: Trigger save operation → Assert file exists in Z → Assert file content matches input schema → Assert file readable on reload"
- **Pattern: Validation Logic**: "'Validation during W' → Test: Initiate W process → Assert validation runs → Assert invalid items show error indicators → Assert valid items process successfully"
- **Evidence Mapping**: "For each test step, specify exact evidence: Screenshot of UI state, File content, API response, Error logs"
- **Coverage Verification**: "List every user requirement sentence and show its corresponding test scenario"

## Lessons Learned from Sprint Planning Experience

**Problems Identified:**
1. **Generic planning without requirement breakdown**: Initial plans used high-level phases instead of breaking down user requirements into concrete, testable components
2. **Missing scope validation**: Plans included features not requested by users (e.g., strategy integration when only variant management was asked for)
3. **Vague testing scenarios**: Tests were too generic and didn't validate exact user workflows or file system outcomes
4. **Poor requirement mapping**: AI didn't validate that each plan element directly matched user specifications
5. **Insufficient UI/UX specificity**: Plans lacked concrete details about exact tab structures, button labels, and user interaction sequences

**Improvements Implemented:**
1. **Explicit scope validation step**: Step 4 requires validating scope boundaries before planning
2. **Transformation pattern requirements**: Step 5 provides specific patterns for converting user requirements into implementation tasks
3. **User confirmation requirement**: Step 5 requires presenting breakdown to user and getting approval before proceeding
4. **Concrete success criteria**: Step 6 requires specific UI elements, file paths, and quantitative measures
5. **Test transformation patterns**: Step 7 provides specific rules for converting requirements into test scenarios
6. **Evidence mapping requirements**: Output requires specific evidence for each test step
7. **Scope compliance cross-referencing**: Output includes validation that each plan element maps to user requirements

**Expected Benefits:**
- **Reduced back-and-forth**: Users won't need to repeatedly clarify requirements
- **Accurate scope**: No more unrequested features added to plans
- **Testable plans**: Each requirement has concrete validation methods
- **Implementation-ready**: Developers know exactly what to build and how to verify it
- **Quality improvement**: Plans match user intent precisely

> If the goal cannot be pursued due to blockers, abort and log reasoning in docs/DECISIONS.md, then use /replan or /set_goals to adjust priorities.

[Always]
Suggest what commands should be executed in the next step and justify why.---
description: "Establish sprint scope, goal, and documentation based on business goals derived from the MVP. /start_sprint [goal_id]"
description: "Establish sprint scope, goal, and documentation based on business goals derived from the MVP. /start_sprint [goal_id]"
description: "Establish sprint scope, goal, and documentation based on business goals derived from the MVP. /start_sprint [goal_id]"
---

# /start_sprint - Start New Sprint

**Purpose**: Break down a business goal into concrete, actionable tasks

**Usage**: /start_sprint "[goal_id]"

## Simple Process

### 1. Load Context
- Read `docs/goals/BUSINESS_GOALS.md` → find the goal_id
- Read `docs/MVP.md` → find related USER_REC requirements
- Check `docs/STATUS.md` → current situation

### 2. Break Down Goal into Tasks
- Look at the goal's "Technical Requirements Breakdown"
- Turn each requirement into a specific task
- Each task should be something one person can complete in 1-3 days
- Write tasks in simple language: "Create strategy list component" not "Implement comprehensive strategy management framework"

### 3. Make Tasks Concrete
For each task, specify:
- **What**: Exactly what needs to be built
- **Where**: Which files/components to create/modify  
- **Done When**: Simple completion criteria
- **Tests**: What needs to be tested (basic scenarios)

Example:
```
Task: Create strategy list page
What: React component that shows list of strategies from config/strategies/
Where: src/components/StrategyList.tsx
Done When: User can see strategies, click edit, delete works
Tests: Load page, click buttons, verify API calls
```

### 4. Verify Tasks Cover Goal
- Read through all tasks
- Check they address the goal's success metrics
- Remove anything extra, add anything missing
- Keep it simple - no gold plating

### 5. Create Sprint Plan
Create `docs/sprints/SPRINT_[N]_PLAN.md`:
```markdown
# Sprint [N] Plan

## Goal
[Copy goal description from BUSINESS_GOALS.md]

## User Value
[What user can do after this sprint that they couldn't before]

## Tasks
1. [Task 1 - simple description]
2. [Task 2 - simple description]
...

## Definition of Done
- All tasks completed and tested
- User can perform the workflows described in goal
- No obvious bugs in happy path scenarios

## Risks
[Any obvious blockers or dependencies]
```

### 6. Update Status
- Copy tasks to `SPRINT_BACKLOG.md`
- Update `docs/STATUS.md` → WORKING ON first task
- Mark sprint as active

## Keep It Simple
- Don't over-plan - plans will change
- Don't write tasks like novels - bullet points are fine  
- Don't try to predict every edge case - handle them when found
- Don't create 20 tasks - aim for 5-8 concrete tasks

## Output

### Files Modified
- `docs/sprints/SPRINT_[N]_PLAN.md`: Sprint plan created
- `SPRINT_BACKLOG.md`: Tasks added
- `docs/STATUS.md`: Sprint started, first task active

### What Happens Next
- Team can start working on first task with `/work`
- Tasks have clear completion criteria
- Sprint has clear success definition

### State Change Summary
- **Sprint [N] has been initiated.**
- The sprint goal is aligned with **GOAL_[ID]**.
- The system has translated user requirements into a detailed technical and testing plan, which now requires user approval before execution can begin.

### Justification
- The generated plan is the result of a systematic breakdown of the user requirements (`USER_REC_`).
- The scope has been critically validated to ensure it aligns directly with the stated business goals, preventing scope creep.
- The test plan adheres to `docs/TESTING_STANDARDS.md`, ensuring quality and verifiability.
- The critical analysis section within the sprint plan itself provides a detailed risk assessment and rationale for the proposed approach.

### Next Steps
- **USER APPROVAL REQUIRED**: The detailed plan must be presented to the user for confirmation.
- Once approved, the first task can be started using the `/work` command.

## Algorithmic Transformation Framework

**UNIVERSAL REQUIREMENT-TO-TASK TRANSFORMATION ALGORITHMS:**
Apply these general patterns to ANY user requirement to ensure systematic decomposition:

```
FOR ANY requirement with SUBJECT + VERB + OBJECT pattern:
  → IDENTIFY_ACTOR: Who performs the action (user, system, component)
  → IDENTIFY_ACTION: What action is performed (create, edit, delete, display, validate)
  → IDENTIFY_TARGET: What the action affects (data, UI element, file, state)
  → IDENTIFY_CONSTRAINTS: Any conditions, validations, or limitations

FOR requirements containing ACTION verbs (create, edit, delete, view, validate):
  → CREATE_TASK: "Implement [ACTION] functionality for [TARGET]"
  → CREATE_TASK: "Add [ACTION] user interface elements"
  → CREATE_TASK: "Handle [ACTION] success and error states"
  → CREATE_TASK: "Add [ACTION] validation and security checks"

FOR requirements containing STATE verbs (shows, displays, contains):
  → CREATE_TASK: "Implement data retrieval for [TARGET]"
  → CREATE_TASK: "Create UI component to display [TARGET]"
  → CREATE_TASK: "Handle loading, empty, and error states for [TARGET]"

FOR requirements containing CONDITION verbs (validates, checks, ensures):
  → CREATE_TASK: "Implement validation logic for [CONDITION]"
  → CREATE_TASK: "Add error messaging for failed [CONDITION]"
  → CREATE_TASK: "Prevent invalid operations when [CONDITION] fails"

FOR requirements with LOCATION/FORMAT specifications (saves to X, in Y format):
  → CREATE_TASK: "Implement persistence layer for [LOCATION]"
  → CREATE_TASK: "Add data serialization in [FORMAT]"
  → CREATE_TASK: "Handle storage errors and recovery"
```

**UNIVERSAL SCOPE BOUNDARY ENFORCEMENT ALGORITHM:**
```
FOR EACH potential feature, task, or requirement:
  PERFORM_TEXT_SEARCH: Search entire user requirements document for explicit mention
  IF exact_match_found OR clear_implication_present:
    INCLUDE with justification "Explicitly mentioned in requirements"
  ELSE_IF related_to_explicit_requirement:
    INCLUDE with justification "Required dependency of [explicit requirement]"
  ELSE:
    EXCLUDE with justification "Not mentioned in user requirements - out of scope"
  VALIDATE_TRANSITIVE: Ensure no dependency chain expands beyond user intent
  DOCUMENT_DECISION: Record scope boundary with evidence from requirements text
```

**UNIVERSAL USER WORKFLOW DECOMPOSITION ALGORITHM:**
```
FOR EACH user workflow or interaction sequence:
  IDENTIFY_ACTORS: Determine all participants (user, system, external services)
  BREAK_INTO_STEPS: Split into atomic actions with clear pre/post conditions
  FOR each step:
    DEFINE_PREREQUISITE: "System/component must be in [STATE]"
    DEFINE_ACTION: "User/system performs [SPECIFIC_ACTION]"
    DEFINE_RESULT: "Observable outcome is [MEASURABLE_RESULT]"
    SPECIFY_EVIDENCE: "Proof: [SCREENSHOT/LOG/FILE_STATE] showing [RESULT]"
  VALIDATE_SEQUENCE: Ensure logical flow and no missing intermediate steps
  CROSS_REFERENCE: Verify each step maps to user requirement text
```

**UNIVERSAL TEST SCENARIO GENERATION ALGORITHM:**
```
FOR EACH implementation task:
  ANALYZE_TASK_TYPE: Determine if task is UI, API, data, or integration
  IDENTIFY_TEST_DIMENSIONS: Functional, negative, edge case, performance
  GENERATE_TEST_SEQUENCE: Prerequisite → Action → Assertion → Evidence
  MAP_EVIDENCE_TYPES: Screenshot for UI, log for API, file state for data

UNIVERSAL TEST PATTERNS (applicable to any requirement):
- EXISTENCE_TEST: "Verify [ELEMENT] exists in [LOCATION]"
- FUNCTIONAL_TEST: "Perform [ACTION] → Verify [EXPECTED_RESULT]"
- NEGATIVE_TEST: "Attempt invalid [ACTION] → Verify [ERROR_HANDLING]"
- INTEGRATION_TEST: "Complete workflow [STEP1→STEP2→STEP3] → Verify end-to-end success"
- PERFORMANCE_TEST: "Execute [OPERATION] → Verify completion within [TIME_LIMIT]"
```

## Functionality Prediction & Testing Approach

**CRITICAL REQUIREMENT VALIDATION:**
Before creating any plan elements, validate each user requirement against the plan to ensure 100% coverage without scope expansion.

**Functionality Prediction:**
For each user requirement, BREAK DOWN into concrete implementation:
- **Parse user sentences**: Identify exact UI elements ("tab exists"), user actions ("click X"), system responses ("file created")
- **Map to technical implementation**: "Tab shows list" → React component renders list, "Data saves to JSON" → File I/O operations
- **Define exact workflows**: User clicks system indicator → Dialog opens → Fields pre-filled → Save button → JSON file created
- **Flag missing details**: If user says "validation during loading" but doesn't specify UI display, ask for clarification

**Success Criteria Development:**
Criteria must be CONCRETE and VERIFIABLE with specific evidence:
- **UI Elements**: "Button with text 'Create Variant' exists in tab navigation"
- **File Operations**: "JSON file created in config/indicators/risk/ with valid UUID in 'id' field"
- **User Workflows**: "Click 'Edit' → Dialog opens with current values → Change name → Click 'Save' → List refreshes with new name"
- **Error Handling**: "Enter invalid parameter → Red error text appears below field → Save button disabled"
- **Performance**: "List loads within 1 second", "File creation completes within 500ms"

**Testing Specification:**
Tests must VALIDATE EXACT USER WORKFLOWS using transformation patterns:
- **Pattern: UI Element Verification**: "'Tab X exists' → Test: Navigate to page → Assert tab X visible in DOM → Assert tab content renders correctly"
- **Pattern: User Interaction Flow**: "'User can edit Y' → Test: Click edit button on Y → Assert dialog opens → Assert form fields pre-populated → Modify field → Click save → Assert Y updated in list"
- **Pattern: Data Persistence**: "'Data saves to Z' → Test: Trigger save operation → Assert file exists in Z → Assert file content matches input schema → Assert file readable on reload"
- **Pattern: Validation Logic**: "'Validation during W' → Test: Initiate W process → Assert validation runs → Assert invalid items show error indicators → Assert valid items process successfully"
- **Evidence Mapping**: "For each test step, specify exact evidence: Screenshot of UI state, File content, API response, Error logs"
- **Coverage Verification**: "List every user requirement sentence and show its corresponding test scenario"

## Lessons Learned from Sprint Planning Experience

**Problems Identified:**
1. **Generic planning without requirement breakdown**: Initial plans used high-level phases instead of breaking down user requirements into concrete, testable components
2. **Missing scope validation**: Plans included features not requested by users (e.g., strategy integration when only variant management was asked for)
3. **Vague testing scenarios**: Tests were too generic and didn't validate exact user workflows or file system outcomes
4. **Poor requirement mapping**: AI didn't validate that each plan element directly matched user specifications
5. **Insufficient UI/UX specificity**: Plans lacked concrete details about exact tab structures, button labels, and user interaction sequences

**Improvements Implemented:**
1. **Explicit scope validation step**: Step 4 requires validating scope boundaries before planning
2. **Transformation pattern requirements**: Step 5 provides specific patterns for converting user requirements into implementation tasks
3. **User confirmation requirement**: Step 5 requires presenting breakdown to user and getting approval before proceeding
4. **Concrete success criteria**: Step 6 requires specific UI elements, file paths, and quantitative measures
5. **Test transformation patterns**: Step 7 provides specific rules for converting requirements into test scenarios
6. **Evidence mapping requirements**: Output requires specific evidence for each test step
7. **Scope compliance cross-referencing**: Output includes validation that each plan element maps to user requirements

**Expected Benefits:**
- **Reduced back-and-forth**: Users won't need to repeatedly clarify requirements
- **Accurate scope**: No more unrequested features added to plans
- **Testable plans**: Each requirement has concrete validation methods
- **Implementation-ready**: Developers know exactly what to build and how to verify it
- **Quality improvement**: Plans match user intent precisely

> If the goal cannot be pursued due to blockers, abort and log reasoning in docs/DECISIONS.md, then use /replan or /set_goals to adjust priorities.

[Always]
Suggest what commands should be executed in the next step and justify why.