# FX Agent AI

A cryptocurrency trading platform that provides **tools for traders** to create their own strategies - not ready-made solutions.

## Core Features

- **Visual Strategy Builder** - Create trading strategies without coding
- **Backtesting** - Test strategies on historical data (10x faster simulation)
- **Paper Trading** - Practice with virtual positions using real market data
- **Live Trading** - Execute real orders on MEXC Futures
- **Real-time Monitoring** - Live market data and position tracking
- **Pump & Dump Detection** - 22+ custom indicators for market analysis

---

## Quick Start

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| QuestDB | 9.1+ | Time-series database |

### One-Command Startup (Recommended)

Run the startup script from the project root:

```powershell
.\start_all.ps1
```

This script automatically:

1. Starts QuestDB and waits for it to be ready
2. Launches the backend server (FastAPI/Uvicorn)
3. Starts the frontend development server (Next.js)
4. Opens the application in your browser

### Service URLs

After startup, access the following:

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | <http://localhost:3000> | Main application UI |
| Backend API | <http://localhost:8080> | REST and WebSocket API |
| QuestDB Console | <http://localhost:9000> | Database management UI |

---

## Installation

### 1. Clone Repository

```powershell
git clone <repository-url>
cd FX_code_AI_v2
```

### 2. Setup Backend

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Setup Frontend

```powershell
cd frontend
npm install
cd ..
```

### 4. Install QuestDB

```powershell
python database/questdb/install_questdb.py
```

This installs QuestDB to `./questdb/` directory. Set the path in your environment:

```powershell
# Add to your PowerShell profile or .env
$env:QUESTDB_PATH = ".\questdb\bin\questdb.exe"
```

### 5. Configure Environment Variables

