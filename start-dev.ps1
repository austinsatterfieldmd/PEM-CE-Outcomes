# CE Outcomes Dashboard - Development Startup Script
# Runs both backend API (SQLite) and frontend together
# All edits will be automatically saved to SQLite database

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  CE Outcomes Dashboard - Development Mode" -ForegroundColor Cyan
Write-Host "  All edits will save to SQLite automatically" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found. Please install Python 3.9+" -ForegroundColor Red
    exit 1
}

# Check if Node is available
try {
    $nodeVersion = node --version 2>&1
    Write-Host "[OK] Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Node.js not found. Please install Node.js" -ForegroundColor Red
    exit 1
}

# Start Backend API server in background
Write-Host ""
Write-Host "Starting Backend API (port 8000)..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location $root
    python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
} -ArgumentList $projectRoot

# Wait a moment for backend to initialize
Write-Host "Waiting for backend to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# Check if backend is running
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "[OK] Backend API is running at http://127.0.0.1:8000" -ForegroundColor Green
    Write-Host "     API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Gray
} catch {
    Write-Host "[WARNING] Backend may still be starting..." -ForegroundColor Yellow
}

# Start Frontend
Write-Host ""
Write-Host "Starting Frontend (port 5173)..." -ForegroundColor Yellow
Set-Location "$projectRoot\dashboard\frontend"

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Dashboard: http://localhost:5173" -ForegroundColor White
Write-Host "  API Docs:  http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  Database:  dashboard/data/questions.db" -ForegroundColor White
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop both servers" -ForegroundColor Gray
Write-Host ""

# Run frontend in foreground (blocking)
try {
    npm run dev
} finally {
    # Cleanup: Stop backend job when frontend exits
    Write-Host ""
    Write-Host "Stopping backend server..." -ForegroundColor Yellow
    Stop-Job -Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $backendJob -ErrorAction SilentlyContinue
    Write-Host "Servers stopped." -ForegroundColor Green
}
