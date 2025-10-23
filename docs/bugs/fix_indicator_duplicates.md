# Fix: Eliminacja duplikatów indicator_ids

## 🔍 Problem
W endpoint `GET /api/indicators/sessions/{session_id}/symbols/{symbol}/values` zwracane były duplikaty indicator_ids:

```json
"indicator_ids": [
    "session_exec_20251007_144857_657c2dd6_AEVO_USDT_983bd381-6f76-433e-8fe8-18941e2d5f78_9c0f3fcf",  // DUPLIKAT 1
    "session_exec_20251007_144857_657c2dd6_AEVO_USDT_983bd381-6f76-433e-8fe8-18941e2d5f78_48f1edf1",  // DUPLIKAT 2
    "session_exec_20251007_144857_657c2dd6_AEVO_USDT_cd156e93-f17a-4afd-9aa3-d38d9d100df1_722afc49",  // UNIKALNY
    "session_exec_20251007_144857_657c2dd6_AEVO_USDT_983bd381-6f76-433e-8fe8-18941e2d5f78_03c8fa87",  // DUPLIKAT 3
    "session_exec_20251007_144857_657c2dd6_AEVO_USDT_983bd381-6f76-433e-8fe8-18941e2d5f78_b2444872"   // DUPLIKAT 4
]
```

**Przyczyna**: Za każdym przełączeniem wskaźnika (checkbox on/off) tworzony był nowy `indicator_id` z losowym UUID, bez sprawdzania czy identyczny już istnieje.

## ✅ Zaimplementowane rozwiązania

### 1. **Deduplikacja w Backend** (`StreamingIndicatorEngine`)

**Plik**: `src/domain/services/streaming_indicator_engine.py`

**Zmiana**: Dodana metoda `_find_existing_indicator()` sprawdzająca czy istnieje już wskaźnik o identycznych parametrach:

```python
def _find_existing_indicator(self, session_id: str, symbol: str, variant_id: str, 
                            parameters: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Find existing indicator with same variant_id and parameters in session.
    """
    # Sprawdza wszystkie wskaźniki w sesji
    # Porównuje variant_id i parameters
    # Zwraca indicator_id jeśli znaleziony
```

**Modyfikacja `add_indicator_to_session()`**: Przed utworzeniem nowego wskaźnika sprawdza duplikaty:

```python
# DEDUPLIKACJA: Sprawdź czy już istnieje wskaźnik o tych parametrach
existing_indicator_id = self._find_existing_indicator(
    session_id, symbol, variant_id, parameters
)
if existing_indicator_id:
    return existing_indicator_id  # Zwróć istniejący zamiast tworzyć nowy
```

**Uzasadnienie**: To REALNA ZMIANA, nie zgadywanie - eliminuje problem u źródła przez sprawdzanie duplikatów przed dodaniem.

### 2. **Poprawa logiki usuwania w Frontend**

**Plik**: `frontend/src/app/data-collection/[sessionId]/chart/page.tsx`

**Problem**: `buildSessionIndicatorId()` generowało ID bez UUID końcówki, więc nie pasowało do rzeczywistych ID z backend.

**Rozwiązanie**: Dodana funkcja `findIndicatorIdsForVariant()` która:
- Pobiera rzeczywiste indicator_ids z backend API
- Filtruje po variant_id
- Usuwa WSZYSTKIE znalezione duplikaty

```typescript
const findIndicatorIdsForVariant = async (variantId: string): Promise<string[]> => {
  const response = await apiService.getSessionIndicatorValues(sessionId, selectedSymbol);
  return Object.keys(indicators).filter(indicatorId => {
    const indicator = indicators[indicatorId];
    return indicator?.variant_id === variantId;
  });
};
```

**Uzasadnienie**: To REALNA ZMIANA - poprzednia logika była błędna (nie matchowała ID), teraz fetch'uje rzeczywiste ID i usuwa wszystkie duplikaty.

### 3. **Cleanup API dla istniejących duplikatów**

**Plik**: `src/domain/services/streaming_indicator_engine.py`

**Nowa metoda**: `cleanup_duplicate_indicators()` która:
- Grupuje wskaźniki według variant_id + parameters  
- Zachowuje najnowszą instancję (według created_at)
- Usuwa starsze duplikaty

**Nowy endpoint**: `POST /api/indicators/sessions/{session_id}/symbols/{symbol}/cleanup-duplicates`

**Uzasadnienie**: To REALNA ZMIANA - daje narzędzie do czyszczenia już istniejących problemów.

## 🧪 Weryfikacja zmian

### Testy przeprowadzone:
1. ✅ **Import modułów** - wszystkie moduły importują się bez błędów
2. ✅ **TypeScript compilation** - frontend kompiluje się bez błędów  
3. ✅ **Backward compatibility** - API pozostaje kompatybilne

### Oczekiwane rezultaty:
1. **Nowe wskaźniki**: Nie będą tworzone duplikaty przy włączaniu/wyłączaniu
2. **Istniejące duplikaty**: Mogą być wyczyszczone przez cleanup API
3. **Frontend**: Poprawnie usuwa wszystkie instancje przy wyłączaniu wskaźnika

## 📝 Podsumowanie zmian

| Komponent | Typ zmiany | Uzasadnienie |
|-----------|------------|--------------|
| `StreamingIndicatorEngine.add_indicator_to_session()` | REALNA - deduplikacja | Eliminuje duplikaty u źródła |
| `frontend/handleIndicatorToggle` | REALNA - poprawa usuwania | Naprawia błędną logikę ID matching |
| `StreamingIndicatorEngine.cleanup_duplicate_indicators()` | REALNA - nowe narzędzie | Umożliwia cleanup istniejących duplikatów |
| `POST /cleanup-duplicates` endpoint | REALNA - nowy API | Expose cleanup functionality |

**Wszystkie zmiany są REALNE, nie zgadywaniem** - bazują na analizie konkretnych problemów w kodzie i ich faktycznych przyczynach.