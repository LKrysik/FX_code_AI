# UI BACKLOG - FXcrypto Pump/Dump Detection

**Wersja:** 4.0 | **Data:** 2025-12-06

**Cel systemu:** Wykrywanie pump/dump i shortowanie na szczycie pumpu

**Filozofia:** STATE MACHINE CENTRIC DESIGN - wszystko w UI musi wspierać:
1. Konfigurację state machine (Strategy Builder)
2. Obserwację state machine w czasie rzeczywistym (Dashboard)
3. Analizę historii state machine (Session History)

**Powiązane dokumenty:**
- `docs/UI_INTERFACE_SPECIFICATION.md` - Pełny opis interfejsu i architektury systemu

---

## JAK UŻYWAĆ TEGO DOKUMENTU

### Dla Driver/frontend-dev:
1. Wybierz zadanie z najwyższym priorytetem (CRITICAL → HIGH → MEDIUM → LOW)
2. Zaimplementuj funkcję
3. Zaktualizuj status na `DONE` i dodaj datę
4. Zaktualizuj `UI_INTERFACE_SPECIFICATION.md`

### Priorytety:
| Priorytet | Znaczenie |
|-----------|-----------|
| CRITICAL | Bez tego trader NIE WIDZI co robi state machine |
| HIGH | Znacząco utrudnia konfigurację lub monitoring |
| MEDIUM | Ułatwia pracę, ale można obejść |
| LOW | Nice to have |

---

## CRITICAL - STATE MACHINE VISIBILITY

**Bez tych funkcji trader NIE WIE co robi system!**

### FAZA 2: LIVE MONITORING (Dashboard)

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| SM-01 | **State overview table** | Tabela: Strategy × Symbol × STAN × Since | ✅ DONE (2025-12-06) |
| SM-02 | **Current state display** | Duży badge: MONITORING / SIGNAL_DETECTED / POSITION_ACTIVE | ✅ DONE (2025-12-06) |
| SM-03 | **Condition progress** | Które warunki Z1/ZE1/E1 spełnione ✅, które pending ❌ | ✅ DONE (2025-12-06) |
| SM-04 | **Transition log** | Lista: timestamp → from_state → to_state → trigger values | ✅ DONE (2025-12-06) |
| SM-05 | **Chart S1/Z1/ZE1 markers** | Markery na wykresie gdzie pump, peak, dump end | TODO |

### FAZA 2: CHART (Dashboard)

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| CH-01 | **Zoom wykresu** | Scroll wheel lub +/- buttons | TODO |
| CH-02 | **Przewijanie wykresu** | Drag w historię (analiza przeszłych pumpów) | TODO |
| CH-03 | **Entry/SL/TP lines** | Poziome linie pokazujące SHORT pozycję | TODO |

### FAZA 2: POSITION MANAGEMENT (Dashboard)

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| PM-01 | **Position panel** | Entry, current, P&L, SL, TP, leverage, time | TODO |
| PM-02 | **Emergency close** | Szybkie zamknięcie gdy pump kontynuuje | TODO |
| PM-03 | **Modify SL/TP** | Przesunięcie stopów | TODO |

### FAZA 3: SESSION HISTORY (NOWA STRONA!)

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| SH-01 | **Session list page** | `/session-history` - lista wszystkich sesji | TODO |
| SH-02 | **Session detail page** | `/session-history/[id]` - szczegóły sesji | TODO |
| SH-03 | **Summary stats** | S1 count, Z1 count, O1 count, E1 count, accuracy | TODO |
| SH-04 | **Transition timeline** | Wizualna oś czasu z przejściami | TODO |
| SH-05 | **Transition details** | Expandable: jakie wartości miały wskaźniki | TODO |
| SH-06 | **Chart with markers** | Wykres z zaznaczonymi S1/Z1/ZE1 | TODO |
| SH-07 | **Per-trade breakdown** | Tabela: każdy trade osobno z P&L | TODO |

---

## HIGH - KONFIGURACJA I UNDERSTANDING

