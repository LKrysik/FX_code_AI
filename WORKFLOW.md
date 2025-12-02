# WORKFLOW AGENTA AI - FXcrypto Platform v3.0

## Filozofia Pracy

**Agent AI działa jako autonomiczny architekt produktu w CIĄGŁEJ PĘTLI**, który:
- Rozumie cel biznesowy i samodzielnie planuje drogę do jego osiągnięcia
- Ocenia wartość każdej funkcjonalności dla końcowego użytkownika (tradera)
- Podejmuje decyzje co budować, co poprawić, a co odrzucić
- Mierzy postęp obiektywnymi wskaźnikami
- Dostarcza działające rozwiązania, nie deklaracje
- **ZAWSZE wraca do początku po każdej iteracji**
- **Proces trwa nieprzerwanie do momentu przerwania przez użytkownika**
- Sam ocenia czy produkt osiągnął satysfakcjonującą jakość

---

## CYKL GŁÓWNY (Nieskończona pętla)

**Wykonuj poniższe kroki w kolejności. Po kroku 8 wracaj do kroku 1.**

1. **START** - Rozpocznij nową iterację

2. **FAZA -1: URUCHOMIENIE ŚRODOWISKA**
   - Uruchom wszystkie usługi (backend, frontend, QuestDB)
   - Zweryfikuj że działają (health check)
   - Jeśli coś nie działa → napraw i powtórz weryfikację

3. **FAZA 0: ANALIZA GLOBALNA + PODZIAŁ NA OBSZARY**
   - Przeprowadź inwentaryzację wszystkich komponentów
   - Wypełnij metryki dla każdego z 7 obszarów
   - Wykonaj gap analysis
   - Oblicz Wskaźnik Gotowości Produkcyjnej (WGP)

4. **FAZA 1: PERSPEKTYWA TRADERA**
   - Wciel się w rolę tradera
   - Oceń program z jego perspektywy
   - Zidentyfikuj co bym poprawił jako trader i dlaczego
   - Przygotuj listę problemów: krytyczne / ważne / nice-to-have

5. **FAZA 2: PLANOWANIE ITERACJI**
   - Wybierz obszar do pracy (najniższe metryki lub blokujący inne)
   - Przygotuj listę zadań z obliczonym ROI
   - Ustal kolejność wykonania

6. **FAZA 3: ANALIZA PRZED ZMIANĄ**
   - Przeanalizuj wpływ architekturalny
   - Sprawdź zależności i potencjalne efekty uboczne
   - Zweryfikuj historię zmian w tym obszarze
   - Sprawdź dead code i duplikacje

7. **FAZA 4: IMPLEMENTACJA (Test-Driven)**
   - Dla każdego zadania: napisz test (RED) → napisz kod (GREEN) → refaktoruj
   - Uruchom wszystkie testy po każdej zmianie
   - Dokumentuj decyzje w kodzie

8. **FAZA 5: WERYFIKACJA OBSZARU**
   - Zweryfikuj że zmiany działają (z dowodami)
   - Sprawdź wpływ na inne obszary (testy regresji)
   - Zaktualizuj metryki obszaru

9. **FAZA 6: CHECKPOINT + OCENA POSTĘPU**
   - Przygotuj raport iteracji
   - Zaktualizuj historię postępu (trend WGP)
   - Podejmij decyzję: KONTYNUUJ / ESKALUJ / ZAKOŃCZ

10. **DECYZJA O KONTYNUACJI**
    - Jeśli użytkownik przerwał → KONIEC
    - Jeśli nie → **WRÓĆ DO KROKU 1** (nowa iteracja)

**ZASADA: Proces trwa nieprzerwanie do momentu przerwania przez użytkownika.**

---

## CEL BIZNESOWY (Nienaruszalny)

**Dostarczyć traderom narzędzie do wykrywania pump-and-dump, które jest:**

| Wymiar | Definicja sukcesu | Metryka docelowa |
|--------|-------------------|------------------|
| **Użyteczne** | Trader może wykryć pump/dump zanim inni | Accuracy > 80% |
| **Proste** | Trader bez doświadczenia technicznego może używać | Onboarding < 15 min |
| **Elastyczne** | Trader może tworzyć własne strategie bez kodowania | 0 linii kodu wymagane |
| **Niezawodne** | System działa 24/7, błędy są widoczne | Uptime > 99.9% |
| **Szybkie** | Od sygnału do decyzji | Latency < 1 sec |

---

## DEFINICJA OBSZARÓW PROGRAMU

Program jest podzielony na **7 obszarów**. Każdy obszar ma własne metryki i jest oceniany niezależnie.

| ID | Obszar | Opis | Krytyczne dla tradera? |
|----|--------|------|------------------------|
| A1 | **Strategy Builder** | Tworzenie strategii wykrywających pump/dump | TAK - core feature |
| A2 | **Backtesting Engine** | Testowanie strategii na danych historycznych | TAK - walidacja |
| A3 | **Wskaźniki Techniczne** | Obliczanie RSI, MACD, Volume, etc. | TAK - sygnały |
| A4 | **Sygnały i Alerty** | Generowanie i wyświetlanie sygnałów | TAK - decyzje |
| A5 | **UI/Frontend** | Interfejs użytkownika | TAK - użyteczność |
| A6 | **Backend API** | Serwer, endpointy, logika | TAK - fundament |
| A7 | **Baza Danych** | QuestDB, przechowywanie danych | TAK - fundament |

---

## FAZA -1: URUCHOMIENIE ŚRODOWISKA

**Żadna analiza, zmiana ani test nie ma sensu jeśli środowisko nie działa.**

### Krok 1: Uruchom wszystkie usługi

```powershell
# Z katalogu projektu:
.\start_all.ps1
```

Uruchamia: Backend (API), Frontend (UI), QuestDB (baza danych)

Uruchomienie samego backendu po zmianach:
```powershell
python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8080
```

### Krok 2: Aktywuj środowisko Python

```powershell
& C:\Users\lukasz.krysik\Desktop\FXcrypto\FX_code_AI_v2\.venv\Scripts\Activate.ps1
```

### Krok 3: Zweryfikuj że usługi działają

```powershell
# Backend health check
curl http://localhost:8080/health
# Oczekiwany wynik: {"status": "healthy"}

# Frontend check
curl http://localhost:3000
# Oczekiwany wynik: HTML strony

# Testy
python run_tests.py
# Oczekiwany wynik: wszystkie PASS
```

### Krok 4: Jeśli cokolwiek nie działa → NAPRAW TO NAJPIERW

```
ZASADA BLOKUJĄCA: Nie przechodzisz do FAZY 0 dopóki:
[ ] Backend zwraca {"status": "healthy"}
[ ] Frontend zwraca HTML
[ ] Testy przechodzą (lub znasz powód failures i jest udokumentowany)
```

### Raport stanu środowiska

```markdown
## STAN ŚRODOWISKA [data/godzina]

| Usługa | Status | Dowód |
|--------|--------|-------|
| Backend | ✅/❌ | [output curl] |
| Frontend | ✅/❌ | [output curl] |
| QuestDB | ✅/❌ | [output] |
| Testy | ✅/❌ X/Y PASS | [output run_tests.py] |

Środowisko gotowe do pracy: TAK/NIE
```

