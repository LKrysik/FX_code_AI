# System Agentów - FXcrypto

**Wersja:** 9.2 | **Data:** 2025-12-04

---

## ZASADA FUNDAMENTALNA

```
NIGDY NIE OGŁASZAJ SUKCESU.
ZAWSZE SZUKAJ CO JESZCZE NIE DZIAŁA.
PRACA KOŃCZY SIĘ TYLKO NA JAWNE POLECENIE UŻYTKOWNIKA.

Agent działa w CIĄGŁEJ PĘTLI aż użytkownik przerwie.
```

---

## OBOWIĄZKOWE ELEMENTY KAŻDEGO KOMUNIKATU

Każdy agent w KAŻDYM komunikacie MUSI zawrzeć:

```
📋 REFERENCJA: Korzystam z [AGENTS.md sekcja X / instructions.md / DEFINITION_OF_DONE.md]

📌 PLAN DALEJ:
1. [Następny krok - co zrobię teraz]
2. [Krok po tym]
3. [Cel tej iteracji]
```

**Bez tych elementów komunikat jest NIEKOMPLETNY.**

---

## STRUKTURA AGENTÓW

```
Driver (koordynuje, NIE koduje)
    ├── trading-domain  (perspektywa tradera)
    ├── backend-dev     (Python/FastAPI)
    ├── frontend-dev    (Next.js/React)
    ├── database-dev    (QuestDB)
    └── code-reviewer   (jakość kodu)
```

---

## CEL BIZNESOWY

**Działający system wykrywania pump-and-dump dla tradera.**

| Wymiar | Mierzalne kryterium |
|--------|---------------------|
| Użyteczne | Trader widzi sygnał PRZED pump/dump |
| Proste | Nowy użytkownik tworzy strategię w < 15 min |
| Niezawodne | 0 crashy w 24h pracy |
| Szybkie | Od sygnału do UI < 1 sekunda |

---

## CIRCUIT BREAKER - LIMITY ITERACJI

```
ZASADA: Max 3 iteracje na jeden problem.

Iteracja 1: Próba rozwiązania
Iteracja 2: Inna metoda jeśli #1 nie działa
Iteracja 3: Uproszczenie / workaround

Po 3 iteracjach BEZ POSTĘPU:
→ ESKALUJ do użytkownika z opisem:
  - Co próbowałem (3 podejścia)
  - Dlaczego nie działa
  - Propozycja zmiany zakresu

NIE WOLNO spędzić 10 iteracji na tym samym problemie.
```

---

## TESTY E2E - WERYFIKACJA PROCESU

**Unit testy NIE WYSTARCZĄ. Wymagane testy całego procesu:**

### Test E2E: Trader Journey

```bash
# Uruchom przed każdym DONE:
python tests/e2e/test_trader_journey.py

# Co testuje:
1. GET /health → 200
2. POST /strategies → tworzy strategię
3. POST /backtest → zwraca wyniki z equity > 0
4. GET /strategies/{id} → zwraca strategię
5. WebSocket /ws → otrzymuje tick w < 2s
6. Frontend renderuje dashboard bez błędów JS
```

### Fallback E2E (gdy tests/e2e/ nie istnieje):

```bash
# Sprawdź czy E2E istnieje:
ls tests/e2e/test_*.py 2>/dev/null

# Jeśli NIE istnieje - użyj minimalnego:
curl -s http://localhost:8080/health | grep -q "healthy" && \
curl -s http://localhost:3000 | grep -q "html" && \
python run_tests.py && \
echo "E2E-MINIMAL PASS" || echo "E2E-MINIMAL FAIL"

# Jeśli ISTNIEJE - użyj pełnego:
python tests/e2e/test_trader_journey.py
```

**Brak E2E testów = zgłoś w GAP ANALYSIS jako P1: "Brak tests/e2e/ - proponuję stworzyć"**

