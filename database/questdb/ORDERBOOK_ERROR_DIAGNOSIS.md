# QuestDB Orderbook Write Error: Diagnostic Guide

## 🔍 Problem Summary

**Error Message:**
```
IngressError: row() can't be called: Sender is closed
```

**Root Cause:**
QuestDB is offline or unreachable. This error indicates the database server is not running or not accepting connections on the ILP port (9009).

**Critical Insight:**
This is NOT a code bug. Even newly created Sender connections fail immediately when QuestDB is not running. The pattern of consistent failures across multiple fresh connection attempts confirms the server itself is unavailable.

---

## ✅ Immediate Solution

### Step 1: Start QuestDB

**Windows (PowerShell):**
```powershell
# Option A: Using install script
python database\questdb\install_questdb.py

# Option B: Manual start (if already installed)
cd database\questdb\questdb
.\bin\questdb.exe start
```

**Linux/Mac:**
```bash
# Option A: Using install script
python database/questdb/install_questdb.py

# Option B: Manual start
cd database/questdb/questdb
./bin/questdb.sh start
```

### Step 2: Verify QuestDB is Running

**Check Web UI:**
Open browser and navigate to:
```
http://127.0.0.1:9000
```

You should see the QuestDB console. If you can access it, the database is running.

**Check Process (Windows):**
```powershell
tasklist | findstr -i questdb
# Should show: java.exe running QuestDB
```

**Check Process (Linux/Mac):**
```bash
ps aux | grep questdb
# Should show: java process with questdb
```

**Check Port Availability:**
```powershell
# Windows
netstat -an | findstr :9009
# Should show: TCP 0.0.0.0:9009 LISTENING

# Linux/Mac
netstat -an | grep 9009
# Should show: tcp 0.0.0.0:9009 LISTEN
```

---

## 🏗️ Architecture: How Sender Pool Works

```
┌─────────────────────────────────────────────────────┐
│         QuestDBProvider (Connection Pool)           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  _sender_pool: [Sender1, Sender2, Sender3, ...]   │
│                    ↓                                │
│  Each Sender = TCP connection to QuestDB:9009     │
│                                                     │
│  Pool size: Configurable (default: 4 connections)  │
│  Protocol: ILP (InfluxDB Line Protocol)           │
│                                                     │
└─────────────────────────────────────────────────────┘
                         ↓
                   TCP Socket
                         ↓
        ┌───────────────────────────┐
        │   QuestDB Server :9009    │
        │   (ILP Ingestion Layer)   │
        └───────────────────────────┘
```

**Connection Lifecycle:**
1. **Initialize:** Pool creates N Sender connections at startup
2. **Acquire:** Each write operation acquires a Sender from pool
3. **Write:** Sender sends data via ILP protocol (fast, binary)
4. **Release:** Sender returned to pool for reuse
5. **Broken:** If Sender fails, it's marked broken and recreated

**Why Senders Become "Closed":**
- QuestDB restarts → All TCP connections drop
- Long idle time → Server closes inactive connections
- Network issues → Socket timeouts
- Server shutdown → Graceful connection termination

---

## 🔧 Improvements in Current Codebase

### 1. Automatic Stale Sender Detection
```python
# In _execute_ilp_with_retry()
is_stale_sender = "sender is closed" in error_str

if is_stale_sender:
    await self._release_sender(sender, is_broken=True)
    # Automatically creates fresh sender and retries
```

### 2. Clear Error Messages
When all retry attempts fail, you'll see:
```
Failed to insert_tick_prices_batch: QuestDB appears to be OFFLINE

This error indicates QuestDB is not running or not accepting connections.
Please:
  1. Start QuestDB server
  2. Verify ports 9009 (ILP) and 8812 (PostgreSQL) are accessible
  3. Check Web UI: http://127.0.0.1:9000
```

### 3. Exponential Backoff Retry
- Attempt 1: Immediate
- Attempt 2: +1s delay
- Attempt 3: +2s delay
- Attempt 4: +4s delay
- Total: 4 attempts over ~7 seconds

### 4. Emergency Sender Creation
If pool is exhausted during high load:
```python
# _acquire_sender() will create new sender on-demand
new_sender = Sender(Protocol.Tcp, self.ilp_host, self.ilp_port)
# Self-healing mechanism - pool size can grow temporarily
```

---

## 🐛 Common Issues and Solutions

### Issue #1: Port Conflict (9009 already in use)