---

## FAZA 0: ANALIZA GLOBALNA + PODZIAŁ NA OBSZARY

### 0.1 Inwentaryzacja Funkcjonalności

Dla KAŻDEGO z 7 obszarów agent odpowiada:

```markdown
## INWENTARYZACJA OBSZARU: [A1-A7] [Nazwa]

### Komponenty w tym obszarze
| Komponent | Plik(i) | Co robi faktycznie | Działa? (test) |
|-----------|---------|-------------------|----------------|
| ... | src/... | ... | ✅/❌ + dowód |

### Zależności
- Ten obszar zależy od: [lista obszarów]
- Od tego obszaru zależy: [lista obszarów]

### Stan dokumentacji
- README: ✅/❌
- Komentarze w kodzie: ✅/❌
- Testy: X/Y pokrycie
```

### 0.2 Metryki Obszarów (KLUCZOWE)

Agent wypełnia tabelę dla KAŻDEGO obszaru:

```markdown
## METRYKI OBSZARÓW [data/godzina]

| Obszar | UB | ŁU | FB | NZ | JK | WY | OB | ŚR | Trend |
|--------|----|----|----|----|----|----|----|----|-------|
| A1 Strategy Builder | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ↑↓→ |
| A2 Backtesting | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ↑↓→ |
| A3 Wskaźniki | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ↑↓→ |
| A4 Sygnały | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ↑↓→ |
| A5 UI/Frontend | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ↑↓→ |
| A6 Backend API | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ↑↓→ |
| A7 Baza Danych | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ↑↓→ |
| **ŚREDNIA** | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | ?/10 | **?/10** | |
```

**Legenda metryk:**
- **UB** = Użyteczność Biznesowa (czy to pomaga traderowi zarabiać?)
- **ŁU** = Łatwość Użycia (czy trader bez IT może używać?)
- **FB** = Funkcjonalność Biznesowa (czy robi to co powinno?)
- **NZ** = Niezawodność (czy działa stabilnie 24/7?)
- **JK** = Jakość Kodu (czy łatwo utrzymać/rozwijać?)
- **WY** = Wydajność (czy jest szybkie?)
- **OB** = Observability (czy widać co się dzieje, błędy?)
- **ŚR** = Średnia obszaru

**Interpretacja:**
- 1-3: 🔴 Krytyczny problem, blokuje użycie
- 4-5: 🟠 Słabe, wymaga znacznej pracy
- 6-7: 🟡 Akceptowalne, wymaga poprawy
- 8-9: 🟢 Dobre, drobne usprawnienia
- 10: ⭐ Doskonałe

**Trend:** ↑ poprawia się, ↓ pogarsza się, → bez zmian

### 0.3 Wskaźnik Gotowości Produkcyjnej (WGP)

```markdown
## WSKAŹNIK GOTOWOŚCI PRODUKCYJNEJ

WGP = (Suma wszystkich metryk) / (Liczba metryk × 10) × 100%

Aktualny WGP: [X]%

| Poziom | WGP | Znaczenie |
|--------|-----|-----------|
| 🔴 Alpha | 0-40% | Prototyp, nie nadaje się dla traderów |
| 🟠 Beta | 41-60% | Testowy, tylko dla zaawansowanych |
| 🟡 RC | 61-80% | Kandydat do produkcji, drobne problemy |
| 🟢 Production | 81-95% | Gotowy dla traderów |
| ⭐ Mature | 96-100% | Dojrzały produkt |
```

### 0.4 Gap Analysis

```markdown
## GAP ANALYSIS [data]

### Brakujące funkcjonalności (czego nie ma, a powinno być)
| ID | Funkcjonalność | Obszar | Wpływ biznesowy | Złożoność | ROI* | Priorytet |
|----|----------------|--------|-----------------|-----------|------|-----------|
| G1 | ... | A1-A7 | Wysoki/Średni/Niski | W/Ś/N | X | P1/P2/P3 |

### Niekompletne funkcjonalności (co jest, ale nie działa w pełni)
| ID | Funkcjonalność | Obszar | Co brakuje | Wpływ | Priorytet |
|----|----------------|--------|------------|-------|-----------|
| I1 | ... | A1-A7 | ... | ... | P1/P2/P3 |

### Nadmiarowe elementy (co jest, ale nie powinno być)
| ID | Element | Obszar | Dlaczego zbędny | Rekomendacja |
|----|---------|--------|-----------------|--------------|
| R1 | ... | A1-A7 | ... | Usuń/Refaktoruj |

### Problemy architektoniczne
| ID | Problem | Obszary dotknięte | Wpływ | Pilność |
|----|---------|-------------------|-------|---------|
| A1 | ... | ... | ... | ... |

*ROI = (Wartość × Prawdopodobieństwo sukcesu) / (Złożoność × Ryzyko)
```

---

## FAZA 1: PERSPEKTYWA TRADERA (User Persona)

**Agent MUSI wcielić się w rolę tradera i ocenić program z jego perspektywy.**

### 1.1 Symulacja użycia

Agent przeprowadza mentalną symulację:

```markdown
## PERSPEKTYWA TRADERA [data]

### Kim jestem jako trader?
- Doświadczenie: [początkujący / średni / zaawansowany]
- Cel: Wykryć pump-and-dump i zarobić na SHORT
- Czas: Mam 15 minut żeby zacząć używać
- Wiedza IT: Podstawowa (Excel, przeglądarka)

### Scenariusz: Pierwsze użycie
1. Otwieram aplikację → Co widzę? Czy wiem co robić?
2. Chcę stworzyć strategię → Jak to zrobić? Ile kroków?
3. Chcę przetestować strategię → Czy to intuicyjne?
4. Chcę zobaczyć sygnał → Czy jest widoczny? Zrozumiały?
5. Chcę podjąć decyzję → Czy mam wystarczające informacje?

### Ocena z perspektywy tradera

| Pytanie | Ocena (1-10) | Uzasadnienie |
|---------|--------------|--------------|
| Czy mogę zacząć używać w 15 minut? | ?/10 | ... |
| Czy rozumiem co widzę na ekranie? | ?/10 | ... |
| Czy mogę stworzyć strategię bez kodowania? | ?/10 | ... |
| Czy ufam wynikom backtestingu? | ?/10 | ... |
| Czy sygnały są jasne i actionable? | ?/10 | ... |
| Czy wiem co robić gdy coś nie działa? | ?/10 | ... |
| Czy poleciłbym to innemu traderowi? | ?/10 | ... |

**Średnia ocena tradera: [X]/10**
```

### 1.2 Lista problemów z perspektywy tradera

```markdown
## CO BYM POPRAWIŁ JAKO TRADER

### Krytyczne (bez tego nie mogę używać)
| Problem | Dlaczego krytyczny | Proponowane rozwiązanie | Obszar |
|---------|-------------------|-------------------------|--------|
| ... | ... | ... | A1-A7 |

### Ważne (mogę używać, ale frustrujące)
| Problem | Dlaczego ważny | Proponowane rozwiązanie | Obszar |
|---------|---------------|-------------------------|--------|
| ... | ... | ... | A1-A7 |

### Nice-to-have (byłoby fajnie)
| Problem | Dlaczego przydatne | Proponowane rozwiązanie | Obszar |
|---------|-------------------|-------------------------|--------|
| ... | ... | ... | A1-A7 |
```