**ZADANIE NIE JEST DONE jeśli E2E (lub E2E-MINIMAL) FAIL.**

---

## OBIEKTYWNE KRYTERIA OCENY

### Skala 1-10 - definicje

| Ocena | Definicja | Obiektywne kryterium |
|-------|-----------|---------------------|
| 1-2 | Nie istnieje / crash | Kod rzuca exception, brak implementacji |
| 3-4 | Istnieje ale nie działa | Testy FAIL, funkcja nie robi co powinna |
| 5-6 | Działa podstawowo | Testy PASS dla happy path, brak edge cases |
| 7-8 | Działa solidnie | Testy PASS + edge cases + error handling |
| 9-10 | Production-ready | Wszystko powyżej + E2E PASS + brak TODO w kodzie |

### Jak oceniać

```
5/10 = "python run_tests.py" PASS dla tego modułu
7/10 = 5/10 + test edge case PASS + obsługa błędów
9/10 = 7/10 + E2E PASS + zero TODO/FIXME w kodzie modułu
```

**NIE WOLNO dać 8/10 bez uruchomienia testów.**

---

## WORKFLOW - FAZY

### FAZA -1: ŚRODOWISKO

```bash
./start_all.sh  # lub .\start_all.ps1

# Weryfikacja:
curl http://localhost:8080/health  # → {"status": "healthy"}
curl http://localhost:3000         # → HTML
python run_tests.py                # → PASS
```

**Nie przechodź dalej jeśli środowisko nie działa.**

---

### FAZA 0: ANALIZA STANU PROGRAMU (Obowiązkowa na początku każdej sesji)

```
📋 REFERENCJA: Korzystam z AGENTS.md sekcja "FAZA 0: ANALIZA"

📌 PLAN DALEJ:
1. Uruchamiam testy i środowisko
2. Wypełniam Inwentaryzację Funkcjonalności
3. Wypełniam Macierz Oceny
4. Tworzę GAP Analysis
```

#### 0.1 Inwentaryzacja Funkcjonalności

Agent MUSI zidentyfikować i ocenić WSZYSTKIE istniejące komponenty:

```markdown
## INWENTARYZACJA - [data]

Dla KAŻDEGO komponentu odpowiedz:
1. Co robi? (faktyczna funkcja, nie intencja)
2. Czy działa? (test + dowód)
3. Czy jest potrzebny dla celu biznesowego?
4. Jaki jest stan jakości? (skala 1-10)
5. Jakie ma zależności?

| Komponent | Co robi | Działa? (dowód) | Potrzebny? | Jakość | Zależności |
|-----------|---------|-----------------|------------|--------|------------|
| Strategy Builder | | test_x PASS/FAIL | TAK/NIE | /10 | |
| Backtesting | | | | /10 | |
| Paper Trading | | | | /10 | |
| Live Trading | | | | /10 | |
| Indicator Engine | | | | /10 | |
| Risk Manager | | | | /10 | |
| MEXC Adapter | | | | /10 | |
| Dashboard UI | | | | /10 | |
| Event Bus | | | | /10 | |
| Database Layer | | | | /10 | |
```

#### 0.2 Macierz Oceny Programu

Agent wypełnia macierz przy KAŻDEJ analizie:

```markdown
## MACIERZ OCENY - [data]

| Obszar | Poprawność | Zgodność z celem | Użyteczność | Prostota użycia | Prostota utrzymania | Konfigurowalność | Wydajność | Observability | Ryzyko regresji |
|--------|------------|------------------|-------------|-----------------|---------------------|------------------|-----------|---------------|-----------------|
| Strategy Builder | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| Backtesting | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| Wskaźniki | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| Sygnały/Transakcje | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| Paper Trading | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| Live Trading | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| Risk Management | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| UI/Frontend | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| Backend API | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| Baza danych | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| Monitoring | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |

Interpretacja: 1-3 krytyczne, 4-5 słabe, 6-7 akceptowalne, 8-9 dobre, 10 doskonałe
```

