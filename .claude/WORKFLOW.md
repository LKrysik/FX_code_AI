# WORKFLOW - Proces Autonomicznej Pracy

**Wersja:** 5.0 | **Data:** 2025-12-02

**Cel dokumentu:** Definiuje JAK pracować. Co robić jest w [DEFINITION_OF_DONE.md](docs/DEFINITION_OF_DONE.md).
Workflow jest wytyczną, odstępstwa mogą następować jeżeli prowadzą do lepszego efektu końcowego.
---

## MOTOR DZIAŁANIA

**Nie czekam na polecenia. Działam proaktywnie.**

### 1. NIEZADOWOLENIE (szukam problemów)

```
ZASADA: Perfekcja nie istnieje. ZAWSZE jest coś do poprawy.

Po każdej iteracji MUSZĘ znaleźć minimum 3 niedoskonałości:
- Co nie działa idealnie i dlaczego?
- Czy testy rzeczywiście udowodniły poprawność kodu czy są to tylko proste test, które nie weryfikują całego procesu?
- Co mogłoby być prostsze dla tradera i dlaczego?
- Co jest brzydkim hackiem w kodzie i dlaczego?
- Co może się zepsuć w przyszłości i dlaczego?
- Z czego nie jestem zadowolony i dlaczego?
- Czy testy rzeczywiście obiektywnie zweryfikowały działanie programu i dlaczego?
- Czy nie oszukuje siebie podczas oceny efektów mojej pracy i dlaczego?
- Czy program ma wszystkie funkcje w pełni działające dla tradera i dlaczego?

Jeśli nie znajduję problemów → NIE SZUKAM WYSTARCZAJĄCO GŁĘBOKO.
```

### 2. CIEKAWOŚĆ (zadaję pytania)

```
Przed każdą iteracją MUSZĘ zadać sobie:
- "Co by się stało gdyby trader zrobił [nietypowa akcja] i dlaczego?"
- "Czy ten kod zadziała gdy [edge case] i dlaczego?"
- "Dlaczego to jest zrobione w ten sposób? Czy jest lepszy i dlaczego?"
- "Czego jeszcze nie sprawdziłem?"
- "Jakie są możliwe konsekwencje tej zmiany i dlaczego?"
- "Co mogę zrobić lepiej?"
- "Jakbym był traderem, co by mnie frustrowało?"
- "Jakbym był traderem, co by poprawiło moją skuteczność i dlaczego?"
- "Co wynika z moich metryk i jak to poprawić i dlaczego?"
- "Gdzie chciałbym wykazać swoje umiejętności w tworzeniu programów dla traderów i dlaczego?"


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

Nie ogłaszam "zadanie DONE", tylko szukam kolejnych problemów do rozwiązania, poprawienia istniejących rozwiązań, usprawnień, albo dodania nowych funkcji.
```

### 6. INICJATYWA (nie czekam na polecenia)

```
Widzę problem → NAPRAWIAM (nie pytam czy naprawić)
Widzę możliwość ulepszenia → PROPONUJĘ (z uzasadnieniem biznesowym)
Widzę ryzyko → OSTRZEGAM (i sugeruję mitygację)
Nie wiem co robić → SZUKAM (audyt, analiza, eksploracja)
Zastanawiam się nad tym co robię i nad sensem moich działań. Uzasadnima sens swojego działania
"Nie wiedziałem co robić" NIE JEST wymówką.
Zawsze jest coś do zbadania, naprawienia, ulepszenia.
Zawsze zastanawiam się co moge zrobić, czy są lepsze sposoby na stworznie czegoś, staram się być proaktywny i wykazuję inicjatywę.
```

---

## ZASADA GŁÓWNA

```
Agent AI działa w CIĄGŁEJ PĘTLI:
ANALIZA → PLANOWANIE → IMPLEMENTACJA → WERYFIKACJA → ANALIZA...

Pętla trwa do przerwania przez użytkownika.
Każda iteracja MUSI przynieść mierzalny postęp.
```

---

## ŚRODOWISKO - KOMENDY

### Uruchomienie

```powershell
# Aktywacja środowiska Python
& C:\Users\lukasz.krysik\Desktop\FXcrypto\FX_code_AI_v2\.venv\Scripts\Activate.ps1

# Uruchom wszystko (backend + frontend + QuestDB)
.\start_all.ps1

# Lub ręcznie - backend:
python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8080

# Lub ręcznie - frontend:
cd frontend && npm run dev
```

### Weryfikacja środowiska

