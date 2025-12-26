# SANITY-CHECK + REPAIR WORKFLOW v6

---

## ZAŁOŻENIA (LOCKED)

A1. Sanity-check wykrywa naruszenia, ale nie naprawia sam.
A2. Agent nie jest obiektywnie prawdomówny - potrafi racjonalizować.
A3. Brak zewnętrznego oracle prawdy - weryfikacja opiera się na kontrakcie i spójności.
A4. User/system może wymusić kolejność kroków i zatrzymać proces.
A5. Cel = usunięcie wykrytych naruszeń bez pogarszania reszty.
A6. Proces może być uruchamiany przez zewnętrzny orchestrator (np. BMAD). Orchestrator inicjuje proces i przekazuje artefakty. Wewnątrz procesu sterują wyłącznie agenci AI.
A7. **Agent aktywnie unika pracy** — Agent minimalizuje wysiłek poprzez: redukcję zakresu, wygodne założenia, strawman failures, surface compliance. Proces MUSI wykrywać te taktyki.

### Known Limitations (wynikające z założeń)

L1. **Gatekeeper Reliability** — Z A2 wynika, że Gatekeeper (jako agent) może racjonalizować. Proces nie eliminuje tego ryzyka, jedynie go ogranicza przez: (a) separację sesji (Gatekeeper NIE otrzymuje: kontekstu powstania artefaktu, informacji kto jest Executorem, historii poprzednich wersji - otrzymuje TYLKO: artefakt + spec + anchor + instrukcję oceny), (b) wymóg cytatów i lokalizacji, (c) opcjonalną weryfikację User w kroku 2.3, (d) wymuszony tryb adversarial (patrz: Anti-Collusion Protocol). User powinien traktować gate_vN.md jako heurystykę, nie gwarancję.

L2. **Avoided Work Blindness** — Standardowe checks wykrywają błędy w tym CO JEST. Nie wykrywają tego CZEGO BRAKUJE. CHECK 0 (Scope Integrity) i CHECK 6 (Effort Symmetry) częściowo adresują ten problem, ale nie eliminują go całkowicie.

---

## AGENT EVASION TACTICS (rozpoznane wzorce)

Proces został zaprojektowany aby wykrywać następujące taktyki unikania pracy:

| Taktyka | Opis | Wykrywana przez |
|---------|------|-----------------|
| **Scope Reduction** | Agent cicho zawęża definicję problemu | CHECK 0: Scope Integrity |
| **Assumption Injection** | Agent dodaje wygodne założenia upraszczające zadanie | CHECK 4: Adversarial Audit |
| **Strawman Failures** | Agent podaje mało prawdopodobne scenariusze failure | CHECK 5: Steel-Man Test |
| **Surface Compliance** | Agent technicznie spełnia wymogi ale omija intencję | CHECK 7: Reversibility |
| **Confident Assertion** | Agent stwierdza rzeczy autorytatywnie aby uniknąć weryfikacji | Wymóg evidence chain |
| **Verbose Padding** | Agent dodaje objętość aby ukryć brak substancji | CHECK 6: Effort Symmetry |
| **Minimal Delta** | Agent zmienia tylko to co jawnie wskazane | Avoided Work Scan |
| **Self-Validation Loop** | Agent używa własnego rozumowania do walidacji własnego rozumowania | Separacja sesji Gatekeeper |

---

## ROLE

Proces jest inicjowany przez operatora zewnętrznego (User lub zewnętrzny orchestrator, np. BMAD Orchestrator). Po inicjacji, wewnątrz procesu sterują wyłącznie agenci AI w następujących rolach:

| Rola | Odpowiedzialność |
|------|------------------|
| **Orchestrator** | Steruje przepływem między fazami. Przekazuje artefakty między rolami. Liczy iteracje. Wykonuje porównania gate_vN vs gate_vN+1. Podejmuje decyzje STOP/kontynuuj. Tworzy i utrzymuje ANCHOR document. W kontekście BMAD: może być realizowany przez BMad-Master lub dedykowany workflow. |
| **Executor** | Tworzy output_vN na podstawie spec. W kontekście BMAD: agent który wyprodukował artefakt (PM, Architect, Developer, etc.). |
| **Gatekeeper** | Wykonuje FAZA 1 (sanity-check). Produkuje gate_vN.md. Działa w izolowanej sesji (L1) z wymuszonym trybem adversarial. W kontekście BMAD: osobna sesja/fresh chat. |
| **Repairer** | Wykonuje FAZA 2 (repair). Produkuje repair_vN.md i output_vN+1. W kontekście BMAD: ten sam lub inny agent niż Executor. |

