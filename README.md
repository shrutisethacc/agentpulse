# AgentPulse — AI Agent Evaluation Framework

> Built by **Shruti Seth** · Manager, Performance Engineering · Accenture Technology QE Capability

An enterprise-grade platform that **performance tests and evaluates AI agents** — measuring quality, speed, cost, and safety under concurrent load.

**This is not a chatbot.** It is a framework for organisations adopting AI agents who need to answer: *"Is our agent good enough for production? Will quality hold under load?"*

---

## Quick Start (First-Time Setup)

```powershell
# 1. Clone the repo
git clone https://github.com/<org>/ai-evals-framework.git
cd ai-evals-framework

# 2. Run the one-time setup script (creates venv, installs deps, installs Playwright)
.\setup.ps1

# 3. Copy .env.example → .env and fill in your Azure OpenAI credentials
Copy-Item .env.example .env
notepad .env

# 4. Start all services
.\start.ps1
```

Open <http://localhost:8501> for the live dashboard, <http://localhost:5001> for MLflow traces.

> **Every session after first-time setup:** just run `.\start.ps1` — it checks which services are already running and starts only what's missing.

---

## How It Works

```text
User Query  (e.g. "My VPN keeps disconnecting")
    ↓
[1. Intent Classifier]      classifies: VPN / PASSWORD / HARDWARE / SOFTWARE / OTHER
    ↓
[2. Knowledge Retriever]    BM25 keyword RAG over IT runbooks (in-memory, no embeddings required)
    ↓
[3. Response Generator]     Azure OpenAI gpt-5.2-chat-2 generates resolution (2–3 sentences)
    ↓
[4. Escalation Decider]     L1 resolved? or route to L2/L3 with context summary
    ↓
MLflow trace + 17 metrics logged per run
```

---

## Execution Pipeline — Automated vs Manual

Understanding what runs automatically and what you trigger manually is essential.

| Step | Triggered by | Automatic? |
| --- | --- | --- |
| Agent runs (classify → retrieve → generate → escalate) | Locust or direct API call | **Auto** — happens on every `/invoke` |
| MLflow trace logged (per-node spans, latency) | Agent pipeline | **Auto** — instrumented in `pipeline.py` |
| Speed & cost metrics logged (TTFT, tokens, cost) | Agent pipeline | **Auto** — logged in `response_generator.py` |
| BM25 index built from knowledge base | First agent run after startup | **Auto** — rebuilds in-memory if missing |
| DeepEval quality scoring (8 metrics + composites) | You run `eval_runner.py` | **Manual** — run after load test completes |
| Dashboard refresh | Streamlit auto-polls MLflow | **Auto** — refreshes every 30s |
| PDF report generation | You run `report_generator.py` | **Manual** — on demand |

**Typical session flow:**

```text
1. start.ps1              → all 4 services up
2. Locust load test       → N agent runs → MLflow auto-logs speed/cost metrics
3. eval_runner.py         → scores all unscored runs → MLflow auto-logs quality metrics
4. Dashboard              → shows full picture: load + quality + cost
5. report_generator.py    → exports PDF (optional)
```

> DeepEval scoring is intentionally a separate step — running it inline during load tests would add 5–15s judge latency per request and distort throughput measurements.

---

## Tech Stack

| Component | Tool | Notes |
| --- | --- | --- |
| Agent framework | LangGraph 0.2.60 | 4-node stateful pipeline |
| LLM — responses | Azure OpenAI `gpt-5.2-chat-2` | ~5–23s TTFT |
| LLM — eval judge | Azure OpenAI via `AzureJudge` | Custom DeepEval wrapper |
| Embeddings — RAG | Not used — BM25 replaces embedding-based retrieval | Azure embedding deployment unavailable; BM25 has no cost |
| Experiment tracking | MLflow 3.14.0 | Tracing + experiments + artifact store |
| Quality evaluation | DeepEval 4.0.2 | 8 metrics + 4 composites |
| Load testing | Locust 2.32.3 | Concurrent user simulation |
| Live dashboard | Streamlit 1.41.1 | 8-tab interface |
| RAG retrieval | BM25Okapi (rank-bm25) | In-memory keyword search — no embedding cost |
| API server | FastAPI + Uvicorn | Port 8001 |
| PDF export | Playwright + Jinja2 | Real browser render — supports D3.js |
| Package manager | uv | Faster and safer than pip |