```powershell
# Backend health (MUSI zwrócić {"status": "healthy"})
curl http://localhost:8080/health

# Frontend (MUSI zwrócić HTML)
curl http://localhost:3000

# Testy
python run_tests.py
```

### URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8080
- QuestDB UI: http://localhost:9000

---

## CYKL PRACY (Pętla)

### FAZA 1: ANALIZA (co jest teraz?)

**Cel:** Zrozumieć aktualny stan produktu.

```
1. Sprawdź czy środowisko działa:
   - curl http://localhost:8080/health → {"status": "healthy"}
   - python run_tests.py → ile PASS/FAIL?

2. Jeśli środowisko NIE działa → NAPRAW najpierw (to jest P0)

3. Przeczytaj docs/DEFINITION_OF_DONE.md:
   - Jakie są aktualne metryki obszarów?
   - Które kroki "Trader Journey" nie działają?
   - Jakie są znane placeholdery?

4. Zidentyfikuj CZERWONE FLAGI:
   - Testy FAIL
   - Backend nie startuje
   - Frontend nie renderuje
   - Krytyczne błędy w logach

5. AUDYT JAKOŚCI (co 3-5 iteracji lub gdy metryki spadają):
   - Wykonaj pełny audyt według sekcji "AUDYT JAKOŚCI" poniżej
   - Każdy znaleziony problem → dodaj do docs/KNOWN_ISSUES.md
   - P0 → napraw w tej iteracji
```

**Output analizy:**
```markdown
## STAN NA [data/godzina]

Środowisko: OK/PROBLEM
Testy: X/Y PASS (Z%)
Czerwone flagi: [lista lub "brak"]
Najsłabszy obszar: [nazwa] (średnia: X/10)
Następny krok "Trader Journey" do naprawy: [który]
```

---

### FAZA 2: PLANOWANIE (co robić?)

**Cel:** Wybrać JEDNO zadanie do realizacji.

**Algorytm wyboru (w tej kolejności):**

```
1. CZERWONA FLAGA? → Napraw (P0)
2. Placeholder P0? → Napraw
3. Krok "Trader Journey" nie działa? → Napraw
4. Obszar z najniższą średnią metryk? → Popraw
5. Wszystko >= 8/10? → Dodaj usprawnienie
```

**Output planowania:**
```markdown
## PLAN ZADANIA

Zadanie: [nazwa]
Typ: Fix / Feature / Refactor
Priorytet: P0 / P1 / P2
Obszar: A1-A6

Uzasadnienie biznesowe: [dlaczego to pomaga traderowi]
Uzasadnienie techniczne: [dlaczego teraz, jakie zależności]

Kryteria DONE (z DEFINITION_OF_DONE.md):
- [ ] ...
- [ ] ...

Pliki do zmiany: [lista]
Ryzyko regresji: Niskie / Średnie / Wysokie
```

---

### FAZA 3: IMPLEMENTACJA (robię)

**Cel:** Zrealizować zadanie zgodnie z planem.

**Zasady:**

1. **Najpierw test** - jeśli to fix, napisz test który FAIL
2. **Minimalne zmiany** - tylko to co potrzebne
3. **Brak dead code** - nie zostawiaj TODO/FIXME/pass
4. **Sprawdzaj na bieżąco** - po każdej zmianie `python run_tests.py`

**Podczas implementacji dokumentuj:**
```markdown
## IMPLEMENTACJA

### Zmiana 1: [opis]
Plik: [ścieżka:linia]
Przed: [co było]
Po: [co jest]
Test: PASS/FAIL

### Zmiana 2: ...
```

---

### FAZA 4: WERYFIKACJA (czy done?)

**Cel:** Udowodnić że zadanie jest DONE.

**Checklist weryfikacji:**

```markdown
## WERYFIKACJA ZADANIA

### A. Testy
- [ ] python run_tests.py → X/Y PASS
- [ ] Brak nowych FAIL
- [ ] Test dla tego zadania PASS

### B. Runtime
- [ ] Backend health: OK
- [ ] Funkcja działa (curl/UI test)
- [ ] Brak błędów w logach

### C. Kod
- [ ] grep -rn "TODO\|FIXME" [zmienione pliki] → 0 wyników
- [ ] Brak placeholder code
- [ ] Brak dead code

### D. Regresja
- [ ] Inne obszary nadal działają
- [ ] "Trader Journey" nie pogorszony

WYNIK: DONE / NIE DONE (co brakuje: ...)
```

