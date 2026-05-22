import mlflow
from mlflow.tracking import MlflowClient

mlflow.set_tracking_uri("http://localhost:5000")
client = MlflowClient()

exp = mlflow.get_experiment_by_name("it-helpdesk-agent-evals")
if not exp:
    print("ERROR: Experiment not found - is MLflow running?")
else:
    runs = client.search_runs([exp.experiment_id], order_by=["start_time DESC"], max_results=50)
    scored = [r for r in runs if "quality_score" in r.data.metrics]
    has_artifact = [r for r in runs if "quality_score" not in r.data.metrics]
    print(f"it-helpdesk-agent-evals: {len(runs)} total runs, {len(scored)} scored")
    if scored:
        print("\nScored runs (latest 5):")
        for r in scored[:5]:
            q   = r.data.metrics.get("quality_score", 0)
            rag = r.data.metrics.get("rag_score", 0)
            hd  = r.data.metrics.get("helpdesk_score", 0)
            sf  = r.data.metrics.get("safety_score", 0)
            intent = r.data.params.get("intent", "?")
            name   = r.data.tags.get("mlflow.runName", r.info.run_id[:8])
            print(f"  {name:<30}  intent={intent:<12}  quality={q:.3f}  rag={rag:.3f}  helpdesk={hd:.3f}  safety={sf:.3f}")
    else:
        print("\nNo scored runs yet. Run:  uv run python -m evals.eval_runner")

exp2 = mlflow.get_experiment_by_name("it-helpdesk-eval-summary")
if exp2:
    sruns = client.search_runs([exp2.experiment_id], order_by=["start_time DESC"], max_results=10)
    print(f"\nit-helpdesk-eval-summary: {len(sruns)} summary runs")
    for r in sruns:
        uc = r.data.params.get("user_count", "?")
        aq = r.data.metrics.get("avg_quality_score", None)
        print(f"  user_count={uc}  avg_quality={aq:.3f if aq else 'N/A'}")
else:
    print("\nit-helpdesk-eval-summary: not found")
