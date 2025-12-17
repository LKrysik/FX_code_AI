# Code Map - FXcrypto

**Cel:** Szybkie znajdowanie plików bez grep/glob. Agent wie od razu gdzie szukać.

---

## BACKEND (Python) - 211 plików

### Sygnały i Strategie

| Chcę naprawić | Plik/Katalog |
|---------------|--------------|
| Generowanie sygnałów S1/Z1/ZE1 | `src/domain/services/strategy_manager.py` |
| Wykrywanie pump/dump | `src/domain/services/pump_detector.py` |
| Schemat strategii (warunki) | `src/domain/services/strategy_schema.py` |
| Zapisywanie strategii do DB | `src/domain/services/strategy_storage_questdb.py` |
| Szablony strategii | `src/domain/services/strategy_template_service.py` |

### Wskaźniki (Indicators)

| Chcę naprawić | Plik/Katalog |
|---------------|--------------|
| **Wszystkie wskaźniki** | `src/domain/services/indicators/` |
| RSI | `src/domain/services/indicators/rsi.py` |
| Price Velocity | `src/domain/services/indicators/price_velocity.py` |
| Volume Surge | `src/domain/services/indicators/volume_surge_ratio.py` |
| TWPA (Time-Weighted Price) | `src/domain/services/indicators/twpa.py` |
| Momentum Reversal | `src/domain/services/indicators/momentum_reversal_index.py` |
| Pump Magnitude | `src/domain/services/indicators/pump_magnitude_pct.py` |
| Baza dla nowych wskaźników | `src/domain/services/indicators/base_algorithm.py` |
| Rejestr wskaźników | `src/domain/services/indicators/algorithm_registry.py` |
| Streaming engine (real-time) | `src/domain/services/streaming_indicator_engine/` |
| Offline engine (backtest) | `src/domain/services/offline_indicator_engine.py` |
| Scheduler (QuestDB) | `src/domain/services/indicator_scheduler_questdb.py` |

### Trading i Zlecenia

| Chcę naprawić | Plik/Katalog |
|---------------|--------------|
| Paper trading engine | `src/trading/paper_trading_engine.py` |
| Paper trading persistence | `src/domain/services/paper_trading_persistence.py` |
| Live order manager | `src/domain/services/order_manager_live.py` |
| Backtest order manager | `src/domain/services/backtest_order_manager.py` |
| Order manager (bazowy) | `src/domain/services/order_manager.py` |
| Trading persistence | `src/domain/services/trading_persistence.py` |
| Performance tracker | `src/trading/performance_tracker.py` |

### Risk Management

| Chcę naprawić | Plik/Katalog |
|---------------|--------------|
| Risk manager (6 kontroli) | `src/domain/services/risk_manager.py` |
| Risk assessment | `src/domain/services/risk_assessment.py` |
| Liquidation monitor | `src/domain/services/liquidation_monitor.py` |
| Risk models | `src/domain/models/risk.py` |

### Sesje i Backtest

| Chcę naprawić | Plik/Katalog |
|---------------|--------------|
| Session manager | `src/trading/session_manager.py` |
| Session service | `src/domain/services/session_service.py` |
| Backtest data provider | `src/trading/backtest_data_provider_questdb.py` |
| Deployment manager | `src/trading/deployment_manager.py` |

### API Endpoints

| Chcę naprawić | Plik/Katalog |
|---------------|--------------|
| **Główny serwer** | `src/api/unified_server.py` |
| Trading routes | `src/api/trading_routes.py` |
| Signals routes | `src/api/signals_routes.py` |
| Indicators routes | `src/api/indicators_routes.py` |
| Paper trading routes | `src/api/paper_trading_routes.py` |
| Dashboard routes | `src/api/dashboard_routes.py` |
| Chart routes | `src/api/chart_routes.py` |
| Transactions routes | `src/api/transactions_routes.py` |
| State machine routes | `src/api/state_machine_routes.py` |
| Data analysis routes | `src/api/data_analysis_routes.py` |
| Monitoring routes | `src/api/monitoring_routes.py` |

### WebSocket

| Chcę naprawić | Plik/Katalog |
|---------------|--------------|
| WebSocket server | `src/api/websocket_server.py` |
| Connection manager | `src/api/connection_manager.py` |
| Subscription manager | `src/api/subscription_manager.py` |
| WS handlers (auth, session, strategy) | `src/api/websocket/handlers/` |
| WS lifecycle | `src/api/websocket/lifecycle/` |

### Giełda (MEXC)

| Chcę naprawić | Plik/Katalog |
|---------------|--------------|
| MEXC Futures adapter | `src/infrastructure/adapters/mexc_futures_adapter.py` |
| MEXC Paper adapter | `src/infrastructure/adapters/mexc_paper_adapter.py` |
| Exchange interfaces | `src/exchanges/` |

### Database (QuestDB)

| Chcę naprawić | Plik/Katalog |
|---------------|--------------|
| QuestDB provider | `src/data_feed/questdb_provider.py` |
| Data collection | `src/data/` |
| Strategy storage | `src/domain/services/strategy_storage_questdb.py` |
| Indicator persistence | `src/domain/services/indicator_persistence_service.py` |

