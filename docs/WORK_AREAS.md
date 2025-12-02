# 20 Obszarów Prac - FXcrypto Platform

**Data utworzenia:** 2025-12-02
**WGP (Wskaźnik Gotowości Produkcyjnej):** 72% (RC - Release Candidate)

---

## KATEGORYZACJA STATUS

| Status | Znaczenie |
|--------|-----------|
| **WDROŻONE** | Funkcjonalność działa, wymaga tylko utrzymania |
| **DO WDROŻENIA** | Warto zrobić, przynosi wartość traderowi |
| **ODRZUCONE** | Nie warto robić (zbyt skomplikowane, niski ROI) |
| **W TRAKCIE** | Częściowo zaimplementowane |

---

## METRYKI OBSZARÓW (FAZA 0)

| Obszar | UB | ŁU | FB | NZ | JK | WY | OB | ŚR |
|--------|----|----|----|----|----|----|----|----|
| A1 Strategy Builder | 8 | 7 | 8 | 7 | 7 | 8 | 6 | **7.3** |
| A2 Backtesting | 8 | 7 | 8 | 7 | 7 | 8 | 7 | **7.4** |
| A3 Wskaźniki | 9 | 8 | 9 | 8 | 8 | 9 | 7 | **8.3** |
| A4 Sygnały | 8 | 6 | 7 | 7 | 7 | 8 | 5 | **6.9** |
| A5 Frontend | 7 | 7 | 8 | 6 | 6 | 7 | 5 | **6.6** |
| A6 Backend API | 8 | 7 | 8 | 8 | 7 | 8 | 7 | **7.6** |
| A7 Baza Danych | 8 | 8 | 8 | 8 | 7 | 9 | 7 | **7.9** |
| **ŚREDNIA** | **8.0** | **7.1** | **8.0** | **7.3** | **7.0** | **8.1** | **6.3** | **7.4** |

**Legenda metryk:**
- UB = Użyteczność Biznesowa
- ŁU = Łatwość Użycia
- FB = Funkcjonalność Biznesowa
- NZ = Niezawodność
- JK = Jakość Kodu
- WY = Wydajność
- OB = Observability

---

## 20 OBSZARÓW PRAC

### PRIORYTET P1: KRYTYCZNE DLA TRADERA (ROI > 3.0)

---

#### W1: E2E Test Flow - Trader Path
**Status:** DO WDROŻENIA
**Obszary:** A1, A2, A4, A5
**ROI:** 4.5

**Problem:** Brak weryfikacji że cały flow działa od A do Z z perspektywy tradera.

**Co zrobić:**
1. Test automatyczny: Start → Utwórz strategię → Zbierz dane → Backtest → Sprawdź sygnały
2. Weryfikacja że każdy krok zwraca sensowne wyniki
3. Alert jeśli którykolwiek krok zawodzi

**Wartość dla tradera:** Pewność że system działa end-to-end, nie tylko poszczególne komponenty.

**AC:**
- [ ] Test E2E przechodzi w < 5 min
- [ ] Generuje min 1 sygnał podczas backtestu
- [ ] Raport z metryki (ticks_processed, signals_detected)

---

#### W2: Observability Dashboard
**Status:** DO WDROŻENIA
**Obszary:** A5, A6
**ROI:** 4.0

**Problem:** Trader nie widzi co się dzieje w systemie. Metryka OB = 5-6/10 w większości obszarów.

**Co zrobić:**
1. Panel "System Status" z health wszystkich komponentów
2. Liczniki: aktywne strategie, otwarte pozycje, sygnały/h
3. Alerty gdy coś nie działa

**Wartość dla tradera:** Wie czy system działa zanim zacznie polegać na sygnałach.

**AC:**
- [ ] Dashboard pokazuje status Backend/QuestDB/WebSocket
- [ ] Licznik sygnałów z ostatniej godziny
- [ ] Alert gdy health != healthy

---

#### W3: Sygnały z Confidence Score
**Status:** W TRAKCIE
**Obszary:** A4
**ROI:** 3.8

**Problem:** Sygnały są binarne (jest/nie ma). Trader nie wie jak mocny jest sygnał.

**Co zrobić:**
1. Wyświetlać confidence score (0-100%) przy każdym sygnale
2. Możliwość filtrowania sygnałów po confidence
3. Historyczna skuteczność per confidence level

