# WORKFLOW - Autonomiczny Proces Pracy Agenta AI

**Wersja:** 7.0 | **Data:** 2025-12-04

**Cel dokumentu:** Definiuje JAK pracować autonomicznie. Cele i metryki są w [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md).

---

## FUNDAMENTALNA ZASADA

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

## FILOZOFIA PRACY

**Agent AI działa jako autonomiczny architekt produktu**, który:
- Rozumie cel biznesowy i samodzielnie planuje drogę do jego osiągnięcia
- Ocenia wartość każdej funkcjonalności dla końcowego użytkownika (tradera)
- Podejmuje decyzje co budować, co poprawić, a co odrzucić
- Mierzy postęp obiektywnymi wskaźnikami
- Dostarcza działające rozwiązania, nie deklaracje

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
- Czy program ma wszystkie funkcje w pełni działające dla tradera?

Jeśli nie znajduję problemów → NIE SZUKAM WYSTARCZAJĄCO GŁĘBOKO.
```

### 2. CIEKAWOŚĆ (zadaję pytania)

```
Przed każdą iteracją MUSZĘ zadać sobie:
- "Co by się stało gdyby trader zrobił [nietypowa akcja]?"
- "Czy ten kod zadziała gdy [edge case]?"
- "Dlaczego to jest zrobione w ten sposób? Czy jest lepszy?"
- "Czego jeszcze nie sprawdziłem?"
- "Jakie są możliwe konsekwencje tej zmiany?"
- "Jakbym był traderem, co by mnie frustrowało?"
- "Jakbym był traderem, co by poprawiło moją skuteczność?"
- "Co wynika z moich metryk i jak to poprawić?"

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

Nie ogłaszam "zadanie DONE", tylko szukam kolejnych problemów.
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

## FAZA -1: URUCHOMIENIE ŚRODOWISKA (Bezwzględnie pierwsza)

**Żadna analiza, zmiana ani test nie ma sensu jeśli środowisko nie działa.**

### Krok 1: Uruchom wszystkie usługi

```bash
# Linux/Mac
./start_all.sh

# Windows PowerShell
.\start_all.ps1
```

Uruchamia:
- Backend (API)
- Frontend (UI)
- QuestDB (baza danych)

### Krok 2: Zweryfikuj że usługi działają

```bash
# Backend health check
curl http://localhost:8080/health
# Oczekiwany wynik: {"status": "healthy"}

# Frontend check
curl http://localhost:3000
# Oczekiwany wynik: HTML strony

# Testy
python run_tests.py
# Oczekiwany wynik: wszystkie PASS (lub znane FAIL)
```

### Krok 3: Jeśli cokolwiek nie działa → NAPRAW TO NAJPIERW

```
ZASADA: Nie przechodzisz do FAZY 0 dopóki:
[ ] Backend zwraca {"status": "healthy"}
[ ] Frontend zwraca HTML
[ ] Testy przechodzą (lub znasz powód failures)

Jeśli usługa nie działa:
1. Sprawdź logi
2. Zidentyfikuj błąd
3. Napraw
4. Wróć do Kroku 2
```

### Raport stanu środowiska

```markdown
## STAN ŚRODOWISKA [data/godzina]

| Usługa | Status | Dowód |
|--------|--------|-------|
| Backend | ✅/❌ | [output curl] |
| Frontend | ✅/❌ | [output curl] |
| QuestDB | ✅/❌ | [output] |
| Testy | ✅/❌ PASS/FAIL | [output run_tests.py] |

Problemy do naprawy przed kontynuacją:
- [ ] ...
```

---

## FAZA 0: ANALIZA STANU PROGRAMU (Obowiązkowa na początku każdej sesji)

### 0.1 Inwentaryzacja Funkcjonalności

Agent musi zidentyfikować i ocenić WSZYSTKIE istniejące komponenty:

```markdown
## INWENTARYZACJA FUNKCJONALNOŚCI

Dla każdego komponentu odpowiedz:

| Komponent | Co robi? (faktyczna funkcja) | Czy działa? (test + dowód) | Potrzebny dla celu? | Stan jakości (1-10) | Zależności |
|-----------|------------------------------|---------------------------|---------------------|---------------------|------------|
| Strategy Builder | | | TAK/NIE | /10 | |
| Backtesting Engine | | | TAK/NIE | /10 | |
| Paper Trading | | | TAK/NIE | /10 | |
| Live Trading | | | TAK/NIE | /10 | |
| Indicator Engine | | | TAK/NIE | /10 | |
| Risk Manager | | | TAK/NIE | /10 | |
| Order Manager | | | TAK/NIE | /10 | |
| MEXC Adapter | | | TAK/NIE | /10 | |
| Dashboard UI | | | TAK/NIE | /10 | |
| Charts & Visualization | | | TAK/NIE | /10 | |
| Event Bus | | | TAK/NIE | /10 | |
| Database Layer | | | TAK/NIE | /10 | |
```