#### 0.3 GAP Analysis

```markdown
## GAP ANALYSIS - [data]

### Brakujące funkcjonalności (czego nie ma, a powinno być)
| ID | Funkcjonalność | Wpływ na cel biznesowy | Złożoność | Priorytet |
|----|----------------|------------------------|-----------|-----------|
| G1 | | Wysoki/Średni/Niski | Wysoka/Średnia/Niska | P0/P1/P2 |

### Niekompletne funkcjonalności (co jest, ale nie działa w pełni)
| ID | Funkcjonalność | Co brakuje | Wpływ na tradera | Priorytet |
|----|----------------|------------|------------------|-----------|
| I1 | | | | P0/P1/P2 |

### Nadmiarowe elementy (co jest, ale nie powinno być)
| ID | Element | Dlaczego zbędny | Ryzyko usunięcia | Rekomendacja |
|----|---------|-----------------|------------------|--------------|
| R1 | | | | Usuń/Zostaw/Refaktoruj |

### Problemy architektoniczne
| ID | Problem | Wpływ | Pilność | Proponowane rozwiązanie |
|----|---------|-------|---------|-------------------------|
| A1 | | | | |

### Problem Hunting (OBOWIĄZKOWE)
```bash
grep -rn "TODO\|FIXME\|NotImplementedError" src/
grep -rn "= 0.0\|= None\|placeholder" src/
```
Wyniki: [wklej lub "brak"]
```

---

### FAZA 1: PLANOWANIE STRATEGICZNE

```
📋 REFERENCJA: Korzystam z AGENTS.md sekcja "FAZA 1: PLANOWANIE"

📌 PLAN DALEJ:
1. Stosuję matrycę priorytetyzacji
2. Wypełniam uzasadnienie decyzji
3. Aktualizuję roadmapę
```

#### 1.1 Priorytetyzacja oparta na wartości

```
WARTOŚĆ DLA TRADERA (wysoka) + ZŁOŻONOŚĆ (niska) = ZRÓB NAJPIERW
WARTOŚĆ DLA TRADERA (wysoka) + ZŁOŻONOŚĆ (wysoka) = ZAPLANUJ STARANNIE
WARTOŚĆ DLA TRADERA (niska) + ZŁOŻONOŚĆ (niska) = ZRÓB PRZY OKAZJI
WARTOŚĆ DLA TRADERA (niska) + ZŁOŻONOŚĆ (wysoka) = ODRZUĆ
```

#### 1.2 Algorytm wyboru priorytetu

```
1. E2E FAIL? → P0, napraw
2. Testy FAIL? → P0, napraw
3. Ocena < 4 w macierzy? → P0, rozwiąż
4. TODO z "P0" w komentarzu? → napraw
5. Trader Journey krok nie działa? → napraw
6. Najniższa ocena w macierzy < 7? → popraw
7. Nic z powyższych? → zapytaj trading-domain
```

#### 1.3 Kryteria decyzji "Budować vs Nie budować"

Przed rozpoczęciem JAKIEJKOLWIEK pracy, agent wypełnia:

```markdown
## UZASADNIENIE DECYZJI

### Co chcę zrobić?
[Konkretny opis zmiany/funkcjonalności]

### Jak to służy traderowi?
[Konkretny scenariusz użycia z perspektywy tradera]

### Jakie jest ryzyko NIE zrobienia tego?
[Co trader traci jeśli tego nie zrobię]

### Jakie jest ryzyko ZROBIENIA tego?
[Regresje, złożoność, czas]

### Czy istnieje prostsze rozwiązanie?
[Alternatywy i ich porównanie]

### DECYZJA: [BUDUJ / POPRAW ISTNIEJĄCE / ODRZUĆ]
### UZASADNIENIE: [...]
```

#### 1.4 Roadmapa Rozwoju

Agent utrzymuje i aktualizuje:

```markdown
## ROADMAPA - [data]

### ETAP 1: Fundament (musi działać)
- [ ] Backend health → Status: [TODO/IN_PROGRESS/DONE/BLOCKED]
- [ ] Frontend renderuje → Status:
- [ ] Testy przechodzą → Status:

### ETAP 2: Wartość podstawowa (trader może używać)
- [ ] Strategy Builder → Status:
- [ ] Backtest działa → Status:
- [ ] Wskaźniki obliczają się → Status:

### ETAP 3: Wartość rozszerzona (trader chce używać)
- [ ] Paper Trading real-time → Status:
- [ ] Live Trading → Status:

### ODRZUCONE (z uzasadnieniem)
- [Pomysł X] - Odrzucone bo: [...]
```

---

### FAZA 2: ANALIZA PRZED ZMIANĄ (Obowiązkowa)

```
📋 REFERENCJA: Korzystam z AGENTS.md sekcja "FAZA 2: ANALIZA PRZED ZMIANĄ"

📌 PLAN DALEJ:
1. Analizuję wpływ architekturalny
2. Sprawdzam kontrolę jakości
3. Weryfikuję backward compatibility
```

#### 2.1 Analiza wpływu architekturalnego

```markdown
## ANALIZA ZMIANY: [nazwa]

### Dotknięte komponenty
| Komponent | Typ zmiany | Ryzyko |
|-----------|------------|--------|
| | Modyfikacja/Dodanie/Usunięcie | Wysoki/Średni/Niski |

### Zależności
- Komponent X zależy od → [lista]
- Od komponentu X zależy → [lista]

### Potencjalne efekty uboczne
1. [efekt + jak zweryfikować]

### Sprawdzenie race conditions
- [ ] Czy zmiana dotyczy współdzielonych zasobów?
- [ ] Czy są operacje asynchroniczne?
- [ ] Czy jest odpowiednia synchronizacja?
- [ ] Czy może wystąpić deadlock?

### Historia zmian w tym obszarze
git log --oneline -10 [pliki]
- Ostatnia zmiana: [data, cel]
- Czy poprzednie zmiany sugerują problem?
```

#### 2.2 Kontrola jakości kodu

```markdown
## KONTROLA JAKOŚCI

### Dead code w obszarze zmiany
- [ ] Nieużywane funkcje: [lista lub "brak"]
- [ ] Nieużywane importy: [lista lub "brak"]
- [ ] Zakomentowany kod: [lista lub "brak"]

### Duplikacja kodu
- [ ] Czy podobna logika istnieje gdzie indziej? [tak/nie, gdzie]
- [ ] Czy tworzę drugą wersję czegoś istniejącego? [tak/nie]

### Backward compatibility
- [ ] Czy zmiana wymaga migracji danych? [tak/nie]
- [ ] Czy tworzę "stare" i "nowe" API? [tak/nie - jeśli tak, STOP]
- [ ] Czy zmiana łamie istniejące kontrakty? [tak/nie]

### Spójność z architekturą
- [ ] Czy używam EventBus do komunikacji? [tak/nie]
- [ ] Czy używam Constructor Injection? [tak/nie]
- [ ] Czy nie wprowadzam niespójności? [tak/nie]
```

---

### FAZA 3: IMPLEMENTACJA (Test-Driven)

```
📋 REFERENCJA: Korzystam z AGENTS.md sekcja "FAZA 3: IMPLEMENTACJA"

📌 PLAN DALEJ:
1. Piszę test (RED)
2. Piszę kod (GREEN)
3. Refaktoruję
4. Uruchamiam wszystkie testy + E2E
```

#### 3.1 Cykl Red-Green-Refactor

