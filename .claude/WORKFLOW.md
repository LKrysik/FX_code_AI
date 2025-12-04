# WORKFLOW - Autonomiczny Proces Pracy

**Wersja:** 6.0 | **Data:** 2025-12-04

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
- "Gdzie chciałbym wykazać swoje umiejętności?"

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

## FAZA 0: ANALIZA STANU PROGRAMU (Obowiązkowa na początku każdej sesji)

### 0.1 Weryfikacja Środowiska

```bash
# KROK 1: Sprawdź czy usługi działają
python run_tests.py
# → X/Y PASS

curl http://localhost:8080/health
# → {"status": "healthy"}

curl http://localhost:3000
# → HTML

# KROK 2: Jeśli cokolwiek FAIL → NAPRAW najpierw (P0)
```

### 0.2 Inwentaryzacja Funkcjonalności

Agent musi zidentyfikować i ocenić WSZYSTKIE istniejące komponenty:

```markdown
Dla każdego komponentu odpowiedz:
1. Co robi? (faktyczna funkcja, nie intencja)
2. Czy działa? (test + dowód)
3. Czy jest potrzebny dla celu biznesowego?
4. Jaki jest stan jakości? (skala 1-10)
5. Jakie ma zależności?
```

### 0.3 Macierz Oceny Programu (OBOWIĄZKOWA)

Agent wypełnia macierz przy każdej analizie:

```markdown
## MACIERZ OCENY PROGRAMU - [data]

| Obszar | Poprawność | Zgodność z celem | Użyteczność | Prostota użycia | Prostota utrzymania | Konfiguracja | Wydajność | Observability | Ryzyko regresji | ŚREDNIA |
|--------|------------|------------------|-------------|-----------------|---------------------|--------------|-----------|---------------|-----------------|---------|
| B1: API Server | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| B2: Strategy Manager | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| B3: Risk Manager | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| B4: Indicator Engine | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| B5: MEXC Adapter | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| B6: Order Manager | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| B7: Session Manager | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| B8: Event Bus | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| F1: Dashboard | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| F2: Strategy Builder | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| F3: Backtesting UI | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| F4: Live Trading UI | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| F5: Paper Trading UI | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| F6: Indicators UI | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| F7: Risk UI | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| F8: Charts | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| D1: QuestDB | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| D2: Data Collection | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |
| D3: Strategy Storage | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 | /10 |

**Interpretacja:**
- 1-3: Krytyczny problem, blokuje użycie
- 4-5: Słabe, wymaga znacznej pracy
- 6-7: Akceptowalne, ale wymaga poprawy
- 8-9: Dobre, drobne usprawnienia
- 10: Doskonałe, nie wymaga zmian

**Kolumny:**
- Poprawność: Czy kod robi to co powinien?
- Zgodność z celem: Czy służy celowi biznesowemu (trader)?
- Użyteczność: Czy trader może efektywnie używać?
- Prostota użycia: Czy jest intuicyjne?
- Prostota utrzymania: Czy kod jest czytelny i łatwy do modyfikacji?
- Konfiguracja: Czy można łatwo skonfigurować?
- Wydajność: Czy jest szybkie?
- Observability: Czy widać co się dzieje (logi, metryki)?
- Ryzyko regresji: Niskie (10) = bezpieczne zmiany, Wysokie (1) = kruche
```

### 0.4 GAP ANALYSIS (OBOWIĄZKOWA)