### Core / Infrastructure

| Chcę naprawić | Plik/Katalog |
|---------------|--------------|
| Event Bus | `src/core/event_bus.py` |
| Time Manager | `src/core/time_manager.py` |
| DI Container | `src/infrastructure/container.py` |
| Config | `src/infrastructure/config/` |
| Monitoring | `src/infrastructure/monitoring/` |
| Startup validation | `src/infrastructure/startup_validation.py` |

### Domain Models

| Chcę naprawić | Plik/Katalog |
|---------------|--------------|
| Trading models | `src/domain/models/trading.py` |
| Signal models | `src/domain/models/signals.py` |
| Risk models | `src/domain/models/risk.py` |
| Market data models | `src/domain/models/market_data.py` |

---

## FRONTEND (TypeScript/React) - 146 plików

### Strony (App Router)

| Strona | Plik |
|--------|------|
| Dashboard (główna) | `frontend/src/app/page.tsx` |
| PumpDump Dashboard | `frontend/src/app/PumpDumpDashboard.tsx` |
| Strategy Builder | `frontend/src/app/strategy-builder/` |
| Strategies list | `frontend/src/app/strategies/` |
| Trading Session | `frontend/src/app/trading-session/` |
| Backtesting | `frontend/src/app/backtesting/` |
| Paper Trading | `frontend/src/app/paper/` |
| Live Trading | `frontend/src/app/trading/` |
| Data Collection | `frontend/src/app/data-collection/` |
| Session History | `frontend/src/app/session-history/` |
| Indicators | `frontend/src/app/indicators/` |
| Risk Management | `frontend/src/app/risk-management/` |
| Settings | `frontend/src/app/settings/` |
| Market Scanner | `frontend/src/app/market-scanner/` |
| Layout | `frontend/src/app/layout.tsx` |

### Komponenty - Dashboard

| Komponent | Plik |
|-----------|------|
| Symbol Watchlist | `frontend/src/components/dashboard/SymbolWatchlist.tsx` |
| Candlestick Chart | `frontend/src/components/dashboard/CandlestickChart.tsx` |
| Live Indicator Panel | `frontend/src/components/dashboard/LiveIndicatorPanel.tsx` |
| Signal History Panel | `frontend/src/components/dashboard/SignalHistoryPanel.tsx` |
| Signal Detail Panel | `frontend/src/components/dashboard/SignalDetailPanel.tsx` |
| Transaction History | `frontend/src/components/dashboard/TransactionHistoryPanel.tsx` |
| Session Config Dialog | `frontend/src/components/dashboard/SessionConfigDialog.tsx` |
| State Badge | `frontend/src/components/dashboard/StateBadge.tsx` |
| State Overview Table | `frontend/src/components/dashboard/StateOverviewTable.tsx` |
| Condition Progress | `frontend/src/components/dashboard/ConditionProgress.tsx` |
| Transition Log | `frontend/src/components/dashboard/TransitionLog.tsx` |
| Active Position Banner | `frontend/src/components/dashboard/ActivePositionBanner.tsx` |
| Pump Indicators Panel | `frontend/src/components/dashboard/PumpIndicatorsPanel.tsx` |

### Komponenty - Charts

| Komponent | Plik |
|-----------|------|
| Equity Curve Chart | `frontend/src/components/charts/EquityCurveChart.tsx` |
| Drawdown Chart | `frontend/src/components/charts/DrawdownChart.tsx` |
| PnL Distribution | `frontend/src/components/charts/PnLDistributionChart.tsx` |
| Win Rate Pie | `frontend/src/components/charts/WinRatePieChart.tsx` |
| Mini Sparkline | `frontend/src/components/charts/MiniSparkline.tsx` |
| UPlot Chart (base) | `frontend/src/components/UPlotChart.tsx` |

### Komponenty - Strategy

| Komponent | Plik |
|-----------|------|
| Strategy Builder (5 sekcji) | `frontend/src/components/strategy/StrategyBuilder5Section.tsx` |
| Strategy Builder (4 sekcji) | `frontend/src/components/strategy/StrategyBuilder4Section.tsx` |
| Condition Block | `frontend/src/components/strategy/ConditionBlock.tsx` |
| Condition Group | `frontend/src/components/strategy/ConditionGroup.tsx` |
| State Machine Diagram | `frontend/src/components/strategy/StateMachineDiagram.tsx` |
| Quick Backtest Preview | `frontend/src/components/strategy/QuickBacktestPreview.tsx` |
| Signal Preview Chart | `frontend/src/components/strategy/SignalPreviewChart.tsx` |
| Template Card/Dialog | `frontend/src/components/strategy/TemplateCard.tsx` |
| Version History | `frontend/src/components/strategy/StrategyVersionHistory.tsx` |

### Komponenty - Trading

