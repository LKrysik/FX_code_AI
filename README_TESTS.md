# E2E Test Suite Documentation

## 📋 **Spis Treści**
- [Przegląd](#przegląd)
- [Szybki Start](#szybki-start)
- [Struktura Testów](#struktura-testów)
- [Uruchamianie Testów](#uruchamianie-testów)
- [Pisanie Nowych Testów](#pisanie-nowych-testów)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

---

## 🎯 **Przegląd**

System testów E2E (End-to-End) dla FX Code AI zgodny z zasadą **KISS** (Keep It Simple, Stupid).

### **Kluczowe Cechy:**
- ✅ **Jeden launcher** dla wszystkich testów: `python run_tests.py`
- ✅ **224 testy** pokrywające wszystkie API endpoints i kluczowe UI flows (213 API + 9 Frontend + 2 Integration)
- ✅ **3 kategorie**: API, Frontend, Integration
- ✅ **Automatyczne cleanup** po każdym teście
- ✅ **Parallel execution** (pytest-xdist)
- ✅ **Timeout 10 minut** dla całego suite

### **Stack Technologiczny:**
- **Backend**: pytest + FastAPI TestClient + httpx
- **Frontend**: Playwright (Python)
- **Fixtures**: JSON test data
- **Coverage**: pytest-cov

---

## 🚀 **Szybki Start**

### **1. Instalacja Zależności**

```bash
# Backend testing
pip install pytest pytest-asyncio pytest-xdist httpx pytest-timeout pytest-cov

# Frontend testing (Playwright)
pip install playwright
playwright install chromium
```

### **2. Uruchomienie Backendu i Frontendu**

Testy **wymagają** uruchomionego backendu i frontendu:

```powershell
# Windows PowerShell
.\start_all.ps1
```

Lub ręcznie:

```bash
# Terminal 1: Backend
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

### **3. Uruchomienie Wszystkich Testów**

```bash
python run_tests.py
```

---

## 📁 **Struktura Testów**

```
tests_e2e/
├── pytest.ini                  # Pytest configuration
├── conftest.py                 # Shared fixtures (auth, clients)
│
├── api/                        # Backend API tests (213 tests)
│   ├── conftest.py
│   ├── test_auth.py            # Authentication (13 tests)
│   ├── test_strategies.py      # Strategy CRUD (22 tests)
│   ├── test_sessions.py        # Session management (11 tests)
│   ├── test_health.py          # Health checks (17 tests)
│   ├── test_risk.py            # Risk management (14 tests)
│   ├── test_wallet_orders.py   # Wallet & Orders (10 tests)
│   ├── test_indicators.py      # Indicators (3 tests)
│   ├── test_results.py         # Results (9 tests)
│   ├── test_misc.py            # Misc endpoints (9 tests)
│   ├── test_data_analysis.py   # Data collection & analysis (25 tests) 🆕
│   ├── test_indicator_variants.py # Indicator variants CRUD (44 tests) 🆕
│   └── test_ops.py             # Operations dashboard (36 tests) 🆕
│
├── frontend/                   # Frontend UI tests (9 tests)
│   ├── conftest.py             # Playwright fixtures
│   ├── test_auth_flow.py       # Login/logout flows (5 tests)
│   └── test_dashboard.py       # Dashboard rendering (2 tests)
│
├── integration/                # Full E2E flows (2 tests)
│   └── test_complete_flow.py   # Complete user workflows
│
└── fixtures/                   # Test data (JSON)
    ├── strategies.json
    ├── users.json
    └── sessions.json
```

---

## 🎮 **Uruchamianie Testów**

### **Wszystkie Testy**

```bash
python run_tests.py
```

**Zawsze generuje**: `test_results.xml` (JUnit XML dla CI/CD)

### **Tylko API**

```bash
python run_tests.py --api
```

### **Tylko Frontend**

```bash
python run_tests.py --frontend
```

### **Tylko Integration**

```bash
python run_tests.py --integration
```

### **Szybkie Testy (Bez Slow)**

```bash
python run_tests.py --fast
```

### **Z Coverage**

```bash
python run_tests.py --coverage
```

**Generuje**:
- `htmlcov/index.html` - Interaktywny raport HTML
- `coverage.xml` - XML dla CI/CD

### **Z Raportem HTML**

```bash
python run_tests.py --html-report
```

**Generuje**: `test_report.html`

### **Verbose Mode (Debug)**

```bash
python run_tests.py --verbose
```

### **🔍 Detailed Mode - Maksymalna szczegółowość** 🆕

```bash
python run_tests.py --detailed
```

**Generuje** (z timestampem):
- `test_log_YYYYMMDD_HHMMSS.txt` - Pełne logi DEBUG
- `test_results_YYYYMMDD_HHMMSS.xml` - JUnit XML
- `test_report_YYYYMMDD_HHMMSS.html` - HTML report (jeśli `--html-report`)

**Zawiera**:
- ✅ Pełne tracebacki (nie skrócone)
- ✅ Wartości zmiennych lokalnych przy błędach
- ✅ DEBUG-level logi z całego systemu w pliku
- ✅ Szczegółowy output każdego testu
- ✅ Parallel execution (szybkie wykonanie)
- ✅ Timestampy dla wszystkich plików (nie nadpisuje poprzednich)

**Idealny do debugowania** failing testów!

**Uwaga**: Console logging (`--log-cli`) jest wyłączony w detailed mode ze względu na konflikt z parallel execution (`pytest-xdist -n auto`). Wszystkie logi są zapisywane do pliku `test_log_*.txt`.

### **Kombinacje**

```bash
# API tests with coverage and verbose
python run_tests.py --api --coverage --verbose

# Fast tests only with HTML report
python run_tests.py --fast --html-report

# All tests with all options
python run_tests.py --all --coverage --html-report --verbose

# 🆕 Detailed mode - maximum debugging
python run_tests.py --detailed

# 🆕 Detailed mode with all reports
python run_tests.py --detailed --html-report --coverage

# 🆕 Debug failing API test
python run_tests.py --api --detailed
```

---

## ✍️ **Pisanie Nowych Testów**

### **1. Test API (Backend)**

```python
# tests_e2e/api/test_my_feature.py

import pytest

@pytest.mark.api
def test_my_endpoint(authenticated_client):
    """Test my new endpoint"""
    response = authenticated_client.get("/api/my-endpoint")

    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert data["data"]["field"] == "expected_value"
```

### **2. Test Frontend (UI)**

```python
# tests_e2e/frontend/test_my_page.py

import pytest
from playwright.sync_api import Page, expect

@pytest.mark.frontend
def test_my_page_loads(authenticated_page: Page, test_config):
    """Test that my page loads"""
    authenticated_page.goto(f"{test_config['frontend_base_url']}/my-page")

    # Check for element
    expect(authenticated_page.locator('h1')).to_contain_text("My Page")

    # Click button
    authenticated_page.click('[data-testid="my-button"]')

    # Verify result
    expect(authenticated_page.locator('.result')).to_be_visible()
```

### **3. Test Integration (Full Flow)**

```python
# tests_e2e/integration/test_my_flow.py

import pytest

@pytest.mark.integration
@pytest.mark.slow
def test_complete_flow(authenticated_client, page, test_config):
    """Test complete user workflow"""
    # Step 1: API call
    response = authenticated_client.post("/api/action", json={...})
    assert response.status_code == 200

    # Step 2: UI verification
    page.goto(f"{test_config['frontend_base_url']}/results")
    expect(page.locator('.status')).to_contain_text("Success")
```

### **Markery (Pytest Markers)**

```python
@pytest.mark.api           # API test
@pytest.mark.frontend      # Frontend test
@pytest.mark.integration   # Integration test
@pytest.mark.slow          # Slow test (skipped with --fast)
@pytest.mark.auth          # Authentication test
@pytest.mark.strategies    # Strategy test
@pytest.mark.sessions      # Session test
@pytest.mark.health        # Health check test
```

### **Dostępne Fixtures**

```python
# API fixtures
api_client                 # FastAPI TestClient (no auth)
authenticated_client       # Authenticated TestClient
test_config               # Test configuration
valid_strategy_config     # Sample valid strategy
test_symbols              # Default test symbols

# Frontend fixtures
page                      # Playwright Page
authenticated_page        # Authenticated Page (logged in)
browser                   # Browser instance
context                   # Browser context

# Utility fixtures
assert_response_ok        # Helper to assert 200 OK
assert_response_error     # Helper to assert error response
load_fixture_json         # Load JSON fixture file
```

---

## 🔧 **CI/CD Integration**

### **GitHub Actions**

```yaml
# .github/workflows/test.yml

name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      questdb:
        image: questdb/questdb:latest
        ports:
          - 9000:9000
          - 8812:8812
          - 9009:9009

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-xdist playwright
          playwright install chromium

      - name: Start backend
        run: |
          python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 &
          sleep 10

      - name: Start frontend
        run: |
          cd frontend
          npm install
          npm run build
          npm start &
          sleep 5

      - name: Run E2E tests
        run: |
          python run_tests.py --all --coverage --html-report

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

      - name: Upload test report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-report
          path: test_report.html
```

---

## 🐛 **Troubleshooting**

### **Problem: Backend nie odpowiada**

```bash
# Sprawdź czy backend działa
curl http://localhost:8080/health

# Jeśli nie, uruchom ręcznie
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080
```

### **Problem: Frontend nie odpowiada**

```bash
# Sprawdź czy frontend działa
curl http://localhost:3000

# Jeśli nie, uruchom ręcznie
cd frontend
npm run dev
```

### **Problem: QuestDB nie działa**

```bash
# Sprawdź czy QuestDB działa
curl http://localhost:9000

# Jeśli nie, uruchom instalator
python database/questdb/install_questdb.py
```

### **Problem: Testy zawsze failują na auth**

```bash
# Sprawdź credentials w test_config
# Domyślne: username=admin, password=supersecret
# Zmień w .env jeśli używasz innych
```

### **Problem: Playwright nie działa**

```bash
# Reinstaluj browsers
playwright install chromium

# Lub wszystkie
playwright install
```

### **Problem: Testy są za wolne**

```bash
# Użyj parallel execution
pip install pytest-xdist

# pytest-xdist automatycznie wykryje liczbę CPU

# Użyj --fast aby pominąć slow testy
python run_tests.py --fast
```

### **Problem: Timeout errors**

```bash
# Zwiększ timeout w tests_e2e/pytest.ini:
timeout = 600  # 10 minutes

# Lub dla konkretnego testu:
@pytest.mark.timeout(120)
def test_slow_operation():
    ...
```

### **Debug Mode (Playwright)**

```python
# W tests_e2e/frontend/conftest.py zmień:
browser = p.chromium.launch(
    headless=False,  # Pokaż browser
    slow_mo=1000     # Spowolnij o 1s
)
```

---

## 📊 **Coverage Target**

| Kategoria | Target Coverage |
|-----------|----------------|
| API endpoints | 100% (wszystkie endpointy) |
| Critical paths | 100% (auth, sessions, strategies) |
| UI flows | 80% (kluczowe flows) |
| Integration | 60% (complete flows) |

---

## 📚 **Dalsze Kroki**

1. **Dodaj więcej testów frontend** gdy UI będzie stabilniejsze
2. **Dodaj performance tests** (pytest-benchmark)
3. **Dodaj load tests** (locust)
4. **Integruj z pre-commit hooks**

---

## 🆘 **Wsparcie**

- **Dokumentacja pytest**: https://docs.pytest.org/
- **Dokumentacja Playwright**: https://playwright.dev/python/
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/

---

## 📝 **Changelog**

### v1.0.0 (2025-01-XX)
- Initial E2E test suite
- 68 tests covering API, Frontend, Integration
- Single launcher (`run_tests.py`)
- Complete documentation

---

**Autor**: Claude Code AI
**Data**: 2025-01-XX
**Wersja**: 1.0.0
