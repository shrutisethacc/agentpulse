import os
import re
import time

import yaml
from rank_bm25 import BM25Okapi

_KB_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base"))
_CFG_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "config.yaml"))

def _load_top_k() -> int:
    try:
        with open(_CFG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f).get("rag", {}).get("top_k", 5)
    except Exception:
        return 5

# Fix: NETWORK now has a dedicated runbook; OTHER falls back to general_it.txt
_INTENT_FILE_MAP = {
    "VPN":      "vpn_issues.txt",
    "PASSWORD": "password_reset.txt",
    "HARDWARE": "hardware_faults.txt",
    "SOFTWARE": "software_install.txt",
    "NETWORK":  "network_issues.txt",
    "OTHER":    "general_it.txt",
}

_corpus: list[dict] | None = None  # [{text, intent, source}, ...]
_bm25: BM25Okapi | None = None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _load_corpus() -> tuple[list[dict], BM25Okapi]:
    global _corpus, _bm25
    if _corpus is not None:
        return _corpus, _bm25

    docs = []
    for intent, filename in _INTENT_FILE_MAP.items():
        if filename is None:
            continue
        path = os.path.join(_KB_DIR, filename)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        chunks = [c.strip() for c in content.split("\n\n") if c.strip()]
        for chunk in chunks:
            docs.append({"text": chunk, "intent": intent, "source": filename})

    tokenized = [_tokenize(d["text"]) for d in docs]
    _corpus = docs
    _bm25 = BM25Okapi(tokenized)
    return _corpus, _bm25


def retrieve_knowledge(state: dict) -> dict:
    t_start = time.time()

    intent = state.get("intent", "OTHER")
    query = state.get("query", "")
    context = ""

    try:
        corpus, bm25 = _load_corpus()
        scores = bm25.get_scores(_tokenize(query))

        # Rank all docs; boost docs whose intent matches the classified intent
        ranked = sorted(
            enumerate(scores),
            key=lambda x: (corpus[x[0]]["intent"] == intent, x[1]),
            reverse=True,
        )
        top_k = _load_top_k()
        top = [corpus[i]["text"] for i, _ in ranked[:top_k]]
        context = "\n\n".join(top)
    except Exception as exc:
        context = f"Knowledge retrieval error: {exc}"

    elapsed = time.time() - t_start
    timings = dict(state.get("node_timings") or {})
    timings["knowledge_retriever"] = round(elapsed, 4)

    return {"context": context, "node_timings": timings}
