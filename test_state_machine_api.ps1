# Test State Machine API Endpoints (PowerShell)
# Prerequisites: Backend server running on localhost:8080

$ErrorActionPreference = "Stop"

$BaseUrl = "http://localhost:8080"
$SessionId = ""

Write-Host "=== State Machine API Test Suite ===" -ForegroundColor Green
Write-Host ""

# Test 1: Get state for non-existent session (should return IDLE)
Write-Host "Test 1: Get state for non-existent session" -ForegroundColor Cyan
$response = Invoke-RestMethod -Uri "$BaseUrl/api/sessions/unknown_session/state" -Method Get
$response | ConvertTo-Json -Depth 10
Write-Host ""

# Test 2: Start a paper trading session
Write-Host "Test 2: Starting paper trading session..." -ForegroundColor Cyan
$startBody = @{
    symbols = @("BTC_USDT", "ETH_USDT")
    session_type = "paper"
    strategy_config = @{
        strategy_name = "pump_peak_short"
        direction = "SHORT"
        signal_detection = @{
            conditions = @(
                @{
                    name = "pump_magnitude_pct"
                    operator = "gte"
                    value = 5.0
                }
            )
        }
    }
} | ConvertTo-Json -Depth 10

try {
    $sessionResponse = Invoke-RestMethod -Uri "$BaseUrl/sessions/start" -Method Post -Body $startBody -ContentType "application/json"
    $sessionResponse | ConvertTo-Json -Depth 10

    # Extract session_id
    if ($sessionResponse.data.session_id) {
        $SessionId = $sessionResponse.data.session_id
    } elseif ($sessionResponse.session_id) {
        $SessionId = $sessionResponse.session_id
    }

    if (-not $SessionId) {
        Write-Host "ERROR: Failed to extract session_id" -ForegroundColor Red
        exit 1
    }

    Write-Host "Session ID: $SessionId" -ForegroundColor Yellow
    Write-Host ""
} catch {
    Write-Host "ERROR: Failed to start session: $_" -ForegroundColor Red
    exit 1
}

# Wait for session to start
Start-Sleep -Seconds 2

# Test 3: Get session state (should be RUNNING)
Write-Host "Test 3: Get session state (should be RUNNING)" -ForegroundColor Cyan
$stateResponse = Invoke-RestMethod -Uri "$BaseUrl/api/sessions/$SessionId/state" -Method Get
$stateResponse | ConvertTo-Json -Depth 10
Write-Host ""

# Test 4: Get session transitions (should be empty - placeholder)
Write-Host "Test 4: Get session transitions (should be empty)" -ForegroundColor Cyan
$transitionsResponse = Invoke-RestMethod -Uri "$BaseUrl/api/sessions/$SessionId/transitions" -Method Get
$transitionsResponse | ConvertTo-Json -Depth 10
Write-Host ""

# Test 5: Verify allowed_transitions for RUNNING state
Write-Host "Test 5: Verify allowed_transitions" -ForegroundColor Cyan
if ($stateResponse.allowed_transitions) {
    $allowedTransitions = $stateResponse.allowed_transitions
} elseif ($stateResponse.data.allowed_transitions) {
    $allowedTransitions = $stateResponse.data.allowed_transitions
}
Write-Host "Allowed transitions from RUNNING: $($allowedTransitions -join ', ')" -ForegroundColor Yellow
Write-Host ""

# Test 6: Verify instances list (strategy × symbol)
Write-Host "Test 6: Verify instances list" -ForegroundColor Cyan
if ($stateResponse.instances) {
    $instances = $stateResponse.instances
} elseif ($stateResponse.data.instances) {
    $instances = $stateResponse.data.instances
}
Write-Host "Active instances:" -ForegroundColor Yellow
$instances | ConvertTo-Json -Depth 10
Write-Host ""

# Test 7: Stop session
Write-Host "Test 7: Stopping session..." -ForegroundColor Cyan
$stopBody = @{
    session_id = $SessionId
} | ConvertTo-Json

$stopResponse = Invoke-RestMethod -Uri "$BaseUrl/sessions/stop" -Method Post -Body $stopBody -ContentType "application/json"
$stopResponse | ConvertTo-Json -Depth 10
Write-Host ""

# Wait for session to stop
Start-Sleep -Seconds 2

# Test 8: Get session state after stop (should be STOPPED)
Write-Host "Test 8: Get session state after stop (should be STOPPED)" -ForegroundColor Cyan
$finalStateResponse = Invoke-RestMethod -Uri "$BaseUrl/api/sessions/$SessionId/state" -Method Get
$finalStateResponse | ConvertTo-Json -Depth 10
Write-Host ""

Write-Host "=== Test Suite Complete ===" -ForegroundColor Green
