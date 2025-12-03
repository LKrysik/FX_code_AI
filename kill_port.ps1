# Kill process on port 8080
$port = 8080
$connections = netstat -ano | Select-String ":$port "
foreach ($conn in $connections) {
    $parts = $conn -split '\s+'
    $pid = $parts[-1]
    if ($pid -match '^\d+$' -and $pid -ne '0') {
        Write-Host "Killing process $pid"
        try {
            Stop-Process -Id $pid -Force -ErrorAction Stop
            Write-Host "Killed $pid successfully"
        } catch {
            Write-Host "Could not kill $pid : $_"
        }
    }
}
Write-Host "Done"
