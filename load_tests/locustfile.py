"""
Locust load test for the IT Helpdesk Agent API.

Run headless (recommended for CI / MLflow logging):
  locust -f load_tests/locustfile.py \
         --host http://localhost:8001 \
         --users 50 --spawn-rate 5 \
         --run-time 120s --headless

Run with web UI (interactive demo):
  locust -f load_tests/locustfile.py --host http://localhost:8001
  # then open http://localhost:8089
"""

import random

import mlflow
from locust import HttpUser, between, events, task

QUERIES = [
    {"query": "My VPN keeps disconnecting every few minutes"},
    {"query": "I forgot my password and cannot log in to my account"},
    {"query": "My laptop screen is flickering and has black bars"},
    {"query": "I need to install Microsoft Teams on my new laptop"},
    {"query": "Cannot connect to the company Wi-Fi network"},
    {"query": "My email inbox is not syncing on Outlook"},
    {"query": "How do I reset my MFA authenticator after getting a new phone?"},
    {"query": "The printer on floor 3 is showing offline status"},
    {"query": "I need admin rights to install a software approved by my manager"},
    {"query": "My computer is extremely slow and freezing frequently"},
    {"query": "VPN certificate error when connecting from home"},
    {"query": "I need to request a new hardware laptop, my current one is broken"},
]


class ITHelpdeskUser(HttpUser):
    """Simulates a single IT helpdesk end-user submitting support queries."""

    wait_time = between(1, 3)

    @task
    def invoke_agent(self):
        payload = random.choice(QUERIES)
        with self.client.post("/invoke", json=payload, catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}: {resp.text[:200]}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log aggregated Locust stats to MLflow when the test ends."""
    stats = environment.stats.total
    if stats.num_requests == 0:
        return

    mlflow.set_tracking_uri("http://localhost:5000")
    mlflow.set_experiment("it-helpdesk-load-test")

    user_count = (
        getattr(environment.parsed_options, "num_users", None)
        or getattr(environment.runner, "target_user_count", None)
        or getattr(environment.runner, "user_count", 0)
    )

    with mlflow.start_run(run_name=f"locust-{user_count}users"):
        mlflow.log_param("user_count", user_count)
        mlflow.log_param("host", environment.host)

        mlflow.log_metric("requests_total", stats.num_requests)
        mlflow.log_metric("failures_total", stats.num_failures)
        mlflow.log_metric("error_rate_pct", round(stats.fail_ratio * 100, 2))
        mlflow.log_metric("avg_response_time_ms", round(stats.avg_response_time, 1))
        mlflow.log_metric("p50_response_time_ms", stats.get_response_time_percentile(0.50) or 0)
        mlflow.log_metric("p95_response_time_ms", stats.get_response_time_percentile(0.95) or 0)
        mlflow.log_metric("p99_response_time_ms", stats.get_response_time_percentile(0.99) or 0)
        mlflow.log_metric("rps_peak", round(stats.total_rps, 3))

    print(
        f"\n[MLflow] Load test run logged — "
        f"{stats.num_requests} reqs | "
        f"p95={stats.get_response_time_percentile(0.95):.0f}ms | "
        f"errors={stats.fail_ratio * 100:.1f}%"
    )
