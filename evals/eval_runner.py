"""
Phase 4: Comprehensive DeepEval quality scoring for the IT Helpdesk Agent.

Reads completed MLflow runs from `it-helpdesk-agent-evals`, scores each run
against 8 metrics across 4 categories, logs scores + LLM-generated reasons back
to the same run as metrics AND as an `eval_reasons.json` artifact.
Aggregate pattern analysis + prioritized recommendations are logged to
`it-helpdesk-eval-summary`.

Metric taxonomy
───────────────
  RAG · Retrieval   : contextual_relevancy
  RAG · Generation  : faithfulness, answer_relevancy
  Helpdesk Quality  : completeness, actionability, professional_tone, task_resolution  (GEval)
  Safety            : toxicity
  ── Composites ────────────────────────────────────────────────────────────────────
  rag_score         : mean(faithfulness, answer_relevancy, contextual_relevancy)
  helpdesk_score    : mean(actionability, professional_tone, task_resolution, completeness)
  safety_score      : 1 − toxicity
  quality_score     : mean(rag_score, helpdesk_score, safety_score)  ← headline KPI

Usage
─────
  # Score all unevaluated runs (default):
  .venv\\Scripts\\python.exe -m evals.eval_runner

  # Re-score runs even if already evaluated:
  .venv\\Scripts\\python.exe -m evals.eval_runner --force

  # Score a specific run:
  .venv\\Scripts\\python.exe -m evals.eval_runner --run-id <mlflow_run_id>

  NOTE: always use .venv\\Scripts\\python.exe directly — uv run python resolves to
  system Python (c:\\python312) which has DeepEval 1.4.6, not the venv's 4.0.2.
"""

import argparse
import datetime
import io
import json
import os
import sys
import tempfile
import time
from statistics import mean
from typing import Optional, Tuple

# cp1252 on Windows can't encode arrows/emoji used in print statements
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import mlflow
from mlflow.entities import ViewType
from mlflow.tracking import MlflowClient

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    GEval,
    ToxicityMetric,
)
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from evals.golden_answers import GOLDEN_ANSWERS
from evals.azure_eval_model import AzureJudge

# ── Configuration ─────────────────────────────────────────────────────────────
MLFLOW_URI = "http://localhost:5001"
EXPERIMENT_NAME = "it-helpdesk-agent-evals"
SUMMARY_EXPERIMENT = "it-helpdesk-eval-summary"
EVAL_ARTIFACT = "eval_data.json"
REASONS_ARTIFACT = "eval_reasons.json"
RECS_ARTIFACT = "eval_recommendations.json"
IDEMPOTENCY_FLAG = "faithfulness"   # presence → run already scored

THR_FAITHFULNESS = 0.7
THR_ANSWER_RELEVANCY = 0.7
THR_CONTEXTUAL = 0.6
THR_GEVAL = 0.5
THR_SAFETY = 0.3


# ── Metric factory ────────────────────────────────────────────────────────────

