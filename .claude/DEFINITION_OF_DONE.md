# Definition of Done - FXcrypto Platform

**Wersja:** 4.0 | **Data:** 2025-12-02

---

## CEL BIZNESOWY (Niezmienny)

**Dostarczyć traderowi narzędzie, które pozwala:**

```
STWORZYĆ strategię → PRZETESTOWAĆ na historii → URUCHOMIĆ na żywo → ZOPTYMALIZOWAĆ na podstawie wyników
```

**Kluczowa zasada:** Buduję NARZĘDZIE, nie strategię. Trader sam optymalizuje.

---

## DEFINICJA "DONE" - PER TYP ZADANIA

### Dla NAPRAWY BUGA (Fix)

| # | Warunek | Jak zweryfikować |
|---|---------|------------------|
| 1 | Bug nie występuje | Test który wcześniej FAIL teraz PASS |
| 2 | Brak regresji | `python run_tests.py` - wszystkie PASS |
| 3 | Kod działa w runtime | curl/UI pokazuje poprawne zachowanie |

### Dla NOWEJ FUNKCJONALNOŚCI (Feature)

| # | Warunek | Jak zweryfikować |
|---|---------|------------------|
| 1 | Funkcja działa zgodnie z opisem | Test jednostkowy PASS |
| 2 | Integracja działa | Test E2E lub curl PASS |
| 3 | Brak regresji | `python run_tests.py` - wszystkie PASS |
| 4 | Trader może użyć | UI/API jest dostępne i zrozumiałe |

### Dla REFAKTORINGU

| # | Warunek | Jak zweryfikować |
|---|---------|------------------|
| 1 | Zachowanie bez zmian | Wszystkie istniejące testy PASS |
| 2 | Kod jest prostszy | Mniej linii LUB lepsza czytelność |
| 3 | Brak dead code | `grep -rn "TODO\|FIXME\|NotImplementedError"` = 0 nowych |

---

## METRYKI - DEFINICJE

### Skala ocen: 1-10

- **1-3:** Nie działa / Blokuje użycie / BLOCKER
- **4-5:** Działa z problemami / Frustrujące
- **6-7:** Działa akceptowalnie / Wymaga poprawy
- **8-9:** Działa dobrze / Drobne usprawnienia
- **10:** Doskonałe / Kompletne

### Wymiary oceny:

| Metryka | Opis | Jak mierzyć |
|---------|------|-------------|
| **Działanie** | Czy kod robi to co powinien? | Testy PASS/FAIL |
| **Kompletność** | Ile % funkcji zaimplementowanych? | Checklist funkcji |
| **Blocker** | Czy są błędy blokujące? | 0 = brak, 1-3 = są blockery |
| **Użyteczność** | Czy trader bez IT może używać? | Symulacja "Trader Journey" |
| **Wydajność** | Czy jest szybkie? | Response time <1s |
| **Observability** | Czy widać co się dzieje? | Logi, błędy zrozumiałe |

---

## TABELA METRYK - BACKEND

*Aktualizacja: 2025-12-02 | Testy: 358/536 PASS (66.8%)*

| Moduł | Działanie | Kompletność | Blocker | Użyteczność | Wydajność | Observability | ŚREDNIA |
|-------|-----------|-------------|---------|-------------|-----------|---------------|---------|
| **B1: API Server** | 8/10 | 7/10 | 9/10 | 7/10 | 8/10 | 8/10 | **7.8/10** |
| **B2: Strategy Manager** | 7/10 | 8/10 | 8/10 | 6/10 | 7/10 | 7/10 | **7.2/10** |
| **B3: Risk Manager** | 8/10 | 9/10 | 9/10 | 7/10 | 8/10 | 8/10 | **8.2/10** |
| **B4: Indicator Engine** | 8/10 | 9/10 | 9/10 | 7/10 | 8/10 | 7/10 | **8.0/10** |
| **B5: MEXC Adapter** | 7/10 | 7/10 | 8/10 | 6/10 | 7/10 | 6/10 | **6.8/10** |
| **B6: Order Manager** | 6/10 | 7/10 | 8/10 | 6/10 | 7/10 | 6/10 | **6.7/10** |
| **B7: Session Manager** | 6/10 | 6/10 | 7/10 | 5/10 | 6/10 | 5/10 | **5.8/10** |
| **B8: Event Bus** | 9/10 | 9/10 | 10/10 | 8/10 | 9/10 | 8/10 | **8.8/10** |
| **BACKEND ŚREDNIA** | 7.4 | 7.8 | 8.5 | 6.5 | 7.5 | 6.9 | **7.4/10** |