See [Environment Variables](#environment-variables) section below.

---

## Environment Variables

### Backend Configuration

Copy the example file and configure:

```powershell
copy .env.backend.example .env
```

**Required variables:**

| Variable | Description | How to Generate |
|----------|-------------|-----------------|
| `JWT_SECRET` | JWT signing secret (min 32 chars) | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `QUESTDB_PATH` | Path to QuestDB executable | Set after installation |
| `DEMO_PASSWORD` | Demo user password (bcrypt hash) | Run migration script |
| `TRADER_PASSWORD` | Trader user password (bcrypt hash) | Run migration script |
| `ADMIN_PASSWORD` | Admin user password (bcrypt hash) | Run migration script |

**Generate password hashes:**

```powershell
python scripts/migrate_passwords_to_bcrypt.py
```

### Default Users

After setup, these users are available:

| Username | Role | Access Level |
|----------|------|--------------|
| `demo` | Demo User | Read-only, paper trading only |
| `trader` | Trader | Full trading access |
| `admin` | Administrator | Full system access |

Passwords are set via environment variables (`DEMO_PASSWORD`, `TRADER_PASSWORD`, `ADMIN_PASSWORD`).

### Frontend Configuration

Copy the example file:

```powershell
copy frontend\.env.example frontend\.env.local
```

**Frontend variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8080` | Backend API URL |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8080` | WebSocket URL |
| `NEXT_PUBLIC_ENABLE_DEBUG_MODE` | `false` | Enable debug features |
| `NEXT_PUBLIC_ENABLE_MOCK_DATA` | `true` | Use mock data |

---

## MEXC Exchange Setup

For live trading, configure your MEXC API credentials:

### 1. Create API Keys

1. Log in to [MEXC](https://www.mexc.com/)
2. Navigate to API Management
3. Create new API key with **Futures Trading** permissions
4. Save your API Key and Secret securely

### 2. Configure Environment

Add to your `.env` file:

```env
# MEXC Exchange Configuration
EXCHANGE__MEXC_API_KEY=your_api_key_here
EXCHANGE__MEXC_API_SECRET=your_api_secret_here
EXCHANGE__MEXC_PAPER_TRADING=true

# Enable live trading (set to true only when ready)
TRADING__LIVE_TRADING_ENABLED=false
```

### 3. Security Notes

- Never commit `.env` files to version control
- Start with paper trading (`MEXC_PAPER_TRADING=true`)
- Only enable live trading after thorough testing

---

## Manual Startup

If you prefer to start services individually:

### 1. Start QuestDB

```powershell
# Windows - run QuestDB executable
questdb.exe
```

Wait until QuestDB is ready (check <http://localhost:9000>).

### 2. Start Backend

```powershell
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload
```

### 3. Start Frontend

```powershell
cd frontend
npm run dev
```

---

## AI Agent Startup (Claude Code)

When Claude Code agent starts services, it must capture process output to monitor for errors and status. The key is using `run_in_background: true` parameter which keeps the process attached to the agent's session.

### Important: How Agent Process Monitoring Works

```
┌─────────────────────────────────────────────────────────────────┐
│ WRONG: Start-Process / New Window                               │
│ Agent → Start-Process python ... → New Window opens → Agent     │
│                                    loses connection, can't see  │
│                                    output or errors             │
├─────────────────────────────────────────────────────────────────┤
│ CORRECT: run_in_background: true                                │
│ Agent → Bash(run_in_background:true) → Process runs attached    │
│         ↓                              ↓                        │
│         TaskOutput(task_id) ←──────── Agent can read output,    │
│                                        see errors, monitor      │
└─────────────────────────────────────────────────────────────────┘
```

### 1. Start QuestDB

**Agent command** (use `run_in_background: true`):
```powershell
# Using environment variable (recommended)
& $env:QUESTDB_PATH

# Or with explicit path
& ".\questdb\bin\questdb.exe"
```

**Health check** (run after ~5 seconds):
```powershell
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9000" -TimeoutSec 3 -UseBasicParsing
    Write-Host "QuestDB ready (Status: $($response.StatusCode))"
} catch {
    Write-Host "QuestDB not ready: $($_.Exception.Message)"
}
```

### 2. Start Backend

**Agent command** (use `run_in_background: true`):
```powershell
python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload
```

The agent sees all uvicorn output directly: startup messages, requests, errors.

**Health check**:
```powershell
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -TimeoutSec 5 -UseBasicParsing
    Write-Host "Backend ready: $($response.Content)"
} catch {
    Write-Host "Backend not ready: $($_.Exception.Message)"
}
```

### 3. Start Frontend

**Agent command** (use `run_in_background: true`):
```powershell
Set-Location frontend; npm run dev
```

The agent sees Next.js compilation output, warnings, and errors directly.

**Health check**:
```powershell
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 5 -UseBasicParsing
    Write-Host "Frontend ready (Status: $($response.StatusCode))"
} catch {
    Write-Host "Frontend not ready: $($_.Exception.Message)"
}
```

### Agent Workflow Example

Here's how Claude Code agent should start the full stack:

```
1. Start QuestDB (run_in_background: true)
   ↓
2. Use TaskOutput to monitor QuestDB startup
   ↓
3. Run health check for port 9000
   ↓
4. Start Backend (run_in_background: true)
   ↓
5. Use TaskOutput to watch for "Uvicorn running on..."
   ↓
6. Run health check for /health endpoint
   ↓
7. Start Frontend (run_in_background: true)
   ↓
8. Use TaskOutput to watch for "Ready in..."
   ↓
9. All services running - agent can monitor all three via TaskOutput
```

### Checking All Services Status

```powershell
$services = @(
    @{Name="QuestDB"; Port=9000; Url="http://localhost:9000"},
    @{Name="Backend"; Port=8080; Url="http://localhost:8080/health"},
    @{Name="Frontend"; Port=3000; Url="http://localhost:3000"}
)

foreach ($svc in $services) {
    $portOpen = Get-NetTCPConnection -LocalPort $svc.Port -ErrorAction SilentlyContinue
    if ($portOpen) {
        Write-Host "$($svc.Name): RUNNING on port $($svc.Port)" -ForegroundColor Green
    } else {
        Write-Host "$($svc.Name): NOT RUNNING" -ForegroundColor Red
    }
}
```

### Stopping Services

```powershell
# Stop service on specific port
$port = 8080  # Change as needed: 9000 (QuestDB), 8080 (Backend), 3000 (Frontend)
$processId = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue).OwningProcess | Select-Object -First 1
if ($processId) {
    Stop-Process -Id $processId -Force
    Write-Host "Stopped process on port $port (PID: $processId)"
} else {
    Write-Host "No process found on port $port"
}
```

### Reading Background Process Output

When agent has started a process with `run_in_background: true`:

1. **TaskOutput (blocking)** - Waits for process output:
   ```
   TaskOutput(task_id, block=true, timeout=30000)
   ```

2. **TaskOutput (non-blocking)** - Checks current output without waiting:
   ```
   TaskOutput(task_id, block=false)
   ```

3. **KillShell** - Stops a background process:
   ```
   KillShell(shell_id)
   ```

### Common Issues Agent Should Watch For

| Output Pattern | Meaning | Action |
|----------------|---------|--------|
| `Address already in use` | Port conflict | Stop existing process first |
| `ModuleNotFoundError` | Missing dependency | Run `pip install -r requirements.txt` |
| `Connection refused` to QuestDB | Database not running | Start QuestDB first |
| `ENOENT` | File/command not found | Check paths and installation |
| `error TS` | TypeScript error | Check frontend code |
| `500 Internal Server Error` | Backend error | Check TaskOutput for stack trace |

---

## Testing

### Backend Tests

```powershell
# Activate virtual environment first
.\.venv\Scripts\Activate.ps1

# Run all tests with coverage
pytest

# Run specific test categories
pytest -m unit          # Unit tests only (no external dependencies)
pytest -m integration   # Integration tests
pytest -m api           # API endpoint tests
pytest -m e2e           # End-to-end tests
pytest -m fast          # Fast tests only

# Run tests for specific modules
pytest tests/test_strategies.py
pytest tests/test_indicators.py

# Run with verbose output
pytest -v --tb=long

# Generate HTML coverage report
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

**Available test markers:**

| Marker | Description |
|--------|-------------|
| `unit` | Unit tests (no external dependencies) |
| `integration` | Full integration tests |
| `api` | API endpoint tests |
| `e2e` | End-to-end tests |
| `database` | Tests requiring QuestDB |
| `fast` | Fast running tests |
| `slow` | Slow running tests |
| `auth` | Authentication tests |
| `strategies` | Strategy CRUD tests |

### Frontend Tests

```powershell
cd frontend

# Run all tests
npm test

# Run tests in watch mode (re-run on file changes)
npm run test:watch

# Run tests with coverage report
npm run test:coverage

# Run E2E tests with Playwright
npx playwright test

# Run E2E tests with UI
npx playwright test --ui
```

### Code Quality

```powershell
# Backend linting
ruff check src/
black --check src/

# Frontend linting
cd frontend
npm run lint
npm run type-check
```

---

## Project Structure

```
FX_code_AI_v2/
├── src/                    # Backend (Python/FastAPI)
│   ├── api/                # REST/WebSocket endpoints
│   ├── application/        # Use cases, orchestrators
│   ├── domain/             # Business logic, models
│   ├── infrastructure/     # External adapters
│   └── trading/            # Trading execution
├── frontend/               # Frontend (Next.js/TypeScript)
│   └── src/
│       ├── app/            # Next.js App Router pages
│       ├── components/     # React components (85+)
│       ├── stores/         # Zustand state stores
│       └── services/       # API services
├── tests/                  # Backend tests
├── database/               # Database scripts and migrations
├── config/                 # Configuration files
├── docs/                   # Documentation
├── scripts/                # Utility scripts
└── start_all.ps1           # One-command startup script
```

---

## Technology Stack

### Backend

- **Framework:** FastAPI
- **Language:** Python 3.10+
- **Architecture:** Clean Architecture + DDD
- **Database:** QuestDB (time-series)
- **Real-time:** WebSockets
- **Validation:** Pydantic
- **Auth:** JWT + bcrypt

### Frontend

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **UI Library:** MUI (Material-UI) v5
- **State:** Zustand
- **Charts:** Recharts, uPlot, Lightweight Charts
- **Flow Editor:** ReactFlow 11.10+
- **Testing:** Jest, Playwright

---

## Available Pages

| Route | Purpose |
|-------|---------|
| `/dashboard` | Main trading dashboard |
| `/trading` | Live trading interface |
| `/paper` | Paper trading (simulation) |
| `/backtesting` | Strategy backtesting |
| `/strategy-builder` | Visual strategy editor |
| `/indicators` | Indicator configuration |
| `/session-history` | Trading history |

---

## Documentation

| Document | Description |
|----------|-------------|
| [Strategy Flow](docs/STRATEGY_FLOW.md) | How strategies, indicators, and signals work together |
| [WebSocket API](docs/WEBSOCKET.md) | Real-time API documentation |
| [Database Schema](docs/SCHEMA.md) | QuestDB table definitions |
| [Coding Standards](docs/CODING_STANDARDS.md) | Code style guidelines |

---

## API Documentation

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trading/positions` | GET | Query live positions |
| `/api/trading/orders` | GET | Query live orders |
| `/api/paper/*` | * | Paper trading operations |
| `/api/dashboard/*` | * | Dashboard data |
| `/api/signals/*` | * | Signal history |
| `/api/indicators/*` | * | Indicator management |
| `/api/strategies/*` | * | Strategy CRUD |

### WebSocket

Real-time streaming available for:

- Market data
- Position updates
- Signal notifications
- State machine transitions

---

## Troubleshooting

### QuestDB not starting

Verify QuestDB is installed:

```powershell
python database/questdb/install_questdb.py
```

### Port already in use

The startup script automatically kills existing processes on port 3000. For other ports:

```powershell
# Find process using port
netstat -ano | findstr :8080

# Kill process by PID
taskkill /PID <pid> /F
```

### Backend connection issues

Ensure QuestDB is running before starting the backend. The startup script handles this automatically.

### Authentication errors

If you see "JWT_SECRET must be set":

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Add output to .env as JWT_SECRET=<value>
```

If you see "credentials must be set via environment variables":

```powershell
python scripts/migrate_passwords_to_bcrypt.py
# Copy generated hashes to .env
```

---

## Contributing

1. Create a feature branch from `main`
2. Make your changes following [Coding Standards](docs/CODING_STANDARDS.md)
3. Write tests for new functionality
4. Run tests: `pytest` and `npm test`
5. Run linters: `ruff check src/` and `npm run lint`
6. Submit a pull request

---

## License

Proprietary - All rights reserved.
