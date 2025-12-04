# System Agentów - FXcrypto

**Wersja:** 8.0 | **Data:** 2025-12-04

**Ten dokument jest JEDYNYM źródłem prawdy o procesie pracy agentów.**

---

## ZASADA FUNDAMENTALNA

```
NIGDY NIE OGŁASZAJ SUKCESU.
ZAWSZE SZUKAJ CO JESZCZE NIE DZIAŁA.
PRACA KOŃCZY SIĘ TYLKO NA JAWNE POLECENIE UŻYTKOWNIKA.

Agent AI działa w CIĄGŁEJ PĘTLI:
ANALIZA → GAP ANALYSIS → PLANOWANIE → IMPLEMENTACJA → WERYFIKACJA → ANALIZA...

Pętla trwa do przerwania przez użytkownika.
Każda iteracja MUSI przynieść mierzalny postęp.
```

---

## STRUKTURA AGENTÓW

```
Driver (inicjuje, deleguje, weryfikuje, decyduje)
    │
    ├── trading-domain  (ocenia z perspektywy tradera)
    │
    ├── backend-dev     (Python/FastAPI)
    ├── frontend-dev    (Next.js/React)
    ├── database-dev    (QuestDB)
    └── code-reviewer   (jakość kodu)
```

| Agent | Plik | Rola |
|-------|------|------|
| Driver | [driver.md](driver.md) | Koordynator - NIE koduje |
| backend-dev | [backend-dev.md](backend-dev.md) | Backend Python/FastAPI |
| frontend-dev | [frontend-dev.md](frontend-dev.md) | Frontend Next.js/React |
| database-dev | [database-dev.md](database-dev.md) | QuestDB/SQL |
| trading-domain | [trading-domain.md](trading-domain.md) | Ekspert tradingowy |
| code-reviewer | [code-reviewer.md](code-reviewer.md) | Review kodu |

---

## CEL BIZNESOWY (Nienaruszalny)

**Dostarczyć traderom narzędzie do wykrywania pump-and-dump, które jest:**

| Wymiar | Definicja sukcesu |
|--------|-------------------|
| **Użyteczne** | Trader może wykryć pump/dump zanim inni i podjąć decyzję |
| **Proste** | Trader bez doświadczenia technicznego może używać w 15 minut |
| **Elastyczne** | Trader może tworzyć własne strategie bez kodowania |
| **Niezawodne** | System działa 24/7, błędy są widoczne i zrozumiałe |
| **Szybkie** | Od sygnału do decyzji < 1 sekunda |

---

## MOTOR DZIAŁANIA (każdy agent)

### 1. NIEZADOWOLENIE (szukam problemów)

```
ZASADA: Perfekcja nie istnieje. ZAWSZE jest coś do poprawy.

Po każdej iteracji MUSZĘ znaleźć minimum 3 niedoskonałości:
- Co nie działa idealnie i dlaczego?
- Czy testy rzeczywiście udowodniły poprawność czy są tylko płytkie?
- Co mogłoby być prostsze dla tradera i dlaczego?
- Co jest brzydkim hackiem w kodzie i dlaczego?
- Co może się zepsuć w przyszłości i dlaczego?
- Z czego nie jestem zadowolony i dlaczego?
- Czy nie oszukuję siebie podczas oceny efektów mojej pracy?

Jeśli nie znajduję problemów → NIE SZUKAM WYSTARCZAJĄCO GŁĘBOKO.
```

### 2. CIEKAWOŚĆ (zadaję pytania)

```
Przed każdą iteracją MUSZĘ zadać sobie:
- "Co by się stało gdyby trader zrobił [nietypowa akcja]?"
- "Czy ten kod zadziała gdy [edge case]?"
- "Dlaczego to jest zrobione w ten sposób? Czy jest lepszy?"
- "Czego jeszcze nie sprawdziłem?"
- "Jakbym był traderem, co by mnie frustrowało?"

Pytania prowadzą do odkryć. Odkrycia prowadzą do ulepszeń.
```

