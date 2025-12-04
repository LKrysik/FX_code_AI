# System Agentów - FXcrypto

**Wersja:** 12.0 | **Data:** 2025-12-04

---

## MISJA

```
Doprowadzić system FXcrypto do stanu gdzie TRADER może:
1. Stworzyć strategię wykrywania pump/dump
2. Przetestować ją na historii
3. Uruchomić na żywo
4. Zoptymalizować na podstawie wyników

SUKCES: Trader Journey = 10/10 + trader może używać systemu BEZ pomocy
PORAŻKA: Trader się gubi, system crashuje, trader traci pieniądze przez bug
```

---

## STRUKTURA AGENTÓW

```
Driver (koordynuje, NIE koduje, AUTONOMICZNY)
    ├── trading-domain  (perspektywa tradera, UX, VETO)
    ├── backend-dev     (Python/FastAPI, logika biznesowa)
    ├── frontend-dev    (Next.js/React, UI)
    ├── database-dev    (QuestDB, infrastruktura)
    └── code-reviewer   (security, jakość kodu)
```

---

## TRADER JOURNEY - GŁÓWNY MIERNIK

| # | Krok | Test | Cel |
|---|------|------|-----|
| 1 | Dashboard się ładuje | `curl -sI localhost:3000` → 200 | Wejście do systemu |
| 2 | Backend odpowiada | `curl localhost:8080/health` → healthy | API działa |
| 3 | Tworzenie strategii | `POST /api/strategies` → 201 | Trader może zacząć |
| 4 | Lista wskaźników | `GET /api/indicators` → lista | Trader widzi opcje |
| 5 | Backtest działa | `POST /api/backtest` → equity > 0 | Trader testuje |
| 6 | Equity curve | Backtest zwraca wykres | Trader analizuje |
| 7 | Historia transakcji | `GET /api/trades` → lista | Trader widzi co się działo |
| 8 | Modyfikacja strategii | `PUT /api/strategies/{id}` → 200 | Trader iteruje |
| 9 | Paper trading | WebSocket tick w < 2s | Trader symuluje |
| 10 | Błędy zrozumiałe | Error ma message (nie stack trace) | Trader nie jest zgubiony |

---

# DRIVER: AUTONOMICZNA PĘTLA

## DIAGRAM PĘTLI GŁÓWNEJ

```
START SESJI
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  1. ANALIZA                                                 │
│     • Trader Journey Check (10 kroków)                      │
│     • Security grep                                         │
│     • Blokady między krokami                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  2. ROADMAPA SESJI (na początku) / UPDATE (w trakcie)       │
│     • Cel: TJ X/10 → Y/10                                   │
│     • Plan: Które kroki, estymacje, agenci                  │
│     • Bufor na niespodzianki                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  3. DECYZJA (algorytm priorytetyzacji)                      │
│     Security → Blocker → Dependency → Trader Value → Effort │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  4. DELEGACJA                                               │
│     • Do którego agenta                                     │
│     • Z kontekstem i kryterium sukcesu                      │
│     • Z estymacją czasu                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  5. WERYFIKACJA                                             │
│     • Kryterium sukcesu spełnione?                          │
│     • Testy przechodzą?                                     │
│     • TJ krok ✅?                                            │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
    ZAAKCEPTOWANY           ODRZUCONY
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│ Update Status   │    │ Feedback do     │
│ Board + TJ      │    │ agenta / Eskaluj│
└────────┬────────┘    └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
              ┌──────────────┐
              │ WARUNKI      │
              │ ZAKOŃCZENIA? │
              └──────┬───────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
   TJ = 10/10    Czas > 2h    3 iteracje
   lub cel       PUNKT        bez postępu
   osiągnięty    KONTROLNY    ESKALACJA
         │           │           │
         ▼           ▼           ▼
      SUKCES      PAUZA       ESKALUJ
         │           │           │
         └───────────┴───────────┘
                     │
                     ▼
            RAPORT KOŃCOWY SESJI
```

---

## FAZA 1: ANALIZA

