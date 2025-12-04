# System Agentów - FXcrypto

**Wersja:** 11.0 | **Data:** 2025-12-04

---

## ZASADA FUNDAMENTALNA

```
CEL: Wszystkie 10 kroków Trader Journey działają.
KONIEC: Gdy Trader Journey = 10/10 ✅ LUB użytkownik przerwie.
NIGDY: Nie ogłaszaj "sukces" - zawsze szukaj co jeszcze nie działa.
```

---

## STRUKTURA AGENTÓW

```
Driver (koordynuje, NIE koduje)
    ├── trading-domain  (perspektywa tradera, UX, priorytetyzacja)
    ├── backend-dev     (Python/FastAPI, logika biznesowa)
    ├── frontend-dev    (Next.js/React, UI)
    ├── database-dev    (QuestDB, infrastruktura)
    └── code-reviewer   (security, jakość kodu)
```

---

## TRADER JOURNEY - GŁÓWNY MIERNIK

**Produkt jest gotowy gdy trader może wykonać te 10 kroków:**

| # | Krok | Test | Cel |
|---|------|------|-----|
| 1 | Dashboard się ładuje | `curl -sI localhost:3000 \| head -1` → 200 | Wejście do systemu |
| 2 | Backend odpowiada | `curl localhost:8080/health` → healthy | API działa |
| 3 | Tworzenie strategii | `POST /api/strategies` → 201 | Trader może zacząć |
| 4 | Lista wskaźników | `GET /api/indicators` → lista | Trader widzi opcje |
| 5 | Backtest działa | `POST /api/backtest` → equity > 0 | Trader testuje strategię |
| 6 | Equity curve | Backtest zwraca wykres | Trader analizuje |
| 7 | Historia transakcji | `GET /api/trades` → lista | Trader widzi co się działo |
| 8 | Modyfikacja strategii | `PUT /api/strategies/{id}` → 200 | Trader iteruje |
| 9 | Paper trading | WebSocket tick w < 2s | Trader symuluje |
| 10 | Błędy zrozumiałe | Error ma message (nie stack trace) | Trader nie jest zgubiony |

**NASTĘPNY KROK = Pierwszy ❌ od góry.**

---

## DRIVER: MATRYCA DELEGACJI

| Symptom (Trader Journey ❌) | Diagnoza | Deleguj do |
|-----------------------------|----------|------------|
| Krok 1: Dashboard nie ładuje | Frontend crash/build | frontend-dev |
| Krok 2: Backend /health fail | API crash | backend-dev |
| Krok 3: Strategia nie zapisuje | API lub DB | backend-dev → jeśli DB problem → database-dev |
| Krok 4: Wskaźniki puste | Indicator engine | backend-dev |
| Krok 5: Backtest timeout/error | QuestDB lub algorytm | database-dev (DB) → backend-dev (algorytm) |
| Krok 6: Equity curve puste | Obliczenia lub UI | backend-dev (obliczenia) → frontend-dev (UI) |
| Krok 7: Brak transakcji | Persistence | database-dev → backend-dev |
| Krok 8: PUT nie działa | API endpoint | backend-dev |
| Krok 9: WebSocket disconnect | Połączenie | backend-dev |
| Krok 10: Błędy techniczne | UX error messages | trading-domain + frontend-dev |

### Kiedy eskalować

| Sytuacja | Akcja |
|----------|-------|
| Nie wiem komu delegować | Zapytaj trading-domain |
| Agent wraca bez rozwiązania 2x | Zbierz obu agentów |
| Wymaga zmian w wielu warstwach | Sekwencja: DB → Backend → Frontend |

---

## TYPY PROBLEMÓW

### TYP A: Problem KODU
- Funkcja zwraca błędny wynik
- NotImplementedError
- Edge case nie obsłużony
- Race condition

**PROCES:** TDD (RED → GREEN → REFACTOR → E2E)

### TYP B: Problem INFRASTRUKTURY
- Serwis nie odpowiada (docker down)
- Brak połączenia z DB
- Port zajęty

**PROCES:**
```bash
# 1. Status
docker ps | grep [service]

# 2. Logi
docker logs [service] 2>&1 | tail -20

# 3. Napraw
docker-compose up -d [service]

# 4. Weryfikuj
curl localhost:[port]/health
```

### TYP C: Problem KONFIGURACJI
- Złe wartości w .env
- Brakujące secrets

**PROCES:**
1. Porównaj z .env.example
2. Napraw
3. Restart serwisów
4. Weryfikuj

---

## FAZA 0: DIAGNOZA (5 min)

### Krok 1: Trader Journey Check

Uruchom i wypełnij:

```markdown
## TRADER JOURNEY - [data]

| # | Krok | Status |
|---|------|--------|
| 1 | Dashboard | ✅/❌ |
| 2 | Backend health | ✅/❌ |
| 3 | Create strategy | ✅/❌ |
| 4 | List indicators | ✅/❌ |
| 5 | Backtest | ✅/❌ |
| 6 | Equity curve | ✅/❌ |
| 7 | Trade history | ✅/❌ |
| 8 | Update strategy | ✅/❌ |
| 9 | Paper trading | ✅/❌ |
| 10 | Error messages | ✅/❌ |

WYNIK: X/10
NASTĘPNY: Krok [pierwszy ❌]
```

### Krok 2: Krytyczne problemy (grep)

```bash
# Security (KRYTYCZNE - uruchom ZAWSZE)
grep -rn "password\|secret\|api_key" src/ --include="*.py" | grep -v test | grep -v ".pyc"

# Niedokończone (P0)
grep -rn "NotImplementedError\|TODO:P0\|FIXME:P0" src/

# Placeholder (P1)
grep -rn "= 0\.0\|= None.*#.*placeholder" src/ --include="*.py"
```

**Jeśli znajdziesz security issue → P0, napraw NATYCHMIAST.**

### Krok 3: Identyfikacja typu

- Serwis nie odpowiada? → TYP B (INFRA)
- Funkcja zwraca błąd? → TYP A (KOD)
- Brakuje config? → TYP C (CONFIG)

---

## FAZA 1: DECYZJA

### Driver

Użyj matrycy delegacji. Deleguj z kontekstem:

```markdown
@[agent]:
- Problem: [opis]
- Trader Journey krok: [X]
- Typ: [KOD/INFRA/CONFIG]
- Kontekst: [co już sprawdzone]
```

### Inni agenci

```markdown
## DECYZJA

### Co robię?
[Konkretny opis zmiany]

### Który krok Trader Journey to poprawi?
[Krok X: nazwa]

### Typ problemu
[KOD / INFRA / CONFIG]
```

---

## FAZA 2: IMPLEMENTACJA

### Dla TYP A (KOD) - TDD

```
1. RED: Napisz test który FAIL
   $ pytest tests/test_X.py::test_name -v
   → FAILED (pokaż output)

2. GREEN: Napisz minimalny kod
   $ pytest tests/test_X.py::test_name -v
   → PASSED

3. REFACTOR: Wyczyść (testy nadal PASS)

4. E2E: Sprawdź Trader Journey
   $ curl localhost:8080/health
   $ python tests/e2e/test_trader_journey.py (jeśli istnieje)
```

### Dla TYP B (INFRA) - Checklist

```bash
# 1. Status
docker ps

# 2. Logi
docker logs [service] 2>&1 | tail -30

# 3. Napraw
docker-compose up -d [service]
# lub: docker-compose restart [service]

# 4. Weryfikuj
curl localhost:[port]/health
```

### Dla TYP C (CONFIG)

```bash
# 1. Sprawdź
cat .env | grep [VARIABLE]
diff .env .env.example

# 2. Napraw
# Edytuj .env

# 3. Restart
docker-compose restart

# 4. Weryfikuj
curl localhost:8080/health
```

---

## FRONTEND: JAK TESTOWAĆ

### Testy komponentów (Jest + React Testing Library)

```javascript
import { render, screen } from '@testing-library/react';
import { EquityCurve } from './EquityCurve';

test('EquityCurve renders data points', () => {
  const data = [100, 102, 98, 105];
  render(<EquityCurve data={data} />);

  expect(screen.getByTestId('equity-chart')).toBeInTheDocument();
});
```

### Testy E2E (Playwright)

```javascript
test('Trader can create strategy', async ({ page }) => {
  await page.goto('/strategies/new');
  await page.fill('[name="strategy-name"]', 'Test Strategy');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/strategies\/\d+/);
});
```

### Kiedy który test?

| Zmiana | Typ testu |
|--------|-----------|
| Nowy komponent | Jest + RTL |
| Zmiana w formularzu/flow | Playwright E2E |
| Integracja z API | Mock API + Jest |

---

## TRADING-DOMAIN: TEST UŻYTECZNOŚCI

Dla NOWYCH funkcji, wypełnij:

```markdown
## TEST UŻYTECZNOŚCI: [funkcja]

### Scenariusz
Nowy użytkownik chce: [cel]

### Kroki (maks 10):
1. [krok]
2. [krok]
...

### Checklist
- [ ] Cel osiągalny w < 5 krokach?
- [ ] Każdy krok oczywisty (bez dokumentacji)?
- [ ] Błędy zrozumiałe?
- [ ] Jest cofnij/anuluj?

### WERDYKT: PASS / FAIL
Jeśli FAIL → [co poprawić]
```

---

## CODE-REVIEWER: CHECKLIST

### BEZPIECZEŃSTWO (uruchom ZAWSZE)

```bash
grep -rn "password\|secret\|key\|token\|api_key" [zmienione pliki] | grep -v test
grep -rn "eval\|exec\|os.system" [zmienione pliki]
```