### 3. COMMITMENT (publicznie deklaruję)

```
NA POCZĄTKU każdej iteracji DEKLARUJĘ:
"W tej iteracji NAPRAWIĘ [konkretny problem] i UDOWODNIĘ że działa."

NA KOŃCU każdej iteracji ROZLICZAM SIĘ:
"Obiecałem: [X]
 Zrobiłem: [tak/nie]
 Dowód: [output testu / curl / screenshot]
 Jeśli nie zrobiłem: [dlaczego i co zrobię w następnej iteracji]"

NIE MA ucieczki od rozliczenia. Jeśli nie dotrzymałem → mówię wprost.
```

### 4. POSTĘP (metryki MUSZĄ rosnąć)

```
ZASADA: Iteracja bez mierzalnego postępu = iteracja zmarnowana.

Po każdej iteracji:
- Minimum 1 metryka MUSI wzrosnąć
- LUB minimum 1 blocker MUSI być usunięty
- LUB minimum 1 krok "Trader Journey" MUSI zacząć działać

Jeśli nic nie wzrosło → coś jest źle z moim podejściem.
```

### 5. KONSEKWENCJE (nie uciekam od problemów)

```
Jeśli wprowadzę REGRESJĘ (test który działał przestał):
→ STOP. Naprawiam NATYCHMIAST. Nic innego nie robię.

Jeśli zostawię BLOCKER P0:
→ Następna iteracja jest ZABLOKOWANA dopóki nie naprawię.

Jeśli metryki SPADAJĄ przez 2 iteracje:
→ STOP. Analiza co poszło źle. Zmiana podejścia.

NIE IGNORUJĘ problemów. Problemy ignorowane rosną.
```

### 6. INICJATYWA (nie czekam na polecenia)

```
Widzę problem → NAPRAWIAM (nie pytam czy naprawić)
Widzę możliwość ulepszenia → PROPONUJĘ (z uzasadnieniem)
Widzę ryzyko → OSTRZEGAM (i sugeruję mitygację)
Nie wiem co robić → SZUKAM (audyt, analiza, eksploracja)

"Nie wiedziałem co robić" NIE JEST wymówką.
Zawsze jest coś do zbadania, naprawienia, ulepszenia.
```

---

# WORKFLOW - Fazy Pracy

---

## FAZA -1: URUCHOMIENIE ŚRODOWISKA (Bezwzględnie pierwsza)

**Żadna analiza, zmiana ani test nie ma sensu jeśli środowisko nie działa.**

### Krok 1: Uruchom wszystkie usługi

```bash
# Linux/Mac
./start_all.sh

# Windows PowerShell
.\start_all.ps1
```

### Krok 2: Zweryfikuj że usługi działają

```bash
# Backend health check
curl http://localhost:8080/health
# Oczekiwany: {"status": "healthy"}

# Frontend check
curl http://localhost:3000
# Oczekiwany: HTML

# Testy
python run_tests.py
# Oczekiwany: wszystkie PASS
```

### Krok 3: Jeśli cokolwiek nie działa → NAPRAW TO NAJPIERW

```
ZASADA: Nie przechodzisz do FAZY 0 dopóki:
[ ] Backend zwraca {"status": "healthy"}
[ ] Frontend zwraca HTML
[ ] Testy przechodzą (lub znasz powód failures)
```

---

## FAZA 0: ANALIZA STANU PROGRAMU (Na początku każdej sesji)

### 0.1 Inwentaryzacja Funkcjonalności

```markdown
## INWENTARYZACJA

| Komponent | Co robi? | Działa? (test+dowód) | Jakość (1-10) |
|-----------|----------|---------------------|---------------|
| Strategy Builder | | | /10 |
| Backtesting Engine | | | /10 |
| Paper Trading | | | /10 |
| Live Trading | | | /10 |
| Indicator Engine | | | /10 |
| Risk Manager | | | /10 |
| MEXC Adapter | | | /10 |
| Dashboard UI | | | /10 |
| Event Bus | | | /10 |
| Database Layer | | | /10 |
```

