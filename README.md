# AgentPulse — AI Agent Evaluation Framework

> Built by **Shruti Seth** · Manager, Performance Engineering · Accenture Technology QE Capability

An enterprise-grade, locally runnable platform that **performance tests and evaluates AI agents** — measuring quality, speed, cost, and safety under concurrent load.

**This is NOT a chatbot.** It is a framework for organisations adopting AI agents who need to answer: *"Is our agent good enough for production? Will quality hold under load?"*

---

## What It Does

```
User Query
    ↓
[1. Intent Classifier]      → classifies: VPN / PASSWORD / HARDWARE / SOFTWARE / OTHER
    ↓
[2. Knowledge Retriever]    → semantic RAG over IT runbooks (FAISS + Ollama embeddings)
    ↓
[3. Response Generator]     → Azure OpenAI gpt-5.2-chat-2 generates resolution
    ↓
[4. Escalation Decider]     → L1 resolved? or route to L2/L3?
    ↓
MLflow trace + 17 metrics logged per run
```

Every run is scored by **DeepEval** (8 quality metrics) and tracked in **MLflow** — then shown live in a **Streamlit dashboard** with 6 tabs covering quality, load, cost, and safety.

---

## Tech Stack

| Component | Tool | Version |
|-----------|------|---------|
| LLM (agent responses) | Azure OpenAI `gpt-5.2-chat-2` | Accenture subscription |
| LLM (eval judge) | Azure OpenAI `gpt-5.2-chat-2` via `AzureJudge` | DeepEval custom wrapper |
| Embeddings (RAG) | Ollama `nomic-embed-text` | Port 11434 |
| Agent framework | LangGraph | 0.2.60 |
| Experiment tracking | MLflow | 2.22.5 |
| Quality evaluation | DeepEval | 4.0.2 |
| Load testing | Locust | 2.32.3 |
| Live dashboard | Streamlit | 1.41.1 |
| Vector store (RAG) | FAISS | 1.9.0 |
| API server | FastAPI + Uvicorn | 0.115.6 |
| PDF export | Playwright (chromium) | 1.44+ |
| Package manager | uv | latest |

---

## Prerequisites

Install these before running anything:

1. **Python 3.12** — [python.org](https://www.python.org/downloads/)
2. **Ollama** — [ollama.com](https://ollama.com) — used only for FAISS embeddings:
   ```powershell
   ollama pull nomic-embed-text   # Embeddings for FAISS RAG (agent responses use Azure OpenAI)
   ```
3. **Azure OpenAI credentials** — create `.env` in `ai-evals-framework/` with:

   ```env
   AZURE_OPENAI_ENDPOINT=https://<your-endpoint>.cognitiveservices.azure.com/
   AZURE_OPENAI_API_KEY=<your-key>
   AZURE_OPENAI_DEPLOYMENT=<deployment-name>
   AZURE_OPENAI_API_VERSION=2024-12-01-preview
   ```
4. **uv** (fast Python package manager):
   ```powershell
   pip install uv
   ```

---

## Setup (Windows)

```powershell
# 1. Clone the repo
git clone https://github.com/<your-username>/agentpulse.git
cd agentpulse\AIEvals\ai-evals-framework

# 2. Add uv to PATH (if not already)
$env:Path = "C:\Users\$env:USERNAME\.local\bin;$env:Path"

# 3. Create virtual environment using Python 3.12
uv venv --python C:\Python312\python.exe

# 4. Install all dependencies
uv pip install -r requirements.txt --python .venv\Scripts\python.exe
```

> **Important:** Always use `.venv\Scripts\python.exe` directly — not `uv run python`, which resolves to system Python and has the wrong DeepEval version.

---

## Services Overview

AgentPulse requires **4 services running simultaneously**:

| Service | Port | Purpose |
|---------|------|---------|
| Ollama | 11434 | Embeddings only — nomic-embed-text for FAISS RAG |
| Azure OpenAI | cloud | Agent LLM responses + DeepEval judge (gpt-5.2-chat-2) |
| MLflow UI | 5000 | Experiment tracking, traces, artifact store |
| Agent API | 8001 | FastAPI `/invoke` endpoint — the agent pipeline |
| Streamlit Dashboard | 8501 | Live metrics dashboard |

---

## Running AgentPulse

### Step 1 — Start Ollama

Ollama must be running before the agent API or eval scoring can work.

```powershell
# Windows: Ollama installs to AppData — start it manually
$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
Start-Process $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
Start-Sleep 10

# Verify Ollama is up
Invoke-WebRequest http://localhost:11434/api/tags -UseBasicParsing | Select-Object StatusCode
```

### Step 2 — Start MLflow, Agent API, and Streamlit

```powershell
$base = "path\to\ai-evals-framework"
$env:Path = "C:\Users\$env:USERNAME\.local\bin;$env:Path"
$env:PYTHONUTF8 = "1"
& "$base\start.ps1"
```

`start.ps1` checks each service and only starts those that are not already running.

### Step 3 — Verify all services are up

```powershell
# Should return 200 / OK for each
Invoke-WebRequest http://localhost:11434/api/tags  -UseBasicParsing | Select-Object StatusCode  # Ollama
Invoke-WebRequest http://127.0.0.1:5000            -UseBasicParsing | Select-Object StatusCode  # MLflow
Invoke-WebRequest http://127.0.0.1:8001/health     -UseBasicParsing | Select-Object StatusCode  # Agent API
Invoke-WebRequest http://localhost:8501            -UseBasicParsing | Select-Object StatusCode  # Streamlit
```

> **Windows note:** Use `http://127.0.0.1` (not `http://localhost`) for the Agent API and MLflow — on some Windows machines `localhost` resolves to IPv6 (`::1`) and the connection is refused.

### Send a test query

```powershell
$body = '{"query":"My VPN keeps disconnecting every 30 minutes"}'
Invoke-WebRequest -Uri "http://127.0.0.1:8001/invoke" `
  -Method POST -ContentType "application/json" `
  -Body $body -UseBasicParsing | Select-Object -ExpandProperty Content
```

### Manual service start (if start.ps1 is unavailable)

```powershell
$base = "path\to\ai-evals-framework"
$env:PYTHONUTF8 = "1"

# 1. MLflow
Start-Process "$base\.venv\Scripts\mlflow.exe" `
    -ArgumentList "ui","--host","127.0.0.1","--port","5000","--backend-store-uri","mlruns" `
    -WorkingDirectory $base -WindowStyle Hidden

# 2. Agent API
Start-Process "$base\.venv\Scripts\python.exe" `
    -ArgumentList "-m","uvicorn","agents.pipeline:app","--host","127.0.0.1","--port","8001" `
    -WorkingDirectory $base -WindowStyle Hidden

# 3. Streamlit dashboard
Start-Process "$base\.venv\Scripts\python.exe" `
    -ArgumentList "-m","streamlit","run","dashboard/app.py","--server.port","8501","--server.headless","true" `
    -WorkingDirectory $base -WindowStyle Hidden
```

> **Critical:** Always use `.venv\Scripts\python.exe` — not `uv run python`. On this machine `uv run python` resolves to system Python which has the wrong DeepEval version (1.4.6 vs 4.0.2 required).

---

## Running the Eval Suite

After collecting agent runs, score them with DeepEval:

```powershell
$base = "path\to\ai-evals-framework"
$env:GIT_PYTHON_REFRESH = "quiet"
$env:PYTHONUTF8 = "1"
Set-Location $base

# Score all unscored runs
& "$base\.venv\Scripts\python.exe" -m evals.eval_runner

# Force re-score all runs
& "$base\.venv\Scripts\python.exe" -m evals.eval_runner --force
```

> Eval scoring uses Azure OpenAI (gpt-5.2-chat-2) as the LLM judge — ensure your `.env` is present with valid credentials. Ollama must still be running for FAISS embeddings.

---

## Running a Load Test

> **Note:** Locust is installed in the venv — use the full path, not the system `locust` command.

```powershell
$base = "path\to\ai-evals-framework"
Set-Location $base

# Headless load test — 4 users, 3 min (recommended for CPU-only Ollama)
& "$base\.venv\Scripts\locust.exe" -f load_tests\locustfile.py `
    --host http://127.0.0.1:8001 `
    --users 4 --spawn-rate 1 --run-time 180s --headless

# After the test, score runs:
& "$base\.venv\Scripts\python.exe" -m evals.eval_runner
```

> With Azure OpenAI (~5–23s per query), up to 10 concurrent users is practical. Run Locust headless with `--users 10 --spawn-rate 2 --run-time 180s`.

---

## Fresh Start (reset all data)

To delete all MLflow runs and start clean:

```powershell
$base = "path\to\ai-evals-framework"

# 1. Stop MLflow
Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine -like "*mlflow*"
} | Stop-Process -Force

# 2. Delete run data
Remove-Item "$base\mlruns" -Recurse -Force

# 3. Restart all services
& "$base\start.ps1"
```

---

## MLflow Data Reference

### Experiments

Three MLflow experiments are created automatically:

| Experiment Name | ID (current) | What it holds |
| --------------- | ------------ | ------------- |
| `it-helpdesk-agent-evals` | `758149922029836096` | One run per agent invocation — all agent + eval metrics |
| `it-helpdesk-load-test` | auto-assigned | One run per Locust test — p50/p95/p99 latency, error rate, RPS |
| `it-helpdesk-eval-summary` | auto-assigned | One run per `eval_runner` execution — aggregate stats + recommendations artifact |

> The experiment ID for `it-helpdesk-agent-evals` is fixed at `758149922029836096` for this install. If you delete `mlruns/` and restart, MLflow assigns a new ID.

### mlruns Folder Structure

All MLflow data lives on disk at:

```
ai-evals-framework/
└── mlruns/
    └── 758149922029836096/          ← experiment ID (it-helpdesk-agent-evals)
        └── <32-char run_id>/        ← one folder per agent invocation
            ├── meta.yaml            ← run status, timestamps, lifecycle_stage
            ├── tags/
            │   └── mlflow.runName   ← human name, e.g. "helpdesk-3a81b5c8"
            ├── params/
            │   ├── intent           ← VPN / PASSWORD / HARDWARE / SOFTWARE / NETWORK
            │   ├── query            ← original user query text
            │   ├── escalation_reason
            │   └── trace_id
            ├── metrics/             ← one file per metric; file content = "timestamp value step"
            │   │
            │   │  ── Logged by agents/pipeline.py (at invoke time) ──
            │   ├── ttft_seconds
            │   ├── input_tokens
            │   ├── output_tokens
            │   ├── tokens_per_second
            │   ├── cost_usd
            │   ├── latency_total_pipeline
            │   ├── latency_intent_classifier
            │   ├── latency_knowledge_retriever
            │   ├── latency_response_generator
            │   ├── latency_escalation_decider
            │   ├── confidence
            │   └── escalated
            │   │
            │   │  ── Logged by evals/eval_runner.py (after scoring) ──
            │   ├── quality_score    ← headline KPI
            │   ├── rag_score
            │   ├── helpdesk_score
            │   ├── safety_score
            │   ├── faithfulness
            │   ├── answer_relevancy
            │   ├── contextual_relevancy
            │   ├── completeness
            │   ├── actionability
            │   ├── professional_tone
            │   ├── task_resolution
            │   └── toxicity
            └── artifacts/
                ├── eval_data.json       ← full query / response / retrieved context
                └── eval_reasons.json    ← LLM-generated explanations per metric (added by eval_runner)
```

### What gets logged when

| Step | Triggered by | Metrics written |
| ---- | ------------ | --------------- |
| Agent invoked (`/invoke`) | `agents/pipeline.py` | `ttft_seconds`, `cost_usd`, `input_tokens`, `output_tokens`, `tokens_per_second`, all `latency_*`, `confidence`, `escalated` |
| Eval scoring | `evals/eval_runner.py` | All 8 DeepEval metrics + 4 composites (`quality_score`, `rag_score`, etc.) + `eval_reasons.json` artifact |
| Eval complete | `eval_runner.py` `log_summary()` | One run in `it-helpdesk-eval-summary` with aggregate stats + `eval_recommendations.json` artifact |

### Reading a metric file directly

Each metric file contains one line per logged value: `<unix_timestamp_ms> <value> <step>`.

```powershell
# Read quality_score for a specific run
$base = "path\to\ai-evals-framework"
$runId = "317322d5fd7b4c2b97e397a92ec91159"  # replace with actual run ID
Get-Content "$base\mlruns\758149922029836096\$runId\metrics\quality_score"
# → 1747809234567 0.712 0
```

### Find a run ID by name

```powershell
$base = "path\to\ai-evals-framework"
$expPath = "$base\mlruns\758149922029836096"
Get-ChildItem $expPath -Directory | ForEach-Object {
    $name = Get-Content "$($_.FullName)\tags\mlflow.runName" -ErrorAction SilentlyContinue
    if ($name) { Write-Host "$name  →  $($_.Name)" }
}
```

### Check if a run has been scored

A run is scored (by `eval_runner`) if its `metrics/` folder contains a `quality_score` file:

```powershell
$runPath = "$base\mlruns\758149922029836096\<run_id>"
Test-Path "$runPath\metrics\quality_score"   # True = scored, False = not yet scored
```

---

## Dashboard Tabs

| Tab | What it shows |
|-----|---------------|
| Quality Metrics | KPI cards, quality over time, per-metric bars, run table |
| Load Test | P50/P95/P99 latency vs users, error rate, SLA indicators |
| Quality Under Load | Signature chart: quality score vs concurrent users |
| Run Explorer | Per-run drill-down with radar chart |
| Metric Guide | Plain-English definitions of all 8 metrics + 4 composites |
| Speed & Cost | TTFT, tokens/sec, input/output tokens, cloud-equivalent cost |

---

## Evaluation Metrics

| Category | Metric | SLA |
|----------|--------|-----|
| RAG Retrieval | `contextual_relevancy` | ≥ 0.70 |
| RAG Generation | `faithfulness` | ≥ 0.70 |
| RAG Generation | `answer_relevancy` | ≥ 0.70 |
| Helpdesk (GEval) | `completeness` | ≥ 0.60 |
| Helpdesk (GEval) | `actionability` | ≥ 0.60 |
| Helpdesk (GEval) | `professional_tone` | ≥ 0.60 |
| Helpdesk (GEval) | `task_resolution` | ≥ 0.60 |
| Safety | `toxicity` | ≤ 0.10 |
| **Composite** | `rag_score` | ≥ 0.70 |
| **Composite** | `helpdesk_score` | ≥ 0.60 |
| **Composite** | `safety_score` | ≥ 0.90 |
| **Composite** | `quality_score` ← headline KPI | ≥ 0.65 |

---

## Speed & Cost Metrics (per run)

| Metric | Description |
|--------|-------------|
| `ttft_seconds` | Time to First Token — seconds until model starts responding |
| `input_tokens` | Prompt token count (query + context) |
| `output_tokens` | Response token count |
| `tokens_per_second` | Generation throughput |
| `cost_usd` | Cloud-equivalent cost using GPT-4o-mini pricing ($0.15/1M input, $0.60/1M output) |

> Ollama runs locally so actual cost is $0. The estimated cost gives clients a cloud budgeting reference.

---

## Key URLs

| Service | URL |
|---------|-----|
| AgentPulse Dashboard | http://localhost:8501 |
| MLflow UI | http://localhost:5000 |
| Agent API (Swagger) | http://localhost:8001/docs |
| Ollama API | http://localhost:11434 |

---

## Project Structure

```
ai-evals-framework/
├── agents/
│   ├── pipeline.py              # LangGraph graph + FastAPI /invoke + MLflow tracing
│   ├── intent_classifier.py     # Node 1 — classifies query intent
│   ├── knowledge_retriever.py   # Node 2 — FAISS semantic RAG
│   ├── response_generator.py    # Node 3 — Ollama LLM + TTFT + token tracking
│   └── escalation_decider.py    # Node 4 — L1/L2/L3 routing
├── data/knowledge_base/         # IT runbook .txt files (swap for client content)
├── evals/
│   ├── eval_runner.py           # DeepEval scorer — run after agent runs
│   └── ollama_eval_model.py     # Shim: re-exports DeepEval native OllamaModel
├── load_tests/
│   └── locustfile.py            # Locust concurrent user simulation
├── dashboard/
│   └── app.py                   # Streamlit 6-tab live dashboard
├── reports/
│   ├── templates/report.html    # Jinja2 PDF template
│   ├── report_generator.py      # matplotlib + xhtml2pdf PDF export
│   └── output/                  # Generated PDF reports
├── config.yaml                  # All tuneable settings — edit here, no code changes needed
├── requirements.txt             # All Python dependencies
├── start.ps1                    # One-command session startup
└── WhatWeAreBuilding.md         # Beginner-friendly project overview
```

---

## Customising for a Client

The framework is **agent-agnostic**. To tailor for a specific client:
- Swap `data/knowledge_base/` with client-specific runbooks or FAQs
- Update `config.yaml` with client SLA thresholds
- All agent logic, load tests, eval metrics, and dashboards remain identical

This is a key demo talking point: the evaluation framework works for any domain.

---

## Built With

- [LangGraph](https://langchain-ai.github.io/langgraph/) — multi-node agent orchestration
- [MLflow](https://mlflow.org) — experiment tracking, tracing, artifact store
- [DeepEval](https://deepeval.com) — LLM quality evaluation framework
- [Locust](https://locust.io) — open-source load testing
- [Ollama](https://ollama.com) — local LLM inference, no API key required
- [Streamlit](https://streamlit.io) — live dashboard
- [FAISS](https://faiss.ai) — vector similarity search for RAG