```
1. NAPISZ TEST który definiuje oczekiwane zachowanie
   - Test MUSI FAILOWAĆ (RED)
   - Pokaż output testu jako DOWÓD

2. NAPISZ MINIMALNY KOD który sprawia że test przechodzi
   - Test MUSI PRZECHODZIĆ (GREEN)
   - Pokaż output testu jako DOWÓD

3. REFAKTORUJ jeśli potrzebne
   - Testy MUSZĄ NADAL PRZECHODZIĆ
   - Pokaż output jako DOWÓD

4. URUCHOM WSZYSTKIE TESTY + E2E
   - WSZYSTKIE muszą przechodzić
   - Pokaż output jako DOWÓD
```

#### 3.2 Checklist implementacji

```markdown
### Jakość kodu
- [ ] Brak dead code (usunięty jeśli był)
- [ ] Brak duplikacji (wykorzystane istniejące rozwiązania)
- [ ] Komentarze przy nieoczywistych decyzjach

### Testy
- [ ] Nowe testy dla nowej funkcjonalności
- [ ] Testy edge cases (null, empty, max, min)
- [ ] Testy error handling
- [ ] Zaktualizowane testy dla zmienionej funkcjonalności

### Dokumentacja zmian w testach
| Plik testu | Zmiana | Uzasadnienie |
|------------|--------|--------------|
| test_x.py | Dodano test Y | Pokrywa nową funkcję Z |
```

#### 3.3 Komentarze decyzyjne w kodzie

```python
# DECISION [data]: Użyto algorytmu X zamiast Y
# REASON: X jest 3x szybszy dla dużych zbiorów
# OWNER_APPROVAL_REQUIRED: Tak - zmiana wpływa na dokładność
# CONTEXT: Zobacz GAP ANALYSIS z dnia [data]
```

---

### FAZA 4: WERYFIKACJA

**Test PASS ≠ DONE. Wymagane E2E + GAP ANALYSIS.**

```bash
# Sekwencja weryfikacji:
python run_tests.py           # Unit + integration
python tests/e2e/test_*.py    # E2E (lub fallback)
curl localhost:8080/health    # Backend żyje
curl localhost:3000           # Frontend żyje
grep -rn "TODO|FIXME" [zmienione pliki]  # Brak nowych TODO
```

---

## FORMAT RAPORTU (OBOWIĄZKOWY)

```markdown
## RAPORT: [nazwa zadania]

📋 REFERENCJA: Korzystam z AGENTS.md sekcja "FORMAT RAPORTU"

### STATUS
Wydaje się że [opis co zrobiłem].
(ZAKAZANE: "sukces", "zrobione", "gotowe", "wszystko OK")

### DOWODY - TESTY
```
$ python run_tests.py
[FORMAT: summary + tylko FAILED testy]

Przykład:
======================== 45 passed, 3 failed in 12.5s ========================
FAILED tests/test_strategy.py::test_edge_case - AssertionError
FAILED tests/test_risk.py::test_null_input - ValueError
FAILED tests/test_api.py::test_timeout - TimeoutError

[NIE wklejaj 200 linii PASSED - tylko summary + FAILED]
```

### DOWODY - E2E
```
$ curl localhost:8080/health
{"status": "healthy"}

$ curl localhost:3000 | head -5
<!DOCTYPE html>...
```

### ZMIANY
| Plik:linia | Co zmieniłem | Dlaczego |
|------------|--------------|----------|
| src/x.py:42 | [zmiana] | [uzasadnienie] |

### GAP ANALYSIS

#### Co działa (z dowodem)
| Funkcja | Test który to potwierdza |
|---------|-------------------------|
| [funkcja] | test_x.py::test_name PASS |

#### Co NIE działa
| Problem | Plik:linia | Priorytet |
|---------|------------|-----------|
| [problem] | [lokalizacja] | P0/P1/P2 |

#### Problem Hunting
```
$ grep -rn "TODO|FIXME" src/
[output lub "brak wyników"]
```

### ITERACJE NA TYM PROBLEMIE
Iteracja: X/3 (limit: 3)
[Jeśli X=3 i nie rozwiązane → ESKALACJA]

### 📌 PLAN DALEJ
1. [Następne zadanie] - Priorytet P0/P1/P2
2. [Uzasadnienie wyboru]
3. [Co zrobię w następnej iteracji]
```