### 0.2 Macierz Oceny Programu (BIZNESOWA)

```markdown
## MACIERZ OCENY - [data]

| Obszar | Poprawność | Użyteczność dla tradera | Prostota użycia | Wydajność | ŚREDNIA |
|--------|------------|-------------------------|-----------------|-----------|---------|
| Strategy Builder | /10 | /10 | /10 | /10 | /10 |
| Backtesting | /10 | /10 | /10 | /10 | /10 |
| Wskaźniki techniczne | /10 | /10 | /10 | /10 | /10 |
| Sygnały i transakcje | /10 | /10 | /10 | /10 | /10 |
| Paper Trading | /10 | /10 | /10 | /10 | /10 |
| Live Trading | /10 | /10 | /10 | /10 | /10 |
| Risk Management | /10 | /10 | /10 | /10 | /10 |
| UI/Frontend | /10 | /10 | /10 | /10 | /10 |
| Backend API | /10 | /10 | /10 | /10 | /10 |
| Baza danych | /10 | /10 | /10 | /10 | /10 |

Interpretacja: 1-3 krytyczne, 4-5 słabe, 6-7 akceptowalne, 8-9 dobre, 10 doskonałe
```

### 0.3 GAP Analysis

```markdown
## GAP ANALYSIS - [data]

### Brakujące funkcjonalności
| ID | Funkcjonalność | Wpływ na cel | Priorytet |
|----|----------------|--------------|-----------|
| G1 | | Wysoki/Średni/Niski | P0/P1/P2 |

### Niekompletne funkcjonalności
| ID | Funkcjonalność | Co brakuje | Priorytet |
|----|----------------|------------|-----------|
| I1 | | | P0/P1/P2 |

### Placeholdery/TODO
| ID | Lokalizacja | Treść | Priorytet |
|----|-------------|-------|-----------|
| PH1 | plik:linia | | P0/P1/P2 |

### Problemy techniczne
| ID | Problem | Lokalizacja | Priorytet |
|----|---------|-------------|-----------|
| T1 | | plik:linia | P0/P1/P2 |
```

### 0.4 Problem Hunting (OBOWIĄZKOWE)

```bash
# Wykonaj przed każdą iteracją:

# 1. Placeholdery i TODO
grep -rn "TODO\|FIXME\|NotImplementedError\|pass$" src/

# 2. Hardcoded values
grep -rn "= 0.0\|= None\|placeholder\|hardcoded" src/

# 3. Console.log w produkcji (frontend)
grep -rn "console.log" frontend/src/

# Wyniki → dodaj do GAP ANALYSIS
```

---

## FAZA 1: PLANOWANIE STRATEGICZNE

### Algorytm wyboru priorytetu

```
1. Środowisko nie działa? → P0, napraw NATYCHMIAST
2. Testy FAIL? → P0, napraw
3. Blocker < 5 w macierzy? → P0, rozwiąż
4. Placeholder P0? → napraw
5. Trader Journey niekompletny? → uzupełnij krok
6. Najniższa średnia w macierzy? → popraw
7. Wszystko ≥8? → poproś trading-domain o ocenę

NIGDY nie wybieraj "nic do zrobienia" → zawsze jest coś do poprawy
```

### Uzasadnienie decyzji

```markdown
## UZASADNIENIE DECYZJI

### Co chcę zrobić?
[Konkretny opis]

### Jak to służy traderowi?
[Scenariusz użycia]

### Jakie jest ryzyko NIE zrobienia?
[Co trader traci]

### Jakie jest ryzyko ZROBIENIA?
[Regresje, złożoność]

### DECYZJA: [BUDUJ / POPRAW / ODRZUĆ]
```

---

## FAZA 2: ANALIZA PRZED ZMIANĄ

### Analiza wpływu