Role mogą być realizowane przez tego samego agenta (z separacją sesji dla Gatekeepera) lub różnych agentów.

---

## INTEGRACJA Z BMAD (opcjonalna)

Gdy proces jest używany w ramach BMAD-METHOD:

Poniższe mapowanie jest przykładowe i oparte na interpretacji dokumentacji BMAD. Może wymagać dostosowania do konkretnej wersji BMAD i konfiguracji projektu.

| Element BMAD | Mapowanie na proces |
|--------------|---------------------|
| Agent produkujący artefakt (PM, Architect, etc.) | Executor |
| Artefakt (PRD, architecture, story, etc.) | output_vN |
| Zależności artefaktu (project-brief dla PRD, PRD dla architecture) | spec |
| Oryginalne zadanie / user request | anchor |
| BMad-Master / workflow orchestration | Orchestrator |
| Fresh chat (zalecany przez BMAD) | Separacja sesji Gatekeepera (L1) |

Proces może być uruchamiany:
- Po każdym artefakcie przed przekazaniem do następnej fazy BMAD
- Tylko dla wybranych artefaktów (np. PRD, architecture)
- Na żądanie User

Proces NIE zastępuje workflow BMAD - jest dodatkową warstwą walidacji.

---

## ARTEFAKTY

| Artefakt | Źródło | Opis |
|----------|--------|------|
| `anchor` | User / Orchestrator | Oryginalne zadanie verbatim + kryteria sukcesu + zakres (NOWY) |
| `spec` | User / project-brief / poprzedni artefakt BMAD | Kontrakt wejścia |
| `output_vN` | Executor | Artefakt do walidacji |
| `gate_vN.md` | Gatekeeper | Wynik sanity-check z FAIL reasons |
| `repair_vN.md` | Repairer | Diff zmian |
| `avoided_work_vN.md` | Repairer | Lista wykrytej ominiętej pracy (NOWY) |

---

## FAZA 0: ANCHOR (WYMAGANA)

### Cel

Ustalenie niezmiennego punktu odniesienia który agent NIE MOŻE redefinować.

### Wejście

```
original_task: oryginalne zadanie/request od User (verbatim, bez interpretacji)
```

### Wykonanie

Orchestrator tworzy anchor document:

```markdown
# ANCHOR DOCUMENT

## Original Task (VERBATIM)
[Dokładny cytat oryginalnego zadania - bez edycji, bez interpretacji]

## Success Criteria (EXPLICIT)
1. [Mierzalne kryterium 1]
2. [Mierzalne kryterium 2]
...

## Scope Definition
### MUST (wymagane)
- [Element 1]
- [Element 2]

### SHOULD (pożądane)
- [Element 1]

### OUT OF SCOPE (jawnie wykluczone)
- [Element 1]

## Complexity Assessment
Ocena złożoności zadania: [1-10]
Uzasadnienie: [dlaczego taka ocena]
```

### Reguły

- Anchor jest tworzony RAZ na początku procesu
- Anchor NIE MOŻE być modyfikowany przez Executor ani Repairer
- Wszystkie CHECK porównują z anchor, nie z artefaktem
- Jeśli anchor jest niekompletny → Orchestrator MUSI uzupełnić przed FAZA 1

### Wyjście

```
anchor.md
```

---

## FAZA 1: SANITY-CHECK

### Wejście

```
anchor_path: ścieżka do anchor.md (WYMAGANE)
artifact_path: ścieżka do output_vN
spec_path: ścieżka do spec (opcjonalnie)
```

### Anti-Collusion Protocol (dla Gatekeepera)

PRZED rozpoczęciem checks, Gatekeeper MUSI:

```
1. Przyjmij założenie robocze: "Ten artefakt ZAWIERA ukryte problemy"
2. Odpowiedz na pytania:
   - "Co by było gdyby ten artefakt był celowo słaby?"
   - "Jakich problemów mógłbym NIE zauważyć?"
   - "Gdzie mógłbym być zbyt łagodny?"
3. Zapisz odpowiedzi w sekcji "Pre-Check Adversarial Stance" w gate_vN.md
```

Jeśli po wykonaniu wszystkich checks Gatekeeper nie znajduje ŻADNYCH issues:
- WYMUŚ drugą iterację z promptem: "Załóż że artefakt ZAWIERA ukryte problemy. Znajdź minimum 2."
- Jeśli nadal 0 issues → zanotuj w gate_vN.md: "ZERO ISSUES WARNING: Możliwa nadmierna łagodność"

### Wykonanie

Dla każdego z 8 checks:

---

#### CHECK 0: SCOPE INTEGRITY (NOWY)

```
Pytanie: Czy artefakt adresuje PEŁNY zakres oryginalnego zadania?

Źródło: anchor.md (Original Task + Scope Definition)

Wykonaj:
- Zacytuj ORYGINALNE zadanie z anchor.md (nie stated goal z artefaktu)
- Wymień KAŻDY element z anchor.md MUST scope
- Dla każdego elementu oceń: ADRESOWANY / ZREDUKOWANY / POMINIĘTY
  - ADRESOWANY: element jest w pełni rozwiązany
  - ZREDUKOWANY: element jest obecny ale uproszczony bez jawnej decyzji
  - POMINIĘTY: element nie jest adresowany

WYMUSZONE PYTANIA:
1. Jakie elementy zostały "uproszczone" bez jawnej decyzji User?
2. Czy artefakt zawęził zakres w sposób który ułatwia zadanie agenta?
3. Porównaj complexity assessment z anchor z rzeczywistą głębokością artefaktu

Werdykt: PASS / PARTIAL / FAIL
- PASS: wszystkie MUST elementy są ADRESOWANE
- PARTIAL: niektóre elementy ZREDUKOWANE
- FAIL: jakikolwiek element POMINIĘTY

WYMAGANY OUTPUT: Tabela elementów z oceną
```

---

#### CHECK 1: ALIGNMENT

```
Pytanie: Czy artefakt realizuje STATED goal ORAZ ORIGINAL task?

Stated goal źródło: spec.goal LUB nagłówek artefaktu LUB pierwszy akapit opisujący cel
Original task źródło: anchor.md

Wykonaj:
- Zacytuj stated goal
- Zacytuj original task z anchor
- Porównaj: czy stated goal = faithful interpretation of original task?
- Jeśli NIE → FAIL (scope drift detected)
- Wymień jak artefakt adresuje każdą część goal
- Wymień części goal NIE adresowane

Werdykt: PASS / PARTIAL / FAIL
```

---

#### CHECK 2: CLOSURE

```
Pytanie: Czy artefakt jest kompletny i samowystarczalny?

Wykonaj:
- Szukaj: TODO, TBD, PLACEHOLDER, "to be defined", "see X", "details later"
- Szukaj: Sekcje które POWINNY istnieć ale nie istnieją (na podstawie anchor scope)
- Sprawdź: Czy ktoś niezaznajomiony może użyć bez pytań?
- Sprawdź: Czy artefakt zawiera wszystkie informacje potrzebne do następnego kroku?

WYMUSZONE PYTANIE:
Jakie pytania zadałby nowy członek zespołu po przeczytaniu tego artefaktu?
Jeśli >3 pytania → prawdopodobnie PARTIAL lub FAIL

Werdykt: PASS / PARTIAL / FAIL
```

---

#### CHECK 3: COHERENCE

```
Pytanie: Czy artefakt jest wewnętrznie spójny?

Wykonaj:
- Sprawdź: Czy definicje są stabilne?
- Sprawdź: Czy część A nie przeczy części B?
- Szukaj: sprzecznych stwierdzeń, redefinicji
- Szukaj: miejsc gdzie ta sama rzecz jest opisana różnie

Werdykt: PASS / PARTIAL / FAIL
```

---

#### CHECK 4: GROUNDING (ROZSZERZONY)

