# Claude Code Instructions

**Single source of truth for Claude Code in this repository.**

## Project Identity

**What**: Cryptocurrency Trading System (Real-time + Backtesting)
**Stack**: Python FastAPI + Next.js 14 + QuestDB
**Architecture**: Layered + Event-Driven
**Goal**: Trader tworzy strategię → testuje → uruchamia → optymalizuje

## Agents

System używa wyspecjalizowanych agentów. Zobacz [.claude/agents/AGENTS.md](agents/AGENTS.md).
System postępje zgodnie z [Workflow](agents/WORKFLOW.md) i [Definition of Done](agents/DEFINITION_OF_DONE.md).

```
Driver (koordynator)
    ├── backend-dev     (Python/FastAPI)
    ├── frontend-dev    (Next.js/React)
    ├── database-dev    (QuestDB/SQL)
    ├── code-reviewer   (jakość kodu)
    └── trading-domain  (przydatność produktu dla tradera)
```

**Kluczowe zasady agentów:**
- Wykonawcy NIGDY nie ogłaszają sukcesu - tylko "wydaje się że działa, proszę o ocenę"
- Każde twierdzenie ma DOWÓD (output, test, curl)
- Driver podejmuje DECYZJE

## Quick Start

```powershell
# Full stack
.\start_all.ps1

# Backend only (port 8080)
python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8080

# Frontend only (port 3000)
cd frontend && npm run dev

# Testy
python run_tests.py
```

## Architecture

```
API Layer           → src/api/unified_server.py
Application Layer   → src/application/controllers/
Domain Layer        → src/domain/services/
Infrastructure      → src/infrastructure/
Core               → src/core/event_bus.py
```

**Zasady:**
- EventBus dla CAŁEJ komunikacji między komponentami
- Constructor injection ONLY (nie globalny Container)
- State Machine: IDLE → STARTING → RUNNING → STOPPING → STOPPED

## Where is X?

| What | Where |
|------|-------|
| API Server | `src/api/unified_server.py` |
| Strategy Manager | `src/domain/services/strategy_manager.py` |
| Risk Manager | `src/domain/services/risk_manager.py` |
| Indicator Engine | `src/domain/services/streaming_indicator_engine.py` |
| Event Bus | `src/core/event_bus.py` |
| Container (DI) | `src/infrastructure/container.py` |
| MEXC Adapter | `src/infrastructure/adapters/mexc_adapter.py` |

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

## Database (QuestDB)

- Web UI: http://localhost:9000
- PostgreSQL: localhost:8812
- ILP writes: localhost:9009

```sql
-- Najnowsze wartości
SELECT * FROM indicators WHERE symbol = 'BTC_USDT' LATEST BY symbol, indicator_id;
```

## Documentation

- **Workflow**: [agents/WORKFLOW.md](agents/WORKFLOW.md)
- **Definition of Done**: [agents/DEFINITION_OF_DONE.md](agents/DEFINITION_OF_DONE.md)
- **Agents**: [agents/AGENTS.md](agents/AGENTS.md)
- **Full docs**: `docs/INDEX.md`

---

**Last Updated**: 2025-12-03
