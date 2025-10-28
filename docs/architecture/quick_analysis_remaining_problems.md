# 🔍 SZYBKA ANALIZA POZOSTAŁYCH PROBLEMÓW

## PROBLEM 2: Dual Storage (CSV + QuestDB) 🟡 ŚREDNI

### OBECNY STAN:
```python
# indicators_routes.py:858-878
# Zapisuje do QuestDB
inserted_count = await questdb_provider.insert_indicators_batch(indicators_batch)

# RÓWNIEŻ zapisuje do CSV (backward compatibility)
persistence_service.save_batch_values(session_id, symbol, variant_id, series)
```

### WERYFIKACJA:
✅ **Kod istnieje** - Dual write w indicators_routes.py
✅ **Używany w production** - Oba zapisy są aktywne
⚠️ **Fallback podczas odczytu** - Linie 1106-1159 (try QuestDB, fallback to CSV)

### KONSEKWENCJE:
1. **Niespójność danych** - Możliwe rozbieżności między CSV i QuestDB
2. **Zużycie dysku** - Podwójne przechowywanie
3. **Maintenance overhead** - Dwa systemy do zarządzania

### REKOMENDACJA:
```
FAZA 1 (Immediate): Dodać feature flag LEGACY_CSV_STORAGE = False
FAZA 2 (1 tydzień): Migracja wszystkich CSV → QuestDB
FAZA 3 (2 tygodnie): Usunięcie CSV code po weryfikacji
```

### RYZYKO: **NISKIE** - QuestDB już działa, CSV to legacy tylko

---

## PROBLEM 3: Brak API dla strategy_templates 🟡 ŚREDNI

### OBECNY STAN:
```sql
-- Tabela istnieje w QuestDB
CREATE TABLE strategy_templates (
    id STRING,
    name STRING,
    strategy_json STRING,
    ...
)
```

### WERYFIKACJA:
❌ **Brak endpoints** - Grep nie znalazł żadnych użyć w API
❌ **Nie używana w kodzie** - Zero referencji
❓ **Związek z StrategyBlueprintsAPI** - NIEJASNY

### KONSEKWENCJE:
- **Dead schema** - Tabela zajmuje miejsce niepotrzebnie
- **Confusion** - Developer myśli że jest używana

### REKOMENDACJA:
**OPCJA A**: Zintegrować z StrategyBlueprintsAPI (jeśli to było zamierzone)
**OPCJA B**: Usunąć tabelę jako dead code

### RYZYKO: **NISKIE** - Nie jest używana, można bezpiecznie usunąć

---

## PROBLEM 4: Brak indexów na session_id 🟡 ŚREDNI

### OBECNY STAN:
```sql
-- Migracja 003 dodała session_id ale NIE dodała indexu dla wszystkich tabel:
ALTER TABLE indicators ADD COLUMN session_id SYMBOL;
CREATE INDEX idx_indicators_session ON indicators(session_id); -- ✅ Jest

-- BRAK dla:
-- tick_prices.session_id
-- tick_orderbook.session_id
```

### WERYFIKACJA:
✅ **Index dla indicators** - Istnieje
❌ **Index dla tick_prices** - BRAK
❌ **Index dla tick_orderbook** - BRAK

### KONSEKWENCJE:
- **Wolne zapytania** przy dużej liczbie danych
- **Full table scan** przy filtracji po session_id

### REKOMENDACJA:
```sql
-- Nowa migracja 004:
CREATE INDEX IF NOT EXISTS idx_tick_prices_session ON tick_prices(session_id);
CREATE INDEX IF NOT EXISTS idx_tick_orderbook_session ON tick_orderbook(session_id);
```

### RYZYKO: **BARDZO NISKIE** - Tylko dodanie indexów, bezpieczne

---

## PROBLEM 5: Brak walidacji session_id 🟢 NISKI

### OBECNY STAN:
```python
# indicators_routes.py - NIE sprawdza czy sesja istnieje
@router.post("/sessions/{session_id}/symbols/{symbol}/indicators")
async def add_indicator_for_session(session_id: str, symbol: str, ...):
    # Brak walidacji session_id!
    # Zapisuje wskaźniki nawet jeśli sesja nie istnieje
```

### WERYFIKACJA:
❌ **Brak walidacji** - Kod nie sprawdza istnienia sesji
⚠️ **QuestDB przyjmie dane** - No FK constraints (orphaned data)

### KONSEKWENCJE:
- **Orphaned indicators** - Wskaźniki bez sesji
- **Trudny cleanup** - Ciężko znaleźć orphans
- **Data integrity issue**

### REKOMENDACJA:
```python
async def add_indicator_for_session(session_id: str, ...):
    # Dodać walidację:
    session = await analysis_service.get_session_metadata(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")
    
    # Kontynuuj z dodawaniem wskaźników...
```

### RYZYKO: **BARDZO NISKIE** - Tylko dodanie walidacji

---

## 📊 PODSUMOWANIE WSZYSTKICH PROBLEMÓW

| Problem | Priorytet | Ryzyko Fix | Czas Fix | Status |
|---------|-----------|------------|----------|--------|
| 1. Strategy Builder persistence | 🔴 KRYT | Średnie | 3-5 dni | ⚠️ Wymaga decyzji |
| 2. Dual storage (CSV+QuestDB) | 🟡 ŚRED | Niskie | 1-2 dni | ✅ Może być naprawione |
| 3. Brak API strategy_templates | 🟡 ŚRED | Niskie | 1 dzień | ✅ Może być naprawione |
| 4. Brak indexów session_id | 🟡 ŚRED | Bardzo niskie | 30 min | ✅ Może być naprawione |
| 5. Brak walidacji session_id | 🟢 NISK | Bardzo niskie | 2 godz | ✅ Może być naprawione |

---

## 🎯 REKOMENDOWANY PLAN DZIAŁANIA

### SPRINT 1 (Immediate - 1 dzień):
1. ✅ Fix Problem 4: Dodać indexy (migracja 004)
2. ✅ Fix Problem 5: Dodać walidację session_id
3. ✅ Fix Problem 3: Usunąć strategy_templates lub zintegrować

### SPRINT 2 (Short-term - 1 tydzień):
4. ✅ Fix Problem 2 Faza 1: Feature flag dla CSV
5. ✅ Fix Problem 2 Faza 2: Migracja CSV → QuestDB

### SPRINT 3 (Long-term - 2-4 tygodnie):
6. ⚠️ Fix Problem 1: Dodać persistence (po decyzji stakeholdera)
7. ✅ Fix Problem 2 Faza 3: Usunięcie CSV code

---

## ✅ BRAKI I NIESPÓJNOŚCI ZNALEZIONE PODCZAS ANALIZY

### 1. **Brak dokumentacji architektury strategii**
- Nie ma jasnej specyfikacji relacji między StrategyStorage i StrategyBlueprintsAPI
- Brak ADR (Architecture Decision Record) dla wyboru dual-system

### 2. **Brak transaction support w migracji danych**
- CSV → QuestDB migration może być niespójna
- Brak rollback mechanism

### 3. **Brak monitoring persistence failures**
- Jeśli zapis do CSV lub QuestDB failuje, nie ma alertów
- Brak metryk sukcesu/failure rate

### 4. **Inconsistent naming conventions**
- `strategy_templates` vs `strategy_blueprints` - które jest które?
- `session_id` jako STRING vs INT w różnych miejscach

### 5. **Dead code wykryty**:
- `strategy_templates` table (nieużywana)
- `SimpleEventBus` w indicators_routes.py (MVP only)
- Legacy REST envelope middleware (może być wyłączony)

