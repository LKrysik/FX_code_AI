# UI BACKLOG - FXcrypto

**Wersja:** 1.0 | **Data:** 2025-12-05

**Powiązane dokumenty:**
- `docs/UI_INTERFACE_SPECIFICATION.md` - Pełny opis interfejsu

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
| CRITICAL | Bez tego trader nie może handlować - blokuje core flow |
| HIGH | Znacząco utrudnia pracę tradera |
| MEDIUM | Ułatwia pracę, ale można obejść |
| LOW | Nice to have |

---

## CRITICAL - BEZ TEGO NIE MOŻNA HANDLOWAĆ

### WYKRES - Interaktywność

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| C-01 | Zoom wykresu | /dashboard | Scroll wheel lub przyciski +/- | TODO |
| C-02 | Przewijanie wykresu | /dashboard | Drag lub scroll w historię | TODO |
| C-03 | Wskaźniki na wykresie | /dashboard | RSI/MACD jako subplot pod wykresem | TODO |
| C-04 | Entry/SL/TP na wykresie | /dashboard | Poziome linie pokazujące pozycję | TODO |

### POZYCJE - Zarządzanie

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| C-05 | Panel pozycji | /dashboard | Szczegóły otwartej pozycji (entry, P&L, size) | TODO |
| C-06 | Zamknięcie pozycji | /dashboard | Przyciski Close 100%, Close 50% | TODO |
| C-07 | Modyfikacja SL/TP | /dashboard | Edycja stop loss / take profit w locie | TODO |

### SYGNAŁY - Szczegóły

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| C-08 | Panel szczegółów sygnału | /dashboard | Po kliknięciu [Details] - panel boczny ze szczegółami | TODO |

---

## HIGH - ZNACZĄCO UTRUDNIA PRACĘ

### DASHBOARD

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| H-01 | Mini-wykres przy symbolu | / | Sparkline w Market Scanner | TODO |
| H-02 | Szczegóły aktywnych pozycji | / | Lista pozycji z P&L w Risk Panel | TODO |
| H-03 | Stan konta z giełdy | / | Rzeczywiste saldo USDT z MEXC | TODO |
| H-04 | Rysowanie linii | /dashboard | Trend line, horizontal line | TODO |
| H-05 | Orderbook | /dashboard | Głębokość rynku (bids/asks) | TODO |
| H-06 | Trade tape | /dashboard | Ostatnie transakcje na rynku | TODO |
| H-07 | Multi-timeframe | /dashboard | Przełącznik 1m/5m/15m/1h/4h/1d | TODO |

### TRADING SESSION

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| H-08 | Podgląd strategii | /trading-session | Po zaznaczeniu strategii - pokaż jej warunki | TODO |

### STRATEGY BUILDER

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| H-09 | Wizualizacja warunków | /strategy-builder | Pokaż na wykresie gdzie warunek był spełniony | TODO |
| H-10 | Quick backtest preview | /strategy-builder | Mini-backtest na 100 świecach | TODO |

### DATA COLLECTION

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| H-11 | Download danych | /data-collection | Eksport do CSV | TODO |

### INDICATORS

| ID | Funkcja | Strona | Opis | Status |
|----|---------|--------|------|--------|
| H-12 | Wizualizacja wskaźnika | /indicators | Wykres pokazujący wartości wskaźnika | TODO |

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
