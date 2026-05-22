import os
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv(Path(__file__).parent.parent / ".env")

_SYSTEM_PROMPT = """You are a corporate IT support agent. Resolve the user's IT issue using the provided context.
Reply in 2-3 sentences maximum. Be direct and specific. No preamble, no disclaimers.
If context is insufficient, say only: "This issue will be escalated to a human agent." """

_INPUT_COST_PER_TOKEN  = 0.15 / 1_000_000   # $0.15 per 1M input tokens
_OUTPUT_COST_PER_TOKEN = 0.60 / 1_000_000   # $0.60 per 1M output tokens


def _make_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        openai_api_key=os.environ["AZURE_OPENAI_API_KEY"],
        openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        streaming=True,
    )


def generate_response(state: dict) -> dict:
    t_start = time.perf_counter()

    query   = state.get("query", "")
    context = state.get("context", "")
    intent  = state.get("intent", "OTHER")

    user_message = f"""User Query: {query}

Relevant Runbook Context (Intent: {intent}):
{context}

Please provide a resolution."""

    llm = _make_llm()
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ]

    # Stream to capture Time to First Token (TTFT)
    ttft: float | None = None
    chunks = []
    for chunk in llm.stream(messages):
        if ttft is None and chunk.content:
            ttft = round(time.perf_counter() - t_start, 4)
        chunks.append(chunk)

    response = "".join(c.content for c in chunks).strip()
    elapsed  = round(time.perf_counter() - t_start, 4)
    ttft     = ttft if ttft is not None else elapsed

    # Token counts from usage_metadata (AzureChatOpenAI populates on last chunk)
    usage = None
    for chunk in reversed(chunks):
        usage = getattr(chunk, "usage_metadata", None)
        if usage:
            break

    input_tokens  = int((usage or {}).get("input_tokens", 0))
    output_tokens = int((usage or {}).get("output_tokens", 0))
    tokens_per_sec = round(output_tokens / elapsed, 1) if elapsed > 0 and output_tokens else 0.0
    cost_usd = round(
        input_tokens * _INPUT_COST_PER_TOKEN + output_tokens * _OUTPUT_COST_PER_TOKEN, 6
    )

    timings = dict(state.get("node_timings") or {})
    timings["response_generator"] = elapsed

    return {
        "response":          response,
        "node_timings":      timings,
        "ttft_seconds":      ttft,
        "input_tokens":      input_tokens,
        "output_tokens":     output_tokens,
        "tokens_per_second": tokens_per_sec,
        "cost_usd":          cost_usd,
    }
