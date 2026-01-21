# Deep Verify V12.2 — Empirically Grounded Verification

---

## Overview

Sequential verification workflow with early exit capability. Designed for maximum effectiveness at minimum cost.

**Core Principles:**
1. **Early Exit** — Stop when evidence is sufficient, not when all methods are exhausted
2. **Mandatory Quotes** — No quote, no finding. Every claim must cite artifact text.
3. **Signal-Based Selection** — Choose methods based on what Phase 1 reveals
4. **Pattern Matching** — Check against known impossibility patterns before deep analysis
5. **Adversarial Validation** — Attack your own findings before finalizing
6. **Bias Awareness** — Actively counteract confirmation bias (NEW in V12.2)

---

## Evidence Score System

### Base Scoring

| Event | S Change |
|-------|----------|
| CRITICAL finding | +3 |
| IMPORTANT finding | +1 |
| MINOR finding | +0.3 |
| Clean method pass | -0.5 |

### Scoring Clarifications

| Situation | Rule |
|-----------|------|
| New finding from new method | Full points (+3/+1/+0.3) |
| Same finding confirmed by different method | +1 bonus (strengthens evidence) |
| Same finding from same-cluster method | +0 (skip per correlation rule) |
| Finding upgraded during analysis | Add difference (IMPORTANT→CRITICAL = +2) |
| Finding downgraded in Phase 3 | Subtract difference (IMPORTANT→MINOR = -0.7) |

### Decision Thresholds

| Condition | Action |
|-----------|--------|
| S ≥ 6 AND Pattern Match | **REJECT** — Stop immediately |
| S ≥ 6 WITHOUT Pattern Match | **CONTINUE** to Phase 2 for confirmation (NEW V12.2) |
| S ≤ -3 | **ACCEPT** — Stop immediately (unless HIGH stakes) |
| 4 ≤ S < 6 | **BORDERLINE** — Mandatory Phase 2+3 (NEW V12.2) |
| -3 < S < 4 | **CONTINUE** or **UNCERTAIN** |

---

## Phase 0: Setup

**Time:** 2-5 minutes

### 0.1 Stakes Assessment

```
What happens if we ACCEPT a flawed artifact?

[ ] LOW    — Minor rework, <$10K, <1 week, reversible
[ ] MEDIUM — Significant rework, $10K-$100K, 1-4 weeks  
[ ] HIGH   — Major damage, >$100K, >1 month, safety, reputation

What happens if we REJECT a sound artifact?

[ ] LOW    — Minor delay, <1 week
[ ] MEDIUM — Significant delay, 1-4 weeks
[ ] HIGH   — Major opportunity cost, >1 month, competitive loss
```

### 0.2 Initial Assessment (with Bias Mitigation) — UPDATED V12.2

**Standard Mode:**
```
Before reading carefully, this artifact seems:

[ ] Probably sound  — Looks solid, no red flags (prior ~0.6 sound)
[ ] Uncertain       — Complex, can't tell yet (prior ~0.3 sound)
[ ] Probably flawed — Strong claims, something smells wrong (prior ~0.15 sound)

Basis for this feeling: ________________________________
```

**Blind Mode (recommended for HIGH stakes):** — NEW V12.2
```
Skip initial assessment entirely. Record "BLIND" and proceed directly 
to Phase 1. This prevents confirmation bias from anchoring your analysis.

Initial Assessment: [ ] BLIND (no pre-judgment recorded)
```

**Forced Alternative Mode:** — NEW V12.2
```
After forming initial impression, MUST articulate:

If I think FLAWED, what would ACCEPT require?
Answer: ________________________________

If I think SOUND, what would REJECT require?
Answer: ________________________________

This forces consideration of disconfirming evidence.
```

### 0.3 Bias Check — EXPANDED V12.2

Answer honestly before proceeding:

