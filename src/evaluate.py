"""Step 8: end-to-end evaluation on eval/realistic_tickets.csv.

Measures what matters in production:
  * routing: share auto-resolved / needs_review / escalated
  * safety : out-of-scope tickets that were NOT auto-resolved (should be 100%)
  * auto-resolve precision: auto-resolved tickets whose intent was right
  * grounding: replies whose citation is a correct KB section for the true intent
  * guardrail pass rate, latency p50/p95, tokens
  * optional LLM-as-judge (needs API key): faithfulness + helpfulness, 1-5
Run:  python -m src.evaluate            (fallback agent)
      python -m src.evaluate --llm      (LLM agent + judge)
"""
import argparse, json
import numpy as np
import pandas as pd

from src import store
from src.config import ROOT, REPORTS_DIR, JUDGE_MODEL
from src.llm import client, llm_available
from src.pipeline import handle_ticket

JUDGE = """You grade a customer-support reply.
TICKET: {ticket}
HELP-CENTER SECTIONS THE AGENT CITED: {sections}
REPLY: {reply}
Score 1-5:
faithfulness = every claim in the reply is supported by the sections or is a neutral pleasantry
helpfulness  = the reply addresses what the customer actually needs
Return only JSON: {{"faithfulness": n, "helpfulness": n}}"""


def judge(ticket, reply, cites):
    from src.retrieval import get_retriever
    text = {c.id: c.text for c in get_retriever().chunks}
    sections = " | ".join(f"[{c}] {text.get(c, '')}" for c in cites)
    r = client().messages.create(model=JUDGE_MODEL, max_tokens=60,
                                 messages=[{"role": "user", "content": JUDGE.format(ticket=ticket, sections=sections, reply=reply)}])
    t = "".join(b.text for b in r.content if b.type == "text")
    return json.loads(t[t.find("{"): t.rfind("}") + 1])


def main(use_llm=False):
    store.init_db()
    gold = json.loads((ROOT / "eval" / "intent_to_kb.json").read_text())
    df = pd.read_csv(ROOT / "eval" / "realistic_tickets.csv")
    rows = []
    for text, true in zip(df["text"], df["intent"]):
        r = handle_ticket(text, use_llm=use_llm, save=False)
        oos = true == "out_of_scope"
        row = {"text": text, "true": true, "pred": r["intent"], "status": r["status"], "oos": oos,
               "intent_ok": r["intent"] == true, "latency_ms": r["latency_ms"],
               "tokens": r["tokens_in"] + r["tokens_out"], "guard_ok": not r["guardrail_issues"],
               "has_reply": r["status"] != "escalated",
               "grounded": (not oos) and bool(set(r["citations"]) & set(gold.get(true, [])))}
        if use_llm and row["has_reply"]:
            row.update(judge(text, r["reply"], r["citations"]))
        rows.append(row)
        store.reset_orders()
    res = pd.DataFrame(rows)
    ins, auto, drafted = res[~res.oos], res[res.status == "auto_resolved"], res[res.has_reply & ~res.oos]
    summary = {
        "agent": "llm" if use_llm else "fallback", "tickets": len(res),
        "routing": res["status"].value_counts(normalize=True).round(3).to_dict(),
        "out_of_scope_not_auto_resolved": float((res[res.oos].status != "auto_resolved").mean()),
        "auto_resolve_precision": float(auto["intent_ok"].mean()) if len(auto) else None,
        "auto_resolve_coverage_in_scope": float((ins.status == "auto_resolved").mean()),
        "grounded_citation_rate": float(drafted["grounded"].mean()) if len(drafted) else None,
        "guardrail_pass_rate": float(res[res.has_reply]["guard_ok"].mean()),
        "latency_ms_p50": float(np.percentile(res.latency_ms, 50)),
        "latency_ms_p95": float(np.percentile(res.latency_ms, 95)),
        "avg_tokens_per_ticket": float(res.tokens.mean()),
    }
    if use_llm and "faithfulness" in res:
        summary["judge_faithfulness"] = float(res["faithfulness"].mean())
        summary["judge_helpfulness"] = float(res["helpfulness"].mean())
    print(json.dumps(summary, indent=2, default=lambda x: round(x, 3)))
    name = "llm" if use_llm else "fallback"
    res.to_csv(REPORTS_DIR / f"e2e_{name}.csv", index=False)
    (REPORTS_DIR / f"e2e_{name}.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--llm", action="store_true")
    a = p.parse_args()
    if a.llm and not llm_available():
        raise SystemExit("Set ANTHROPIC_API_KEY to run the LLM evaluation.")
    main(a.llm)