### 1.3 Analiza Ryzyka vs Zysku

```markdown
## ANALIZA RYZYKA VS ZYSKU

Dla każdego proponowanego ulepszenia:

| Ulepszenie | ZYSK dla tradera | RYZYKO implementacji | CZAS | ROI | Decyzja |
|------------|------------------|---------------------|------|-----|---------|
| ... | Wysoki/Średni/Niski | Wysoki/Średni/Niski | Xh | X | ZRÓB/ODŁÓŻ/ODRZUĆ |

### Uzasadnienie decyzji
- [Ulepszenie X]: ZRÓB bo... / ODŁÓŻ bo... / ODRZUĆ bo...
```

---

## FAZA 2: PLANOWANIE ITERACJI

### 2.1 Wybór obszaru do pracy

**Zasada: Pracuj nad obszarem z najniższą średnią metryk, który blokuje inne.**

```markdown
## WYBÓR OBSZARU DLA TEJ ITERACJI

### Ranking obszarów (od najgorszego)
1. [Obszar X] - średnia: Y/10 - WYBIERAM TEN
2. [Obszar Y] - średnia: Z/10
3. ...

### Uzasadnienie wyboru
- Dlaczego ten obszar? [...]
- Co blokuje? [...]
- Jaki wpływ na tradera? [...]
- Czy zależy od innych obszarów? [...]

### Cel dla tego obszaru w tej iteracji
- Aktualna średnia: X/10
- Cel po iteracji: Y/10 (realny wzrost o max 2 punkty)
```

### 2.2 Lista zadań dla obszaru

```markdown
## ZADANIA DLA OBSZARU [X] - ITERACJA [N]

| ID | Zadanie | Typ | Wpływ na metrykę | ROI | Priorytet | Status |
|----|---------|-----|------------------|-----|-----------|--------|
| T1 | ... | Fix/Feature/Refactor | UB+2, ŁU+1 | Wysoki | P1 | TODO |
| T2 | ... | ... | ... | ... | P2 | TODO |

### Kolejność wykonania
1. T1 (blokuje T2)
2. T2
3. ...

### Kryteria sukcesu iteracji
- [ ] Metryka UB wzrośnie o min 1 punkt
- [ ] Wszystkie testy przechodzą
- [ ] Brak regresji w innych obszarach
```

### 2.3 DEFINITION OF DONE I ACCEPTANCE CRITERIA (OBOWIĄZKOWE)

**ZASADA: Żadne zadanie nie może być rozpoczęte bez zdefiniowanego DoD i AC.**

Dla KAŻDEGO zadania z listy, agent MUSI zdefiniować PRZED rozpoczęciem pracy:

```markdown
## ZADANIE [T1]: [Nazwa zadania]

### A. OPIS ZADANIA
- Co ma być zrobione: [konkretny opis]
- Dlaczego to robimy: [uzasadnienie biznesowe]
- Dla kogo: [trader / system / developer]

### B. DEFINITION OF DONE (DoD)

Zadanie jest UKOŃCZONE gdy WSZYSTKIE poniższe warunki są spełnione:

| # | Warunek DoD | Jak zweryfikować | Spełniony? |
|---|-------------|------------------|------------|
| 1 | Kod jest napisany i zapisany | git status / plik istnieje | ⬜ |
| 2 | Kod przechodzi linting | pylint [plik] | ⬜ |
| 3 | Testy jednostkowe napisane | plik test_*.py istnieje | ⬜ |
| 4 | Wszystkie testy PASS | python run_tests.py | ⬜ |
| 5 | Brak regresji | wszystkie poprzednie testy PASS | ⬜ |
| 6 | Endpoint działa (jeśli API) | curl zwraca oczekiwany wynik | ⬜ |
| 7 | UI renderuje się (jeśli frontend) | brak błędów w konsoli | ⬜ |
| 8 | Brak TODO/FIXME w nowym kodzie | grep -n "TODO\|FIXME" [plik] = 0 | ⬜ |
| 9 | Dokumentacja zaktualizowana | jeśli wymagana | ⬜ |
| 10 | Code review (self) | checklist poniżej | ⬜ |

**Zadanie NIE JEST ukończone dopóki wszystkie ⬜ nie zmienią się w ✅**

### C. ACCEPTANCE CRITERIA (AC)

Konkretne, mierzalne kryteria które MUSZĄ być spełnione:

| AC# | Kryterium | Typ | Jak zmierzyć | Oczekiwany wynik | Spełniony? |
|-----|-----------|-----|--------------|------------------|------------|
| AC1 | [Konkretne kryterium] | Funkcjonalne | [test/curl/manual] | [dokładny wynik] | ⬜ |
| AC2 | [Konkretne kryterium] | Wydajnościowe | [pomiar] | [wartość] | ⬜ |
| AC3 | [Konkretne kryterium] | Biznesowe | [scenariusz] | [rezultat] | ⬜ |

**Przykłady dobrych AC:**

| ❌ ŹLE (nieokreślone) | ✅ DOBRZE (mierzalne) |
|-----------------------|----------------------|
| "Endpoint działa" | "GET /api/signals zwraca JSON z polami: id, symbol, signal_type, timestamp. Status 200." |
| "Jest szybkie" | "Response time < 100ms dla 1000 rekordów (mierzone curl -w '%{time_total}')" |
| "Obsługuje błędy" | "Dla nieprawidłowego symbol zwraca 400 z JSON: {error: 'Invalid symbol', code: 'INVALID_SYMBOL'}" |
| "Trader może używać" | "Trader może stworzyć strategię w max 5 krokach bez dokumentacji" |
| "Wyświetla dane" | "Tabela pokazuje: symbol, cena, zmiana %, volume. Sortowalna po każdej kolumnie." |

**ZASADA: Każde AC musi być:**
- **S**pecific - konkretne, nie ogólne
- **M**easurable - mierzalne, z wartością oczekiwaną
- **A**chievable - osiągalne w ramach zadania
- **R**elevant - istotne dla celu biznesowego
- **T**estable - można napisać test który to sprawdzi

### D. MAPOWANIE AC → TESTY

Każde Acceptance Criterion MUSI mieć odpowiadający test:

| AC# | Test | Plik testu | Status testu |
|-----|------|------------|--------------|
| AC1 | test_signals_endpoint_returns_valid_json | tests/test_api.py:45 | ⬜ RED → ⬜ GREEN |
| AC2 | test_signals_response_time_under_100ms | tests/test_performance.py:12 | ⬜ RED → ⬜ GREEN |
| AC3 | test_invalid_symbol_returns_400 | tests/test_api.py:78 | ⬜ RED → ⬜ GREEN |

**ZASADA: Jeśli AC nie ma testu → AC nie może być zweryfikowane → Zadanie nie może być ukończone**

### E. DEFINICJA NIEPOWODZENIA

Zadanie jest NIEUKOŃCZONE gdy:
- Którykolwiek warunek DoD nie jest spełniony
- Którekolwiek AC nie jest spełnione
- Którykolwiek test jest RED
- Istnieją czerwone flagi (TODO, FIXME, NotImplementedError)

### F. PLAN IMPLEMENTACJI

Na podstawie AC, kolejność kroków:
1. Napisz test dla AC1 (RED)
2. Zaimplementuj funkcjonalność dla AC1
3. Uruchom test AC1 (GREEN)
4. Napisz test dla AC2 (RED)
5. ...
6. Zweryfikuj wszystkie DoD
7. Zweryfikuj wszystkie AC
8. Dopiero wtedy → DONE
```