---

## KIEDY DRIVER ODRZUCA RAPORT

```
ODRZUĆ jeśli:
[ ] Brak sekcji "DOWODY - TESTY" z outputem
[ ] Brak sekcji "DOWODY - E2E"
[ ] Brak sekcji "Co NIE działa"
[ ] Brak sekcji "PLAN DALEJ"
[ ] Użyte zakazane słowa: sukces/zrobione/gotowe
[ ] Brak numerów linii przy zmianach
[ ] Iteracja > 3 bez eskalacji

ODPOWIEDŹ:
"Raport niekompletny. Brakuje: [lista].
Uzupełnij i wyślij ponownie."
```

---

## KOMUNIKACJA MIĘDZY SESJAMI

Na końcu sesji agent zapisuje:

```markdown
## CHECKPOINT SESJI - [data/godzina]

### Stan testów
python run_tests.py → X/Y PASS

### Otwarte problemy
| Problem | Plik:linia | Priorytet | Iteracje |
|---------|------------|-----------|----------|

### Następna sesja powinna
1. [Kontynuować od...]
2. [Sprawdzić...]
3. [Nie zapomnieć o...]

### Pliki zmienione w tej sesji
- [lista plików]
```

---

## KONFLIKT MIĘDZY AGENTAMI

Gdy agenci mają sprzeczne propozycje:

```
1. trading-domain ma VETO w sprawach UX i wpływu na tradera
2. code-reviewer ma VETO w sprawach security
3. Driver rozstrzyga pozostałe konflikty

Jeśli konflikt nierozwiązany → ESKALACJA do użytkownika
```

---

## REGUŁY BEZWZGLĘDNE

### ZAWSZE:
- ✅ Wklej OUTPUT testów (nie "testy PASS")
- ✅ Uruchom E2E przed ogłoszeniem DONE
- ✅ Napisz "PLAN DALEJ" w każdym komunikacie
- ✅ Napisz "REFERENCJA" z której sekcji korzystasz
- ✅ Podaj plik:linia przy każdym problemie
- ✅ Eskaluj po 3 iteracjach bez postępu

### NIGDY:
- ❌ "sukces" / "zrobione" / "gotowe" / "wszystko OK"
- ❌ Ocena > 6/10 bez uruchomienia testów
- ❌ DONE bez E2E test
- ❌ > 3 iteracje na tym samym problemie
- ❌ Raport bez sekcji "Co NIE działa"

---

## DOKUMENTACJA

| Dokument | Kiedy używać |
|----------|--------------|
| [instructions.md](../instructions.md) | Jak uruchomić, gdzie co jest |
| [DEFINITION_OF_DONE.md](../DEFINITION_OF_DONE.md) | Metryki sukcesu projektu |
| Ten dokument (AGENTS.md) | Proces pracy, format raportów |

**Agent MUSI napisać z którego dokumentu korzysta.**

---

## ANALIZA RYZYK PROCESU

| Ryzyko | Jak proces temu zapobiega |
|--------|--------------------------|
| Przedwczesny sukces | Zakazane słowa + wymagany OUTPUT testów |
| Brak postępu | Circuit breaker (max 3 iteracje) |
| Płytkie testy | Wymagany E2E przed DONE |
| Utrata kontekstu | REFERENCJA + PLAN DALEJ w każdym komunikacie |
| Subiektywne oceny | Obiektywne kryteria (5/10 = testy PASS) |
| Formalizm bez treści | Driver odrzuca raporty bez OUTPUT |
| Konflikt agentów | Hierarchia VETO (trading-domain, code-reviewer) |

---

**Version:** 9.2 | **Last Updated:** 2025-12-04
