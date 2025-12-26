# Sprint Cadence Definition - FX Agent AI

**Created:** 2025-12-26
**Updated:** 2025-12-26 (v1.1 - Paradox Verification Improvements)
**Owner:** SM (Bob)
**Version:** 1.1

---

## Sprint Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Sprint Length** | 1 week (5 working days) | Solo developer, fast feedback loops |
| **Sprint Start** | Monday | Fresh week start |
| **Sprint End** | **Friday** | Weekend free (work-life balance) |
| **Working Days** | Mon-Fri (flexible hours) | Minimum 20h/week commitment |
| **Ceremonies Day** | **Friday afternoon** | End week with reflection |

---

## Sprint Ceremonies

### 1. Sprint Planning (Monday morning)
| Attribute | Value |
|-----------|-------|
| **Duration** | 30-60 minutes |
| **Participants** | Developer (Mr Lu) + AI agents (optional) |
| **Input** | Product Backlog, Sprint Status, Risk Register |
| **Output** | Sprint Goal, Selected Stories, Updated sprint-status.yaml |

**Agenda:**
1. Review previous sprint results (5 min)
2. Review Risk Register for blockers (5 min)
3. Check availability for this week (5 min)
4. Select stories for sprint (15 min)
5. Define Sprint Goal (5 min)
6. Update sprint-status.yaml (5 min)

**Sprint Goal Template:**
> "By Friday, [SPECIFIC OUTCOME] will be achieved, demonstrating [USER VALUE]."

---

### 2. Daily Check-in - OPTIONAL
| Attribute | Value |
|-----------|-------|
| **Duration** | 5 minutes |
| **Frequency** | Daily - **OPTIONAL for solo dev** |
| **Format** | Mental check or AI-assisted |
| **Skip if** | Feels like theater, no value |

**For Solo Developer:** Daily standups can feel performative. Skip them if they don't add value. The REQUIRED ceremonies are Sprint Planning and Retrospective only.

**AI-Assisted Alternative:**
Instead of self-standup, ask Claude:
> "Review my commits from yesterday. What did I accomplish? What should I focus on today based on sprint goal: [goal]?"

---

### 3. Sprint Review (Friday, first half)
| Attribute | Value |
|-----------|-------|
| **Duration** | 30 minutes |
| **Purpose** | Demonstrate completed work |
| **When** | Friday afternoon (before retro) |

**Agenda:**
1. Demo completed stories (15 min) - record if valuable
2. Update sprint-status.yaml (5 min)
3. Update Risk Register if needed (5 min)
4. Document any deferred work (5 min)

**Success Metric:** Can I show working software for each completed story?

---

### 4. Sprint Retrospective (Friday, after Review)
| Attribute | Value |
|-----------|-------|
| **Duration** | 15-30 minutes |
| **Purpose** | Continuous improvement |
| **Status** | **REQUIRED** (not optional!) |
| **When** | Friday afternoon (after review) |

**Format (Solo Retro):**
| Question | Answer |
|----------|--------|
| What went well? | (2-3 items) |
| What didn't go well? | (2-3 items) |
| What will I do differently? | (1-2 specific actions) |
| Velocity this sprint | X stories / Y hours |

**Retro Log Location:** `_bmad-output/retrospectives/sprint-N.md`

**AI-Assisted Retro Prompt:**
> "Review my sprint commits and story completions. What patterns do you see? What should I do differently next sprint?"

---

## Story Workflow

### Story States
```
backlog → ready-for-dev → in-progress → blocked → review → done
                              ↑            │
                              └────────────┘
```

| State | Description | Action Required |
|-------|-------------|-----------------|
| `backlog` | Story exists in epic file only | Create story file (create-story workflow) |
| `ready-for-dev` | Story file created, ready to implement | Start implementation |
| `in-progress` | Actively being worked on | Complete tasks |
| `blocked` | Waiting on external dependency | Document blocker, work on other story |
| `review` | Implementation complete, needs review | Run code-review workflow |
| `done` | All DoD criteria met | Update sprint-status.yaml |

### State Transitions
- Stories move forward primarily (backlog → ready → in-progress → review → done)
- `blocked` is a side-state: in-progress ↔ blocked
- If review rejected: review → in-progress (fix issues)

---

## WIP Limits (REVISED)

| Type | Limit | Notes |
|------|-------|-------|
| **In-Progress** | 1 | Active work - full focus |
| **Blocked** | 1 | Waiting on external |
| **Total WIP** | **2** | Active + Blocked maximum |

### WIP Rules:
1. Only ONE story actively worked on at a time
2. If story becomes blocked, can start ONE other story
3. If both slots full (1 active + 1 blocked):
   - First: Try to unblock the blocked story
   - Second: Help with blocker (investigate, escalate)
   - Last resort only: Start 3rd story (requires justification)

**Anti-Pattern:** Context switching between multiple active stories kills velocity. WIP=2 allows flexibility for blockers without chaos.

---

## Variable Availability Protocol

Not all weeks are equal. Handle variable capacity explicitly.

### Low Availability Sprint (< 15h expected)
| Adjustment | Action |
|------------|--------|
| Sprint Scope | 1-2 XS/S stories MAX |
| Ceremonies | Combine Review + Retro (15 min total) |
| Planning | 15 min, pick ONE story |
| Documentation | Minimal, notes only |

**Declare at Sprint Planning:** "This is a reduced sprint due to [reason]."

