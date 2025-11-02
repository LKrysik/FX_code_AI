# Container Architecture - Dependency Injection Patterns

## 🎯 OVERVIEW

Use a central container for dependency injection to assemble application components without business logic, ensuring loose coupling and testability.

## 🏗️ PRINCIPLES

- **Pure Assembly**: Container only wires dependencies from config.
- **No Logic**: Delegate conditionals to factories.
- **Injection**: Use constructor injection exclusively.
- **Scopes**: Support singleton and transient services.

## 📜 IMPLEMENTATION

### Actual Container Structure

```python
class Container:
    def __init__(self, settings: Settings, event_bus: EventBus, logger: StructuredLogger):
        self.settings = settings
        self.event_bus = event_bus
        self.logger = logger
        # Singletons cached here
        self._cached_services = {}
```

### Factory Methods (Real Examples)

```python
# From src/infrastructure/container.py

async def create_websocket_server(self):
    """Creates WebSocket API server (singleton)"""
    if 'websocket_server' not in self._cached_services:
        server = WebSocketAPIServer(
            event_bus=self.event_bus,
            logger=self.logger,
            host=self.settings.api.websocket_host,
            port=self.settings.api.websocket_port
        )
        self._cached_services['websocket_server'] = server
    return self._cached_services['websocket_server']

async def create_unified_trading_controller(self):
    """Creates execution controller"""
    execution_controller = await self.create_execution_controller()
    strategy_manager = await self.create_strategy_manager()

    controller = UnifiedTradingController(
        execution_controller=execution_controller,
        strategy_manager=strategy_manager,
        event_bus=self.event_bus,
        logger=self.logger
    )
    return controller

async def create_market_data_provider(self):
    """Factory creates appropriate provider based on mode"""
    if self.settings.trading.mode == TradingMode.LIVE:
        return MEXCAdapter(...)
    elif self.settings.trading.mode == TradingMode.BACKTEST:
        return HistoricalDataProvider(...)
    else:
        return DataCollectionProvider(...)
```

### Real Usage in unified_server.py

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings_from_working_directory()
    logger = StructuredLogger("UnifiedServer", settings.logging)
    event_bus = EventBus()
    container = Container(settings, event_bus, logger)

    # Create services via container
    ws_server = await container.create_websocket_server()
    app.state.websocket_api_server = ws_server

    ws_controller = await container.create_unified_trading_controller()
    ws_strategy_manager = await container.create_strategy_manager()
    ws_server.controller = ws_controller
    ws_server.strategy_manager = ws_strategy_manager

    live_market_adapter = await container.create_live_market_adapter()
    session_manager = await container.create_session_manager()

    # Store in app.state for endpoint access
    app.state.live_market_adapter = live_market_adapter
    app.state.session_manager = session_manager

    yield

    # Shutdown
    await ws_server.stop()
```

## 🚫 ANTI-PATTERNS

- **NO global container access** - pass through constructors only
- **NO service locator pattern** - explicit dependency injection
- **NO business logic in Container** - pure object assembly only

## ✅ BEST PRACTICES

1. **Factory Methods**: One method per service type
2. **Singleton Caching**: Cache expensive services in `_cached_services`
3. **Constructor Injection**: Pass dependencies explicitly
4. **Mode-Based Factories**: Use settings to decide which implementation to create
5. **Lifespan Management**: Create in startup, cleanup in shutdown

Follow for clean, maintainable architecture.