```markdown
## GAP ANALYSIS - [data]

### Brakujące funkcjonalności (czego nie ma, a powinno być)
| ID | Funkcjonalność | Wpływ na tradera | Złożoność | Priorytet |
|----|----------------|------------------|-----------|-----------|
| G1 | ... | Wysoki/Średni/Niski | Wysoka/Średnia/Niska | P0/P1/P2 |

### Niekompletne funkcjonalności (co jest, ale nie działa w pełni)
| ID | Funkcjonalność | Co brakuje | Wpływ na tradera | Priorytet |
|----|----------------|------------|------------------|-----------|
| I1 | ... | ... | ... | P0/P1/P2 |

### Placeholdery/TODO (co jest zadeklarowane ale nie zaimplementowane)
| ID | Lokalizacja | Treść | Wpływ | Priorytet |
|----|-------------|-------|-------|-----------|
| PH1 | plik:linia | TODO: ... | ... | P0/P1/P2 |

### Problemy techniczne (co psuje działanie)
| ID | Problem | Lokalizacja | Wpływ | Priorytet |
|----|---------|-------------|-------|-----------|
| T1 | ... | plik:linia | ... | P0/P1/P2 |

### Problemy architektoniczne
| ID | Problem | Wpływ | Pilność | Proponowane rozwiązanie |
|----|---------|-------|---------|-------------------------|
| A1 | ... | ... | ... | ... |

### Nadmiarowe elementy (do usunięcia)
| ID | Element | Dlaczego zbędny | Ryzyko usunięcia | Rekomendacja |
|----|---------|-----------------|------------------|--------------|
| R1 | ... | ... | ... | Usuń/Zostaw/Refaktoruj |
```

### 0.5 Problem Hunting (OBOWIĄZKOWE SKANOWANIE)

```bash
# Wykonaj przed każdą iteracją:

# 1. Placeholdery
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

### 1.1 Algorytm wyboru priorytetu

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

### 1.2 Priorytetyzacja oparta na wartości

```
WARTOŚĆ DLA TRADERA (wysoka) + ZŁOŻONOŚĆ (niska) = ZRÓB NAJPIERW
WARTOŚĆ DLA TRADERA (wysoka) + ZŁOŻONOŚĆ (wysoka) = ZAPLANUJ STARANNIE
WARTOŚĆ DLA TRADERA (niska) + ZŁOŻONOŚĆ (niska) = ZRÓB PRZY OKAZJI
WARTOŚĆ DLA TRADERA (niska) + ZŁOŻONOŚĆ (wysoka) = ODRZUĆ
```

### 1.3 Uzasadnienie decyzji (przed każdą zmianą)

```markdown
## UZASADNIENIE DECYZJI

### Co chcę zrobić?
[Konkretny opis zmiany/funkcjonalności]

### Jak to służy traderowi?
[Konkretny scenariusz użycia]

### Jakie jest ryzyko NIE zrobienia tego?
[Co trader traci]

### Jakie jest ryzyko ZROBIENIA tego?
[Regresje, złożoność]

### Czy istnieje prostsze rozwiązanie?
[Alternatywy]

### DECYZJA: [BUDUJ / POPRAW ISTNIEJĄCE / ODRZUĆ]
### UZASADNIENIE: [...]
```

---

## FAZA 2: ANALIZA PRZED ZMIANĄ (Obowiązkowa)

### 2.1 Analiza wpływu

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

### Historia zmian w tym obszarze
git log --oneline -10 [pliki]
- Ostatnia zmiana: [data, autor, cel]
```

### 2.2 Kontrola jakości przed zmianą

```markdown
## KONTROLA JAKOŚCI

### Dead code w obszarze zmiany
- [ ] Nieużywane funkcje: [lista lub "brak"]
- [ ] Nieużywane importy: [lista lub "brak"]

### Duplikacja kodu
- [ ] Czy podobna logika istnieje gdzie indziej? [tak/nie, gdzie]

### Spójność z architekturą
- [ ] Czy zmiana pasuje do istniejących wzorców? [tak/nie]
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

4. URUCHOM WSZYSTKIE TESTY
   - WSZYSTKIE muszą przechodzić
   - Pokaż output jako dowód
```

### 3.2 Checklist implementacji

```markdown
## CHECKLIST IMPLEMENTACJI

### Jakość kodu
- [ ] Brak dead code (usunięty jeśli był)
- [ ] Brak duplikacji (wykorzystane istniejące rozwiązania)
- [ ] Komentarze przy nieoczywistych decyzjach

### Testy
- [ ] Nowe testy dla nowej funkcjonalności (happy path + edge cases)
- [ ] Zaktualizowane testy dla zmienionej funkcjonalności
- [ ] Testy integracyjne (nie tylko jednostkowe)

### Dokumentacja
- [ ] Zmienione pliki udokumentowane w raporcie
- [ ] Decyzje biznesowe oznaczone komentarzem
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

### 4.2 Format raportu weryfikacji

```markdown
## WERYFIKACJA: [zadanie]

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

