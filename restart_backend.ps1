# Restart Backend Script
Write-Host "Stopping backend processes..."

# Find and kill processes using port 8080
$portInfo = netstat -ano | Select-String ":8080 " | ForEach-Object {
    $parts = $_ -split '\s+'
    $parts[-1]
} | Select-Object -Unique | Where-Object { $_ -match '^\d+$' -and $_ -ne '0' }

foreach ($procId in $portInfo) {
    Write-Host "Killing process $procId using port 8080"
    try {
        Stop-Process -Id $procId -Force -ErrorAction Stop
        Write-Host "Killed process $procId"
    } catch {
        Write-Host "Could not kill process $procId : $_"
    }
}

Start-Sleep -Seconds 2

Write-Host "Starting backend..."
Set-Location "c:\Users\lukasz.krysik\Desktop\FXcrypto\FX_code_AI_v2"

# Start new backend
Start-Process python -ArgumentList "-m", "uvicorn", "src.api.unified_server:create_unified_app", "--factory", "--host", "0.0.0.0", "--port", "8080" -NoNewWindow

Write-Host "Backend restarting... please wait 5 seconds"
Start-Sleep -Seconds 5

# Verify
$response = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing -ErrorAction SilentlyContinue
if ($response.StatusCode -eq 200) {
    Write-Host "Backend is running!"
} else {
    Write-Host "Backend may not be ready yet"
}
