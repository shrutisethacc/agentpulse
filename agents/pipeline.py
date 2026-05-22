import io
import os
import sys
import time
import uuid
from typing import TypedDict

# MLflow 2.22.5 prints emoji to stdout on run end — cp1252 on Windows can't encode it
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Silence MLflow's "git not in PATH" warning — harmless but noisy
os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")

import mlflow
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from agents.intent_classifier import classify_intent
from agents.knowledge_retriever import retrieve_knowledge
from agents.response_generator import generate_response
from agents.escalation_decider import decide_escalation

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("it-helpdesk-agent-evals")
# mlflow.langchain.autolog() removed — causes 'MlflowSpanProcessor has no attribute _metrics'
# in MLflow 2.22.5 + LangGraph. Replaced with explicit @mlflow.trace spans below.


class AgentState(TypedDict):
    query: str
    intent: str
    confidence: float
    context: str
    response: str
    escalate: bool
    escalation_reason: str
    trace_id: str
    node_timings: dict
    # Speed & cost metrics — populated by response_generator
    ttft_seconds: float
    input_tokens: int
    output_tokens: int
    tokens_per_second: float
    cost_usd: float


def _timed_node(node_fn, state: AgentState) -> AgentState:
    updates = node_fn(state)
    return {**state, **updates}


@mlflow.trace(name="classify_intent", span_type="CHAIN")
def _classify_node(state: AgentState) -> AgentState:
    return _timed_node(classify_intent, state)


@mlflow.trace(name="retrieve_knowledge", span_type="RETRIEVER")
def _retrieve_node(state: AgentState) -> AgentState:
    return _timed_node(retrieve_knowledge, state)


@mlflow.trace(name="generate_response", span_type="LLM")
def _generate_node(state: AgentState) -> AgentState:
    return _timed_node(generate_response, state)


@mlflow.trace(name="decide_escalation", span_type="CHAIN")
def _escalate_node(state: AgentState) -> AgentState:
    return _timed_node(decide_escalation, state)


def _build_graph() -> object:
    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", _classify_node)
    graph.add_node("retrieve_knowledge", _retrieve_node)
    graph.add_node("generate_response", _generate_node)
    graph.add_node("decide_escalation", _escalate_node)
    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "generate_response")
    graph.add_edge("generate_response", "decide_escalation")
    graph.add_edge("decide_escalation", END)
    return graph.compile()


_compiled_graph = _build_graph()

app = FastAPI(title="IT Helpdesk Agent", version="2.0.0")


class QueryRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/invoke")
def invoke(request: QueryRequest):
    trace_id = str(uuid.uuid4())
    pipeline_start = time.time()

    initial_state: AgentState = {
        "query": request.query,
        "intent": "",
        "confidence": 0.0,
        "context": "",
        "response": "",
        "escalate": False,
        "escalation_reason": "",
        "trace_id": trace_id,
        "node_timings": {},
        "ttft_seconds": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "tokens_per_second": 0.0,
        "cost_usd": 0.0,
    }

    with mlflow.start_run(run_name=f"helpdesk-{trace_id[:8]}"):
        mlflow.log_param("query", request.query)
        mlflow.log_param("trace_id", trace_id)

        with mlflow.start_span(name="IT-Helpdesk-Agent") as root_span:
            root_span.set_inputs({"query": request.query})
            final_state = _compiled_graph.invoke(initial_state)
            root_span.set_outputs({
                "intent": final_state.get("intent", ""),
                "escalate": final_state.get("escalate", False),
                "response_preview": final_state.get("response", "")[:200],
            })

        pipeline_elapsed = round(time.time() - pipeline_start, 4)
        timings = final_state.get("node_timings", {})

        mlflow.log_metric("latency_intent_classifier", timings.get("intent_classifier", 0))
        mlflow.log_metric("latency_knowledge_retriever", timings.get("knowledge_retriever", 0))
        mlflow.log_metric("latency_response_generator", timings.get("response_generator", 0))
        mlflow.log_metric("latency_escalation_decider", timings.get("escalation_decider", 0))
        mlflow.log_metric("latency_total_pipeline", pipeline_elapsed)
        mlflow.log_metric("confidence", final_state.get("confidence", 0.0))
        mlflow.log_metric("escalated", int(final_state.get("escalate", False)))
        # Speed & cost metrics
        mlflow.log_metric("ttft_seconds",      final_state.get("ttft_seconds", 0.0))
        mlflow.log_metric("input_tokens",      final_state.get("input_tokens", 0))
        mlflow.log_metric("output_tokens",     final_state.get("output_tokens", 0))
        mlflow.log_metric("tokens_per_second", final_state.get("tokens_per_second", 0.0))
        mlflow.log_metric("cost_usd",          final_state.get("cost_usd", 0.0))
        mlflow.log_param("intent", final_state.get("intent", ""))
        mlflow.log_param("escalation_reason", final_state.get("escalation_reason", ""))

        # Artifact consumed by Phase 4 eval_runner — stores full text data
        # (response + context can exceed MLflow's 500-char param limit)
        mlflow.log_dict(
            {
                "query": request.query,
                "intent": final_state.get("intent", ""),
                "confidence": final_state.get("confidence", 0.0),
                "response": final_state.get("response", ""),
                "context": final_state.get("context", ""),
                "escalated": final_state.get("escalate", False),
                "escalation_reason": final_state.get("escalation_reason", ""),
                "total_latency_seconds": pipeline_elapsed,
                "ttft_seconds": final_state.get("ttft_seconds", 0.0),
                "input_tokens": final_state.get("input_tokens", 0),
                "output_tokens": final_state.get("output_tokens", 0),
                "tokens_per_second": final_state.get("tokens_per_second", 0.0),
                "cost_usd": final_state.get("cost_usd", 0.0),
            },
            "eval_data.json",
        )

    return JSONResponse(content={
        "trace_id": trace_id,
        "query": final_state["query"],
        "intent": final_state["intent"],
        "confidence": final_state["confidence"],
        "context": final_state["context"],
        "response": final_state["response"],
        "escalate": final_state["escalate"],
        "escalation_reason": final_state["escalation_reason"],
        "node_timings": final_state["node_timings"],
        "total_latency_seconds": pipeline_elapsed,
        "ttft_seconds": final_state.get("ttft_seconds", 0.0),
        "input_tokens": final_state.get("input_tokens", 0),
        "output_tokens": final_state.get("output_tokens", 0),
        "tokens_per_second": final_state.get("tokens_per_second", 0.0),
        "cost_usd": final_state.get("cost_usd", 0.0),
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
