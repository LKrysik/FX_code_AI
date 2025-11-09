# Quick Start - E2E Tests

## 1️⃣ **Instalacja (1 minuta)**

```bash
# Install test dependencies
pip install -r test_requirements.txt

# Install Playwright browsers
playwright install chromium
```

## 2️⃣ **Uruchomienie Środowiska (2 minuty)**

```powershell
# Start backend + frontend + QuestDB
.\start_all.ps1
```

**Weryfikacja:**
- Backend: http://localhost:8080/health → "healthy"
- Frontend: http://localhost:3000 → strona logowania
- QuestDB: http://localhost:9000 → web UI

## 3️⃣ **Uruchomienie Testów**

### **Wszystkie testy:**
```bash
python run_tests.py
```

### **Tylko API:**
```bash
python run_tests.py --api
```

### **Tylko Frontend:**
```bash
python run_tests.py --frontend
```

### **Z coverage:**
```bash
python run_tests.py --coverage
```

### **🔥 Z pełnymi logami (DETAILED MODE):** 🆕
```bash
python run_tests.py --detailed
```

**Generuje:**
- `test_log_TIMESTAMP.txt` - Pełne logi DEBUG (wszystkie szczegóły)
- `test_results_TIMESTAMP.xml` - JUnit XML
- Pełne tracebacki z wartościami zmiennych lokalnych
- Szybkie wykonanie (parallel execution z pytest-xdist)

**Idealny do debugowania failing testów!**

## 4️⃣ **Sprawdzenie Wyników**

✅ **Success:**
```
================== Test Run Summary ==================
✓ All tests passed! ✓
Coverage report: htmlcov/index.html
```

❌ **Failure:**
```
================== Test Run Summary ==================
✗ Tests failed with exit code 1
Run with --verbose for more details
```

## 🐛 **Troubleshooting**

| Problem | Rozwiązanie |
|---------|-------------|
| Backend nie działa | `curl http://localhost:8080/health` → Sprawdź czy odpowiada |
| Frontend nie działa | `curl http://localhost:3000` → Sprawdź czy odpowiada |
| QuestDB nie działa | `python database/questdb/install_questdb.py` |
| Testy za wolne | `python run_tests.py --fast` |
| Test failuje - potrzebuję szczegółów | `python run_tests.py --detailed` → Zobacz `test_log_*.txt` 🆕 |

## 📚 **Pełna Dokumentacja**

Zobacz: [README_TESTS.md](README_TESTS.md)

---

**Czas instalacji:** ~3 minuty
**Czas pierwszego uruchomienia:** ~2 minuty
**Liczba testów:** 224 (API: 213, Frontend: 9, Integration: 2)
**Pokrycie:** 97+ endpointów API + UI flows (wszystkie routery: data_analysis, indicators, ops)