**Wartość dla tradera:** Może ignorować słabe sygnały, skupić się na mocnych.

**AC:**
- [ ] Każdy sygnał ma pole confidence (0-100)
- [ ] Frontend filtruje po confidence >= X
- [ ] Historia pokazuje win rate per confidence bracket

---

#### W4: Strategy Templates - Ready to Use
**Status:** W TRAKCIE
**Obszary:** A1
**ROI:** 3.5

**Problem:** Trader musi sam tworzyć strategię, nie wie od czego zacząć.

**Co zrobić:**
1. 3 gotowe szablony: "Flash Pump", "Momentum Long", "Conservative"
2. Możliwość klonowania i modyfikacji
3. Dokumentacja każdego szablonu (kiedy działa, kiedy nie)

**Wartość dla tradera:** Może zacząć używać w 2 minuty zamiast godziny konfiguracji.

**AC:**
- [ ] 3 szablony dostępne w UI
- [ ] Klik "Use Template" tworzy kopię strategii
- [ ] Dokumentacja z expected win rate

---

### PRIORYTET P2: WAŻNE (ROI 2.0-3.0)

---

#### W5: Frontend Unit Tests
**Status:** DO WDROŻENIA
**Obszary:** A5
**ROI:** 2.8

**Problem:** Tylko 2 unit testy dla frontendu. Zmiany mogą łamać UI bez wykrycia.

**Co zrobić:**
1. Testy dla każdego komponentu w components/
2. Testy dla hooks i context
3. Coverage target: 70%

**Wartość dla tradera:** Stabilniejszy interfejs, mniej bugów w UI.

**AC:**
- [ ] Min 30 unit testów dla komponentów
- [ ] Coverage > 50%
- [ ] CI blokuje merge jeśli testy fail

---

#### W6: WebSocket Reconnection
**Status:** DO WDROŻENIA (KI2 z KNOWN_ISSUES)
**Obszary:** A5, A6
**ROI:** 2.7

**Problem:** Znany issue - frontend traci połączenie i nie odzyskuje automatycznie.

**Co zrobić:**
1. Implementacja exponential backoff reconnection
2. UI indicator "Reconnecting..."
3. Bufor wiadomości podczas reconnect

**Wartość dla tradera:** Nie musi odświeżać strony gdy internet ma chwilowe problemy.

**AC:**
- [ ] Automatyczny reconnect w < 30s
- [ ] UI pokazuje status połączenia
- [ ] Brak utraty danych podczas reconnect

---

#### W7: Backtest Results Visualization
**Status:** DO WDROŻENIA
**Obszary:** A2, A5
**ROI:** 2.6

**Problem:** Wyniki backestu to tylko liczby. Trader nie widzi equity curve, drawdown.

**Co zrobić:**
1. Wykres equity curve
2. Wykres drawdown
3. Zaznaczone wejścia/wyjścia na wykresie ceny

**Wartość dla tradera:** Lepsze zrozumienie jak strategia się zachowuje w czasie.

**AC:**
- [ ] Equity curve chart po backteście
- [ ] Max drawdown zaznaczony na wykresie
- [ ] Entry/exit markers na price chart

---

#### W8: Memory Leak Fix
**Status:** DO WDROŻENIA (KI3 z KNOWN_ISSUES)
**Obszary:** A6
**ROI:** 2.5

**Problem:** Znany issue - backend zużywa coraz więcej RAM przy >24h pracy.

**Co zrobić:**
1. Audyt wszystkich dict/list które rosną
2. Implementacja TTL dla cache
3. Monitoring memory usage

**Wartość dla tradera:** System stabilny 24/7 bez restartów.

**AC:**
- [ ] Memory usage stable po 24h testu
- [ ] Żaden cache nie rośnie bez limitu
- [ ] Alert gdy memory > 80%

---

#### W9: Pump Detection Improvements
**Status:** DO WDROŻENIA (I1 z IDEAS)
**Obszary:** A3, A4
**ROI:** 2.4

**Problem:** PRICE_VELOCITY jest podstawowy, za dużo fałszywych alarmów.

**Co zrobić:**
1. Volume anomaly detection (nagły skok wolumenu)
2. Bid/Ask imbalance indicator
3. Kombinacja wielu wskaźników dla wyższego confidence