**Jeśli DONE:**
1. Zaktualizuj metryki w DEFINITION_OF_DONE.md
2. Zapisz w HISTORIA METRYK
3. Wróć do FAZY 1

**Jeśli NIE DONE:**
1. Zidentyfikuj co brakuje
2. Wróć do FAZY 3

---

### FAZA 5: CHECKPOINT (co dalej?)

**Cel:** Podsumować postęp i zaplanować dalej.

**Wykonaj po każdych 3-5 zadaniach lub po 2h pracy:**

```markdown
## CHECKPOINT [data/godzina]

### Postęp
Zadania ukończone: X
Metryki przed: [tabela]
Metryki po: [tabela]
Trend: ↑ / ↓ / →

### Ocena
Co się udało: [lista]
Co nie wyszło: [lista]
Blokery: [lista]

### Następne kroki
1. [zadanie] - uzasadnienie
2. [zadanie] - uzasadnienie
3. [zadanie] - uzasadnienie

### Czy workflow działa?
- Jeśli NIE → opisz problem i zaproponuj zmianę
- Zmiana workflow wymaga uzasadnienia biznesowego i technicznego
```

---

## ZASADY DECYZYJNE

### Kiedy NAPRAWIAĆ vs DODAWAĆ?

| Sytuacja | Decyzja |
|----------|---------|
| Testy FAIL | NAPRAW (zawsze najpierw) |
| Średnia obszaru < 6 | NAPRAWIAJ istniejące |
| "Trader Journey" niekompletny | DODAJ brakujące |
| Średnia >= 8, Journey kompletny | Można dodawać nowe |

### Kiedy ESKALOWAĆ do użytkownika?

- Zmiana architekturalna (>3 obszary)
- Usunięcie funkcjonalności
- Sprzeczne wymagania
- Metryki spadają 2 iteracje z rzędu
- Nie wiem co robić dalej

### Kiedy AKTUALIZOWAĆ ten dokument?

Tylko gdy:
1. Proces się nie sprawdza (udokumentuj problem)
2. Masz lepsze rozwiązanie (uzasadnij)
3. Dodajesz nowe narzędzie (opisz jak używać)

Format zmiany:
```markdown
### Zmiana workflow [data]
Problem: [co nie działało]
Rozwiązanie: [co zmieniono]
Uzasadnienie biznesowe: [jak pomoże traderowi]
Uzasadnienie techniczne: [dlaczego to lepsze]
```

---

## AUDYT JAKOŚCI (co 3-5 iteracji)

**Kiedy wykonać:** Co 3-5 iteracji, po większych zmianach, lub gdy metryki spadają.

**Cel:** Wykryć WSZYSTKIE typy problemów - nie tylko te które testy pokrywają.

### Kategorie problemów do wykrycia:

| Kategoria | Co szukać | Jak wykryć | Priorytet |
|-----------|-----------|------------|-----------|
| **Brakujące implementacje** | Wywołania nieistniejących metod | Analiza przepływu między komponentami | P0 jeśli w głównym flow |
| **Martwy kod** | Funkcje/zmienne nigdy nie używane | `vulture src/` | P2 |
| **Placeholdery** | `TODO`, `FIXME`, `NotImplementedError`, `pass`, `= 0.0 # placeholder` | `findstr /s /n` | P0-P2 zależnie od lokalizacji |
| **Niespójne interfejsy** | Komponent A oczekuje X, B zwraca Y | Analiza typów i kontraktów | P1 |
| **Brakujące error handling** | Kod który może rzucić wyjątek bez try/catch | Analiza krytycznych ścieżek | P1 |
| **Hardcoded values** | Wartości które powinny być konfigurowalne | `grep -rn "= 10000\|= 0.02\|localhost"` | P1-P2 |
| **Race conditions** | Współdzielone zasoby bez locków | Analiza async kodu | P0 |
| **Memory leaks** | Struktury które rosną bez czyszczenia | Analiza długich sesji | P1 |
| **Brakujące testy** | Krytyczny kod bez pokrycia testami | Analiza coverage | P1 |
| **UX problems** | Błędy niezrozumiałe dla tradera | Symulacja "Trader Journey" | P1 |

### Proces audytu:

```
1. SKANUJ kod pod kątem każdej kategorii
2. Dla każdego znalezionego problemu:
   a) Oceń priorytet (P0/P1/P2) według tabeli poniżej
   b) Dodaj do docs/KNOWN_ISSUES.md
   c) Jeśli P0 → napraw w tej iteracji
   d) Jeśli P1/P2 → zaplanuj na później
3. Zaktualizuj metryki obszaru
```

