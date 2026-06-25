# AgentPulse — Next Steps & Vision

## What's Built (Phases 1–5)

| Phase | Description | Status |
|---|---|---|
| 1 | Environment setup — uv, venv, Azure OpenAI, MLflow 3.14.0 | DONE |
| 2 | LangGraph 4-node agent + FastAPI /invoke + MLflow tracing | DONE |
| 3 | BM25 RAG over IT runbooks + Locust load test | DONE |
| 4 | DeepEval quality scoring — 8 metrics, 4 composites, eval_runner.py | DONE |
| 5 | Streamlit 8-tab dashboard + PDF report + Insights tab | DONE |

---

## Phase 6 — AgentPulse MCP Server (CURRENT)

### Vision

Turn AgentPulse into an **MCP-enabled eval platform** so Claude Code can read live eval
data, reason over it, and raise a GitHub PR with code fixes — all within a chat session.
No separate API key required: Claude Code (VS Code extension) is already authenticated.

### The Full Agentic Workflow

```
1. eval_runner.py runs
         ↓
2. eval_recommendations.json saved to MLflow artifacts (HIGH / MEDIUM / INFO findings)
         ↓
3. AgentPulse MCP Server exposes live eval data as Claude tools
         ↓
4. User types in Claude Code chat:
   "Check AgentPulse recommendations and raise a PR fixing all HIGH findings"
         ↓
5. Claude calls MCP tools → reads recommendations + failing metrics + run details
         ↓
6. Claude reads relevant source files → writes targeted code fixes
         ↓
7. Claude commits + gh pr create  →  GitHub PR opened automatically
         ↓
8. Human reviews PR → approves / requests changes / rejects
         ↓
9. Merge → re-run eval_runner.py → confirm quality improvement in dashboard
```

### Why MCP (not a direct API call)

- No Anthropic API key needed — Claude Code subscription covers it
- Structured tool interface — Claude gets clean JSON, not raw file text
- Reusable — any MCP-compatible client (Claude, Copilot Agent, Cursor) can consume it
- Extensible — add tools later: trigger_eval_run(), compare_runs(), get_cost_summary()

### What the MCP Server Exposes

| Tool | Description |
|---|---|
| `get_recommendations()` | Latest HIGH/MEDIUM/INFO findings from eval_recommendations.json |
| `get_failing_metrics()` | All metrics below SLA with average score and gap |
| `list_recent_runs(limit)` | Most recent evaluated runs with quality scores |
| `get_run_details(run_id)` | Per-run scores + LLM reasons from eval_reasons.json |

### Files Created (Phase 6)

```
mcp_server/
├── __init__.py
└── agentpulse_mcp.py      ← MCP server (FastMCP, stdio transport)
```

Claude Code settings updated: `~/.claude/settings.json` → `mcpServers.agentpulse`

### How to Start

The MCP server is started automatically by Claude Code when needed (stdio subprocess).
No manual start required — Claude Code spawns it on first tool call.

To verify it's registered:
```
/mcp   (in Claude Code chat)
```

---

## Phase 7 — Automated Eval-to-PR Pipeline (FUTURE)

Run the full cycle without manual prompting:

```powershell
# One command triggers: eval → MCP context → Claude fixes → PR
.\run_cycle.ps1
```

`run_cycle.ps1` would:
1. Run eval_runner.py
2. Check if any HIGH findings exist
3. If yes, open a Claude Code session with the prompt pre-loaded
4. Claude raises the PR automatically

---

## Phase 8 — DeepFlow eBPF Tracing (BACKLOG)

Zero-instrumentation container-level tracing complementing AgentPulse's application-level
metrics. See project_backlog_deepflow.md in memory.

---

## Demo Story (for Rohit / AD-level audience)

> "AgentPulse doesn't just measure quality — it drives improvement.
> The eval runner scores every agent run across 8 metrics.
> When scores fall below SLA, the Insights tab surfaces prioritised findings.
> Those findings are exposed via an MCP server.
> Claude Code reads them, understands the codebase, and raises a PR with fixes.
> A human reviews and approves.
> We re-run the eval and confirm the scores improved.
> That's a closed-loop, human-in-the-loop AI quality workflow —
> the kind of DevPerfOps discipline that production AI systems need."