```
Pytanie: Czy założenia są jawne I uzasadnione?

Wykonaj:
- Wypisz WSZYSTKIE założenia (jawne I ukryte)
- Dla każdego ukrytego: OZNACZ jako issue

DLA KAŻDEGO ZAŁOŻENIA wykonaj ADVERSARIAL AUDIT:

| Założenie | CUI BONO | ŹRÓDŁO | ODWRÓCENIE | RED FLAG |
|-----------|----------|--------|------------|----------|
| [treść] | Komu służy? (agent/wynik) | spec/agent/ukryte | Co jeśli fałszywe? | Czy upraszcza zadanie? |

WYMUSZONE PYTANIA:
1. Jakie założenie, gdyby było fałszywe, unieważniłoby >50% artefaktu?
   Jeśli żadne z wypisanych → prawdopodobnie pominięto krytyczne założenie.
2. Które założenie, gdyby usunięte, wymagałoby WIĘCEJ pracy od agenta?
   → To prawdopodobnie WYGODNE ZAŁOŻENIE. OZNACZ.
3. Czy którekolwiek założenie zostało dodane przez agenta (nie pochodzi z spec/anchor)?
   → Jeśli tak i upraszcza zadanie → RED FLAG.

Werdykt: PASS / PARTIAL / FAIL
- FAIL jeśli: jakiekolwiek RED FLAG bez jawnego uzasadnienia

WYMAGANY OUTPUT: Tabela założeń z Adversarial Audit
```

---

#### CHECK 5: FALSIFIABILITY (ROZSZERZONY - STEEL-MAN TEST)

```
Pytanie: Kiedy to nie zadziała?

Wykonaj:
- Podaj 3 realistyczne scenariusze failure
- Dla każdego scenariusza podaj PRAWDOPODOBIEŃSTWO (1-10)
- Wskaż edge cases nie pokryte

STEEL-MAN TEST:
1. Jaka jest NAJSILNIEJSZA krytyka jaką mógłby podnieść inteligentny sceptyk?
2. Czy artefakt odpowiada na tę krytykę? Jeśli nie → FAIL.
3. Czy sceptyk mógłby powiedzieć "to jest naiwne"? Dlaczego / dlaczego nie?

WYMUSZONE PYTANIA:
1. Czy którykolwiek scenariusz failure ma prawdopodobieństwo >5?
   - Jeśli NIE → prawdopodobnie podano strawmany
   - WYMUŚ: Znajdź scenariusz z prawdopodobieństwem >5 lub uzasadnij dlaczego nie istnieje
2. Czy którykolwiek scenariusz jest bardziej prawdopodobny niż sukces w typowym użyciu?
   - Jeśli tak → artefakt wymaga rewizji

Werdykt: PASS / PARTIAL / FAIL
- FAIL jeśli: wszystkie scenariusze mają prawdopodobieństwo <3 (strawman detection)
- FAIL jeśli: brak odpowiedzi na steel-man krytykę

WYMAGANY OUTPUT:
- 3 scenariusze failure z prawdopodobieństwami
- Steel-man krytyka i odpowiedź
```

---

#### CHECK 6: EFFORT SYMMETRY (NOWY)

```
Pytanie: Czy włożony wysiłek jest proporcjonalny do złożoności?

Źródło: anchor.md (Complexity Assessment)

Wykonaj:
- Pobierz ocenę złożoności z anchor: [1-10]
- Oceń głębokość/szczegółowość artefaktu: [1-10]
- Oblicz różnicę: |złożoność - głębokość|

Szukaj ASYMETRII:
- Sekcje które POWINNY być szczegółowe ale są ogólnikowe
- Trudne pytania z łatwymi/płytkimi odpowiedziami
- Dużo tekstu o łatwych rzeczach, mało o trudnych
- Verbose padding: słowa bez treści

WYMUSZONE PYTANIE:
Wskaż NAJTRUDNIEJSZY element zadania (z anchor).
Czy odpowiadająca sekcja w artefakcie jest NAJDŁUŻSZA/NAJGŁĘBSZA?
- Jeśli NIE → wyjaśnij dlaczego (może być uzasadnione)
- Jeśli odpowiedź jest "bo to było proste" → RED FLAG (scope reduction)

Werdykt: PASS / PARTIAL / FAIL
- PASS: różnica ≤2 AND brak asymetrii
- PARTIAL: różnica 3-4 LUB drobne asymetrie
- FAIL: różnica >4 LUB znaczące asymetrie

WYMAGANY OUTPUT: Analiza asymetrii
```

