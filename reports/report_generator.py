"""
Phase 5: PDF report generator for AI Agent Evals Framework.

Uses Playwright (Chromium) to render a D3.js + Jinja2 HTML template to PDF.
Replaces the previous xhtml2pdf + matplotlib approach.

Usage (from dashboard or CLI):
    from reports.report_generator import generate_report
    path = generate_report(df_evals, df_load, df_summary, cfg)
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

BASE_DIR   = Path(__file__).parent.parent
TMPL_DIR   = BASE_DIR / "reports" / "templates"
OUTPUT_DIR = BASE_DIR / "reports" / "output"

# Category colour mappings used by the D3 metric bar chart
_CAT_COLOUR = {
    "faithfulness":         "#0d9488",   # TEAL  — RAG Gen
    "answer_relevancy":     "#0d9488",   # TEAL  — RAG Gen
    "contextual_relevancy": "#2563eb",   # BLUE  — RAG Ret
    "completeness":         "#7c3aed",   # PURPLE — Helpdesk
    "actionability":        "#7c3aed",
    "professional_tone":    "#7c3aed",
    "task_resolution":      "#7c3aed",
    "toxicity":             "#d97706",   # AMBER — Safety
}


# ── Stats helpers ──────────────────────────────────────────────────────────────

def _summary_stats(df_evals: pd.DataFrame, df_load: pd.DataFrame) -> dict:
    s: dict = {}
    if not df_evals.empty:
        scored = df_evals.dropna(subset=["quality_score"]) if "quality_score" in df_evals.columns else pd.DataFrame()
        s["total_runs"]  = len(df_evals)
        s["scored_runs"] = len(scored)
        for col, key in [
            ("quality_score",  "avg_quality"),
            ("faithfulness",   "avg_faithfulness"),
            ("rag_score",      "avg_rag"),
            ("helpdesk_score", "avg_helpdesk"),
            ("safety_score",   "avg_safety"),
        ]:
            if col in scored.columns and not scored.empty:
                s[key] = round(float(scored[col].mean()), 3)
    if not df_load.empty:
        dl = df_load.copy()
        dl["user_count"] = pd.to_numeric(dl.get("user_count", pd.Series(dtype=float)), errors="coerce")
        if "user_count" in dl.columns:
            s["max_users"] = int(dl["user_count"].max()) if not dl["user_count"].isna().all() else None
        if "p95_response_time_ms" in dl.columns:
            s["best_p95"]  = round(float(dl["p95_response_time_ms"].min()), 0)
            s["worst_p95"] = round(float(dl["p95_response_time_ms"].max()), 0)
    return s


def _metric_table(df_evals: pd.DataFrame, eval_cfg: dict) -> list[dict]:
    all_metrics = [
        "faithfulness","answer_relevancy","contextual_relevancy",
        "completeness","actionability","professional_tone","task_resolution","toxicity",
        "rag_score","helpdesk_score","safety_score","quality_score",
    ]
    thresholds = {
        "faithfulness":         eval_cfg.get("min_faithfulness_score", 0.70),
        "answer_relevancy":     eval_cfg.get("min_answer_relevancy", 0.70),
        "contextual_relevancy": eval_cfg.get("min_contextual_relevancy", 0.60),
        "completeness":         eval_cfg.get("min_completeness", 0.50),
        "actionability":        eval_cfg.get("min_actionability", 0.50),
        "professional_tone":    eval_cfg.get("min_professional_tone", 0.50),
        "task_resolution":      eval_cfg.get("min_task_resolution", 0.50),
        "toxicity":             eval_cfg.get("max_toxicity", 0.30),
        "rag_score":            eval_cfg.get("min_rag_score", 0.70),
        "helpdesk_score":       eval_cfg.get("min_helpdesk_score", 0.60),
        "safety_score":         eval_cfg.get("min_safety_score", 0.70),
        "quality_score":        eval_cfg.get("min_quality_score", 0.65),
    }
    categories = {
        "faithfulness": "RAG Generation", "answer_relevancy": "RAG Generation",
        "contextual_relevancy": "RAG Retrieval",
        "completeness": "Helpdesk GEval","actionability": "Helpdesk GEval",
        "professional_tone": "Helpdesk GEval","task_resolution": "Helpdesk GEval",
        "toxicity": "Safety",
        "rag_score": "Composite","helpdesk_score": "Composite",
        "safety_score": "Composite","quality_score": "Composite",
    }

    scored = df_evals.dropna(subset=["quality_score"]) if (
        not df_evals.empty and "quality_score" in df_evals.columns
    ) else df_evals

    rows = []
    for m in all_metrics:
        if m in scored.columns:
            vals = scored[m].dropna()
            if len(vals) > 0:
                avg = round(float(vals.mean()), 3)
                thr = thresholds.get(m, 0.5)
                passed = avg <= thr if m in ("toxicity",) else avg >= thr
                rows.append({
                    "metric":    m,
                    "category":  categories.get(m, ""),
                    "avg_score": avg,
                    "threshold": thr,
                    "n":         int(len(vals)),
                    "status":    "PASS" if passed else "FAIL",
                })
    return rows


def _concurrency_table(df_summary: pd.DataFrame, df_load: pd.DataFrame) -> list[dict]:
    if df_summary.empty:
        return []
    df = df_summary.copy()
    if "user_count" in df.columns:
        df["user_count"] = pd.to_numeric(df["user_count"], errors="coerce")
    df = df.dropna(subset=["user_count"]).sort_values("user_count")

    dl = pd.DataFrame()
    if not df_load.empty:
        dl = df_load.copy()
        dl["user_count"] = pd.to_numeric(dl.get("user_count", pd.Series(dtype=float)), errors="coerce")

    rows = []
    for _, row in df.iterrows():
        uc = int(row["user_count"])
        entry: dict = {"user_count": uc}
        for col in ["avg_quality_score","avg_rag_score","avg_helpdesk_score","avg_safety_score"]:
            if col in row and pd.notna(row[col]):
                entry[col] = round(float(row[col]), 3)
        if not dl.empty and "user_count" in dl.columns and "p95_response_time_ms" in dl.columns:
            match = dl[dl["user_count"] == uc]
            if not match.empty:
                entry["p95_latency_ms"] = int(float(match["p95_response_time_ms"].iloc[0]))
        rows.append(entry)
    return rows


def _speed_data(df_evals: pd.DataFrame) -> tuple[dict, list[dict]]:
    """Extract speed KPIs and per-run speed table from evals DataFrame."""
    speed_cols = ["ttft_seconds", "tokens_per_second", "input_tokens", "output_tokens", "estimated_cost_usd"]
    available = [c for c in speed_cols if c in df_evals.columns]
    if not available or df_evals.empty:
        return {}, []

    df = df_evals.dropna(subset=["ttft_seconds"] if "ttft_seconds" in df_evals.columns else available[:1]).copy()
    if df.empty:
        return {}, []

    kpis: dict = {"n_runs": len(df)}
    if "ttft_seconds" in df.columns:
        kpis["avg_ttft"] = round(float(df["ttft_seconds"].mean()), 2)
    if "tokens_per_second" in df.columns:
        kpis["avg_tps"] = round(float(df["tokens_per_second"].mean()), 1)
    if "output_tokens" in df.columns:
        kpis["avg_output_tokens"] = round(float(df["output_tokens"].mean()), 0)
    if "estimated_cost_usd" in df.columns:
        kpis["total_cost"] = round(float(df["estimated_cost_usd"].sum()), 6)

    df_sorted = df.sort_values("start_time") if "start_time" in df.columns else df
    runs = []
    for _, row in df_sorted.iterrows():
        entry: dict = {
            "run_name": row.get("run_name", row.get("run_id", "")[:8] if "run_id" in row else "—")
        }
        for col in speed_cols:
            if col in row and pd.notna(row[col]):
                entry[col] = row[col]
        runs.append(entry)
    return kpis, runs


def _scored_runs_table(df_evals: pd.DataFrame) -> list[dict]:
    """Per-run quality scores table for the report."""
    if df_evals.empty or "quality_score" not in df_evals.columns:
        return []
    scored = df_evals.dropna(subset=["quality_score"]).copy()
    scored = scored.sort_values("start_time") if "start_time" in scored.columns else scored

    rows = []
    for _, row in scored.iterrows():
        entry: dict = {
            "run_name": row.get("run_name", str(row.get("run_id", ""))[:8]),
            "intent":   row.get("intent", "—"),
        }
        for col in ["quality_score", "rag_score", "helpdesk_score", "safety_score", "faithfulness"]:
            if col in row and pd.notna(row[col]):
                entry[col] = round(float(row[col]), 3)
        rows.append(entry)
    return rows


def _intent_scores(df_evals: pd.DataFrame) -> list[dict]:
    """Aggregate quality metrics by intent category."""
    if df_evals.empty or "intent" not in df_evals.columns or "quality_score" not in df_evals.columns:
        return []
    scored = df_evals.dropna(subset=["quality_score"]).copy()
    if scored.empty:
        return []

    rows = []
    for intent, grp in scored.groupby("intent"):
        entry: dict = {"intent": intent, "n_runs": len(grp)}
        for col, key in [
            ("quality_score",  "quality"),
            ("rag_score",      "rag"),
            ("helpdesk_score", "helpdesk"),
            ("safety_score",   "safety"),
        ]:
            if col in grp.columns:
                vals = grp[col].dropna()
                if not vals.empty:
                    entry[key] = round(float(vals.mean()), 3)
        rows.append(entry)
    rows.sort(key=lambda r: r.get("quality", 1.0))
    return rows


def _date_range(df_evals: pd.DataFrame) -> str:
    if df_evals.empty or "start_time" not in df_evals.columns:
        return "—"
    try:
        ts = pd.to_datetime(df_evals["start_time"])
        lo = ts.min().strftime("%Y-%m-%d")
        hi = ts.max().strftime("%Y-%m-%d")
        return lo if lo == hi else f"{lo} — {hi}"
    except Exception:
        return "—"


def _trend_deltas(df_evals: pd.DataFrame) -> dict:
    """Compare newest half vs oldest half of scored runs for trend deltas."""
    if df_evals.empty or "quality_score" not in df_evals.columns:
        return {}
    scored = df_evals.dropna(subset=["quality_score"]).copy()
    scored = scored.sort_values("start_time") if "start_time" in scored.columns else scored
    n = len(scored)
    if n < 2:
        return {}
    mid = n // 2
    old_half = scored.iloc[:mid]
    new_half = scored.iloc[mid:]
    deltas: dict = {}
    for col, key in [
        ("quality_score",  "quality_delta"),
        ("faithfulness",   "faithfulness_delta"),
        ("rag_score",      "rag_delta"),
        ("safety_score",   "safety_delta"),
    ]:
        if col in scored.columns:
            old_mean = old_half[col].dropna().mean()
            new_mean = new_half[col].dropna().mean()
            if pd.notna(old_mean) and pd.notna(new_mean):
                deltas[key] = round(float(new_mean - old_mean), 3)
    return deltas


# ── D3 data builders ───────────────────────────────────────────────────────────

def _build_composite_json(df_evals: pd.DataFrame) -> tuple[str, str]:
    """Returns (runs_json, data_json) for the composite line chart."""
    if df_evals.empty or "quality_score" not in df_evals.columns:
        return "[]", "[]"
    scored = df_evals.dropna(subset=["quality_score"]).copy()
    scored = scored.sort_values("start_time") if "start_time" in scored.columns else scored

    runs = []
    data = []
    for _, row in scored.iterrows():
        name = str(row.get("run_name", row.get("run_id", "run")))
        intent = str(row.get("intent", ""))
        label = name[-8:] + ("\n" + intent[:2] if intent else "")
        runs.append(label)
        entry = {}
        for col, key in [("quality_score","q"),("rag_score","r"),("helpdesk_score","h"),("safety_score","s")]:
            if col in row and pd.notna(row[col]):
                entry[key] = round(float(row[col]), 3)
            else:
                entry[key] = None
        data.append(entry)
    return json.dumps(runs), json.dumps(data)


def _build_metric_data_json(metric_table: list[dict]) -> str:
    """Build D3 metric bar data — excludes composite metrics."""
    non_composite = [r for r in metric_table if r["category"] not in ("Composite",)]
    items = []
    for r in non_composite:
        items.append({
            "name": r["metric"],
            "v":    r["avg_score"],
            "t":    r["threshold"],
            "c":    _CAT_COLOUR.get(r["metric"], "#7c3aed"),
        })
    return json.dumps(items)


def _build_speed_jsons(speed_runs: list[dict]) -> tuple[str, str, str, str]:
    """Returns (ttft_json, tps_json, token_json, cost_json)."""
    ttft, tps, tok, cost = [], [], [], []
    for r in speed_runs:
        label = str(r.get("run_name", "run"))[-4:]
        if r.get("ttft_seconds") is not None:
            ttft.append({"r": label, "v": round(float(r["ttft_seconds"]), 1)})
        if r.get("tokens_per_second") is not None:
            tps.append({"r": label, "v": round(float(r["tokens_per_second"]), 1)})
        if r.get("input_tokens") is not None or r.get("output_tokens") is not None:
            tok.append({
                "r":   label,
                "inp": int(r["input_tokens"])  if r.get("input_tokens")  is not None else None,
                "out": int(r["output_tokens"]) if r.get("output_tokens") is not None else None,
            })
        if r.get("estimated_cost_usd") is not None:
            cost.append({"r": label, "v": float(r["estimated_cost_usd"])})
    return json.dumps(ttft), json.dumps(tps), json.dumps(tok), json.dumps(cost)


def _build_load_latency_json(df_load: pd.DataFrame) -> str:
    """Build D3 load latency data — [{u, p50, p95, p99}, ...]."""
    if df_load.empty:
        return "[]"
    dl = df_load.copy()
    dl["user_count"] = pd.to_numeric(dl.get("user_count", pd.Series(dtype=float)), errors="coerce")
    dl = dl.dropna(subset=["user_count"]).sort_values("user_count")
    items = []
    for _, row in dl.iterrows():
        entry: dict = {"u": int(row["user_count"])}
        for col, key in [
            ("p50_response_time_ms","p50"),
            ("p95_response_time_ms","p95"),
            ("p99_response_time_ms","p99"),
        ]:
            if col in row and pd.notna(row[col]):
                entry[key] = int(float(row[col]))
        items.append(entry)
    return json.dumps(items)


def _build_qual_load_json(df_summary: pd.DataFrame) -> str:
    """Build quality-under-load data — [{u, q, r, h, s}, ...]."""
    if df_summary.empty:
        return "[]"
    df = df_summary.copy()
    df["user_count"] = pd.to_numeric(df.get("user_count", pd.Series(dtype=float)), errors="coerce")
    df = df.dropna(subset=["user_count"]).sort_values("user_count")
    items = []
    for _, row in df.iterrows():
        entry: dict = {"u": int(row["user_count"])}
        for col, key in [
            ("avg_quality_score","q"),("avg_rag_score","r"),
            ("avg_helpdesk_score","h"),("avg_safety_score","s"),
        ]:
            if col in row and pd.notna(row[col]):
                entry[key] = round(float(row[col]), 3)
        items.append(entry)
    return json.dumps(items)


def _build_intent_json(intent_scores: list[dict]) -> str:
    """Build intent quality bar data — [{intent, q}, ...] sorted ascending."""
    items = [{"intent": r["intent"], "q": round(float(r.get("quality", 0)), 3)} for r in intent_scores]
    return json.dumps(items)


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_report(
    df_evals:        pd.DataFrame,
    df_load:         pd.DataFrame,
    df_summary:      pd.DataFrame,
    cfg:             dict,
    recommendations: Optional[list] = None,
) -> Path:
    """
    Generate a PDF evaluation report using Playwright + D3.js.
    Returns the Path to the saved file.

    Args:
        df_evals:        MLflow evals experiment DataFrame
        df_load:         MLflow load-test experiment DataFrame
        df_summary:      MLflow eval-summary experiment DataFrame
        cfg:             config.yaml dict
        recommendations: Optional list of recommendation dicts from eval_runner
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    eval_cfg   = cfg.get("eval", {})
    sla_cfg    = cfg.get("sla_thresholds", {})
    mlflow_uri = cfg["mlflow"]["tracking_uri"]
    agent_name = cfg.get("agent", {}).get("name", "AI Agent")

    # Build data tables
    stats          = _summary_stats(df_evals, df_load)
    metric_tbl     = _metric_table(df_evals, eval_cfg)
    conc_tbl       = _concurrency_table(df_summary, df_load)
    speed_kpis, speed_runs = _speed_data(df_evals)
    scored_runs    = _scored_runs_table(df_evals)
    intent_sc      = _intent_scores(df_evals)
    date_range     = _date_range(df_evals)
    deltas         = _trend_deltas(df_evals)

    sla_breaches   = sum(1 for r in metric_tbl if r["status"] == "FAIL")
    sla_ok         = len(metric_tbl) - sla_breaches

    # Build D3 JSON constants
    composite_runs_json, composite_data_json = _build_composite_json(df_evals)
    metric_data_json    = _build_metric_data_json(metric_tbl)
    ttft_json, tps_json, token_json, cost_json = _build_speed_jsons(speed_runs)
    load_latency_json   = _build_load_latency_json(df_load)
    qual_load_json      = _build_qual_load_json(df_summary)
    intent_json         = _build_intent_json(intent_sc)

    # Render Jinja2 template
    env  = Environment(loader=FileSystemLoader(str(TMPL_DIR)), autoescape=False)
    tmpl = env.get_template("report.html")
    html = tmpl.render(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        agent_name=agent_name,
        mlflow_uri=mlflow_uri,
        date_range=date_range,
        stats=stats,
        eval_cfg=eval_cfg,
        sla_cfg=sla_cfg,
        sla_ok=sla_ok,
        sla_breaches=sla_breaches,
        metric_table=metric_tbl,
        concurrency_table=conc_tbl,
        speed_kpis=speed_kpis,
        speed_runs=speed_runs,
        scored_runs=scored_runs,
        intent_scores=intent_sc,
        recommendations=recommendations or [],
        quality_delta=deltas.get("quality_delta", 0),
        faithfulness_delta=deltas.get("faithfulness_delta", 0),
        rag_delta=deltas.get("rag_delta", 0),
        safety_delta=deltas.get("safety_delta", 0),
        # D3 JSON constants
        composite_runs_json=composite_runs_json,
        composite_data_json=composite_data_json,
        metric_data_json=metric_data_json,
        ttft_data_json=ttft_json,
        tps_data_json=tps_json,
        token_data_json=token_json,
        cost_data_json=cost_json,
        qual_load_data_json=qual_load_json,
        intent_data_json=intent_json,
        load_latency_data_json=load_latency_json,
        load_p95_sla_ms=sla_cfg.get("p95_latency_ms", 15000),
    )

    # Produce PDF using Playwright
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"ai_evals_report_{timestamp}.pdf"

    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as f:
        f.write(html)
        html_path = Path(f.name)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1100, "height": 900})
            page.goto(f"file:///{html_path.as_posix()}", wait_until="networkidle", timeout=30000)
            page.pdf(path=str(output_path), format="A4", print_background=True, scale=0.82)
            browser.close()
    finally:
        html_path.unlink(missing_ok=True)

    return output_path


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import yaml
    import mlflow
    from mlflow.tracking import MlflowClient

    sys.path.insert(0, str(BASE_DIR))

    with open(BASE_DIR / "config.yaml") as fh:
        cfg = yaml.safe_load(fh)

    mlflow.set_tracking_uri(cfg["mlflow"]["tracking_uri"])
    client = MlflowClient()

    def _load(name):
        exp = mlflow.get_experiment_by_name(name)
        if not exp:
            return pd.DataFrame()
        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            order_by=["start_time DESC"],
            max_results=200,
        )
        if not runs:
            return pd.DataFrame()
        records = []
        for r in runs:
            row = {
                "run_id":     r.info.run_id,
                "run_name":   r.data.tags.get("mlflow.runName", r.info.run_id[:8]),
                "start_time": pd.to_datetime(r.info.start_time, unit="ms"),
            }
            row.update(r.data.metrics)
            row.update(r.data.params)
            records.append(row)
        return pd.DataFrame(records)

    def _load_recommendations() -> list:
        import json as _json
        import tempfile as _tmp
        exp = mlflow.get_experiment_by_name("it-helpdesk-eval-summary")
        if not exp:
            return []
        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            order_by=["start_time DESC"],
            max_results=1,
        )
        if not runs:
            return []
        try:
            with _tmp.TemporaryDirectory() as tmp:
                local = client.download_artifacts(runs[0].info.run_id, "eval_recommendations.json", tmp)
                with open(local, "r", encoding="utf-8") as f:
                    data = _json.load(f)
            return data.get("recommendations", [])
        except Exception:
            return []

    df_e = _load("it-helpdesk-agent-evals")
    df_l = _load("it-helpdesk-load-test")
    df_s = _load("it-helpdesk-eval-summary")
    recs = _load_recommendations()

    path = generate_report(df_e, df_l, df_s, cfg, recommendations=recs)
    print(f"Report saved: {path}")
