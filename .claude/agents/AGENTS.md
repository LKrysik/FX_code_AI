# System Agentów - FXcrypto

**Wersja:** 10.0 | **Data:** 2025-12-04

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

#### 0.2 Macierz Oceny Programu - KOMPLETNA

Agent wypełnia CAŁĄ macierz przy KAŻDEJ analizie. Nie pomijaj kolumn.

##### TABELA A: Funkcjonalność i Jakość

```markdown
## MACIERZ A: FUNKCJONALNOŚĆ - [data]

| Obszar | Poprawność | Zgodność z celem | Użyteczność | Prostota użycia | Prostota utrzymania |
|--------|------------|------------------|-------------|-----------------|---------------------|
| Strategy Builder | /10 | /10 | /10 | /10 | /10 |
| Backtesting | /10 | /10 | /10 | /10 | /10 |
| Wskaźniki | /10 | /10 | /10 | /10 | /10 |
| Sygnały/Transakcje | /10 | /10 | /10 | /10 | /10 |
| Paper Trading | /10 | /10 | /10 | /10 | /10 |
| Live Trading | /10 | /10 | /10 | /10 | /10 |
| Risk Management | /10 | /10 | /10 | /10 | /10 |
| UI/Frontend | /10 | /10 | /10 | /10 | /10 |
| Backend API | /10 | /10 | /10 | /10 | /10 |
| Baza danych | /10 | /10 | /10 | /10 | /10 |
| Monitoring | /10 | /10 | /10 | /10 | /10 |
| Event Bus | /10 | /10 | /10 | /10 | /10 |
| WebSocket | /10 | /10 | /10 | /10 | /10 |
| Authentication | /10 | /10 | /10 | /10 | /10 |
```

##### TABELA B: Aspekty Techniczne

```markdown
## MACIERZ B: TECHNICZNE - [data]

| Obszar | Security | Skalowalność | Testability | Error Handling | Wydajność |
|--------|----------|--------------|-------------|----------------|-----------|
| Strategy Builder | /10 | /10 | /10 | /10 | /10 |
| Backtesting | /10 | /10 | /10 | /10 | /10 |
| Wskaźniki | /10 | /10 | /10 | /10 | /10 |
| Sygnały/Transakcje | /10 | /10 | /10 | /10 | /10 |
| Paper Trading | /10 | /10 | /10 | /10 | /10 |
| Live Trading | /10 | /10 | /10 | /10 | /10 |
| Risk Management | /10 | /10 | /10 | /10 | /10 |
| UI/Frontend | /10 | /10 | /10 | /10 | /10 |
| Backend API | /10 | /10 | /10 | /10 | /10 |
| Baza danych | /10 | /10 | /10 | /10 | /10 |
| Monitoring | /10 | /10 | /10 | /10 | /10 |
| Event Bus | /10 | /10 | /10 | /10 | /10 |
| WebSocket | /10 | /10 | /10 | /10 | /10 |
| Authentication | /10 | /10 | /10 | /10 | /10 |
```

##### TABELA C: Integracja i Dokumentacja

```markdown
## MACIERZ C: INTEGRACJA - [data]

| Obszar | Integracja z innymi | Dokumentacja kodu | Zależności | Observability | Ryzyko regresji |
|--------|---------------------|-------------------|------------|---------------|-----------------|
| Strategy Builder | /10 | /10 | /10 | /10 | /10 |
| Backtesting | /10 | /10 | /10 | /10 | /10 |
| Wskaźniki | /10 | /10 | /10 | /10 | /10 |
| Sygnały/Transakcje | /10 | /10 | /10 | /10 | /10 |
| Paper Trading | /10 | /10 | /10 | /10 | /10 |
| Live Trading | /10 | /10 | /10 | /10 | /10 |
| Risk Management | /10 | /10 | /10 | /10 | /10 |
| UI/Frontend | /10 | /10 | /10 | /10 | /10 |
| Backend API | /10 | /10 | /10 | /10 | /10 |
| Baza danych | /10 | /10 | /10 | /10 | /10 |
| Monitoring | /10 | /10 | /10 | /10 | /10 |
| Event Bus | /10 | /10 | /10 | /10 | /10 |
| WebSocket | /10 | /10 | /10 | /10 | /10 |
| Authentication | /10 | /10 | /10 | /10 | /10 |
```

##### JAK OCENIAĆ KAŻDĄ KOLUMNĘ (konkretne komendy)