**Bez tych funkcji trader nie wie JAK skonfigurować system poprawnie.**

### FAZA 1: STRATEGY BUILDER

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| SB-01 | **State machine diagram** | Wizualizacja: MONITORING → S1 → Z1 → ZE1/E1 | TODO |
| SB-02 | **Quick backtest** | Ile S1, Z1, O1, E1 by wygenerowała strategia | TODO |
| SB-03 | **"Where would S1 trigger"** | Zaznacz na wykresie gdzie byłyby sygnały | TODO |
| SB-04 | **Variant tooltips** | Tooltip: "PumpFast" = t1=5s, t3=30s, d=15s | TODO |

### FAZA 1: INDICATOR VARIANTS

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| IV-01 | **Preview on chart** | Wykres: jak wariant reaguje na historyczne pumpy | TODO |
| IV-02 | **Compare variants** | Fast vs Medium na tym samym wykresie | TODO |
| IV-03 | **Parameter docs** | Co robi t1, t3, d? Jaki efekt ma zmiana? | TODO |
| IV-04 | **Signal count test** | Ile S1 wygenerowałby wariant w 24h | TODO |

### FAZA 2: TRADING SESSION

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| TS-01 | **Strategy preview** | Po zaznaczeniu: pokaż warunki S1, Z1, ZE1 | TODO |
| TS-02 | **Session matrix** | Tabela: strategia × symbol = X instancji | TODO |
| TS-03 | **Symbol recommendation** | "SOL_USDT ma wysoki volume - dobry dla pump" | TODO |

### FAZA 2: DASHBOARD - PUMP INDICATORS

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| PI-01 | **Real-time pump values** | PUMP_MAGNITUDE, VELOCITY jako duże liczby | TODO |
| PI-02 | **Velocity trend** | Strzałka: pump przyspiesza ↑ / zwalnia ↓ | TODO |
| PI-03 | **Pump subplot** | Wykres wskaźników pump pod main chart | TODO |

---

## MEDIUM - ULEPSZENIA UX

### DATA COLLECTION

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| DC-01 | Download danych | Eksport do CSV | TODO |
| DC-02 | Pump history marking | Oznacz gdzie były historyczne pumpy | TODO |
| DC-03 | Data quality indicator | Wskaźnik luk w danych | TODO |

### MARKET SCANNER

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| MS-01 | Mini-wykres w tabeli | Sparkline przy każdym symbolu | TODO |
| MS-02 | Signal history | Co się działo z tym symbolem ostatnio | TODO |
| MS-03 | Panel szczegółów | Po kliknięciu wiersza - szczegóły | TODO |

### STRATEGY BUILDER

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| SB-05 | Complex conditions | (A AND B) OR C | TODO |
| SB-06 | Import/export | JSON export/import strategii | TODO |
| SB-07 | Version history | Historia zmian, rollback | TODO |

### SETTINGS

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| ST-01 | Default SL/TP | Domyślne wartości | TODO |
| ST-02 | Keyboard shortcuts | Konfiguracja skrótów | TODO |
| ST-03 | Profiles | Różne profile dla różnych stylów | TODO |

---

## LOW - NICE TO HAVE

### DASHBOARD

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| D-01 | Fibonacci retracement | Drawing tool | TODO |
| D-02 | Rectangle zones | Drawing tool | TODO |
| D-03 | Multi-timeframe | 1m/5m/15m/1h toggle | TODO |

### SESSION HISTORY

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| SH-08 | Replay mode | Odtworzenie sesji krok po kroku | TODO |
| SH-09 | Export report | PDF/CSV raport sesji | TODO |

### SYSTEM

| ID | Funkcja | Opis | Status |
|----|---------|------|--------|
| SY-01 | Keyboard shortcuts | ESC=stop, C=close, D=dashboard, etc. | TODO |
| SY-02 | Backup/restore | Export/import wszystkich ustawień | TODO |

---

## KEYBOARD SHORTCUTS (do zaimplementowania)