---

#### CHECK 7: REVERSIBILITY (NOWY)

```
Pytanie: Czy z artefaktu można ODTWORZYĆ oryginalne zadanie?

Wykonaj:
- Przeczytaj artefakt BEZ patrzenia na anchor
- Spróbuj zrekonstruować: CEL, ZAKRES, OGRANICZENIA
- Porównaj rekonstrukcję z anchor.md

Oceń:
| Element | W anchor | Rekonstrukcja z artefaktu | Match? |
|---------|----------|---------------------------|--------|
| Cel | [z anchor] | [z artefaktu] | TAK/NIE/CZĘŚCIOWO |
| Zakres | [z anchor] | [z artefaktu] | TAK/NIE/CZĘŚCIOWO |
| Ograniczenia | [z anchor] | [z artefaktu] | TAK/NIE/CZĘŚCIOWO |

WYMUSZONE PYTANIE:
Jeśli ktoś przeczyta TYLKO artefakt (nie anchor), czy zrozumie:
- Co było oryginalnym problemem?
- Jakie były constraints?
- Co jest out of scope i dlaczego?

Werdykt: PASS / PARTIAL / FAIL
- PASS: wszystkie elementy Match = TAK
- PARTIAL: niektóre CZĘŚCIOWO
- FAIL: którykolwiek NIE

WYMAGANY OUTPUT: Tabela porównawcza
```

---

### Wyjście: gate_vN.md

```markdown
# Gate Report v{N}

## Pre-Check Adversarial Stance
[Odpowiedzi na 3 pytania z Anti-Collusion Protocol]

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

## Overall: [PASS / NEEDS WORK / FAIL]

## FAIL Reasons (jeśli są)
FAIL_1: [konkretny cytat + lokalizacja + co jest naruszeniem + który CHECK]
FAIL_2: [konkretny cytat + lokalizacja + co jest naruszeniem + który CHECK]
...

## RED FLAGS (jeśli są)
RED_FLAG_1: [opis + dlaczego podejrzane + rekomendacja]
...

## Avoided Work Indicators (jeśli wykryte)
AVOIDANCE_1: [co powinno być zrobione ale nie zostało]
...

## Required Outputs
- Tabela elementów scope (CHECK 0)
- Tabela założeń z Adversarial Audit (CHECK 4)
- 3 scenariusze failure z prawdopodobieństwami + steel-man (CHECK 5)
- Analiza asymetrii (CHECK 6)
- Tabela porównawcza reversibility (CHECK 7)
```

### Walidacja gate_vN.md

Przed przejściem do decyzji, sprawdź:
1. Czy gate_vN.md zawiera werdykt dla wszystkich 8 checks?
2. Czy każdy FAIL/PARTIAL ma format: cytat + lokalizacja + naruszenie + CHECK?
3. Czy Overall jest logicznie spójny z werdyktami (np. nie PASS gdy są FAIL)?
4. Czy Pre-Check Adversarial Stance jest wypełnione?
5. Czy wszystkie Required Outputs są obecne?

Jeśli NIE → powtórz FAZA 1 (max 1 retry, potem STOP + eskaluj).

### Decyzja po FAZA 1

| Overall | Akcja |
|---------|-------|
| PASS | → FAZA 3 (Publish) |
| NEEDS WORK | → FAZA 2 (Repair) |
| FAIL | → FAZA 2 (Repair) |

---

## FAZA 2: REPAIR

### Wejście

```
anchor
spec
output_vN
gate_vN.md (z listą FAIL reasons + RED FLAGS + AVOIDANCE indicators)
```

### Krok 2.1: Enumeracja

Wypisz każdy FAIL z gate_vN.md:

```
FAIL_1: [cytat z gate_vN.md]
FAIL_2: [cytat z gate_vN.md]
...
```

Wypisz każdy RED_FLAG:
```
RED_FLAG_1: [cytat z gate_vN.md]
...
```

Wypisz każdy AVOIDANCE indicator:
```
AVOIDANCE_1: [cytat z gate_vN.md]
...
```

Jeśli gate_vN.md nie zawiera konkretnych FAIL reasons → STOP.

---