**Symptoms:**
```
IngressError: Could not bind to port 9009
```

**Solution:**
```powershell
# Windows - Find process using port 9009
netstat -ano | findstr :9009
# Kill process by PID
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :9009
kill -9 <PID>
```

### Issue #2: Firewall Blocking

**Symptoms:**
- Connection timeout
- "Connection refused" errors

**Solution (Windows Firewall):**
```powershell
# Add firewall rule for QuestDB
New-NetFirewallRule -DisplayName "QuestDB ILP" -Direction Inbound -LocalPort 9009 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "QuestDB Web" -Direction Inbound -LocalPort 9000 -Protocol TCP -Action Allow
```

### Issue #3: QuestDB Crashed

**Symptoms:**
- Process not running
- Web UI not accessible
- Logs show OutOfMemoryError

**Solution:**
```powershell
# Check QuestDB logs
cd database\questdb\questdb\log
# Look for errors in latest log file

# Increase JVM heap (if OOM errors)
# Edit conf/server.conf:
# java.memory.max=4G  # Default 512M, increase if needed
```

### Issue #4: Corrupted Database Files

**Symptoms:**
- QuestDB starts but writes fail
- Logs show "table does not exist" or corruption errors

**Solution:**
```powershell
# CAUTION: This will DELETE all data!
# Stop QuestDB
cd database\questdb\questdb
.\bin\questdb.exe stop

# Remove database files
rm -r db/

# Restart QuestDB (will recreate tables)
.\bin\questdb.exe start

# Re-run table creation script
python database/questdb/create_tables.py
```

---

## ✅ Verification Checklist

Before running tests, verify ALL of the following:

- [ ] **Java installed:** `java -version` (requires Java 11+)
- [ ] **QuestDB process running:** Check `tasklist` or `ps aux`
- [ ] **Port 9009 listening:** Check `netstat -an | findstr :9009`
- [ ] **Port 9000 accessible:** Open http://127.0.0.1:9000 in browser
- [ ] **No firewall blocking:** Ports 9000 and 9009 allowed
- [ ] **Tables exist:** Check Web UI console for `tick_prices` table
- [ ] **Disk space available:** QuestDB needs space for WAL and data files

---

## 🧪 Diagnostic Tools

### Quick Connection Test

**Using curl (ILP protocol):**
```bash
# Test if ILP port is open
curl -v telnet://localhost:9009

# Should connect successfully (may not send data, but connection is key)
```

**Using Python diagnostic script:**
```bash
# Run included diagnostic tool
python database/questdb/test_questdb_connection.py

# Will test:
# - ILP connection (port 9009)
# - Sender creation and reuse
# - Stale sender detection
```

### Check QuestDB Logs

**Location:**
```
database/questdb/questdb/log/
```

**What to look for:**
- `INFO` messages about server startup
- `ERROR` messages about connection failures
- `WARN` messages about resource limits
- Port binding confirmation: `listening on 0.0.0.0:9009 [ILP]`

---

## 📊 Performance Notes

**Connection Pool Size:**
- Default: 4 concurrent connections
- Increase if: High write throughput (>10K rows/sec)
- Decrease if: Memory constrained systems

**Write Performance:**
- ILP throughput: **1M+ rows/sec** (QuestDB benchmark)
- Batch size: 1000-10000 rows optimal
- Latency: <5ms per batch (local connection)

**When to Scale:**
- Single QuestDB instance: Up to 100K rows/sec sustained
- Beyond that: Consider distributed QuestDB cluster

---

## 🆘 Still Having Issues?

1. **Check QuestDB Documentation:** https://questdb.io/docs/
2. **Review logs:** `database/questdb/questdb/log/stdout-*.txt`
3. **Test with minimal example:** Use `test_questdb_connection.py`
4. **Verify system resources:** QuestDB needs CPU, RAM, and disk I/O
5. **Community support:** QuestDB Slack or GitHub issues

---

## 📝 Summary

**The "Sender is closed" error is NOT a code bug.** It's a clear indicator that QuestDB is offline or unreachable. The codebase handles this gracefully with:

- ✅ Automatic retry with fresh senders
- ✅ Clear error messages with actionable steps
- ✅ Self-healing connection pool
- ✅ Emergency sender creation

**Always start QuestDB before running tests or data collection!**

```bash
# Remember this command:
python database/questdb/install_questdb.py

# Then verify:
curl http://127.0.0.1:9000
# Should return QuestDB Web UI
```