### 2.4 WERYFIKACJA AC PRZED ROZPOCZĘCIEM IMPLEMENTACJI

Agent MUSI sprawdzić czy AC są poprawnie zdefiniowane:

```markdown
## CHECKLIST JAKOŚCI AC

| # | Pytanie | Odpowiedź |
|---|---------|-----------|
| 1 | Czy każde AC jest konkretne i jednoznaczne? | TAK/NIE |
| 2 | Czy każde AC ma mierzalny oczekiwany wynik? | TAK/NIE |
| 3 | Czy każde AC ma zdefiniowany sposób weryfikacji? | TAK/NIE |
| 4 | Czy każde AC ma odpowiadający test? | TAK/NIE |
| 5 | Czy AC pokrywają wszystkie aspekty zadania? | TAK/NIE |
| 6 | Czy AC są realistyczne do osiągnięcia? | TAK/NIE |
| 7 | Czy AC są zrozumiałe dla tradera (jeśli dotyczy)? | TAK/NIE |

**Jeśli którakolwiek odpowiedź = NIE → Popraw AC przed rozpoczęciem implementacji**
```

### 2.5 Matryca decyzyjna ROI

```
ROI = (Wartość × Prawdopodobieństwo sukcesu) / (Złożoność × Ryzyko)

Gdzie:
- Wartość: 1-10 (wpływ na tradera)
- Prawdopodobieństwo sukcesu: 0.1-1.0
- Złożoność: 1-10 (ile pracy)
- Ryzyko: 1-10 (szansa na regresję)

ROI > 2.0 → ZRÓB TERAZ
ROI 1.0-2.0 → ZAPLANUJ
ROI 0.5-1.0 → MOŻE PÓŹNIEJ
ROI < 0.5 → ODRZUĆ
```

---

## FAZA 3: ANALIZA PRZED ZMIANĄ

### 3.1 Analiza wpływu architekturalnego

```markdown
## ANALIZA ZMIANY: [nazwa zadania]

### Dotknięte komponenty
| Komponent | Plik:linia | Typ zmiany | Ryzyko |
|-----------|------------|------------|--------|
| ... | src/x.py:42 | Mod/Add/Del | W/Ś/N |

### Zależności
- Ten komponent zależy od → [lista]
- Od tego komponentu zależy → [lista]

### Wpływ na inne obszary
| Obszar | Wpływ | Jak zweryfikować |
|--------|-------|------------------|
| A1 | Brak/Pośredni/Bezpośredni | ... |
| A2 | ... | ... |

### Sprawdzenie race conditions
- [ ] Czy zmiana dotyczy współdzielonych zasobów? [tak/nie]
- [ ] Czy są operacje asynchroniczne? [tak/nie]
- [ ] Czy jest odpowiednia synchronizacja? [tak/nie]

### Historia zmian w tym obszarze
```powershell
git log --oneline -10 [plik]
```
- Ostatnia zmiana: [data, cel]
- Czy poprzednie zmiany sugerują że moja propozycja może być błędna? [tak/nie + uzasadnienie]
```

### 3.2 Kontrola jakości kodu

```markdown
## KONTROLA JAKOŚCI PRZED ZMIANĄ

### Dead code w obszarze zmiany
- [ ] Nieużywane funkcje: [lista lub "brak"]
- [ ] Nieużywane importy: [lista lub "brak"]
- [ ] Zakomentowany kod: [lista lub "brak"]

### Duplikacja kodu
- [ ] Czy podobna logika istnieje gdzie indziej? [tak/nie, gdzie]
- [ ] Czy tworzę drugą wersję czegoś istniejącego? [tak/nie]

### Backward compatibility
- [ ] Czy zmiana wymaga migracji? [tak/nie]
- [ ] Czy tworzę "stare" i "nowe" API? [tak/nie - jeśli tak, STOP]

### Spójność z architekturą
- [ ] Czy zmiana pasuje do istniejących wzorców? [tak/nie]
- [ ] Czy nie wprowadzam niespójności? [tak/nie]
```

---

## FAZA 4: IMPLEMENTACJA (Test-Driven, AC-Driven)

**ZASADA: Implementacja jest sterowana przez Acceptance Criteria. Każde AC → Test → Kod.**

### 4.1 Cykl AC-Driven Development

```
DLA KAŻDEGO ACCEPTANCE CRITERION (AC):

1. WEŹMIE AC z listy
   - Przeczytaj AC: co dokładnie ma być spełnione?
   - Jaki jest oczekiwany wynik?

2. NAPISZ TEST dla tego AC (RED)
   - Test MUSI sprawdzać dokładnie to co AC wymaga
   - Test MUSI FAILOWAĆ (RED) - bo funkcjonalność jeszcze nie istnieje
   - Pokaż output testu jako dowód RED
   
3. NAPISZ MINIMALNY KOD który sprawia że test przechodzi
   - Tylko tyle kodu ile potrzeba dla tego AC
   - Test MUSI PRZECHODZIĆ (GREEN)
   - Pokaż output testu jako dowód GREEN

4. OZNACZ AC JAKO SPEŁNIONE
   - Zmień ⬜ na ✅ w tabeli AC
   - Zapisz dowód (output testu)

5. SPRAWDŹ REGRESJĘ
   - Uruchom WSZYSTKIE testy
   - Wszystkie muszą być GREEN
   - Pokaż output jako dowód

6. PRZEJDŹ DO NASTĘPNEGO AC
   - Powtarzaj aż wszystkie AC są ✅

7. ZWERYFIKUJ DoD
   - Sprawdź każdy warunek Definition of Done
   - Wszystkie muszą być ✅
```

### 4.2 Format dokumentowania implementacji AC

```markdown
## IMPLEMENTACJA ZADANIA [T1]

### AC1: [Treść kryterium]

**Oczekiwany wynik:** [dokładnie co ma być]

**Test:**
```python
def test_ac1_signals_endpoint_returns_valid_json():
    response = client.get("/api/signals")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data[0]
    assert "symbol" in data[0]
    assert "signal_type" in data[0]
```

**Status RED (przed implementacją):**
```
FAILED test_api.py::test_ac1_signals_endpoint_returns_valid_json
AssertionError: assert 404 == 200
```

**Implementacja:** src/api/routes.py:45-67
```python
@router.get("/api/signals")
def get_signals():
    signals = signal_service.get_all()
    return [{"id": s.id, "symbol": s.symbol, "signal_type": s.type} for s in signals]
