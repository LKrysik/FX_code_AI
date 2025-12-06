# UI BACKLOG - FXcrypto Pump/Dump Detection

**Wersja:** 2.0 | **Data:** 2025-12-06

**Cel systemu:** Wykrywanie pump/dump i shortowanie na szczycie pumpu

**Powiązane dokumenty:**
- `docs/UI_INTERFACE_SPECIFICATION.md` - Pełny opis interfejsu i architektury systemu

---

## JAK UŻYWAĆ TEGO DOKUMENTU

### Dla Driver/frontend-dev:
1. Wybierz zadanie z najwyższym priorytetem (CRITICAL → HIGH → MEDIUM → LOW)
2. Zaimplementuj funkcję
3. Zaktualizuj status na `DONE` i dodaj datę
4. Zaktualizuj `UI_INTERFACE_SPECIFICATION.md` (usuń z sekcji "Braki")

### Kiedy aktualizować:
- Po implementacji funkcji → zmień status na DONE
- Po krytycznej ocenie UI → dodaj nowe pozycje
- Co kilka iteracji → przejrzyj priorytety

---

## LEGENDA PRIORYTETÓW

| Priorytet | Znaczenie |
|-----------|-----------|
| CRITICAL | Bez tego trader nie może wykrywać pump/dump i shortować |
| HIGH | Znacząco utrudnia konfigurację strategii lub monitoring |
| MEDIUM | Ułatwia pracę, ale można obejść |
| LOW | Nice to have |

---

## CRITICAL - BEZ TEGO NIE MOŻNA WYKRYWAĆ PUMP/DUMP

### WYKRES - Pump Detection Visualization

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| C-01 | Zoom wykresu | /dashboard | Scroll wheel lub przyciski +/- (widzieć szczegóły pumpu) | TODO |
| C-02 | Przewijanie wykresu | /dashboard | Drag w historię (analiza przeszłych pumpów) | TODO |
| C-03 | Wskaźniki pump na wykresie | /dashboard | PUMP_MAGNITUDE, VELOCITY, VOLUME_SURGE jako subplots | TODO |
| C-04 | Entry/SL/TP SHORT na wykresie | /dashboard | Poziome linie pokazujące SHORT pozycję | TODO |
| C-05 | Oznaczenia S1/Z1/ZE1 | /dashboard | Markery gdzie był pump(S1), peak(Z1), dump end(ZE1) | TODO |

### SHORT POZYCJA - Zarządzanie

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| C-06 | Panel SHORT pozycji | /dashboard | Entry peak, current price, P&L, SL powyżej, TP poniżej | TODO |
| C-07 | Emergency close | /dashboard | Szybkie zamknięcie gdy pump kontynuuje | TODO |
| C-08 | Modyfikacja SL/TP | /dashboard | Przesunięcie SL bliżej jeśli dump się rozwija | TODO |

### STRATEGY STATE - Real-time Monitoring

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| C-09 | State machine display | /dashboard | Aktualny stan: MONITORING/SIGNAL_DETECTED/POSITION_ACTIVE | TODO |
| C-10 | Condition status | /dashboard | Które warunki Z1 spełnione, które pending | TODO |
| C-11 | Panel szczegółów sygnału | /dashboard | Wartości wskaźników w momencie S1 | TODO |

### INDICATOR VARIANTS - Configuration

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| C-12 | Preview wariantu | /indicators | Wykres jak wariant reaguje na historyczne pumpy | TODO |

---

## HIGH - ZNACZĄCO UTRUDNIA KONFIGURACJĘ LUB MONITORING

### STRATEGY BUILDER - Pump Detection Config

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| H-01 | Wizualizacja "gdzie by był S1" | /strategy-builder | Zaznacz na wykresie gdzie strategia by wykryła pump | TODO |
| H-02 | State machine preview | /strategy-builder | Diagram S1→O1/Z1→ZE1/E1 z warunkami | TODO |
| H-03 | Quick backtest | /strategy-builder | Ile pumpów by wykryła, ile szczytów trafiła | TODO |
| H-04 | Opis wariantów w dropdown | /strategy-builder | "PumpFast" - pokaż tooltip z parametrami | TODO |

### INDICATOR VARIANTS - Tuning

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| H-05 | Porównanie wariantów | /indicators | Fast vs Medium na tym samym wykresie | TODO |
| H-06 | Opis parametrów | /indicators | Co robi t1, t3, d? Jaki efekt zmiany? | TODO |
| H-07 | Test "ile sygnałów" | /indicators | Ile S1 wygenerowałby wariant w 24h | TODO |

### DASHBOARD - Pump Monitoring

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| H-08 | Real-time pump indicators | /dashboard | PUMP_MAGNITUDE, VELOCITY jako duże liczby | TODO |
| H-09 | Velocity trend | /dashboard | Czy pump zwalnia czy przyspiesza (strzałka) | TODO |
| H-10 | Peak prediction | /dashboard | "Zbliża się szczyt" indicator | TODO |