### GAP ANALYSIS po zmianie
[Tabela GAP ANALYSIS]

### Aktualizacja macierzy
| Obszar | Przed | Po | Zmiana |
|--------|-------|-----|--------|

### NASTĘPNY PRIORYTET
Na podstawie GAP ANALYSIS: [...]

WYNIK: DONE / NIE DONE (co brakuje: ...)
```

---

## FAZA 5: CIĄGŁA PĘTLA (NIGDY nie kończysz)

### 5.1 Po każdym zadaniu

```
1. Wykonaj GAP ANALYSIS
2. Zaktualizuj macierz oceny
3. Zidentyfikuj następny priorytet
4. NIE CZEKAJ na polecenie użytkownika
5. KONTYNUUJ do następnej iteracji

"Zadanie done" → NIE SUKCES → tylko krok do następnego zadania
```

### 5.2 Checkpoint (co 3-5 iteracji)

```markdown
## CHECKPOINT [data/godzina]

### Postęp sesji
- Iteracje: X
- Zadania ukończone: Y
- Metryki przed: [...]
- Metryki po: [...]
- Trend: ↑ / ↓ / →

### Macierz oceny - porównanie
| Warstwa | Przed | Po | Zmiana |
|---------|-------|-----|--------|
| Backend | X/10 | Y/10 | +/-Z |
| Frontend | X/10 | Y/10 | +/-Z |
| Database | X/10 | Y/10 | +/-Z |

### GAP ANALYSIS - pozostałe problemy
[Tabela]

### Następne priorytety
1. [P0] ...
2. [P1] ...
3. [P2] ...
```

---

## AUDYT JAKOŚCI (co 3-5 iteracji)

### Kategorie problemów do wykrycia

| Kategoria | Co szukać | Jak wykryć | Priorytet |
|-----------|-----------|------------|-----------|
| Brakujące implementacje | Wywołania nieistniejących metod | Analiza przepływu | P0 |
| Martwy kod | Funkcje/zmienne nigdy nie używane | grep/analiza | P2 |
| Placeholdery | TODO, FIXME, NotImplementedError, pass | grep | P0-P2 |
| Niespójne interfejsy | Komponent A oczekuje X, B zwraca Y | Analiza typów | P1 |
| Brakujące error handling | Kod bez try/catch | Analiza | P1 |
| Hardcoded values | Wartości które powinny być konfigurowalne | grep | P1-P2 |
| Race conditions | Współdzielone zasoby bez locków | Analiza async | P0 |
| Memory leaks | Struktury które rosną bez czyszczenia | Analiza | P1 |
| Brakujące testy | Krytyczny kod bez pokrycia | Coverage | P1 |
| UX problems | Błędy niezrozumiałe dla tradera | Symulacja Journey | P1 |

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

---

## HISTORIA ZMIAN WORKFLOW

| Wersja | Data | Zmiana | Uzasadnienie |
|--------|------|--------|--------------|
| 6.0 | 2025-12-04 | Dodano obowiązkową Macierz Oceny, rozbudowaną GAP ANALYSIS, wymuszenie ciągłej pętli | Agenci ogłaszali sukces przedwcześnie, nie szukali problemów, nie działali autonomicznie |
| 5.0 | 2025-12-02 | Dodano MOTOR DZIAŁANIA | Wewnętrzne mechanizmy motywujące |
| 4.1 | 2025-12-02 | Dodano AUDYT JAKOŚCI | Wykrywanie problemów poza testami |
| 4.0 | 2025-12-02 | Separacja od DoD | Workflow = proces, DoD = cele |

---

*Workflow definiuje JAK pracować. Cele i metryki są w [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md)*