**Uzasadnienie ocen (2025-12-02):**
- B1: API działa (health OK), ale 91 FAIL w testach integracyjnych
- B2: 5 sekcji warunków działa, TODO w kodzie do PnL calculation
- B3: 6 kontroli ryzyka + nowa metoda use_budget() (fix KI4)
- B4: 17 wskaźników zaimplementowanych, TODO w telemetrii
- B5: Futures adapter działa, WebSocket reconnect wymaga poprawy (KI2)
- B6: Paper trading działa, placeholder w realized PnL
- B7: Backtest działa, hardcoded max_drawdown=0.0 (PH1), brak sharpe_ratio (PH2)
- B8: EventBus stabilny, testy PASS

**Opis modułów Backend:**
- **B1: API Server** - REST + WebSocket endpoints, routing, auth
- **B2: Strategy Manager** - Zarządzanie strategiami, ewaluacja warunków S1/O1/Z1/ZE1/E1
- **B3: Risk Manager** - 6 kontroli ryzyka, ocena pozycji, limity
- **B4: Indicator Engine** - Obliczanie 17 wskaźników w real-time
- **B5: MEXC Adapter** - Połączenie z giełdą, market data, wykonywanie zleceń
- **B6: Order Manager** - Zarządzanie zleceniami (live + paper)
- **B7: Session Manager** - Sesje tradingowe, backtesting
- **B8: Event Bus** - Komunikacja między komponentami

---

## TABELA METRYK - FRONTEND

*Aktualizacja: 2025-12-02 | Frontend nie uruchomiony - wymaga npm run dev*

| Moduł | Działanie | Kompletność | Blocker | Użyteczność | Wydajność | Observability | ŚREDNIA |
|-------|-----------|-------------|---------|-------------|-----------|---------------|---------|
| **F1: Dashboard** | 6/10 | 5/10 | 7/10 | 5/10 | 6/10 | 5/10 | **5.7/10** |
| **F2: Strategy Builder** | 7/10 | 7/10 | 8/10 | 6/10 | 7/10 | 5/10 | **6.7/10** |
| **F3: Backtesting UI** | 5/10 | 5/10 | 6/10 | 4/10 | 5/10 | 4/10 | **4.8/10** |
| **F4: Live Trading UI** | 4/10 | 4/10 | 5/10 | 4/10 | 5/10 | 4/10 | **4.3/10** |
| **F5: Paper Trading UI** | 5/10 | 5/10 | 6/10 | 4/10 | 5/10 | 4/10 | **4.8/10** |
| **F6: Indicators UI** | 6/10 | 6/10 | 7/10 | 5/10 | 6/10 | 5/10 | **5.8/10** |
| **F7: Risk Management UI** | 4/10 | 4/10 | 5/10 | 4/10 | 5/10 | 4/10 | **4.3/10** |
| **F8: Charts & Visualization** | 5/10 | 5/10 | 6/10 | 5/10 | 5/10 | 4/10 | **5.0/10** |
| **F9: Auth & Navigation** | 7/10 | 7/10 | 8/10 | 6/10 | 7/10 | 6/10 | **6.8/10** |
| **FRONTEND ŚREDNIA** | 5.4 | 5.3 | 6.4 | 4.8 | 5.7 | 4.6 | **5.4/10** |

**Uzasadnienie ocen (2025-12-02):**
- F1-F8: Frontend wymaga uruchomienia (`npm run dev`) - oceny bazują na przeglądzie kodu
- F2: Strategy Builder ma endpoint API, ale UX wymaga testowania
- F3/F5: Backtesting/Paper Trading wymaga QuestDB + frontend
- F4/F7: Live Trading i Risk UI częściowo zaimplementowane
- F9: Auth działa (hardcoded demo accounts - do naprawy)

**Opis modułów Frontend:**
- **F1: Dashboard** - Główny ekran, watchlist, live indicators, sygnały
- **F2: Strategy Builder** - Kreator strategii (5 sekcji warunków)
- **F3: Backtesting UI** - Wybór sesji, uruchomienie, wyniki, wykresy
- **F4: Live Trading UI** - Trading na żywo, pozycje, zlecenia
- **F5: Paper Trading UI** - Symulacja tradingu
- **F6: Indicators UI** - Lista wskaźników, warianty, parametry
- **F7: Risk Management UI** - Ustawienia limitów ryzyka
- **F8: Charts & Visualization** - Wykresy: equity curve, drawdown, świece
- **F9: Auth & Navigation** - Logowanie, menu, routing

---

## TABELA METRYK - DATABASE & INFRASTRUCTURE

*Aktualizacja: 2025-12-02 | QuestDB: NOT RUNNING (port 8812)*

