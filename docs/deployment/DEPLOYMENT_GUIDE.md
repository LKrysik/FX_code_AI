# Deployment Guide - FX Trading System

**Version:** 1.0
**Last Updated:** 2025-11-07
**Author:** Deployment Specialist Agent
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Blue-Green Deployment](#blue-green-deployment)
5. [Rollback Procedures](#rollback-procedures)
6. [Database Management](#database-management)
7. [Monitoring and Health Checks](#monitoring-and-health-checks)
8. [Troubleshooting](#troubleshooting)
9. [Production Checklist](#production-checklist)

---

## Overview

This guide covers the complete deployment process for the FX Trading System using Docker containers and blue-green deployment strategy for zero-downtime updates.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Nginx Load Balancer                  │
│                 (Traffic Switching)                     │
└────────────────┬────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        ↓                 ↓
┌──────────────┐  ┌──────────────┐
│ Blue Env     │  │ Green Env    │
│ Port 8080    │  │ Port 8081    │
│ Port 3000    │  │ Port 3002    │
└──────┬───────┘  └──────┬───────┘
       │                 │
       └────────┬────────┘
                ↓
        ┌──────────────┐
        │   QuestDB    │
        │ (Shared DB)  │
        └──────────────┘
```

### Key Features

- **Zero-downtime deployment** - Blue-green strategy ensures continuous service
- **Automatic health checks** - Pre-deployment and post-deployment validation
- **Automatic rollback** - Failed deployments automatically revert
- **Database backup** - Automatic backup before deployment
- **Monitoring integration** - Prometheus + Grafana for real-time metrics
- **Security** - Non-root containers, secrets from environment variables

---

## Prerequisites

### System Requirements

- **OS:** Linux (Ubuntu 20.04+ recommended) or macOS
- **RAM:** 8GB minimum, 16GB recommended
- **CPU:** 4 cores minimum
- **Disk:** 50GB free space
- **Network:** Stable internet connection for exchange API

### Software Requirements

Install the following before deployment:

```bash
# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Nginx (for load balancing)
sudo apt-get update
sudo apt-get install -y nginx

# PostgreSQL client tools (for database operations)
sudo apt-get install -y postgresql-client
```

### Verify Installation

```bash
docker --version          # Should show Docker version 20.10+
docker-compose --version  # Should show docker-compose version 1.29+
nginx -v                  # Should show nginx version 1.18+
psql --version           # Should show PostgreSQL 12+
```

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/FX_code_AI.git
cd FX_code_AI
```

### 2. Configure Environment

```bash
# Copy production environment template
cp .env.production.template .env.production

# Edit with your actual credentials
nano .env.production
```

**CRITICAL:** Fill in these required values:
- `MEXC_API_KEY` - Your MEXC API key
- `MEXC_API_SECRET` - Your MEXC API secret
- `GRAFANA_ADMIN_PASSWORD` - Secure Grafana password
- `JWT_SECRET` - Generate with `openssl rand -hex 32`

### 3. Initial Setup

```bash
# Create required directories
mkdir -p logs backups

# Setup Nginx configuration
sudo cp nginx/sites-available/trading.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/trading.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Create Docker networks
docker network create trading-internal
docker network create trading-external

# Create Docker volumes
docker volume create trading-questdb-data
docker volume create trading-prometheus-data
docker volume create trading-grafana-data
```

### 4. First Deployment

```bash
# Start with standard docker-compose (all services)
docker-compose up -d

# Wait for services to be healthy (2-3 minutes)
docker-compose ps

# Verify health
curl http://localhost:8080/health/ready
curl http://localhost:3000/api/health
```

### 5. Access Services

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8080/api
- **Grafana:** http://localhost:3001 (admin/your_password)
- **Prometheus:** http://localhost:9090
- **QuestDB Console:** http://localhost:9000

---

## Blue-Green Deployment

Blue-green deployment allows zero-downtime updates by maintaining two identical environments (blue and green) and switching traffic between them.

### How It Works

1. **Current state:** Blue environment active, serving traffic
2. **Deploy:** Build and start Green environment
3. **Health check:** Verify Green environment is healthy
4. **Smoke test:** Monitor Green for 30 seconds
5. **Switch:** Nginx redirects traffic to Green
6. **Cleanup:** Stop Blue environment after connection draining

### Deployment Process

#### Step 1: Prepare for Deployment

```bash
# Ensure you're on the correct branch
git pull origin main

# Verify no uncommitted changes
git status

# Check current environment
curl http://localhost:8080/health | jq '.environment'
```

#### Step 2: Run Deployment Script

```bash
# Standard deployment (with build)
./scripts/deploy.sh

# Skip build (if images already built)
./scripts/deploy.sh --skip-build

# Deploy without automatic rollback (advanced)
./scripts/deploy.sh --no-rollback
```

#### Step 3: Monitor Deployment

The script will:
1. Detect current active environment (blue or green)
2. Build Docker images for target environment
3. Start target environment containers
4. Wait for health checks (max 10 retries, 5s interval)
5. Run smoke tests (30 second monitoring)
6. Update Nginx configuration
7. Switch traffic to target environment
8. Wait 30 seconds for connection draining
9. Stop old environment

**Deployment Log:**
```bash
tail -f logs/deployment-YYYYMMDD-HHMMSS.log
```

#### Step 4: Verify Deployment

```bash
# Check active environment
curl http://localhost:8080/health | jq

# Check frontend
curl http://localhost:3000/api/health

# Check metrics
curl http://localhost:8080/metrics | grep orders_submitted_total

# Check Grafana dashboards
open http://localhost:3001
```

### Deployment Timeline

- **Build phase:** 2-5 minutes (depending on changes)
- **Startup phase:** 1-2 minutes
- **Health checks:** 30-60 seconds
- **Smoke tests:** 30 seconds
- **Total:** ~5-10 minutes

---

## Rollback Procedures

### When to Rollback

Rollback immediately if:
- Health checks fail after deployment
- Critical errors in logs
- Trading functionality broken
- Database corruption detected
- High error rate in metrics

### Automatic Rollback

The deployment script automatically rolls back if:
- Health checks fail (10 retries)
- Smoke tests fail (3+ failures in 30s)
- Post-switch health check fails

### Manual Rollback

If you need to manually rollback:

```bash
# Emergency rollback (with confirmation)
./scripts/rollback.sh

# Force rollback (skip confirmation)
./scripts/rollback.sh --force

# Rollback and restore database
./scripts/rollback.sh --force --restore-db
```

### Rollback Process

The rollback script will:
1. Identify current active environment
2. Start previous environment
3. Wait for health checks
4. Switch Nginx back to previous environment
5. Stop failed environment

**Rollback Timeline:** ~2-3 minutes

### Verify Rollback Success

```bash
# Check environment
curl http://localhost:8080/health | jq '.environment'

# Check logs
tail -f logs/rollback-YYYYMMDD-HHMMSS.log

# Check trading functionality
# - Place test order
# - Verify position sync
# - Check WebSocket connection
```

---

## Database Management

### Database Migrations

Migrations are applied automatically during container startup. To manually apply:

```bash
# Run migrations
docker exec trading-backend python database/questdb/migrate.py
```

### Database Backup

Backups are created automatically before deployment:

```bash
# Manual backup
docker exec trading-backend python database/questdb/backup.py

# Backups stored in: ./backups/questdb-backup-YYYYMMDD-HHMMSS.sql
```

### Database Rollback

Rollback a specific migration:

```bash
# Interactive rollback (with confirmation)
python database/questdb/rollback_migration.py 016

# List applied migrations
python database/questdb/rollback_migration.py --list

# Rollback last migration
python database/questdb/rollback_migration.py --last
```

### Database Restore

Restore from backup:

```bash
# Find latest backup
ls -lah backups/

# Restore (replace TIMESTAMP with actual backup file)
PGPASSWORD=quest psql -h localhost -p 8812 -U admin -d qdb < backups/questdb-backup-TIMESTAMP.sql
```

### Database Health Check

```bash
# Check QuestDB health
curl http://localhost:9000/

# Check table sizes
docker exec trading-backend python -c "
import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host='localhost', port=8812, user='admin',
        password='quest', database='qdb'
    )
    tables = await conn.fetch(\"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'\")
    for table in tables:
        count = await conn.fetchval(f\"SELECT COUNT(*) FROM {table['table_name']}\")
        print(f\"{table['table_name']}: {count} rows\")
    await conn.close()

asyncio.run(check())
"
```

---

## Monitoring and Health Checks

### Health Check Endpoints

**Backend:**
- `GET /health` - Basic liveness check (always 200 OK)
- `GET /health/ready` - Readiness check (DB + EventBus + MEXC)
- `GET /health/deep` - Deep health check (all subsystems)

**Frontend:**
- `GET /api/health` - Next.js health check

### Monitoring Dashboards

**Grafana (http://localhost:3001):**

1. **Trading Overview Dashboard**
   - Orders per minute
   - Fill rate
   - P&L chart
   - Active positions

2. **Risk Dashboard**
   - Margin ratio gauge
   - Daily loss percentage
   - Position concentration
   - Risk alerts timeline

3. **System Health Dashboard**
   - EventBus throughput
   - Circuit breaker state
   - API latency
   - Memory usage

4. **Exchange Integration Dashboard**
   - MEXC API latency
   - API error rate
   - Position sync status

### Critical Alerts

Prometheus alerts are configured for:

- **MarginRatioLow** - Margin ratio < 15% (CRITICAL)
- **DailyLossLimitExceeded** - Daily loss > 5% (CRITICAL)
- **CircuitBreakerOpen** - Circuit breaker opened (CRITICAL)
- **OrderSubmissionLatencyHigh** - P95 latency > 5s (WARNING)
- **NoOrderFills** - No fills in 5 minutes (WARNING)
- **HighErrorRate** - Error rate > 10% (WARNING)
- **PositionSyncFailure** - Sync failed for 60s (CRITICAL)

### Log Monitoring

```bash
# Backend logs
docker logs -f trading-backend

# Frontend logs
docker logs -f trading-frontend

# QuestDB logs
docker logs -f trading-questdb

# All services
docker-compose logs -f

# Search for errors
docker-compose logs | grep ERROR
```

---

## Troubleshooting

### Common Issues

#### 1. Health Check Timeout

**Symptom:** Deployment fails with "Health check failed after 10 attempts"

**Causes:**
- Backend not starting properly
- Database connection failure
- Port already in use

**Solution:**
```bash
# Check backend logs
docker logs trading-backend-green

# Check database connection
docker exec trading-backend-green curl http://localhost:8080/health/ready

# Check port availability
sudo netstat -tulpn | grep 8081

# Manual restart
docker-compose -f docker-compose.green.yml restart backend-green
```

#### 2. Database Connection Failure

**Symptom:** Backend logs show "asyncpg.exceptions.ConnectionDoesNotExistError"

**Causes:**
- QuestDB not running
- Wrong credentials
- Network issue

**Solution:**
```bash
# Check QuestDB status
docker ps | grep questdb

# Test database connection
docker exec trading-questdb curl http://localhost:9000/

# Restart QuestDB
docker-compose restart questdb

# Verify credentials in .env.production
```

#### 3. Nginx Configuration Error

**Symptom:** "nginx: [emerg] invalid parameter" or 502 Bad Gateway

**Causes:**
- Syntax error in config
- Backend not responding
- Upstream server down

**Solution:**
```bash
# Test nginx config
sudo nginx -t

# Check nginx error log
sudo tail -f /var/log/nginx/error.log

# Reload nginx
sudo systemctl reload nginx

# Check upstream health
curl http://localhost:8080/health
curl http://localhost:8081/health
```

#### 4. Docker Build Failure

**Symptom:** "ERROR: failed to solve: process "/bin/sh -c ..." did not complete"

**Causes:**
- Missing dependencies
- Network timeout
- Disk space full

**Solution:**
```bash
# Check disk space
df -h

# Clean Docker cache
docker system prune -a

# Rebuild with no cache
docker-compose -f docker-compose.green.yml build --no-cache

# Check build logs
docker-compose -f docker-compose.green.yml build 2>&1 | tee build.log
```

#### 5. WebSocket Connection Failure

**Symptom:** Frontend shows "WebSocket connection failed"

**Causes:**
- Nginx not forwarding WebSocket properly
- Backend WebSocket server down
- CORS issues

**Solution:**
```bash
# Test WebSocket endpoint
wscat -c ws://localhost:8080/ws

# Check Nginx WebSocket config
grep -A 10 "location /ws" /etc/nginx/sites-available/trading.conf

# Check backend WebSocket logs
docker logs trading-backend | grep WebSocket
```

### Emergency Procedures

#### Complete System Restart

```bash
# Stop all services
docker-compose down
docker-compose -f docker-compose.blue.yml down
docker-compose -f docker-compose.green.yml down

# Clean up (careful! removes volumes)
# docker volume prune  # Only if you want to reset database

# Start fresh
docker-compose up -d

# Wait 2 minutes for startup
sleep 120

# Verify health
curl http://localhost:8080/health/ready
```

#### Database Recovery

```bash
# Stop services
docker-compose down

# Restore from backup
PGPASSWORD=quest psql -h localhost -p 8812 -U admin -d qdb < backups/questdb-backup-latest.sql

# Start services
docker-compose up -d

# Verify data integrity
python database/questdb/verify_data.py
```

---

## Production Checklist

### Pre-Deployment Checklist

- [ ] Code reviewed and approved
- [ ] All tests passing (unit + integration + E2E)
- [ ] Environment variables configured (`.env.production`)
- [ ] Database backup created
- [ ] Monitoring dashboards verified
- [ ] Alert channels tested (Slack, PagerDuty, Email)
- [ ] Team notified of deployment window
- [ ] Rollback plan documented

### Deployment Checklist

- [ ] Run `./scripts/deploy.sh`
- [ ] Monitor deployment logs
- [ ] Verify health checks pass
- [ ] Verify smoke tests pass
- [ ] Check Grafana dashboards
- [ ] Test critical user flows:
  - [ ] Start live session
  - [ ] Place test order
  - [ ] Verify position sync
  - [ ] Check WebSocket updates
  - [ ] Verify risk alerts
- [ ] Monitor for 15 minutes post-deployment

### Post-Deployment Checklist

- [ ] All services healthy
- [ ] No critical errors in logs
- [ ] Metrics look normal (compare to baseline)
- [ ] Trading functionality confirmed
- [ ] Database integrity verified
- [ ] Old environment stopped
- [ ] Deployment documented
- [ ] Team notified of completion

### Weekly Maintenance Checklist

- [ ] Review logs for errors
- [ ] Check disk space (`df -h`)
- [ ] Verify database backups exist
- [ ] Review Grafana metrics
- [ ] Update dependencies (security patches)
- [ ] Test rollback procedure (staging)
- [ ] Review alert history

---

## Advanced Topics

### Multi-Server Deployment

For high-availability, deploy across multiple servers:

```bash
# Server 1 (Primary)
docker-compose -f docker-compose.yml up -d

# Server 2 (Replica)
docker-compose -f docker-compose.replica.yml up -d

# Load balancer routes to both servers
```

### Database Replication

For database redundancy:

```bash
# Setup QuestDB replication
# (Refer to QuestDB documentation)
```

### SSL/TLS Configuration

Enable HTTPS for production:

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d trading.yourdomain.com

# Update nginx config
# Uncomment SSL server block in nginx/sites-available/trading.conf

# Reload nginx
sudo systemctl reload nginx
```

---

## Contact and Support

**Issues:** https://github.com/yourusername/FX_code_AI/issues
**Documentation:** https://github.com/yourusername/FX_code_AI/tree/main/docs
**Monitoring:** http://localhost:3001 (Grafana)

---

**End of Deployment Guide**
