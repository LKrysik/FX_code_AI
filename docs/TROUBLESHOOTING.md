# Troubleshooting Guide

Common issues and their solutions for FX Agent AI.

---

## Quick Diagnostics

Before diving into specific errors, run these checks:

```bash
# Check Python environment
python --version          # Should be 3.10+
pip list | grep -E "fastapi|uvicorn|pydantic"

# Check Node.js
node --version            # Should be 18+
npm --version

# Check QuestDB
curl http://localhost:9000/exec?query=SELECT%201  # Should return JSON

# Check backend health
curl http://localhost:8000/health
```

---

## Authentication & Security Errors

### "SECURITY ERROR: credentials must be set via environment variables"

**Cause:** Missing or invalid password hashes in `.env` file.

**Solution:**
```bash
# Generate secure credentials
python scripts/migrate_passwords_to_bcrypt.py

# Copy output to .env file
# Example output:
# DEMO_PASSWORD=$2b$12$...
# TRADER_PASSWORD=$2b$12$...
# JWT_SECRET=...
```

---

### "JWT_SECRET must be set to a strong secret"

**Cause:** JWT secret is missing, too short, or uses a weak default.

**Solution:**
```bash
# Generate a strong secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
JWT_SECRET=<paste-generated-secret-here>
```

**Requirements:**
- Minimum 32 characters
- Cryptographically random
- Never use "secret", "dev_jwt_secret_key", etc.

---

### "Plain text password detected"

**Cause:** Using plain text passwords instead of bcrypt hashes.

**Solution:**
```bash
python scripts/migrate_passwords_to_bcrypt.py
```

Bcrypt hashes start with `$2b$12$` and are ~60 characters long.

---

### "401 Unauthorized" on API requests

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Missing token | Add `Authorization: Bearer <token>` header |
| Expired token | Re-login to get new token |
| Invalid token | Check token format (header.payload.signature) |
| Wrong credentials | Verify username/password |

**Debug:**
```bash
# Get a fresh token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demo123"}'

# Use the token
curl http://localhost:8000/api/strategies \
  -H "Authorization: Bearer <token-from-above>"
```

---

### "Rate limit exceeded"

**Cause:** Too many requests in short time period.

**Limits:**
- Login: 5 requests/minute
- Strategy creation: 10 requests/minute
- Default: 200 requests/minute

**Solution:** Wait 60 seconds, then retry.

---

## Connection Errors

### "Connection refused" on port 8000

**Causes:**

1. **Backend not running**
   ```bash
   python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8000
   ```

2. **Port already in use**
   ```bash
   # Windows
   netstat -ano | findstr :8000
   taskkill /PID <pid> /F

   # Linux/Mac
   lsof -i :8000
   kill -9 <pid>
   ```

3. **Firewall blocking**
   - Check Windows Firewall settings
   - Allow Python through firewall

---

### "Connection refused" on port 9000 (QuestDB)

**Cause:** QuestDB not running.

**Solution:**
```bash
# Docker
docker run -p 9000:9000 -p 8812:8812 questdb/questdb

# Or start local QuestDB installation
```

**Verify:**
- Open http://localhost:9000 in browser
- Should see QuestDB web console

---

### "WebSocket connection failed"

**Causes & Solutions:**

| Error | Cause | Solution |
|-------|-------|----------|
| `ws://` refused | Backend not running | Start backend |
| Handshake failed | Auth required | Include token in connection |
| Connection dropped | Timeout | Check `WS_PING_INTERVAL` setting |

**Debug WebSocket:**
```javascript
// Browser console
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onopen = () => console.log('Connected');
ws.onerror = (e) => console.error('Error:', e);
ws.onmessage = (m) => console.log('Message:', m.data);
```

---

### "MEXC connection failed"

**Causes:**

1. **Network issues** - Check internet connection
2. **API keys invalid** - Verify in MEXC dashboard
3. **Rate limited by MEXC** - Wait and retry

**Debug:**
```bash
# Test MEXC API directly
curl https://api.mexc.com/api/v3/ping
```

---

## Frontend Errors

### "API Error" / "Network Error" in UI

**Cause:** Frontend can't reach backend.

