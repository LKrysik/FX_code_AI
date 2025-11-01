# Prosty System Konfiguracji w PostgreSQL

## Problem
Obecnie konfiguracja jest tylko w JSON. Nie można zmieniać parametrów bez restartu aplikacji.

## Rozwiązanie

### 1. Tabela w PostgreSQL (NIE QuestDB!)

```sql
-- Używamy PostgreSQL (już masz connection przez QuestDB!)
CREATE TABLE runtime_config (
    config_key VARCHAR(255) PRIMARY KEY,
    config_value TEXT NOT NULL,
    value_type VARCHAR(20) NOT NULL,  -- 'int', 'float', 'bool', 'string'
    category VARCHAR(50),
    description TEXT,
    min_value NUMERIC,
    max_value NUMERIC,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(100)
);

-- Historia zmian
CREATE TABLE config_history (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(255),
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT NOW()
);

-- Przykładowe wartości
INSERT INTO runtime_config VALUES
('buffer.max_series_length', '1000', 'int', 'memory',
 'Maksymalna długość ring buffera', 100, 10000, NOW(), 'system'),

('buffer.ttl_seconds', '600', 'int', 'memory',
 'TTL dla nieużywanych danych', 60, 3600, NOW(), 'system'),

('indicator.rsi_period', '14', 'int', 'indicator',
 'Okres RSI', 5, 200, NOW(), 'system');
```

### 2. Prosty ConfigService (150 linii kodu)

```python
# src/application/services/config_service.py

class ConfigService:
    """
    Prosty serwis konfiguracji z cache i fallback do AppSettings.
    """

    def __init__(self, pg_pool, settings: AppSettings, logger):
        self.pg_pool = pg_pool  # ✅ Używa istniejącego PostgreSQL pool!
        self.settings = settings  # ✅ Fallback do JSON config
        self.logger = logger
        self._cache = {}
        self._cache_ttl = 300  # 5 minut
        self._last_refresh = 0

    async def get(self, key: str, default=None):
        """
        Pobierz wartość konfiguracji.

        Kolejność:
        1. PostgreSQL override (jeśli istnieje)
        2. AppSettings (z JSON)
        3. default value
        """
        # Cache check
        if key in self._cache:
            cached = self._cache[key]
            if time.time() - cached['timestamp'] < self._cache_ttl:
                return cached['value']

        # Query PostgreSQL
        async with self.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT config_value, value_type FROM runtime_config WHERE config_key = $1",
                key
            )

        if row:
            # Parse typed value
            value = self._parse_value(row['config_value'], row['value_type'])
            self._cache[key] = {'value': value, 'timestamp': time.time()}
            return value

        # Fallback to AppSettings
        return self._get_from_appsettings(key, default)

    async def set(self, key: str, value: Any, changed_by: str = 'system'):
        """
        Ustaw wartość konfiguracji (z audit trail).
        """
        # Get old value for history
        old_value = await self.get(key)

        async with self.pg_pool.acquire() as conn:
            # Update config
            await conn.execute("""
                INSERT INTO runtime_config (config_key, config_value, value_type, updated_at, updated_by)
                VALUES ($1, $2, $3, NOW(), $4)
                ON CONFLICT (config_key) DO UPDATE
                SET config_value = $2, updated_at = NOW(), updated_by = $4
            """, key, str(value), type(value).__name__, changed_by)

            # Add to history
            await conn.execute("""
                INSERT INTO config_history (config_key, old_value, new_value, changed_by)
                VALUES ($1, $2, $3, $4)
            """, key, str(old_value), str(value), changed_by)

        # Invalidate cache
        if key in self._cache:
            del self._cache[key]

        self.logger.info("config.updated", {
            'key': key,
            'old_value': old_value,
            'new_value': value,
            'changed_by': changed_by
        })
```

### 3. Integracja w StreamingIndicatorEngine

```python
# src/domain/services/streaming_indicator_engine.py

class StreamingIndicatorEngine:
    def __init__(self, ..., config_service: ConfigService):
        self.config_service = config_service

        # ✅ ZAMIAST hardcoded wartości:
        # self._max_series_length = 1000

        # ✅ NOWE: Pobierz z config_service
        self._max_series_length = await config_service.get(
            'buffer.max_series_length',
            default=1000
        )

        self._data_ttl_seconds = await config_service.get(
            'buffer.ttl_seconds',
            default=600
        )
```

### 4. API Endpoint Do Zmiany Konfiguracji

```python
# src/api/config_routes.py

@router.get("/api/config/{key}")
async def get_config(key: str):
    """Pobierz wartość konfiguracji"""
    value = await config_service.get(key)
    return {"key": key, "value": value}

@router.post("/api/config/{key}")
async def update_config(key: str, request: UpdateConfigRequest):
    """Zmień wartość konfiguracji"""
    await config_service.set(key, request.value, request.changed_by)
    return {"success": True, "key": key, "new_value": request.value}

@router.get("/api/config/{key}/history")
async def get_config_history(key: str):
    """Historia zmian konfiguracji"""
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM config_history
            WHERE config_key = $1
            ORDER BY changed_at DESC
            LIMIT 100
        """, key)
    return {"key": key, "history": [dict(r) for r in rows]}
```

## Korzyści

1. ✅ **Prosty** - tylko 150 linii kodu (nie 2000+ jak w PRD)
2. ✅ **Używa PostgreSQL** - właściwa baza do konfiguracji
3. ✅ **Nie zmienia architektury** - tylko dodaje warstwę config
4. ✅ **Cache** - szybki dostęp (5 min TTL)
5. ✅ **Audit trail** - historia wszystkich zmian
6. ✅ **Fallback** - działa nawet jeśli baza nie odpowiada
7. ✅ **Nie konfliktuje ze Sprint 16**

## Implementacja (1 tydzień)

### Dzień 1-2: PostgreSQL schema i ConfigService
- Stwórz tabele
- Implementuj ConfigService (150 linii)
- Unit testy

### Dzień 3-4: Integracja
- Dodaj ConfigService do Container (DI)
- Zintegruj ze StreamingIndicatorEngine
- Zintegruj z DataCollectionPersistenceService

### Dzień 5: API endpoints
- GET /api/config/{key}
- POST /api/config/{key}
- GET /api/config/{key}/history

### Dzień 6-7: Testowanie
- Integration tests
- Manual testing
- Documentation

## Porównanie z PRD

| Metryka | PRD | Ta propozycja |
|---------|-----|---------------|
| Linie kodu | 2000+ | 150 |
| Nowe tabele | 10+ | 2 |
| Ryzyko konfliktu ze Sprint 16 | WYSOKIE | BRAK |
| Performance impact | Regression (50-100ms) | Zero (tylko config load) |
| Baza danych | QuestDB (ZŁA) | PostgreSQL (DOBRA) |
| Czas implementacji | 6 tygodni | 1 tydzień |
| Korzyści | Wątpliwe | Jasne i natychmiastowe |
