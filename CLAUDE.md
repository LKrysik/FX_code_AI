# CLAUDE.md

Kontekst dla Claude Code pracującego nad tym projektem.

## TRYB PRACY: AUTONOMICZNY

Agent AI pracuje w **ciągłej pętli** bez udziału użytkownika:
```
ANALIZA → PLANOWANIE → IMPLEMENTACJA → WERYFIKACJA → ANALIZA...
```

## GŁÓWNE DOKUMENTY

| Dokument | Co definiuje | Kiedy czytać |
|----------|--------------|--------------|
| **[docs/DEFINITION_OF_DONE.md](docs/DEFINITION_OF_DONE.md)** | CEL + METRYKI sukcesu | Na początku każdej iteracji |
| **[WORKFLOW.md](WORKFLOW.md)** | PROCES pracy | Gdy nie wiesz jak działać |

**ZASADA: Buduję NARZĘDZIE, nie strategię. Trader sam optymalizuje.**

## SZYBKI START DLA AGENTA

```powershell
# 1. Aktywuj środowisko
& C:\Users\lukasz.krysik\Desktop\FXcrypto\FX_code_AI_v2\.venv\Scripts\Activate.ps1

# 2. Sprawdź stan
python run_tests.py                    # Testy
curl http://localhost:8080/health      # Backend

# 3. Przeczytaj docs/DEFINITION_OF_DONE.md → wybierz zadanie → realizuj
```

## Co To Jest

**FXcrypto** - platforma do wykrywania pump-and-dump na kryptowalutach.

Szczegółowy opis produktu: [docs/PRODUCT.md](docs/PRODUCT.md)

## Quick Start

```powershell
# Uruchom wszystko:
.\start_all.ps1

# Sprawdź:
curl http://localhost:8080/health  # → {"status": "healthy"}
# Frontend: http://localhost:3000
# QuestDB: http://localhost:9000
```

## Struktura Projektu

```
src/
├── api/                    # REST + WebSocket (FastAPI)
├── application/controllers # Orchestracja (ExecutionController, UnifiedTradingController)
├── domain/services/        # Logika biznesowa
│   ├── strategy_manager.py       # Zarządzanie strategiami
│   ├── risk_manager.py           # Zarządzanie ryzykiem
│   └── streaming_indicator_engine/ # Obliczanie wskaźników
├── infrastructure/         # Adaptery, baza danych
│   ├── adapters/mexc_*     # Połączenie z giełdą MEXC
│   └── container.py        # Dependency Injection
└── core/                   # EventBus, Logger, Config

frontend/                   # Next.js 14

docs/
├── PRODUCT.md              # Opis produktu i funkcjonalności
├── IDEAS.md                # Backlog pomysłów na rozwój
├── HOW_TO_TEST.md          # Jak testować
├── KNOWN_ISSUES.md         # Znane problemy
└── ROADMAP.md              # Roadmapa rozwoju
```

## Kluczowe Koncepty

### Strategy Builder - 5 Sekcji Warunków

1. **S1 (Signal Detection)** - kiedy szukać okazji
2. **O1 (Signal Cancellation)** - kiedy anulować sygnał
3. **Z1 (Entry Conditions)** - kiedy wejść w pozycję
4. **ZE1 (Close Order)** - kiedy zamknąć z zyskiem
5. **E1 (Emergency Exit)** - kiedy uciekać (stop-loss)

### Wskaźniki

```python
# Główne wskaźniki dla pump detection:
- price_velocity  # szybkość zmiany ceny
- volume_surge    # anomalie wolumenu
- twpa            # Time-Weighted Price Average

# Parametry czasowe (t1, t2) w sekundach:
# t1=300, t2=0 oznacza "ostatnie 5 minut"
```

### EventBus - Komunikacja Komponentów

```
market.price_update → StreamingIndicatorEngine → indicator.updated → StrategyManager → signal_generated
```

### Baza Danych

**QuestDB** (NIE PostgreSQL!) na portach:
- 9000: Web UI
- 8812: SQL (protokół PostgreSQL)
- 9009: Line Protocol (szybki zapis)

## Testowanie

```powershell
# Testy automatyczne:
python run_tests.py

# Test Strategy Builder:
python scripts/test_strategy_builder_e2e.py

# Więcej: docs/HOW_TO_TEST.md
```

## Znane Problemy

- Backtest może nie generować sygnałów jeśli progi są za wysokie
- WebSocket reconnection może wymagać odświeżenia strony
- Szczegóły: [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)

## Pomysły na Rozwój

Backlog: [docs/IDEAS.md](docs/IDEAS.md)

## Zasady Pracy

1. **Nie zakładaj - sprawdź** - uruchom kod, zobacz output
2. **Nie duplikuj** - sprawdź czy podobna logika już istnieje
3. **Nie twórz backward compatibility hacków** - napraw źródło problemu
4. **Testuj przed i po** - `python run_tests.py`
5. **Dokumentuj tylko to co potrzebne** - nie twórz nadmiaru plików MD
