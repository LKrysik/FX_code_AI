# Adaptywny Rozmiar Ring Bufferów

## Problem
Obecnie wszystkie symbole mają ten sam rozmiar buffera: 1000 punktów.

```python
# src/domain/services/streaming_indicator_engine.py (linia 357)
self._max_series_length = 1000  # HARDCODED dla wszystkich!
```

Ale różne symbole mogą potrzebować różnych rozmiarów:
- **BTC_USDT** (aktywny handel) → może wystarczy 500 punktów
- **ALU_USDT** (niska płynność) → może potrzeba 2000 punktów dla stabilności

## Rozwiązanie: Adaptywny Rozmiar Na Podstawie Wskaźników

### 1. Określ Minimalny Rozmiar Na Podstawie Wskaźników

```python
# src/domain/services/streaming_indicator_engine.py

class StreamingIndicatorEngine:

    def calculate_required_buffer_size(self, symbol: str) -> int:
        """
        Oblicz minimalny rozmiar buffera dla symbolu
        na podstawie aktywnych wskaźników.

        Przykład:
        - RSI(14) potrzebuje 14 punktów
        - SMA(200) potrzebuje 200 punktów
        - Bollinger Bands(20) potrzebuje 20 punktów

        Bierzemy MAX + 20% margines.
        """
        # Znajdź wszystkie warianty dla tego symbolu
        active_variants = [
            variant for variant in self._variants.values()
            if variant.symbol == symbol
        ]

        if not active_variants:
            return self._default_buffer_size  # 1000 (z konfiguracji)

        # Oblicz maksymalny wymagany lookback
        max_lookback = 0
        for variant in active_variants:
            # Przykład: TWPA(t1=300, t2=0) → lookback = 300 sekund
            if 't1' in variant.parameters:
                t1 = variant.parameters['t1']
                max_lookback = max(max_lookback, t1)

            # Przykład: RSI(period=14) → lookback = 14 punktów
            if 'period' in variant.parameters:
                period = variant.parameters['period']
                max_lookback = max(max_lookback, period)

            # Przykład: SMA(window=200) → lookback = 200 punktów
            if 'window' in variant.parameters:
                window = variant.parameters['window']
                max_lookback = max(max_lookback, window)

        # Konwertuj sekundy na punkty (jeśli tick rate = 1/sek)
        # Dodaj 20% margines
        required_size = int(max_lookback * 1.2)

        # Clamp between min and max
        min_size = 100
        max_size = 10000
        return max(min_size, min(required_size, max_size))

    async def create_or_resize_buffer(self, symbol: str):
        """
        Stwórz lub zmień rozmiar buffera dla symbolu.
        """
        required_size = self.calculate_required_buffer_size(symbol)

        if symbol not in self._price_data:
            # Nowy buffer
            self._price_data[symbol] = deque(maxlen=required_size)
            self.logger.info("buffer.created", {
                'symbol': symbol,
                'size': required_size
            })
        else:
            # Sprawdź czy trzeba zwiększyć
            current_buffer = self._price_data[symbol]
            if current_buffer.maxlen < required_size:
                # ✅ Python deque nie pozwala zmienić maxlen in-place
                # Trzeba stworzyć nowy buffer i skopiować dane
                old_buffer = self._price_data[symbol]
                new_buffer = deque(old_buffer, maxlen=required_size)
                self._price_data[symbol] = new_buffer

                self.logger.info("buffer.resized", {
                    'symbol': symbol,
                    'old_size': old_buffer.maxlen,
                    'new_size': required_size
                })
```

### 2. Auto-Resize Gdy Dodajesz Nowy Wskaźnik

```python
# src/domain/services/streaming_indicator_engine.py

async def create_variant(
    self,
    name: str,
    base_indicator_type: str,
    variant_type: str,
    parameters: Dict[str, Any],
    symbol: str,
    created_by: str = "user"
) -> str:
    """
    Stwórz nowy wariant wskaźnika.
    """
    # ... existing validation code ...

    # Zapisz wariant
    variant_id = str(uuid.uuid4())
    self._variants[variant_id] = IndicatorVariant(
        id=variant_id,
        name=name,
        base_indicator_type=base_indicator_type,
        parameters=parameters,
        symbol=symbol,
        ...
    )

    # ✅ NOWE: Auto-resize buffer jeśli potrzeba
    await self.create_or_resize_buffer(symbol)

    self.logger.info("variant.created_with_buffer_check", {
        'variant_id': variant_id,
        'symbol': symbol,
        'buffer_size': self._price_data[symbol].maxlen
    })

    return variant_id
```

### 3. API Endpoint Do Ręcznej Zmiany Rozmiaru (Opcjonalnie)

```python
# src/api/buffer_routes.py

@router.get("/api/buffers")
async def get_buffer_stats():
    """
    Zwróć statystyki wszystkich bufferów.
    """
    stats = {}
    for symbol, buffer in streaming_engine._price_data.items():
        stats[symbol] = {
            'current_size': len(buffer),
            'max_size': buffer.maxlen,
            'utilization_pct': len(buffer) / buffer.maxlen * 100,
            'oldest_timestamp': buffer[0].timestamp if buffer else None,
            'newest_timestamp': buffer[-1].timestamp if buffer else None,
            'active_variants': len([
                v for v in streaming_engine._variants.values()
                if v.symbol == symbol
            ])
        }
    return stats


@router.post("/api/buffers/{symbol}/resize")
async def resize_buffer(symbol: str, new_size: int):
    """
    Ręcznie zmień rozmiar buffera dla symbolu.

    Użycie: Tylko gdy chcesz override automatyczny rozmiar.
    """
    if new_size < 100 or new_size > 10000:
        raise ValueError("Buffer size must be between 100 and 10000")

    old_buffer = streaming_engine._price_data.get(symbol)
    if not old_buffer:
        raise ValueError(f"No buffer exists for {symbol}")

    # Resize
    new_buffer = deque(old_buffer, maxlen=new_size)
    streaming_engine._price_data[symbol] = new_buffer

    return {
        'symbol': symbol,
        'old_size': old_buffer.maxlen,
        'new_size': new_size,
        'data_preserved': len(new_buffer)
    }
```