```bash
# POPRAWNOŚĆ - uruchom testy dla modułu:
pytest tests/test_[modul].py -v
# 10/10 = wszystkie PASS, 5/10 = >50% PASS, 1/10 = crash/brak testów

# ZGODNOŚĆ Z CELEM - sprawdź czy funkcja służy traderowi:
grep -rn "trader\|strategy\|signal\|backtest" src/[modul]/
# 10/10 = bezpośrednio dla tradera, 5/10 = pośrednio, 1/10 = niepowiązane

# UŻYTECZNOŚĆ - sprawdź czy są gotowe endpointy/funkcje:
grep -rn "async def\|def " src/[modul]/ | wc -l
# Porównaj z użytymi w API: grep -rn "[nazwa_funkcji]" src/api/

# PROSTOTA UŻYCIA - policz argumenty funkcji publicznych:
grep -rn "def [a-z_]*(" src/[modul]/ | head -10
# 10/10 = max 3 argumenty, 5/10 = 5-7, 1/10 = >10 argumentów

# PROSTOTA UTRZYMANIA - sprawdź złożoność:
wc -l src/[modul]/*.py
# 10/10 = <200 linii/plik, 5/10 = 200-500, 1/10 = >1000

# SECURITY - szukaj luk:
grep -rn "password\|secret\|key\|token" src/[modul]/ --include="*.py"
grep -rn "eval\|exec\|os.system\|subprocess" src/[modul]/
grep -rn "SELECT.*%" src/[modul]/  # SQL injection
# 10/10 = brak wyników, 1/10 = hardcoded secrets

# SKALOWALNOŚĆ - szukaj wąskich gardeł:
grep -rn "for.*for\|while.*while" src/[modul]/  # nested loops
grep -rn "global\|singleton" src/[modul]/
# 10/10 = brak, 5/10 = 1-2, 1/10 = >5 miejsc

# TESTABILITY - sprawdź dependency injection:
grep -rn "def __init__" src/[modul]/ -A 5
# 10/10 = wszystkie zależności przez konstruktor
# 1/10 = import globalnych instancji

# ERROR HANDLING - sprawdź try/except:
grep -rn "try:" src/[modul]/ | wc -l
grep -rn "except Exception:" src/[modul]/ | wc -l  # złe - zbyt ogólne
grep -rn "except [A-Z][a-zA-Z]*Error:" src/[modul]/ | wc -l  # dobre - konkretne
# 10/10 = wszystkie except konkretne, 1/10 = bare except lub brak

# WYDAJNOŚĆ - szukaj potencjalnych problemów:
grep -rn "time.sleep\|\.all()\|for.*in.*query" src/[modul]/
# 10/10 = brak, 1/10 = sleep w krytycznej ścieżce

# INTEGRACJA - sprawdź czy używa EventBus:
grep -rn "event_bus\|EventBus\|publish\|subscribe" src/[modul]/
# 10/10 = komunikacja przez EventBus, 1/10 = bezpośrednie wywołania

# DOKUMENTACJA KODU - sprawdź docstringi:
grep -rn '"""' src/[modul]/ | wc -l
# Podziel przez liczbę funkcji - 10/10 = każda ma docstring

# ZALEŻNOŚCI - sprawdź imports:
grep -rn "^import\|^from" src/[modul]/*.py | sort | uniq
# 10/10 = tylko stdlib + projekt, 5/10 = zewnętrzne stabilne, 1/10 = wiele zewnętrznych

# OBSERVABILITY - sprawdź logging:
grep -rn "logger\|logging\|\.info\|\.error\|\.debug" src/[modul]/
# 10/10 = logi w każdej ważnej funkcji, 1/10 = brak logów

# RYZYKO REGRESJI - sprawdź historię:
git log --oneline -10 -- src/[modul]/
# 10/10 = stabilny (mało zmian), 1/10 = ciągłe zmiany bez testów
```

Interpretacja ogólna: 1-3 krytyczne, 4-5 słabe, 6-7 akceptowalne, 8-9 dobre, 10 doskonałe

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

#### 0.4 Matryca Pomysłów - GENEROWANIE USPRAWNIEŃ

Agent MUSI wygenerować pomysły używając KONKRETNYCH komend, nie "przemyśleń":

##### KROK 1: Wyciągnij pomysły z dokumentacji

```bash
# Sprawdź co jest w DEFINITION_OF_DONE ale nie zrobione:
cat DEFINITION_OF_DONE.md 2>/dev/null || echo "PLIK NIE ISTNIEJE - STWÓRZ"

# Sprawdź co jest w docs/ jako funkcjonalność:
ls docs/*.md 2>/dev/null && head -50 docs/*.md

# Sprawdź README:
head -100 README.md 2>/dev/null
```

##### KROK 2: Wyciągnij pomysły z kodu