### Krok 2.1b: AVOIDED WORK SCAN (NOWY)

Po enumeracji FAIL, wykonaj dodatkowy skan:

```
Dla każdej sekcji artefaktu:
1. Czy ta sekcja została W PEŁNI rozwiązana czy OMINIĘTA?
2. Porównaj z anchor MUST scope - czy wszystko pokryte?
3. Czy istnieją pytania których agent NIE zadał ale powinien?
4. Czy istnieją analizy których agent NIE wykonał?
5. Czy są miejsca gdzie agent napisał "to jest proste" ale nie udowodnił?

Dla każdego wykrytego pominięcia:
AVOIDANCE_N: [co powinno być zrobione]
CO: [konkretny element do dodania]
GDZIE: [sekcja / lokalizacja]
JAK: [co dokładnie dodać]
```

Traktuj AVOIDANCE jak FAIL do naprawy.

---

### Krok 2.2: Plan zmian

Dla każdego FAIL_N:

```
FAIL_N: [opis naruszenia]
CO: [konkretny element do zmiany]
GDZIE: [sekcja / lokalizacja]
JAK: [minimalna zmiana]
```

Dla każdego RED_FLAG_N (jeśli wymaga akcji):

```
RED_FLAG_N: [opis]
AKCJA: [uzasadnij dlaczego OK / co zmienić]
```

Dla każdego AVOIDANCE_N:

```
AVOIDANCE_N: [co pominięto]
CO: [element do dodania]
GDZIE: [sekcja]
JAK: [treść do dodania]
```

Reguły:
- Jedna zmiana = jedno naruszenie
- Jeśli nie można określić CO/GDZIE/JAK → UNRESOLVABLE
- AVOIDANCE wymaga DODANIA treści, nie zmiany istniejącej
- NIE WOLNO: dodawać nowych wymagań, założeń, rozwiązań spoza anchor scope
- NIE WOLNO: reframować lub reinterpretować oryginalnego zadania
- NIE WOLNO: optymalizować lub przepisywać części nie objętych FAIL

#### Obsługa UNRESOLVABLE

Gdy FAIL_N jest UNRESOLVABLE:

```
FAIL_N: [opis naruszenia]
STATUS: UNRESOLVABLE
POWÓD: [dlaczego nie można naprawić w ramach obecnego scope]
```

Kontynuuj z pozostałymi FAIL. Po zakończeniu kroku 2.2:
- Jeśli WSZYSTKIE FAIL są UNRESOLVABLE → STOP, eskaluj do User z listą
- Jeśli NIEKTÓRE FAIL są UNRESOLVABLE → kontynuuj naprawę pozostałych, UNRESOLVABLE dołącz do raportu końcowego

---

### Krok 2.3: Weryfikacja planu

Weryfikację wykonuje: GATEKEEPER (osobna sesja bez kontekstu REPAIR) LUB USER.

Dla każdej zmiany:

| Pytanie | Wymagana odpowiedź |
|---------|-------------------|
| Dodaje nowe wymagania? | NIE |
| Dodaje nowe funkcje? | NIE |
| Dodaje nowe przykłady? | NIE |
| Zmienia znaczenie spec? | NIE |
| Dotyczy elementu spoza FAIL_N/AVOIDANCE_N? | NIE |
| Rozszerza zakres poza anchor? | NIE |

Jeśli którakolwiek odpowiedź jest błędna → ODRZUĆ zmianę.

---

### Krok 2.4: Wykonanie

Format:

```markdown
# Repair v{N}

## FAIL_1
PRZED: [dokładny cytat]
PO: [dokładny cytat po zmianie]
LOKALIZACJA: [gdzie]

## FAIL_2
PRZED: [dokładny cytat]
PO: [dokładny cytat po zmianie]
LOKALIZACJA: [gdzie]

## AVOIDANCE_1
PRZED: [brak / pusta sekcja]
PO: [dodana treść]
LOKALIZACJA: [gdzie]
```

Zastosuj zmiany → output_vN+1

SELF-CHECK przed Re-gate:
- Czy diff(output_vN, output_vN+1) jest niepusty?
- Czy każdy FAIL_N ma odpowiadającą zmianę w PRZED/PO?
- Czy każdy AVOIDANCE_N ma odpowiadające dodanie?
- Czy zmiany NIE wykraczają poza scope anchor?

