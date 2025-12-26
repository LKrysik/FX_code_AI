# Set the title of the console
$Host.UI.RawUI.WindowTitle = "FXcrypto Backend & Frontend"

# Create logs directory for agent-accessible output
$logsDir = Join-Path $PSScriptRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
    Write-Host "Created logs directory: $logsDir" -ForegroundColor Gray
}

# Clear old log files
$backendLog = Join-Path $logsDir "backend.log"
$backendErrorLog = Join-Path $logsDir "backend_error.log"
$frontendLog = Join-Path $logsDir "frontend.log"
$questdbLog = Join-Path $logsDir "questdb.log"

# Initialize log files with timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$timestamp] Starting FXcrypto services..." | Out-File -FilePath $backendLog -Encoding utf8
"[$timestamp] Backend error log" | Out-File -FilePath $backendErrorLog -Encoding utf8
"[$timestamp] Starting frontend..." | Out-File -FilePath $frontendLog -Encoding utf8
"[$timestamp] Starting QuestDB..." | Out-File -FilePath $questdbLog -Encoding utf8

Write-Host "Logs directory: $logsDir" -ForegroundColor Gray
Write-Host "  - backend.log, backend_error.log" -ForegroundColor Gray
Write-Host "  - frontend.log" -ForegroundColor Gray
Write-Host "  - questdb.log" -ForegroundColor Gray
Write-Host ""

# Start QuestDB
$questDbPath = "C:\Users\lukasz.krysik\Desktop\FXcrypto\questdb-9.1.0-rt-windows-x86-64\bin\questdb.exe"
$questdbErrorLog = Join-Path $logsDir "questdb_error.log"
"[$timestamp] QuestDB error log" | Out-File -FilePath $questdbErrorLog -Encoding utf8

if (Test-Path $questDbPath) {
    Write-Host "Starting QuestDB..." -ForegroundColor Green
    # QuestDB needs to run without output redirection (it manages its own logs)
    # Use -WindowStyle Minimized to keep it accessible but not in the way
    Start-Process -FilePath $questDbPath -WorkingDirectory (Split-Path $questDbPath) -WindowStyle Minimized

    # Wait for QuestDB to be ready (increased timeout for cold start)
    Write-Host "Waiting for QuestDB to be ready..." -ForegroundColor Yellow
    $maxAttempts = 60
    $attempt = 0
    $questDbReady = $false

    while ($attempt -lt $maxAttempts -and -not $questDbReady) {
        $attempt++
        try {
            # Test PostgreSQL wire protocol port (8812) - this is what the backend needs
            $tcpClient = New-Object System.Net.Sockets.TcpClient
            $tcpClient.Connect("127.0.0.1", 8812)
            $tcpClient.Close()

            # Also verify Web UI is responding (9000)
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:9000" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $questDbReady = $true
                Write-Host ""
                Write-Host "QuestDB is ready! (port 8812 + web UI)" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "." -NoNewline
            Start-Sleep -Seconds 1
        }
    }

    if (-not $questDbReady) {
        Write-Host ""
        Write-Host "ERROR: QuestDB failed to start within 60 seconds!" -ForegroundColor Red
        Write-Host "Check http://127.0.0.1:9000 manually" -ForegroundColor Yellow
        Write-Host "Backend will likely fail to connect to port 8812" -ForegroundColor Yellow
        # Don't exit - let user see what happens
    }
}
else {
    Write-Host "QuestDB executable not found at $questDbPath" -ForegroundColor Red
    Write-Host "Please install QuestDB using: python database/questdb/install_questdb.py" -ForegroundColor Yellow
    exit 1
}

# Start the backend server with output redirection
Write-Host ""
Write-Host "Starting backend server on port 8080..." -ForegroundColor Green
Write-Host "Backend logs: $backendLog" -ForegroundColor Gray

# Use cmd wrapper for proper output capture with uvicorn
$backendCmd = "python -m uvicorn src.api.unified_server:create_unified_app --factory --host 0.0.0.0 --port 8080 --reload"
Start-Process cmd -ArgumentList "/c", "$backendCmd >> `"$backendLog`" 2>> `"$backendErrorLog`"" -WindowStyle Hidden

# Wait for backend to be ready with health check
Write-Host "Waiting for backend to be ready..." -ForegroundColor Yellow
$backendReady = $false
$maxBackendAttempts = 30
$backendAttempt = 0

while ($backendAttempt -lt $maxBackendAttempts -and -not $backendReady) {
    $backendAttempt++
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
            Write-Host "Backend is ready!" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "." -NoNewline
        # Check for errors in log
        if (Test-Path $backendErrorLog) {
            $errorContent = Get-Content $backendErrorLog -Tail 5 -ErrorAction SilentlyContinue
            if ($errorContent -match "Error|Exception|Failed") {
                Write-Host ""
                Write-Host "ERROR detected in backend startup!" -ForegroundColor Red
                Write-Host "Check $backendErrorLog for details" -ForegroundColor Yellow
                Write-Host "Last few lines:" -ForegroundColor Yellow
                $errorContent | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
                break
            }
        }
    }
}

if (-not $backendReady) {
    Write-Host ""
    Write-Host "WARNING: Backend may not be ready. Check logs/backend_error.log" -ForegroundColor Yellow
}

# Kill any existing Node.js processes on port 3000
Write-Host ""
Write-Host "Checking for existing processes on port 3000..." -ForegroundColor Yellow
$existingProcess = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1
if ($existingProcess) {
    Write-Host "Killing existing process on port 3000 (PID: $existingProcess)..." -ForegroundColor Yellow
    Stop-Process -Id $existingProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Start the frontend server with output redirection
Write-Host ""
Write-Host "Starting frontend server on port 3000..." -ForegroundColor Green
Write-Host "Frontend logs: $frontendLog" -ForegroundColor Gray

$frontendCmd = "cd frontend && npm run dev"
Start-Process cmd -ArgumentList "/c", "$frontendCmd >> `"$frontendLog`" 2>&1" -WindowStyle Hidden

# Wait for frontend to be ready
Write-Host "Waiting for frontend to start..." -ForegroundColor Yellow
$frontendReady = $false
$maxFrontendAttempts = 30
$frontendAttempt = 0

while ($frontendAttempt -lt $maxFrontendAttempts -and -not $frontendReady) {
    $frontendAttempt++
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $frontendReady = $true
            Write-Host "Frontend is ready!" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "." -NoNewline
    }
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "FXcrypto Backend & Frontend Started!" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8080" -ForegroundColor White
Write-Host "Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "QuestDB:  http://localhost:9000" -ForegroundColor White
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Log files (agent-accessible):" -ForegroundColor Gray
Write-Host "  Backend:  $backendLog" -ForegroundColor Gray
Write-Host "  Errors:   $backendErrorLog" -ForegroundColor Gray
Write-Host "  Frontend: $frontendLog" -ForegroundColor Gray
Write-Host "  QuestDB:  $questdbLog" -ForegroundColor Gray
Write-Host ""

Write-Host "Opening frontend in browser..." -ForegroundColor Green
Start-Process "http://localhost:3000/"