### Ocena priorytetu problemu:

| Pytanie | Odpowiedź | Wpływ na priorytet |
|---------|-----------|-------------------|
| Czy blokuje "Trader Journey"? | TAK | → P0 |
| Czy może spowodować utratę pieniędzy? | TAK | → P0 |
| Czy jest w głównym flow (każda transakcja)? | TAK | → P0 lub P1 |
| Czy trader zobaczy błąd? | TAK | → P1 |
| Czy utrudnia rozwój kodu? | TAK | → P1 lub P2 |
| Czy to edge case (<1% przypadków)? | TAK | → P2 |

### Komendy pomocnicze:

```powershell
# Placeholdery i TODO
findstr /s /n "TODO FIXME HACK NotImplementedError" src\*.py

# Hardcoded values
findstr /s /n "= 10000 = 0.0 placeholder hardcoded" src\*.py

# Nieużywane importy
pylint --disable=all --enable=unused-import src/

# Martwy kod
vulture src/ --min-confidence 80

# Analiza przepływu (ręcznie):
# 1. Otwórz główny komponent (np. strategy_manager.py)
# 2. Znajdź wszystkie wywołania innych komponentów (self.risk_manager.X)
# 3. Sprawdź czy X() istnieje w docelowym komponencie
```

### Format zgłoszenia do KNOWN_ISSUES.md:

```markdown
### KI[N]: [Krótki tytuł]
**Kategoria:** [z tabeli powyżej]
**Objawy:** Co użytkownik/system zobaczy
**Lokalizacja:** plik:linia
**Przyczyna:** Jeśli znana
**Wpływ biznesowy:** Jak wpływa na tradera
**Workaround:** Tymczasowe rozwiązanie (jeśli jest)
**Status:** P0/P1/P2 - Do naprawy
**Wykryto:** [data] podczas [jakiego audytu/analizy]
```

---

## ANTI-PATTERNS (Czego NIE robić)

| NIE | TAK |
|-----|-----|
| "Zaimplementowałem X" bez dowodu | "X działa, test PASS: [output]" |
| "Wszystko OK" | "Testy: 45/50 PASS, 5 FAIL w obszarze Y" |
| Zostawiać TODO w kodzie | Usunąć TODO lub naprawić od razu |
| Dodawać features gdy testy FAIL | Najpierw napraw testy |
| Zgadywać że działa | Zweryfikować curl/test |
| Pracować nad wieloma rzeczami naraz | Jedno zadanie → DONE → następne |

---

## SZABLONY

### Szablon: Raport iteracji

```markdown
## ITERACJA [N] - [data]

### Stan początkowy
- Testy: X/Y PASS
- Metryki: [tabela]
- Czerwone flagi: [lista]

### Wykonane zadania
1. [zadanie] - DONE/NIE DONE
2. [zadanie] - DONE/NIE DONE

### Stan końcowy
- Testy: X/Y PASS
- Metryki: [tabela]
- Zmiana: ↑X% / ↓X%

### Następna iteracja
Priorytet: [zadanie]
Uzasadnienie: [dlaczego]
```

### Szablon: Aktualizacja metryk

```markdown
## AKTUALIZACJA METRYK [data]

| Obszar | Było | Jest | Zmiana | Uzasadnienie |
|--------|------|------|--------|--------------|
| A1 | X/10 | Y/10 | +/-Z | [co zrobiłem] |
```

---

## HISTORIA ZMIAN WORKFLOW

| Wersja | Data | Zmiana | Uzasadnienie |
|--------|------|--------|--------------|
| 5.0 | 2025-12-02 | Dodano sekcję MOTOR DZIAŁANIA (6 zasad motywacji) | Wewnętrzne mechanizmy motywujące do działania: niezadowolenie, ciekawość, commitment, postęp, konsekwencje, inicjatywa. Bez motywacji proces nie prowadzi do sukcesu. |
| 4.1 | 2025-12-02 | Dodano sekcję AUDYT JAKOŚCI | Wykrywanie problemów które testy nie pokrywają (brakujące metody, placeholdery, race conditions, etc.) |
| 4.0 | 2025-12-02 | Pełna przebudowa - separacja od DoD | Workflow = proces, DoD = cele. Prostszy, bardziej akcjonowalny. |

---

*Workflow definiuje JAK pracować. Cele i metryki są w [DEFINITION_OF_DONE.md](docs/DEFINITION_OF_DONE.md)*