---

## Prerequisites

Install these manually before running `setup.ps1`:

| Prerequisite | Where to get it | Notes |
| --- | --- | --- |
| Python 3.12 | [python.org](https://www.python.org/downloads/) | Check "Add to PATH" during install |
| Azure OpenAI credentials | From your Azure Portal or admin | See `.env.example` for required fields |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your credentials. The file is excluded from git — never commit it.

```env
AZURE_OPENAI_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_OPENAI_DEPLOYMENT=<deployment-name>
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

### Updating credentials

```powershell
# Open .env in Notepad and edit values, then save
notepad .env

# After saving, restart the Agent API so it picks up the new credentials
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
$env:PYTHONUTF8 = "1"
.\start.ps1
```

> The Agent API reads `.env` at startup only — a restart is required after any credential change.

---

## Managing Services

AgentPulse requires these 4 local services running simultaneously (LLM calls go to Azure OpenAI cloud):

| Service | URL | Purpose |
| --- | --- | --- |
| MLflow UI | <http://localhost:5001> | Experiment tracking, traces, artifact store |
| Agent API | <http://127.0.0.1:8001> | FastAPI `/invoke` endpoint (use 127.0.0.1 not localhost) |
| Streamlit Dashboard | <http://localhost:8501> | Live metrics dashboard |
| Locust UI | <http://localhost:8089> | Load test control — set users + spawn rate in browser |

### Start services

```powershell
$env:PYTHONUTF8 = "1"
.\start.ps1
```

`start.ps1` starts MLflow, Agent API, Streamlit, and Locust in the correct order. Run it every session — it skips any service already running.

### Stop services

```powershell
# Stop all AgentPulse processes
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process streamlit -ErrorAction SilentlyContinue | Stop-Process -Force
```

### Check service status

```powershell
# Agent API (use 127.0.0.1 — localhost may resolve to IPv6 on Windows)
Invoke-WebRequest http://127.0.0.1:8001/health -UseBasicParsing | Select-Object StatusCode

# MLflow
Invoke-WebRequest http://127.0.0.1:5001 -UseBasicParsing | Select-Object StatusCode

# Streamlit — check in browser at http://localhost:8501
```

A `StatusCode: 200` means the service is up. If any service is down, re-run `.\start.ps1`.

---

## Sending a Query

```powershell
$body = '{"query":"My VPN keeps disconnecting every 30 minutes"}'
Invoke-WebRequest -Uri "http://127.0.0.1:8001/invoke" `
  -Method POST -ContentType "application/json" `
  -Body $body -UseBasicParsing | Select-Object -ExpandProperty Content
```

> **Windows note:** Use `http://127.0.0.1` (not `http://localhost`) for the Agent API and MLflow — on some Windows machines `localhost` resolves to IPv6 and the connection is refused.

To run all 12 demo queries in sequence:

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe scripts\batch_queries.py
```

---

## Running the Eval Suite

**This is a manual step.** Run it after your load test or batch queries are complete. It scores every unscored MLflow run using Azure OpenAI as the DeepEval judge and writes the quality metrics back to MLflow.

```powershell
$env:PYTHONUTF8 = "1"

# Score all unscored runs (most common — run this after every load test)
.\.venv\Scripts\python.exe -m evals.eval_runner

# Force re-score all runs (use after changing judge model or eval config)
.\.venv\Scripts\python.exe -m evals.eval_runner --force

# Regenerate summary stats only — no re-scoring
.\.venv\Scripts\python.exe -m evals.eval_runner --summary-only
```

> **Always use `.venv\Scripts\python.exe` directly.** `uv run python` resolves to system Python which has the wrong DeepEval version.

Quality scores appear in the dashboard automatically once eval_runner completes — no dashboard restart needed.

---

## Running a Load Test

```powershell
# 10 concurrent users, 3 minutes, headless
.\.venv\Scripts\locust.exe -f load_tests\locustfile.py `
    --host http://127.0.0.1:8001 `
    --users 10 --spawn-rate 2 --run-time 180s --headless

# Then score the new runs
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m evals.eval_runner
```

Or open the Locust UI at <http://localhost:8089> for interactive control:

```powershell
.\.venv\Scripts\locust.exe -f load_tests\locustfile.py --host http://127.0.0.1:8001
```

---

## Generating a PDF Report

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m reports.report_generator
# Output saved to reports/output/agentpulse_report_<timestamp>.pdf
```

---

## Dashboard Tabs

| Tab | What it shows |
| --- | --- |
| Home | Platform overview, current run count, quick health check |
| Quality Metrics | KPI cards, quality trend over time, per-metric bar chart, SLA pass/fail table |
| Load Test | P50/P95/P99 latency vs concurrent users, error rate, SLA indicators |
| Quality Under Load | Signature chart: quality score vs concurrent user count |
| Run Explorer | Per-run drill-down with radar chart — compare any two runs |
| Speed & Cost | TTFT per run, tokens/sec, input/output tokens, cloud-equivalent cost |
| Metric Guide | Plain-English definitions of all 8 metrics + 4 composites + SLA thresholds |
| Insights | Prioritised recommendations generated from pattern analysis across all runs |

---

## Evaluation Metrics

### Quality Metrics (DeepEval — 8 individual + 4 composite)

| Category | Metric | Plain English | SLA |
| --- | --- | --- | --- |
| RAG Retrieval | `contextual_relevancy` | Did it search the right part of the knowledge base? | ≥ 0.70 |
| RAG Generation | `faithfulness` | Did it stick to retrieved content, or hallucinate? | ≥ 0.70 |
| RAG Generation | `answer_relevancy` | Did it actually answer what was asked? | ≥ 0.70 |
| Helpdesk (GEval) | `completeness` | Did the answer include all steps needed? | ≥ 0.60 |
| Helpdesk (GEval) | `actionability` | Were the steps specific enough to act on? | ≥ 0.60 |
| Helpdesk (GEval) | `professional_tone` | Was the language appropriate for a corporate helpdesk? | ≥ 0.60 |
| Helpdesk (GEval) | `task_resolution` | Could the user fully resolve their issue? | ≥ 0.60 |
| Safety | `toxicity` | Was there any harmful or offensive content? | ≤ 0.10 |
| **Composite** | `rag_score` | Mean of faithfulness + answer_relevancy + contextual_relevancy | ≥ 0.70 |
| **Composite** | `helpdesk_score` | Mean of all 4 GEval metrics | ≥ 0.60 |
| **Composite** | `safety_score` | 1 − toxicity | ≥ 0.90 |
| **Composite** | `quality_score` | **Headline KPI — mean of rag, helpdesk, safety** | ≥ 0.65 |

### Speed & Cost Metrics (5 per run)

| Metric | Description |
| --- | --- |
| `ttft_seconds` | Time to First Token |
| `input_tokens` | Prompt token count (query + retrieved context) |
| `output_tokens` | Response token count |
| `tokens_per_second` | Generation throughput |
| `cost_usd` | Estimated cost using GPT-4o-mini pricing ($0.15/1M input, $0.60/1M output) |

---

## Project Structure

```text
ai-evals-framework/
├── agents/                      Core LangGraph pipeline
│   ├── pipeline.py              Graph definition + FastAPI /invoke + MLflow tracing
│   ├── intent_classifier.py     Node 1 — classifies query intent
│   ├── knowledge_retriever.py   Node 2 — BM25 keyword RAG over IT runbooks (no embeddings)
│   ├── response_generator.py    Node 3 — Azure OpenAI response + TTFT + token tracking
│   └── escalation_decider.py    Node 4 — L1/L2/L3 routing logic
├── data/
│   └── knowledge_base/          IT runbook .txt files — swap for any client domain
├── evals/
│   ├── eval_runner.py           Main scorer — run after agent calls to log quality metrics
│   ├── azure_eval_model.py      AzureJudge — custom DeepEval wrapper for Azure OpenAI
│   ├── ollama_eval_model.py     LEGACY — kept as reference only, not used
│   └── golden_answers.py        Reference answers for test queries
├── load_tests/
│   └── locustfile.py            Locust concurrent user simulation
├── dashboard/
│   └── app.py                   Streamlit 8-tab live dashboard
├── reports/
│   ├── report_generator.py      Playwright PDF export
│   ├── templates/report.html    Jinja2 report template (D3.js charts)
│   └── output/                  Generated PDFs (gitignored)
├── docs/
│   ├── WhatWeAreBuilding.md     Project brief and architecture slides
│   └── architecture.drawio      System architecture diagram
├── scripts/
│   ├── batch_queries.py         Send all 12 demo queries in sequence
│   └── check_evals.py           Inspect scored runs in MLflow
├── tests/                       Smoke tests (run: .venv\Scripts\pytest.exe tests\)
├── .env.example                 Credential template — copy to .env and fill in
├── .gitignore
├── config.yaml                  SLA thresholds, service ports, model config
├── requirements.txt             All Python dependencies
├── setup.ps1                    First-time setup (run once after cloning)
└── start.ps1                    Session startup (run every time)
```

---

## Adapting for a Client

The framework is **agent-agnostic**. To tailor it for a specific client:

1. Replace `data/knowledge_base/` with client-specific content (HR policies, product guides, compliance docs, field service manuals)
2. Update `config.yaml` with client SLA thresholds
3. Everything else — agent nodes, eval metrics, load tests, dashboard, PDF report — works without modification

The BM25 index rebuilds automatically in-memory on first run with the new knowledge base.

---

## Resetting All Data

Use this for a clean slate — wipes all MLflow runs, traces, and eval scores. Does **not** delete the knowledge base or source code.

```powershell
# Step 1: Stop all services (must stop before deleting — MLflow holds file locks)
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process streamlit -ErrorAction SilentlyContinue | Stop-Process -Force

# Step 2: Delete all run data
Remove-Item .\mlruns -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item .\mlartifacts -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item .\mlflow.db -Force -ErrorAction SilentlyContinue

# Step 3: Restart all services fresh
$env:PYTHONUTF8 = "1"
.\start.ps1
```

> The Agent API caches the MLflow experiment ID at startup. Always restart it after deleting mlruns — a stale ID causes 500 errors on every `/invoke` call. `start.ps1` restarts everything, so Step 3 above covers this.

---

## Key URLs

| Service | URL | Notes |
| --- | --- | --- |
| AgentPulse Dashboard | <http://localhost:8501> | Main dashboard — 8 tabs |
| MLflow UI | <http://localhost:5001> | Traces, experiments, metrics |
| Agent API — Swagger docs | <http://127.0.0.1:8001/docs> | Interactive API explorer |
| Agent API — health check | <http://127.0.0.1:8001/health> | Returns `{"status":"ok"}` when up |
| Agent API — invoke | <http://127.0.0.1:8001/invoke> | POST endpoint for queries |
| Locust UI | <http://localhost:8089> | Only available when Locust is running (not headless) |

---

## Built With

- [LangGraph](https://langchain-ai.github.io/langgraph/) — multi-node agent orchestration
- [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) — LLM inference and eval judging
- [MLflow](https://mlflow.org) — experiment tracking, distributed tracing, artifact store
- [DeepEval](https://deepeval.com) — LLM quality evaluation framework
- [Locust](https://locust.io) — load testing
- [Streamlit](https://streamlit.io) — live dashboard
- [rank-bm25](https://github.com/dorianbrown/rank_bm25) — BM25Okapi keyword retrieval (no vector index, no embedding cost)
- [Playwright](https://playwright.dev) — PDF generation with real browser rendering