### Standard Sprint (15-30h expected)
| Adjustment | Action |
|------------|--------|
| Sprint Scope | 2-4 stories (mix of sizes) |
| Ceremonies | Full ceremonies |
| Planning | 30-45 min |

### High Availability Sprint (> 35h expected)
| Adjustment | Action |
|------------|--------|
| Sprint Scope | Can add stories mid-sprint if ahead |
| Larger stories | Can take L stories |
| Buffer | Consider taking stretch goals |

**Caution:** High availability sprints can lead to overcommitment. Don't plan for max capacity.

---

## Sprint Capacity

### Capacity Calculation (Solo Developer)
| Factor | Hours | Notes |
|--------|-------|-------|
| Available hours/week | Variable (declare at planning) | Be honest |
| Ceremony overhead | 1.5 hours | Planning + Review + Retro |
| Buffer (interruptions) | 20% | Bugs, meetings, life |
| **Net capacity** | 80% of declared time | Realistic planning |

### Story Sizing (T-Shirt)
| Size | Hours | Description | Example |
|------|-------|-------------|---------|
| XS | 1-2h | Trivial change, single file | Fix typo, add log |
| S | 2-4h | Small feature, few files | Add validation, simple component |
| M | 4-8h | Medium feature, integration | New endpoint + frontend |
| L | 8-16h | Large feature, complex | Full feature across layers |
| XL | 16-32h | Epic-sized | **Must be split** |

**Rules:**
- No XL stories in sprint - must be split first
- Max 1 L story per sprint
- If stories consistently carry over, increase sprint length to 2 weeks

---

## Sprint Planning Rules

### Commitment Guidelines
1. **Underpromise, overdeliver** - 80% of capacity, not 100%
2. **Declare availability** - Be explicit about this week's hours
3. **One epic at a time** - Focus on completing epics
4. **Blockers first** - Resolve blockers before new work

### Story Selection Priority
1. Blockers and critical bugs (always first)
2. In-progress stories (finish what's started)
3. Highest priority epic stories
4. Technical debt (max 20% of sprint)
5. Stretch goals (only if ahead)

---

## AI-Assisted Sprint (Experimental)

Leverage AI for solo developer productivity.

### AI Sprint Planning
Ask Claude:
> "Given my velocity of X stories/week and these ready stories: [list], suggest optimal sprint composition for [available hours]h."

### AI Daily Progress
Ask Claude:
> "Review my recent commits. Am I on track for sprint goal: [goal]? Any concerns?"

### AI Retrospective Analysis
Ask Claude:
> "Review sprint-N retrospective and my recent patterns. What systemic improvements should I make?"

### AI Code Context
Before starting story, ask Claude:
> "I'm starting story [title]. What existing code should I review first? What patterns should I follow?"

---

## Velocity Tracking

### Sprint Velocity Log
| Sprint | Dates | Planned | Completed | Hours | Velocity | Notes |
|--------|-------|---------|-----------|-------|----------|-------|
| 0 | Pre-cadence | - | - | - | - | Setup work |
| 1 | Dec 30 - Jan 3 | TBD | TBD | TBD | TBD | First formal sprint |

**Location:** Track in sprint-status.yaml header AND here

### Velocity Metrics
- **Story Velocity:** Stories completed per sprint
- **Hour Velocity:** Hours worked per story
- **Completion Rate:** Stories completed / Stories planned

After 3 sprints, use average velocity for planning. Watch for gaming (inflating counts).

---

## Communication

### Async Communication (Solo + AI)
| Channel | Purpose |
|---------|---------|
| CLAUDE.md | AI context and instructions |
| sprint-status.yaml | Current sprint state |
| Risk Register | Active risks and blockers |
| Stories folder | Detailed story specs |
| Retrospectives | Sprint learnings |

### Escalation Path
| Trigger | Action |
|---------|--------|
| Blocker found | Document in Risk Register, try to unblock |
| Cannot meet sprint goal | Reduce scope (not quality), document why |
| Critical bug discovered | Stop sprint, fix bug, adjust scope |
| Burnout warning | Reduce next sprint, take break |

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why Bad | Alternative |
|--------------|---------|-------------|
| Skipping retros | No learning | 15 min minimum, even voice note |
| WIP > 2 | Context switching | Finish or block before starting new |
| Heroic sprints | Burnout, unsustainable | Reduce scope, protect weekends |
| Carrying over stories | Sprint loses meaning | Re-estimate, right-size |
| Gold plating | Features nobody asked for | Stick to acceptance criteria |
| Planning at 100% capacity | No room for reality | Plan at 80% max |
| Weekend ceremonies | Work-life balance | Friday only |

---

## Artifacts Location

| Artifact | Path |
|----------|------|
| Sprint Status | `_bmad-output/sprint-status.yaml` |
| Stories | `_bmad-output/stories/*.md` |
| Retrospectives | `_bmad-output/retrospectives/` |
| Risk Register | `_bmad-output/risk-register.md` |
| Definition of Done | `_bmad-output/definition-of-done.md` |
| Release Criteria | `_bmad-output/release-criteria-m1.md` |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-26 | SM | Initial version |
| 1.1 | 2025-12-26 | SM | Changed: Sunday→Friday, WIP=1→WIP=2, Added: Variable Availability Protocol, AI-assisted options, blocked state |

---

*Cadence is a tool, not a prison. Adapt as needed, but always with intention. Protect your weekends.*