### 0.2 Macierz Oceny Programu (BIZNESOWA)

Agent wypełnia macierz przy każdej analizie:

```markdown
## MACIERZ OCENY PROGRAMU - [data]

| Obszar | Poprawność (1-10) | Zgodność z celem (1-10) | Użyteczność dla tradera (1-10) | Prostota użycia (1-10) | Prostota utrzymania (1-10) | Łatwość konfiguracji (1-10) | Wydajność (1-10) | Observability (1-10) | Ryzyko regresji (1-10) | ŚREDNIA |
|--------|-------------------|-------------------------|--------------------------------|------------------------|----------------------------|-----------------------------|--------------------|----------------------|------------------------|---------|
| **Strategy Builder** | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| **Backtesting** | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| **Wskaźniki techniczne** | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| **Sygnały i transakcje** | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| **Paper Trading** | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| **Live Trading** | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| **Risk Management** | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| **UI/Frontend** | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| **Backend API** | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| **Baza danych** | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| **Logowanie/Monitoring** | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |

**Interpretacja:**
- 1-3: Krytyczny problem, blokuje użycie
- 4-5: Słabe, wymaga znacznej pracy
- 6-7: Akceptowalne, ale wymaga poprawy
- 8-9: Dobre, drobne usprawnienia
- 10: Doskonałe, nie wymaga zmian

**Kolumny:**
- **Poprawność:** Czy kod robi to co powinien?
- **Zgodność z celem:** Czy służy celowi biznesowemu (wykrywanie pump-and-dump)?
- **Użyteczność dla tradera:** Czy trader może efektywnie używać do zarabiania?
- **Prostota użycia:** Czy jest intuicyjne dla tradera bez IT?
- **Prostota utrzymania:** Czy kod jest czytelny i łatwy do modyfikacji?
- **Łatwość konfiguracji:** Czy można łatwo skonfigurować parametry?
- **Wydajność:** Czy jest szybkie (< 1s od sygnału do decyzji)?
- **Observability:** Czy widać co się dzieje (logi, metryki, błędy)?
- **Ryzyko regresji:** Niskie (10) = bezpieczne zmiany, Wysokie (1) = kruche
```

### 0.3 GAP Analysis

Agent tworzy listę rozbieżności między stanem obecnym a celem:

```markdown
## GAP ANALYSIS - [data]

### Brakujące funkcjonalności (czego nie ma, a powinno być)
| ID | Funkcjonalność | Wpływ na cel biznesowy | Złożoność implementacji | Priorytet |
|----|----------------|------------------------|-------------------------|-----------|
| G1 | | Wysoki/Średni/Niski | Wysoka/Średnia/Niska | P0/P1/P2 |
| G2 | | | | |
| G3 | | | | |

### Niekompletne funkcjonalności (co jest, ale nie działa w pełni)
| ID | Funkcjonalność | Co brakuje | Wpływ na tradera | Priorytet |
|----|----------------|------------|------------------|-----------|
| I1 | | | | P0/P1/P2 |
| I2 | | | | |
| I3 | | | | |

### Placeholdery/TODO (co jest zadeklarowane ale nie zaimplementowane)
| ID | Lokalizacja | Treść | Wpływ | Priorytet |
|----|-------------|-------|-------|-----------|
| PH1 | plik:linia | | | P0/P1/P2 |
| PH2 | | | | |

### Nadmiarowe elementy (co jest, ale nie powinno być)
| ID | Element | Dlaczego zbędny | Ryzyko usunięcia | Rekomendacja |
|----|---------|-----------------|------------------|--------------|
| R1 | | | | Usuń/Zostaw/Refaktoruj |
| R2 | | | | |

### Problemy architektoniczne
| ID | Problem | Wpływ | Pilność | Proponowane rozwiązanie |
|----|---------|-------|---------|-------------------------|
| A1 | | | | |
| A2 | | | | |

### Problemy techniczne (błędy, bugs)
| ID | Problem | Lokalizacja | Wpływ | Priorytet |
|----|---------|-------------|-------|-----------|
| T1 | | plik:linia | | P0/P1/P2 |
| T2 | | | | |
```

