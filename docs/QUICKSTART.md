# Quickstart Guide

Get FX Agent AI running in under 10 minutes.

---

## Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.10+ | `python --version` |
| Node.js | 18+ | `node --version` |
| QuestDB | 7.0+ | Running on `localhost:9000` |

---

## 1. Clone and Setup Environment

```bash
# Clone repository
git clone <repository-url>
cd FX_code_AI_v2

# Create Python virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

---

## 2. Configure Environment

```bash
# Copy environment templates
cp .env.example .env
cp .env.backend.example .env.backend
cp frontend/.env.example frontend/.env.local

# Generate secure credentials
python scripts/migrate_passwords_to_bcrypt.py
```

Edit `.env` with the generated bcrypt hashes and JWT secret.

**Minimum required in `.env`:**
```env
JWT_SECRET=<your-generated-secret-min-32-chars>
DEMO_PASSWORD=<bcrypt-hash-from-script>
```

---

## 3. Start QuestDB

QuestDB must be running before starting the backend.

**Option A: Docker (Recommended)**
```bash
docker run -p 9000:9000 -p 8812:8812 questdb/questdb
```

**Option B: Local Install**
Download from [questdb.io](https://questdb.io/get-questdb/) and run.

Verify: Open http://localhost:9000 in browser.

---

## 4. Start Backend

```bash
# From project root, with venv activated
python -m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8000 --reload
```

Verify: http://localhost:8000/health should return `{"status": "healthy"}`

---

## 5. Start Frontend

```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

Verify: Open http://localhost:3000 in browser.

---

## 6. Login

Default credentials (for development only):

| Username | Password | Permissions |
|----------|----------|-------------|
| demo | demo123 | Read-only |
| trader | trader123 | Paper trading |
| admin | admin123 | Full access |

**Note:** Generate new passwords for any non-development use.

---

## Quick Verification Checklist

- [ ] QuestDB running on http://localhost:9000
- [ ] Backend health check: http://localhost:8000/health
- [ ] Frontend loads: http://localhost:3000
- [ ] Can login with demo/demo123
- [ ] Dashboard displays (may show empty data)

---

## Common Issues

### "SECURITY ERROR: credentials must be set"
```bash
python scripts/migrate_passwords_to_bcrypt.py
# Copy generated hashes to .env
```

### "Connection refused" on backend
- Check QuestDB is running
- Check port 8000 is not in use

### Frontend shows "API Error"
- Ensure backend is running on port 8000
- Check `frontend/.env.local` has correct API URL

### "Module not found" errors
```bash
pip install -r requirements.txt
```

---

## Next Steps

1. **Explore Strategy Builder:** Navigate to `/strategy-builder`
2. **Read the Architecture:** `_bmad-output/architecture.md`
3. **Check Known Limitations:** `docs/KNOWN_LIMITATIONS.md`

---

## Project Structure

```
FX_code_AI_v2/
├── src/                    # Python backend
│   ├── api/               # REST + WebSocket endpoints
│   ├── domain/            # Business logic
│   └── infrastructure/    # External integrations
├── frontend/              # Next.js frontend
├── docs/                  # Documentation
├── _bmad-output/          # BMAD artifacts (PRD, architecture)
└── config/                # Configuration files
```

---

*For detailed setup, see `docs/development/SETUP.md`*
