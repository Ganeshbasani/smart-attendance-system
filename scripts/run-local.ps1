$ErrorActionPreference = "Stop"
Write-Host "Starting AttendX backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..\backend'; python -m uvicorn app.main:app --reload --port 8000"
Write-Host "Starting AttendX frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..\frontend'; npm install; npm run dev"
Start-Sleep -Seconds 2
Start-Process "http://localhost:5173"