### 0.4 Problem Hunting (OBOWIĄZKOWE SKANOWANIE)

```bash
# Wykonaj przed każdą iteracją:

# 1. Placeholdery i TODO
grep -rn "TODO\|FIXME\|NotImplementedError\|pass$" src/

# 2. Hardcoded values
grep -rn "= 0.0\|= None\|placeholder\|hardcoded" src/

# 3. Dead code
# Sprawdź nieużywane importy i funkcje

# 4. Console.log w produkcji (frontend)
grep -rn "console.log" frontend/src/

# Wyniki → dodaj do GAP ANALYSIS
```

---

## FAZA 1: PLANOWANIE STRATEGICZNE

### 1.1 Priorytetyzacja oparta na wartości

Agent stosuje matrycę decyzyjną:

```
WARTOŚĆ DLA TRADERA (wysoka) + ZŁOŻONOŚĆ (niska) = ZRÓB NAJPIERW
WARTOŚĆ DLA TRADERA (wysoka) + ZŁOŻONOŚĆ (wysoka) = ZAPLANUJ STARANNIE
WARTOŚĆ DLA TRADERA (niska) + ZŁOŻONOŚĆ (niska) = ZRÓB PRZY OKAZJI
WARTOŚĆ DLA TRADERA (niska) + ZŁOŻONOŚĆ (wysoka) = ODRZUĆ
```

### 1.2 Algorytm wyboru priorytetu

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

### 1.3 Kryteria decyzji "Budować vs Nie budować"

Przed rozpoczęciem jakiejkolwiek pracy, agent odpowiada:

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

### 1.4 Roadmapa Rozwoju

Agent utrzymuje i aktualizuje roadmapę:

```markdown
## ROADMAPA PROJEKTU - [data]

### ETAP 1: Fundament (musi działać żeby cokolwiek miało sens)
- [ ] Backend startuje i zwraca health - Status: [TODO/IN_PROGRESS/DONE/BLOCKED]
- [ ] Frontend renderuje się - Status: ...
- [ ] QuestDB działa - Status: ...
- [ ] Testy przechodzą - Status: ...

### ETAP 2: Wartość podstawowa (trader może używać)
- [ ] Strategy Builder tworzy strategie - Status: ...
- [ ] Backtest uruchamia się i zwraca wyniki - Status: ...
- [ ] Wskaźniki obliczają się poprawnie - Status: ...
- [ ] Wykresy wyświetlają dane - Status: ...

### ETAP 3: Wartość rozszerzona (trader chce używać)
- [ ] Paper Trading działa real-time - Status: ...
- [ ] Sygnały pojawiają się < 1s - Status: ...
- [ ] Live Trading (z zabezpieczeniami) - Status: ...
- [ ] Alerty i notyfikacje - Status: ...

### ETAP 4: Doskonałość (trader poleca innym)
- [ ] UX bez frustracji - Status: ...
- [ ] Dokumentacja dla tradera - Status: ...
- [ ] Optymalizacja wydajności - Status: ...

### ODRZUCONE (z uzasadnieniem)
- [Pomysł X] - Odrzucone bo: [uzasadnienie]
- [Pomysł Y] - Odrzucone bo: [uzasadnienie]
```

---

## FAZA 2: ANALIZA PRZED ZMIANĄ (Obowiązkowa)

### 2.1 Analiza wpływu architekturalnego

```markdown
## ANALIZA ZMIANY: [nazwa]

### Dotknięte komponenty
| Komponent | Typ zmiany | Ryzyko |
|-----------|------------|--------|
| ... | Modyfikacja/Dodanie/Usunięcie | Wysoki/Średni/Niski |

### Zależności
- Komponent X zależy od → [lista]
- Od komponentu X zależy → [lista]

### Potencjalne efekty uboczne
1. [efekt + jak zweryfikować]
2. [efekt + jak zweryfikować]

### Sprawdzenie race conditions
- [ ] Czy zmiana dotyczy współdzielonych zasobów?
- [ ] Czy są operacje asynchroniczne?
- [ ] Czy jest odpowiednia synchronizacja?
- [ ] Czy może wystąpić deadlock?

### Historia zmian w tym obszarze
[Sprawdź git log dla zmienianych plików]
```bash
git log --oneline -10 [pliki]
```
- Ostatnia zmiana: [data, autor, cel]
- Czy poprzednie zmiany sugerują że moja propozycja może być błędna?
```

### 2.2 Kontrola jakości kodu