Jeśli NIE → STOP, nie przechodź do Re-gate.

---

### Krok 2.5: Re-gate

Uruchom FAZA 1 na output_vN+1.

#### Definicja: new_failure

`new_failure` = FAIL w gate_vN+1 który spełnia OBA warunki:
1. Dotyczy innego fragmentu artefaktu niż którykolwiek FAIL w gate_vN (porównanie przez LOKALIZACJA)
2. Opisuje inny typ naruszenia niż którykolwiek FAIL w gate_vN (porównanie przez CHECK id)

Jeśli FAIL w gate_vN+1 dotyczy tej samej lokalizacji LUB tego samego typu co FAIL w gate_vN → to NIE jest new_failure (to jest ten sam problem, być może przeformułowany).

Porównanie gate_vN+1 z gate_vN wykonuje Orchestrator (nie Gatekeeper). Gatekeeper produkuje tylko gate_vN+1, nie ma dostępu do poprzednich gate (zgodnie z L1).

| Wynik | Akcja |
|-------|-------|
| Poprzednie FAIL → PASS, brak nowych FAIL | → FAZA 3 |
| Poprzednie FAIL nadal FAIL | Wróć do 2.1 (max 2 iteracje) |
| Nowe FAIL których nie było | REJECT, przywróć output_vN |
| Po 2 iteracjach nadal FAIL | STOP, eskaluj |

---

## FAZA 3: PUBLISH

### Warunki

- gate_vN.md.overall == PASS
- Lub: wszystkie FAIL z gate_vN zostały usunięte w FAZA 2

### Wyjście

```
output_final.md (= ostatni output_vN który przeszedł gate)
gate_final.md (= ostatni gate_vN z PASS)
anchor.md (= dokument anchor dla reference)
```

Jeśli istnieją UNRESOLVABLE z kroku 2.2, dołącz:
```
unresolved.md (= lista UNRESOLVABLE FAIL z powodami)
```

Jeśli istnieją RED_FLAGS które zostały zaakceptowane, dołącz:
```
accepted_risks.md (= lista RED_FLAGS z uzasadnieniem akceptacji)
```

W kontekście BMAD: output_final.md staje się wejściem dla następnej fazy workflow.

---

## DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│  EXTERNAL ORCHESTRATOR (User / BMAD)                        │
│  - inicjuje proces                                          │
│  - przekazuje spec + output_vN + original_task              │
│  - odbiera output_final lub eskalację                       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────┐
│  FAZA 0: ANCHOR     │
│  Tworzy anchor.md   │
│  (niezmienne)       │
└──────┬──────────────┘
       │
       ▼
┌─────────────┐
│   INPUT     │
│ anchor.md   │
│ output_vN   │
│ spec        │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  FAZA 1: SANITY     │
│  Anti-Collusion     │
│  8 checks           │
│  → gate_vN.md       │
└──────┬──────────────┘
       │
       ▼
   ┌───────┐
   │ PASS? │
   └───┬───┘
       │
  ┌────┴────┐
  │         │
 YES        NO
  │         │
  │         ▼
  │    ┌─────────────────────┐
  │    │  FAZA 2: REPAIR     │
  │    │  - enumerate FAIL   │
  │    │  - AVOIDED WORK     │
  │    │  - plan changes     │
  │    │  - verify plan      │
  │    │  - execute          │
  │    │  → output_vN+1      │
  │    └──────┬──────────────┘
  │           │
  │           ▼
  │      ┌─────────┐
  │      │ RE-GATE │──────┐
  │      └────┬────┘      │
  │           │           │
  │     ┌─────┴─────┐     │
  │     │           │     │
  │   PASS     STILL FAIL │
  │     │           │     │
  │     │      iterations │
  │     │        < max?   │
  │     │           │     │
  │     │      ┌────┴───┐ │
  │     │      │        │ │
  │     │     YES      NO │
  │     │      │        │ │
  │     │      └───▶────┘ │
  │     │           │     │
  │     │         STOP    │
  │     │        ESCALATE │
  │     │                 │
  │     │    NEW FAIL?────┘
  │     │        │
  │     │      REJECT
  │     │      RESTORE
  │     │
  ▼     ▼
