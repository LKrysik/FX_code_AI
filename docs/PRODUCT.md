# FXcrypto - Pump & Dump Detection Platform

**Wersja:** 2.0 | **Data:** 2025-12-02

---

## CEL BIZNESOWY

Dostarczyć traderowi narzędzie do:

```
STWORZYĆ strategię → PRZETESTOWAĆ na historii → URUCHOMIĆ na żywo → ZOPTYMALIZOWAĆ
```

**Kluczowa zasada:** Buduję NARZĘDZIE, nie strategię. Trader sam optymalizuje parametry.

---

## GŁÓWNE FUNKCJONALNOŚCI

### 1. Strategy Builder (Kreator Strategii)

**Co to jest:** Wizualny kreator strategii tradingowych bez kodowania.

**5 sekcji warunków:**

| Sekcja | Nazwa | Cel | Przykład |
|--------|-------|-----|----------|
| **S1** | Signal Detection | Kiedy szukać okazji | `velocity > 0.001` |
| **O1** | Signal Cancellation | Kiedy anulować sygnał | `velocity < -0.002` |
| **Z1** | Entry Conditions | Kiedy wejść w pozycję | `velocity > 0` |
| **ZE1** | Close Order | Kiedy zamknąć z zyskiem | `profit > 2%` |
| **E1** | Emergency Exit | Stop-loss | `loss > 1%` |

**Typ strategii:** LONG (zakład na wzrost) lub SHORT (zakład na spadek)

---

### 2. Backtesting (Testowanie Historyczne)

**Co to jest:** Symulacja strategii na danych historycznych.

**Jak działa:**
1. Użytkownik wybiera sesję z danymi historycznymi
2. System odtwarza dane (np. 10x szybciej)
3. Wskaźniki liczą się w czasie rzeczywistym
4. Strategia generuje sygnały
5. Wyniki: P&L, win rate, drawdown

**Kluczowe metryki backtestingu:**
- Equity curve (zmiana kapitału w czasie)
- Max drawdown (największy spadek)
- Sharpe ratio (ryzyko vs zysk)
- Win rate (% zyskownych)

---

### 3. Data Collection (Zbieranie Danych)

**Co to jest:** Nagrywanie danych rynkowych do backtestingu.

**Jak działa:**
1. Start sesji dla wybranych symboli
2. WebSocket do MEXC (giełda)
3. Zapis ticków (cena, wolumen, timestamp) do QuestDB
4. Sesja może trwać minuty → dni

---

### 4. Live/Paper Trading

**Paper Trading:** Symulacja z wirtualnymi pieniędzmi
- Testowanie strategii bez ryzyka
- Real-time sygnały

**Live Trading:** Prawdziwe transakcje
- Połączenie z MEXC Futures API
- Sygnał → Risk check → Zlecenie
- Monitorowanie pozycji

---

### 5. Wskaźniki Techniczne

**Zaimplementowane (17):**

| Wskaźnik | Opis | Użycie |
|----------|------|--------|
| PRICE_VELOCITY | Szybkość zmiany ceny | Wykrywanie pump |
| VOLUME_SURGE | Anomalie wolumenu | Potwierdzenie pump |
| TWPA | Time-Weighted Price Average | Trend |
| TWPA_RATIO | Stosunek ceny do TWPA | Odchylenie |
| PUMP_MAGNITUDE_PCT | Wielkość pump w % | Siła ruchu |
| VELOCITY_CASCADE | Kaskadowy wzrost velocity | Momentum |
| BID_ASK_IMBALANCE | Nierównowaga bid/ask | Presja kupna/sprzedaży |
| EMA, SMA, VWAP, RSI | Klasyczne wskaźniki | Analiza techniczna |
| Bollinger Bands | Wstęgi zmienności | Breakout |

**Parametry czasowe:**
- `t1` = okno główne (np. 300s = 5 min)
- `t2` = okno porównawcze (np. 0 = teraz)

---

## ARCHITEKTURA

```
┌─────────────────┐     ┌──────────────────────────────────────┐
│   Frontend      │     │            Backend (FastAPI)         │
│   (Next.js)     │◄───►│                                      │
│   Port: 3000    │ WS  │  ┌─────────────────────────────────┐ │
└─────────────────┘ REST│  │  StreamingIndicatorEngine       │ │
                        │  │  (oblicza wskaźniki real-time)  │ │
                        │  └─────────────┬───────────────────┘ │
                        │                │                     │
                        │  ┌─────────────▼───────────────────┐ │
                        │  │  StrategyManager                │ │
                        │  │  (ewaluuje warunki S1/Z1/etc)   │ │
                        │  └─────────────┬───────────────────┘ │
                        │                │                     │
                        │  ┌─────────────▼───────────────────┐ │
                        │  │  RiskManager → OrderManager     │ │
                        │  │  (sprawdza ryzyko, składa zlec.)│ │
                        │  └─────────────┬───────────────────┘ │
                        │                │         Port: 8080  │
                        └────────────────┼─────────────────────┘
                                         │
                        ┌────────────────▼─────────────────────┐
                        │           QuestDB                    │
                        │   (baza danych time-series)          │
                        │   Ports: 9000 (UI), 8812 (SQL)       │
                        └──────────────────────────────────────┘
```

---

## JAK URUCHOMIĆ

### Wszystko naraz:
```powershell
.\start_all.ps1
```

### Ręcznie:

```powershell
# 1. Aktywuj środowisko Python
& C:\Users\lukasz.krysik\Desktop\FXcrypto\FX_code_AI_v2\.venv\Scripts\Activate.ps1

# 2. Backend (Terminal 1)
python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8080

# 3. Frontend (Terminal 2)
cd frontend && npm run dev

# QuestDB musi być uruchomiony osobno
```

### URLs:

| Usługa | URL | Opis |
|--------|-----|------|
| Frontend | http://localhost:3000 | UI dla tradera |
| Backend API | http://localhost:8080 | REST + WebSocket |
| Backend Health | http://localhost:8080/health | Status backendu |
| QuestDB UI | http://localhost:9000 | Podgląd bazy danych |

---

## STRUKTURA PROJEKTU

```
src/
├── api/                    # REST + WebSocket (FastAPI)
├── application/controllers # Orchestracja
├── domain/services/        # Logika biznesowa
│   ├── strategy_manager.py
│   ├── risk_manager.py
│   └── streaming_indicator_engine/
├── infrastructure/         # Adaptery, baza danych
│   ├── adapters/mexc_*
│   └── container.py
└── core/                   # EventBus, Logger, Config

frontend/                   # Next.js 14

docs/
├── DEFINITION_OF_DONE.md   # Cele i metryki sukcesu
├── PRODUCT.md              # Ten dokument
├── KNOWN_ISSUES.md         # Znane problemy
└── HOW_TO_TEST.md          # Jak testować
```

---

## POWIĄZANE DOKUMENTY

| Dokument | Zawartość |
|----------|-----------|
| [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) | Cele, metryki, "Trader Journey" |
| [../WORKFLOW.md](../WORKFLOW.md) | Proces pracy agenta AI |
| [KNOWN_ISSUES.md](KNOWN_ISSUES.md) | Znane problemy i workaroundy |
| [HOW_TO_TEST.md](HOW_TO_TEST.md) | Jak testować system |

---

*Ten dokument opisuje CO to jest. Jak mierzyć sukces: [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md)*