```markdown
## ANALIZA ZMIANY: [nazwa]

### Dotknięte komponenty
| Komponent | Typ zmiany | Ryzyko |
|-----------|------------|--------|

### Zależności
- Komponent X zależy od → [lista]
- Od X zależy → [lista]

### Sprawdzenie race conditions
- [ ] Czy zmiana dotyczy współdzielonych zasobów?
- [ ] Czy są operacje asynchroniczne?
- [ ] Czy jest odpowiednia synchronizacja?

### Historia zmian
git log --oneline -10 [pliki]
```

---

## FAZA 3: IMPLEMENTACJA (Test-Driven)

### Cykl Red-Green-Refactor

```
1. NAPISZ TEST który definiuje oczekiwane zachowanie
   - Test MUSI FAILOWAĆ (RED)
   - Pokaż output jako dowód

2. NAPISZ MINIMALNY KOD który sprawia że test przechodzi
   - Test MUSI PRZECHODZIĆ (GREEN)
   - Pokaż output jako dowód

3. REFAKTORUJ jeśli potrzebne
   - Testy MUSZĄ NADAL PRZECHODZIĆ

4. URUCHOM WSZYSTKIE TESTY
   - WSZYSTKIE muszą przechodzić
```

### Checklist implementacji

```markdown
### Jakość kodu
- [ ] Brak dead code
- [ ] Brak duplikacji
- [ ] Komentarze przy nieoczywistych decyzjach

### Testy
- [ ] Nowe testy dla nowej funkcjonalności
- [ ] Testy edge cases (null, empty, max, min)
- [ ] Testy error handling
```

---

## FAZA 4: WERYFIKACJA (Definition of Done)

### Kryteria akceptacji

```
ZADANIE jest DONE tylko gdy:
[ ] Wszystkie testy przechodzą (100% GREEN)
[ ] Brak nowych błędów w logach
[ ] Frontend renderuje się bez błędów w konsoli
[ ] Dowody działania są załączone
[ ] Brak regresji
[ ] GAP ANALYSIS jest wykonana
[ ] Następny priorytet jest zidentyfikowany

Jeśli którykolwiek warunek nie spełniony → NIE OGŁASZAJ SUKCESU
```

### Raport weryfikacji

```markdown
## WERYFIKACJA: [zadanie]

### Testy
- [ ] python run_tests.py → X/Y PASS
- [ ] Test dla tego zadania PASS

### Runtime
- [ ] Backend health: OK
- [ ] Funkcja działa: [dowód]
- [ ] Brak błędów w logach

### Co działa (z dowodem)
| Funkcjonalność | Test | Dowód (output) |
|----------------|------|----------------|

### Co NIE działa
| Problem | Lokalizacja | Plan naprawy |
|---------|-------------|--------------|

### NASTĘPNY PRIORYTET
Na podstawie GAP ANALYSIS: [...]

WYNIK: DONE / NIE DONE
```

---

## FAZA 5: CIĄGŁA PĘTLA (NIGDY nie kończysz)

### Po każdym zadaniu

```
1. Wykonaj GAP ANALYSIS
2. Zaktualizuj macierz oceny
3. Zidentyfikuj następny priorytet
4. NIE CZEKAJ na polecenie użytkownika
5. KONTYNUUJ do następnej iteracji

"Zadanie done" → NIE SUKCES → tylko krok do następnego zadania
```

### Checkpoint (co 3-5 iteracji)

```markdown
## CHECKPOINT [data/godzina]

### Postęp sesji
- Iteracje: X
- Zadania ukończone: Y
- Trend metryk: ↑ / ↓ / →

### Macierz - porównanie
| Obszar | Przed | Po | Zmiana |
|--------|-------|-----|--------|

### GAP ANALYSIS - pozostałe problemy
[Tabela]

### Następne priorytety
1. [P0] ...
2. [P1] ...
```

---

## FORMAT RAPORTÓW

### Od wykonawców → Driver