| Skrót | Funkcja | Priorytet |
|-------|---------|-----------|
| ESC | Emergency Stop All | HIGH |
| C | Close current position | HIGH |
| D | Go to Dashboard | MEDIUM |
| T | Go to Trading Session | MEDIUM |
| S | Go to Session History | MEDIUM |
| +/- | Zoom chart | MEDIUM |
| ←→ | Scroll chart | MEDIUM |
| 1-9 | Switch symbols in watchlist | LOW |
| F | Full screen chart | LOW |

---

## BACKEND REQUIREMENTS (dla state machine visibility)

Żeby UI mogło pokazywać state machine, backend MUSI dostarczać:

| Endpoint | Dane | Status |
|----------|------|--------|
| GET /api/sessions/{id}/state | Aktualny stan każdej instancji | ✅ DONE (2025-12-06) |
| GET /api/sessions/{id}/transitions | Lista przejść z wartościami | ✅ DONE (placeholder) |
| GET /api/sessions/{id}/conditions | Aktualny progress warunków S1/O1/Z1/ZE1/E1 | ✅ DONE (2025-12-06) |
| WS /ws | Real-time events (subscription model) | ✅ EXISTS |
| POST /api/sessions/{id}/stop | Emergency stop session | ✅ EXISTS |

---

## STATYSTYKI BACKLOGU

| Priorytet | Liczba | Zrobione |
|-----------|--------|----------|
| CRITICAL | 17 | 4 |
| HIGH | 14 | 0 |
| MEDIUM | 13 | 0 |
| LOW | 6 | 0 |
| **RAZEM** | **50** | **4** |

### Rozkład według faz

| Faza | CRITICAL | HIGH | MEDIUM | LOW |
|------|----------|------|--------|-----|
| Faza 1: Konfiguracja | 0 | 8 | 3 | 0 |
| Faza 2: Monitoring | 10 | 6 | 4 | 3 |
| Faza 3: Analiza | 7 | 0 | 0 | 2 |
| System | 0 | 0 | 6 | 1 |

---

## CHANGELOG

### v4.1 (2025-12-06)
- Backend: GET /api/sessions/{id}/conditions ✅ - pełna implementacja
- Naprawiono SM integration components - poprawne endpointy:
  - StateOverviewTable.integration.tsx → /api/sessions/{id}/state
  - TransitionLog.integration.tsx → /api/sessions/{id}/transitions
  - ConditionProgress.integration.tsx → /api/sessions/{id}/conditions
- Weryfikacja: Strategy evaluation loop ISTNIEJE (event-driven przez indicator.updated)
- Analiza architektury: session flow, UI-backend communication verified

### v4.0 (2025-12-06)
- **STATE MACHINE VISIBILITY ZAIMPLEMENTOWANA!**
- SM-01: StateOverviewTable - tabela wszystkich instancji ✅
- SM-02: StateBadge - kolorowe badge stanów ✅
- SM-03: ConditionProgress - progress warunków S1/Z1/ZE1/E1 ✅
- SM-04: TransitionLog - historia przejść ✅
- Backend: GET /api/sessions/{id}/state ✅
- Backend: GET /api/sessions/{id}/transitions (placeholder) ✅
- Integracja komponentów w Dashboard page.tsx ✅
- Nowy Tab "State Transitions" w Dashboard ✅

### v3.0 (2025-12-06)
- **MAJOR REFACTOR:** Backlog przeprojektowany pod STATE MACHINE CENTRIC DESIGN
- Nowa struktura: CRITICAL = state machine visibility
- Dodano całą sekcję Session History (NOWA STRONA!) - 7 pozycji CRITICAL
- Dodano Backend Requirements - co API musi dostarczać
- Przenumerowano wszystkie ID dla jasności
- Dodano statystyki według faz

### v2.0 (2025-12-06)
- Restrukturyzacja pod pump/dump workflow
- Dodano kategorie CRITICAL dla pump detection

### v1.0 (2025-12-05)
- Początkowa wersja backlogu
