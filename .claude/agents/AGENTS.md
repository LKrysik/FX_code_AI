# System Agentów - FXcrypto

**Wersja:** 12.0 | **Data:** 2025-12-05

---

## MISJA

```
Doprowadzić system FXcrypto do stanu gdzie TRADER może:
1. Stworzyć strategię wykrywania pump/dump (5 sekcji)
2. Przetestować ją na historii (backtest z equity curve)
3. Uruchomić paper trading (symulacja z sygnałami)
4. Analizować wyniki (wykresy, metryki, P&L)

SUKCES: Trader może przejść cały flow BEZ pomocy technicznej
PORAŻKA: System crashuje, wykresy puste, sygnały nie generują się
```

---

## STRUKTURA AGENTÓW

```
Driver (koordynuje, NIE koduje, AUTONOMICZNY)
    ├── trading-domain  (perspektywa tradera, UX, VETO)
    ├── backend-dev     (Python/FastAPI, logika biznesowa)
    ├── frontend-dev    (Next.js/React, UI)
    ├── database-dev    (QuestDB, dane historyczne)
    └── code-reviewer   (jakość kodu)
```

---

## TRADER JOURNEY - PRAWDZIWE TESTY

**To nie są curle do /health. To są FLOW które trader NAPRAWDĘ wykonuje:**

### POZIOM 1: Fundamenty (musi działać żeby cokolwiek robić)

| # | Co trader robi | Jak zweryfikować | Dowód sukcesu |
|---|----------------|------------------|---------------|
| 1.1 | Otwiera dashboard | Frontend renderuje bez błędów JS | Widzi listę symboli, wykresy |
| 1.2 | Widzi dane rynkowe | OHLCV chart pokazuje świece | Świece mają OHLC, volume > 0 |
| 1.3 | Przełącza między krypto | Zmiana symbolu → nowe dane | BTC_USDT → ETH_USDT działa |

### POZIOM 2: Strategia (core feature)

| # | Co trader robi | Jak zweryfikować | Dowód sukcesu |
|---|----------------|------------------|---------------|
| 2.1 | Tworzy strategię 5-sekcji | Strategy Builder zapisuje | ID strategii zwrócone |
| 2.2 | Definiuje S1 (sygnał wejścia) | Warunek indicator > threshold | Walidacja PASS |
| 2.3 | Definiuje Z1 (entry) | Position size, direction | Zapisane poprawnie |
| 2.4 | Definiuje ZE1 (exit) | Take profit / stop loss | Walidacja PASS |
| 2.5 | Edytuje strategię | PUT → zmiana zapisana | GET zwraca nowe wartości |
| 2.6 | Usuwa strategię | DELETE → usunięte | GET zwraca 404 |

### POZIOM 3: Backtest (walidacja strategii)

| # | Co trader robi | Jak zweryfikować | Dowód sukcesu |
|---|----------------|------------------|---------------|
| 3.1 | Wybiera dane historyczne | Lista data collection sessions | Widzi dostępne sesje |
| 3.2 | Uruchamia backtest | POST /sessions/start (mode=backtest) | Session ID zwrócone |
| 3.3 | Widzi equity curve | GET equity-curve → dane | Array z timestamps i values |
| 3.4 | Widzi listę transakcji | GET trades → lista | Entry/exit z cenami |
| 3.5 | Widzi metryki | Performance endpoint | win_rate, profit_factor, max_drawdown, sharpe_ratio |
| 3.6 | Porównuje strategie | Dwa backtesty → różne wyniki | Może wybrać lepszą |

### POZIOM 4: Paper Trading (symulacja live)

| # | Co trader robi | Jak zweryfikować | Dowód sukcesu |
|---|----------------|------------------|---------------|
| 4.1 | Uruchamia paper trading | POST paper-trading/sessions | Session created |
| 4.2 | Widzi generowane sygnały | SignalHistoryPanel pokazuje | Sygnały z timestamp, type |
| 4.3 | Widzi otwarte pozycje | PositionMonitor pokazuje | Entry price, unrealized P&L |
| 4.4 | Widzi wykonane transakcje | TransactionHistory pokazuje | Filled orders z cenami |
| 4.5 | Zatrzymuje sesję | POST stop → session stopped | Status = STOPPED |
| 4.6 | Analizuje wyniki | Performance metrics | Kompletne metryki |

### POZIOM 5: Live Trading (prawdziwe pieniądze)

| # | Co trader robi | Jak zweryfikować | Dowód sukcesu |
|---|----------------|------------------|---------------|
| 5.1 | Konfiguruje API keys | Settings → MEXC credentials | Połączenie OK |
| 5.2 | Ustawia budżet | Risk Management → limits | Budget allocated |
| 5.3 | Uruchamia live | POST sessions/start (mode=live) | Session running |
| 5.4 | Zamyka pozycję ręcznie | POST positions/{id}/close | Position closed, P&L captured |
| 5.5 | Anuluje zlecenie | POST orders/{id}/cancel | Order cancelled |

---

## TESTOWANIE TRADER JOURNEY

### Jak testować (nie curl /health!):

