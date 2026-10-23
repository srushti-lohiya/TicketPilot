"""Step 5: priority + risk scoring (transparent rules; every point has a reason)."""
import re

CRITICAL = {r"\blawyer|\blegal action|\bsue\b|\blawsuit": "legal threat",
            r"\bhack(ed)?\b|\bfraud|unauthori[sz]ed|didn'?t make": "security / fraud",
            r"\binjur|\bburn(ed)?\b|\bfire\b|\bunsafe\b": "safety issue",
            r"\bchargeback\b|\bdispute\b": "chargeback",
            r"\bjournalist|\bpress\b|\bmedia\b": "press inquiry"}
NEGATIVE = r"\b(terrible|awful|worst|unacceptable|ridiculous|furious|angry|disgusting|rude|scam|useless)\b"
REPEAT = r"\b(third|3rd|again|still|multiple times|several times|second time)\b"
URGENT = r"\b(urgent|asap|immediately|right now|now!)\b"
HIGH_INTENTS = {"complaint": 2, "payment_issue": 2, "contact_human_agent": 1, "delete_account": 1, "track_refund": 1}


def assess(text: str, intent: str):
    t = text.lower()
    reasons, score = [], 0
    for pat, why in CRITICAL.items():
        if re.search(pat, t):
            reasons.append(why); score += 5
    if re.search(NEGATIVE, t): reasons.append("negative sentiment"); score += 2
    if re.search(REPEAT, t): reasons.append("repeat contact"); score += 1
    if re.search(URGENT, t) or t.count("!") >= 3: reasons.append("urgent"); score += 1
    letters = [c for c in text if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.5 and len(letters) > 15:
        reasons.append("shouting"); score += 1
    if intent in HIGH_INTENTS:
        reasons.append(f"intent: {intent}"); score += HIGH_INTENTS[intent]
    priority = "P1" if score >= 5 else "P2" if score >= 3 else "P3" if score >= 1 else "P4"
    return {"priority": priority, "risk_score": score, "risk_reasons": reasons,
            "critical": score >= 5}
