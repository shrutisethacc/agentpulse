import time
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

VALID_INTENTS = ["VPN", "PASSWORD", "HARDWARE", "SOFTWARE", "NETWORK", "OTHER"]

_SYSTEM_PROMPT = """You are an IT helpdesk intent classifier. Classify the user query into exactly one of these categories:
- VPN: issues with VPN connection, corporate network tunneling, remote access
- PASSWORD: password reset, account lockout, MFA issues, credential problems
- HARDWARE: physical device issues — laptop, monitor, keyboard, mouse, printer
- SOFTWARE: software installation, license issues, application errors, software requests
- NETWORK: internet connectivity, Wi-Fi, network drives, DNS, proxy (but NOT VPN)
- OTHER: anything that does not fit the above categories

Respond in this exact format (two lines only):
INTENT: <category>
CONFIDENCE: <decimal between 0.0 and 1.0>"""


def classify_intent(state: dict) -> dict:
    t_start = time.time()

    llm = ChatOllama(model="llama3.2:3b", base_url="http://localhost:11434", temperature=0)
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=state["query"]),
    ]
    response = llm.invoke(messages)
    raw = response.content.strip()

    intent = "OTHER"
    confidence = 0.5

    for line in raw.splitlines():
        if line.startswith("INTENT:"):
            candidate = line.split(":", 1)[1].strip().upper()
            if candidate in VALID_INTENTS:
                intent = candidate
        elif line.startswith("CONFIDENCE:"):
            try:
                confidence = float(line.split(":", 1)[1].strip())
                confidence = max(0.0, min(1.0, confidence))
            except ValueError:
                confidence = 0.5

    elapsed = time.time() - t_start
    timings = dict(state.get("node_timings") or {})
    timings["intent_classifier"] = round(elapsed, 4)

    return {"intent": intent, "confidence": confidence, "node_timings": timings}