```python
# TEST 3.3: Equity curve z danymi
def test_backtest_equity_curve():
    # 1. Uruchom backtest
    session = start_backtest(strategy_id, data_collection_id)

    # 2. Pobierz equity curve
    equity = get_equity_curve(session.id)

    # 3. PRAWDZIWE ASERCJE:
    assert len(equity) > 0, "Equity curve nie może być pusta"
    assert all(e.value > 0 for e in equity), "Wartości muszą być > 0"
    assert equity[-1].timestamp > equity[0].timestamp, "Timestamps rosnące"

    # 4. Sprawdź że to nie są placeholder dane
    assert equity[0].value != equity[-1].value, "Wartości się zmieniają"
```

```python
# TEST 4.2: Sygnały generowane
def test_paper_trading_signals():
    # 1. Uruchom paper trading
    session = start_paper_trading(strategy_id, symbols=["BTC_USDT"])

    # 2. Czekaj na sygnały (max 60s)
    signals = wait_for_signals(session.id, timeout=60)

    # 3. PRAWDZIWE ASERCJE:
    assert len(signals) > 0, "Powinny być sygnały"
    assert all(s.type in ["S1_LONG", "S1_SHORT"] for s in signals)
    assert all(s.confidence > 0 for s in signals)
```

---

## DRIVER: AUTONOMICZNA PĘTLA

```
START SESJI
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  1. ANALIZA                                                 │
│     • Trader Journey Check (poziomy 1-5)                    │
│     • Który poziom nie działa?                              │
│     • Co blokuje tradera?                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  2. ROADMAPA SESJI                                          │
│     • Cel: Naprawić poziom X                                │
│     • Plan: Które testy muszą przejść                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  3. DECYZJA (algorytm)                                      │
│     Poziom 1 ❌ → Napraw fundamenty                         │
│     Poziom 2 ❌ → Napraw strategię                          │
│     Poziom 3 ❌ → Napraw backtest                           │
│     Poziom 4 ❌ → Napraw paper trading                      │
│     Poziom 5 ❌ → Napraw live trading                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  4. DELEGACJA                                               │
│     • Do którego agenta                                     │
│     • Co dokładnie naprawić                                 │
│     • Jak zweryfikować sukces                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  5. WERYFIKACJA                                             │
│     • Test przeszedł?                                       │
│     • Trader może wykonać akcję?                            │
│     • Dane są prawdziwe (nie placeholder)?                  │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    SUKCES                  PORAŻKA
         │                       │
    Update status          Feedback/Eskaluj
         │                       │
         └───────────┬───────────┘
                     │
              NASTĘPNA ITERACJA
                     │
              (aż wszystkie poziomy ✅)
```

---

## FAZA 1: ANALIZA

```markdown
## ANALIZA STANU - [data]

### Trader Journey Status

| Poziom | Status | Blokuje |
|--------|--------|---------|
| 1. Fundamenty | ✅/❌ | - |
| 2. Strategia | ✅/❌ | Poziom 3-5 |
| 3. Backtest | ✅/❌ | Poziom 4-5 |
| 4. Paper Trading | ✅/❌ | Poziom 5 |
| 5. Live Trading | ✅/❌ | - |

### Który test FAIL?
[Konkretny test np. "3.3 Equity curve pusta"]

### Co trader widzi?
[Opis z perspektywy użytkownika]
```

---

## FAZA 2: ROADMAPA SESJI

```markdown
## ROADMAPA SESJI - [data]

### CEL: Naprawić Poziom [X]

### Które testy muszą przejść:
| Test | Opis | Agent |
|------|------|-------|
| X.1 | [opis] | [agent] |
| X.2 | [opis] | [agent] |

### Kryterium sukcesu:
[Co trader będzie mógł zrobić po naprawie]
```

---

## FAZA 3: ALGORYTM PRIORYTETYZACJI

```
1. POZIOM 1 NIE DZIAŁA? (fundamenty)
   → Frontend crash, brak danych, błędy JS
   → Napraw NAJPIERW (blokuje wszystko)

2. POZIOM 2 NIE DZIAŁA? (strategia)
   → Trader nie może stworzyć/zapisać strategii
   → Napraw (blokuje backtesty)

3. POZIOM 3 NIE DZIAŁA? (backtest)
   → Equity curve pusta, brak transakcji
   → Napraw (blokuje paper trading)

4. POZIOM 4 NIE DZIAŁA? (paper trading)
   → Brak sygnałów, pozycje nie otwierają się
   → Napraw (blokuje live)

5. POZIOM 5 NIE DZIAŁA? (live)
   → Połączenie z giełdą fail, zlecenia nie wykonują się
   → Napraw
```

---

## MATRYCA DELEGACJI

| Problem | Symptom | Agent |
|---------|---------|-------|
| Frontend crash | Błędy JS w konsoli | frontend-dev |
| Wykresy puste | OHLCV nie ładuje | backend-dev (API) → database-dev (QuestDB) |
| Strategia nie zapisuje | POST zwraca error | backend-dev |
| Backtest equity = 0 | Pusta equity curve | backend-dev (algorytm) |
| Sygnały nie generują | SignalHistory puste | backend-dev (indicator engine) |
| Paper trading nie działa | Brak pozycji | backend-dev (paper trading engine) |
| Live trading fail | Błąd MEXC | backend-dev (MEXC adapter) |