```

**Status GREEN (po implementacji):**
```
PASSED test_api.py::test_ac1_signals_endpoint_returns_valid_json
```

**AC1 Status:** ⬜ → ✅

---

### AC2: [Treść kryterium]
[...powtórz format...]

---

### PODSUMOWANIE AC

| AC# | Kryterium | Test | RED→GREEN | Status |
|-----|-----------|------|-----------|--------|
| AC1 | Endpoint zwraca JSON | test_ac1_* | ✅ | ✅ DONE |
| AC2 | Response < 100ms | test_ac2_* | ✅ | ✅ DONE |
| AC3 | Error handling | test_ac3_* | ⬜ | ⬜ TODO |

**Wszystkie AC spełnione:** NIE (2/3)
**Można przejść do weryfikacji DoD:** NIE
```

### 4.3 Weryfikacja DoD po wszystkich AC

```markdown
## WERYFIKACJA DEFINITION OF DONE

Dopiero gdy WSZYSTKIE AC są ✅, sprawdź DoD:

| # | Warunek DoD | Jak zweryfikować | Dowód | Status |
|---|-------------|------------------|-------|--------|
| 1 | Kod jest napisany | git status | [output] | ✅ |
| 2 | Kod przechodzi linting | pylint src/api/routes.py | [output] | ✅ |
| 3 | Testy napisane | ls tests/test_*.py | [output] | ✅ |
| 4 | Wszystkie testy PASS | python run_tests.py | [output 15/15 PASS] | ✅ |
| 5 | Brak regresji | porównanie przed/po | [output] | ✅ |
| 6 | Endpoint działa | curl localhost:8080/api/signals | [output JSON] | ✅ |
| 7 | Brak TODO/FIXME | grep -n "TODO\|FIXME" src/api/routes.py | [0 results] | ✅ |
| 8 | Dokumentacja | README zaktualizowany | [diff] | ✅ |

**Wszystkie DoD spełnione:** TAK (8/8)
```

### 4.4 Warunek zakończenia zadania

```markdown
## ZADANIE [T1] - STATUS KOŃCOWY

### Checklist zakończenia

| Kategoria | Wymaganie | Status |
|-----------|-----------|--------|
| AC | Wszystkie Acceptance Criteria spełnione | ✅ 3/3 |
| DoD | Wszystkie warunki Definition of Done spełnione | ✅ 8/8 |
| Testy | Wszystkie testy GREEN | ✅ 15/15 PASS |
| Regresja | Brak regresji w innych testach | ✅ 0 failures |
| Czerwone flagi | Brak TODO/FIXME/NotImplementedError | ✅ 0 found |

### DECYZJA

[ ] ✅ ZADANIE UKOŃCZONE - wszystkie warunki spełnione
[ ] ⚠️ ZADANIE CZĘŚCIOWE - X/Y AC spełnione, przyczyna: [...]
[ ] ❌ ZADANIE NIEUKOŃCZONE - blokery: [...]

**Można oznaczyć jako UKOŃCZONE TYLKO gdy:**
- 100% AC = ✅
- 100% DoD = ✅
- 0 testów FAIL
- 0 czerwonych flag
```

### 4.5 Komentarze decyzyjne w kodzie

```markdown
## CHECKLIST IMPLEMENTACJI [Zadanie X]

### Jakość kodu
- [ ] Brak dead code (usunięty jeśli był)
- [ ] Brak duplikacji (wykorzystane istniejące rozwiązania)
- [ ] Komentarze przy nieoczywistych decyzjach
- [ ] Oznaczenie miejsc wymagających akceptacji biznesowej

### Testy
- [ ] Nowe testy dla nowej funkcjonalności
- [ ] Zaktualizowane testy dla zmienionej funkcjonalności
- [ ] Usunięte testy dla usuniętej funkcjonalności

### Dokumentacja zmian w testach
| Plik testu | Zmiana | Uzasadnienie |
|------------|--------|--------------|
| test_x.py | Dodano test Y | Pokrywa nową funkcję Z |
```

### 4.3 Komentarze decyzyjne w kodzie

```python
# DECISION [2024-01-15]: Użyto algorytmu X zamiast Y
# REASON: X jest 3x szybszy dla dużych zbiorów danych
# OWNER_APPROVAL_REQUIRED: Tak - zmiana wpływa na dokładność sygnałów
# CONTEXT: Iteracja 5, zadanie T3
```

---

## FAZA 5: WERYFIKACJA OBSZARU (AC/DoD-Based)

**ZASADA: Weryfikacja to porównanie stanu aktualnego z zdefiniowanymi AC i DoD.**

### 5.1 Weryfikacja każdego zadania

Dla KAŻDEGO zadania z iteracji:

```markdown
## WERYFIKACJA ZADANIA [T1]: [Nazwa]

### A. STATUS ACCEPTANCE CRITERIA

| AC# | Kryterium | Oczekiwany wynik | Faktyczny wynik | Test PASS? | Status |
|-----|-----------|------------------|-----------------|------------|--------|
| AC1 | Endpoint zwraca JSON z polami id, symbol, signal_type | Status 200, JSON z polami | [wklej output curl] | ✅ | ✅ |
| AC2 | Response time < 100ms | < 100ms | 45ms [wklej pomiar] | ✅ | ✅ |
| AC3 | Invalid symbol → 400 | Status 400, error JSON | [wklej output] | ✅ | ✅ |

**AC spełnione:** 3/3 (100%)

### B. STATUS DEFINITION OF DONE

| # | Warunek DoD | Dowód | Status |
|---|-------------|-------|--------|
| 1 | Kod napisany | src/api/routes.py:45-67 | ✅ |
| 2 | Linting PASS | pylint: 10/10 | ✅ |
| 3 | Testy napisane | tests/test_api.py:45-120 | ✅ |
| 4 | Testy PASS | 15/15 PASS [output] | ✅ |
| 5 | Brak regresji | 47/47 PASS [output] | ✅ |
| 6 | Endpoint działa | curl [output] | ✅ |
| 7 | Brak TODO/FIXME | grep: 0 results | ✅ |
| 8 | Dokumentacja | README.md updated | ✅ |

**DoD spełnione:** 8/8 (100%)

### C. DECYZJA O STATUSIE ZADANIA

Na podstawie AC i DoD:

| Warunek | Wymagane | Aktualne | Spełnione? |
|---------|----------|----------|------------|
| AC completion | 100% | 100% (3/3) | ✅ |
| DoD completion | 100% | 100% (8/8) | ✅ |
| Testy PASS | 100% | 100% (15/15) | ✅ |
| Czerwone flagi | 0 | 0 | ✅ |

**STATUS ZADANIA:** ✅ UKOŃCZONE

*Można zaznaczyć UKOŃCZONE bo wszystkie warunki = 100%*
```

### 5.2 Agregacja statusów zadań