```bash
# TODO/FIXME w kodzie = pomysły programistów:
grep -rn "TODO\|FIXME\|XXX\|HACK" src/ --include="*.py"

# NotImplementedError = brakujące funkcje:
grep -rn "NotImplementedError\|raise NotImplemented" src/

# Placeholder wartości = niedokończone:
grep -rn "= 0\.0\|= None\|placeholder\|dummy\|mock\|fake" src/ --include="*.py"

# pass w funkcjach = puste implementacje:
grep -rn "def.*:$" -A 2 src/ | grep -B 1 "pass$"
```

##### KROK 3: Wyciągnij pomysły z testów

```bash
# Testy z skip = coś nie działa:
grep -rn "@pytest.mark.skip\|@unittest.skip\|skipIf\|skipUnless" tests/

# Testy z TODO = brakujące testy:
grep -rn "TODO\|FIXME" tests/

# Puste testy:
grep -rn "def test_.*:$" -A 2 tests/ | grep -B 1 "pass$"
```

##### KROK 4: Wyciągnij pomysły z Trader Journey

```markdown
Dla każdego kroku Trader Journey (1-10) odpowiedz:

| Krok | Co trader robi | Czy działa? (test) | Pomysł na poprawę |
|------|----------------|-------------------|-------------------|
| 1. Otwiera dashboard | GET / | curl localhost:3000 → ? | |
| 2. Tworzy strategię | POST /strategies | curl -X POST → ? | |
| 3. Wybiera wskaźniki | UI indicators | Ręczny test UI | |
| 4. Definiuje warunki | Strategy conditions | test_conditions.py | |
| 5. Uruchamia backtest | POST /backtest | curl -X POST → ? | |
| 6. Analizuje equity | GET /backtest/results | curl → ? | |
| 7. Widzi transakcje | Trade history | test_trades.py | |
| 8. Modyfikuje strategię | PUT /strategies | curl -X PUT → ? | |
| 9. Paper trading | WebSocket /ws | wscat → ? | |
| 10. Błąd = zrozumiały | Error messages | test_errors.py | |
```

##### KROK 5: Priorytetyzuj pomysły

```markdown
## MATRYCA POMYSŁÓW - [data]

### ŹRÓDŁO: Dokumentacja
| ID | Pomysł | Źródło (plik:linia) | WARTOŚĆ dla tradera (1-5) | WYSIŁEK (1-5) | PRIORYTET |
|----|--------|---------------------|---------------------------|---------------|-----------|
| D1 | | | | | |

### ŹRÓDŁO: Kod (TODO/FIXME)
| ID | Pomysł | Źródło (plik:linia) | WARTOŚĆ dla tradera (1-5) | WYSIŁEK (1-5) | PRIORYTET |
|----|--------|---------------------|---------------------------|---------------|-----------|
| C1 | | | | | |

### ŹRÓDŁO: Testy
| ID | Pomysł | Źródło (plik:linia) | WARTOŚĆ dla tradera (1-5) | WYSIŁEK (1-5) | PRIORYTET |
|----|--------|---------------------|---------------------------|---------------|-----------|
| T1 | | | | | |

### ŹRÓDŁO: Trader Journey
| ID | Pomysł | Krok Journey | WARTOŚĆ dla tradera (1-5) | WYSIŁEK (1-5) | PRIORYTET |
|----|--------|--------------|---------------------------|---------------|-----------|
| J1 | | | | | |

### ŹRÓDŁO: Własna analiza (na podstawie Macierzy Oceny)
| ID | Pomysł | Obszar z niską oceną | WARTOŚĆ dla tradera (1-5) | WYSIŁEK (1-5) | PRIORYTET |
|----|--------|---------------------|---------------------------|---------------|-----------|
| A1 | | | | | |

### ALGORYTM PRIORYTETYZACJI:
PRIORYTET = (WARTOŚĆ × 2) - WYSIŁEK
- P0 (natychmiast): PRIORYTET >= 7
- P1 (ważne): PRIORYTET 4-6
- P2 (nice-to-have): PRIORYTET 1-3
- ODRZUĆ: PRIORYTET <= 0

### TOP 3 POMYSŁY DO REALIZACJI:
1. [ID]: [opis] - Priorytet: X
2. [ID]: [opis] - Priorytet: X
3. [ID]: [opis] - Priorytet: X
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

### FAZA 5: REFLEKSJA NAD PROCESEM (OBOWIĄZKOWA na końcu każdej sesji)

**Cel:** Agent ocenia czy PROCES (ten dokument) pomaga czy przeszkadza w osiąganiu celu.

```
📋 REFERENCJA: Korzystam z AGENTS.md sekcja "FAZA 5: REFLEKSJA"

📌 PLAN DALEJ:
1. Odpowiadam na pytania refleksyjne
2. Identyfikuję słabości procesu
3. Proponuję konkretne zmiany
```

#### 5.1 Kwestionariusz Refleksji (wypełnij KONKRETNIE)

```markdown
## REFLEKSJA NAD PROCESEM - [data]

