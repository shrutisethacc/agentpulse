import os
import time

from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

_KB_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base"))
_INDEX_CACHE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "faiss_index"))

_INTENT_FILE_MAP = {
    "VPN": "vpn_issues.txt",
    "PASSWORD": "password_reset.txt",
    "HARDWARE": "hardware_faults.txt",
    "SOFTWARE": "software_install.txt",
    "NETWORK": "vpn_issues.txt",
    "OTHER": None,
}

_embeddings: OllamaEmbeddings | None = None
_index: FAISS | None = None


def _get_embeddings() -> OllamaEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url="http://localhost:11434",
        )
    return _embeddings


def _build_index() -> FAISS:
    docs: list[Document] = []
    for intent, filename in _INTENT_FILE_MAP.items():
        if filename is None:
            continue
        path = os.path.join(_KB_DIR, filename)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # Split on blank lines to get logical paragraphs / runbook sections
        chunks = [c.strip() for c in content.split("\n\n") if c.strip()]
        for chunk in chunks:
            docs.append(Document(page_content=chunk, metadata={"intent": intent, "source": filename}))

    idx = FAISS.from_documents(docs, _get_embeddings())
    # Persist so subsequent restarts skip re-embedding (slow on CPU)
    idx.save_local(_INDEX_CACHE)
    return idx


def _get_index() -> FAISS:
    global _index
    if _index is None:
        if os.path.exists(_INDEX_CACHE):
            _index = FAISS.load_local(_INDEX_CACHE, _get_embeddings(), allow_dangerous_deserialization=True)
        else:
            _index = _build_index()
    return _index


def retrieve_knowledge(state: dict) -> dict:
    t_start = time.time()

    intent = state.get("intent", "OTHER")
    query = state.get("query", "")
    context = ""

    try:
        index = _get_index()
        results = index.similarity_search(query, k=5)
        # Prioritise chunks that match the classified intent, then fill with semantic matches
        intent_hits = [r for r in results if r.metadata.get("intent") == intent]
        other_hits = [r for r in results if r.metadata.get("intent") != intent]
        top = (intent_hits + other_hits)[:3]
        context = "\n\n".join(r.page_content for r in top)
    except Exception as exc:
        context = f"Knowledge retrieval error: {exc}"

    elapsed = time.time() - t_start
    timings = dict(state.get("node_timings") or {})
    timings["knowledge_retriever"] = round(elapsed, 4)

    return {"context": context, "node_timings": timings}
