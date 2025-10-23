---
description: "Request and log user or stakeholder feedback for a specific feature. **Usage**: /feedback [feature]"
---

# /feedback - Capture User Input

**Purpose**: Request and log user or stakeholder feedback for a specific feature.

**Usage**: /feedback "[feature]" [--completed "item1,item2" --issues "issue1,issue2" --doc-changes "file1.md,file2.md" --evidence "path/to/recording.mp4"]

## Procedure
1. Prepare context: link to demo, environment access, or screenshots.
2. Document questions or validation goals in `docs/STATUS.md` → User Feedback.
3. Send or simulate request depending on environment; log expected response window.
4. When feedback arrives:
   a. Analyze feedback: identify what is confirmed as completed, what needs rework, what is missing or incorrect.
   b. Update `docs/STATUS.md` with feedback summary, marking confirmed completed items and highlighting issues.
   c. If changes required, update `docs/BACKLOG.md` with new tasks, modifications, or corrections based on feedback.
   d. Document important changes in relevant documents (e.g., update `docs/MVP.md` if scope confirmed/changed, `docs/ROADMAP.md` if timeline affected, `docs/DECISIONS.md` if architectural decisions needed).
   e. Assign priorities to identified issues/changes: MVP_CRITICAL (fix immediately, block other work), HIGH (fix in current sprint), MEDIUM (plan for next sprint), LOW (add to backlog).
   f. If feedback indicates implementation issues (e.g., bugs), trigger /verify_implementation for affected tasks.
   g. If significant scope change or rework needed, trigger /replan or add to backlog with assigned priority.

## Phase Guidance
- **Discovery**: Capture qualitative insights on hypotheses; adjust MUST TEST priorities.
- **Validation**: Tie feedback to acceptance criteria; record whether user value confirmed. Use to verify sprint deliverables and identify unimplemented features.
- **Production**: Ensure feedback loops include operational stakeholders; log any support or performance concerns.

## Evidence Requirements
- Provide evidence for feedback analysis: recordings, transcripts, screenshots, or session logs.
- For automated parsing: use AI tools to categorize feedback into completed/pending/issues (if available in environment).
- Store evidence in `docs/evidence/feedback/[feature]/` for traceability.

## Output
- Update COMPLETED or LEARNED sections with feedback results.
- Record follow-up work via /replan or backlog entries if significant scope change needed.

## When to Use
- After delivering features in Validation phase
- During Production for operational feedback
- When stakeholder input is needed for decision making
- After sprint completion (/end_sprint) to verify implemented steps and identify unimplemented features
- Automatically triggered in /end_sprint if user feedback collection is required for sprint closure

## Example
/feedback "User Authentication" --completed "Login form, Password reset" --issues "Two-factor auth not implemented" --doc-changes "docs/MVP.md" --evidence "docs/evidence/feedback/auth/session_recording.mp4"