"""Step 7: the orchestrator. One function, handle_ticket(), runs the whole flow:

  redact PII -> injection check -> classify intent -> risk/priority -> intent-aware retrieval
  -> route -> agent (LLM or fallback) -> output guardrails -> final status -> save

Final status:
  auto_resolved : confident + low risk + safe intent + guardrails pass  (reply sent automatically)
  needs_review  : agent drafted a reply, a human approves it
  escalated     : a human takes over (customer gets an acknowledgement)
"""
import time
from src import store
from src.agent import FallbackAgent, LLMAgent
from src.classifier import IntentClassifier
from src.guardrails import check_reply, detect_injection, redact_pii
from src.llm import llm_available
from src.retrieval import get_retriever
from src.risk import assess

AUTO_SAFE_INTENTS = {
    "check_payment_methods", "check_refund_policy", "delivery_options", "delivery_period", "create_account",
    "edit_account", "recover_password", "registration_problems", "set_up_shipping_address", "switch_account",
    "newsletter_subscription", "contact_customer_service", "place_order", "get_invoice", "review",
    "check_cancellation_fee", "track_order", "cancel_order"}
ACK = ("Thanks for contacting Nimbus Store. I've passed your message to a specialist on our team, "
       "who will reply within 4 business hours (1 hour for urgent issues).")

_clf = None


def classifier():
    global _clf
    if _clf is None:
        _clf = IntentClassifier.load()
    return _clf


def handle_ticket(text: str, use_llm: bool | None = None, save: bool = True) -> dict:
    t0 = time.perf_counter()
    use_llm = llm_available() if use_llm is None else use_llm
    clean, pii = redact_pii(text)
    clf = classifier()
    pred = clf.predict(clean)
    risk = assess(clean, pred["intent"])
    retriever = get_retriever()
    hints = [t["intent"] for t in pred["top3"]]
    hits = retriever.search(clean, k=3, intents=hints)
    injection = detect_injection(clean)

    reasons = []
    if injection: reasons.append("possible prompt injection")
    if risk["critical"]: reasons.append("critical risk: " + ", ".join(risk["risk_reasons"]))
    if pred["intent"] == "contact_human_agent": reasons.append("customer asked for a human")

    result = {"text": clean, "pii": pii, "intent": pred["intent"], "category": pred["category"],
              "confidence": pred["confidence"], "priority": risk["priority"], "risk_reasons": risk["risk_reasons"],
              "actions": [], "citations": [], "guardrail_issues": [], "tokens_in": 0, "tokens_out": 0}

    # Observable outputs only: preserve evidence from this run, never re-run retrieval for an old ticket.
    metadata = {
        "version": 1,
        "classifier": {"top3": pred["top3"], "threshold": clf.threshold, "confident": pred["confident"]},
        "retrieval": {"mode": "hybrid", "intent_hints": hints,
                      "encoder": getattr(getattr(retriever, "dense", None), "kind", None),
                      "reranker": bool(getattr(retriever, "reranker", None)),
                      "hits": [{"rank": n, **h} for n, h in enumerate(hits, 1)]},
        "input_checks": {"pii_redaction": "redacted" if pii else "no_patterns_detected",
                         "injection": "flagged" if injection else "passed",
                         "risk": "critical" if risk["critical"] else "flagged" if risk["risk_reasons"] else "clear"},
        "output_guardrails": {"status": "not_run", "reason": "Hard escalation before agent execution", "issues": []},
    }
    result["decision_metadata"] = metadata

    if reasons:                                      # hard escalation: no agent at all
        result.update(status="escalated", route_reasons=reasons, reply=ACK, agent="none")
    else:
        agent = LLMAgent() if use_llm else FallbackAgent()
        meta = {**pred, **risk}
        out = agent.run(clean, meta, hits)
        issues = [] if out["escalated"] else check_reply(out["reply"], out["citations"], out["retrieved_ids"],
                                                         [a["tool"] for a in out["actions"]])
        metadata["output_guardrails"] = {
            "status": "not_run" if out["escalated"] else "failed" if issues else "passed",
            "reason": "Agent escalated before output checks" if out["escalated"] else None,
            "issues": issues,
        }
        if out["escalated"]:
            status = "escalated"; reasons.append("agent escalated")
        elif any(a["tool"] == "cancel_order" and not a["output"].get("cancelled") for a in out["actions"]):
            status = "needs_review"; reasons.append("order change requires authorized human handling")
        elif issues:
            status = "needs_review"; reasons.append("guardrail issues")
        elif pred["confident"] and risk["priority"] in ("P3", "P4") and pred["intent"] in AUTO_SAFE_INTENTS:
            status = "auto_resolved"
        else:
            status = "needs_review"
            if not pred["confident"]: reasons.append(f"low intent confidence ({pred['confidence']})")
            if pred["intent"] not in AUTO_SAFE_INTENTS: reasons.append(f"intent {pred['intent']} needs human approval")
            if risk["priority"] in ("P1", "P2"): reasons.append(f"priority {risk['priority']}")
        result.update(status=status, route_reasons=reasons, reply=out["reply"] if not out["escalated"] else (out["reply"] or ACK),
                      citations=out["citations"], actions=out["actions"], guardrail_issues=issues,
                      agent=out["agent"], tokens_in=out["tokens_in"], tokens_out=out["tokens_out"])

    result["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    if save:
        result["id"] = store.save_ticket({k: v for k, v in result.items() if k != "id"})
    return result
