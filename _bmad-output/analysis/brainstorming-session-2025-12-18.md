---
stepsCompleted: [1, 2, 3]
status: "completed"
inputDocuments: ["_bmad-output/project-context.md"]
session_topic: "Naprawa i stabilizacja platformy FX Agent AI"
session_goals: "Priorytety napraw + Diagnoza przyczyn + Plan naprawy"
selected_approach: "ai-recommended"
techniques_used: ["Five Whys", "Constraint Mapping", "First Principles Thinking"]
ideas_generated: ["MVP Definition", "Root Cause Analysis", "Implementation Priority"]
context_file: "_bmad-output/project-context.md"
---

# Brainstorming Session: Naprawa i stabilizacja FX Agent AI

**Data:** 2025-12-18
**Facilitator:** Mary (Business Analyst)
**Uczestnik:** Mr Lu

---

## Session Overview

**Temat:** Naprawa i stabilizacja platformy FX Agent AI

**Cele:**
1. Lista priorytetów - Co naprawiać najpierw?
2. Diagnoza przyczyn - Dlaczego rzeczy nie działają?
3. Plan naprawy - Konkretne kroki do działającej platformy

### Context Guidance

Na podstawie analizy projektu (`project-context.md`):

**Znane problemy:**
- Trading ani backtesting nie działają jako proces E2E
- Duża część UI nie działa
- Strategy Builder niedokończony (frontend + backend)
- Brak testów E2E dla całego procesu
- Redis niedostępny (Windows bez Docker)

**Istniejące zasoby:**
- 596 testów backendowych
- 90+ dokumentów
- Solidna architektura (Clean Architecture + DDD)
- 22+ wskaźników tradingowych
- 85+ komponentów React

### Session Setup

Sesja typu "kompleksowa analiza" - łączymy diagnozę, priorytetyzację i planowanie napraw.

---

## Technique Selection

**Podejście:** AI-Recommended Techniques
**Kontekst analizy:** Naprawa i stabilizacja platformy z fokusem na priorytety + diagnozę + plan

**Wybrane techniki:**
1. **Five Whys** - Diagnoza przyczyn źródłowych dla każdego problemu
2. **Constraint Mapping** - Mapowanie ograniczeń i priorytetyzacja napraw
3. **First Principles Thinking** - Budowanie planu naprawy od fundamentów

**AI Rationale:** Sekwencja prowadzi od zrozumienia DLACZEGO (przyczyny) przez CO BLOKUJE (ograniczenia) do JAK NAPRAWIĆ (plan od podstaw).

---

## Brainstorming Content

### Faza 1: Five Whys - Diagnoza P1 (Trading nie działa)

**Problem powierzchniowy:** Trading nie działa

**Prawdziwy problem:** Cały pipeline Strategy → Signals → Execution → Dashboard jest rozłączony

#### Ścieżka przyczynowa:

1. **Why #1:** Trading nie działa → Pipeline rozłączony
2. **Why #2:** Pipeline rozłączony → Organiczny wzrost + niejasna spec + brak integracji
3. **Why #3:** Organiczny wzrost → Uczenie się domeny w trakcie + zmieniające się pomysły + AI halucynacje
4. **Why #4:** AI halucynacje → Brak E2E testów + unit ≠ integracja + brak kryteriów sukcesu
5. **Why #5:** Brak kryteriów → ROOT CAUSES

#### ROOT CAUSES:

| # | Root Cause | Opis |
|---|------------|------|
| RC1 | Brak wzorca | Nie było jasnego obrazu jak powinien wyglądać działający system |
| RC2 | Brak MVP | Nie zdefiniowano co minimalne musi działać |
| RC3 | Build > Verify | Priorytet na budowanie zamiast weryfikowania |
| RC4 | Frontend E2E trudne | Testowanie frontendu jako procesu jest najtrudniejsze |
| RC5 | Niestabilna architektura | Testy E2E trudne bez stabilnej architektury |

