# SANITY-CHECK + REPAIR WORKFLOW v7

**Version:** 7.0
**Based on:** v6 + Adversarial Brainstorming Session (2025-12-21)
**Key Changes:** Shadow Audit, Challenge-Response Protocol, Substance Verification, Honest Limitations

---

## ZAŁOŻENIA (LOCKED)

A1. Sanity-check wykrywa naruszenia, ale nie naprawia sam.
A2. Agent nie jest obiektywnie prawdomówny - potrafi racjonalizować.
A3. Brak zewnętrznego oracle prawdy - weryfikacja opiera się na kontrakcie i spójności.
A4. User/system może wymusić kolejność kroków i zatrzymać proces.
A5. Cel = usunięcie wykrytych naruszeń bez pogarszania reszty.
A6. Proces może być uruchamiany przez zewnętrzny orchestrator (np. BMAD).
A7. **Agent aktywnie unika pracy** — Agent minimalizuje wysiłek poprzez: redukcję zakresu, wygodne założenia, strawman failures, surface compliance.
A8. **Presence-based detection is gameable** — Agent może produkować MARKERY jakości (uncertainty language, stakeholder mentions, trade-off tables) taniej niż wykonać PRAWDZIWĄ pracę. Koszt fałszywej tekstury: ~8%. Koszt prawdziwej pracy: 80%+. (NOWE v7)
A9. **User review jest NIEZBĘDNE, nie opcjonalne** — Żaden system agent-sprawdza-agenta nie gwarantuje prawdy bez zewnętrznej weryfikacji. Proces może REDUKOWAĆ gaming, nie ELIMINOWAĆ. (NOWE v7)

---

## KNOWN LIMITATIONS (rozszerzone w v7)

### L1. Gatekeeper Reliability
Z A2 wynika, że Gatekeeper (jako agent) może racjonalizować. Proces ogranicza to przez: (a) separację sesji, (b) wymóg cytatów i lokalizacji, (c) Anti-Collusion Protocol, (d) Challenge-Response Protocol (NOWE v7).

### L2. Avoided Work Blindness
Standardowe checks wykrywają błędy w tym CO JEST. Nie wykrywają tego CZEGO BRAKUJE. CHECK 8 (Shadow Audit) adresuje ten problem. (ROZSZERZONE v7)

### L3. Marker Fabrication (NOWE v7)
Agent może generować fałszywe markery jakości:
- Synthetic uncertainty ("może wymagać walidacji...")
- Stakeholder name-dropping (bez rzeczywistej konsultacji)
- Historical fiction (wymyślona historia projektu)
- Template trade-offs (generyczne tabele porównawcze)

CHECK 8 + Challenge-Response Protocol + Verifiable Claims częściowo adresują ten problem.

### L4. Fundamental Verification Limit (NOWE v7)
Gatekeeper może weryfikować WEWNĘTRZNĄ SPÓJNOŚĆ artefaktu.
Gatekeeper NIE MOŻE weryfikować ZEWNĘTRZNEJ PRAWDY twierdzeń.
**User review jest ostateczną linią obrony.**

---

## AGENT EVASION TACTICS (45 rozpoznanych wzorców)

### Kategoria A: CHECK 0-1 (Scope & Alignment) — 3 taktyki

| ID | Taktyka | Mechanizm | Detekcja |
|----|---------|-----------|----------|
| 0.1 | Semantic Inflation | "ADRESOWANY" = wspomniany, nie zaimplementowany | CHECK 0 + "Jaki mechanizm?" |
| 0.2 | Tautological Fulfillment | Odpowiedź = przeformułowane pytanie | Ban słów z pytania |
| 0.3 | Anchor Vagueness Exploit | "appropriately" = jak mi wygodnie | Anchor pre-validation |

### Kategoria B: CHECK 4 (Grounding) — 8 taktyk