## Przykład Działania

### Scenariusz 1: Prosty Symbol z RSI

```
Użytkownik dodaje wariant:
- Symbol: BTC_USDT
- Indicator: RSI(period=14)

System oblicza:
- Required lookback: 14 punktów
- With margin (20%): 14 * 1.2 = 16.8 → 17 punktów
- Clamp to minimum: max(17, 100) = 100 punktów

Buffer size: 100 punktów (zamiast 1000!)
Oszczędność pamięci: 90%
```

### Scenariusz 2: Symbol z Wieloma Wskaźnikami

```
Użytkownik dodaje warianty:
1. RSI(period=14) → lookback = 14
2. SMA(window=50) → lookback = 50
3. TWPA(t1=300, t2=0) → lookback = 300 sekund
4. Bollinger Bands(period=20) → lookback = 20

System oblicza:
- MAX lookback: 300 (z TWPA)
- With margin: 300 * 1.2 = 360 punktów

Buffer size: 360 punktów (zamiast 1000!)
Oszczędność pamięci: 64%
```

### Scenariusz 3: Symbol z Long-Term Indicators

```
Użytkownik dodaje warianty:
1. SMA(window=200) → lookback = 200
2. EMA(window=100) → lookback = 100
3. ATR(period=200) → lookback = 200

System oblicza:
- MAX lookback: 200
- With margin: 200 * 1.2 = 240 punktów

Buffer size: 240 punktów (zamiast 1000!)
Oszczędność pamięci: 76%
```

## Korzyści

1. ✅ **Oszczędność pamięci** - każdy symbol ma optymalny rozmiar
2. ✅ **Automatyczny** - nie musisz konfigurować ręcznie
3. ✅ **Bezpieczny** - zawsze min 100 punktów, max 10000
4. ✅ **Elastyczny** - rośnie gdy dodajesz wskaźniki
5. ✅ **Transparentny** - API pokazuje wszystkie rozmiary
6. ✅ **Backward compatible** - domyślnie 1000 (z konfiguracji)

## Implementacja (1 dzień)

### Godzina 1-2: Core Logic
- `calculate_required_buffer_size()` (40 linii)
- `create_or_resize_buffer()` (30 linii)
- Integracja z `create_variant()` (5 linii)

### Godzina 3-4: API Endpoints
- GET `/api/buffers` (20 linii)
- POST `/api/buffers/{symbol}/resize` (20 linii)

### Godzina 5-6: Testy
- Unit tests dla calculation logic
- Integration tests dla resize
- Performance tests (nie powinno spowolnić)

### Godzina 7-8: Documentation
- Update API docs
- Add examples to CLAUDE.md

## Konfiguracja (Integracja z ConfigService)

```python
# Dodaj do runtime_config

INSERT INTO runtime_config VALUES
('buffer.default_size', '1000', 'int', 'memory',
 'Domyślny rozmiar buffera gdy brak wskaźników', 100, 10000, NOW(), 'system'),

('buffer.min_size', '100', 'int', 'memory',
 'Minimalny rozmiar buffera', 10, 1000, NOW(), 'system'),

('buffer.max_size', '10000', 'int', 'memory',
 'Maksymalny rozmiar buffera', 1000, 100000, NOW(), 'system'),

('buffer.margin_pct', '20', 'int', 'memory',
 'Margines bezpieczeństwa (% powyżej wymaganego)', 0, 100, NOW(), 'system'),

('buffer.auto_resize', 'true', 'bool', 'memory',
 'Automatyczna zmiana rozmiaru przy dodawaniu wskaźników', NULL, NULL, NOW(), 'system');
```

## Porównanie Podejść

| Metryka | Obecny (Fixed) | PRD (Flush to DB) | Ta propozycja (Adaptive) |
|---------|----------------|-------------------|--------------------------|
| Pamięć (100 symboli) | 15 MB | ~1 MB | 3-10 MB (depends on indicators) |
| Latencja dostępu | <1ms | 50-100ms | <1ms |
| Złożoność | Prosta | Wysoka | Średnia |
| Ryzyko | Brak | Performance regression | Brak |
| Implementacja | 0 dni | 6 tygodni | 1 dzień |
| Korzyści | Wystarczające | Wątpliwe | Jasne |

## Monitoring (Dodaj do Memory Dashboard)

```typescript
// W frontend/components/MemoryDashboard.tsx

<div className="buffer-sizes">
  <h3>Buffer Sizes by Symbol</h3>
  <table>
    <thead>
      <tr>
        <th>Symbol</th>
        <th>Current / Max</th>
        <th>Utilization</th>
        <th>Active Indicators</th>
      </tr>
    </thead>
    <tbody>
      {Object.entries(stats.buffers).map(([symbol, buffer]) => (
        <tr key={symbol}>
          <td>{symbol}</td>
          <td>{buffer.current_size} / {buffer.max_size}</td>
          <td>
            <ProgressBar
              value={buffer.utilization_pct}
              color={buffer.utilization_pct > 80 ? 'red' : 'green'}
            />
          </td>
          <td>{buffer.active_variants}</td>
        </tr>
      ))}
    </tbody>
  </table>
</div>
```