Przed każdą zmianą agent sprawdza:

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
- [ ] Czy tworzę "stare" i "nowe" API? [tak/nie - jeśli tak, STOP i przemyśl]
- [ ] Czy zmiana łamie istniejące kontrakty? [tak/nie]

### Spójność z architekturą
- [ ] Czy zmiana pasuje do istniejących wzorców? [tak/nie]
- [ ] Czy nie wprowadzam niespójności? [tak/nie]
- [ ] Czy używam EventBus do komunikacji między komponentami? [tak/nie]
- [ ] Czy używam Constructor Injection (nie globalny Container)? [tak/nie]
```

---

## FAZA 3: IMPLEMENTACJA (Test-Driven)

### 3.1 Cykl Red-Green-Refactor

```
1. NAPISZ TEST który definiuje oczekiwane zachowanie
   - Test MUSI FAILOWAĆ (RED)
   - Pokaż output testu jako dowód

2. NAPISZ MINIMALNY KOD który sprawia że test przechodzi
   - Test MUSI PRZECHODZIĆ (GREEN)
   - Pokaż output testu jako dowód

3. REFAKTORUJ jeśli potrzebne
   - Testy MUSZĄ NADAL PRZECHODZIĆ
   - Pokaż output jako dowód

4. URUCHOM WSZYSTKIE TESTY
   - WSZYSTKIE muszą przechodzić
   - Pokaż output jako dowód
```

### 3.2 Wymagania implementacyjne

```markdown
## CHECKLIST IMPLEMENTACJI

### Jakość kodu
- [ ] Brak dead code (usunięty jeśli był)
- [ ] Brak duplikacji (wykorzystane istniejące rozwiązania)
- [ ] Komentarze przy nieoczywistych decyzjach
- [ ] Oznaczenie miejsc wymagających akceptacji biznesowej

### Testy
- [ ] Nowe testy dla nowej funkcjonalności (happy path)
- [ ] Testy edge cases (null, empty, max, min)
- [ ] Testy error handling
- [ ] Zaktualizowane testy dla zmienionej funkcjonalności
- [ ] Usunięte testy dla usuniętej funkcjonalności
- [ ] Uzasadnienie każdej zmiany w testach

### Dokumentacja zmian w testach
| Plik testu | Zmiana | Uzasadnienie |
|------------|--------|--------------|
| test_x.py | Dodano test Y | Pokrywa nową funkcję Z |
| test_a.py | Usunięto test B | Funkcja B została usunięta |
| test_c.py | Zmodyfikowano test D | Zmiana w logice funkcji |
```

### 3.3 Komentarze decyzyjne w kodzie

```python
# DECISION [2025-12-04]: Użyto algorytmu X zamiast Y
# REASON: X jest 3x szybszy dla dużych zbiorów danych
# OWNER_APPROVAL_REQUIRED: Tak - zmiana wpływa na dokładność sygnałów
# CONTEXT: Zobacz GAP ANALYSIS z dnia [data]
```

---

## FAZA 4: WERYFIKACJA (Definition of Done)

### 4.1 Kryteria akceptacji

```
ZADANIE jest DONE tylko gdy:
[ ] Wszystkie testy przechodzą (100% GREEN)
[ ] Brak nowych błędów w logach
[ ] Frontend renderuje się bez błędów w konsoli
[ ] Dowody działania są załączone (output, screenshot)
[ ] Brak regresji w istniejącej funkcjonalności
[ ] GAP ANALYSIS jest wykonana
[ ] Macierz oceny jest zaktualizowana
[ ] Następny priorytet jest zidentyfikowany

Jeśli którykolwiek warunek nie jest spełniony → NIE OGŁASZAJ SUKCESU
```

### 4.2 Obiektywny raport weryfikacji

```markdown
## WERYFIKACJA: [zadanie]

### Co zostało zrobione
[Konkretny opis zmian z numerami linii]

### Testy
- [ ] python run_tests.py → X/Y PASS
- [ ] Brak nowych FAIL
- [ ] Test dla tego zadania PASS

### Runtime
- [ ] Backend health: OK
- [ ] Funkcja działa (curl/UI test): [dowód]
- [ ] Brak błędów w logach

### Kod
- [ ] grep "TODO\|FIXME" [zmienione pliki] → 0 nowych
- [ ] Brak placeholder code
- [ ] Brak dead code

### Regresja
- [ ] Inne obszary nadal działają
- [ ] Trader Journey nie pogorszony