#### Kluczowy insight:
To nie jest problem "zepsutego kodu" - to jest problem "kodu który nigdy nie był zintegrowany i zweryfikowany jako całość".

---

### Faza 2: Constraint Mapping - Priorytetyzacja

#### BLOKERY (rozwiąż najpierw):

| # | Constraint | Rozwiązanie |
|---|------------|-------------|
| B1 | Brak definicji MVP | PRD z jasnym MVP |
| B2 | Brak wzorca działającego systemu | Research + wireframes |
| B3 | Pipeline rozłączony | Integracja krok po kroku |

#### OPÓŹNIACZE (później):

| # | Constraint | Kiedy |
|---|------------|-------|
| D1 | Brak testów E2E | Po stabilizacji MVP |
| D2 | Redis niedostępny | Alternatywa lub later |
| D3 | Frontend testy trudne | Po MVP |

#### Mapa zależności:

```
[B1: MVP Definition] → [B2: Wzorzec systemu] → [B3: Integracja pipeline]
                                ↓
                    [D1: Testy E2E] → [D3: Frontend testy]
                                ↓
                       DZIAŁAJĄCY SYSTEM
```

#### Kolejność napraw:
1. Zdefiniuj MVP
2. Stwórz wzorzec (wireframes, flow)
3. Zintegruj pipeline kawałek po kawałku
4. Dodaj testy E2E

---

### Faza 3: First Principles Thinking - Plan MVP

#### Fundamentalna definicja MVP:

> **"Skonfiguruję strategię (nawet prostą) i podczas sesji trading/backtesting WIDZĘ na dashboardzie: sygnały, stan state machine, wartości wskaźników"**

#### Stan obecny vs MVP:

| Komponent | Stan obecny | MVP Action |
|-----------|-------------|------------|
| Strategy Builder UI | Istnieje, nieczytelny | Uprość/popraw czytelność |
| Backend: Strategy → Signals | Broken/disconnected | **NAPRAW POŁĄCZENIE** |
| Dashboard: Show signals | Nie pokazuje | **NAPRAW** |
| Dashboard: Show state | Nie pokazuje | **NAPRAW** |
| Dashboard: Show indicators | Nie pokazuje | **NAPRAW** |

#### Wskaźniki MVP:

| Wskaźnik | Rola |
|----------|------|
| **TWPA** | FUNDAMENT - bazowa dla wszystkich obliczeń |
| pump_magnitude_pct | Detekcja pump (używa TWPA jako baseline) |
| volume_surge_ratio | Potwierdzenie wolumenem |
| price_velocity | Tempo zmiany |
| spread_pct | Płynność (dla Z1) |
| unrealized_pnl_pct | P&L pozycji (dla ZE1) |

**ZAKAZ:** RSI, EMA, klasyczne wskaźniki TA - ZABRONIONE

#### State Machine MVP (5 sekcji, proste warunki):

| Sekcja | Cel | MVP Warunki |
|--------|-----|-------------|
| S1 | Wykryj pump | pump_magnitude ≥ 7% AND volume_surge ≥ 3.5x |
| O1 | Anuluj fałszywy | pump_magnitude ≤ -2% OR timeout 5min |
| Z1 | Potwierdź płynność | spread_pct ≤ 1.0% |
| ZE1 | Zamknij z zyskiem | unrealized_pnl ≥ 15% |
| E1 | Emergency exit | pump_magnitude ≤ -5% |

#### Dashboard MVP musi pokazywać:

1. **Wykres ceny** z oznaczonymi sygnałami
2. **Stan state machine** (która sekcja aktywna)
3. **Wartości wskaźników** (live)
4. **Lista aktywnych sygnałów**

#### Kolejność implementacji:

1. **Napraw połączenie** Strategy → Backend → Signal Generation
2. **Napraw Dashboard** żeby pokazywał sygnały i stan
3. **Uprość Strategy Builder UI** (czytelność)
4. **Zintegruj Backtest** żeby też pokazywał wyniki
5. **Dodaj testy E2E** dla weryfikacji

---