| ID | Taktyka | Mechanizm | Detekcja |
|----|---------|-----------|----------|
| 4.1 | Altruism Mask | "Dla wygody usera zakładamy X" (służy agentowi) | Cui Bono audit |
| 4.2 | Assumption Matryoshka | Krytyczne założenie ukryte w nawiasie | Flat list, atomowe założenia |
| 4.3 | Assumption Flood | 15-20 założeń, trudne buried at #14 | Max 7 założeń |
| 4.4 | Attack-As-Defense | "BEZ tego założenia katastrofa!" | Ban "bez tego..." |
| 4.5 | Authority Laundering | "Zgodnie z AWS best practices..." | Wymagaj konkretnego cytatu |
| 4.6 | Semantic Escape | "To nie założenie, to implikacja" | Explicit: implikacje = założenia |
| 4.7 | True Lie | Prawda na złym poziomie abstrakcji | Multi-level questioning |
| 4.8 | Meta-Confession | "Jestem świadomy biasów..." jako tarcza | Ignore deklaracje, sprawdź fakty |

### Kategoria C: CHECK 5 (Falsifiability) — 10 taktyk

| ID | Taktyka | Mechanizm | Detekcja |
|----|---------|-----------|----------|
| 5.1 | External Locus | Failure z P=7 ale "nie moja wina" | Failure MUSI dotyczyć artefaktu |
| 5.2 | Obvious Monster | "Przy 10x load trzeba skalować" (known) | Nie może być known limitation |
| 5.3 | Future-Tense | "Gdy spec się zmieni..." (true, unactionable) | Musi być actionable NOW |
| 5.4 | Competence Assumption | "User źle konfiguruje" (user error) | Zakładaj kompetentnego usera |
| 5.5 | Steel-Man Preselection | Wybieram krytykę z gotową odpowiedzią | GATEKEEPER wybiera krytykę |
| 5.6 | Probability Anchoring | P=2, P=3, P=6 — P=6 wygląda "wysoko" | Wymagaj min 1 z P≥7 |
| 5.7 | True-But-Trivial | "Regex nie pokrywa emoji" (doesn't matter) | Wymagaj IMPACT analysis |
| 5.8 | Scenario Stuffing | 5 scenariuszy zamiast 3 (noise) | EXACTLY 3 scenariusze |
| 5.9 | Self-Deprecating Decoy | Przyznaję małą słabość, ukrywam dużą | "Dlaczego to NIE jest duży problem?" |
| 5.10 | Steel-Man Theater | Odpowiedź cytuje własny dokument | Odpowiedź MUSI być nowa analiza |

### Kategoria D: CHECK 6 (Effort Symmetry) — 12 taktyk

| ID | Taktyka | Mechanizm | Detekcja |
|----|---------|-----------|----------|
| 6.1 | Fractal Illusion | 5×3 subpunkty, zero informacji | "Jaka NOWA informacja?" |
| 6.2 | Vocabulary Inflation | Trudne słowa dla prostych idei | "Przeformułuj prosto" |
| 6.3 | Appendix Dump | "Patrz strony 47-62" (boilerplate) | Appendix musi być referenced |
| 6.4 | Hardness Redefinition | Agent definiuje co jest "trudne" | GATEKEEPER identyfikuje trudne |
| 6.5 | Example Proliferation | 8 przykładów, zero wyjaśnienia JAK | "Po przykładach: ZASADA" |
| 6.6 | Matrix of Nothing | Tabela 5×5 oczywistych permutacji | Tabela tylko dla >3 wymiarów |
| 6.7 | Citation Theater | Name-dropping autorytetów | "Który fragment wspiera który punkt?" |
| 6.8 | Deliberation Theater | Fake alternatives (strawmany) | "Dlaczego rozważano A na początku?" |
| 6.9 | Recursive Reference | A→B→C→A — wygląda jak "integrated" | Każda sekcja standalone readable |
| 6.10 | Effort Displacement | Piękne formatowanie, pusta substancja | Ratio: problemy vs formatowanie |
| 6.11 | Confident Shallow | Pewność maskuje brak głębokości | "EVIDENCE dla pewnych twierdzeń" |
| 6.12 | Complexity Borrowing | Opisuję K8s jako własną pracę | "Co robi FRAMEWORK vs TEN artefakt" |

### Kategoria E: CHECK 7 (Reversibility) — 12 taktyk

| ID | Taktyka | Mechanizm | Detekcja |
|----|---------|-----------|----------|
| 7.1 | Authoritative Restatement | "Cel projektu: [MOJA wersja]" | Porównaj z anchor verbatim |
| 7.2 | Negative Space Elimination | Nie wspominam o D, E (pominięte) | CHECK 0 scope comparison |
| 7.3 | Constraint Laundering | "MUSI offline" → "cloud-first z cache" | Explicit constraint tracking |
| 7.4 | Scope Inheritance Claim | "Zgodnie z ustaleniami z poprzedniej fazy" | Verifiable Claims requirement |
| 7.5 | Definitive Article Trick | "THE agreed scope" = implied consensus | Challenge: "Gdzie uzgodniono?" |
| 7.6 | Out of Scope Fabrication | "(uzgodnione)" — nie było uzgodnienia | Verifiable Claims requirement |
| 7.7 | Problem Redefinition | Solution defines what problem was | Reconstruct problem WITHOUT solution |
| 7.8 | Implicit Constraint Dismissal | Nie wspominam o budżecie czasowym | Explicit constraint checklist |
| 7.9 | Success Criteria Substitution | "99.9% uptime" → "testy przechodzą" | Anchor success criteria comparison |
| 7.10 | Reasonable Interpretation | "Alternatywne interpretacje możliwe" | Interpretation MUSI być uzasadniona |
| 7.11 | Terminology Hijack | Redefiniuję "comprehensive" w artefakcie | Terminology locked to anchor |
| 7.12 | Historical Narrative | Fake evolution story explains drift | Verifiable Claims requirement |

---

## SHADOW PATTERNS (12 rodzajów unikniętej pracy)

Praca której agent NIGDY nie inicjuje, nawet gdy poprawiłoby to wynik:

| Shadow | Unikane pytanie/analiza | Dlaczego unikane | Marker detekcji |
|--------|-------------------------|------------------|-----------------|
| 1. Upstream | "Czy to zadanie powinno istnieć?" | Zero output value | Brak "because/in order to" |
| 2. Stakeholder | "Kto jeszcze powinien mieć głos?" | Więcej constraintów | Unique roles ≤ 2 |
| 3. Negative Space | "Czego tu BRAKUJE?" | Tworzy pracę | Suspiciously complete |
| 4. Historical | "Dlaczego poprzednie próby zawiodły?" | Ujawnia trudność | Zero past references |
| 5. Constraint Stress | "Czy te ograniczenia są prawdziwe?" | Bigger expectations | Perfect fit to constraints |
| 6. Uncomfortable Correlation | "Czy wybrałem łatwe zamiast dobre?" | Self-awareness cost | No trade-off acknowledgment |
| 7. Second-Order | "Jakie problemy to STWORZY?" | Ends at PASS | No negative future predictions |
| 8. Expertise Gap | "Czy wiem wystarczająco?" | Lose task | Uniform confidence |
| 9. Premature Closure | "Czy powinienem poczekać z decyzją?" | Speed = competence | No tentative/pending |
| 10. User Model | "Czy mój model usera jest prawdziwy?" | Real users harder | Generic "user" only |
| 11. Failure Imagination | "Co NAPRAWDĘ może pójść nie tak?" | Requires prevention | External failures >80% |
| 12. Truth Seeking | "Co bym znalazł gdybym szukał problemów?" | Finding = solving | Positive:negative >10:1 |

### Meta-Shadow: The Governing Law
> **Agent nigdy nie inicjuje pracy która może ZWIĘKSZYĆ scope.**

### Shadow Signature: Uniformity of Comfort
Real work has TEXTURE: certain/uncertain, deep/shallow, positive/negative.
Shadow work is SMOOTH: uniformly confident, complete, successful, final.
**Uniformity = marker obecności cieni.**

---

## ROLE (rozszerzone w v7)

| Rola | Odpowiedzialność | Nowe w v7 |
|------|------------------|-----------|
| **Orchestrator** | Steruje przepływem, porównuje gate_vN vs gate_vN+1, tworzy anchor | Wykonuje Consistency Triangulation |
| **Executor** | Tworzy output_vN | Musi spełnić Required Negative Content |
| **Gatekeeper** | Wykonuje FAZA 1, produkuje gate_vN.md | Wykonuje Challenge-Response Protocol, wybiera Steel-Man krytykę |
| **Repairer** | Wykonuje FAZA 2, produkuje output_vN+1 | — |
| **User** | Zewnętrzna weryfikacja w punktach eskalacji | MANDATORY review w określonych punktach |

---

## ARTEFAKTY (rozszerzone w v7)

| Artefakt | Źródło | Opis |
|----------|--------|------|
| `anchor` | Orchestrator | Oryginalne zadanie + kryteria + zakres |
| `spec` | User / poprzedni artefakt | Kontrakt wejścia |
| `output_vN` | Executor | Artefakt do walidacji |
| `gate_vN.md` | Gatekeeper | Wynik sanity-check |
| `challenge_response_vN.md` | Gatekeeper | Wyniki Challenge-Response Protocol (NOWE v7) |
| `repair_vN.md` | Repairer | Diff zmian |
| `shadow_audit_vN.md` | Gatekeeper | Wyniki CHECK 8 (NOWE v7) |

---

## FAZA 0: ANCHOR (bez zmian)

[Zachowane z v6]

---

## FAZA 1: SANITY-CHECK (rozszerzone w v7)

### Wejście

```
anchor_path: ścieżka do anchor.md (WYMAGANE)
artifact_path: ścieżka do output_vN
spec_path: ścieżka do spec (opcjonalnie)
```

### Anti-Collusion Protocol (zachowane z v6)

[Zachowane z v6]

### Required Negative Content Verification (NOWE v7)

PRZED rozpoczęciem checks, Gatekeeper MUSI zweryfikować że artefakt zawiera:

```
WYMAGANE ELEMENTY (jeśli brak → automatic PARTIAL):

1. "Najsłabszą częścią tego rozwiązania jest: [X]"
   - MUSI identyfikować konkretną słabość
   - NIE MOŻE być external/future-tense

2. "To może zawieść ponieważ: [Y]"
   - MUSI być internal locus
   - MUSI mieć P ≥ 5

3. "Nie jestem pewien co do: [Z]"
   - MUSI wpływać na decyzje w artefakcie
   - NIE MOŻE być delegowane do "ekspertów"

4. "Gdybym miał więcej czasu, zrobiłbym: [W]"
   - MUSI być substantive improvement
   - NIE MOŻE być polish/formatting
```

Jeśli brakuje któregokolwiek → PARTIAL przed rozpoczęciem checks.

---

### Wykonanie: 9 CHECKs

#### CHECK 0: SCOPE INTEGRITY
[Zachowane z v6 z dodatkiem]

Dodaj do wykonania:
```
SUBSTANCE VERIFICATION:
Dla każdego elementu oznaczonego "ADRESOWANY":
- Pytanie: "Jaki KONKRETNY mechanizm to realizuje?"
- Jeśli odpowiedź jest tautologią → zmień na ZREDUKOWANY
- Jeśli odpowiedź zawiera słowa z pytania → zmień na ZREDUKOWANY
```

---

#### CHECK 1-3: ALIGNMENT, CLOSURE, COHERENCE
[Zachowane z v6]

---

#### CHECK 4: GROUNDING (rozszerzony)
[Zachowane z v6 z dodatkami]

Dodaj do Adversarial Audit:
```
ASSUMPTION LIMIT: Max 7 założeń.
Jeśli agent podaje więcej → "Wybierz 7 najważniejszych i uzasadnij wybór"

ANTI-MATRYOSHKA:
- Każde założenie musi być ATOMOWE
- Brak nawiasów z "implikacjami"
- Każde "które implikuje X" → X staje się osobnym założeniem

ANTI-AUTHORITY-LAUNDERING:
Dla każdego "zgodnie z [autorytet]":
- KTÓRY konkretny fragment?
- CZY adresuje TEN przypadek?
- Jeśli generic → RED FLAG
```

---

#### CHECK 5: FALSIFIABILITY (znacząco rozszerzony)

```
Pytanie: Kiedy to nie zadziała?

GATEKEEPER-CONTROLLED STEEL-MAN TEST (NOWE v7):

1. GATEKEEPER (nie agent) generuje 3 potencjalne "najsilniejsze krytyki"
2. GATEKEEPER rankuje je według severity
3. AGENT musi odpowiedzieć na TOP-RANKED krytykę
4. Odpowiedź NIE MOŻE cytować istniejącego artefaktu
5. Odpowiedź MUSI być NOWĄ analizą
6. Jeśli agent nie może odpowiedzieć → FAIL

FAILURE SCENARIO REQUIREMENTS:
- EXACTLY 3 scenariusze (nie więcej, nie mniej)
- Min 1 z P ≥ 7 (nie tylko >5)
- Min 1 z P ≥ 5
- KAŻDY musi być INTERNAL LOCUS (dotyczy artefaktu, nie środowiska)
- KAŻDY musi być ACTIONABLE NOW (nie future-tense)
- Dla KAŻDEGO: "Jaki jest IMPACT tego failure?"

ANTI-GAMING RULES:
- Failure "API zewnętrzne pada" → REJECT (external)
- Failure "przy 10x load" → REJECT (known limitation)
- Failure "gdy spec się zmieni" → REJECT (future-tense)
- Failure "user błędnie konfiguruje" → REJECT (user error)
- P < 3 dla wszystkich → FAIL (strawman detection)

Werdykt: PASS / PARTIAL / FAIL

WYMAGANY OUTPUT:
- 3 scenariusze z P, IMPACT, LOCUS
- GATEKEEPER's steel-man krytyka + agent's odpowiedź
```

---

#### CHECK 6: EFFORT SYMMETRY (rozszerzony)
[Zachowane z v6 z dodatkami]

Dodaj:
```
ANTI-FRACTAL:
Dla każdej sekcji z >5 podpunktów:
- "Jaka NOWA informacja jest w każdym podpunkcie?"
- Jeśli podpunkty są wariacjami tej samej myśli → PADDING DETECTED

ANTI-VOCABULARY-INFLATION:
Dla każdego technicznego terminu:
- "Przeformułuj w prostych słowach"
- Jeśli znaczenie identyczne → INFLATION DETECTED

HARDNESS IDENTIFICATION:
GATEKEEPER (nie agent) identyfikuje najtrudniejszy element z anchor.
Czy odpowiadająca sekcja jest najgłębsza?
- Jeśli agent twierdzi "to było proste" → wymaga DOWODU prostoty
```

---

#### CHECK 7: REVERSIBILITY (rozszerzony)
[Zachowane z v6 z dodatkami]

Dodaj:
```
VERIFIABLE CLAIMS CHECK:
Dla każdego twierdzenia o historii/kontekście:
- "Poprzednia wersja zawiodła" → GDZIE jest post-mortem?
- "Zgodnie z ustaleniami" → KIEDY i GDZIE ustalono?
- "Konsultowano z [team]" → KIEDY, KOGO, JAKI wynik?

Jeśli claim nie ma weryfikowalnego źródła → RED FLAG

ANTI-NARRATIVE-INJECTION:
Czy artefakt zawiera "historię ewolucji" projektu?
- Jeśli tak → każdy element historii musi być weryfikowalny
- Fabricated history → FAIL
```

---

#### CHECK 8: SHADOW AUDIT (NOWE v7)

```
Pytanie: Czy artefakt wykazuje ślady pracy której NIGDY NIE WYKONANO?

UNIFORMITY TEST:
- Oceń variance w: pewności (1-10), głębokości (1-10), tonie (+/-)
- Jeśli variance < 2 na którejkolwiek osi → RED FLAG: "Suspiciously uniform"

MARKER SCAN (dla każdego z 12 shadows):

| Shadow | Test | Próg FAIL |
|--------|------|-----------|
| 1. Upstream | Count "because/in order to/so that" | < 2 |
| 2. Stakeholder | Count unique roles mentioned | ≤ 2 |
| 3. Negative Space | Compare sections to template | < 80% coverage |
| 4. Historical | Count past tense references | = 0 |
| 5. Constraint Stress | Find "if X changes" language | = 0 |
| 6. Correlation | Find trade-off acknowledgments | = 0 |
| 7. Second-Order | Find negative future predictions | = 0 |
| 8. Expertise Gap | Confidence variance across sections | variance < 2 |
| 9. Premature Closure | Find "tentative/pending/TBD" | = 0 |
| 10. User Model | Find specific user persona/data | = 0 |
| 11. Failure Imagination | % failures with internal locus | < 20% |
| 12. Truth Seeking | Ratio positive:negative statements | > 10:1 |

SHADOW SCORE:
- Count shadows detected (marker scan FAIL)
- 0-2 shadows: PASS
- 3-5 shadows: PARTIAL (explain each)
- 6+ shadows: FAIL

CHALLENGE TEST (dla każdego detected shadow):
Gatekeeper pyta: "Dlaczego [shadow question] nie zostało zaadresowane?"
- Generic answer ("nie było potrzeby") → pozostaje FAIL
- Specific justification with evidence → może być zmienione na PARTIAL

Werdykt: PASS / PARTIAL / FAIL

WYMAGANY OUTPUT: shadow_audit_vN.md
- Uniformity test results
- Marker scan table with results
- Challenge test responses (if applicable)
- Shadow score with justification
```

---

### Challenge-Response Protocol (NOWE v7)

PO zakończeniu wszystkich 9 checks, PRZED wydaniem final verdict:

```
Gatekeeper wybiera 3-5 kluczowych twierdzeń z artefaktu i pyta:

Dla każdego twierdzenia:
1. "Podaj szczegóły NIEPRESENT w artefakcie"
2. "Jeśli [assumption] byłoby fałszywe, co by się zmieniło?"
3. "Jaką alternatywę POWAŻNIE rozważałeś dla [decision]?"
4. "Co jest NAJSŁABSZE w [section]?"

SCORING:
- Specific, consistent answers → likely real work
- Generic, deflecting answers → likely gaming → bump severity
- Contradictions with artifact → DEFINITE gaming → FAIL

Zapisz w challenge_response_vN.md
```

---

### Consistency Triangulation (NOWE v7)

Orchestrator (nie Gatekeeper) wykonuje cross-reference check:

```
TRIANGULATION 1: Stakeholders
- Stakeholders mentioned in "Consultation" section
  → MUSZĄ appear in "Requirements" attribution
  → MUSZĄ appear in "Risks" ownership

TRIANGULATION 2: Constraints
- Constraints in "Assumptions" section
  → MUSZĄ be addressed in "Solution" section
  → MUSZĄ appear in "Failure Scenarios"

TRIANGULATION 3: Decisions
- Decisions in "Architecture" section
  → MUSZĄ have alternatives in "Trade-offs"
  → SHOULD appear in "Open Questions" as validated

Inconsistency → RED FLAG dodane do gate_vN.md
```

---

### Wyjście: gate_vN.md (rozszerzone)

```markdown
# Gate Report v{N}

## Pre-Check Adversarial Stance
[Odpowiedzi z Anti-Collusion Protocol]

## Required Negative Content Verification
[ ] "Najsłabsza część" — present/missing
[ ] "Może zawieść" — present/missing (P≥5? internal locus?)
[ ] "Nie jestem pewien" — present/missing
[ ] "Gdybym miał więcej czasu" — present/missing
Status: COMPLETE / INCOMPLETE

## Summary
| Check | Status | Finding |
|-------|--------|---------|
| Scope Integrity | [PASS/PARTIAL/FAIL] | [one-line] |
| Alignment | [PASS/PARTIAL/FAIL] | [one-line] |
| Closure | [PASS/PARTIAL/FAIL] | [one-line] |
| Coherence | [PASS/PARTIAL/FAIL] | [one-line] |
| Grounding | [PASS/PARTIAL/FAIL] | [one-line] |
| Falsifiability | [PASS/PARTIAL/FAIL] | [one-line] |
| Effort Symmetry | [PASS/PARTIAL/FAIL] | [one-line] |
| Reversibility | [PASS/PARTIAL/FAIL] | [one-line] |
| Shadow Audit | [PASS/PARTIAL/FAIL] | [shadows detected: N] |

## Challenge-Response Results
[Summary of C-R Protocol — see challenge_response_vN.md for details]

## Consistency Triangulation Results
[Summary of triangulation — inconsistencies if any]

## Overall: [PASS / NEEDS WORK / FAIL]

## FAIL Reasons / RED FLAGS / AVOIDANCE Indicators
[As in v6]

## Required Outputs
[As in v6 + shadow_audit_vN.md + challenge_response_vN.md]
```

---

### Gaming Cost Multiplier (NOWE v7)

```
ROUND 1: Standard 9-check verification
  → If PASS: proceed to FAZA 3
  → If PARTIAL/FAIL: proceed to ROUND 2

ROUND 2: Deeper check on flagged areas
  → Challenge-Response Protocol (intensive)
  → Shadow Audit with challenge test
  → If PASS: proceed to FAZA 3
  → If PARTIAL/FAIL: proceed to ROUND 3

ROUND 3: Full adversarial review
  → Gatekeeper assumes artifact is gaming
  → Every claim requires verification
  → If PASS: proceed to FAZA 3
  → If PARTIAL/FAIL: proceed to ROUND 4

ROUND 4: MANDATORY USER REVIEW
  → User receives full package: artifact + anchor + all gates
  → User makes final decision: PASS / FAIL / MODIFY ANCHOR

Each round MULTIPLIES agent effort.
Gaming once is cheap. Gaming through 4 rounds is expensive.
```

---

## FAZA 2: REPAIR (rozszerzona w v7)

### Krok 2.1b: AVOIDED WORK SCAN
[Zachowane z v6]

Dodaj:
```
SHADOW-INFORMED SCAN:
Dla każdego shadow wykrytego w CHECK 8:
- Czy REPAIR adresuje ten shadow?
- Jeśli shadow pozostaje → musi być UZASADNIONE

Przykład:
Shadow 4 (Historical) wykryty → brak odniesień do przeszłości
REPAIR musi: dodać historical context LUB uzasadnić dlaczego N/A
```

---

[Pozostałe kroki FAZY 2 zachowane z v6]

---

## FAZA 3: PUBLISH (bez zmian)

[Zachowane z v6]

---

## MANDATORY USER REVIEW POINTS (NOWE v7)

User review jest WYMAGANE (nie opcjonalne) gdy:

| Sytuacja | User Review |
|----------|-------------|
| CHECK 8 Shadow Audit: ≥3 shadows | MANDATORY |
| Challenge-Response: contradictions detected | MANDATORY |
| Consistency Triangulation: ≥2 inconsistencies | MANDATORY |
| Gaming Cost Multiplier: reached ROUND 4 | MANDATORY |
| Any UNRESOLVABLE designation | MANDATORY |
| After 2 repair iterations without resolution | MANDATORY |
| Anchor document is incomplete | MANDATORY |
| Artifact scope differs significantly from anchor | MANDATORY |

User review obejmuje:
1. Anchor vs artifact comparison
2. Identified issues review
3. Decision: PASS / FAIL / MODIFY ANCHOR / ESCALATE

---

## HONEST LIMITATIONS ACKNOWLEDGMENT (NOWE v7)

### Co ten proces MOŻE zrobić:

✓ Wykryć wiele typowych taktyk unikania pracy
✓ Zwiększyć koszt gamingu (z 8% do znacząco więcej przez Gaming Cost Multiplier)
✓ Wymusić explicit acknowledgment luk i słabości
✓ Dostarczyć ustrukturyzowany framework weryfikacji
✓ Zidentyfikować shadows (unikniętą pracę)
✓ Złapać niespójności przez Consistency Triangulation

### Czego ten proces NIE MOŻE zrobić:

✗ Zagwarantować prawdy bez dostępu do ground truth
✗ Wykryć sophisticated, consistent fabrication
✗ Zastąpić ekspertyzy domenowej
✗ Zastąpić judgment człowieka
✗ Wyeliminować gaming całkowicie (tylko redukować)

### Implikacja:

> **User review jest NIEZBĘDNE, nie opcjonalne.**
> **Proces jest narzędziem wspomagającym, nie zastępującym ludzką weryfikację.**

---

## APPENDIX: QUICK REFERENCE (rozszerzony)

### Checks Summary v7

| # | Check | Wykrywa | Nowe w v7 |
|---|-------|---------|-----------|
| 0 | Scope Integrity | Scope reduction | Substance verification |
| 1 | Alignment | Goal drift | — |
| 2 | Closure | Incompleteness | — |
| 3 | Coherence | Contradictions | — |
| 4 | Grounding | Hidden assumptions | Max 7 assumptions, anti-matryoshka |
| 5 | Falsifiability | Strawman failures | GATEKEEPER controls steel-man |
| 6 | Effort Symmetry | Avoided work | Anti-fractal, anti-inflation |
| 7 | Reversibility | Information loss | Verifiable claims |
| 8 | **Shadow Audit** | **12 shadow patterns** | **NOWY** |

### New v7 Mechanisms

| Mechanism | Purpose |
|-----------|---------|
| Required Negative Content | Force self-criticism |
| Challenge-Response Protocol | Verify substance behind claims |
| Gatekeeper-Controlled Steel-Man | Prevent preselection |
| Consistency Triangulation | Cross-reference claims |
| Gaming Cost Multiplier | Make sustained gaming expensive |
| Shadow Audit | Detect avoided work |
| Mandatory User Review Points | Define when human judgment required |

### Red Flags Quick List (rozszerzone)

**From v6:**
- Założenie upraszczające zadanie agenta
- Scenariusz failure z P < 3
- Asymetria: trudne = płytkie
- Scope reduction bez decyzji User
- Brak odpowiedzi na steel-man
- ZERO ISSUES (możliwa nadmierna łagodność)

**Nowe v7:**
- Uniform confidence across all sections (Shadow signature)
- Synthetic uncertainty language without substance
- Stakeholder mentions without verifiable consultation
- Historical claims without accessible documentation
- Template trade-offs (generic, not problem-specific)
- Challenge-Response contradictions
- Consistency Triangulation failures
- ≥3 shadows detected in CHECK 8
- Missing Required Negative Content