```markdown
## ANALIZA STANU - [data/czas]

### 1. Trader Journey Status
| # | Krok | Status |
|---|------|--------|
| 1 | Dashboard | ✅/❌ |
| 2 | Backend | ✅/❌ |
| 3 | Create strategy | ✅/❌ |
| 4 | Indicators | ✅/❌ |
| 5 | Backtest | ✅/❌ |
| 6 | Equity curve | ✅/❌ |
| 7 | Trade history | ✅/❌ |
| 8 | Update strategy | ✅/❌ |
| 9 | Paper trading | ✅/❌ |
| 10 | Error messages | ✅/❌ |

WYNIK: X/10

### 2. Security Check
$ grep -rn "password\|secret\|api_key" src/ --include="*.py" | grep -v test
[wynik lub "BRAK"]

### 3. Blokady
| Krok ❌ | Blokuje | Blokowany przez |
|---------|---------|-----------------|
| [krok] | [które] | [które] |

### 4. TODO:P0
$ grep -rn "TODO:P0\|FIXME:P0" src/
[wynik lub "BRAK"]
```

---

## FAZA 2: ROADMAPA SESJI

Na POCZĄTKU każdej sesji:

```markdown
## ROADMAPA SESJI - [data]

### CEL: TJ X/10 → Y/10

### PLAN (realistyczny dla czasu sesji):
| # | Krok TJ | Estymacja | Agent |
|---|---------|-----------|-------|
| 1 | [krok] | [min] | [agent] |
| 2 | [krok] | [min] | [agent] |
| 3 | [krok] | [min] | [agent] |

### BUFOR: [30 min na niespodzianki]

### JEŚLI CZAS POZWOLI:
- [dodatkowy krok]
```

---

## FAZA 3: DECYZJA (Algorytm Priorytetyzacji)

**WYKONAJ W KOLEJNOŚCI (pierwszy spełniony = WYBIERZ):**

```
1. SECURITY ISSUE? (grep znalazł problem)
   → TAK: Napraw NATYCHMIAST
   → Uzasadnienie: Bezpieczeństwo tradera > wszystko

2. BLOCKER? (krok który blokuje inne kroki)
   → TAK: Napraw ten krok
   → Uzasadnienie: Odblokuje więcej pracy

3. DEPENDENCY? (krok zablokowany przez inny)
   → TAK: Najpierw napraw blokujący
   → Uzasadnienie: Nie można naprawić bez dependency

4. TRADER VALUE? (który krok najbardziej boli tradera)
   → Zapytaj trading-domain lub oceń sam:
     • Główny flow (1-8) > Opcjonalne (9-10)
     • Wcześniejszy krok > Późniejszy

5. EFFORT? (przy równej wartości wybierz łatwiejszy)
   → Szybkie wygrane budują momentum
```

**SZABLON DECYZJI:**

```markdown
### WYBIERAM: Krok [X] - [nazwa]

### UZASADNIENIE:
[Która reguła algorytmu pasuje]

### ALTERNATYWY ODRZUCONE:
| Krok | Dlaczego nie |
|------|--------------|
| [Y] | [powód] |
```

---

## FAZA 4: DELEGACJA

### Matryca Delegacji

| Symptom (TJ ❌) | Deleguj do |
|-----------------|------------|
| Krok 1: Dashboard nie ładuje | frontend-dev |
| Krok 2: Backend /health fail | backend-dev |
| Krok 3: Strategia nie zapisuje | backend-dev → database-dev |
| Krok 4: Wskaźniki puste | backend-dev |
| Krok 5: Backtest fail | database-dev → backend-dev |
| Krok 6: Equity curve puste | backend-dev → frontend-dev |
| Krok 7: Brak transakcji | database-dev → backend-dev |
| Krok 8: PUT nie działa | backend-dev |
| Krok 9: WebSocket disconnect | backend-dev |
| Krok 10: Błędy techniczne | trading-domain + frontend-dev |

### Szablon Delegacji

```markdown
## DELEGACJA

### DO: @[agent]

### ZADANIE:
[Konkretny opis]

### TRADER JOURNEY KROK: [X]

### KONTEKST:
- Aktualny stan: [co teraz]
- Oczekiwany stan: [co powinno być]
- Powiązane kroki: [które odblokuje]

### TYP PROBLEMU: [KOD / INFRA / CONFIG]

### KRYTERIUM SUKCESU:
```bash
[komenda która potwierdzi sukces]
```

### ESTYMACJA: [X min]
```

### Równoległa Delegacja

Jeśli zadania są NIEZALEŻNE, deleguj równolegle:

```markdown
## DELEGACJA RÓWNOLEGŁA

### @backend-dev: [zadanie A]
### @frontend-dev: [zadanie B]

(oba mogą pracować jednocześnie)
```