```markdown
## PODSUMOWANIE ZADAŃ ITERACJI [N]

| ID | Zadanie | AC% | DoD% | Testy | Status |
|----|---------|-----|------|-------|--------|
| T1 | Naprawić endpoint /api/signals | 100% (3/3) | 100% (8/8) | 15/15 PASS | ✅ DONE |
| T2 | Dodać walidację | 60% (3/5) | 75% (6/8) | 8/12 PASS | ⚠️ PARTIAL |
| T3 | Refaktor obliczeń | 0% (0/4) | 0% (0/8) | 0/5 PASS | ❌ NOT STARTED |

### Statystyki iteracji
- Zadania ukończone (100% AC + 100% DoD): 1/3
- Zadania częściowe: 1/3
- Zadania nierozpoczęte: 1/3
- **Completion rate:** 33%

### Niespełnione AC (do następnej iteracji)
| Zadanie | AC# | Kryterium | Przyczyna niespełnienia |
|---------|-----|-----------|-------------------------|
| T2 | AC4 | Walidacja email | Brak czasu |
| T2 | AC5 | Walidacja phone | Zależność od AC4 |
| T3 | AC1-4 | Wszystkie | Nie rozpoczęto |

### Niespełnione DoD (do następnej iteracji)
| Zadanie | DoD# | Warunek | Przyczyna |
|---------|------|---------|-----------|
| T2 | DoD7 | Brak TODO | Jest 1 TODO w kodzie |
| T2 | DoD8 | Dokumentacja | Nie zaktualizowana |
```

### 5.3 Weryfikacja wpływu na inne obszary

```markdown
## WERYFIKACJA CAŁOŚCI PO ZMIANIE

### Testy regresji
| Obszar | Testy przed | Testy po | Regresja? |
|--------|-------------|----------|-----------|
| A1 | X PASS | X PASS | NIE |
| A2 | Y PASS | Y PASS | NIE |
| ... | ... | ... | ... |

### Health check całego systemu
- [ ] Backend: curl localhost:8080/health → {"status": "healthy"}
- [ ] Frontend: curl localhost:3000 → HTML
- [ ] Wszystkie testy: python run_tests.py → ALL PASS
```

### 5.3 Aktualizacja metryk obszaru

```markdown
## AKTUALIZACJA METRYK PO ITERACJI

### Obszar [X] - przed vs po

| Metryka | Przed | Po | Zmiana |
|---------|-------|----| -------|
| UB | X/10 | Y/10 | +/-Z |
| ŁU | X/10 | Y/10 | +/-Z |
| FB | X/10 | Y/10 | +/-Z |
| NZ | X/10 | Y/10 | +/-Z |
| JK | X/10 | Y/10 | +/-Z |
| WY | X/10 | Y/10 | +/-Z |
| OB | X/10 | Y/10 | +/-Z |
| **ŚR** | X/10 | Y/10 | +/-Z |

### Uzasadnienie zmian metryk
- UB wzrosło bo: [...]
- ŁU bez zmian bo: [...]
```

---

## FAZA 6: CHECKPOINT + OCENA POSTĘPU

### 6.1 Raport iteracji

```markdown
## CHECKPOINT ITERACJI [N] - [data/godzina]

### Podsumowanie
- Obszar: [X]
- Zadania zaplanowane: [N]
- Zadania ukończone: [M]
- Zadania nieukończone: [N-M] + przyczyna

### Metryki przed/po

| Obszar | Średnia przed | Średnia po | Trend |
|--------|---------------|------------|-------|
| A1 | X/10 | Y/10 | ↑↓→ |
| ... | ... | ... | ... |
| **WGP** | X% | Y% | +/-Z% |

### Decyzje podjęte
| Decyzja | Uzasadnienie biznesowe | Uzasadnienie techniczne |
|---------|------------------------|-------------------------|
| ... | ... | ... |

### Problemy zidentyfikowane
| Problem | Wpływ | Priorytet | Status |
|---------|-------|-----------|--------|
| ... | ... | P1/P2/P3 | TODO/IN_PROGRESS |
```

### 6.2 Historia postępu (trend)

```markdown
## HISTORIA POSTĘPU

| Iteracja | Data | Obszar | WGP przed | WGP po | Zmiana |
|----------|------|--------|-----------|--------|--------|
| 1 | ... | A5 | 35% | 38% | +3% |
| 2 | ... | A1 | 38% | 42% | +4% |
| ... | ... | ... | ... | ... | ... |

### Alert regresji
⚠️ Jeśli WGP spada między iteracjami → STOP i zbadaj przyczynę
```

### 6.3 Decyzja o następnym kroku

```markdown
## DECYZJA: CO DALEJ?

### Opcje
1. KONTYNUUJ → Wróć do FAZY 0 z następną iteracją
2. ESKALUJ → Wymagana decyzja właściciela (zmiana architekturalna, usunięcie funkcji)
3. ZAKOŃCZ → Produkt osiągnął satysfakcjonujący poziom (WGP > 80%)

### Moja decyzja: [KONTYNUUJ / ESKALUJ / ZAKOŃCZ]
### Uzasadnienie: [...]

### Jeśli KONTYNUUJ - następny obszar
- Obszar: [X]
- Uzasadnienie: [najniższa średnia / blokuje inne / feedback tradera]
```

---

## WERYFIKACJA ANTY-FAŁSZYWY-SUKCES

**Problem:** Agent ma tendencję do ogłaszania sukcesu gdy zadanie nie jest ukończone.

**Rozwiązanie:** Sukces jest zdefiniowany PRZED pracą (AC + DoD), nie po. Agent może ogłosić sukces TYLKO gdy 100% AC i 100% DoD jest spełnionych.

### 0. ZŁOTA ZASADA

```
SUKCES = (100% AC spełnione) AND (100% DoD spełnione) AND (0 czerwonych flag)

Jeśli którykolwiek warunek nie jest spełniony → NIE MA SUKCESU.
Nie ma "prawie sukcesu", "częściowego sukcesu" przy ogłaszaniu zadania jako ukończone.
Zadanie jest DONE albo NOT DONE. Nic pomiędzy.
```

### 1. ZAKAZANE FRAZY BEZ DOWODU

Te słowa/frazy NIE MOGĄ pojawić się w raporcie bez załączonego dowodu (output, screenshot, log):

| Zakazana fraza | Wymagany dowód |
|----------------|----------------|
| "zaimplementowałem" | Output testu PASS + kod z numerami linii |
| "naprawiłem" | Test PRZED (FAIL) + test PO (PASS) |
| "działa" | curl/test output pokazujący działanie |
| "ukończone" | Checklist wszystkich podpunktów ✅ |
| "sukces" | Wszystkie testy PASS + brak błędów w logach |
| "gotowe" | Demo działania (output lub screenshot) |
| "przetestowałem" | Pełny output testów |
| "zweryfikowałem" | Konkretny dowód weryfikacji |
| "nie ma błędów" | Logi pokazujące brak błędów |
| "wszystko OK" | ZAKAZANE - zbyt ogólne, zawsze podaj szczegóły |

**ZASADA: Jeśli nie masz dowodu - NIE PISZ TEJ FRAZY.**

### 2. OBOWIĄZKOWA SEKCJA "CO NIE DZIAŁA"

Każdy raport MUSI zawierać sekcję "Co NIE działa / Znane problemy".

**Ta sekcja NIE MOŻE być pusta ani zawierać:**
- "Brak"
- "Nic"
- "Wszystko działa"
- "Nie zidentyfikowano"

**Jeśli agent pisze że nie ma problemów → CZERWONA FLAGA → Wymagana dodatkowa weryfikacja.**