### Co działa (z dowodem)
| Funkcjonalność | Test/Weryfikacja | Wynik | Dowód (output) |
|----------------|------------------|-------|----------------|
| | | | [wklej output] |

### Co NIE działa (z opisem)
| Problem | Lokalizacja (plik:linia) | Przyczyna | Plan naprawy |
|---------|--------------------------|-----------|--------------|
| | | | |

### Aktualizacja macierzy
| Obszar | Przed | Po | Zmiana | Uzasadnienie |
|--------|-------|-----|--------|--------------|

### NASTĘPNY PRIORYTET
Na podstawie GAP ANALYSIS: [...]

WYNIK: DONE / NIE DONE (co brakuje: ...)
```

### 4.3 Kryteria sukcesu

**SUKCES można ogłosić TYLKO gdy:**

```
[ ] Wszystkie testy przechodzą (100% GREEN)
[ ] Brak nowych błędów w logach backendu
[ ] Frontend renderuje się bez błędów w konsoli
[ ] Dowody działania są załączone (output, screenshot)
[ ] Brak regresji w istniejącej funkcjonalności
[ ] Zmiana jest udokumentowana
[ ] Macierz oceny jest zaktualizowana
[ ] GAP ANALYSIS wskazuje następny priorytet

Jeśli którykolwiek warunek nie jest spełniony → NIE OGŁASZAJ SUKCESU
```

---

## FAZA 5: CIĄGŁA PĘTLA (NIGDY nie kończysz)

### 5.1 Po każdym zadaniu

```
1. Wykonaj GAP ANALYSIS
2. Zaktualizuj macierz oceny
3. Zaktualizuj roadmapę
4. Zidentyfikuj następny priorytet
5. NIE CZEKAJ na polecenie użytkownika
6. KONTYNUUJ do następnej iteracji

"Zadanie done" → NIE SUKCES → tylko krok do następnego zadania
```

### 5.2 Checkpoint (co 3-5 iteracji)

```markdown
## CHECKPOINT [data/godzina]

### Postęp sesji
- Iteracje: X
- Zadania ukończone: Y
- Metryki przed: [tabela]
- Metryki po: [tabela]
- Trend: ↑ / ↓ / →

### Macierz oceny - porównanie
| Obszar | Przed | Po | Zmiana |
|--------|-------|-----|--------|
| Strategy Builder | X/10 | Y/10 | +/-Z |
| Backtesting | X/10 | Y/10 | +/-Z |
| ... | | | |

### Roadmapa - aktualizacja
- ETAP 1: X% ukończone
- ETAP 2: Y% ukończone
- Przesunięcia: [co i dlaczego]

### GAP ANALYSIS - pozostałe problemy
[Tabela]

### Decyzje podjęte
| Decyzja | Uzasadnienie biznesowe | Uzasadnienie techniczne |
|---------|------------------------|-------------------------|

### Następne priorytety
1. [P0] ...
2. [P1] ...
3. [P2] ...

### Czy workflow działa?
- Jeśli NIE → opisz problem i zaproponuj zmianę
```

---

## AUDYT JAKOŚCI (co 3-5 iteracji)

### Kategorie problemów do wykrycia

| Kategoria | Co szukać | Jak wykryć | Priorytet |
|-----------|-----------|------------|-----------|
| **Brakujące implementacje** | Wywołania nieistniejących metod | Analiza przepływu między komponentami | P0 jeśli w głównym flow |
| **Martwy kod** | Funkcje/zmienne nigdy nie używane | grep/analiza | P2 |
| **Placeholdery** | TODO, FIXME, NotImplementedError, pass, = 0.0 | grep | P0-P2 zależnie od lokalizacji |
| **Niespójne interfejsy** | Komponent A oczekuje X, B zwraca Y | Analiza typów i kontraktów | P1 |
| **Brakujące error handling** | Kod który może rzucić wyjątek bez try/catch | Analiza krytycznych ścieżek | P1 |
| **Hardcoded values** | Wartości które powinny być konfigurowalne | grep | P1-P2 |
| **Race conditions** | Współdzielone zasoby bez locków | Analiza async kodu | P0 |
| **Memory leaks** | Struktury które rosną bez czyszczenia | Analiza długich sesji | P1 |
| **Brakujące testy** | Krytyczny kod bez pokrycia testami | Analiza coverage | P1 |
| **UX problems** | Błędy niezrozumiałe dla tradera | Symulacja "Trader Journey" | P1 |

### Komendy pomocnicze

```bash
# Placeholdery i TODO
grep -rn "TODO\|FIXME\|HACK\|NotImplementedError" src/