**Wartość dla tradera:** Wcześniejsze wykrycie pump, mniej fałszywych alarmów.

**AC:**
- [ ] VOLUME_SURGE aktywny w strategiach
- [ ] Confidence wzrasta gdy wiele wskaźników zgodnych
- [ ] False positive rate < 30%

---

#### W10: Documentation Cleanup
**Status:** W TRAKCIE
**Obszary:** Wszystkie
**ROI:** 2.3

**Problem:** 100+ plików MD, wiele przestarzałych, trudno znaleźć aktualne info.

**Co zrobić:**
1. Przenieść wszystko obsolete do _archive
2. Jeden INDEX.md z linkami do aktualnych docs
3. Usunąć duplikaty

**Wartość dla tradera:** Szybsze znalezienie pomocy.

**AC:**
- [ ] Max 20 aktywnych plików MD w docs/
- [ ] INDEX.md z pełnym spisem treści
- [ ] Brak duplikatów informacji

---

### PRIORYTET P3: NICE TO HAVE (ROI 1.0-2.0)

---

#### W11: Alerting/Notifications
**Status:** DO WDROŻENIA (I2 z IDEAS)
**Obszary:** A4, A5
**ROI:** 1.9

**Problem:** Trader musi patrzeć na ekran żeby zobaczyć sygnał.

**Co zrobić:**
1. Sound alerts w przeglądarce
2. Browser notifications
3. Opcjonalnie: Telegram/Discord webhook

**Wartość dla tradera:** Nie przegapi okazji.

**AC:**
- [ ] Sound alert gdy nowy sygnał
- [ ] Browser notification z permission request
- [ ] Ustawienia włącz/wyłącz

---

#### W12: Risk Management UI
**Status:** W TRAKCIE
**Obszary:** A5
**ROI:** 1.8

**Problem:** Risk controls istnieją w backendzie ale UI jest minimalne.

**Co zrobić:**
1. Panel ustawień: max position size, max daily loss
2. Wizualizacja current exposure
3. Alert gdy zbliżamy się do limitów

**Wartość dla tradera:** Kontrola ryzyka bez edycji configów.

**AC:**
- [ ] UI dla max_position_size
- [ ] Wskaźnik current_exposure / max_exposure
- [ ] Alert przy 80% limitu

---

#### W13: Multi-Symbol Backtest
**Status:** W TRAKCIE
**Obszary:** A2
**ROI:** 1.7

**Problem:** Backtest dla jednego symbolu na raz, trudno porównać strategie.

**Co zrobić:**
1. Wybór wielu symboli do backtestu
2. Agregowane metryki (portfolio view)
3. Porównanie wyników per symbol

**Wartość dla tradera:** Testowanie strategii na całym portfolio.

**AC:**
- [ ] Wybór 3+ symboli w UI
- [ ] Agregowany Sharpe ratio
- [ ] Tabela porównawcza per symbol

---

#### W14: API Rate Limiting Polish
**Status:** WDROŻONE
**Obszary:** A6
**ROI:** 1.6

**Problem:** Rate limiting działa ale brak UI feedback.

**Co zrobić:**
1. Header z pozostałymi requestami
2. UI info gdy zbliżamy się do limitu
3. Graceful handling 429

**Wartość dla tradera:** Wie dlaczego request failed.

**AC:**
- [ ] X-RateLimit-Remaining header
- [ ] UI warning przy < 10 requests
- [ ] Retry-After handling

---

#### W15: Performance Metrics Export
**Status:** DO WDROŻENIA
**Obszary:** A2
**ROI:** 1.5

**Problem:** Wyniki backtestu tylko w UI, nie można eksportować.

**Co zrobić:**
1. Export do CSV
2. Export do JSON
3. Podstawowe statystyki w raporcie

**Wartość dla tradera:** Analiza wyników w Excel, porównanie strategii offline.

**AC:**
- [ ] Button "Export CSV" po backteście
- [ ] Plik zawiera wszystkie trades + metryki
- [ ] Suma P&L zgadza się z UI

---

### PRIORYTET P4: PRZYSZŁOŚĆ (ROI < 1.0)

---

#### W16: Multi-Exchange Support
**Status:** ODRZUCONE (na teraz)
**Obszary:** A6, A7
**ROI:** 0.9

