import time

_ESCALATION_PHRASES = [
    "unable to resolve",
    "cannot resolve",
    "escalated to a human agent",
    "please contact support",
    "i don't have enough information",
]


def decide_escalation(state: dict) -> dict:
    t_start = time.time()

    intent = state.get("intent", "OTHER")
    confidence = state.get("confidence", 1.0)
    response = state.get("response", "").lower()

    escalate = False
    escalation_reason = ""

    if confidence < 0.4:
        escalate = True
        escalation_reason = f"Low classifier confidence: {confidence:.2f}"
    elif intent == "OTHER":
        escalate = True
        escalation_reason = "Query intent could not be categorised into a known IT domain"
    elif any(phrase in response for phrase in _ESCALATION_PHRASES):
        escalate = True
        escalation_reason = "Response generator indicated insufficient information to resolve the query"

    elapsed = time.time() - t_start
    timings = dict(state.get("node_timings") or {})
    timings["escalation_decider"] = round(elapsed, 4)

    return {
        "escalate": escalate,
        "escalation_reason": escalation_reason,
        "node_timings": timings,
    }
