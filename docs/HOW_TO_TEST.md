# Jak Testować Funkcjonalności

## Quick Start

```powershell
# 1. Uruchom środowisko
.\start_all.ps1

# 2. Sprawdź czy działa
curl http://localhost:8080/health
# Oczekiwane: {"status": "healthy"}

# 3. Uruchom testy automatyczne
python run_tests.py
```

## Testy Manualne

### Test 1: Strategy Builder generuje sygnały

**Cel:** Sprawdzić czy strategia wykrywa pump w danych syntetycznych

**Kroki:**
```powershell
# Uruchom test E2E
python scripts/test_strategy_builder_e2e.py
```

**Oczekiwany wynik:**
```
[PASS] Market data received
[PASS] Indicators calculated
[PASS] Signals generated
OVERALL: SUCCESS
```

**Co się dzieje:**
1. Tworzy strategię z niskimi progami (velocity_threshold=0.00001)
2. Generuje syntetyczne dane z wzorcem pump-and-dump
3. Sprawdza czy strategia wygenerowała sygnały

---

### Test 2: Backtest na prawdziwych danych

**Cel:** Sprawdzić czy backtest przetwarza dane z QuestDB

**Warunki wstępne:**
- QuestDB działa (http://localhost:9000)
- Istnieje sesja z danymi w tabeli `tick_prices`

**Kroki:**
1. Otwórz http://localhost:3000
2. Przejdź do "Sessions"
3. Wybierz sesję historyczną
4. Kliknij "Start Backtest"

**Oczekiwany wynik:**
- Status zmienia się: STARTING → RUNNING → COMPLETED
- W metrics widzisz: ticks_processed > 0

**Jak sprawdzić czy są dane:**
```sql
-- W QuestDB Web UI (http://localhost:9000)
SELECT count() FROM tick_prices;
SELECT DISTINCT session_id FROM tick_prices;
```

---

### Test 3: Data Collection

**Cel:** Sprawdzić czy system zbiera dane z MEXC

**Kroki:**
1. Otwórz http://localhost:3000
2. Przejdź do "Sessions"
3. Wybierz symbole (np. BTCUSDT)
4. Kliknij "Start Collection"

**Oczekiwany wynik:**
- Status: RUNNING
- W metrics: records_collected rośnie

**Weryfikacja:**
```sql
-- Po 1-2 minutach kolekcji
SELECT count() FROM tick_prices WHERE session_id = 'twoja_sesja';
```

---

### Test 4: Wskaźniki działają poprawnie

**Cel:** Sprawdzić czy wskaźniki liczą wartości

**Kroki:**
```powershell
# Test jednostkowy wskaźników
python -m pytest tests/test_indicators.py -v
```

**Lub test manualny przez API:**
```powershell
# Pobierz listę wskaźników
curl http://localhost:8080/api/indicators/variants
```

---

### Test 5: Frontend łączy się z backendem

**Cel:** Sprawdzić WebSocket connection

**Kroki:**
1. Otwórz http://localhost:3000
2. Otwórz DevTools (F12) → Network → WS
3. Powinieneś widzieć połączenie ws://localhost:8080/ws

**Problemy:**
- "Connection refused" → Backend nie działa
- "401 Unauthorized" → Problem z JWT (może być OK bez logowania)

---

## Testy Automatyczne

### Pełny zestaw testów
```powershell
python run_tests.py
```

### Tylko backend
```powershell
python run_tests.py --api
```

### Tylko frontend (Playwright)
```powershell
python run_tests.py --frontend
```

### Szybkie testy (bez integracyjnych)
```powershell
python run_tests.py --fast
```

---

## Typowe Problemy

### Problem: "signals_detected: 0" podczas backtestu

**Przyczyny:**
1. Progi w strategii za wysokie dla danych
2. Brak aktywnych strategii dla symbolu
3. Wskaźniki nie są zarejestrowane dla symbolu

**Diagnostyka:**
```powershell
# Sprawdź czy strategia jest aktywna
curl http://localhost:8080/api/strategies/active

# Sprawdź logi backendu
# (szukaj "signal_generated" lub "indicator.updated")
```

### Problem: "Connection refused" do backend

**Przyczyny:**
1. Backend nie uruchomiony
2. Port 8080 zajęty

**Diagnostyka:**
```powershell
netstat -an | findstr 8080
```

### Problem: Brak danych w QuestDB

**Przyczyny:**
1. QuestDB nie działa
2. Data collection nie zapisuje

**Diagnostyka:**
```sql
-- W QuestDB UI (http://localhost:9000)
SELECT count() FROM tick_prices;
```

---

## Weryfikacja Całego Flow

### Scenariusz: Od zera do sygnału

1. **Uruchom środowisko:** `.\start_all.ps1`
2. **Sprawdź health:** `curl http://localhost:8080/health`
3. **Utwórz strategię:** Frontend → Strategy Builder → Create
4. **Zbierz dane:** Frontend → Sessions → Start Collection (2-3 min)
5. **Uruchom backtest:** Frontend → Sessions → wybierz sesję → Start Backtest
6. **Sprawdź wyniki:** metrics.signals_detected > 0

Jeśli wszystko działa, system jest gotowy do użycia.
