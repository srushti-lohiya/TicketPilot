# 🛟 SupportPilot — AI customer-support agent with ML routing, RAG and guardrails

SupportPilot reads a customer ticket, figures out what the customer wants, finds the right
help-center policy, looks up their order, and then **either answers automatically, drafts a reply
for a human to approve, or escalates** — and it can prove which of those it should do.

```
ticket ─► PII redaction ─► injection check ─► intent classifier (27 intents, calibrated)
                                                    │
                          risk & priority (P1–P4) ◄─┤
                                                    ▼
                     intent-aware hybrid RAG (BM25 + dense + RRF [+ cross-encoder])
                                                    ▼
             agent (Claude tool use: search_kb · lookup_order · check_refund_eligibility
                    · cancel_order · escalate_to_human)   — or offline fallback agent
                                                    ▼
                 output guardrails (citations required, no unauthorised promises)
                                                    ▼
             auto_resolved  |  needs_review (human approves)  |  escalated
                                                    ▼
              SQLite ─► FastAPI ─► Streamlit review dashboard ─► feedback ─► retraining
```

## Results (all reproducible with `make all`)

**1. The classic benchmark lies.** On Bitext's own test split the classifier gets **99.9%**
accuracy, because the dataset is template-generated. On 66 hand-written realistic tickets
(messy emails + 12 out-of-scope ones like legal threats, app bugs, prompt injection) it gets **~67%**.

**2. So the system decides *when* to trust itself.** The auto-resolve threshold is picked on a
dev split with a cost function (a wrong automatic answer costs 3× a correct one) and reported on a held-out split:

| Realistic held-out tickets | Value |
|---|---|
| Auto-resolved answers with correct intent | **100%** |
| Out-of-scope tickets auto-answered | **0%** |
| In-scope coverage of auto-resolve | ~30% (the rest get a human-reviewed draft) |

**3. Retrieval: routing beats fancier search.** recall@3 on realistic tickets:

| BM25 | Dense | Hybrid (RRF) | **Hybrid + intent routing** |
|---|---|---|---|
| 0.61 | 0.69 | 0.65 | **0.85** |

**4. End-to-end (offline fallback agent, 66 tickets):** 0 out-of-scope tickets auto-resolved,
100% auto-resolve precision, 95% guardrail pass rate, p95 latency ≈ 4 ms.
Run `make eval-llm` to add the Claude agent and an LLM-as-judge (faithfulness / helpfulness).

## Quick start

The Next.js operations console is available in [`frontend/`](frontend/README.md). It uses the existing API and local fallback mode; the Streamlit dashboard remains runnable.

```bash
pip install -r requirements.txt
make all                         # download data → train → retrieval eval → e2e eval → tests
make api                         # http://127.0.0.1:8000/docs
make ui                          # dashboard
export ANTHROPIC_API_KEY=...     # optional: real LLM agent
docker compose up --build        # API :8000 + dashboard :8501
```

## Design decisions
* **Calibrated abstention over raw accuracy** — the threshold is a business decision, made explicit.
* **The LLM never issues refunds** — it checks eligibility; a human approves. Cancels only work on unshipped orders.
* **Ticket text is data, not instructions** — injection detection + system-prompt rule + escalation.
* **Everything runs offline** — the fallback agent keeps CI, tests and demos free and deterministic.
* **Feedback loop** — reviewers' intent corrections are added to training on the next `make train`.

## Data & limitations
Bitext Customer Support dataset (CDLA-Sharing 1.0), downloaded at build time. The knowledge base and
order database are a fictional store ("Nimbus Store"). The realistic test set is small (66 tickets);
treat its numbers as indicative and grow it with real tickets from the feedback loop.

## Portfolio hosting (prepared, not deployed)

The zero-cost Vercel Hobby frontend (`frontend/` project root) and Render Free native Python backend are documented in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Hosting uses the existing model with lightweight TF-IDF retrieval, explicit CORS, isolated ephemeral demo storage and disabled privileged actions. Remote deployments and pushes require owner approval.
