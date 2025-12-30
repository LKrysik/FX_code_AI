# BUG-003-9a: UX Validation Plan

**Story ID:** BUG-003-9a
**Status:** ready-for-dev
**Priority:** P0 (BLOCKING - must complete before implementing UX changes)
**Parent:** BUG-003-9 (UX Designer Review)
**Created:** 2025-12-30
**Agent:** Sally (UX Designer) + PM

---

## Problem Statement

UX Designer Review (BUG-003-9) identified 15+ UX issues and recommendations, but verification revealed **critical gaps**:

| Finding | Risk | Impact |
|---------|------|--------|
| Progressive disclosure może ukryć krytyczne dane | 🔴 HIGH | Trader może przegapić liquidation warning |
| Brak obserwacji użytkownika | 🔴 HIGH | Rekomendacje mogą nie trafić w realne potrzeby |
| Brak pomiaru Time-to-Insight | 🟡 MEDIUM | Nie wiemy czy zmiany poprawią sytuację |
| Założenia bez walidacji | 🔴 HIGH | Możemy pogorszyć UX zamiast poprawić |

**Cel tego planu:** Zwalidować rekomendacje UX PRZED implementacją.

---

## Plan naprawczy

### Faza 1: User Research (BLOCKING)

#### Task 1.1: Wywiad z traderem

**Cel:** Zrozumieć co "nieczytelny" oznacza dla użytkownika.

**Pytania do zadania:**

1. "Kiedy ostatnio interfejs Cię zmylił? Co się stało?"
2. "Co jest PIERWSZĄ rzeczą którą szukasz po otwarciu dashboardu?"
3. "Czy kiedykolwiek przegapiłeś ważny sygnał lub pozycję? Dlaczego?"
4. "Które elementy ekranu są dla Ciebie NAJWAŻNIEJSZE podczas aktywnej pozycji?"
5. "Czy wolisz widzieć wszystko naraz, czy ukrywać szczegóły?"
6. "Co oznacza dla Ciebie S1, O1, Z1? Czy te skróty są zrozumiałe?"

**Output:** Notatki z wywiadu w `_bmad-output/user-research/interview-001.md`

**Owner:** PM lub UX Designer
**Effort:** 30-60 minut

---

#### Task 1.2: Obserwacja użytkownika (Contextual Inquiry)

**Cel:** Zobaczyć jak trader FAKTYCZNIE używa interfejsu.

**Protokół:**

1. Poproś tradera o uruchomienie sesji Paper Trading
2. Obserwuj przez 15-30 minut (bez komentowania)
3. Notuj:
   - Gdzie patrzy najpierw? (eye tracking substitute)
   - Jakie akcje wykonuje?
   - Gdzie się waha?
   - Co pomija?
   - Jakie błędy popełnia?

4. Po obserwacji zapytaj:
   - "Zauważyłem że [X] - dlaczego tak zrobiłeś?"
   - "Czy szukałeś czegoś czego nie mogłeś znaleźć?"

**Output:** Notatki z obserwacji w `_bmad-output/user-research/observation-001.md`

**Owner:** UX Designer
**Effort:** 30-60 minut

---

#### Task 1.3: Pomiar Time-to-Insight (Baseline)

**Cel:** Zmierzyć aktualny czas potrzebny na zrozumienie stanu systemu.

**Protokół:**

1. Przygotuj 5 scenariuszy:
   - Scenariusz A: "Czy mam otwartą pozycję?"
   - Scenariusz B: "Jaki jest mój P&L?"
   - Scenariusz C: "W jakim stanie jest strategia?"
   - Scenariusz D: "Czy wykryto sygnał?"
   - Scenariusz E: "Jaka jest wartość PUMP_MAGNITUDE?"

2. Dla każdego scenariusza:
   - Pokaż dashboard (świeży load)
   - Zmierz czas do poprawnej odpowiedzi
   - Zapisz błędne odpowiedzi

**Metryki:**

| Scenariusz | Target | Baseline (do zmierzenia) |
|------------|--------|--------------------------|
| A: Otwarta pozycja? | < 2s | ??? |
| B: P&L? | < 2s | ??? |
| C: Stan strategii? | < 3s | ??? |
| D: Sygnał? | < 2s | ??? |
| E: PUMP_MAGNITUDE? | < 5s | ??? |

**Output:** Wyniki w `_bmad-output/user-research/time-to-insight-baseline.md`

**Owner:** QA lub UX Designer
**Effort:** 15-30 minut

---

### Faza 2: Walidacja Progressive Disclosure

#### Task 2.1: Identyfikacja krytycznych danych

**Cel:** Zdefiniować co MUSI być widoczne podczas aktywnej pozycji.

**Pytanie do tradera:**

> "Wyobraź sobie że masz otwartą pozycję LONG na BTC.
> Które z tych informacji MUSISZ widzieć cały czas, bez klikania?"

**Checklist do walidacji:**

| Element | Zawsze widoczny? | Można ukryć? | Decyzja usera |
|---------|------------------|--------------|---------------|
| Aktualny P&L | ? | ? | |
| Unrealized P&L % | ? | ? | |
| Entry price | ? | ? | |
| Current price | ? | ? | |
| Margin ratio | ? | ? | |
| Liquidation price | ? | ? | |
| Stop Loss | ? | ? | |
| Take Profit | ? | ? | |
| Stan strategii (S1/Z1/etc) | ? | ? | |
| PUMP_MAGNITUDE | ? | ? | |
| PRICE_VELOCITY | ? | ? | |
| Wykres cenowy | ? | ? | |
| Historia transakcji | ? | ? | |

