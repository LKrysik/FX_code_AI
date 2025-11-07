# Deployment Quick Reference

**Quick commands for deployment, rollback, and troubleshooting**

---

## Quick Start (First Time)

```bash
# 1. Configure environment
cp .env.production.template .env.production
nano .env.production  # Fill in MEXC_API_KEY, MEXC_API_SECRET, etc.

# 2. Setup infrastructure
docker network create trading-internal
docker network create trading-external
docker volume create trading-questdb-data

# 3. Deploy
docker-compose up -d

# 4. Verify
curl http://localhost:8080/health/ready
```

---

## Regular Deployment

```bash
# Standard deployment (with build)
./scripts/deploy.sh

# Fast deployment (skip build)
./scripts/deploy.sh --skip-build

# Check logs
tail -f logs/deployment-*.log
```

---

## Emergency Rollback

```bash
# Interactive rollback
./scripts/rollback.sh

# Forced rollback (no confirmation)
./scripts/rollback.sh --force

# Rollback with database restore
./scripts/rollback.sh --force --restore-db
```

---

## Health Checks

```bash
# Backend
curl http://localhost:8080/health
curl http://localhost:8080/health/ready

# Frontend
curl http://localhost:3000/api/health

# Check which environment is active
curl http://localhost:8080/health | jq '.environment'
```

---

## Docker Commands

```bash
# Check running containers
docker ps

# Check logs
docker logs -f trading-backend
docker logs -f trading-frontend

# Restart service
docker-compose restart backend

# Stop all
docker-compose down

# Clean everything (CAREFUL!)
docker-compose down -v  # Removes volumes
```

---

## Database Operations

```bash
# List migrations
python database/questdb/rollback_migration.py --list

# Rollback last migration
python database/questdb/rollback_migration.py --last

# Manual backup
mkdir -p backups
PGPASSWORD=quest pg_dump -h localhost -p 8812 -U admin -d qdb > backups/backup-$(date +%Y%m%d-%H%M%S).sql
```

---

## Monitoring

```bash
# Grafana: http://localhost:3001
# Prometheus: http://localhost:9090
# QuestDB: http://localhost:9000

# Check metrics
curl http://localhost:8080/metrics | grep orders_submitted_total
```

---

## Troubleshooting

```bash
# Check environment
docker ps | grep trading
docker-compose ps

# Check logs for errors
docker-compose logs | grep ERROR

# Test database connection
docker exec trading-backend python -c "
import asyncio
import asyncpg
async def test():
    conn = await asyncpg.connect(host='localhost', port=8812, user='admin', password='quest', database='qdb')
    print('✓ Database connected')
    await conn.close()
asyncio.run(test())
"

# Restart everything
docker-compose down && docker-compose up -d
```

---

## Service URLs

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8080/api
- **WebSocket:** ws://localhost:8080/ws
- **Health:** http://localhost:8080/health
- **Metrics:** http://localhost:8080/metrics
- **Grafana:** http://localhost:3001 (admin/admin)
- **Prometheus:** http://localhost:9090
- **QuestDB:** http://localhost:9000

---

## Common Issues

**502 Bad Gateway**
```bash
# Check if backend is running
docker ps | grep backend
# Restart backend
docker-compose restart backend
```

**Health check fails**
```bash
# Check backend logs
docker logs trading-backend
# Check database
curl http://localhost:9000/
```

**Deployment stuck**
```bash
# Check logs
tail -f logs/deployment-*.log
# Kill and rollback
Ctrl+C
./scripts/rollback.sh --force
```

---

## Files Reference

- **Deployment script:** `scripts/deploy.sh`
- **Rollback script:** `scripts/rollback.sh`
- **DB rollback:** `database/questdb/rollback_migration.py`
- **Compose files:** `docker-compose.yml`, `docker-compose.{blue,green}.yml`
- **Environment:** `.env.production`
- **Nginx config:** `nginx/sites-available/trading.conf`
- **Full docs:** `docs/deployment/DEPLOYMENT_GUIDE.md`

---

**For detailed information, see DEPLOYMENT_GUIDE.md**
