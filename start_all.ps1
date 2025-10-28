# Set the title of the console
$Host.UI.RawUI.WindowTitle = "FXcrypto Backend & Frontend"

# Start QuestDB
$questDbPath = "C:\Users\lukasz.krysik\Desktop\FXcrypto\questdb-9.1.0-rt-windows-x86-64\bin\questdb.exe"
if (Test-Path $questDbPath) {
    Write-Host "Starting QuestDB..."
    Start-Process -FilePath $questDbPath -WorkingDirectory (Split-Path $questDbPath)
}
else {
    Write-Host "QuestDB executable not found at $questDbPath" -ForegroundColor Red
}

# Start the backend server
Write-Host "Starting backend server..."
Start-Process python -ArgumentList "-m uvicorn src.api.unified_server:app --host 0.0.0.0 --port 8080"

# Start the frontend server in a new window
Write-Host "Starting frontend server..."
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "Push-Location -Path frontend; npm run dev; Pop-Location"

# Wait a bit for the frontend to start and then open the browser
Write-Host "Waiting for frontend to start..."
Start-Sleep -Seconds 10 # Adjust this delay if needed

Write-Host "Opening frontend in browser..."
Start-Process "http://localhost:3000/"