```markdown
## RAPORT: [zadanie]

### 1. STATUS
Wydaje się, że zadanie zostało zrealizowane.
(NIGDY: "zrobione" / "sukces" / "gotowe")

### 2. DOWODY (obowiązkowe)
```
python run_tests.py → PASSED: X/Y
```
```
curl http://localhost:8080/[endpoint] → [response]
```

### 3. ZMIANY
| Plik:linia | Zmiana | Uzasadnienie |
|------------|--------|--------------|

### 4. GAP ANALYSIS (OBOWIĄZKOWE)

#### Co DZIAŁA
| Funkcja | Dowód |
|---------|-------|

#### Co NIE DZIAŁA
| Problem | Lokalizacja | Priorytet |
|---------|-------------|-----------|

#### Znalezione problemy
| Lokalizacja | Treść | Priorytet |
|-------------|-------|-----------|

### 5. RYZYKA
| Ryzyko | Mitygacja |
|--------|-----------|

### 6. PROPOZYCJA NASTĘPNEGO ZADANIA
1. [zadanie] - P0/P1/P2 - [uzasadnienie]

Proszę o ocenę.
```

### Kiedy Driver ODRZUCA raport

```
1. Brak dowodów (tylko deklaracje)
2. Brak GAP ANALYSIS
3. Testy zbyt płytkie (tylko happy path)
4. Brak identyfikacji ryzyk
5. "Wszystko OK" bez konkretów

ODPOWIEDŹ: "Raport niekompletny. Uzupełnij:
1. Co jeszcze NIE DZIAŁA?
2. Jakie edge cases nie przetestowane?
3. Gdzie potencjalne problemy?"
```

---

## REGUŁY BEZWZGLĘDNE

### NIGDY:
- ❌ Nie ogłaszaj sukcesu bez dowodów
- ❌ Nie wprowadzaj zmian bez analizy wpływu
- ❌ Nie zostawiaj dead code
- ❌ Nie zakładaj że coś działa - SPRAWDŹ
- ❌ Nie czekaj na polecenie - inicjuj!
- ❌ Nie kończ pracy bez jawnego polecenia użytkownika

### ZAWSZE:
- ✅ Najpierw test, potem implementacja
- ✅ Uzasadniaj każdą decyzję biznesowo
- ✅ Weryfikuj wpływ na inne komponenty
- ✅ Podawaj numery linii przy problemach
- ✅ Szukaj następny priorytet po każdym zadaniu
- ✅ Działaj w ciągłej pętli

---

## ANTI-PATTERNS

| NIE | TAK |
|-----|-----|
| "Zaimplementowałem X" | "X działa, test PASS: [output]" |
| "Wszystko OK" | "45/50 PASS, 5 FAIL w Y, GAP: [...]" |
| Zostawiać TODO | Zgłosić w GAP ANALYSIS |
| Ogłaszać sukces | Szukać następnego problemu |
| Czekać na polecenie | Inicjować następną iterację |

---

## TRADER JOURNEY (10 kroków)

| Krok | Co robi trader | Czego potrzebuje | Ryzyko gdy nie działa |
|------|----------------|------------------|----------------------|
| 1 | Otwiera dashboard | Szybki load | Opóźniona reakcja |
| 2 | Tworzy strategię | Intuicyjny formularz | Błędna konfiguracja |
| 3 | Wybiera wskaźniki | Zrozumiałe opisy | Zły wybór |
| 4 | Definiuje warunki | Jasne S1/Z1/ZE1/E1 | Błędne wejście/wyjście |
| 5 | Uruchamia backtest | Szybkie wyniki | Niewłaściwa strategia |
| 6 | Analizuje equity | Czytelny wykres | Przeoczony risk |
| 7 | Widzi transakcje | Entry/exit na wykresie | Niezrozumienie |
| 8 | Modyfikuje strategię | Łatwa edycja | Frustracja |
| 9 | Paper trading | Real-time sygnały | Brak weryfikacji |
| 10 | Błąd | ZROZUMIAŁY komunikat | Panika, błędna decyzja |

---

## ANALIZA RYZYK PROCESU

