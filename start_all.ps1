# Set the title of the console
$Host.UI.RawUI.WindowTitle = "FXcrypto Backend & Frontend"

# Start QuestDB
$questDbPath = "C:\Users\lukasz.krysik\Desktop\FXcrypto\questdb-9.1.0-rt-windows-x86-64\bin\questdb.exe"
if (Test-Path $questDbPath) {
    Write-Host "Starting QuestDB..." -ForegroundColor Green
    Start-Process -FilePath $questDbPath -WorkingDirectory (Split-Path $questDbPath)

    # Wait for QuestDB to be ready
    Write-Host "Waiting for QuestDB to be ready..." -ForegroundColor Yellow
    $maxAttempts = 30
    $attempt = 0
    $questDbReady = $false

    while ($attempt -lt $maxAttempts -and -not $questDbReady) {
        $attempt++
        try {
            # Test PostgreSQL wire protocol port (8812)
            $tcpClient = New-Object System.Net.Sockets.TcpClient
            $tcpClient.Connect("127.0.0.1", 8812)
            $tcpClient.Close()

            # Test Web UI port (9000)
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:9000" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $questDbReady = $true
                Write-Host "QuestDB is ready!" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "." -NoNewline
            Start-Sleep -Seconds 1
        }
    }

    if (-not $questDbReady) {
        Write-Host ""
        Write-Host "WARNING: QuestDB may not be fully ready. Check http://127.0.0.1:9000" -ForegroundColor Yellow
    }
}
else {
    Write-Host "QuestDB executable not found at $questDbPath" -ForegroundColor Red
    Write-Host "Please install QuestDB using: python database/questdb/install_questdb.py" -ForegroundColor Yellow
    exit 1
}

# Start the backend server
Write-Host ""
Write-Host "Starting backend server on port 8080..." -ForegroundColor Green
Start-Process python -ArgumentList "-m", "uvicorn", "src.api.unified_server:create_unified_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--reload"

# Wait for backend to be ready
Write-Host "Waiting for backend to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Kill any existing Node.js processes on port 3000
Write-Host ""
Write-Host "Checking for existing processes on port 3000..." -ForegroundColor Yellow
$existingProcess = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1
if ($existingProcess) {
    Write-Host "Killing existing process on port 3000 (PID: $existingProcess)..." -ForegroundColor Yellow
    Stop-Process -Id $existingProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Start the frontend server in a new window
Write-Host ""
Write-Host "Starting frontend server on port 3000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "Push-Location -Path frontend; npm run dev; Pop-Location"

# Wait a bit for the frontend to start and then open the browser
Write-Host "Waiting for frontend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10 # Adjust this delay if needed

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "FXcrypto Backend & Frontend Started!" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8080" -ForegroundColor White
Write-Host "Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "QuestDB:  http://localhost:9000" -ForegroundColor White
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Opening frontend in browser..." -ForegroundColor Green
Start-Process "http://localhost:3000/"
