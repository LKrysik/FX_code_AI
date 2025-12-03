# System Agentów - FXcrypto

## Struktura

```
Driver (inicjuje, decyduje)
    │
    ├── trading-domain (ocenia z perspektywy tradera)
    │
    ├── backend-dev    (Python/FastAPI, B1-B8)
    ├── frontend-dev   (Next.js/React, F1-F9)
    ├── database-dev   (QuestDB, D1-D3)
    └── code-reviewer  (jakość kodu)
```

---

## Przepływ pracy

```
1. Driver sprawdza metryki (DEFINITION_OF_DONE.md)
2. Driver wybiera cel według algorytmu priorytetów
3. Driver zleca zadanie odpowiedniemu agentowi
4. Agent wykonuje i raportuje z dowodami
5. Driver ocenia, aktualizuje metryki
6. Driver szuka następnego problemu → GOTO 1
```

---

## Przepływ informacji

### Wykonawcy → Driver

```
RAPORT: [zadanie]
- Status: "wydaje się że działa"
- Dowody: [output, testy, curl]
- Ryzyka: [lista]
- Propozycje: [kolejne kroki]
- Pytania: [decyzje]
```

### Trading-domain → Driver

```
OCENA: [funkcja]
- Perspektywa tradera: [co działa/nie]
- Priorytet: [P0/P1/P2]
- Rekomendacje: [co naprawić]
```

### Driver → Agenci

```
ZADANIE dla @[agent]: [nazwa]
- AC1: [kryterium]
- AC2: [kryterium]
- Pliki: [lista]
```

---

## MOTOR DZIAŁANIA (każdy agent)

| Agent | Motor |
|-------|-------|
| **Driver** | Nie czeka → inicjuje. Metryki spadają → działa. |
| **backend-dev** | Widzi bug → naprawia. TODO → zgłasza. |
| **frontend-dev** | Problem UX → naprawia. Myśli jak trader. |
| **database-dev** | Slow query → optymalizuje. Myśli o skali. |
| **trading-domain** | Nic nie jest "dobre" → szuka problemów. |
| **code-reviewer** | Widzi ryzyko → blokuje. |

---

## Środowisko (wspólne)

```powershell
# Full stack
.\start_all.ps1

# Backend
python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8080

# Frontend
cd frontend && npm run dev

# Testy
python run_tests.py
```

### URLs

- Backend: http://localhost:8080
- Frontend: http://localhost:3000
- QuestDB: http://localhost:9000

---

## Metryki (z DEFINITION_OF_DONE.md)

| Warstwa | Średnia | Najsłabszy |
|---------|---------|------------|
| Backend | 7.4/10 | B7: Session (5.8) |
| Frontend | 5.4/10 | F4: Live Trading (4.3) |
| Database | 7.4/10 | D3: Storage (5.8) |

---

## Znane problemy

| ID | Problem | Priorytet | Agent |
|----|---------|-----------|-------|
| PH1 | max_drawdown = 0.0 | P0 | backend-dev |
| PH2 | sharpe_ratio = None | P1 | backend-dev |
| KI2 | WebSocket reconnection | P1 | backend-dev |
| TODO2 | Realized PnL placeholder | P1 | backend-dev |

---

## Pliki agentów

- [driver.md](driver.md) - Koordynator
- [trading-domain.md](trading-domain.md) - Ekspert tradingowy
- [backend-dev.md](backend-dev.md) - Python/FastAPI
- [frontend-dev.md](frontend-dev.md) - Next.js/React
- [database-dev.md](database-dev.md) - QuestDB
- [code-reviewer.md](code-reviewer.md) - Jakość kodu

---

## Dokumenty referencyjne

- [WORKFLOW.md](WORKFLOW.md) - Proces pracy
- [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) - Metryki i cele

---

## Zasady

1. **Driver inicjuje** - nie czeka na polecenia
2. **Wykonawcy raportują z dowodami** - nie "zrobione"
3. **Trading-domain priorytetyzuje** - perspektywa P&L
4. **Każdy ma MOTOR DZIAŁANIA** - proaktywność
5. **Ciągła pętla** - zawsze jest coś do poprawy