### TRADING SESSION

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| H-11 | Podgląd strategii | /trading-session | Po zaznaczeniu - pokaż warunki S1, Z1, ZE1 | TODO |
| H-12 | Symbol recommendation | /trading-session | "SOL_USDT ma wysoki volume - dobry dla pump detection" | TODO |

### DATA COLLECTION

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| H-13 | Download danych | /data-collection | Eksport do CSV (analiza pumpów offline) | TODO |
| H-14 | Pump history in data | /data-collection | Oznacz gdzie były historyczne pumpy | TODO |

### MARKET SCANNER

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| H-13 | Mini-wykres w tabeli | /market-scanner | Sparkline przy każdym symbolu | TODO |

### SETTINGS

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| H-14 | Domyślne SL/TP | /settings | Ustawienia domyślnych wartości | TODO |

### NOWE STRONY

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| H-15 | Strona raportów | /reports | Win rate, avg win/loss, drawdown, calendar | TODO |

---

## MEDIUM - UŁATWIA PRACĘ

### DASHBOARD

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| M-01 | Historia przegapionych sygnałów | / | Sygnały z ostatnich 24h | TODO |

### TRADING SESSION

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| M-02 | Rekomendacja symboli | /trading-session | Na podstawie aktywnych sygnałów ze skanera | TODO |
| M-03 | Porównanie strategii | /trading-session | Statystyki win rate/profit dla każdej | TODO |

### STRATEGY BUILDER

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| M-04 | Złożone warunki | /strategy-builder | (A AND B) OR C | TODO |
| M-05 | Import/eksport strategii | /strategy-builder | JSON export/import | TODO |
| M-06 | Wersjonowanie strategii | /strategy-builder | Historia zmian, rollback | TODO |

### DATA COLLECTION

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| M-07 | Jakość danych | /data-collection | Wskaźnik luk w danych | TODO |

### INDICATORS

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| M-08 | Opis wskaźnika | /indicators | Dokumentacja co mierzy i jak interpretować | TODO |
| M-09 | Test wskaźnika | /indicators | Ile sygnałów wygenerował ostatnio | TODO |

### MARKET SCANNER

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| M-10 | Historia sygnału | /market-scanner | Co się działo z tym symbolem ostatnio | TODO |
| M-11 | Statystyki trafności | /market-scanner | % trafnych sygnałów STRONG/MEDIUM/WEAK | TODO |
| M-12 | Panel szczegółów | /market-scanner | Po kliknięciu wiersza - szczegóły | TODO |

### SETTINGS

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| M-13 | Klawisze skrótów | /settings | Konfiguracja keyboard shortcuts | TODO |
| M-14 | Profile | /settings | Różne profile dla różnych stylów tradingu | TODO |

---

## LOW - NICE TO HAVE

### DASHBOARD

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| L-01 | Fibonacci retracement | /dashboard | Drawing tool | TODO |
| L-02 | Rectangle zones | /dashboard | Drawing tool | TODO |

### TRADING SESSION

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| L-03 | Ostrzeżenie o konflikcie | /trading-session | 2 strategie na ten sam symbol | TODO |

### STRATEGY BUILDER

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| L-04 | Komentarze/notatki | /strategy-builder | Notatki przy warunkach | TODO |

### DATA COLLECTION

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| L-05 | Statystyki danych | /data-collection | Min/max/avg cena, volume | TODO |

### SETTINGS

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| L-06 | Backup/restore | /settings | Export/import wszystkich ustawień | TODO |
| L-07 | 2FA | /settings | Two-factor authentication | TODO |

---

## SYSTEMOWE - KEYBOARD SHORTCUTS

| Skrót | Funkcja | Status |
|-------|---------|--------|
| ESC | Emergency Stop All | TODO |
| C | Close current position | TODO |
| S | Toggle Scanner | TODO |
| D | Go to Dashboard | TODO |
| T | Go to Trading Session | TODO |
| 1-9 | Switch symbols in watchlist | TODO |
| +/- | Zoom chart | TODO |
| ←→ | Scroll chart | TODO |
| F | Full screen chart | TODO |

---

## STATYSTYKI BACKLOGU

| Priorytet | Liczba | Zrobione |
|-----------|--------|----------|
| CRITICAL | 8 | 0 |
| HIGH | 15 | 0 |
| MEDIUM | 14 | 0 |
| LOW | 7 | 0 |
| **RAZEM** | **44** | **0** |

---

## CHANGELOG

### v1.0 (2025-12-05)
- Początkowa wersja backlogu na podstawie krytycznej oceny UI
- 44 pozycje: 8 CRITICAL, 15 HIGH, 14 MEDIUM, 7 LOW