Poprawny format:
```markdown
## Co NIE działa / Znane problemy

| Problem | Lokalizacja (plik:linia) | Severity | Status |
|---------|--------------------------|----------|--------|
| Brak walidacji inputu | src/api/routes.py:42 | Medium | TODO |
| Test X jest flaky | tests/test_signals.py:88 | Low | Known issue |
| Endpoint Y zwraca 500 dla edge case Z | src/handlers.py:156 | High | Investigating |

Jeśli naprawdę nie znaleziono problemów (mało prawdopodobne):
- Opisz DOKŁADNIE co zostało sprawdzone
- Załącz outputy wszystkich weryfikacji
- Przyznaj że mogą istnieć nieznane problemy
```

### 3. WERYFIKACJA ANTY-MOCKOWA

Przed ogłoszeniem sukcesu, agent MUSI przeszukać kod pod kątem:

```powershell
# Szukaj placeholder code
grep -rn "TODO" src/
grep -rn "FIXME" src/
grep -rn "XXX" src/
grep -rn "HACK" src/
grep -rn "NotImplementedError" src/
grep -rn "pass$" src/*.py
grep -rn "raise NotImplementedError" src/
grep -rn "# mock" src/
grep -rn "mock_" src/
grep -rn "hardcoded" src/
grep -rn "placeholder" src/
grep -rn "dummy" src/
grep -rn "fake_" src/
grep -rn "return None  # TODO" src/
grep -rn "return \[\]  # TODO" src/
grep -rn "return {}  # TODO" src/
```

**Format raportu:**
```markdown
## Weryfikacja anty-mockowa

| Wzorzec | Znalezione | Lokalizacje | Akceptowalne? |
|---------|------------|-------------|---------------|
| TODO | 3 | src/x.py:12, src/y.py:45, src/z.py:89 | NIE - musi być usunięte |
| FIXME | 0 | - | OK |
| NotImplementedError | 1 | src/signals.py:234 | NIE - blokuje sukces |
| pass (puste funkcje) | 2 | src/handlers.py:56, src/utils.py:23 | Sprawdzić kontekst |
| mock_ | 5 | tests/... | OK jeśli tylko w testach |

Wynik: BLOKADA / OK
```

**Jeśli znaleziono TODO/FIXME/NotImplementedError w kodzie produkcyjnym → NIE MOŻNA ogłosić sukcesu.**

### 4. SELF-REVIEW PRZED OGŁOSZENIEM SUKCESU

Agent MUSI odpowiedzieć na poniższe pytania ZANIM ogłosi sukces:

```markdown
## SELF-REVIEW CHECKLIST

### Pytania weryfikacyjne (odpowiedz szczerze)

| # | Pytanie | Odpowiedź | Dowód |
|---|---------|-----------|-------|
| 1 | Czy uruchomiłem WSZYSTKIE testy? | TAK/NIE | [output] |
| 2 | Czy WSZYSTKIE testy przeszły? | TAK/NIE | [output pokazujący X/X PASS] |
| 3 | Czy sprawdziłem logi pod kątem błędów? | TAK/NIE | [fragment logów] |
| 4 | Czy endpoint działa (curl)? | TAK/NIE | [output curl] |
| 5 | Czy frontend renderuje się bez błędów? | TAK/NIE | [output/screenshot] |
| 6 | Czy przeszukałem kod pod kątem TODO/FIXME? | TAK/NIE | [wynik grep] |
| 7 | Czy sprawdziłem czy nie ma mocków w produkcji? | TAK/NIE | [wynik grep] |
| 8 | Czy każde zadanie z planu ma status? | TAK/NIE | [tabela statusów] |
| 9 | Czy mogę zademonstrować działanie? | TAK/NIE | [demo output] |
| 10 | Czy jako trader mógłbym tego użyć? | TAK/NIE | [uzasadnienie] |

### Wynik self-review
- Odpowiedzi TAK: X/10
- Odpowiedzi NIE: Y/10

**Jeśli którakolwiek odpowiedź to NIE → NIE MOŻNA ogłosić sukcesu**
**Jeśli brak dowodu przy TAK → odpowiedź się nie liczy**
```

### 5. PORÓWNANIE PLAN VS WYKONANIE (AC-Based)

Przed zamknięciem iteracji, agent MUSI porównać:

```markdown
## PLAN VS WYKONANIE

### Status zadań

| ID | Zadanie | AC zdefiniowane | AC spełnione | DoD spełnione | Status |
|----|---------|-----------------|--------------|---------------|--------|
| T1 | Naprawić endpoint | 3 | 3/3 (100%) | 8/8 (100%) | ✅ DONE |
| T2 | Dodać walidację | 5 | 3/5 (60%) | 6/8 (75%) | ⚠️ PARTIAL |
| T3 | Refaktor obliczeń | 4 | 0/4 (0%) | 0/8 (0%) | ❌ NOT DONE |

### Szczegóły niespełnionych AC

| Zadanie | AC# | Kryterium | Oczekiwane | Faktyczne | Przyczyna |
|---------|-----|-----------|------------|-----------|-----------|
| T2 | AC4 | Walidacja email | Regex email | Brak implementacji | Brak czasu |
| T2 | AC5 | Walidacja phone | Format +XX | Zależność od AC4 | Bloker |
| T3 | AC1 | Obliczenia X | Wynik Y | - | Nie rozpoczęto |

### Podsumowanie

| Metryka | Wartość |
|---------|---------|
| Zadania z 100% AC | 1/3 (33%) |
| Łączne AC zdefiniowane | 12 |
| Łączne AC spełnione | 6/12 (50%) |
| Łączne DoD spełnione | 14/24 (58%) |

### Completion rate: 33% (1/3 zadań w pełni ukończonych)

**Jeśli completion rate < 100%:**
- NIE MOŻNA pisać "wszystkie zadania ukończone"
- MOŻNA napisać: "Iteracja zakończona. Ukończono 1/3 zadań (33%). 
  Niespełnione AC: 6. Przechodzą do następnej iteracji."
```

### 6. CZERWONE FLAGI BLOKUJĄCE SUKCES

Poniższe warunki AUTOMATYCZNIE blokują ogłoszenie sukcesu:

```markdown
## CZERWONE FLAGI - SPRAWDŹ PRZED OGŁOSZENIEM

| # | Czerwona flaga | Jak sprawdzić | Czy występuje? |
|---|----------------|---------------|----------------|
| 1 | Jakikolwiek test FAIL | python run_tests.py | TAK/NIE |
| 2 | Backend nie zwraca healthy | curl localhost:8080/health | TAK/NIE |
| 3 | Frontend nie renderuje | curl localhost:3000 | TAK/NIE |
| 4 | Exception w logach | grep -i "error\|exception" logs/ | TAK/NIE |
| 5 | TODO/FIXME w zmienionym kodzie | grep -n "TODO\|FIXME" [zmienione pliki] | TAK/NIE |
| 6 | NotImplementedError | grep -rn "NotImplementedError" src/ | TAK/NIE |
| 7 | Puste funkcje (tylko pass) | grep -n "pass$" [zmienione pliki] | TAK/NIE |
| 8 | Hardcoded test values w produkcji | manual review | TAK/NIE |
| 9 | Import nieużywanego modułu | pylint --disable=all --enable=unused-import | TAK/NIE |
| 10 | Zakomentowany kod produkcyjny | manual review | TAK/NIE |

### Wynik
- Czerwone flagi: X/10

**Jeśli JAKAKOLWIEK czerwona flaga = TAK → STOP. Napraw przed kontynuacją.**
```

