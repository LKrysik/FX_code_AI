# 🔍 ANALIZA ARCHITEKTONICZNA - PROBLEM 1: Strategy Builder Persistence

## STATUS: ⚠️ WYMAGA DECYZJI ARCHITEKTONICZNEJ

---

## 📋 PODSUMOWANIE WYKONAWCZE

**Problem**: Strategy Builder API (Visual Graph Strategies) przechowuje blueprinty tylko w pamięci (in-memory dict), tracąc wszystkie dane po restarcie serwera.

**Wpływ**: 🔴 KRYTYCZNY - Frontend zakłada że dane są persystowane (używa `id`, `created_at`, `updated_at`), ale backend ich nie zapisuje.

**Root Cause**: Architektura NOT CLEAR - istnieją DWA osobne systemy strategii bez jasno zdefiniowanej relacji.

---

## 🏗️ ODKRYTA ARCHITEKTURA

### SYSTEM 1: StrategyStorage (`strategy_storage.py`)
```
Type: 5-Section Strategies (JSON/YAML)
Format: { s1_signal, z1_entry, o1_cancel, ze1_close, emergency_exit }
Storage: ✅ JSON files + atomic operations + backups
Frontend: strategiesApi.ts → StrategyBuilder5Section.tsx
Use Case: EXECUTABLE strategies (for trading engine)
Status: ✅ DZIAŁA POPRAWNIE
```

### SYSTEM 2: StrategyBlueprintsAPI (`strategy_blueprints.py`)
```
Type: Visual Graph Strategies (nodes + edges)
Format: { nodes: [], edges: [], metadata: {} }
Storage: ❌ In-memory TYLKO (self.blueprints = {})
Frontend: strategyBuilderApi.ts → strategy-builder/page.tsx
Use Case: DESIGN-ONLY tool (visual strategy builder)
Status: ⚠️ BRAK PERSISTENCE
```

### POWIĄZANIA
```
┌────────────────────────────────────────────────────────────┐
│ Frontend Request                                            │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  POST /api/strategy-blueprints/                            │
│  Body: { name: "My Strategy", graph: { nodes, edges } }   │
│                                                             │
│  ↓                                                          │
│                                                             │
│  StrategyBlueprintsAPI.blueprints[uuid] = blueprint  ← ❌  │
│                  (in-memory dict)                           │
│                                                             │
│  ↓ Server restart                                          │
│                                                             │
│  ❌ ALL DATA LOST                                           │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## ⚠️ PROBLEMY ARCHITEKTONICZNE

### 1. **Duplikacja Konceptów**
Dwa osobne systemy dla strategii bez jasno zdefiniowanego API kontraktu:
- StrategyStorage vs StrategyBlueprintsAPI
- JSON files vs In-memory dict
- 5-section format vs Graph format

**Pytanie**: Czy to jest feature (różne typy strategii) czy bug (brak spójności)?

### 2. **Brak Integracji**
`migrate_yaml_to_graph()` w strategy_blueprints.py NIE używa StrategyStorage:
```python
# strategy_blueprints.py:177
def migrate_yaml_to_graph(self, yaml_config: Dict[str, Any]) -> StrategyGraph:
    # Tworzy graf z YAML, ale NIE integruje się z StrategyStorage!
    # Czy to powinno używać StrategyStorage.load()?
