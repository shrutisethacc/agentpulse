# AI Evals Framework - Session Startup Script
# Run this at the start of every session to ensure all services are up.
# Usage: .\start.ps1

$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"   # uv lives here for the current user
$env:PYTHONUTF8 = "1"
$env:MLFLOW_ALLOW_FILE_STORE = "true"   # MLflow 3.x deprecated file store; opt-in to keep ./mlruns
$base = $PSScriptRoot
$venv = "C:\AgentPulse-venv"   # venv is outside OneDrive to avoid filesystem/Defender conflicts

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

# 1. MLflow
Write-Host "[1/4] MLflow UI (port 5001) ..." -NoNewline
if (Test-Port 5001) {
    Write-Host " RUNNING  -> http://localhost:5001" -ForegroundColor Green
} else {
    Write-Host " NOT RUNNING - starting ..." -ForegroundColor Yellow
    Start-Process -FilePath "$venv\Scripts\python.exe" `
        -ArgumentList "-m","mlflow","ui","--host","127.0.0.1","--port","5001",
                      "--backend-store-uri","sqlite:///mlflow.db",
                      "--serve-artifacts" `
        -WorkingDirectory $base -WindowStyle Minimized
    Write-Host "      Waiting for MLflow to be ready ..." -ForegroundColor Yellow
    $waited = 0
    do { Start-Sleep -Seconds 2; $waited += 2 } until ((Test-Http "http://localhost:5001") -or $waited -ge 60)
    if (Test-Http "http://localhost:5001") {
        Write-Host "      MLflow ready. ($waited s)" -ForegroundColor Green
    } else {
        Write-Host "      MLflow did not respond in 60s - check taskbar window." -ForegroundColor Red
    }
}

# 2. Agent API
Write-Host "[2/4] Agent API (port 8001) ..." -NoNewline
if (Test-Port 8001) {
    Write-Host " RUNNING  -> http://localhost:8001/health" -ForegroundColor Green
} else {
    Write-Host " NOT RUNNING - starting ..." -ForegroundColor Yellow
    Start-Process -FilePath "$venv\Scripts\python.exe" `
        -ArgumentList "-m","uvicorn","agents.pipeline:app","--host","127.0.0.1","--port","8001" `
        -WorkingDirectory $base -WindowStyle Hidden `
        -RedirectStandardError "$env:TEMP\agent_api_err.log"
    Write-Host "      Waiting for Agent API (LangGraph + FAISS init takes ~60s) ..." -ForegroundColor Yellow
    $waited = 0
    do { Start-Sleep -Seconds 5; $waited += 5 } until ((Test-Http "http://localhost:8001/health") -or $waited -ge 180)
    if (Test-Http "http://localhost:8001/health") {
        Write-Host "      Agent API ready. ($waited s)" -ForegroundColor Green
    } else {
        Write-Host "      Agent API did not respond in 180s - check: $env:TEMP\agent_api_err.log" -ForegroundColor Red
    }
}

# 3. Streamlit Dashboard
Write-Host "[3/4] Streamlit Dashboard (port 8501) ..." -NoNewline
if (Test-Port 8501) {
    Write-Host " RUNNING  -> http://localhost:8501" -ForegroundColor Green
} else {
    Write-Host " NOT RUNNING - starting ..." -ForegroundColor Yellow
    Start-Process -FilePath "$venv\Scripts\python.exe" `
        -ArgumentList "-m","streamlit","run","dashboard/app.py","--server.port","8501","--server.headless","true" `
        -WorkingDirectory $base -WindowStyle Hidden `
        -RedirectStandardError "$env:TEMP\streamlit_err.log"
    Write-Host "      Streamlit launched. Open http://localhost:8501 in ~10s." -ForegroundColor Yellow
}

# 4. Locust UI (on standby - no test running until you trigger from browser)
Write-Host "[4/4] Locust UI (port 8089) ..." -NoNewline
if (Test-Port 8089) {
    Write-Host " RUNNING  -> http://localhost:8089" -ForegroundColor Green
} else {
    Write-Host " NOT RUNNING - starting ..." -ForegroundColor Yellow
    Start-Process -FilePath "$venv\Scripts\python.exe" `
        -ArgumentList "-m","locust","-f","load_tests\locustfile.py","--host","http://127.0.0.1:8001" `
        -WorkingDirectory $base -WindowStyle Hidden `
        -RedirectStandardError "$env:TEMP\locust_err.log"
    Write-Host "      Locust UI launched. Open http://localhost:8089 in ~5s." -ForegroundColor Yellow
    Write-Host "      Set users + spawn rate in the browser, then click Start Swarming." -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "-----------------------------------------"
Write-Host "  Service URLs"
Write-Host "-----------------------------------------"
Write-Host "  MLflow UI  : http://localhost:5001"
Write-Host "  Agent API  : http://127.0.0.1:8001"
Write-Host "  Streamlit  : http://localhost:8501"
Write-Host "  Locust UI  : http://localhost:8089   (set users + spawn rate, click Start)"
Write-Host ""
Write-Host "  LLM        : Azure OpenAI gpt-5.2-chat-2 (responses + embeddings + eval judge)"
Write-Host ""
Write-Host "  Quick test once Agent API is ready:"
Write-Host '  Invoke-WebRequest http://localhost:8001/invoke -Method POST -ContentType "application/json" -Body ''{"query":"My VPN is not working"}'' -UseBasicParsing'
Write-Host ""
Write-Host "  Phase status:"
Write-Host "    Phase 1 - Setup: venv (uv), MLflow 3.14.0, Azure OpenAI      DONE"
Write-Host "    Phase 2 - LangGraph agent + FastAPI + MLflow tracing         DONE"
Write-Host "    Phase 3 - FAISS RAG + Locust load test                       DONE"
Write-Host "    Phase 4 - DeepEval quality scoring (11 metrics)              DONE"
Write-Host "    Phase 5 - Streamlit dashboard + PDF report                   DONE"
Write-Host "-----------------------------------------"
Write-Host ""