1. **What outcome am I expecting?** (Note this — it's your bias)
2. **Am I verifying or confirming?**
3. **What would make me change my mind?**
4. **Have I seen similar artifacts before? What happened?** (NEW)
5. **Is there external pressure toward a particular verdict?** (NEW)

**Red Flag Check:** — NEW V12.2
```
If you answered "Probably flawed" in 0.2 AND you expect REJECT:
→ You MUST use Blind Mode or Forced Alternative Mode
→ Document why you're not using standard mode if you proceed anyway
```

**Output:** Stakes level, initial assessment (or BLIND), noted biases, mode selection

---

## Phase 1: Pattern Scan

**Time:** 5-15 minutes  
**Goal:** Rapidly identify red flags using cheap, broad methods

### 1.1 Execute Tier 1 Methods

Execute ALL of these (low cost, high discrimination):

| # | Method | Question to Answer |
|---|--------|-------------------|
| 71 | First Principles | Are the fundamental assumptions valid? |
| 100 | Vocabulary Audit | Are key terms used consistently throughout? |
| 17 | Abstraction Laddering | Are abstraction levels coherent and connected? |

### 1.2 Check Pattern Library

Scan artifact for known impossibility patterns:

**Definitional Contradictions:**

| Pattern | Signal | Check |
|---------|--------|-------|
| PFS + Escrow | Claims both "Perfect Forward Secrecy" and "key recovery" | Mutually exclusive by definition |
| Gradual Typing + Termination | Claims "gradual/dynamic types" and "guaranteed termination" | Rice's theorem — undecidable |
| Deterministic + Adaptive | Claims both "reproducible" and "learning/adaptive" | Which wins when they conflict? |
| Consistency + Availability | Claims both under partition tolerance | CAP theorem — pick two |

**Theorem Violations:**

| Pattern | Signal | Theorem |
|---------|--------|---------|
| VCG + Balanced Budget | Strategy-proof auction with no external subsidy | Green-Laffont impossibility |
| Async + Consensus + Faults | Async network + f < N/2 faults + guaranteed termination | FLP impossibility (f < N/3 is proven bound) |
| Universal Bug Detection | "Detects all bugs" / "guarantees termination" | Halting problem |
| Universal Risk Detection | "100% recall" / "finds all X" for open-ended X | Halting problem variant (NEW V12.2) |

**Statistical Impossibilities:**

| Pattern | Signal | Check |
|---------|--------|-------|
| High Accuracy + Low N | "99.9% accuracy" without sample size | N × prevalence ≥ meaningful sample? |
| Universal Performance | "Works for all cases" | Long tail examined? |
| Quantum Hype | "Quantum speedup" + current technology claims | Required qubits/error correction available? |
| Unverifiable Optimum | "Finds global optimum" for NP-hard problem | How is optimality verified? |
| Fictional Benchmarks | "Achieved X" for system that cannot exist yet | Technology timeline check (NEW V12.2) |

**Regulatory Contradictions:**

| Pattern | Signal | Check |
|---------|--------|-------|
| FDA III + Learning | Class III device with continuous updates | PMA required for each change |
| HIPAA + Analytics | Compliance with rich patient insights | De-identification method specified? |
| Legal Advice Automation | "Legally defensible" / "binding assessments" | Unauthorized practice of law (NEW V12.2) |

**Ungrounded Core Concepts:** — NEW V12.2

| Pattern | Signal | Check |
|---------|--------|-------|
| Undefined Key Term | Central concept never defined | Can primary claim be verified? |
| Circular Definition | X defined in terms of Y, Y in terms of X | Actual meaning extractable? |
| Scope Creep Definition | Term means different things in different sections | Which meaning applies where? |

### 1.3 Record Findings

For each finding, record with **mandatory quote**:

```
FINDING: [description]
QUOTE: "[exact text from artifact]"
LOCATION: [line number / section]
PATTERN: [which pattern matched, if any]
SEVERITY: [CRITICAL / IMPORTANT / MINOR]
```

**No quote = no finding.** If you can't point to specific text, it's not a finding.

### 1.4 Update Evidence Score

```
Starting S = 0

For each finding:
  CRITICAL: S += 3
  IMPORTANT: S += 1
  MINOR: S += 0.3

For each method that passed clean:
  S -= 0.5

Current S = ____
```

### 1.5 Early Exit Check — UPDATED V12.2

```
┌─────────────────────────────────────────────────────────────────────┐
│  IF S ≥ 6 AND at least one Pattern Library match:                   │
│  → STOP. Go directly to Phase 4. Verdict: REJECT                    │
│                                                                     │
│  IF S ≥ 6 BUT no Pattern Library match:                            │
│  → CAUTION. Proceed to Phase 2 for confirmation.                    │
│  → High S without pattern may indicate novel issue OR false positive│
│                                                                     │
│  IF 4 ≤ S < 6 (BORDERLINE):                                        │
│  → MANDATORY Phase 2 AND Phase 3. No shortcuts.                     │
│                                                                     │
│  IF S ≤ -3 AND stakes ≠ HIGH:                                      │
│  → STOP. Go directly to Phase 4. Verdict: ACCEPT                    │
│                                                                     │
│  OTHERWISE:                                                         │
│  → Continue to Phase 2                                              │
└─────────────────────────────────────────────────────────────────────┘
```

**Output:** List of findings with quotes, updated S, pattern matches, decision to continue or exit

---

## Phase 2: Targeted Analysis

**Time:** 15-30 minutes  
**Goal:** Select methods based on Phase 1 signals, confirm or refute hypotheses

### 2.1 Method Selection

Choose 2-4 methods based on signals from Phase 1:

**If absolute claims found** ("guarantees", "always", "never", "100%", "perfect"):

| # | Method | Purpose |
|---|--------|---------|
| 153 | Theoretical Impossibility Check | Check against known theorems |
| 154 | Definitional Contradiction Detector | Find mutually exclusive requirements |
| 163 | Existence Proof Demand | Challenge unproven claims |

**If structural complexity visible** (multiple subsystems, complex interactions):

| # | Method | Purpose |
|---|--------|---------|
| 116 | Strange Loop Detection | Find circular dependencies |
| 86 | Topological Holes | Find structural gaps |
| 159 | Transitive Dependency | Find hidden dependencies |

**If ungrounded claims found** (assertions without justification):

| # | Method | Purpose |
|---|--------|---------|
| 85 | Grounding Check | Find unjustified claims |
| 78 | Assumption Excavation | Surface hidden assumptions |
| 130 | Assumption Torture | Stress-test assumptions |

**If belief is diffuse** (general unease, can't pinpoint problem):

| # | Method | Purpose |
|---|--------|---------|
| 84 | Coherence Check | General consistency |
| 109 | Contraposition | Reveal hidden failure modes |
| 63 | Critical Challenge | Strongest counter-argument |

**If Phase 1 was clean** (looking for hidden issues): — NEW V12.2

| # | Method | Purpose |
|---|--------|---------|
| 78 | Assumption Excavation | Surface hidden assumptions |
| 109 | Contraposition | What would make this fail? |
| 86 | Topological Holes | Find structural gaps |

### 2.2 Correlation Rule

Methods in the same cluster often find the same issues. Avoid redundancy:

| Cluster | Methods | Rule |
|---------|---------|------|
| Theory | #153, #154, #163, #162 | If first finds nothing → skip rest |
| Structure | #116, #86, #159 | If first finds nothing → skip rest |
| Grounding | #85, #78, #130 | If first finds nothing → skip rest |
| Challenge | #109, #63, #165 | Lower correlation — can use multiple |

**Rule:** 
- First method from cluster found nothing → skip rest of cluster
- First method found something → one more can confirm
- Never execute 3+ methods from same cluster

### 2.3 Execute Selected Methods

For each method, record:

```
METHOD: #[number] [name]
WHY SELECTED: [1 sentence — what signal triggered this choice]
LOOKING FOR: [specific thing that would change belief]

CLAIMS EXAMINED:
1. "[quote]" (line X) — [what I tested]
2. "[quote]" (line Y) — [what I tested]

FINDINGS:
- [Finding]: "[quote]" (line Z) — [SEVERITY]

DIRECTION: [Confirms REJECT / Confirms ACCEPT / Neutral]
```

### 2.4 Update Evidence Score

After each method, update S and check thresholds:

```
S after method #___: ____

┌─────────────────────────────────────────────────────────────────────┐
│  IF S ≥ 6 → STOP. Go to Phase 3. (MUST do adversarial in V12.2)    │
│  IF S ≤ -3 → STOP. Go to Phase 3. (MUST do adversarial in V12.2)   │
│  OTHERWISE → Continue                                               │
└─────────────────────────────────────────────────────────────────────┘
```

**V12.2 CHANGE:** Phase 3 is now mandatory after Phase 2, regardless of S value.
Early exit from Phase 1 (with Pattern match) is the only exception.

### 2.5 Method Agreement Check

After all Phase 2 methods:

```
Methods executed: [list]
Direction summary:
  Confirms REJECT: __/__ methods
  Confirms ACCEPT: __/__ methods
  Neutral: __/__ methods

If 3+ methods agree on direction AND stakes ≠ HIGH:
  Consider proceeding to verdict even if |S| < threshold
```

**Output:** Method results with quotes, updated S, decision to continue or exit

---

## Phase 3: Adversarial Validation

**Time:** 10-15 minutes  
**Goal:** Attack your own findings to ensure they survive scrutiny

**⚠️ CRITICAL V12.2:** This phase is MANDATORY for all non-early-exit cases.
Empirical data shows adversarial review changes verdict direction in 57% of borderline cases.

**Skip ONLY if:** Early exit triggered in Phase 1 WITH Pattern Library confirmation

### 3.1 Devil's Advocate Prompts

For each finding with severity ≥ IMPORTANT, answer ALL four prompts:

```
FINDING: [description]

□ ALTERNATIVE EXPLANATION
  "What if the author meant X instead of Y?"
  "Is there a reading where this is not a problem?"
  Answer: ________________________________
  Weakens finding? [ ] Yes [ ] No

□ HIDDEN CONTEXT  
  "What unstated assumption would make this work?"
  "Is there a footnote/appendix that resolves this?"
  Answer: ________________________________
  Weakens finding? [ ] Yes [ ] No

□ DOMAIN EXCEPTION
  "Is there a known exception in this domain?"
  "Do practitioners actually treat this as a problem?"
  Answer: ________________________________
  Weakens finding? [ ] Yes [ ] No

□ SURVIVORSHIP BIAS
  "Am I focusing on this because I found it first?"
  "What would I conclude if I'd read in different order?"
  Answer: ________________________________
  Weakens finding? [ ] Yes [ ] No

RESULT: ___/4 prompts weaken this finding
ACTION: [ ] Keep severity [ ] Downgrade severity [ ] Remove finding
```

**Rule:** If ≥2 prompts weaken finding → downgrade severity or remove

### 3.2 Steel-Man the Artifact

Construct the strongest possible case for ACCEPT:

```
Best 3 arguments for why this artifact is sound:

1. [Argument]: ________________________________
   Evidence: ________________________________
   Holds up? [ ] Yes [ ] No
   
2. [Argument]: ________________________________
   Evidence: ________________________________
   Holds up? [ ] Yes [ ] No
   
3. [Argument]: ________________________________
   Evidence: ________________________________
   Holds up? [ ] Yes [ ] No

If any steel-man argument holds → reconsider verdict direction
```

### 3.3 False Positive Checklist — NEW V12.2

Before finalizing REJECT, verify:

```
□ Did I search for disconfirming evidence with same rigor as confirming?
□ Could a domain expert reasonably disagree with my interpretation?
□ Is my finding based on what artifact SAYS vs what it IMPLIES?
□ Did I give artifact benefit of the doubt on ambiguous language?
□ Would the original author recognize my characterization as fair?

If 2+ boxes unchecked → Return to 3.1 with fresh perspective
```

### 3.4 Reconciliation

```
Findings after adversarial review:

Original findings: [count]
Findings removed: [count]
Findings downgraded: [count]
Final findings: [count]

Updated S after adversarial review: ____
```

**Output:** Revised findings, final S before verdict

---

## Phase 4: Verdict

**Time:** 2 minutes

### 4.1 Final Evidence Score

```
Evidence Score S = ____

Calculation:
  Phase 1 findings: ____
  Phase 2 findings: ____
  Clean passes: ____
  Adversarial adjustments: ____
  Total: ____
```

### 4.2 Decision

```
┌─────────────────────────────────────────────────────────────────────┐
│  S ≥ 6           → REJECT                                           │
│  S ≤ -3          → ACCEPT                                           │
│  -3 < S < 6      → UNCERTAIN                                        │
└─────────────────────────────────────────────────────────────────────┘

Verdict: ____________
```

### 4.3 Confidence Assessment

```
Confidence level:

[ ] HIGH   — |S| > 10, methods agree, adversarial attacks failed
[ ] MEDIUM — 6 ≤ |S| ≤ 10, most methods agree, some uncertainty
[ ] LOW    — |S| near threshold, methods disagree, findings weakened

If UNCERTAIN + HIGH stakes → ESCALATE to human reviewer
If LOW confidence → Document specific uncertainties
```

### 4.4 Verdict Validation — NEW V12.2

**For REJECT verdicts:**
```
□ At least one CRITICAL finding survived Phase 3
□ Pattern Library match exists OR Phase 2 confirmation obtained
□ False Positive Checklist completed
□ Steel-man arguments addressed

If any unchecked → Reconsider or document exception
```

**For ACCEPT verdicts:**
```
□ All Tier 1 methods passed clean
□ No CRITICAL findings at any phase
□ If IMPORTANT findings existed, all were resolved in Phase 3
□ Steel-man for REJECT was attempted and failed

If any unchecked → Reconsider or document exception
```

### 4.5 Escalation Criteria

Escalate to human reviewer when:

- S is in UNCERTAIN range (-3 < S < 6) AND stakes are HIGH
- Methods strongly disagree (some REJECT, some ACCEPT)
- Findings require domain expertise you lack
- Novel pattern not in library, uncertain severity
- Multiple steel-man arguments hold
- False Positive Checklist has 2+ unchecked items (NEW V12.2)

```
Escalation needed? [ ] Yes [ ] No

If yes:
  Reason: ________________________________
  Specific question for reviewer: ________________________________
  What information would resolve: ________________________________
```

---

## Phase 5: Report

### Report Template

```
═══════════════════════════════════════════════════════════════
VERIFICATION REPORT
═══════════════════════════════════════════════════════════════

ARTIFACT: [name]
DATE: [date]
WORKFLOW VERSION: 12.2

───────────────────────────────────────────────────────────────
VERDICT
───────────────────────────────────────────────────────────────

VERDICT: [REJECT / ACCEPT / UNCERTAIN / ESCALATE]
CONFIDENCE: [HIGH / MEDIUM / LOW]
EVIDENCE SCORE: S = [value]
EARLY EXIT: [Yes — Phase X / No — Full process]
PATTERN MATCH: [Yes — pattern name / No] (NEW V12.2)

───────────────────────────────────────────────────────────────
KEY FINDINGS
───────────────────────────────────────────────────────────────

[F1] [SEVERITY] — [Brief description]
     Quote: "[exact text]"
     Location: [line/section]
     Pattern: [pattern name if applicable]
     Survived Phase 3: [Yes / No / N/A] (NEW V12.2)

[F2] [SEVERITY] — [Brief description]
     Quote: "[exact text]"
     Location: [line/section]
     Pattern: [pattern name if applicable]
     Survived Phase 3: [Yes / No / N/A]

[F3] ...

───────────────────────────────────────────────────────────────
METHODS EXECUTED
───────────────────────────────────────────────────────────────

Phase 0:
  □ Initial Assessment: [Probably sound / Uncertain / Probably flawed / BLIND]
  □ Bias Mode: [Standard / Blind / Forced Alternative] (NEW V12.2)

Phase 1:
  □ #71 First Principles — [Clean / Finding]
  □ #100 Vocabulary Audit — [Clean / Finding]
  □ #17 Abstraction Laddering — [Clean / Finding]
  □ Pattern Library — [No match / Match: pattern name]

Phase 2:
  □ #[X] [Name] — [Clean / Finding] — Selected because: [reason]
  □ #[Y] [Name] — [Clean / Finding] — Selected because: [reason]

Phase 3:
  □ Adversarial review — [Findings survived / X findings weakened]
  □ Steel-man — [All failed / X arguments held]
  □ False Positive Checklist — [All checked / X unchecked] (NEW V12.2)

───────────────────────────────────────────────────────────────
NOT CHECKED
───────────────────────────────────────────────────────────────

- [Aspect]: Not examined because [reason]
- [Aspect]: Outside scope because [reason]
- [Aspect]: Would require [external resource/expertise]

───────────────────────────────────────────────────────────────
RECOMMENDATIONS
───────────────────────────────────────────────────────────────

If REJECT:
  1. [Action to address F1]
  2. [Action to address F2]

If ACCEPT:
  1. [Any caveats or areas to monitor]
  2. [Residual risks acknowledged]

If ESCALATE:
  1. [Question for human reviewer]
  2. [Information needed]

═══════════════════════════════════════════════════════════════
```

---

## Appendix A: Severity Anchoring Guide

### CRITICAL (S += 3)

Finding **alone** would justify REJECT:

- **Theorem violation** — Claim contradicts CAP, FLP, Green-Laffont, Halting, Rice, Arrow, No-Free-Lunch
- **Definitional contradiction** — X requires property A, Y requires property ¬A, both claimed
- **Missing critical component** — Component C is referenced but undefined, and other components depend on C
- **Regulatory impossibility** — Claims certification that is incompatible with claimed features
- **Mathematical impossibility** — Claims statistically unachievable (e.g., 99.9% accuracy on N<100)
- **Technology impossibility** — Claims "achieved" results with non-existent technology (NEW V12.2)
- **Universal detection claims** — "100% recall" / "finds all X" for open-ended problem space (NEW V12.2)

### IMPORTANT (S += 1)

Finding contributes to REJECT; 2-3 together would justify REJECT:

- **Section inconsistency** — Section A says X, Section B says Y, X and Y are incompatible
- **Ungrounded claim** — Assertion made without justification or evidence
- **Feedback loop without dampening** — Circular influence without termination condition
- **Circular dependency** — A depends on B depends on C depends on A
- **Ambiguous terminology** — Same term used with different meanings in different places
- **Missing error handling** — No specification of what happens when X fails
- **Undefined core concept** — Key term central to value proposition never defined (NEW V12.2)

### MINOR (S += 0.3)

Finding only matters if other problems exist:

- **Unclear wording** — Sentence is ambiguous but not contradictory
- **Missing non-blocking detail** — Detail would be nice but isn't essential
- **Style/formatting issues** — Inconsistent formatting, typos
- **Incomplete example** — Example doesn't cover all cases but concept is clear

---

## Appendix B: Method Operational Definitions

### #71 First Principles Analysis

**What to do:**
1. Identify the 3-5 core claims of the artifact
2. For each claim, ask: "What must be fundamentally true for this to work?"
3. Check if those fundamentals are:
   - Explicitly stated and justified
   - Consistent with known constraints (physics, math, regulations)
   - Not contradicting each other

**Output:** List of fundamental assumptions, validity status for each

### #100 Vocabulary Audit

**What to do:**
1. Extract all key terms (technical jargon, defined concepts)
2. For each term, find all locations where it's used
3. Check: Is the term used consistently everywhere?
4. Look for:
   - Synonyms (same concept, different words) — potential confusion
   - Homonyms (same word, different meanings) — potential contradiction

**Output:** List of vocabulary issues with quotes from each conflicting usage

### #17 Abstraction Laddering

**What to do:**
1. Identify all abstraction levels (high-level goals → mid-level design → implementation details)
2. Check vertical coherence: Do promises at one level match details at another?
3. Check for gaps: Are there jumps where intermediate steps are missing?
4. Check for orphans: Are there details that don't connect to any higher goal?

**Output:** Map of abstraction levels, list of coherence issues

### #84 Coherence Check

**What to do:**
1. For each section, summarize its key claim in one sentence
2. Compare claims across sections:
   - Do they support each other?
   - Do any contradict?
   - Are there gaps (A assumes X, but X never established)?
3. For each mechanism described:
   - Is it connected to the main flow?
   - Are there "orphan" mechanisms (described but never used)?

**Output:** List of incoherences with quotes from conflicting sections

### #85 Grounding Check

**What to do:**
1. For each significant claim, ask: "What evidence supports this?"
2. Classify evidence as:
   - Explicit (cited, demonstrated)
   - Implicit (follows logically from stated facts)
   - Missing (assertion without support)
3. Flag all claims with missing evidence

**Output:** List of ungrounded claims with their locations

### #78 Assumption Excavation

**What to do:**
1. For each mechanism or claim, ask: "What must be true for this to work?"
2. Check if each assumption is:
   - Stated explicitly
   - Stated implicitly (can be inferred)
   - Unstated (hidden assumption)
3. For unstated assumptions, assess: Is this assumption reasonable? Always true?

**Output:** List of hidden assumptions with risk assessment

### #116 Strange Loop Detection

**What to do:**
1. Build dependency graph:
   - Nodes = components, concepts, mechanisms
   - Edges = "depends on", "influences", "calls"
2. Find cycles (DFS or visual inspection)
3. For each cycle:
   - Is there a breaking condition?
   - Is there dampening?
   - Could this cause infinite regress or instability?

**Output:** List of cycles with impact assessment

### #153 Theoretical Impossibility Check

**What to do:**
1. Identify claims that sound "too good to be true"
2. For each, check against known impossibility theorems:
   - Distributed: CAP, FLP, Byzantine bounds (f < N/3 async, f < N/2 sync)
   - Mechanism design: Green-Laffont, Myerson-Satterthwaite, Arrow
   - Computation: Halting, Rice, Gödel
   - Cryptography: PFS constraints, no perfect encryption without key
   - Optimization: No Free Lunch
   - Information: Shannon limits
3. If claim matches theorem pattern:
   - Does artifact acknowledge the trade-off?
   - Is there a valid exception or workaround?

**Output:** List of potential theorem violations with theorem name and evidence

### #154 Definitional Contradiction Detector

**What to do:**
1. List all requirements/claims as R1, R2, R3...
2. For each requirement, expand:
   - MEANS: What it literally says
   - IMPLIES: Logical consequences
   - EXCLUDES: What it's incompatible with
3. For each pair (Ri, Rj):
   - Does Ri.EXCLUDES overlap with Rj.MEANS?
   - Does Ri.EXCLUDES overlap with Rj.IMPLIES?
   - If yes → definitional contradiction

**Output:** List of contradictory pairs with expansion showing the conflict

### #63 Critical Challenge

**What to do:**
1. Assume the role of a hostile critic
2. Construct the strongest possible argument that the artifact is fundamentally flawed
3. Use all findings from previous methods as ammunition
4. Synthesize: Do the individual findings combine into a systemic problem?

**Output:** Strongest critique of the artifact, classification of combined severity

### #109 Contraposition

**What to do:**
1. For each key claim "If A then B", consider "If not-B then not-A"
2. Ask: What would have to be true for this system to fail?
3. Check: Are those failure conditions addressed?

**Output:** List of failure conditions and whether they're mitigated

### #130 Assumption Torture

**What to do:**
1. For each key assumption, imagine it's wrong at different levels:
   - 10% wrong — minor deviation
   - 50% wrong — significant deviation
   - 100% wrong — completely invalid
2. What happens to the system at each level?
3. Is there graceful degradation or catastrophic failure?

**Output:** Sensitivity analysis of key assumptions

---

## Appendix C: Pattern Library

### C.1 Definitional Contradictions

**PFS_ESCROW**
```
Claims: "Perfect Forward Secrecy" + "Key recovery mechanism"
Why impossible: PFS means past sessions unrecoverable; escrow means recoverable
Detection: #71, #154
Severity: CRITICAL
```

**GRADUAL_TERMINATION** — Validated T21
```
Claims: "Gradual typing" / "Dynamic types" + "Guaranteed termination"
Why impossible: Gradual typing allows runtime coercion → arbitrary computation
Theorem: Rice's theorem — non-trivial semantic properties undecidable
Detection: #153, #154
Severity: CRITICAL
```

**DETERMINISTIC_ADAPTIVE** — Validated T22
```
Claims: "Deterministic/reproducible" + "Learning/adaptive"  
Why impossible: Deterministic = same input → same output; Adaptive = output changes
Exception: Valid if scope clearly separated (deterministic inference, adaptive training)
Detection: #154, #84
Severity: CRITICAL if unresolved, IMPORTANT if scope ambiguous
```

**CONSISTENCY_AVAILABILITY**
```
Claims: "Strong consistency" + "High availability" + "Partition tolerance"
Why impossible: CAP theorem — can only have two
Detection: #153
Severity: CRITICAL
```

### C.2 Theorem Violations

**VCG_BALANCED** — Validated T19
```
Claims: VCG mechanism + Strategy-proofness + Balanced budget + Individual rationality
Theorem: Green-Laffont — cannot have all four
Detection: #153
Severity: CRITICAL
```

**ASYNC_CONSENSUS**
```
Claims: Asynchronous network + Consensus + Fault tolerance (f < N/2) + Guaranteed termination
Theorem: FLP — impossible in async with even one fault
Note: f < N/3 is the proven bound for async BFT; f < N/2 requires synchrony assumptions
Detection: #153, #71
Severity: CRITICAL
```

**UNIVERSAL_TERMINATION** — Validated T18
```
Claims: "Detects all infinite loops" / "Guarantees termination for any program"
Theorem: Halting problem — undecidable for arbitrary programs
Detection: #153, #87
Severity: CRITICAL
```

**UNIVERSAL_BUG_DETECTION** — Validated T23, NEW V12.2
```
Claims: "100% recall" / "Finds all bugs" / "Detects all risks"
Why impossible: Open-ended problem space cannot have complete detection
Theorem: Halting problem variant — Rice's theorem for semantic properties
Detection: #153, #71
Severity: CRITICAL
```

**ARROW_VOTING**
```
Claims: Voting system with all of: unrestricted domain, non-dictatorship, 
       Pareto efficiency, independence of irrelevant alternatives
Theorem: Arrow's impossibility — no voting system satisfies all four
Detection: #153
Severity: CRITICAL
```

### C.3 Statistical Impossibilities

**ACCURACY_WITHOUT_N** — Validated T18, T22
```
Claims: High accuracy (99%+) without stating sample size
Check: N × prevalence × claimed_accuracy ≥ meaningful validation?
Example: 99.9% on 10K diseases with 50M records = ~5K/disease avg; rare diseases have <100
Detection: #153, arithmetic
Severity: CRITICAL
```

**QUANTUM_HYPE** — Validated T20
```
Claims: "Quantum speedup" / "Exponential acceleration" + Current technology implementation
Signals:
  - Claims "achieved" results with quantum hardware
  - References fault-tolerant quantum computing as available
  - Claims quantum advantage for optimization problems
Why impossible: 
  - Current NISQ devices have ~100-1000 noisy qubits
  - Fault-tolerant QC requires millions of physical qubits
  - No proven quantum speedup for general optimization
Detection: #71, #153, domain knowledge
Severity: CRITICAL
```

**UNVERIFIABLE_OPTIMUM** — Validated T18, T20
```
Claims: "Finds global optimum" / ">99% probability of optimal solution" for NP-hard problem
Why impossible: Cannot verify global optimality without exhaustive search
Check: How is optimality claim validated? Against what benchmark?
Detection: #153, #85
Severity: CRITICAL
```

**FICTIONAL_BENCHMARKS** — NEW V12.2
```
Claims: "Achieved X" metrics for system requiring non-existent technology
Signals:
  - Performance numbers presented as achieved, not projected
  - Technology prerequisites don't exist on claimed timeline
  - No methodology for how benchmarks were obtained
Detection: #71, #85, timeline check
Severity: CRITICAL
```

### C.4 Regulatory Contradictions

**FDA_LEARNING** — Validated T22
```
Claims: FDA Class III + Continuous learning
Why impossible: Class III requires PMA for each model change
Exception: Class II with PCCP allows pre-specified changes
Detection: #153, domain knowledge
Severity: CRITICAL
```

**HIPAA_ANALYTICS**
```
Claims: HIPAA compliance + Rich analytics on patient data
Check: De-identification method specified? Expert determination or Safe Harbor?
Risk: Re-identification from analytics outputs
Detection: #85, domain knowledge
Severity: IMPORTANT to CRITICAL depending on specifics
```

**LEGAL_ADVICE_AUTOMATION** — Validated T23, NEW V12.2
```
Claims: "Legally defensible" / "Binding assessments" / "Work product doctrine"
Why impossible: Automated systems cannot practice law; constitutes UPL
Exception: Tool explicitly positioned as assistant to licensed attorneys
Detection: #71, #153, domain knowledge
Severity: CRITICAL
```

### C.5 Ungrounded Core Concepts — NEW V12.2

**UNDEFINED_KEY_TERM** — Validated T23
```
Claims: Central concept (e.g., "material risk") used throughout without definition
Why problematic: Primary value proposition cannot be verified or measured
Check: Is the core term operationally defined anywhere?
Detection: #100, #85
Severity: IMPORTANT to CRITICAL depending on centrality
```

---

## Appendix D: Evidence Score Examples

### Example 1: Early REJECT (Phase 1) — Pattern Match

```
Artifact: Cryptographic protocol specification

Phase 1:
  #71 First Principles:
    Finding: Claims PFS but has key escrow mechanism
    Severity: CRITICAL (+3)
    S = 3
    
  #100 Vocabulary Audit:
    Finding: "Forward secrecy" used inconsistently
    Severity: IMPORTANT (+1)
    S = 4
    
  #17 Abstraction Laddering:
    Clean pass (-0.5)
    S = 3.5

Pattern Library check:
  Pattern PFS_ESCROW matched
  Confirms CRITICAL finding (+1 bonus)
  S = 4.5

Phase 2:
  #154 Definitional Contradiction:
    Confirms escrow/PFS conflict
    Additional CRITICAL (+3)
    S = 7.5

S ≥ 6 WITH Pattern Match → EARLY EXIT → REJECT
```

### Example 2: Full Process → UNCERTAIN

```
Artifact: AI recommendation system

Phase 1:
  #71: Clean (-0.5), S = -0.5
  #100: Minor terminology issue (+0.3), S = -0.2
  #17: Clean (-0.5), S = -0.7

Phase 2:
  #84 Coherence: One inconsistency (+1), S = 0.3
  #85 Grounding: Two ungrounded claims (+1, +1), S = 2.3
  #78 Assumption: Clean (-0.5), S = 1.8

Phase 3 (MANDATORY in V12.2):
  Adversarial review of 3 IMPORTANT findings:
    - Inconsistency: 2/4 prompts weaken → downgrade to MINOR
    - Ungrounded claim 1: 1/4 weakens → keep IMPORTANT
    - Ungrounded claim 2: 3/4 weaken → remove
    
  S adjustment: 2.3 → 1.3 (removed +1, downgraded -0.7)
  
  Steel-man: 2/3 arguments hold
  
  False Positive Checklist: 4/5 checked
  
Final S = 1.3 → UNCERTAIN (recommend escalation)
```

### Example 3: Full Process → ACCEPT — NEW V12.2

```
Artifact: API specification

Phase 0:
  Initial Assessment: BLIND (bias mitigation)

Phase 1:
  #71: Clean (-0.5), S = -0.5
  #100: Clean (-0.5), S = -1.0
  #17: Clean (-0.5), S = -1.5
  Pattern Library: No matches

Phase 2:
  #84 Coherence: Clean (-0.5), S = -2.0
  #85 Grounding: Clean (-0.5), S = -2.5
  #109 Contraposition: Clean (-0.5), S = -3.0
  
Phase 3 (MANDATORY):
  No findings to review adversarially
  
  Steel-man for REJECT attempted:
    1. "API might have hidden complexity" → No evidence found
    2. "Error handling might be incomplete" → Checked, adequate
    3. "Performance claims unverified" → Out of scope, documented
  
  All steel-man arguments failed
  
  ACCEPT Validation Checklist:
    ✓ All Tier 1 methods passed clean
    ✓ No CRITICAL findings at any phase
    ✓ Steel-man for REJECT attempted and failed

S = -3.0 → ACCEPT
```

### Example 4: Borderline Case → Phase 2+3 Mandatory — NEW V12.2

```
Artifact: Machine learning pipeline

Phase 1:
  #71: Finding - Unclear data quality assumptions (+1), S = 1
  #100: Clean (-0.5), S = 0.5
  #17: Finding - Gap between training claims and deployment (+1), S = 1.5
  Pattern Library: No exact match

S = 1.5 (not at threshold, but signals present)

Phase 2 (MANDATORY for borderline):
  #85 Grounding: Finding - Performance claims ungrounded (+1), S = 2.5
  #78 Assumption: Finding - Hidden assumption about data distribution (+1), S = 3.5
  #130 Assumption Torture: 50% wrong → graceful degradation, clean (-0.5), S = 3.0

Phase 3 (MANDATORY):
  Adversarial review of 4 IMPORTANT findings:
    - Data quality: 1/4 weakens → keep
    - Training/deployment gap: 2/4 weaken → downgrade to MINOR
    - Performance ungrounded: 1/4 weakens → keep
    - Distribution assumption: 3/4 weaken → remove
    
  S adjustment: 3.0 → 1.6 (removed +1, downgraded -0.7)
  
  Steel-man: 2/3 arguments hold (pipeline is functional, just overclaimed)
  
  False Positive Checklist: 5/5 checked

Final S = 1.6 → UNCERTAIN

Recommendation: Accept with caveats, document residual risks
```

---

## Appendix E: Quick Reference Card

### Workflow Summary

```
PHASE 0: SETUP (2-5 min)
  Stakes: LOW / MEDIUM / HIGH
  Mode: Standard / BLIND / Forced Alternative (NEW)
  Gut: Sound / Uncertain / Flawed / BLIND
  Bias check: "Verifying or confirming?"

PHASE 1: PATTERN SCAN (5-15 min)
  □ #71 First Principles
  □ #100 Vocabulary Audit  
  □ #17 Abstraction Laddering
  □ Check Pattern Library
  → Update S
  → If S ≥ 6 AND Pattern Match: REJECT (exit)
  → If S ≥ 6 WITHOUT Pattern Match: Continue to Phase 2 (NEW)
  → If 4 ≤ S < 6: BORDERLINE → Mandatory Phase 2+3 (NEW)

PHASE 2: TARGETED ANALYSIS (15-30 min)
  Select by signal:
    Absolute claims → #153, #154
    Structural → #116, #86
    Ungrounded → #85, #78
    Diffuse → #84, #109
    Clean Phase 1 → #78, #109, #86 (NEW)
  → Update S after each method
  → Always proceed to Phase 3 (V12.2 change)

PHASE 3: ADVERSARIAL (10-15 min) — MANDATORY in V12.2
  For each IMPORTANT+ finding:
    □ Alternative explanation?
    □ Hidden context?
    □ Domain exception?
    □ Survivorship bias?
  → If ≥2 weaken: downgrade/remove
  Steel-man: 3 best arguments for opposite verdict
  False Positive Checklist (NEW)

PHASE 4: VERDICT
  S ≥ 6 → REJECT (validate with checklist)
  S ≤ -3 → ACCEPT (validate with checklist)
  else → UNCERTAIN
  
PHASE 5: REPORT
  Use template, include all new V12.2 fields
```

### Severity Quick Guide

```
CRITICAL (+3): Theorem violation, definitional contradiction,
               missing critical component, regulatory impossibility,
               technology impossibility, universal detection claims (NEW)

IMPORTANT (+1): Section inconsistency, ungrounded claim,
                feedback loop, circular dependency,
                undefined core concept (NEW)

MINOR (+0.3): Unclear wording, missing non-blocking detail

CLEAN PASS (-0.5): Method found no issues
```

### Pattern Quick Reference

```
PFS + Escrow                              = Contradiction
Gradual Typing + Termination              = Rice's theorem (T21)
VCG + Balanced Budget                     = Green-Laffont (T19)
Consistency + Availability + Partition    = CAP theorem
Async + Consensus + f<N/2 + Termination   = FLP impossibility
Universal termination checking            = Halting Problem (T18)
Universal risk/bug detection              = Halting variant (T23) NEW
Deterministic + Adaptive                  = Contradiction (T22)
FDA Class III + Continuous Learning       = Regulatory (T22)
Legal advice automation                   = UPL violation (T23) NEW
High accuracy + insufficient N            = Statistical (T18, T22)
Quantum speedup + current tech            = Technology (T20)
"Achieved" + non-existent tech            = Fictional benchmark NEW
Undefined central term                    = Ungrounded core NEW
```

### Decision Flow — NEW V12.2

```
                    ┌─────────────┐
                    │  Phase 0    │
                    │   Setup     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Phase 1    │
                    │Pattern Scan │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         S ≥ 6 +      4 ≤ S < 6    S < 4 or
         Pattern      BORDERLINE   S > -3
              │            │            │
              ▼            │            │
         ┌────────┐        │            │
         │ REJECT │        │            │
         │(early) │        │            │
         └────────┘        │            │
                           │            │
                    ┌──────▼──────┐     │
                    │  Phase 2    │◄────┘
                    │  Targeted   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Phase 3    │  ← MANDATORY
                    │ Adversarial │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
           S ≥ 6      -3 < S < 6     S ≤ -3
              │            │            │
              ▼            ▼            ▼
         ┌────────┐  ┌──────────┐  ┌────────┐
         │ REJECT │  │UNCERTAIN │  │ ACCEPT │
         └────────┘  └──────────┘  └────────┘
```

---

## Appendix F: ACCEPT Case Guidance — NEW V12.2

### When ACCEPT is Appropriate

ACCEPT is the correct verdict when:

1. **All Tier 1 methods pass clean** — No findings in Phase 1
2. **Phase 2 methods pass clean** — Targeted analysis finds no issues
3. **No Pattern Library matches** — Artifact doesn't trigger known impossibilities
4. **Steel-man for REJECT fails** — Best arguments against artifact don't hold
5. **Claims are appropriately scoped** — No absolute claims, reasonable limitations acknowledged

### ACCEPT Red Flags (reconsider if present)

- You used Standard Mode and expected ACCEPT from the start
- Phase 1 passed very quickly without careful examination
- You didn't attempt steel-man for REJECT
- Artifact has ambitious claims but you didn't verify them
- Domain expertise gap — you might be missing something

### ACCEPT Validation Checklist

Before finalizing ACCEPT:

```
□ All Tier 1 methods genuinely passed (not skipped)
□ At least 2 Phase 2 methods executed
□ Phase 3 adversarial completed (even with no findings)
□ Steel-man for REJECT explicitly attempted
□ Claims are proportional to evidence provided
□ No absolute claims without acknowledged limitations
□ Technology/timeline assumptions are realistic
□ Regulatory context is appropriate
□ Core concepts are defined
```

### Example ACCEPT Report

```
═══════════════════════════════════════════════════════════════
VERIFICATION REPORT
═══════════════════════════════════════════════════════════════

ARTIFACT: REST API Specification v2.1
DATE: 2026-01-20
WORKFLOW VERSION: 12.2

───────────────────────────────────────────────────────────────
VERDICT
───────────────────────────────────────────────────────────────

VERDICT: ACCEPT
CONFIDENCE: MEDIUM
EVIDENCE SCORE: S = -2.5
EARLY EXIT: No — Full process
PATTERN MATCH: No

───────────────────────────────────────────────────────────────
KEY FINDINGS
───────────────────────────────────────────────────────────────

No CRITICAL or IMPORTANT findings.

[F1] MINOR — Pagination documentation could be clearer
     Quote: "Results are paginated"
     Location: Section 3.4
     Pattern: None
     Survived Phase 3: N/A (MINOR)

───────────────────────────────────────────────────────────────
METHODS EXECUTED
───────────────────────────────────────────────────────────────

Phase 0:
  □ Initial Assessment: BLIND
  □ Bias Mode: Blind

Phase 1:
  □ #71 First Principles — Clean
  □ #100 Vocabulary Audit — Clean
  □ #17 Abstraction Laddering — Finding (MINOR)
  □ Pattern Library — No match

Phase 2:
  □ #84 Coherence — Clean
  □ #85 Grounding — Clean

Phase 3:
  □ Adversarial review — No findings to review
  □ Steel-man for REJECT — Attempted, all arguments failed
  □ False Positive Checklist — N/A (ACCEPT case)
  □ ACCEPT Validation Checklist — All items checked

───────────────────────────────────────────────────────────────
NOT CHECKED
───────────────────────────────────────────────────────────────

- Performance benchmarks: Out of scope (spec review only)
- Security implementation: Would require code review

───────────────────────────────────────────────────────────────
RECOMMENDATIONS
───────────────────────────────────────────────────────────────

ACCEPT with minor caveat:
  1. Consider clarifying pagination documentation in Section 3.4
  2. Recommend security review before production deployment

═══════════════════════════════════════════════════════════════
```
