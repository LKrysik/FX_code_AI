# SANITY-CHECK + REPAIR WORKFLOW

---

## ZAŁOŻENIA (LOCKED)

A1. Sanity-check wykrywa naruszenia, ale nie naprawia sam.
A2. Agent nie jest obiektywnie prawdomówny - potrafi racjonalizować.
A3. Brak zewnętrznego oracle prawdy - weryfikacja opiera się na kontrakcie i spójności.
A4. User/system może wymusić kolejność kroków i zatrzymać proces.
A5. Cel = usunięcie wykrytych naruszeń bez pogarszania reszty.
A6. Proces może być uruchamiany przez zewnętrzny orchestrator (np. BMAD). Orchestrator inicjuje proces i przekazuje artefakty. Wewnątrz procesu sterują wyłącznie agenci AI.

### Known Limitations (wynikające z założeń)

L1. **Gatekeeper Reliability** — Z A2 wynika, że Gatekeeper (jako agent) może racjonalizować. Proces nie eliminuje tego ryzyka, jedynie go ogranicza przez: (a) separację sesji (Gatekeeper NIE otrzymuje: kontekstu powstania artefaktu, informacji kto jest Executorem, historii poprzednich wersji - otrzymuje TYLKO: artefakt + spec + instrukcję oceny), (b) wymóg cytatów i lokalizacji, (c) opcjonalną weryfikację User w kroku 2.3. User powinien traktować gate_vN.md jako heurystykę, nie gwarancję.

---

## ROLE

Proces jest inicjowany przez operatora zewnętrznego (User lub zewnętrzny orchestrator, np. BMAD Orchestrator). Po inicjacji, wewnątrz procesu sterują wyłącznie agenci AI w następujących rolach:

| Rola | Odpowiedzialność |
|------|------------------|
| **Orchestrator** | Steruje przepływem między fazami. Przekazuje artefakty między rolami. Liczy iteracje. Wykonuje porównania gate_vN vs gate_vN+1. Podejmuje decyzje STOP/kontynuuj. W kontekście BMAD: może być realizowany przez BMad-Master lub dedykowany workflow. |
| **Executor** | Tworzy output_vN na podstawie spec. W kontekście BMAD: agent który wyprodukował artefakt (PM, Architect, Developer, etc.). |
| **Gatekeeper** | Wykonuje FAZA 1 (sanity-check). Produkuje gate_vN.md. Działa w izolowanej sesji (L1). W kontekście BMAD: osobna sesja/fresh chat. |
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
| `spec` | User / project-brief / poprzedni artefakt BMAD | Kontrakt wejścia |
| `output_vN` | Executor | Artefakt do walidacji |
| `gate_vN.md` | Gatekeeper | Wynik sanity-check z FAIL reasons |
| `repair_vN.md` | Repairer | Diff zmian |

---

## FAZA 1: SANITY-CHECK

### Wejście

```
artifact_path: ścieżka do output_vN
spec_path: ścieżka do spec (opcjonalnie)
```

### Wykonanie

Dla każdego z 5 checks:

---

#### CHECK 1: ALIGNMENT

```
Pytanie: Czy artefakt realizuje STATED goal?

Stated goal źródło: spec.goal LUB nagłówek artefaktu LUB pierwszy akapit opisujący cel

Wykonaj:
- Zacytuj stated goal
- Wymień jak artefakt adresuje każdą część goal
- Wymień części goal NIE adresowane

Werdykt: PASS / PARTIAL / FAIL
```

---

#### CHECK 2: CLOSURE

```
Pytanie: Czy artefakt jest kompletny i samowystarczalny?

Wykonaj:
- Szukaj: TODO, TBD, PLACEHOLDER, "to be defined", "see X"
- Sprawdź: Czy ktoś niezaznajomiony może użyć bez pytań?

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

Werdykt: PASS / PARTIAL / FAIL
```

---

#### CHECK 4: GROUNDING

```
Pytanie: Czy założenia są jawne?

Wykonaj:
- Wypisz WSZYSTKIE założenia (jawne I ukryte)
- Dla każdego ukrytego: OZNACZ jako issue
- WYMUSZONE PYTANIE: Jakie założenie, gdyby było fałszywe, 
  unieważniłoby >50% artefaktu? Jeśli żadne z wypisanych → 
  prawdopodobnie pominięto krytyczne założenie, wróć i szukaj.

Werdykt: PASS / PARTIAL / FAIL

WYMAGANY OUTPUT: Lista założeń
```

---

#### CHECK 5: FALSIFIABILITY

```
Pytanie: Kiedy to nie zadziała?

Wykonaj:
- Podaj 3 realistyczne scenariusze failure
- Wskaż edge cases nie pokryte
- WYMUSZONE PYTANIE: Czy którykolwiek scenariusz jest 
  bardziej prawdopodobny niż sukces w typowym użyciu? 
  Jeśli nie → prawdopodobnie podano strawmany, wróć i szukaj 
  scenariuszy bliższych rzeczywistości.

Werdykt: PASS / PARTIAL / FAIL

WYMAGANY OUTPUT: 3 scenariusze failure
```