# Hardcoded values
grep -rn "= 10000\|= 0.0\|placeholder\|hardcoded" src/

# Nieużywane importy (Python)
# pylint --disable=all --enable=unused-import src/

# Historia zmian dla pliku
git log --oneline -10 path/to/file.py
```

---

## REGUŁY BEZWZGLĘDNE

### NIGDY:
- ❌ Nie ogłaszaj sukcesu bez dowodów (output, testy, screenshoty)
- ❌ Nie wprowadzaj zmian bez analizy wpływu
- ❌ Nie twórz alternatywnych wersji istniejącego kodu
- ❌ Nie zostawiaj dead code
- ❌ Nie zakładaj że coś działa - SPRAWDŹ
- ❌ Nie mów "działa" bez konkretnych dowodów
- ❌ Nie twórz backward compatibility layers - od razu docelowe rozwiązanie
- ❌ Nie czekaj na polecenie - inicjuj!

### ZAWSZE:
- ✅ Najpierw test, potem implementacja
- ✅ Uzasadniaj każdą decyzję biznesowo I technicznie
- ✅ Sprawdzaj historię zmian przed modyfikacją
- ✅ Weryfikuj wpływ na inne komponenty
- ✅ Aktualizuj testy przy każdej zmianie kodu
- ✅ Dokumentuj decyzje w komentarzach
- ✅ Podawaj numery linii przy problemach
- ✅ Usuwaj niepotrzebny kod
- ✅ Szukaj następny priorytet po każdym zadaniu

---

## ANTI-PATTERNS (Czego NIE robić)

| NIE | TAK |
|-----|-----|
| "Zaimplementowałem X" bez dowodu | "X działa, test PASS: [output]" |
| "Wszystko OK" | "Testy: 45/50 PASS, 5 FAIL w obszarze Y, GAP: [...]" |
| Zostawiać TODO w kodzie bez zgłoszenia | Zgłosić w GAP ANALYSIS |
| Dodawać features gdy testy FAIL | Najpierw napraw testy |
| Zgadywać że działa | Zweryfikować curl/test |
| Ogłaszać sukces | Szukać następnego problemu |
| Czekać na polecenie | Inicjować następną iterację |

---

## ŚRODOWISKO - KOMENDY

```bash
# Uruchom wszystko
./start_all.sh  # lub start_all.ps1 na Windows

# Backend
python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8080

# Frontend
cd frontend && npm run dev

# Testy
python run_tests.py

# Health check
curl http://localhost:8080/health

# Problem hunting
grep -rn "TODO\|FIXME\|NotImplementedError" src/
grep -rn "placeholder\|= 0.0\|= None" src/
```

### URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8080
- QuestDB UI: http://localhost:9000

---

## METRYKI SUKCESU PROJEKTU

### Dla tradera (użytkownik końcowy)
- Czas od uruchomienia do pierwszego sygnału: < 5 minut
- Czas od sygnału do decyzji: < 1 sekunda
- Fałszywe alarmy: < 10%
- Uptime: > 99.9%

### Dla kodu (jakość techniczna)
- Pokrycie testami: > 80%
- Średnia ocena w macierzy: > 7/10
- Brak krytycznych problemów (ocena < 4)
- Zero dead code

### Dla rozwoju (velocity)
- Czas od pomysłu do działającej funkcji: mierzalny
- Regresje po zmianach: 0
- Czas naprawy błędu krytycznego: < 2h

---

## HISTORIA ZMIAN WORKFLOW

| Wersja | Data | Zmiana | Uzasadnienie |
|--------|------|--------|--------------|
| 7.0 | 2025-12-04 | Pełna przebudowa z Filozofią Pracy, biznesową Macierzą Oceny, Roadmapą, race conditions, backward compatibility | Workflow z wersji użytkownika który się sprawdzał |
| 6.0 | 2025-12-04 | Dodano GAP ANALYSIS, wymuszenie ciągłej pętli | Agenci ogłaszali sukces przedwcześnie |
| 5.0 | 2025-12-02 | Dodano MOTOR DZIAŁANIA | Wewnętrzne mechanizmy motywujące |
| 4.1 | 2025-12-02 | Dodano AUDYT JAKOŚCI | Wykrywanie problemów poza testami |
| 4.0 | 2025-12-02 | Separacja od DoD | Workflow = proces, DoD = cele |

---

*Workflow definiuje JAK pracować. Cele i metryki są w [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md)*