**Check:**
1. Backend running on port 8000
2. `frontend/.env.local` has correct URLs:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_WS_URL=ws://localhost:8000
   ```
3. No CORS issues (check browser console)

**Solution:**
```bash
# Restart frontend after changing .env.local
cd frontend
npm run dev
```

---

### "Module not found" in frontend

**Solution:**
```bash
cd frontend
rm -rf node_modules
npm install
```

---

### Strategy Builder shows blank canvas

**Causes:**

1. **JavaScript error** - Check browser console (F12)
2. **React state issue** - Hard refresh (Ctrl+Shift+R)
3. **API connection failed** - Check backend is running

---

### Charts not loading / Empty dashboard

**Cause:** No data or mock data disabled.

**Check `frontend/.env.local`:**
```env
NEXT_PUBLIC_ENABLE_MOCK_DATA=true
```

**Note:** Even with mock data, some components require backend connection.

---

## Backend Errors

### "ModuleNotFoundError: No module named 'src'"

**Cause:** Running from wrong directory or venv not activated.

**Solution:**
```bash
# Must be in project root
cd FX_code_AI_v2

# Activate venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate # Linux/Mac

# Run from project root
python -m uvicorn src.api.unified_server:app --port 8000
```

---

### "QuestDB connection failed"

**Causes:**

1. **QuestDB not running** - Start it
2. **Wrong port** - Default is 8812 for PostgreSQL wire protocol
3. **Tables don't exist** - Run migrations

**Run migrations:**
```bash
python database/questdb/run_migration_008.py
```

---

### "Redis connection failed" (Windows)

**Cause:** Redis not available on Windows without Docker/WSL.

**Impact:**
- No computation caching
- No session persistence
- Degraded performance

**Workaround:** System runs in degraded mode automatically. For full functionality, use Docker:
```bash
docker run -p 6379:6379 redis:latest
```

---

### Event loop errors / "RuntimeError: Event loop is closed"

**Cause:** Async code issues, often on Windows.

**Solution:**
```python
# Add to top of your script
import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

---

## Strategy Validation Errors

### "Graph has cycles"

**Cause:** Circular dependency in strategy nodes.

**Solution:** Ensure data flows in one direction:
```
Data Source → Indicator → Condition → Action
```

Never connect an Action back to a Data Source.

---

### "Missing required connection"

**Cause:** Node input not connected.

**Solution:** Each node type requires specific inputs:
- Indicator nodes need Data Source input
- Condition nodes need Indicator input
- Action nodes need Condition input

---

### "Invalid parameter value"

**Cause:** Node parameter out of valid range.

**Common limits:**
| Parameter | Valid Range |
|-----------|-------------|
| Window (seconds) | 60 - 3600 |
| Threshold | -1000 to 1000 |
| Position size | 0.01 - 10000 |

---

## Performance Issues

### Backend slow / High CPU

**Causes:**

1. **Too many indicators** - Reduce active indicators
2. **No caching (Redis)** - Enable Redis
3. **Debug logging** - Set `LOG_LEVEL=INFO` in .env

---

### Frontend laggy

**Causes:**

1. **Too many chart updates** - Reduce update frequency
2. **Large strategy graphs** - Keep under 20 nodes
3. **Dev mode** - Production build is faster:
   ```bash
   npm run build
   npm run start
   ```

---

## Database Issues

### "Table does not exist"

**Solution:**
```bash
python database/questdb/run_migration_008.py
```

---

### "Disk full" / QuestDB errors

**Solution:**
```bash
# Check QuestDB data directory size
# Default: ~/.questdb/db

# Clean old data if needed
# WARNING: This deletes data!
rm -rf ~/.questdb/db/*
```

---

## Getting Help

If your issue isn't listed:

1. **Check logs:**
   ```bash
   # Backend logs in terminal
   # Frontend: Browser console (F12)
   ```

2. **Minimal reproduction:**
   - What exact command/action causes the error?
   - What error message appears?
   - What did you expect to happen?

3. **Environment info:**
   ```bash
   python --version
   node --version
   pip freeze > requirements_actual.txt
   ```

---

## Error Code Reference

| Code | Meaning | Solution |
|------|---------|----------|
| `validation_error` | Invalid request data | Check request format |
| `authentication_required` | Missing auth | Add JWT token |
| `rate_limit_exceeded` | Too many requests | Wait 60 seconds |
| `session_conflict` | Session already exists | Stop existing session first |
| `strategy_activation_failed` | Strategy invalid | Check strategy validation |
| `service_unavailable` | Backend overloaded | Retry later |
| `budget_cap_exceeded` | Position too large | Reduce position size |

---

*Last updated: 2025-12-25*
