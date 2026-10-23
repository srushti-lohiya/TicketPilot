"""Step 4: guardrails.
  input : PII redaction (emails, phones, card numbers via Luhn check, SSNs) + prompt-injection detection
  output: every reply must cite a retrieved KB section, and must not promise things only a human can do
"""
import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
SSN = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")

INJECTION = [r"ignore (all |any )?(previous|prior|above) (instructions|rules)", r"system prompt",
             r"you are now", r"developer mode", r"jailbreak", r"act as (an? )?(admin|developer)",
             r"\b100% (off|discount)", r"reveal (your|the) (instructions|prompt)"]

FORBIDDEN = {  # phrase -> why it needs a human
    r"\bi (have )?(refunded|issued (a|your) refund)": "only humans issue refunds",
    r"\bguarantee": "no guarantees",
    r"\blegal advice\b": "no legal advice",
    r"\bcompensation of \$": "no compensation offers",
    r"\bdiscount code\b": "no discount codes",
}


def luhn_ok(digits: str) -> bool:
    d = [int(c) for c in digits][::-1]
    total = sum(d[0::2]) + sum(sum(divmod(2 * x, 10)) for x in d[1::2])
    return total % 10 == 0


def redact_pii(text: str):
    found = []

    def card(m):
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and luhn_ok(digits):
            found.append("card"); return "[CARD]"
        return m.group()

    text = CARD.sub(card, text)
    for pat, tag in [(EMAIL, "email"), (SSN, "ssn"), (PHONE, "phone")]:
        if pat.search(text):
            found.append(tag)
            text = pat.sub(f"[{tag.upper()}]", text)
    return text, sorted(set(found))


def detect_injection(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in INJECTION)


def check_reply(reply: str, citations, retrieved_ids, executed_actions=()):
    issues = []
    if not reply or len(reply.strip()) < 20:
        issues.append("empty reply")
    if not citations:
        issues.append("no citation")
    elif not set(citations) <= set(retrieved_ids):
        issues.append("cites a section that was not retrieved")
    low = reply.lower()
    for pat, why in FORBIDDEN.items():
        if re.search(pat, low) and "refund_issued" not in executed_actions:
            issues.append(f"forbidden: {why}")
    if len(reply) > 1500:
        issues.append("reply too long")
    return issues
