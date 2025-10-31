# Orderbook Write Error Diagnosis and Fix

## Problem Summary

When running `test_real_orderbook_write.py`, all tests fail with:
```
row() can't be called: Sender is closed.
```

This error occurs **even on freshly created senders**, indicating QuestDB connectivity issues.

## Root Cause

The error pattern indicates **QuestDB is not running** or not accepting connections:

1. ✅ **Sender pool contains stale senders** - When QuestDB restarts or connections idle timeout, pooled senders become "closed"
2. ✅ **No sender health validation** - Senders from pool were used without checking if still alive
3. ❌ **QuestDB is offline** - Even newly created senders fail immediately (most likely cause)

## Fixes Applied

### Fix 1: Enhanced Error Messages

**File**: `src/data_feed/questdb_provider.py`

**Changes**:
- Added clear error messages when all senders fail
- Provides step-by-step instructions to start QuestDB
- Distinguishes between temporary failures and QuestDB being offline

**Example new error message**:
```
╔══════════════════════════════════════════════════════════════════╗
║  ALL SENDERS ARE CLOSED - QuestDB is likely OFFLINE             ║
╚══════════════════════════════════════════════════════════════════╝

To fix:
  1. Check if QuestDB is running (task manager / process list)
  2. Start QuestDB: python database\questdb\install_questdb.py
  3. Verify Web UI is accessible: http://127.0.0.1:9000
  4. Check port 9009 is not blocked by firewall
```

### Fix 2: Sender Health Validation (Infrastructure)

**File**: `src/data_feed/questdb_provider.py`

**Changes**:
- Added `_is_sender_healthy()` method to validate senders before use
- Modified `_acquire_sender()` to check sender health from pool
- Stale senders are now closed and replaced instead of being used

**Note**: Due to QuestDB Python client limitations, full health validation isn't possible without attempting actual writes. The retry logic handles this gracefully.

## How to Fix Your Issue

### Step 1: Check if QuestDB is Running

**Windows (PowerShell/CMD)**:
```powershell
# Check if QuestDB process is running
tasklist | findstr -i questdb

# Or use Task Manager (Ctrl+Shift+Esc)
# Look for "java.exe" with command line containing "questdb"
```

**Expected output if running**:
```
java.exe    12345 Console    1    524,288 K
```

**If not running**, proceed to Step 2.

### Step 2: Start QuestDB

**Option A: Using install script (recommended)**:
```powershell
cd C:\Users\lukasz.krysik\Desktop\FXcrypto\FX_code_AI_v2
python database\questdb\install_questdb.py
```

**Option B: Manual start**:
```powershell
# Navigate to QuestDB installation directory
cd C:\questdb  # Or wherever you installed it

# Start QuestDB
.\bin\questdb.exe start

# Or on Windows:
java -jar questdb.jar
```

### Step 3: Verify QuestDB is Running

**Test Web UI**:
1. Open browser to: http://127.0.0.1:9000
2. You should see the QuestDB console
3. Try running a test query: `SELECT * FROM tables()`

**Test ILP Port**:
```powershell
# Check if port 9009 is listening
netstat -an | findstr :9009
```

**Expected output**:
```
TCP    0.0.0.0:9009    0.0.0.0:0    LISTENING
```

### Step 4: Re-run Your Test

```powershell
python test_real_orderbook_write.py
```

**Expected output** (if QuestDB is running):
```
TEST 1: Valid orderbook data (baseline)
✅ Valid data: 1 records written

TEST 2: Empty bids/asks arrays
✅ Empty bids/asks: 1 records written (all zeros)
...
```

## Technical Details

### Why "Sender is closed" Happens

1. **Sender Pool Lifecycle**:
   - Senders are created in pool during `initialize()`
   - Connections are TCP sockets to QuestDB on port 9009
   - If QuestDB restarts or connections timeout, senders become "closed"

2. **Old Behavior** (before fix):
   - Acquired sender from pool without validation
   - Called `sender.row()` on closed sender → Error!
   - Retry logic created new sender, but if QuestDB offline, also closed