```

### 3. **Table strategy_templates Nieużywana**
QuestDB ma tabelę `strategy_templates` ale:
- ❌ Brak API endpoints
- ❌ Nie jest używana przez Strategy Builder
- ❌ Nie jest używana przez StrategyStorage
- ❓ Jaki jest jej cel?

### 4. **Frontend Assumptions vs Backend Reality**
```typescript
// frontend/src/services/strategyBuilderApi.ts
export interface StrategyBlueprint {
  id?: string;              // ← Generowany przez backend
  created_at?: string;      // ← ❌ Tracony po restarcie!
  updated_at?: string;      // ← ❌ Tracony po restarcie!
}
```

---

## 🎯 ZWERYFIKOWANE ZAŁOŻENIA

### ✅ Założenie 1: "Frontend wymaga persistence"
**PRAWDA** - Frontend używa:
- `listBlueprints()` - oczekuje zachowanych danych
- `updateBlueprint(id)` - wymaga trwałego ID
- `created_at` / `updated_at` - timestamp metadata

### ✅ Założenie 2: "Są to dwa różne systemy"
**PRAWDA** - Według dokumentacji:
- StrategyBuilder = Design-only tool (Sprint 5)
- StrategyStorage = Executable strategies

### ❌ Założenie 3: "Można użyć strategy_templates table"
**FAŁSZ** - Tabela istnieje ale:
- Nie pasuje do formatu StrategyGraph
- Brak API endpoints
- Nie jest używana w kodzie

---

## 💡 REKOMENDACJE

### OPCJA A: Rozszerz StrategyBlueprintsAPI o QuestDB persistence

**Pro:**
- Proste rozwiązanie
- Wykorzystuje istniejącą architekturę
- Minimal code changes

**Con:**
- Duplicates storage logic (vs StrategyStorage)
- Nie rozwiązuje problemu duplikacji systemów

### OPCJA B: Zunifikuj oba systemy pod jednym API

**Pro:**
- Single source of truth
- Eliminuje duplikację
- Jasna architektura

**Con:**
- Major refactoring
- Breaking changes w frontend
- Wysokie ryzyko

### OPCJA C: Dedicated BlueprintsStorage service

**Pro:**
- Clean separation of concerns
- Reusable storage abstraction
- Testable

**Con:**
- Więcej kodu
- Trzeci system storage

---

## 🚦 DECYZJA WYMAGANA

**Pytania do stakeholdera:**

1. Czy Visual Graph Strategies i 5-Section Strategies powinny być **unifikowane** czy **osobne**?
2. Czy migrate_yaml_to_graph() powinno działać z StrategyStorage?
3. Jaki jest cel tabeli `strategy_templates` w QuestDB?
4. Czy dopuszczamy 3 systemy storage (Files, In-memory, QuestDB)?

---

## 📊 WPŁYW NA SYSTEM

### Powiązane moduły:
- ✅ `src/api/strategy_blueprints.py` - **GŁÓWNY PROBLEM**
- ✅ `src/api/unified_server.py` - Dependency injection
- ✅ `src/infrastructure/container.py` - Factory method
- ⚠️ `src/domain/services/strategy_storage.py` - Potencjalna integracja?
- ⚠️ `database/questdb/migrations/001_create_initial_schema.sql` - Table strategy_templates
- ✅ `frontend/src/services/strategyBuilderApi.ts` - Frontend API
- ✅ `frontend/src/stores/graphStore.ts` - State management

### Ryzyko zmian:
- **NISKIE** jeśli dodamy tylko persistence (Opcja A)
- **WYSOKIE** jeśli unifikujemy systemy (Opcja B)

---

## 🎬 NASTĘPNE KROKI (Conditional on decision)

Jeśli OPCJA A (Recommended for now):
1. Dodać `BlueprintsPersistenceService` z QuestDB backend
2. Rozszerzyć tabelę `strategy_blueprints` (nowa)
3. Update `StrategyBlueprintsAPI` do użycia persistence service
4. Dodać migrację danych (in-memory → QuestDB)
5. Testy integracyjne

Jeśli OPCJA B (Long-term):
1. Zdefiniować zunifikowany StrategyModel
2. Refactor obu systemów do wspólnego API
3. Deprecate stary format
4. Multi-phase migration plan

---

**CONCLUSION**: System ma NIEJASNĄ ARCHITEKTURĘ dla strategii. Wymaga DECYZJI czy to feature (dwa różne typy) czy bug (brak spójności).