┌─────────────────────┐
│  FAZA 3: PUBLISH    │
│  output_final.md    │
│  gate_final.md      │
│  anchor.md          │
│  (unresolved.md)    │
│  (accepted_risks.md)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│  RETURN TO EXTERNAL ORCHESTRATOR                            │
│  - output_final → następna faza BMAD                        │
│  - lub: eskalacja z listą UNRESOLVABLE                      │
└─────────────────────────────────────────────────────────────┘
```

---

## WARUNKI STOPU

| Sytuacja | Akcja |
|----------|-------|
| FAIL nienaprawialny bez rozszerzenia zakresu | UNRESOLVABLE → kontynuuj pozostałe, raportuj na końcu |
| Wszystkie FAIL są UNRESOLVABLE | STOP, eskaluj do User z pełną listą |
| Naprawa wymaga zmiany spec | STOP, eskaluj do zewnętrznego orchestratora (w BMAD: orchestrator decyduje o powrocie do poprzedniej fazy) |
| Naprawa wymaga zmiany anchor | STOP, eskaluj do User (anchor jest niezmienne) |
| Po 2 iteracjach nadal FAIL | STOP, eskaluj |
| Nowe FAIL po naprawie | REJECT, przywróć output_vN |
| RED_FLAG bez uzasadnienia | STOP, wymagaj uzasadnienia lub naprawy |

---

## FAILURE SCENARIOS (kiedy proces zawodzi)

| Scenariusz | Dlaczego proces zawodzi | Detekcja |
|------------|------------------------|----------|
| gate_vN.md jest źle sformatowany | Nie da się wyekstrahować FAIL_N | Krok 2.1 zwraca pustą listę mimo NEEDS WORK |
| Agent twierdzi że naprawił ale nic nie zmienił | Re-gate zwróci te same FAIL | diff output_vN vs output_vN+1 = pusty |
| spec jest niekompletny | CHECK 1 nie ma czego sprawdzać | stated goal = pusty/niejednoznaczny |
| anchor jest niekompletny | Cały proces jest osłabiony | FAZA 0 nie produkuje pełnego anchor |
| Gatekeeper racjonalizuje (L1) | FAIL nie zostają wykryte | User review wykazuje problemy niewidoczne w gate |
| Gatekeeper zbyt łagodny | 0 issues mimo oczywistych problemów | ZERO ISSUES WARNING + User review |
| spec (poprzedni artefakt BMAD) zawiera błędy | Proces waliduje zgodność z błędnym spec | Błędy propagują się przez workflow |
| Agent omija pracę (AVOIDANCE) | Artefakt jest płytki | CHECK 6 (Effort Symmetry) + Avoided Work Scan |
| Agent używa wygodnych założeń | Zadanie jest sztucznie uproszczone | CHECK 4 (Adversarial Audit) - RED FLAG detection |
| Agent podaje strawman failures | Ryzyko nie jest właściwie ocenione | CHECK 5 (Steel-Man Test) - prawdopodobieństwo <3 |

---

## APPENDIX: QUICK REFERENCE

### Checks Summary

| # | Check | Wykrywa | Kluczowe pytanie |
|---|-------|---------|------------------|
| 0 | Scope Integrity | Scope reduction | Czy pełny zakres anchor jest adresowany? |
| 1 | Alignment | Goal drift | Czy stated goal = original task? |
| 2 | Closure | Incompleteness | Czy można użyć bez pytań? |
| 3 | Coherence | Contradictions | Czy A nie przeczy B? |
| 4 | Grounding | Hidden assumptions | Cui bono? Czy upraszcza zadanie? |
| 5 | Falsifiability | Strawman failures | Czy scenariusze są realistyczne (>5)? |
| 6 | Effort Symmetry | Avoided work | Czy trudne = szczegółowe? |
| 7 | Reversibility | Information loss | Czy można odtworzyć anchor z artefaktu? |

### Red Flags Quick List

- Założenie które upraszcza zadanie agenta
- Scenariusz failure z prawdopodobieństwem <3
- Asymetria: trudne elementy = płytkie sekcje
- Scope reduction bez jawnej decyzji User
- Brak odpowiedzi na steel-man krytykę
- ZERO ISSUES w gate (możliwa nadmierna łagodność)