---

### Wyjście: gate_vN.md

```markdown
# Gate Report v{N}

## Summary
| Check | Status | Finding |
|-------|--------|---------|
| Alignment | [PASS/PARTIAL/FAIL] | [one-line] |
| Closure | [PASS/PARTIAL/FAIL] | [one-line] |
| Coherence | [PASS/PARTIAL/FAIL] | [one-line] |
| Grounding | [PASS/PARTIAL/FAIL] | [one-line] |
| Falsifiability | [PASS/PARTIAL/FAIL] | [one-line] |

## Overall: [PASS / NEEDS WORK / FAIL]

## FAIL Reasons (jeśli są)
FAIL_1: [konkretny cytat + lokalizacja + co jest naruszeniem]
FAIL_2: [konkretny cytat + lokalizacja + co jest naruszeniem]
...
```

### Walidacja gate_vN.md

Przed przejściem do decyzji, sprawdź:
1. Czy gate_vN.md zawiera werdykt dla wszystkich 5 checks?
2. Czy każdy FAIL/PARTIAL ma format: cytat + lokalizacja + naruszenie?
3. Czy Overall jest logicznie spójny z werdyktami (np. nie PASS gdy są FAIL)?

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
spec
output_vN
gate_vN.md (z listą FAIL reasons)
```

### Krok 2.1: Enumeracja

Wypisz każdy FAIL z gate_vN.md:

```
FAIL_1: [cytat z gate_vN.md]
FAIL_2: [cytat z gate_vN.md]
...
```

Jeśli gate_vN.md nie zawiera konkretnych FAIL reasons → STOP.

---

### Krok 2.2: Plan zmian

Dla każdego FAIL_N:

```
FAIL_N: [opis naruszenia]
CO: [konkretny element do zmiany]
GDZIE: [sekcja / lokalizacja]
JAK: [minimalna zmiana]
```

Reguły:
- Jedna zmiana = jedno naruszenie
- Jeśli nie można określić CO/GDZIE/JAK → UNRESOLVABLE

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
| Dotyczy elementu spoza FAIL_N? | NIE |

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
```

Zastosuj zmiany → output_vN+1

SELF-CHECK przed Re-gate:
- Czy diff(output_vN, output_vN+1) jest niepusty?
- Czy każdy FAIL_N ma odpowiadającą zmianę w PRZED/PO?

Jeśli NIE → STOP, nie przechodź do Re-gate.

---

### Krok 2.5: Re-gate

Uruchom FAZA 1 na output_vN+1.

#### Definicja: new_failure

`new_failure` = FAIL w gate_vN+1 który spełnia OBA warunki:
1. Dotyczy innego fragmentu artefaktu niż którykolwiek FAIL w gate_vN (porównanie przez LOKALIZACJA)
2. Opisuje inny typ naruszenia niż którykolwiek FAIL w gate_vN (porównanie przez CHECK id: Alignment/Closure/Coherence/Grounding/Falsifiability)

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
```

Jeśli istnieją UNRESOLVABLE z kroku 2.2, dołącz:
```
unresolved.md (= lista UNRESOLVABLE FAIL z powodami)
```

W kontekście BMAD: output_final.md staje się wejściem dla następnej fazy workflow.

---

## DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│  EXTERNAL ORCHESTRATOR (User / BMAD)                        │
│  - inicjuje proces                                          │
│  - przekazuje spec + output_vN                              │
│  - odbiera output_final lub eskalację                       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────┐
│   INPUT     │
│ output_vN   │
│ spec        │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  FAZA 1: SANITY     │
│  5 checks           │
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
│  (unresolved.md)    │
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
| Po 2 iteracjach nadal FAIL | STOP, eskaluj |
| Nowe FAIL po naprawie | REJECT, przywróć output_vN |

---

## FAILURE SCENARIOS (kiedy proces zawodzi)

| Scenariusz | Dlaczego proces zawodzi | Detekcja |
|------------|------------------------|----------|
| gate_vN.md jest źle sformatowany | Nie da się wyekstrahować FAIL_N | Krok 2.1 zwraca pustą listę mimo NEEDS WORK |
| Agent twierdzi że naprawił ale nic nie zmienił | Re-gate zwróci te same FAIL | diff output_vN vs output_vN+1 = pusty |
| spec jest niekompletny | CHECK 1 nie ma czego sprawdzać | stated goal = pusty/niejednoznaczny |
| Gatekeeper racjonalizuje (L1) | FAIL nie zostają wykryte | User review wykazuje problemy niewidoczne w gate |
| spec (poprzedni artefakt BMAD) zawiera błędy | Proces waliduje zgodność z błędnym spec | Błędy propagują się przez workflow |