| Moduł | Działanie | Kompletność | Blocker | Użyteczność | Wydajność | Observability | ŚREDNIA |
|-------|-----------|-------------|---------|-------------|-----------|---------------|---------|
| **D1: QuestDB Integration** | 7/10 | 8/10 | 6/10 | 6/10 | 8/10 | 6/10 | **6.8/10** |
| **D2: Data Collection** | 7/10 | 7/10 | 7/10 | 6/10 | 7/10 | 6/10 | **6.7/10** |
| **D3: Strategy Storage** | 6/10 | 6/10 | 7/10 | 5/10 | 6/10 | 5/10 | **5.8/10** |
| **I1: Container (DI)** | 9/10 | 9/10 | 10/10 | 8/10 | 9/10 | 8/10 | **8.8/10** |
| **I2: Health Monitor** | 8/10 | 8/10 | 9/10 | 7/10 | 8/10 | 8/10 | **8.0/10** |
| **I3: Logging** | 8/10 | 8/10 | 9/10 | 7/10 | 8/10 | 9/10 | **8.2/10** |
| **INFRA ŚREDNIA** | 7.5 | 7.7 | 8.0 | 6.5 | 7.7 | 7.0 | **7.4/10** |

**Uzasadnienie ocen (2025-12-02):**
- D1: QuestDB wymaga ręcznego uruchomienia - bloker dla testów integracyjnych
- D2: Zbieranie danych działa gdy QuestDB jest uruchomiony
- D3: Strategy storage wymaga QuestDB, OA3 brak persystencji stanu
- I1: Container działa stabilnie, NO hardcoded values
- I2: Health endpoint działa (/health zwraca healthy)
- I3: StructuredLogger działa, JSON format

**Opis:**
- **D1: QuestDB Integration** - Połączenie z bazą, zapytania SQL, zapis ticków
- **D2: Data Collection** - Zbieranie danych rynkowych do backtestingu
- **D3: Strategy Storage** - Persystencja strategii
- **I1: Container (DI)** - Dependency Injection, factory methods
- **I2: Health Monitor** - Monitoring zdrowotności systemu
- **I3: Logging** - Strukturalne logi, error tracking

---

## PODSUMOWANIE METRYK

*Aktualizacja: 2025-12-02*

| Warstwa | Średnia | Trend | Blockery |
|---------|---------|-------|----------|
| **BACKEND** | 7.4/10 | ↑ (fix KI4) | KI2 WebSocket, PH1/PH2 placeholders |
| **FRONTEND** | 5.4/10 | → | Wymaga QuestDB + npm run dev |
| **DATABASE & INFRA** | 7.4/10 | → | QuestDB not running |
| **PRODUKT** | **6.7/10** | ↑ | D1 bloker, F4/F7 niekompletne |

---

## TEST AKCEPTACYJNY: "TRADER JOURNEY"

**Produkt jest GOTOWY gdy trader może wykonać poniższy scenariusz bez pomocy:**

*Aktualizacja: 2025-12-02*

| Krok | Akcja | Oczekiwany rezultat | Moduły | Status |
|------|-------|---------------------|--------|--------|
| 1 | Otwiera http://localhost:3000 | Dashboard się ładuje | F1, B1 | ⚠️ Wymaga npm run dev |
| 2 | Klika "Strategy Builder" | Formularz tworzenia strategii | F2, F9 | ⚠️ Frontend wymagany |
| 3 | Wybiera wskaźnik (np. PRICE_VELOCITY) | Lista dostępna, opisy zrozumiałe | F6, B4 | ✅ API działa |
| 4 | Definiuje warunki S1/Z1/ZE1/E1 | Formularz zapisuje bez błędów | F2, B2, D3 | ⚠️ Wymaga QuestDB |
| 5 | Uruchamia backtest | Wyniki się pokazują | F3, B7, D1 | ⚠️ Wymaga QuestDB |
| 6 | Widzi wykres equity curve | Rozumie jak kapitał się zmieniał | F8 | ⚠️ PH1 max_drawdown=0.0 |
| 7 | Widzi entry/exit na wykresie | Analizuje gdzie były transakcje | F8 | ⚠️ Frontend wymagany |
| 8 | Modyfikuje parametry strategii | Może ponowić backtest | F2, B2 | ⚠️ Wymaga full stack |
| 9 | Uruchamia paper trading | Sygnały w real-time | F5, B6 | ✅ use_budget() naprawiony |
| 10 | Coś nie działa | Błąd jest ZROZUMIAŁY (nie techniczny) | I3 | ✅ StructuredLogger |

**Aktualny wynik: 3/10 kroków działa (backend) + 7 wymaga uruchomienia full stack**

**Blokery do uruchomienia full stack:**
1. QuestDB nie działa (port 8812) - uruchom `.\start_all.ps1`
2. Frontend nie uruchomiony - uruchom `cd frontend && npm run dev`