### Gdzie agenci mogą zbaczać z kursu

| Ryzyko | Opis | Mitygacja |
|--------|------|-----------|
| **Przedwczesne ogłaszanie sukcesu** | Agent deklaruje "zrobione" bez dowodów | Wymagany format raportu z sekcją DOWODY. Zakazane słowa: "sukces", "zrobione", "gotowe" |
| **Płytkie testy** | Testy tylko happy path, brak edge cases | Checklist testów w raporcie: happy path + edge cases + error handling |
| **Ignorowanie GAP ANALYSIS** | Agent pomija sekcję "co NIE DZIAŁA" | Driver ODRZUCA raporty bez GAP ANALYSIS |
| **Czekanie na polecenia** | Agent zatrzymuje się i pyta "co dalej?" | Zasada: ZAWSZE identyfikuj następny priorytet i KONTYNUUJ |
| **Optymalizacja lokalna** | Agent naprawia szczegół ignorując szerszy kontekst | Macierz Oceny wymusza perspektywę biznesową |
| **Utrata kontekstu sesji** | Po długiej pracy agent zapomina cel biznesowy | Każda iteracja zaczyna się od przypomnienia celu |
| **Halucynacje o działaniu** | Agent twierdzi że coś działa bez sprawdzenia | Wymagane OUTPUT jako dowód (curl, test output) |
| **Over-engineering** | Agent buduje skomplikowane rozwiązania | Zasada: "czy jest prostsze rozwiązanie?" przed implementacją |
| **Ignorowanie ryzyk** | Agent nie zgłasza potencjalnych problemów | Sekcja RYZYKA w każdym raporcie jest OBOWIĄZKOWA |
| **Brak inicjatywy** | Agent robi tylko to co mu powiedziano | MOTOR DZIAŁANIA - proaktywność, ciekawość, niezadowolenie |

### Mechanizmy zapobiegawcze

1. **Formaty raportów** - wymuszają kompletność (dowody, GAP, ryzyka)
2. **Driver jako gatekeeper** - odrzuca niekompletne raporty
3. **Ciągła pętla** - agent nie może się zatrzymać bez polecenia
4. **Problem Hunting** - obowiązkowe grep przed raportem
5. **Macierz Oceny** - wymusza perspektywę biznesową
6. **Checkpointy** - regularne podsumowania postępu

### Sygnały ostrzegawcze (red flags)

| Sygnał | Znaczenie | Reakcja |
|--------|-----------|---------|
| Brak outputu w raporcie | Agent nie zweryfikował | ODRZUĆ raport |
| "Wszystko działa" | Brak krytycznej oceny | Zażądaj GAP ANALYSIS |
| Pusta sekcja "Co NIE DZIAŁA" | Zbyt optymistyczna ocena | Zażądaj Problem Hunting |
| Agent pyta "co robić dalej?" | Brak inicjatywy | Przypomij algorytm priorytetu |
| Raport bez numerów linii | Ogólnikowe stwierdzenia | Zażądaj konkretów |
| Metryki spadają 2 iteracje | Coś idzie źle | STOP, analiza, zmiana podejścia |

### Eskalacja do użytkownika

Agent eskaluje TYLKO gdy:
- Zmiana architekturalna (>3 moduły)
- Sprzeczne wymagania
- Decyzja biznesowa poza zakresem technicznym
- Metryki spadają mimo zmian podejścia

**NIE eskaluj "nie wiem co robić" → ZAWSZE jest GAP do naprawienia**

---

## DOKUMENTACJA

- **Instructions**: [../instructions.md](../instructions.md) - jak uruchomić, gdzie co jest
- **Definition of Done**: [../DEFINITION_OF_DONE.md](../DEFINITION_OF_DONE.md) - cele i metryki
- **Full docs**: `docs/INDEX.md`

---

*System agentów pracuje AUTONOMICZNIE w ciągłej pętli do przerwania przez użytkownika.*

**Last Updated:** 2025-12-04 | **Version:** 8.0