3. **New Behavior** (after fix):
   - Acquire sender from pool
   - Validate health (best effort - limited by QuestDB client API)
   - If closed, discard and get new one
   - Clear error message if all attempts fail

### Why Even New Senders Fail

When the error says "ALL SENDERS ARE CLOSED", it means:

1. Initial sender from pool was stale → Marked as broken
2. Retry #1: Created new sender → Also immediately closed
3. Retry #2: Created new sender → Also immediately closed
4. Retry #3: Created new sender → Also immediately closed
5. **Conclusion**: QuestDB is not accepting connections = OFFLINE

### QuestDB Connection Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Python Application (questdb_provider.py)              │
│                                                         │
│  ┌────────────────────────────────────────┐            │
│  │  Sender Pool (5 persistent connections)│            │
│  │  [Sender1] [Sender2] [Sender3] ...     │            │
│  └────────────────────────────────────────┘            │
│                    │ TCP (port 9009)                    │
└────────────────────┼───────────────────────────────────┘
                     │
                     ▼
       ┌─────────────────────────────┐
       │     QuestDB Server          │
       │  (must be running!)         │
       │                             │
       │  - ILP port: 9009           │
       │  - PostgreSQL: 8812         │
       │  - Web UI: 9000             │
       └─────────────────────────────┘
```

## Common Issues and Solutions

### Issue 1: Port Already in Use

**Symptom**:
```
Address already in use (10048)
```

**Solution**:
```powershell
# Find process using port 9009
netstat -ano | findstr :9009

# Kill the process (replace PID with actual process ID)
taskkill /PID 12345 /F

# Restart QuestDB
python database\questdb\install_questdb.py
```

### Issue 2: Firewall Blocking

**Symptom**:
```
Connection refused / timeout
```

**Solution**:
1. Check Windows Firewall settings
2. Add exception for ports 9000, 9009, 8812
3. Or temporarily disable firewall for testing

### Issue 3: QuestDB Crashes on Start

**Symptom**:
```
QuestDB starts but immediately exits
```

**Solution**:
1. Check QuestDB logs in installation directory
2. Look for errors in `questdb.log`
3. Common causes:
   - Corrupted database files → Delete data directory and restart
   - Java version mismatch → Ensure Java 11+ is installed
   - Insufficient memory → Increase Java heap size

## Verification Checklist

Before running orderbook tests, verify:

- [ ] QuestDB process is running (check task manager)
- [ ] Port 9009 is listening (netstat)
- [ ] Web UI accessible at http://127.0.0.1:9000
- [ ] Can run simple query in Web UI
- [ ] No firewall blocking ports
- [ ] No antivirus blocking connections

## Still Having Issues?

If QuestDB is running but tests still fail:

1. **Check QuestDB logs**:
   - Location: `<questdb-install-dir>/log/questdb.log`
   - Look for connection errors or rejections

2. **Test direct connection**:
   ```python
   from questdb.ingress import Sender, Protocol

   # This should NOT raise an error
   sender = Sender(Protocol.Tcp, 'localhost', 9009)
   print("✅ Sender created successfully!")
   sender.close()
   ```

3. **Restart everything**:
   - Stop QuestDB
   - Clear any stale connections: `taskkill /F /IM java.exe`
   - Wait 10 seconds
   - Restart QuestDB
   - Re-run tests

4. **Check network configuration**:
   - Ensure localhost (127.0.0.1) is accessible
   - Try `ping 127.0.0.1` - should work
   - Check hosts file: `C:\Windows\System32\drivers\etc\hosts`

## Summary

**The "Sender is closed" error means QuestDB is offline or unreachable.**

**Quick fix**:
1. Start QuestDB: `python database\questdb\install_questdb.py`
2. Verify: Open http://127.0.0.1:9000 in browser
3. Re-run: `python test_real_orderbook_write.py`

**Code improvements made**:
- ✅ Better error messages when QuestDB is offline
- ✅ Sender health validation (best effort)
- ✅ Clearer diagnostics for troubleshooting

The fix ensures you'll get a clear, actionable error message when QuestDB is offline, instead of cryptic "Sender is closed" errors.
