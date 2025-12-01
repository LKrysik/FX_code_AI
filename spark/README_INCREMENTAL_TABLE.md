# Incremental Table - Quick Start Guide

## 🎯 Co to jest?

Nowy `operation_type: "Incremental Table"` integruje funkcjonalność `create_incremental_table()` bezpośrednio w system `metadata_json`.

**Przed**: 50+ linii kodu, 2 metadane, ręczne zarządzanie
**Teraz**: 3 linie kodu, 1 metadata, wszystko automatyczne

---

## 🚀 Szybki start

### Podstawowe użycie:

```python
metadata_json = '''
{
    "target_table": {
        "target_schema": "output",
        "target_table": "my_table",
        "format": "delta",
        "operation_type": "Incremental Table",
        "incremental_params": {
            "id_key_column": "id"
        }
    },
    "source_tables": [
        {"schema": "process", "table": "my_source", "view": "source"}
    ],
    "env": "'''+ str(ENV) +'''",
    "project_name": "'''+ str(PROJECT_NAME) +'''"
}
'''

make_env_tables(metadata_json)
df = spark.sql("SELECT * FROM source")
df_result = create_table(metadata_json, df)
```

### Z historią zmian:

```python
"incremental_params": {
    "id_key_column": "id",
    "log_history": true,
    "history_table_name": "my_table_history",
    "history_retention_days": 30
}
```

### Z wykluczeniem kolumn:

```python
"incremental_params": {
    "id_key_column": "id",
    "excluded_columns_for_hash": ["last_modified", "etl_timestamp"]
}
```

---

## 📋 Parametry

| Parametr | Wymagane | Domyślnie | Opis |
|----------|----------|-----------|------|
| `id_key_column` | ✅ Tak | - | Klucz główny |
| `included_columns_for_hash` | Nie | null | Kolumny do śledzenia (null = wszystkie) |
| `excluded_columns_for_hash` | Nie | null | Kolumny ignorowane |
| `log_history` | Nie | false | Czy logować zmiany |
| `history_table_name` | Nie | null | Nazwa tabeli historii |
| `history_retention_days` | Nie | null | Retencja historii (dni) |
| `ignore_new_columns_as_change` | Nie | true | Czy nowe kolumny = Update |

---

## 🔄 Jak to działa?

### Full Load (pierwsza próba - target nie istnieje):
```
1. Sprawdza czy target istnieje → NIE
2. Tworzy tabelę z danymi z source_tables
3. Dodaje kolumny: operation_type='I', last_update_dt
```

### Delta Load (kolejne próby - target istnieje):
```
1. Sprawdza czy target istnieje → TAK
2. Dodaje nowe kolumny do target (schema evolution)
3. Porównuje source vs target (hash-based)
4. Wykrywa zmiany:
   ├─ INSERT (I)      - nowe w source
   ├─ UPDATE (U)      - zmienione dane
   ├─ DELETE (D)      - usunięte ze source
   └─ REACTIVATE (U)  - poprzednio usunięte, teraz wrócone
5. Opcjonalnie loguje do history table
6. Merge'uje zmiany do target
```

---

## 📊 Output

### Kolumny dodane do target:
- `operation_type` (string): 'I', 'U', lub 'D'
- `last_update_dt` (timestamp): Kiedy rekord został zmieniony

### Kolumny w history table (jeśli `log_history=true`):
- Wszystkie kolumny z target
- `_audit_timestamp` - kiedy zmiana została zalogowana
- `_audit_operation` - typ operacji (Insert/Update/Delete/Reactivate)

---

## ✅ Zalety

- ✅ **Prostota**: 3 linie zamiast 50+
- ✅ **Spójność**: Jak inne operation_type
- ✅ **Automatyzacja**: Nie trzeba sprawdzać czy target istnieje
- ✅ **Konfiguracja**: Wszystko w metadata_json
- ✅ **Backward compatible**: Stary kod działa (`opertation_type`)
- ✅ **Schema evolution**: Automatyczne dodawanie kolumn
- ✅ **Audyt**: Opcjonalna historia zmian
- ✅ **Performance**: Hash-based change detection

---

## 📚 Dokumentacja

- **[examples.md](examples.md)** - Przykłady użycia (stary vs nowy sposób)
- **[CHANGELOG_v3.15.md](CHANGELOG_v3.15.md)** - Szczegółowy changelog
- **[test_incremental_table.py](test_incremental_table.py)** - Skrypty testowe

---

## 🐛 Troubleshooting

### Problem: "Incremental Table operation requires 'id_key_column'"
**Rozwiązanie**: Dodaj `id_key_column` do `incremental_params`

### Problem: Wszystkie rekordy są Update'ami
**Rozwiązanie**: Sprawdź czy `id_key_column` jest poprawny i unique

### Problem: Nowe kolumny powodują Update wszystkich rekordów
**Rozwiązanie**: Ustaw `ignore_new_columns_as_change: true` (domyślnie już jest)

### Problem: Historia rośnie za szybko
**Rozwiązanie**: Ustaw `history_retention_days` (np. 30, 90)

---

## 🔄 Migracja ze starego kodu

### Przed (50+ linii):
```python
metadata_full_load = '...'
metadata_delta_load = '...'
target_table_name = get_table_env_name(...)
source_table_name = get_table_env_name(...)
history_table_name = get_table_env_name(...)

df = create_incremental_table(
    id_key_column="id",
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

### Po (3 linie):
```python
metadata_json = '{... "operation_type": "Incremental Table" ...}'
make_env_tables(metadata_json)
df = create_table(metadata_json, dataframe)
```

---

## 📞 Support

W przypadku pytań lub problemów:
1. Sprawdź [examples.md](examples.md)
2. Zobacz [CHANGELOG_v3.15.md](CHANGELOG_v3.15.md)
3. Uruchom [test_incremental_table.py](test_incremental_table.py)

---

**Autor**: Claude Code
**Data**: 2025-11-24
**Wersja**: 3.15