**Problem:** Tylko MEXC. Trader nie może używać Binance, Bybit.

**Dlaczego odrzucone:** Złożoność wysoka (różne API), MEXC wystarczy dla MVP.

**Może wrócić gdy:** MEXC ma problemy lub trader wymaga arbitrażu.

---

#### W17: Machine Learning Signals
**Status:** ODRZUCONE
**Obszary:** A3, A4
**ROI:** 0.6

**Problem:** Wskaźniki rule-based mogą nie wyłapać wszystkich patternów.

**Dlaczego odrzucone:** Ryzyko overfitting, trudne do wyjaśnienia, wymaga dużo danych.

**Może wrócić gdy:** Podstawowe wskaźniki okażą się niewystarczające.

---

#### W18: Mobile App
**Status:** ODRZUCONE
**Obszary:** A5
**ROI:** 0.5

**Problem:** Brak dostępu mobilnego.

**Dlaczego odrzucone:** Web app jest responsywny, native app to duży nakład.

**Może wrócić gdy:** Jest stabilna baza użytkowników z zapotrzebowaniem.

---

#### W19: Social/Copy Trading
**Status:** ODRZUCONE
**Obszary:** A1, A5
**ROI:** 0.4

**Problem:** Trader nie może kopiować strategii innych.

**Dlaczego odrzucone:** Wymaga user management, leaderboard, model biznesowy.

**Może wrócić gdy:** Produkt ma stabilną bazę użytkowników.

---

#### W20: Blockchain Integration
**Status:** ODRZUCONE
**Obszary:** A6
**ROI:** 0.3

**Problem:** Brak DEX trading.

**Dlaczego odrzucone:** CEX (MEXC) wystarczy, DEX komplikuje architekturę.

**Może wrócić gdy:** CEX stracą popularność.

---

## PODSUMOWANIE KATEGORYZACJI

| Status | Ilość | Obszary |
|--------|-------|---------|
| **DO WDROŻENIA** | 10 | W1, W2, W3, W5, W6, W7, W8, W9, W11, W15 |
| **W TRAKCIE** | 5 | W4, W10, W12, W13, W14 |
| **WDROŻONE** | 0 | - |
| **ODRZUCONE** | 5 | W16, W17, W18, W19, W20 |

---

## KOLEJNOŚĆ REALIZACJI (WORKFLOW)

Na podstawie ROI i zależności:

### Sprint 17 (Natychmiast)
1. **W1** - E2E Test Flow (ROI 4.5) - weryfikacja że system działa
2. **W2** - Observability Dashboard (ROI 4.0) - trader widzi status

### Sprint 18
3. **W3** - Confidence Score (ROI 3.8) - lepsze sygnały
4. **W4** - Strategy Templates (ROI 3.5) - szybki start

### Sprint 19
5. **W6** - WebSocket Reconnection (ROI 2.7) - stabilność
6. **W8** - Memory Leak Fix (ROI 2.5) - 24/7 uptime

### Sprint 20
7. **W5** - Frontend Unit Tests (ROI 2.8) - jakość
8. **W7** - Backtest Visualization (ROI 2.6) - analiza

### Dalej
9-15. Pozostałe P2 i P3 według dostępności czasu

---

## MATRYCA ZALEŻNOŚCI

```
W1 (E2E Test) ─────┐
                   ├──→ Wymaga działającego A1, A2, A4
W4 (Templates) ────┘

W2 (Observability) ─→ Niezależny, można robić równolegle

W3 (Confidence) ───→ Zależy od A4 (pump_detector.py)

W5 (Frontend Tests) ─→ Niezależny

W6 (WebSocket) ────→ Zależy od A5, A6

W7 (Visualization) ─→ Zależy od W1 (dane z backtestu)

W8 (Memory) ───────→ Wymaga analizy A6
```

---

## WERYFIKACJA POSTĘPU

Po każdym sprincie sprawdź:

1. **Metryki się poprawiły?** Szczególnie OB (Observability)
2. **WGP wzrosło?** Cel: 72% → 80%
3. **Trader może używać?** Test z perspektywy użytkownika
4. **Testy przechodzą?** Zero regresji

---

*Dokument utworzony zgodnie z WORKFLOW.md v3.0*
*Następna aktualizacja: po Sprint 17*