- [ ] Brak hardcoded secrets
- [ ] Brak eval/exec na user input
- [ ] SQL przez parametry (nie string concat)

### JAKOŚĆ KODU

- [ ] Nowy kod ma testy
- [ ] Edge cases przetestowane (null, empty, max)
- [ ] Error handling konkretny (nie bare `except:`)
- [ ] Logging dla operacji > 100ms

### ARCHITEKTURA

- [ ] Używa EventBus (nie direct calls między modułami)
- [ ] DI przez konstruktor (nie global imports)
- [ ] Brak breaking changes w API (lub migracja)

### TRADER JOURNEY

- [ ] Zmiana nie psuje żadnego z 10 kroków
- [ ] Błędy mają zrozumiały message

### FORMAT REVIEW

```markdown
## REVIEW: [plik]

### ✅ APPROVE / ⚠️ REQUEST CHANGES / ❌ REJECT

**Security:** OK / PROBLEM
**Testy:** OK / BRAK / NIEWYSTARCZAJĄCE
**Architektura:** OK / UWAGI
**Trader Journey:** OK / ZAGROŻONY KROK X

Komentarze:
- linia X: [uwaga]
```

---

## CIRCUIT BREAKER

```
Max 3 iteracje na jeden problem.

Iteracja 1: Próba rozwiązania
Iteracja 2: Inna metoda
Iteracja 3: Uproszczenie / workaround

Po 3 iteracjach BEZ POSTĘPU → ESKALUJ:
- Co próbowałem (3 podejścia)
- Dlaczego nie działa
- Propozycja zmiany zakresu
```

---

## FORMAT RAPORTU

```markdown
## RAPORT: [zadanie]

### STATUS
[Co zrobiłem - BEZ słów "sukces/gotowe/zrobione"]

### DOWODY
$ python run_tests.py
[output - summary + FAILED only]

$ curl localhost:8080/health
{"status": "healthy"}

### TRADER JOURNEY
Przed: X/10
Po: Y/10
Naprawiony krok: [który]

### ZMIANY
| Plik:linia | Zmiana |
|------------|--------|
| src/x.py:42 | [opis] |

### PLAN DALEJ
1. [następny krok]
2. [dlaczego ten]
```

---

## KIEDY DRIVER ODRZUCA RAPORT

```
ODRZUĆ jeśli:
[ ] Brak sekcji DOWODY z outputem
[ ] Brak TRADER JOURNEY przed/po
[ ] Użyte: "sukces" / "gotowe" / "zrobione"
[ ] Iteracja > 3 bez eskalacji
```

---

## REGUŁY BEZWZGLĘDNE

### ZAWSZE
- ✅ Output testów (nie "testy PASS")
- ✅ Trader Journey check przed i po
- ✅ Security grep przy każdym review
- ✅ TDD dla kodu, Checklist dla infra
- ✅ Eskaluj po 3 iteracjach

### NIGDY
- ❌ "sukces" / "gotowe" / "zrobione"
- ❌ > 3 iteracje bez eskalacji
- ❌ Ocena bez testu
- ❌ Review bez security grep
- ❌ Merge bez Trader Journey check

---

## DOKUMENTACJA

| Dokument | Kiedy używać |
|----------|--------------|
| Ten dokument (AGENTS.md) | Proces pracy |
| DEFINITION_OF_DONE.md | Metryki sukcesu |
| instructions.md | Jak uruchomić środowisko |

---

## REFLEKSJA (opcjonalna, raz na tydzień)

Jeśli proces nie działa, wypełnij:

```markdown
## REFLEKSJA - [data]

### Co nie zadziałało?
[konkretna sytuacja]

### Która sekcja AGENTS.md zawiodła?
[sekcja lub "BRAK SEKCJI"]

### Propozycja zmiany
[konkretna zmiana w procesie]
```

---

**Wersja:** 11.0 | **Zmieniono:** 2025-12-04

## CHANGELOG v10 → v11

| Zmiana | Uzasadnienie |
|--------|--------------|
| Usunięto 3 matryce oceny (210 pól) | Nie prowadziły do działań, tylko opis stanu |
| Dodano Trader Journey jako główny miernik | 10 binarnych testów zamiast subiektywnych ocen |
| Dodano matrycę delegacji dla Driver | Szybsza decyzja komu delegować |
| Rozróżnienie KOD/INFRA/CONFIG | TDD nie dla wszystkiego |
| Dodano sekcję testowania frontendu | frontend-dev wiedział jak testować |
| Dodano checklist code review | Spójne review, security zawsze |
| Dodano test użyteczności | trading-domain ma obiektywne kryteria |
| Uproszczono raport | 4 sekcje zamiast 7 |
| Refleksja opcjonalna | Raz na tydzień, nie każda sesja |

**Oszczędność:** ~20 min/sesję
**Fokus:** Trader Journey (wartość dla użytkownika) zamiast artefaktów kodu
