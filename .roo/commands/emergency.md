---
description: "Respond to severe incidents or blockers threatening delivery or operations. Usage /emergency [issue description]"
---

# /emergency - Handle Critical Production Issues

**Purpose**: Respond to severe incidents or blockers threatening delivery or operations.

**Usage**: /emergency "[issue description]"

## Steps
1. Document issue in `docs/STATUS.md` → Blocker with severity and impact.
2. Assess blast radius: affected services, users, data.
3. Initiate mitigation plan:
   - If incident: trigger runbook, apply hotfix, or rollback.
   - If blocker: identify workaround or escalate decision needs.
4. Pause current sprint tasks if necessary and note in `docs/BACKLOG.md`.
5. Record decisions and actions in `docs/DECISIONS.md` (Operational Notes) and update `docs/ROADMAP.md` risks.
6. After resolution, run targeted regression tests and document evidence.
7. Create follow-up tasks for long-term fixes or post-mortem actions.

## Output
- Clear log of incident, response, and outcome.
- Step-by-Step Reasoning
- Updated backlog with remediation items.
- Communication plan captured in `docs/STATUS.md` → NEXT SESSION and relevant reports.