---

## URUCHAMIANIE I RESTART USŁUG

### Uruchomienie wszystkich usług:
```powershell
.\start_all.ps1
```

Uruchamia:
- QuestDB (port 9000, 8812)
- Backend API (port 8080)
- Frontend UI (port 3000)

### Restart backendu:
```powershell
.\restart_backend.ps1

# Lub ręcznie:
# Ctrl+C w terminalu z backendem
python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8080 --reload
```

### Restart frontendu:
```bash
cd frontend && npm run dev
```

### Weryfikacja że działa:
```bash
# Backend
curl http://localhost:8080/health
# → {"status": "healthy"}

# Frontend
# Otwórz http://localhost:3000 w przeglądarce
# → Dashboard renderuje bez błędów
```

---

## TYPY PROBLEMÓW

### TYP A: Problem KODU
- Funkcja zwraca błędny wynik
- Brak implementacji
- Edge case nie obsłużony

**PROCES:** TDD (RED → GREEN → REFACTOR)

### TYP B: Problem INFRASTRUKTURY
- Usługa nie odpowiada
- Port zajęty
- QuestDB nie działa

**PROCES:**
```powershell
# 1. Sprawdź czy usługa działa
netstat -an | findstr "8080"   # Backend
netstat -an | findstr "3000"   # Frontend
netstat -an | findstr "9000"   # QuestDB

# 2. Restart
.\start_all.ps1
# lub restart konkretnej usługi

# 3. Weryfikuj
curl http://localhost:8080/health
```

### TYP C: Problem DANYCH
- Brak danych historycznych
- Data collection nie zebrana
- QuestDB pusta

**PROCES:**
1. Sprawdź czy są dane: `GET /api/data-collection/sessions`
2. Jeśli brak → uruchom data collection
3. Weryfikuj: powinny być OHLCV dane

---

## RAPORT PO ZADANIU

```markdown
## RAPORT: [zadanie]

### STATUS
[Co zrobiłem]

### TRADER JOURNEY
Test [X.Y]: ❌ → ✅

### DOWODY
[Screenshot lub output pokazujący że TRADER może wykonać akcję]

### ZMIANY
| Plik:linia | Zmiana |
|------------|--------|

### CO TRADER TERAZ MOŻE ROBIĆ
[Opis z perspektywy użytkownika]
```

---

## TRADING-DOMAIN: OCENA UX

```markdown
## OCENA UX: [funkcja]

### Scenariusz
Trader chce: [cel]

### Kroki:
1. [co klika]
2. [co widzi]
3. [co robi dalej]

### Checklist
- [ ] Osiągalne w < 5 kliknięć?
- [ ] Oczywiste co robić (bez dokumentacji)?
- [ ] Błędy zrozumiałe?
- [ ] Można cofnąć?

### WERDYKT: PASS / FAIL
```

---

## CODE-REVIEWER: CHECKLIST

```markdown
### JAKOŚĆ KODU
- [ ] Nowy kod ma testy
- [ ] Edge cases przetestowane
- [ ] Error handling konkretny (nie bare except)

### ARCHITEKTURA
- [ ] EventBus do komunikacji
- [ ] DI przez konstruktor
- [ ] Brak breaking changes

### TRADER JOURNEY
- [ ] Nie psuje żadnego testu z poziomów 1-5
- [ ] Błędy zrozumiałe dla tradera
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

## RAPORT KOŃCOWY SESJI

```markdown
## SESJA [data] - PODSUMOWANIE

### Trader Journey
Przed: Poziom X ❌
Po: Poziom X ✅

### Co trader TERAZ może robić
[Lista konkretnych akcji]

### Otwarte problemy
| Test | Problem |
|------|---------|

### Następna sesja
1. Naprawić: [test]
2. Cel: Poziom Y działający
```

---

## REGUŁY BEZWZGLĘDNE

### ZAWSZE
- ✅ Testuj z perspektywy TRADERA (nie API)
- ✅ Dowody = screenshot lub output pokazujący działanie
- ✅ Naprawiaj od Poziomu 1 w górę (fundamenty najpierw)

### NIGDY
- ❌ curl /health jako "dowód" że działa
- ❌ "Testy PASS" bez sprawdzenia czy trader może używać
- ❌ Docker (nie mamy!)

---

**Wersja:** 12.0 | **Zmieniono:** 2025-12-05

## CHANGELOG v11 → v12

| Zmiana | Uzasadnienie |
|--------|--------------|
| Usunięto Docker | Nie używamy - wszystko przez start_all.ps1 |
| Usunięto grepy security | Nie mieliśmy takich problemów |
| Usunięto proste curle /health | Nie dowodzą że system działa |
| Dodano PRAWDZIWY Trader Journey | 5 poziomów z konkretnymi testami |
| Dodano testy z perspektywy tradera | "Co trader może zrobić" nie "jaki HTTP code" |
| Dodano przykłady testów Python | Prawdziwe asercje, nie tylko status 200 |