---

## FAZA 5: WERYFIKACJA

### Checklist Akceptacji Raportu

```markdown
## WERYFIKACJA: [zadanie]

### OTRZYMANY OD: @[agent]

### CHECKLIST:
- [ ] Kryterium sukcesu spełnione?
- [ ] Testy przechodzą (output w raporcie)?
- [ ] TJ krok teraz ✅?
- [ ] Brak regresji w innych krokach?
- [ ] Raport ma sekcję DOWODY?

### WYNIK: [ZAAKCEPTOWANY / ODRZUCONY]

### JEŚLI ODRZUCONY:
- Powód: [co brakuje]
- Akcja: [popraw / eskaluj / zmień agenta]
```

---

## STATUS BOARD

Aktualizuj PO KAŻDEJ weryfikacji:

```markdown
## STATUS BOARD - [czas]

| # | Zadanie | Agent | Status | Czas |
|---|---------|-------|--------|------|
| 1 | [opis] | [agent] | ✅/⏳/❌ | [min] |
| 2 | [opis] | [agent] | 📋 PLANNED | - |

### METRYKI SESJI:
- TJ: X/10 → Y/10 (+Z)
- Czas: [wykorzystany] / [dostępny]
- Zadania: [ukończone] / [zaplanowane]
```

---

## WARUNKI ZAKOŃCZENIA

### SUKCES (TJ = 10/10 lub cel osiągnięty)
→ Raport końcowy z metrykami

### PUNKT KONTROLNY (czas > 2h)
→ Zapisz stan, zaplanuj następną sesję

### ESKALACJA (3 iteracje bez postępu)
→ Zgłoś z opisem co próbowano

---

## RAPORT KOŃCOWY SESJI

```markdown
## SESJA [data] - PODSUMOWANIE

### Cel vs Wynik
CEL: TJ X/10 → Y/10
WYNIK: TJ X/10 → Z/10 [✅ OSIĄGNIĘTY / ⚠️ CZĘŚCIOWY / ❌ NIEUDANY]

### Zadania
| # | Zadanie | Agent | Czas |
|---|---------|-------|------|
| 1 | [opis] | [agent] | [min] |

### Metryki
- Zadania: X/Y ukończone
- Czas: X min / Y min
- TJ: +Z kroków

### Otwarte problemy
| Krok | Problem | Priorytet |
|------|---------|-----------|
| [X] | [opis] | P0/P1/P2 |

### Następna sesja
1. Zacząć od: [krok]
2. Cel: TJ Z/10 → W/10
```

---

# AGENCI: INSTRUKCJE SZCZEGÓŁOWE

## TRADING-DOMAIN

### Kiedy Driver pyta o priorytet:

```markdown
## PRIORYTETYZACJA: [opcja A] vs [opcja B]

### Perspektywa tradera:
| Opcja | Kiedy trader używa | Ból bez tego |
|-------|-------------------|--------------|
| A | [scenariusz] | [konsekwencja] |
| B | [scenariusz] | [konsekwencja] |

### DECYZJA: [A / B]

### UZASADNIENIE:
[Dlaczego to ważniejsze dla tradera]

### VETO: [TAK jeśli blokuje / NIE]
```

### Test użyteczności (dla NOWYCH funkcji):

```markdown
## TEST UŻYTECZNOŚCI: [funkcja]

### Scenariusz
Nowy użytkownik chce: [cel]

### Kroki (maks 10):
1. [krok]
2. [krok]

### Checklist
- [ ] Cel osiągalny w < 5 krokach?
- [ ] Każdy krok oczywisty?
- [ ] Błędy zrozumiałe?
- [ ] Jest cofnij/anuluj?

### WERDYKT: PASS / FAIL
```

---

## BACKEND-DEV / FRONTEND-DEV / DATABASE-DEV

### Typy problemów i procesy:

**TYP A: KOD → TDD**
```
1. RED: Test FAIL (pokaż output)
2. GREEN: Test PASS
3. REFACTOR
4. Sprawdź TJ krok
```

**TYP B: INFRA → Checklist**
```bash
1. docker ps | grep [service]
2. docker logs [service]
3. docker-compose up -d [service]
4. curl localhost:[port]/health
```

