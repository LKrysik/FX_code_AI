# Changelog - wersja 3.15

## Data: 2025-11-24

## Główne zmiany

### 1. Nowy `operation_type`: "Incremental Table"

Funkcja `create_incremental_table()` została zintegrowana jako standardowy `operation_type` w systemie `metadata_json`.

#### Poprzednia implementacja (LEGACY):
```python
# 50+ linii kodu
metadata_full_load = '...'
metadata_delta_load = '...'
target_table_name = get_table_env_name(...)
source_table_name = get_table_env_name(...)
history_table_name = get_table_env_name(...)

df = create_incremental_table(
    id_key_column="src_agnostic_unique_id",
    target_table_name=target_table_name,
    source_table_name=source_table_name,
    metadata_full_load=metadata_full_load,
    metadata_delta_load=metadata_delta_load,
    create_table_params={"skip_data_lineage": True},
    log_history=True,
    history_table_name=history_table_name,
    history_retention_days=30
)
```

#### Nowa implementacja:
```python
# 3 linie kodu!
metadata_json = '''
{
    "target_table": {
        "operation_type": "Incremental Table",
        "incremental_params": {
            "id_key_column": "src_agnostic_unique_id",
            "log_history": true,
            "history_table_name": "..._delta_log",
            "history_retention_days": 30
        }
    },
    "source_tables": [...]
}
'''
make_env_tables(metadata_json)
df = create_table(metadata_json)
```

### 2. Backward Compatibility dla typo "opertation_type"

System teraz obsługuje zarówno:
- `"operation_type"` (poprawna nazwa)
- `"opertation_type"` (literówka używana w istniejącym kodzie)

Zmiana w linii 205 funkcji `create_table`:
```python
# Poprzednio:
opertation_type = metadata["target_table"].get("opertation_type", None)

# Teraz:
opertation_type = metadata["target_table"].get("operation_type",
                  metadata["target_table"].get("opertation_type", None))
```

### 3. Parametry "Incremental Table"

Wszystkie parametry konfigurowane przez `incremental_params` w metadata:

| Parametr | Typ | Wymagane | Domyślnie | Opis |
|----------|-----|----------|-----------|------|
| `id_key_column` | string | ✅ Tak | - | Klucz główny do porównywania rekordów |
| `included_columns_for_hash` | list | Nie | null | Kolumny śledzone (null = wszystkie) |
| `excluded_columns_for_hash` | list | Nie | null | Kolumny ignorowane w detekcji |
| `log_history` | boolean | Nie | false | Czy zapisywać historię zmian |
| `history_table_name` | string | Nie | null | Tabela z historią |
| `history_retention_days` | int | Nie | null | Dni retencji historii |
| `ignore_new_columns_as_change` | boolean | Nie | true | Czy nowe kolumny = Update |

### 4. Logika działania

#### Full Load (target nie istnieje):
1. Tworzy tabelę target z danych z `source_tables`
2. Dodaje kolumny:
   - `operation_type = 'I'` (Insert)
   - `last_update_dt = current_timestamp()`

#### Delta Load (target istnieje):
1. **Schema Evolution** - automatycznie dodaje nowe kolumny
2. **Detekcja zmian**:
   - **Insert** (I) - nowe rekordy w source
   - **Update** (U) - zmienione dane
     - tracked columns changed → nowy `last_update_dt`
     - tylko untracked columns → stary `last_update_dt`
   - **Delete** (D) - rekordy usunięte ze source
   - **Reactivate** (U) - poprzednio usunięte, teraz wrócone
3. **Hash-based comparison** - MD5 hash dla wykrywania zmian
4. **History logging** (opcjonalnie) - audyt wszystkich zmian
5. **Merge do target** - aktualizacja tabeli docelowej

### 5. Zalety nowej implementacji

✅ **Prostota** - 3 linie zamiast 50+
✅ **Spójność** - jednolita składnia z innymi operation_type
✅ **Automatyzacja** - nie trzeba ręcznie sprawdzać istnienia tabeli
✅ **Konfiguracja** - wszystko w jednym miejscu (metadata_json)
✅ **Backward compatible** - stary kod nadal działa
✅ **Schema evolution** - automatyczne dodawanie kolumn
✅ **Audyt** - opcjonalna historia zmian
✅ **Performance** - hash-based change detection

## Przykłady użycia

Zobacz plik: `spark/examples.md`

## Pliki zmodyfikowane

1. **spark/data_processing_utilis_v2.ipynb**
   - Linia 205: Dodano backward compatibility
   - Po linii 542: Dodano nowy operation_type "Incremental Table" (361 linii kodu)

2. **spark/examples.md**
   - Dodano sekcję z nowym sposobem użycia
   - Oznaczono stary sposób jako LEGACY

3. **spark/CHANGELOG_v3.15.md**
   - Ten plik - dokumentacja zmian

## Migration Guide

### Dla istniejącego kodu używającego `create_incremental_table()`:

**Opcja 1: Nic nie rób** - stary kod nadal działa (backward compatible)

**Opcja 2: Migruj do nowej składni** (zalecane):

1. Zamień dwa metadata (full_load + delta_load) na jeden metadata_json
2. Przenieś parametry do sekcji `incremental_params`
3. Usuń wywołania `get_table_env_name()` - to jest automatyczne
4. Zamień `create_incremental_table()` na `create_table()`

## Testing

Przed użyciem w produkcji przetestuj:

1. Full Load nowej tabeli
2. Delta Load z:
   - Insertami
   - Update'ami
   - Delete'ami
   - Nowym kolumnami (schema evolution)
3. History logging (jeśli używane)
4. Retention policy (jeśli ustawione)

## Znane ograniczenia

- Wymaga Delta Lake format (`format: "delta"`)
- `id_key_column` musi być unique w source
- History table używa tego samego schematu co target

## Support

W przypadku problemów sprawdź:
1. Czy `id_key_column` jest poprawnie ustawiony
2. Czy tabela target ma kolumny `operation_type` i `last_update_dt`
3. Logi Spark - szczegółowe informacje o procesie
4. Liczby: Insert/Update/Delete są wyświetlane w output

---

**Autor**: Claude Code
**Data**: 2025-11-24
**Wersja**: 3.15
