# Claude Code Instructions

**Single source of truth for Claude Code in this repository.**

---

## Project Identity

| Aspekt | Wartość |
|--------|---------|
| **What** | Cryptocurrency Trading System (Real-time + Backtesting) |
| **Stack** | Python FastAPI + Next.js 14 + QuestDB |
| **Architecture** | Layered + Event-Driven |
| **Goal** | Trader tworzy strategię → testuje → uruchamia → optymalizuje |

---

## Quick Start

### Uruchomienie wszystkich usług

```powershell
# Windows PowerShell
.\start_all.ps1

# Linux/Mac
./start_all.sh
```

Uruchamia:
- Backend API (port 8080)
- Frontend UI (port 3000)
- QuestDB (porty 9000, 8812, 9009)

### Uruchomienie pojedynczych usług

```bash
# Backend only (port 8080)
python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8080

# Frontend only (port 3000)
cd frontend && npm run dev

# QuestDB (jeśli nie uruchomiony przez start_all)
python database/questdb/install_questdb.py
```

### Restart/Refresh backendu

```bash
# Ctrl+C w terminalu z backendem, potem:
python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8080

# Lub z auto-reload:
python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8080 --reload
```

---

## Testy

```bash
# Wszystkie testy
python run_tests.py

# Tylko API testy
python run_tests.py --api

# Pojedynczy plik
pytest tests/test_strategy.py -v

# Z coverage
pytest --cov=src tests/
```

---

## URLs i Porty

| Usługa | URL | Opis |
|--------|-----|------|
| Frontend | http://localhost:3000 | UI dla tradera |
| Backend API | http://localhost:8080 | REST API |
| Backend Health | http://localhost:8080/health | Health check |
| API Docs | http://localhost:8080/docs | Swagger UI |
| QuestDB UI | http://localhost:9000 | Web UI bazy danych |
| QuestDB PostgreSQL | localhost:8812 | PostgreSQL protocol |
| QuestDB ILP | localhost:9009 | Fast writes |

### Health Checks

```bash
# Backend
curl http://localhost:8080/health
# Oczekiwany: {"status": "healthy"}

# Frontend
curl http://localhost:3000
# Oczekiwany: HTML
```

---

## Where is X?

### Backend (Python)

| Co | Gdzie |
|----|-------|
| API Server | `src/api/unified_server.py` |
| Strategy Manager | `src/domain/services/strategy_manager.py` |
| Risk Manager | `src/domain/services/risk_manager.py` |
| Indicator Engine | `src/domain/services/streaming_indicator_engine.py` |
| Event Bus | `src/core/event_bus.py` |
| Container (DI) | `src/infrastructure/container.py` |
| MEXC Adapter | `src/infrastructure/adapters/mexc_adapter.py` |
| Paper Trading | `src/trading/paper_trading_engine.py` |

### Frontend (Next.js)

| Co | Gdzie |
|----|-------|
| App Router | `frontend/src/app/` |
| Components | `frontend/src/components/` |
| API calls | `frontend/src/lib/api.ts` |
| Dashboard | `frontend/src/app/page.tsx` |

### Database (QuestDB)

| Co | Gdzie |
|----|-------|
| QuestDB Provider | `src/data_feed/questdb_provider.py` |
| Data Collection | `src/data/data_collection_persistence_service.py` |
| Strategy Storage | `src/domain/services/strategy_storage.py` |

---

## Architecture Layers

```
API Layer           → src/api/unified_server.py
Application Layer   → src/application/controllers/
Domain Layer        → src/domain/services/
Infrastructure      → src/infrastructure/
Core               → src/core/event_bus.py
```

### Zasady architektury

```python
# TAK - EventBus dla CAŁEJ komunikacji między komponentami
await event_bus.publish("signal_generated", data)

# TAK - Constructor injection ONLY
def __init__(self, db: IDatabase):
    self.db = db

# NIE - Globalny Container
from container import container  # ZAKAZANE

# NIE - Przeskakiwanie stanów
controller.state = RUNNING  # ZAKAZANE (użyj start())
```

---

## Agents

System używa wyspecjalizowanych agentów. Zobacz:

- **[agents/AGENTS.md](agents/AGENTS.md)** - **GŁÓWNY DOKUMENT** z pełnym workflow
- [agents/driver.md](agents/driver.md) - Koordynator projektu
- [agents/backend-dev.md](agents/backend-dev.md) - Backend Python/FastAPI
- [agents/frontend-dev.md](agents/frontend-dev.md) - Frontend Next.js/React
- [agents/database-dev.md](agents/database-dev.md) - QuestDB/SQL
- [agents/trading-domain.md](agents/trading-domain.md) - Ekspert tradingowy
- [agents/code-reviewer.md](agents/code-reviewer.md) - Jakość kodu

### Kluczowe zasady agentów

```
NIGDY nie ogłaszaj sukcesu bez obiektywnych testów.
Raportuj "wydaje się że działa" + DOWODY + GAP ANALYSIS.
Driver DECYDUJE o akceptacji.
Pracuj w CIĄGŁEJ PĘTLI do jawnego polecenia użytkownika.
```

---

## Definition of Done

Szczegółowe metryki i kryteria sukcesu znajdują się w:

**[DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md)**

### Skrót - kiedy zadanie jest DONE:

```
[ ] Wszystkie testy przechodzą (100% GREEN)
[ ] Brak nowych błędów w logach
[ ] Dowody działania załączone (output, screenshot)
[ ] Brak regresji
[ ] GAP ANALYSIS wykonana
[ ] Następny priorytet zidentyfikowany
```

---

## Documentation

| Dokument | Opis |
|----------|------|
| [agents/AGENTS.md](agents/AGENTS.md) | Workflow i proces pracy agentów |
| [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) | Cele i metryki sukcesu |
| `docs/INDEX.md` | Pełna dokumentacja projektu |

---

## Anti-patterns

```python
# NIE - globalny Container
from container import container
db = container.get("database")

# TAK - constructor injection
def __init__(self, db: IDatabase):
    self.db = db

# NIE - defaultdict (memory leak)
self.cache = defaultdict(list)

# TAK - bounded
self.cache: Dict = {}
MAX_SIZE = 1000
```

---

## Troubleshooting

### Backend nie startuje

```bash
# Sprawdź czy port zajęty
netstat -an | grep 8080

# Sprawdź logi
python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8080 2>&1 | head -50

# Sprawdź zależności
pip install -r requirements.txt
```

### Frontend nie startuje

```bash
# Sprawdź czy port zajęty
netstat -an | grep 3000

# Zainstaluj zależności
cd frontend && npm install

# Sprawdź logi
npm run dev 2>&1 | head -50
```

### QuestDB nie działa

```bash
# Sprawdź porty
netstat -an | grep "9000\|8812\|9009"

# Restart
python database/questdb/install_questdb.py
```

---

**Last Updated**: 2025-12-04