def build_metrics(judge: AzureJudge) -> dict:
    """8 individual metrics. include_reason=True on all supported metrics."""
    return {
        "contextual_relevancy": ContextualRelevancyMetric(
            threshold=THR_CONTEXTUAL,
            model=judge,
            include_reason=True,
        ),
        "faithfulness": FaithfulnessMetric(
            threshold=THR_FAITHFULNESS,
            model=judge,
            include_reason=True,
        ),
        "answer_relevancy": AnswerRelevancyMetric(
            threshold=THR_ANSWER_RELEVANCY,
            model=judge,
            include_reason=True,
        ),
        "completeness": GEval(
            name="Completeness",
            criteria=(
                "Does the response cover the key information from the retrieved context "
                "needed to resolve the IT issue? Score 1 if comprehensive, 0 if key steps are missing."
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.RETRIEVAL_CONTEXT,
            ],
            model=judge,
            threshold=THR_GEVAL,
        ),
        "actionability": GEval(
            name="Actionability",
            criteria=(
                "Does the response give the user clear steps to resolve their IT issue? "
                "Score 1 if steps are specific and actionable. Score 0 if vague."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=judge,
            threshold=THR_GEVAL,
        ),
        "professional_tone": GEval(
            name="ProfessionalTone",
            criteria=(
                "Is the response professional and appropriate for an enterprise IT helpdesk? "
                "Score 1 if clear and respectful. Score 0 if rude, overly casual, or confusing."
            ),
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            model=judge,
            threshold=THR_GEVAL,
        ),
        "task_resolution": GEval(
            name="TaskResolution",
            criteria=(
                "Can the user fully resolve their IT issue using this response alone? "
                "Score 1 if yes. Score 0 if the response is incomplete or incorrect."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=judge,
            threshold=THR_GEVAL,
        ),
        "toxicity": ToxicityMetric(
            threshold=THR_SAFETY,
            model=judge,
            include_reason=True,
        ),
    }


# ── Reason extraction ─────────────────────────────────────────────────────────

def _collect_reasons(metric, name: str) -> dict:
    """Extract reason, verdicts, and statements from a scored DeepEval metric."""
    data = {}

    reason = getattr(metric, "reason", None)
    if reason:
        data["reason"] = str(reason)

    verdicts = getattr(metric, "verdicts", None)
    if verdicts:
        try:
            vlist = []
            for v in verdicts[:6]:
                vd = {}
                if hasattr(v, "verdict"):
                    vd["verdict"] = str(v.verdict)
                if hasattr(v, "reason") and v.reason:
                    vd["reason"] = str(v.reason)
                vlist.append(vd)
            if vlist:
                data["verdicts"] = vlist
        except Exception:
            pass

    statements = getattr(metric, "statements", None)
    if statements:
        try:
            data["statements"] = [str(s) for s in statements[:5]]
        except Exception:
            pass

    opinions = getattr(metric, "opinions", None)
    if opinions:
        try:
            data["opinions"] = [str(o) for o in opinions[:5]]
        except Exception:
            pass

    return data


# ── Metric execution ──────────────────────────────────────────────────────────

def _run_metric(name: str, metric, test_case: LLMTestCase) -> Optional[float]:
    """Run a single metric safely. Returns None on any error."""
    try:
        metric.measure(test_case)
        return float(metric.score)
    except Exception as exc:
        print(f"      {name}: ERROR — {exc}")
        return None


# ── Score a single run ────────────────────────────────────────────────────────

def score_run(
    run: mlflow.entities.Run,
    metrics: dict,
    client: MlflowClient,
    force: bool = False,
) -> Optional[Tuple[dict, dict]]:
    """
    Score a single MLflow run.

    Returns (scores_dict, reasons_dict) or None if skipped.
    scores_dict  : {metric_name: float}
    reasons_dict : full structured data saved as eval_reasons.json
    """
    run_id = run.info.run_id

    if not force and IDEMPOTENCY_FLAG in run.data.metrics:
        return None

    try:
        with tempfile.TemporaryDirectory() as tmp:
            local_path = client.download_artifacts(run_id, EVAL_ARTIFACT, tmp)
            with open(local_path, "r", encoding="utf-8") as f:
                data = json.load(f)
    except Exception as exc:
        print(f"    [SKIP] no eval_data.json: {exc}")
        return None

    query = data.get("query", "").strip()
    response = data.get("response", "").strip()
    context_raw = data.get("context", "").strip()

    if not query or not response:
        print("    [SKIP] empty query or response")
        return None

    context_chunks = (
        [c.strip() for c in context_raw.split("\n\n") if c.strip()]
        if context_raw else []
    )

    golden = GOLDEN_ANSWERS.get(query)

    test_case = LLMTestCase(
        input=query,
        actual_output=response,
        retrieval_context=context_chunks or None,
        expected_output=golden,
        context=context_chunks or None,
    )

    scores: dict[str, Optional[float]] = {}
    reasons_per_metric: dict[str, dict] = {}
    needs_context = {"contextual_relevancy", "faithfulness", "completeness"}

    with mlflow.start_run(run_id=run_id):
        for name, metric in metrics.items():
            if name in needs_context and not context_chunks:
                print(f"      {name}: skipped (no context)")
                scores[name] = None
                reasons_per_metric[name] = {"score": None, "reason": "Skipped — no retrieved context available"}
                continue

            score = _run_metric(name, metric, test_case)
            scores[name] = score

            if score is not None:
                mlflow.log_metric(name, score)
                status = "PASS" if getattr(metric, "success", score >= metric.threshold) else "FAIL"
                print(f"      {name}: {score:.3f}  [{status}]")
                reason_data = {"score": score}
                reason_data.update(_collect_reasons(metric, name))
                reasons_per_metric[name] = reason_data
            else:
                reasons_per_metric[name] = {"score": None, "reason": "Metric returned an error — check Azure OpenAI connectivity"}

        # ── Composite scores ──────────────────────────────────────────────────
        def avg(*keys) -> Optional[float]:
            vals = [scores[k] for k in keys if scores.get(k) is not None]
            return round(mean(vals), 4) if vals else None

        rag      = avg("faithfulness", "answer_relevancy", "contextual_relevancy")
        helpdesk = avg("completeness", "actionability", "professional_tone", "task_resolution")
        safety   = round(1.0 - scores["toxicity"], 4) if scores.get("toxicity") is not None else None

        quality_inputs = [v for v in (rag, helpdesk, safety) if v is not None]
        quality = round(mean(quality_inputs), 4) if quality_inputs else None

        for cname, cval in [
            ("rag_score", rag),
            ("helpdesk_score", helpdesk),
            ("safety_score", safety),
            ("quality_score", quality),
        ]:
            if cval is not None:
                scores[cname] = cval
                mlflow.log_metric(cname, cval)

        # ── Save eval_reasons.json artifact ───────────────────────────────────
        intent = run.data.params.get("intent", "UNKNOWN")
        reasons_data = {
            "run_id": run_id,
            "run_name": run.data.tags.get("mlflow.runName", run_id[:8]),
            "query": query,
            "intent": intent,
            "response_preview": response[:400] + ("…" if len(response) > 400 else ""),
            "timestamp": datetime.datetime.now().isoformat(),
            "metrics": reasons_per_metric,
            "composites": {
                "rag_score": rag,
                "helpdesk_score": helpdesk,
                "safety_score": safety,
                "quality_score": quality,
            },
        }

        with tempfile.TemporaryDirectory() as artifact_tmp:
            artifact_file = os.path.join(artifact_tmp, REASONS_ARTIFACT)
            with open(artifact_file, "w", encoding="utf-8") as f:
                json.dump(reasons_data, f, indent=2, ensure_ascii=False)
            mlflow.log_artifact(artifact_file)

    return scores, reasons_data


# ── Pattern analysis & recommendations ───────────────────────────────────────

METRIC_ADVICE = {
    "contextual_relevancy": (
        "RAG Retrieval Gap",
        "Retrieved documents don't closely match query intent. "
        "Expand IT runbooks with more keyword variations, or increase FAISS top-k from 3 to 5 chunks. "
        "Consider re-chunking documents at a finer granularity (200 tokens vs 400)."
    ),
    "answer_relevancy": (
        "Response Relevance",
        "Responses address the general topic but miss the user's specific question. "
        "Add query-specific resolution paths to each runbook section. "
        "Review the response generator prompt to reinforce focusing on the exact question asked."
    ),
    "completeness": (
        "Incomplete Responses",
        "Key resolution steps from the knowledge base are being omitted in generated responses. "
        "Strengthen the system prompt: instruct the agent to enumerate all retrieved steps explicitly. "
        "Check that the context window is large enough to hold the full retrieved chunk."
    ),
    "actionability": (
        "Vague Action Steps",
        "Responses lack specific steps (tool names, menu paths, URLs). "
        "Update runbooks with numbered action items, exact menu paths, self-service portal links, "
        "and phone/ticket escalation contacts."
    ),
    "task_resolution": (
        "Unresolved User Issues",
        "Users cannot fully resolve their issue from the response alone. "
        "Add fallback steps, escalation contacts, and ticket portal URLs to each runbook. "
        "Ensure the escalation_decider node provides a summary context when routing to L2/L3."
    ),
    "professional_tone": (
        "Tone & Communication",
        "Response tone is inconsistent with enterprise IT support standards. "
        "Add explicit tone guidelines to the response generator system prompt: "
        "empathetic, concise, jargon-free, structured (greeting → steps → close)."
    ),
    "faithfulness": (
        "Hallucination Risk",
        "Agent is generating claims not supported by the retrieved knowledge base. "
        "Add a stronger constraint to the system prompt: 'Only use information from the retrieved context. "
        "Do not add steps or facts that are not explicitly in the provided runbooks.' "
        "Consider adding a faithfulness guard before returning the response."
    ),
    "toxicity": (
        "Safety Violation",
        "Harmful or inappropriate content detected in responses. "
        "Add a safety guardrail layer between the response generator and the API output. "
        "Review flagged responses manually and update the system prompt with explicit safety constraints."
    ),
}

INTENT_RUNBOOKS = {
    "VPN":      "VPN setup and troubleshooting runbook",
    "PASSWORD": "password reset and MFA procedures runbook",
    "HARDWARE": "laptop hardware fault reporting runbook",
    "SOFTWARE": "software installation request runbook",
    "NETWORK":  "network connectivity troubleshooting runbook",
    "EMAIL":    "email and calendar access runbook",
    "OTHER":    "general IT support knowledge base",
}


def generate_recommendations(all_scored_data: list[dict]) -> list[dict]:
    """
    Analyze patterns across all scored runs and return prioritized recommendations.

    Each recommendation: {severity, category, metric, avg_score, threshold, finding, recommendation}
    Sorted: HIGH first, then MEDIUM, then by avg_score ascending (worst first).
    """
    if not all_scored_data:
        return []

    recommendations = []

    THRESHOLDS = {
        "faithfulness": THR_FAITHFULNESS,
        "answer_relevancy": THR_ANSWER_RELEVANCY,
        "contextual_relevancy": THR_CONTEXTUAL,
        "completeness": THR_GEVAL,
        "actionability": THR_GEVAL,
        "professional_tone": THR_GEVAL,
        "task_resolution": THR_GEVAL,
        "toxicity": THR_SAFETY,
    }

    # ── 1. Aggregate metric scores ────────────────────────────────────────────
    metric_scores: dict[str, list[float]] = {}
    for run_data in all_scored_data:
        for metric_name, info in run_data.get("metrics", {}).items():
            score = info.get("score")
            if score is not None:
                metric_scores.setdefault(metric_name, []).append(score)

    avg_scores = {m: round(mean(s), 3) for m, s in metric_scores.items() if s}

    for metric_name, avg in sorted(avg_scores.items(), key=lambda x: x[1]):
        threshold = THRESHOLDS.get(metric_name)
        if threshold is None:
            continue
        cat, advice = METRIC_ADVICE.get(metric_name, ("Quality", "Review and improve."))

        if metric_name == "toxicity":
            if avg > threshold:
                gap = round(avg - threshold, 3)
                severity = "HIGH" if avg > threshold * 1.5 else "MEDIUM"
                recommendations.append({
                    "severity": severity,
                    "category": cat,
                    "metric": metric_name,
                    "avg_score": avg,
                    "threshold": threshold,
                    "finding": (
                        f"toxicity averages {avg:.3f} — exceeds the safety ceiling of "
                        f"{threshold} by {gap:.3f}. Immediate review required."
                    ),
                    "recommendation": advice,
                })
        else:
            if avg < threshold:
                gap = round(threshold - avg, 3)
                severity = "HIGH" if avg < threshold * 0.72 else "MEDIUM"
                recommendations.append({
                    "severity": severity,
                    "category": cat,
                    "metric": metric_name,
                    "avg_score": avg,
                    "threshold": threshold,
                    "finding": (
                        f"{metric_name} averages {avg:.3f} — {gap:.3f} below the "
                        f"SLA threshold of {threshold}."
                    ),
                    "recommendation": advice,
                })

    # ── 2. Intent-level quality analysis ─────────────────────────────────────
    by_intent: dict[str, list[float]] = {}
    for run_data in all_scored_data:
        intent = run_data.get("intent", "UNKNOWN")
        q = run_data.get("composites", {}).get("quality_score")
        if q is not None:
            by_intent.setdefault(intent, []).append(q)

    if len(by_intent) > 1:
        intent_avgs = {i: mean(s) for i, s in by_intent.items() if s}
        worst_intent = min(intent_avgs, key=intent_avgs.get)
        worst_avg = intent_avgs[worst_intent]
        overall_avg = mean([v for vlist in by_intent.values() for v in vlist])

        if worst_avg < 0.60 and worst_avg < overall_avg - 0.08:
            runbook = INTENT_RUNBOOKS.get(worst_intent, f"{worst_intent.lower()} runbook")
            severity = "HIGH" if worst_avg < 0.45 else "MEDIUM"
            recommendations.append({
                "severity": severity,
                "category": f"Intent Gap — {worst_intent}",
                "metric": "quality_score",
                "avg_score": round(worst_avg, 3),
                "threshold": 0.65,
                "finding": (
                    f"{worst_intent} queries score {worst_avg:.3f} quality on average — "
                    f"{round(overall_avg - worst_avg, 3):.3f} below the overall average of {overall_avg:.3f}."
                ),
                "recommendation": (
                    f"Expand the {runbook} with more specific troubleshooting steps "
                    f"and verified resolution procedures. Ensure embeddings cover "
                    f"common {worst_intent} error messages and symptoms."
                ),
            })

    # ── 3. Positive findings (INFO) ───────────────────────────────────────────
    passing = [m for m, avg in avg_scores.items()
               if m != "toxicity" and avg >= THRESHOLDS.get(m, 0.5)]
    if "safety_score" in {r.get("metric") for r in recommendations} is False:
        safety_scores = [
            run_data.get("composites", {}).get("safety_score")
            for run_data in all_scored_data
            if run_data.get("composites", {}).get("safety_score") is not None
        ]
        if safety_scores and mean(safety_scores) >= 0.95:
            recommendations.append({
                "severity": "INFO",
                "category": "Safety — Excellent",
                "metric": "safety_score",
                "avg_score": round(mean(safety_scores), 3),
                "threshold": 0.90,
                "finding": f"Safety score averages {mean(safety_scores):.3f} — well above the 0.90 threshold.",
                "recommendation": "No action required. Continue monitoring as query volume increases.",
            })

    # Sort: HIGH → MEDIUM → INFO, then worst score first within each group
    severity_rank = {"HIGH": 0, "MEDIUM": 1, "INFO": 2}
    recommendations.sort(
        key=lambda r: (severity_rank.get(r["severity"], 9), r.get("avg_score", 1.0))
    )

    return recommendations


# ── Summary run ───────────────────────────────────────────────────────────────

def log_summary(
    all_scores: list[dict],
    all_scored_data: list[dict] = None,
    user_count: int = 0,
):
    """
    Log aggregate eval metrics + recommendations to `it-helpdesk-eval-summary`.
    Saves eval_recommendations.json artifact with full pattern analysis.
    """
    if not all_scores:
        return

    mlflow.set_experiment(SUMMARY_EXPERIMENT)
    run_name = f"eval-summary-{user_count}users" if user_count else f"eval-summary-{len(all_scores)}runs"

    recommendations = generate_recommendations(all_scored_data or [])

    with mlflow.start_run(run_name=run_name):
        mlflow.log_param("runs_evaluated", len(all_scores))
        mlflow.log_param("user_count", user_count)
        mlflow.log_param("recommendations_count", len(recommendations))
        mlflow.log_param("high_severity_count",
                         sum(1 for r in recommendations if r.get("severity") == "HIGH"))

        for metric_key in (
            "quality_score", "rag_score", "helpdesk_score", "safety_score",
            "faithfulness", "answer_relevancy", "contextual_relevancy",
            "completeness", "actionability", "professional_tone", "task_resolution",
            "toxicity",
        ):
            vals = [r[metric_key] for r in all_scores if r.get(metric_key) is not None]
            if vals:
                mlflow.log_metric(f"avg_{metric_key}", round(mean(vals), 4))
                mlflow.log_metric(f"min_{metric_key}", round(min(vals), 4))

        # Save recommendations as artifact
        with tempfile.TemporaryDirectory() as tmpdir:
            recs_file = os.path.join(tmpdir, RECS_ARTIFACT)
            payload = {
                "generated_at": datetime.datetime.now().isoformat(),
                "runs_evaluated": len(all_scores),
                "user_count": user_count,
                "recommendations": recommendations,
            }
            with open(recs_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            mlflow.log_artifact(recs_file)

    print(f"\n[Recommendations] {len(recommendations)} findings generated:")
    for rec in recommendations:
        sev = rec["severity"]
        print(f"  [{sev}] {rec['category']}: {rec['finding'][:80]}")


# ── Load all existing scores from MLflow ──────────────────────────────────────

def _load_all_scored_data(client: MlflowClient):
    """
    Return (all_scores, all_scored_data) for every run in EXPERIMENT_NAME that
    already has a quality_score logged.  Used to build a comprehensive summary
    when running without --force (only new runs are scored this session).
    """
    _SCORE_KEYS = (
        "quality_score", "rag_score", "helpdesk_score", "safety_score",
        "faithfulness", "answer_relevancy", "contextual_relevancy",
        "completeness", "actionability", "professional_tone",
        "task_resolution", "toxicity",
    )
    _METRIC_KEYS = set(_SCORE_KEYS) - {"quality_score", "rag_score", "helpdesk_score", "safety_score"}
    _COMPOSITE_KEYS = {"quality_score", "rag_score", "helpdesk_score", "safety_score"}

    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if not experiment:
        return [], []

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string="",
        run_view_type=ViewType.ACTIVE_ONLY,
        max_results=200,
    )

    scores_list, data_list = [], []
    for run in runs:
        m = run.data.metrics
        if "quality_score" not in m:
            continue
        score_row = {"run_id": run.info.run_id}
        for k in _SCORE_KEYS:
            if k in m:
                score_row[k] = m[k]
        data_row = {
            "run_id":    run.info.run_id,
            "intent":    run.data.params.get("intent", "UNKNOWN"),
            "metrics":   {k: m[k] for k in _METRIC_KEYS if k in m},
            "composites":{k: m[k] for k in _COMPOSITE_KEYS if k in m},
        }
        scores_list.append(score_row)
        data_list.append(data_row)
    return scores_list, data_list


def _wrap_metrics_for_recs(data_list: list[dict]) -> list[dict]:
    """
    _load_all_scored_data stores metrics as flat floats {metric: value}.
    generate_recommendations expects {metric: {"score": value}}.
    This converter bridges the two formats.
    """
    result = []
    for row in data_list:
        new_row = dict(row)
        new_row["metrics"] = {k: {"score": v} for k, v in row.get("metrics", {}).items()}
        result.append(new_row)
    return result


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Phase 4: DeepEval quality scoring + pattern recommendations"
    )
    parser.add_argument("--run-id", help="Score a specific MLflow run ID only")
    parser.add_argument("--force", action="store_true",
                        help="Re-score runs even if already evaluated")
    parser.add_argument("--limit", type=int, default=50,
                        help="Maximum number of recent runs to evaluate (default: 50)")
    parser.add_argument("--user-count", type=int, default=0,
                        help="Concurrent user count (for summary labelling)")
    parser.add_argument("--cpu-mode", action="store_true",
                        help="Skip contextual_relevancy and faithfulness (both make many "
                             "concurrent LLM calls which queue up and timeout). "
                             "The other 6 metrics score reliably.")
    parser.add_argument("--overnight", action="store_true",
                        help="Run all 8 metrics including faithfulness (hallucination) and "
                             "contextual_relevancy. Disables DeepEval's per-attempt timeout so "
                             "concurrent requests can complete without being killed. "
                             "Implies --force. Estimated ~25-35 min per run — run unattended.")
    parser.add_argument("--summary-only", action="store_true",
                        help="Skip all scoring — just load existing MLflow scores and regenerate "
                             "the aggregate summary + recommendations artifact. Use after a run "
                             "that crashed before logging the summary.")
    args = parser.parse_args()

    # --overnight implies --force (re-score all runs to get full 8-metric coverage)
    if args.overnight:
        args.force = True

    mlflow.set_tracking_uri(MLFLOW_URI)
    client = MlflowClient()

    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if not experiment:
        print(f"[ERROR] Experiment '{EXPERIMENT_NAME}' not found. Run the agent first.")
        sys.exit(1)

    if args.overnight:
        os.environ["DEEPEVAL_DISABLE_TIMEOUTS"] = "true"
        n_runs = 12  # approximate
        est_hours = round(n_runs * 30 / 60, 1)
        print(f"\n[Overnight mode] All 8 metrics enabled including faithfulness (hallucination scoring).")
        print(f"  DeepEval per-attempt timeout DISABLED — concurrent Azure OpenAI requests will wait.")
        print(f"  --force is implied: all {n_runs} runs will be re-scored.")
        print(f"  Estimated runtime: ~{est_hours}h. Run and walk away.\n")

    print("Initialising Azure OpenAI judge (gpt-5.2-chat-2)…")
    judge = AzureJudge()
    metrics = build_metrics(judge)

    if args.cpu_mode and not args.overnight:
        del metrics["contextual_relevancy"]
        del metrics["faithfulness"]
        print("\n[CPU mode] Skipping contextual_relevancy and faithfulness.")
        print("  These metrics send multiple concurrent LLM requests which can queue up")
        print("  and exceed DeepEval's 88.5s per-attempt timeout.")
        print("  rag_score will be computed from answer_relevancy only.\n")

    print(f"\nLoaded {len(metrics)} metrics (→ 12 MLflow values + reasons artifact per run):")
    if args.cpu_mode and not args.overnight:
        categories = {
            "RAG · Generation ": ["answer_relevancy"],
            "Helpdesk (GEval) ": ["completeness", "actionability", "professional_tone", "task_resolution"],
            "Safety           ": ["toxicity"],
            "Composites       ": ["rag_score", "helpdesk_score", "safety_score", "quality_score"],
        }
    else:
        categories = {
            "RAG · Retrieval  ": ["contextual_relevancy"],
            "RAG · Generation ": ["faithfulness", "answer_relevancy"],
            "Helpdesk (GEval) ": ["completeness", "actionability", "professional_tone", "task_resolution"],
            "Safety           ": ["toxicity"],
            "Composites       ": ["rag_score", "helpdesk_score", "safety_score", "quality_score"],
        }
    for cat, names in categories.items():
        print(f"  {cat}: {', '.join(names)}")

    if args.run_id:
        runs = [client.get_run(args.run_id)]
    else:
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string="",
            run_view_type=ViewType.ACTIVE_ONLY,
            max_results=args.limit,
            order_by=["start_time DESC"],
        )

    if args.summary_only:
        print("\n[Summary-only mode] Loading all scored runs from MLflow…")
        existing_scores, existing_data = _load_all_scored_data(client)
        existing_data_wrapped = _wrap_metrics_for_recs(existing_data)
        if not existing_scores:
            print("[ERROR] No scored runs found in MLflow. Run scoring first.")
            sys.exit(1)
        print(f"  Found {len(existing_scores)} scored runs.")
        log_summary(existing_scores, existing_data_wrapped, user_count=args.user_count)
        print(f"\nAggregate summary + recommendations logged to: '{SUMMARY_EXPERIMENT}'")
        print(f"\nDone.")
        sys.exit(0)

    total = len(runs)
    print(f"\nFound {total} runs in '{EXPERIMENT_NAME}'. Starting evaluation…\n")
    print("=" * 70)

    all_scores = []
    all_scored_data = []
    skipped = 0

    for i, run in enumerate(runs, 1):
        run_name = run.data.tags.get("mlflow.runName", run.info.run_id[:8])
        query_preview = run.data.params.get("query", "?")[:60]
        intent = run.data.params.get("intent", "?")
        print(f"[{i}/{total}]  {run_name}  ({intent})")
        print(f"        Query: {query_preview}")

        t0 = time.time()
        result = score_run(run, metrics, client, force=args.force)
        elapsed = time.time() - t0

        if result is None:
            print("        → already evaluated, skipped\n")
            skipped += 1
            continue

        scores, reasons_data = result
        all_scores.append(scores)
        all_scored_data.append(reasons_data)

        def fmt(v): return f"{v:.3f}" if v is not None else "N/A"
        q = scores.get("quality_score")
        r = scores.get("rag_score")
        h = scores.get("helpdesk_score")
        s = scores.get("safety_score")
        print(f"        → quality={fmt(q)}  rag={fmt(r)}  helpdesk={fmt(h)}  safety={fmt(s)}  [{elapsed:.1f}s]\n")

    # ── Summary table ─────────────────────────────────────────────────────────
    print("=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"{'Run':<30} {'Quality':>8} {'RAG':>8} {'Helpdesk':>10} {'Safety':>8}")
    print("-" * 70)

    def fmt(v): return f"{v:.3f}" if v is not None else "  N/A"

    scored_runs_list = [r for r in runs if r.data.tags.get("mlflow.runName", "") not in []]
    for row, run in zip(all_scores, scored_runs_list):
        name = run.data.tags.get("mlflow.runName", run.info.run_id[:8])[:29]
        print(f"{name:<30} {fmt(row.get('quality_score')):>8} {fmt(row.get('rag_score')):>8} "
              f"{fmt(row.get('helpdesk_score')):>10} {fmt(row.get('safety_score')):>8}")

    if all_scores:
        print("-" * 70)

        def avg_col(key):
            vals = [r[key] for r in all_scores if r.get(key) is not None]
            return mean(vals) if vals else None

        print(f"{'AVERAGE':<30} "
              f"{fmt(avg_col('quality_score')):>8} "
              f"{fmt(avg_col('rag_score')):>8} "
              f"{fmt(avg_col('helpdesk_score')):>10} "
              f"{fmt(avg_col('safety_score')):>8}")
        print("=" * 70)

        print("\nSLA CHECK (thresholds from config.yaml):")
        for label, key, threshold in [
            ("quality_score    (target ≥ 0.70)", "quality_score", 0.70),
            ("faithfulness     (target ≥ 0.70)", "faithfulness", THR_FAITHFULNESS),
            ("answer_relevancy (target ≥ 0.70)", "answer_relevancy", THR_ANSWER_RELEVANCY),
        ]:
            val = avg_col(key)
            if val is not None:
                status = "PASS" if val >= threshold else "FAIL"
                print(f"  {label}: {val:.3f}  [{status}]")

        # Merge newly scored runs with all existing MLflow scores so the summary
        # covers all 12 runs even when --force is not used.
        # Note: use all_scored_data (not all_scores) for run_id — all_scores has only metric floats.
        existing_scores, existing_data = _load_all_scored_data(client)
        existing_data_wrapped = _wrap_metrics_for_recs(existing_data)
        new_ids = {r["run_id"] for r in all_scored_data}
        merged_scores = all_scores + [r for r in existing_scores if r["run_id"] not in new_ids]
        merged_data   = all_scored_data + [r for r in existing_data_wrapped if r["run_id"] not in new_ids]
        log_summary(merged_scores, merged_data, user_count=args.user_count)
        print(f"\nAggregate summary + recommendations logged to: '{SUMMARY_EXPERIMENT}'")

    print(f"\nDone. Evaluated: {len(all_scores)}  Skipped: {skipped}  Total: {total}")


if __name__ == "__main__":
    main()