**Output:** Tabela z decyzjami w `_bmad-output/user-research/critical-data-map.md`

**Owner:** UX Designer + Trader
**Effort:** 15 minut

---

#### Task 2.2: Prototyp A/B

**Cel:** Przetestować progressive disclosure przed implementacją.

**Opcja A: Current Layout**
- Wszystko widoczne naraz
- 12+ paneli

**Opcja B: Progressive Disclosure**
- StatusHero + 3 key metrics
- Sekcje zwijane
- Krytyczne dane zawsze widoczne (per Task 2.1)

**Metoda testowania:**

1. Stwórz mockup Opcji B (Figma lub Excalidraw rozszerzony)
2. Pokaż traderowi oba layouty
3. Zadaj pytanie: "Który wolisz podczas aktywnej pozycji? Dlaczego?"
4. Zapisz preferencję i uzasadnienie

**Output:** Decyzja w `_bmad-output/user-research/ab-test-results.md`

**Owner:** UX Designer
**Effort:** 1-2 godziny (mockup + test)

---

### Faza 3: Rewizja rekomendacji

#### Task 3.1: Aktualizacja UX Review

**Cel:** Zaktualizować BUG-003-9 na podstawie user research.

**Co zaktualizować:**

1. Priority Matrix - zmień priorytety na podstawie feedbacku usera
2. Progressive Disclosure - dostosuj do krytycznych danych
3. Dodaj sekcję "User Research Findings"
4. Zaktualizuj User Stories z konkretnymi wymaganiami usera

**Output:** Zaktualizowany `bug-003-9-ux-designer-review.md`

**Owner:** UX Designer
**Effort:** 1 godzina

---

#### Task 3.2: Go/No-Go Decision

**Cel:** Podjąć decyzję czy implementować rekomendacje.

**Kryteria Go:**

- [ ] User potwierdza że issues z review odpowiadają jego doświadczeniu
- [ ] User akceptuje progressive disclosure (lub modyfikację)
- [ ] Baseline Time-to-Insight zmierzony
- [ ] Krytyczne dane zdefiniowane

**Kryteria No-Go:**

- [ ] User mówi że potrzebuje WIĘCEJ danych, nie mniej
- [ ] User nie rozpoznaje issues z review
- [ ] Brak czasu na user research

**Output:** Decyzja w sprint-status.yaml

**Owner:** PM
**Effort:** 15 minut

---

## Deliverables

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | `_bmad-output/user-research/interview-001.md` | pending |
| 2 | `_bmad-output/user-research/observation-001.md` | pending |
| 3 | `_bmad-output/user-research/time-to-insight-baseline.md` | pending |
| 4 | `_bmad-output/user-research/critical-data-map.md` | pending |
| 5 | `_bmad-output/user-research/ab-test-results.md` | pending |
| 6 | Updated `bug-003-9-ux-designer-review.md` | pending |
| 7 | Go/No-Go decision | pending |

---

## Timeline

```
┌─────────────────────────────────────────────────────────────────┐
│ FAZA 1: User Research                                           │
│ ├── Task 1.1: Wywiad (30-60 min)                               │
│ ├── Task 1.2: Obserwacja (30-60 min)                           │
│ └── Task 1.3: Time-to-Insight baseline (15-30 min)             │
│                                                                 │
│ FAZA 2: Walidacja Progressive Disclosure                        │
│ ├── Task 2.1: Krytyczne dane (15 min)                          │
│ └── Task 2.2: Prototyp A/B (1-2h)                              │
│                                                                 │
│ FAZA 3: Rewizja                                                 │
│ ├── Task 3.1: Update UX Review (1h)                            │
│ └── Task 3.2: Go/No-Go Decision (15 min)                       │
└─────────────────────────────────────────────────────────────────┘

Total: ~4-6 godzin pracy + dostępność tradera
```

---

## Acceptance Criteria

- [ ] AC1: Przeprowadzono wywiad z min. 1 traderem
- [ ] AC2: Przeprowadzono obserwację użytkownika
- [ ] AC3: Zmierzono baseline Time-to-Insight dla 5 scenariuszy
- [ ] AC4: Zdefiniowano krytyczne dane podczas aktywnej pozycji
- [ ] AC5: Przetestowano progressive disclosure z userem
- [ ] AC6: Podjęto decyzję Go/No-Go z uzasadnieniem
- [ ] AC7: Zaktualizowano UX Review na podstawie findings

---

## Dependencies

| Dependency | Status |
|------------|--------|
| Dostępność tradera (usera) | REQUIRED |
| Działająca sesja Paper Trading | REQUIRED |
| BUG-003-9 UX Review | ✅ DONE |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| User niedostępny | Przełóż UX implementation do czasu dostępności |
| User nie chce progressive disclosure | Nie implementuj VH-1, skup się na innych issues |
| Time-to-Insight już dobry (< 3s) | Re-priorytetyzuj - może problem nie jest wizualny |

---

*Plan created by: Sally (UX Designer Agent)*
*BMAD Framework - FX Agent AI Project*