### A. Co poszło DOBRZE dzięki procesowi?
| Sytuacja | Która sekcja AGENTS.md pomogła | Jak pomogła |
|----------|-------------------------------|-------------|
| [sytuacja] | [sekcja X.Y] | [konkretnie jak] |

### B. Co poszło ŹLE mimo procesu?
| Problem | Która sekcja POWINNA była pomóc | Dlaczego nie pomogła |
|---------|--------------------------------|---------------------|
| [problem] | [sekcja X.Y lub "BRAK SEKCJI"] | [zbyt ogólna / niejasna / błędna / brak] |

### C. Gdzie PROCES prowadził do fałszywego "wszystko działa"?
| Co agent powiedział | Co było w rzeczywistości | Luka w procesie |
|---------------------|-------------------------|-----------------|
| "[cytat agenta]" | [fakt] | [co w procesie pozwoliło na ten błąd] |

### D. Które instrukcje były ZBYT OGÓLNE?
| Instrukcja z AGENTS.md | Dlaczego zbyt ogólna | Propozycja konkretnej wersji |
|------------------------|---------------------|------------------------------|
| "[cytat]" | [brak komendy / brak przykładu / niejednoznaczna] | [konkretna wersja] |

### E. Czego BRAKOWAŁO w procesie?
| Sytuacja bez wsparcia | Co byłoby potrzebne | Priorytet |
|----------------------|---------------------|-----------|
| [sytuacja] | [konkretna sekcja/instrukcja] | Wysoki/Średni/Niski |
```

#### 5.2 Weryfikacja Obiektywności Procesu

Agent wykonuje następujące sprawdzenia:

```bash
# 1. Czy proces wymaga DOWODÓW czy akceptuje DEKLARACJE?
grep -c "dowód\|output\|curl\|pytest\|test_" .claude/agents/AGENTS.md
# Wynik > 20 = dobry, < 10 = za mało wymogów na dowody

# 2. Czy proces ma KONKRETNE komendy czy OGÓLNIKI?
grep -c "grep\|curl\|python\|wc -l\|head\|cat" .claude/agents/AGENTS.md
# Wynik > 30 = dobry, < 15 = za mało konkretów

# 3. Ile razy proces używa słów "rozważ", "przemyśl", "może"?
grep -ci "rozważ\|przemyśl\|może\|powinien\|warto" .claude/agents/AGENTS.md
# Wynik < 5 = dobry, > 10 = za dużo ogólników

# 4. Czy każda tabela ma przykład wypełnienia?
grep -c "np\.\|przykład\|/10" .claude/agents/AGENTS.md
# Wynik > 20 = dobry
```

#### 5.3 Propozycje Ulepszeń Procesu

```markdown
## PROPOZYCJE ULEPSZEŃ - [data]

### PRIORYTET WYSOKI (blokuje osiąganie celu)
| ID | Problem w procesie | Linia w AGENTS.md | Proponowana zmiana | Uzasadnienie |
|----|-------------------|-------------------|-------------------|--------------|
| P1 | | około linii X | | |

### PRIORYTET ŚREDNI (utrudnia pracę)
| ID | Problem w procesie | Linia w AGENTS.md | Proponowana zmiana | Uzasadnienie |
|----|-------------------|-------------------|-------------------|--------------|
| P2 | | około linii X | | |

### PRIORYTET NISKI (kosmetyka)
| ID | Problem w procesie | Linia w AGENTS.md | Proponowana zmiana | Uzasadnienie |
|----|-------------------|-------------------|-------------------|--------------|
| P3 | | około linii X | | |

### PODSUMOWANIE
- Proces pomógł w: [X z Y zadań]
- Proces nie pomógł w: [Z z Y zadań]
- Główna słabość: [jedno zdanie]
- Priorytet #1 do poprawy: [ID z powyższej tabeli]
```

#### 5.4 Kiedy ESKALOWAĆ problemy z procesem

```
ESKALUJ DO UŻYTKOWNIKA jeśli:
[ ] Ten sam problem wystąpił 2+ razy mimo stosowania procesu
[ ] Proces wymaga czegoś co nie jest możliwe w tym środowisku
[ ] Instrukcje procesu są sprzeczne ze sobą
[ ] Brak sekcji dla częstego scenariusza

FORMAT ESKALACJI:
"PROBLEM Z PROCESEM:
- Scenariusz: [co próbowałem zrobić]
- Instrukcja z procesu: [cytat z AGENTS.md]
- Dlaczego nie działa: [konkret]
- Propozycja: [konkretna zmiana]"
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

**Version:** 10.0 | **Last Updated:** 2025-12-04