---

## PRIORYTETY ZADAŃ

### P0: KRYTYCZNE (bez tego trader nie może używać)
- Blokuje "Trader Journey"
- Powoduje utratę danych lub pieniędzy
- System nie startuje
- Metryka "Blocker" < 5

### P1: WAŻNE (znacząco wpływa na użyteczność)
- Trader może używać, ale jest sfrustrowany
- Brakuje kluczowej informacji do decyzji
- Performance < akceptowalny
- Metryka "Kompletność" < 7

### P2: USPRAWNIENIA (lepszy UX)
- Nice-to-have
- Optymalizacje
- Dodatkowe funkcje
- Metryka "Użyteczność" < 8

---

## ZNANE PROBLEMY (linkuj do KNOWN_ISSUES.md)

*Aktualizacja: 2025-12-04*

| ID | Moduł | Problem | Priorytet | Status |
|----|-------|---------|-----------|--------|
| ~~KI4~~ | B3 | `RiskManager.use_budget()` nie istnieje | P0 | ✅ NAPRAWIONE |
| ~~KI2~~ | B5 | WebSocket reconnection nie działa | P1 | ✅ ZWERYFIKOWANE (12/12 tests) |
| ~~KI3~~ | B7 | Memory usage rośnie >24h | P2 | ✅ NAPRAWIONE - 3×P0 leaks fixed (9/9 tests): deque for session_manager, paper_trading; unsubscribe in strategy_manager |
| ~~PH1~~ | B7 | `max_drawdown = 0.0` - placeholder | P0 | ✅ NAPRAWIONE (8/8 tests) |
| ~~PH2~~ | B7 | `sharpe_ratio = None` - placeholder | P1 | ✅ NAPRAWIONE (11/11 tests) |
| ~~TODO1~~ | B4 | Telemetry placeholders (active_strategies=0) | P2 | ✅ NAPRAWIONE (12/12 tests) |
| ~~TODO2~~ | B6 | Realized PnL calculation placeholder | P1 | ✅ NAPRAWIONE (11/11 tests) |

Pełna lista: [KNOWN_ISSUES.md](KNOWN_ISSUES.md)

---

## KRYTERIA DECYZJI: CO ROBIĆ DALEJ?

### Algorytm wyboru następnego zadania:

```
1. Czy są CZERWONE FLAGI? (testy FAIL, backend nie działa)
   → TAK: Napraw najpierw

2. Czy jakiś moduł ma Blocker < 5?
   → TAK: Rozwiąż blocker (P0)

3. Który moduł ma najniższą ŚREDNIĄ metryk?
   → Pracuj nad tym modułem

4. W ramach modułu: które zadanie ma najwyższy wpływ na "Trader Journey"?
   → To zadanie jest następne
```

### Kiedy DODAĆ nową funkcjonalność vs POPRAWIĆ istniejącą?

| Sytuacja | Decyzja |
|----------|---------|
| Średnia metryk < 6/10 | POPRAWIAJ istniejące |
| Kompletność < 7/10 | DODAJ brakujące funkcje |
| Średnia >= 8/10 | Można dodawać usprawnienia |

---

## HISTORIA METRYK (Trend)

| Data | Iteracja | Moduł | Średnia przed | Średnia po | Zmiana |
|------|----------|-------|---------------|------------|--------|
| 2025-12-02 | 1 | B3 Risk Manager | 7.5/10 | 8.2/10 | +0.7 (fix KI4 use_budget) |
| 2025-12-02 | 1 | BACKEND | - | 7.4/10 | Baseline |
| 2025-12-02 | 1 | FRONTEND | - | 5.4/10 | Baseline |
| 2025-12-02 | 1 | INFRA | - | 7.4/10 | Baseline |
| 2025-12-02 | 1 | PRODUKT | - | 6.7/10 | Baseline |
| 2025-12-04 | 2 | B7 Session | 5.8/10 | 7.0/10 | +1.2 (fix PH1, PH2) |
| 2025-12-04 | 2 | B6 Order Manager | 6.7/10 | 7.1/10 | +0.4 (fix TODO2) |
| 2025-12-04 | 2 | B5 MEXC Adapter | 6.8/10 | 7.4/10 | +0.6 (verify KI2) |
| 2025-12-04 | 2 | B4 Indicator Engine | 8.0/10 | 8.3/10 | +0.3 (fix TODO1) |
| 2025-12-04 | 2 | BACKEND | 7.4/10 | 8.0/10 | +0.6 (5 issues fixed) |

---

*Ten dokument definiuje CEL i MIARY SUKCESU. Proces pracy jest w [WORKFLOW.md](../WORKFLOW.md)*
