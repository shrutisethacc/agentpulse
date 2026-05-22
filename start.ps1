# AI Evals Framework - Session Startup Script
# Run this at the start of every session to ensure all services are up.
# Usage: .\start.ps1

$env:Path = "C:\Users\shruti.s.seth\.local\bin;$env:Path"
$env:PYTHONUTF8 = "1"
$base = $PSScriptRoot

function Test-Port {
    param([int]$Port)
    $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Test-Http {
    param([string]$Url)
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        return $r.StatusCode -lt 500
    } catch { return $false }
}

Write-Host ""
Write-Host "========================================="
Write-Host "  AI Evals Framework - Session Startup"
Write-Host "========================================="
Write-Host ""

# 1. Ollama
Write-Host "[1/3] Ollama (port 11434) ..." -NoNewline
if (Test-Http "http://localhost:11434/api/tags") {
    Write-Host " RUNNING" -ForegroundColor Green
} else {
    Write-Host " NOT RUNNING - starting ..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Write-Host "      Ollama launched. Allow 10s to load before first LLM call." -ForegroundColor Yellow
}

# 2. MLflow
Write-Host "[2/3] MLflow UI (port 5000) ..." -NoNewline
if (Test-Port 5000) {
    Write-Host " RUNNING  -> http://localhost:5000" -ForegroundColor Green
} else {
    Write-Host " NOT RUNNING - starting ..." -ForegroundColor Yellow
    Start-Process -FilePath "$base\.venv\Scripts\mlflow.exe" `
        -ArgumentList "ui","--host","127.0.0.1","--port","5000" `
        -WorkingDirectory $base -WindowStyle Hidden
    Write-Host "      MLflow launched. Open http://localhost:5000 in ~30s." -ForegroundColor Yellow
}

# 3. Agent API
Write-Host "[3/4] Agent API (port 8001) ..." -NoNewline
if (Test-Port 8001) {
    Write-Host " RUNNING  -> http://localhost:8001/health" -ForegroundColor Green
} else {
    Write-Host " NOT RUNNING - starting ..." -ForegroundColor Yellow
    Start-Process -FilePath "$base\.venv\Scripts\python.exe" `
        -ArgumentList "-m","uvicorn","agents.pipeline:app","--host","127.0.0.1","--port","8001" `
        -WorkingDirectory $base -WindowStyle Hidden `
        -RedirectStandardError "$env:TEMP\agent_api_err.log"
    Write-Host "      Agent API launched. Ready in ~30s (first Ollama call takes ~2min cold start)." -ForegroundColor Yellow
    Write-Host "      Error log: $env:TEMP\agent_api_err.log" -ForegroundColor DarkGray
}

# 4. Streamlit Dashboard
Write-Host "[4/4] Streamlit Dashboard (port 8501) ..." -NoNewline
if (Test-Port 8501) {
    Write-Host " RUNNING  -> http://localhost:8501" -ForegroundColor Green
} else {
    Write-Host " NOT RUNNING - starting ..." -ForegroundColor Yellow
    Start-Process -FilePath "$base\.venv\Scripts\python.exe" `
        -ArgumentList "-m","streamlit","run","dashboard/app.py","--server.port","8501","--server.headless","true" `
        -WorkingDirectory $base -WindowStyle Hidden `
        -RedirectStandardError "$env:TEMP\streamlit_err.log"
    Write-Host "      Streamlit launched. Open http://localhost:8501 in ~10s." -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "-----------------------------------------"
Write-Host "  Service URLs"
Write-Host "-----------------------------------------"
Write-Host "  MLflow UI  : http://localhost:5000"
Write-Host "  Agent API  : http://localhost:8001"
Write-Host "  Streamlit  : http://localhost:8501"
Write-Host "  Ollama     : http://localhost:11434"
Write-Host "  Locust     : http://localhost:8089   (start manually for load tests)"
Write-Host ""
Write-Host "  Quick test once Agent API is ready:"
Write-Host '  Invoke-WebRequest http://localhost:8001/invoke -Method POST -ContentType "application/json" -Body ''{"query":"My VPN is not working"}'' -UseBasicParsing'
Write-Host ""
Write-Host "  Phase status:"
Write-Host "    Phase 1 - Setup: venv (uv), MLflow 2.22.5, Ollama       DONE"
Write-Host "    Phase 2 - LangGraph agent + FastAPI + MLflow tracing     DONE"
Write-Host "    Phase 3 - FAISS RAG + Locust load test                   DONE"
Write-Host "    Phase 4 - DeepEval quality scoring (11 metrics)          DONE"
Write-Host "    Phase 5 - Streamlit dashboard + PDF report               DONE"
Write-Host "-----------------------------------------"
Write-Host ""