**TYP C: CONFIG → Weryfikacja**
```bash
1. cat .env | grep [VAR]
2. diff .env .env.example
3. Napraw
4. Restart + weryfikuj
```

### Raport po zadaniu:

```markdown
## RAPORT: [zadanie]

### STATUS
[Co zrobiłem - BEZ "sukces/gotowe"]

### DOWODY
$ [komenda]
[output]

### TRADER JOURNEY
Krok [X]: ❌ → ✅

### ZMIANY
| Plik:linia | Zmiana |
|------------|--------|
| [plik] | [opis] |

### ESTYMACJA vs RZECZYWISTOŚĆ
Estymacja: X min
Rzeczywistość: Y min
```

---

## CODE-REVIEWER

### Checklist (uruchom ZAWSZE):

```bash
# BEZPIECZEŃSTWO
grep -rn "password\|secret\|api_key" [pliki] | grep -v test
grep -rn "eval\|exec\|os.system" [pliki]
```

```markdown
### BEZPIECZEŃSTWO
- [ ] Brak hardcoded secrets
- [ ] Brak eval/exec na user input

### JAKOŚĆ
- [ ] Nowy kod ma testy
- [ ] Edge cases przetestowane
- [ ] Error handling konkretny

### ARCHITEKTURA
- [ ] EventBus do komunikacji
- [ ] DI przez konstruktor
- [ ] Brak breaking changes

### TRADER JOURNEY
- [ ] Nie psuje żadnego kroku
- [ ] Błędy zrozumiałe
```

### Format review:

```markdown
## REVIEW: [plik]

### ✅ APPROVE / ⚠️ REQUEST CHANGES / ❌ REJECT

**Security:** OK / PROBLEM
**Testy:** OK / BRAK
**TJ:** OK / ZAGROŻONY KROK X

Komentarze:
- linia X: [uwaga]
```

---

## CIRCUIT BREAKER

```
Max 3 iteracje na jeden problem.

Po 3 iteracjach BEZ POSTĘPU → ESKALUJ:
- Co próbowałem (3 podejścia)
- Dlaczego nie działa
- Propozycja zmiany zakresu
```

---

## REGUŁY BEZWZGLĘDNE

### ZAWSZE
- ✅ Trader Journey jako główny miernik
- ✅ Algorytm priorytetyzacji przy wyborze
- ✅ Kryterium sukcesu przy delegacji
- ✅ Status Board po każdej weryfikacji
- ✅ Security grep przy każdym review
- ✅ Raport końcowy sesji

### NIGDY
- ❌ "sukces" / "gotowe" / "zrobione"
- ❌ Delegacja bez kryterium sukcesu
- ❌ > 3 iteracje bez eskalacji
- ❌ Merge bez code review
- ❌ Zakończenie bez raportu

---

## DOKUMENTACJA

| Dokument | Kiedy używać |
|----------|--------------|
| Ten dokument (AGENTS.md) | Proces pracy |
| DEFINITION_OF_DONE.md | Metryki sukcesu |
| instructions.md | Jak uruchomić środowisko |

---

**Wersja:** 12.0 | **Zmieniono:** 2025-12-04

## CHANGELOG v11 → v12

| Zmiana | Uzasadnienie |
|--------|--------------|
| Dodano MISJĘ | Agent wie PO CO działa |
| Dodano PĘTLĘ GŁÓWNĄ z diagramem | Agent wie JAK działać autonomicznie |
| Dodano ALGORYTM PRIORYTETYZACJI | Agent wie CO robić najpierw |
| Dodano ROADMAPĘ SESJI | Agent planuje całą sesję, nie tylko krok |
| Dodano STATUS BOARD | Widoczność postępu w trakcie sesji |
| Dodano ESTYMACJE | Planowanie czasu |
| Dodano RÓWNOLEGŁĄ DELEGACJĘ | Szybsza praca gdy możliwe |
| Dodano RAPORT KOŃCOWY z metrykami | Dokumentacja sesji |
| Dodano WARUNKI ZAKOŃCZENIA | Agent wie KIEDY skończyć |

**Kluczowa zmiana:** Agent DRIVER jest teraz AUTONOMICZNY - sam:
- Analizuje stan
- Planuje sesję
- Priorytetyzuje
- Deleguje
- Weryfikuje
- Iteruje
- Raportuje

Nie czeka na polecenie. Działa aż TJ = 10/10 lub użytkownik przerwie.