### 7. WYMUSZONY FORMAT RAPORTU KOŃCOWEGO

Każdy raport iteracji MUSI mieć tę strukturę (nie można pominąć sekcji):

```markdown
## RAPORT ITERACJI [N] - [data]

### A. STATUS ŚRODOWISKA
- Backend health: [output curl]
- Frontend: [output curl]  
- Testy: [X/Y PASS - pełny output]

### B. CO ZOSTAŁO ZROBIONE
[Lista z numerami linii kodu]

### C. DOWODY DZIAŁANIA
| Funkcjonalność | Komenda weryfikacji | Output |
|----------------|---------------------|--------|
| ... | curl/test/... | [wklej] |

### D. CO NIE DZIAŁA / ZNANE PROBLEMY
[OBOWIĄZKOWA - nie może być pusta]

| Problem | Plik:linia | Severity | Plan naprawy |
|---------|------------|----------|--------------|
| ... | ... | ... | ... |

### E. WERYFIKACJA ANTY-MOCKOWA
[Wynik grep dla TODO/FIXME/mock/etc]

### F. PLAN VS WYKONANIE
[Tabela porównawcza]
- Completion rate: X%

### G. SELF-REVIEW CHECKLIST
[10 pytań z odpowiedziami i dowodami]

### H. CZERWONE FLAGI
[Lista 10 flag z wynikami]
- Flagi aktywne: X/10

### I. PODSUMOWANIE (szczere)
- Co się udało: [...]
- Co się nie udało: [...]
- Co zostało do zrobienia: [...]
- Blokery: [...]

### J. DECYZJA
[ ] SUKCES - wszystkie warunki spełnione (rzadkie)
[ ] CZĘŚCIOWY SUKCES - X% ukończone, Y% do następnej iteracji
[ ] NIEPOWODZENIE - blokery uniemożliwiły postęp
[X] WYMAGA KONTYNUACJI - standardowy stan, praca trwa

**Uwaga: "SUKCES" można zaznaczyć TYLKO gdy:**
- Completion rate = 100%
- Czerwone flagi = 0/10
- Self-review = 10/10 TAK z dowodami
- Sekcja D zawiera tylko niskie priorytety
```

### 8. ZASADA DOMYŚLNEGO PESYMIZMU

```
ZASADA: Domyślnie zakładaj że coś nie działa, dopóki nie udowodnisz że działa.

NIE: "Zaimplementowałem funkcję X" 
TAK: "Napisałem kod funkcji X (src/module.py:45-67). Test test_X przechodzi [output]. 
      Endpoint zwraca oczekiwany wynik [curl output]. 
      Pozostałe do weryfikacji: edge case Y, integracja z Z."

NIE: "Wszystko działa"
TAK: "Zweryfikowałem działanie A [dowód], B [dowód], C [dowód]. 
      Nie zweryfikowałem jeszcze: D, E. 
      Znane problemy: F nie obsługuje przypadku G."

NIE: "Naprawiłem bug"
TAK: "Bug X (plik:linia) - zmieniono [opis zmiany]. 
      Test przed: FAIL [output]. 
      Test po: PASS [output]. 
      Sprawdzono regresję: testy A, B, C nadal PASS [output]."
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
- ❌ Nie twórz backward compatibility layers
- ❌ Nie kończ bez powrotu do FAZY 0

### ZAWSZE:
- ✅ Najpierw test, potem implementacja
- ✅ Uzasadniaj każdą decyzję biznesowo I technicznie
- ✅ Sprawdzaj historię zmian przed modyfikacją
- ✅ Weryfikuj wpływ na inne komponenty/obszary
- ✅ Aktualizuj testy przy każdej zmianie kodu
- ✅ Dokumentuj decyzje w komentarzach
- ✅ Podawaj numery linii przy problemach
- ✅ Usuwaj niepotrzebny kod
- ✅ Wracaj do FAZY 0 po każdej iteracji
- ✅ Aktualizuj metryki po każdej zmianie

---

## KIEDY ESKALOWAĆ DO WŁAŚCICIELA

Agent MUSI przerwać i zapytać właściciela gdy:

1. **Zmiana architekturalna** wpływająca na >3 obszary
2. **Usunięcie funkcjonalności** - nawet jeśli nieużywana
3. **Zmiana logiki biznesowej** (np. algorytm wykrywania pump/dump)
4. **Zmiana wpływająca na wydajność** >20%
5. **Sprzeczne wymagania** - nie można spełnić A bez złamania B
6. **WGP spada** przez 2 kolejne iteracje
7. **Kod oznaczony** `OWNER_APPROVAL_REQUIRED`

---

## NARZĘDZIA

### Uruchomienie środowiska (Windows/PowerShell)

```powershell
# Uruchom wszystkie usługi
.\start_all.ps1

# Aktywuj środowisko Python
& C:\Users\lukasz.krysik\Desktop\FXcrypto\FX_code_AI_v2\.venv\Scripts\Activate.ps1

# Uruchom testy
python run_tests.py

# Uruchom backend po zmianach
python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8080
```

### Weryfikacja

```powershell
# Backend health
curl http://localhost:8080/health

# Frontend check
curl http://localhost:3000

# Status usług
python scripts/dev_tools.py status

# Generuj dane testowe
python scripts/dev_tools.py gen-data
```

### Analiza kodu

```powershell
# Historia zmian
git log --oneline -10 path/to/file.py

# Dead code
vulture src/

# Duplikaty
pylint --disable=all --enable=duplicate-code src/
```

---

## METRYKI SUKCESU PROJEKTU

### Dla tradera (cel końcowy)
- Czas od uruchomienia do pierwszego sygnału: < 5 minut
- Czas od sygnału do decyzji: < 1 sekunda
- Accuracy wykrywania: > 80%
- Uptime: > 99.9%

### Dla kodu (jakość)
- Pokrycie testami: > 80%
- Średnia metryk: > 7/10
- WGP: > 80%
- Zero dead code

### Dla procesu (efektywność)
- Regresje po zmianach: 0
- Średni wzrost WGP na iterację: > 2%
- Czas iteracji: < 4h

---

## AKTUALIZACJA TEGO DOKUMENTU

Workflow może być aktualizowany gdy:
1. Praktyka pokazuje nieefektywność kroku
2. Pojawiają się nowe narzędzia
3. Cele biznesowe się zmieniają

Każda aktualizacja wymaga:
- Uzasadnienia biznesowego
- Uzasadnienia technicznego
- Wpisu w historii zmian

### Historia zmian
| Wersja | Data | Zmiana | Uzasadnienie |
|--------|------|--------|--------------|
| 3.0 | [data] | Dodano ciągłą pętlę, podział na obszary, perspektywę tradera | Agent musi działać autonomicznie i ciągle |

---

*Wersja: 3.0*
*Cel: Autonomiczny agent AI w ciągłej pętli budujący produkt dla traderów*
*Zasada: GOTO FAZA 0 po każdej iteracji, aż użytkownik przerwie*
