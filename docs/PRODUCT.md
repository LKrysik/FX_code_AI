# FXcrypto - Pump & Dump Detection Platform

## Cel Biznesowy

Dostarczyć traderom kryptowalut narzędzie do:
- **Wykrywania pump & dump** zanim inni uczestnicy rynku
- **Automatyzacji decyzji tradingowych** na podstawie zdefiniowanych strategii
- **Backtestowania strategii** na danych historycznych przed użyciem na żywo

## Kluczowe Funkcjonalności

### 1. Strategy Builder (Kreator Strategii)

**Co to jest:** Wizualny kreator strategii tradingowych bez kodowania.

**Jak działa:**
- Użytkownik definiuje 5 sekcji warunków:
  - **S1 (Signal Detection)** - kiedy szukać okazji (np. "velocity > 0.001")
  - **O1 (Signal Cancellation)** - kiedy anulować sygnał (np. "velocity < -0.002")
  - **Z1 (Entry Conditions)** - kiedy wejść w pozycję (np. "velocity > 0")
  - **ZE1 (Close Order)** - kiedy zamknąć pozycję z zyskiem
  - **E1 (Emergency Exit)** - kiedy uciekać (stop-loss)
- Warunki używają wskaźników technicznych (price_velocity, volume_surge, itp.)
- Strategia może być LONG (zakład na wzrost) lub SHORT (zakład na spadek)

**Stan aktualny:**
- Backend: działa, generuje sygnały podczas backtestów
- Frontend: formularz tworzenia strategii działa
- Testowane: scripts/test_strategy_builder_e2e.py (PASS)

### 2. Backtesting (Testowanie Historyczne)

**Co to jest:** Symulacja strategii na danych historycznych.

**Jak działa:**
- Użytkownik wybiera sesję z zebranymi danymi historycznymi
- System "odtwarza" dane z zadaną prędkością (np. 10x szybciej)
- Wskaźniki liczą się w czasie rzeczywistym
- Strategia generuje sygnały jak na żywo
- Wyniki pokazują: ile sygnałów, ile zyskownych, drawdown, itp.

**Stan aktualny:**
- Backend: działa, przetwarza ticki, liczy wskaźniki, generuje sygnały
- Frontend: panel backtestingu działa, pokazuje wyniki
- Problem: czasem brak sygnałów gdy progi są za wysokie

### 3. Data Collection (Zbieranie Danych)

**Co to jest:** Nagrywanie danych rynkowych do późniejszego backtestingu.

**Jak działa:**
- Użytkownik startuje sesję zbierania danych dla wybranych symboli
- System łączy się z MEXC (giełda) przez WebSocket
- Zapisuje ticki (cena, wolumen, timestamp) do bazy QuestDB
- Sesja może trwać minuty, godziny lub dni

**Stan aktualny:**
- Backend: działa, zapisuje do QuestDB
- Frontend: panel session management działa

### 4. Live Trading (Trading na Żywo)

**Co to jest:** Automatyczne wykonywanie transakcji na giełdzie.

**Jak działa:**
- Połączenie z MEXC Futures API
- Strategia generuje sygnał → system sprawdza ryzyko → składa zlecenie
- Monitorowanie otwartych pozycji

**Stan aktualny:**
- Paper trading (symulowany): działa
- Real trading: adapter gotowy, wymaga kluczy API

### 5. Wskaźniki Techniczne

**Zaimplementowane:**
- **PRICE_VELOCITY** - szybkość zmiany ceny (najważniejszy dla pump detection)
- **TWPA** - Time-Weighted Price Average
- **VWAP** - Volume-Weighted Average Price
- **VOLUME_SURGE** - anomalie wolumenu
- I inne (12 algorytmów w sumie)

**Jak używać:**
- Każdy wskaźnik ma parametry (np. t1=300, t3=30 sekundy)
- Strategia porównuje wartość wskaźnika z progiem (np. velocity > 0.001)

## Architektura (uproszczona)

```
Frontend (Next.js)  ←WebSocket/REST→  Backend (FastAPI)
                                            ↓
                                    StreamingIndicatorEngine
                                            ↓
                                    StrategyManager
                                            ↓
                                    RiskManager → OrderManager
                                            ↓
                                    QuestDB (baza danych)
```

## Jak Uruchomić

```powershell
# Wszystko naraz:
.\start_all.ps1

# Lub ręcznie:
# Terminal 1 - Backend:
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080

# Terminal 2 - Frontend:
cd frontend && npm run dev

# QuestDB powinien być uruchomiony
```

**URL:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8080
- Backend Health: http://localhost:8080/health
- QuestDB UI: http://localhost:9000

## Jak Testować

Zobacz: [HOW_TO_TEST.md](HOW_TO_TEST.md)
