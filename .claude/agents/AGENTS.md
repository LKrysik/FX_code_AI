# System Agentów - FXcrypto

**Wersja:** 9.0 | **Data:** 2025-12-04

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

### FAZA 0: ANALIZA (na początku sesji)

```
📋 REFERENCJA: Korzystam z AGENTS.md sekcja "FAZA 0: ANALIZA"

📌 PLAN DALEJ:
1. Uruchamiam testy: python run_tests.py
2. Sprawdzam TODO: grep -rn "TODO|FIXME" src/
3. Wypełniam GAP ANALYSIS
```

#### GAP ANALYSIS

```markdown
## GAP ANALYSIS - [data]

### Wynik testów
python run_tests.py → X/Y PASS, Z FAIL
Failing tests: [lista]

### Problem Hunting
grep -rn "TODO|FIXME" src/ → [liczba] wyników
Krytyczne: [lista plik:linia]

### Co NIE DZIAŁA
| Problem | Plik:linia | Priorytet | Dlaczego P0/P1/P2 |
|---------|------------|-----------|-------------------|
```

---

### FAZA 1: WYBÓR PRIORYTETU

```
ALGORYTM:
1. E2E FAIL? → napraw
2. Testy FAIL? → napraw
3. TODO z "P0" w komentarzu? → napraw
4. Trader Journey krok nie działa? → napraw
5. Najniższa ocena w macierzy < 7? → popraw
6. Nic z powyższych? → zapytaj trading-domain o ocenę
```

---

### FAZA 2: IMPLEMENTACJA

```
📋 REFERENCJA: Korzystam z AGENTS.md sekcja "FAZA 2: IMPLEMENTACJA"

📌 PLAN DALEJ:
1. Piszę test który FAIL (RED)
2. Piszę minimalny kod → test PASS (GREEN)
3. Uruchamiam wszystkie testy
4. Uruchamiam E2E test
```

---

### FAZA 3: WERYFIKACJA

**Test PASS ≠ DONE. Wymagane E2E.**

```bash
# Sekwencja weryfikacji:
python run_tests.py           # Unit + integration
python tests/e2e/test_*.py    # E2E (jeśli istnieje)
curl localhost:8080/health    # Backend żyje
curl localhost:3000           # Frontend żyje
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

**Version:** 9.1 | **Last Updated:** 2025-12-04