| Komponent | Plik |
|-----------|------|
| Position Monitor | `frontend/src/components/trading/PositionMonitor.tsx` |
| Order History | `frontend/src/components/trading/OrderHistory.tsx` |
| Risk Alerts | `frontend/src/components/trading/RiskAlerts.tsx` |
| Liquidation Alert | `frontend/src/components/trading/LiquidationAlert.tsx` |
| Signal Log | `frontend/src/components/trading/SignalLog.tsx` |
| Trading Chart | `frontend/src/components/trading/TradingChart.tsx` |
| Session Config | `frontend/src/components/trading/SessionConfigDialog.tsx` |
| Strategy Preview Panel | `frontend/src/components/trading/StrategyPreviewPanel.tsx` |

### State Management (Zustand)

| Store | Plik |
|-------|------|
| Trading Store | `frontend/src/stores/tradingStore.ts` |
| Dashboard Store | `frontend/src/stores/dashboardStore.ts` |
| WebSocket Store | `frontend/src/stores/websocketStore.ts` |
| Auth Store | `frontend/src/stores/authStore.ts` |
| Health Store | `frontend/src/stores/healthStore.ts` |
| UI Store | `frontend/src/stores/uiStore.ts` |
| Types | `frontend/src/stores/types.ts` |

### Hooks

| Hook | Plik |
|------|------|
| useWebSocket | `frontend/src/hooks/useWebSocket.ts` |
| useSmartCache | `frontend/src/hooks/useSmartCache.ts` |
| useFinancialSafety | `frontend/src/hooks/useFinancialSafety.ts` |
| usePerformanceMonitor | `frontend/src/hooks/usePerformanceMonitor.ts` |
| useKeyboardShortcuts | `frontend/src/hooks/useKeyboardShortcuts.ts` |

### Utils

| Util | Plik |
|------|------|
| API fetch | `frontend/src/utils/fetchWithRetry.ts` |
| Config | `frontend/src/utils/config.ts` |
| Safety Guards | `frontend/src/utils/safetyGuards.ts` |
| Strategy Validation | `frontend/src/utils/strategyValidation.ts` |
| Leverage Calculator | `frontend/src/utils/leverageCalculator.ts` |

### Types

| Types | Plik |
|-------|------|
| Strategy types | `frontend/src/types/strategy.ts` |
| API types | `frontend/src/types/api.ts` |
| Theme types | `frontend/src/types/theme.ts` |

---

## MAPOWANIE: UI → API → Backend → DB

| Co widzi trader | Komponent UI | API Endpoint | Backend Service | Tabela DB |
|-----------------|--------------|--------------|-----------------|-----------|
| Lista symboli | `SymbolWatchlist` | `GET /api/symbols` | MEXC adapter | - |
| Wykres świecowy | `CandlestickChart` | `GET /api/ohlcv/{symbol}` | QuestDB provider | `ohlcv_1m` |
| Wartości wskaźników | `LiveIndicatorPanel` | `GET /api/indicators/{symbol}` | Indicator engine | - (calculated) |
| Historia sygnałów | `SignalHistoryPanel` | `GET /sessions/{id}/signals` | Strategy manager | `signals` |
| Equity curve | `EquityCurveChart` | `GET /sessions/{id}/equity` | Session service | `trading_sessions` |
| Drawdown | `DrawdownChart` | `GET /sessions/{id}/equity` | Session service | `trading_sessions` |
| Pozycje | `PositionMonitor` | `GET /sessions/{id}/positions` | Order manager | `trades` |
| Transakcje | `TransactionHistoryPanel` | `GET /sessions/{id}/transactions` | Order manager | `trades` |
| Strategy builder | `StrategyBuilder5Section` | `POST /api/strategies` | Strategy storage | JSON file |

---

## TESTY

| Katalog | Co testuje |
|---------|------------|
| `tests/` | Testy backendowe (pytest) |
| `tests/unit/` | Testy jednostkowe |
| `tests/integration/` | Testy integracyjne |
| `frontend/src/**/__tests__/` | Testy frontendowe |

**Komendy:**
```bash
python run_tests.py              # Wszystkie testy backend
pytest tests/test_X.py -v        # Pojedynczy test
cd frontend && npm run test      # Testy frontend
```

---

## SZYBKI LOOKUP: "Mam błąd w X"

| Błąd / Symptom | Sprawdź najpierw |
|----------------|------------------|
| Sygnały nie generują się | `strategy_manager.py`, `pump_detector.py` |
| Wskaźnik zwraca błędne wartości | `src/domain/services/indicators/{wskaźnik}.py` |
| Equity curve pusta | `session_service.py`, `performance_tracker.py` |
| Paper trading nie działa | `paper_trading_engine.py`, `order_manager.py` |
| WebSocket disconnect | `websocket_server.py`, `connection_manager.py` |
| API zwraca 500 | `src/api/*_routes.py`, sprawdź logi |
| Frontend nie ładuje danych | `frontend/src/stores/`, `frontend/src/hooks/useWebSocket.ts` |
| Wykres pusty | `frontend/src/components/charts/`, sprawdź API response |
| QuestDB nie odpowiada | `questdb_provider.py`, sprawdź port 8812 |
| MEXC connection error | `mexc_futures_adapter.py` |

---

**Ostatnia aktualizacja:** 2025-12-17
