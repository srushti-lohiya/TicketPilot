# TicketPilot: repository audit and one-day plan

Implementation follow-up: the local Next.js console has now been added in [`frontend/`](../frontend/README.md). The audit below records the pre-implementation repository. Backend approval, identity, persistence and deployment safeguards remain pending; the frontend does not claim to implement them.

Inspected and validated on 2026-10-23. This is a plan, not a frontend implementation. Only this document was added; existing source, tests, model, database, and reports were preserved. No other project was accessed. This directory has no `.git` metadata or `AGENTS.md`; change history cannot be verified here.

## Architecture inventory

| Location | Actual responsibility |
| --- | --- |
| `src/api.py` | FastAPI app, currently titled **SupportPilot**, version `1.0`; seven application endpoints. Startup initializes SQLite and warms classifier/retriever. |
| `src/pipeline.py` | Redact → classify → assess risk → retrieve top three sections using predicted top-three intents → hard escalation or agent → reply checks → routing → persist. Injection is checked before agent execution, but after classification/retrieval. |
| `src/classifier.py` | Word TF-IDF (1–2 grams) + character TF-IDF (3–5 grams), logistic regression, top-three intent probabilities, intent-to-category mapping, abstention threshold. Reports calibration error; does **not** fit a separate probability calibrator. |
| `src/retrieval.py` | Markdown section chunks, local BM25, sentence-transformer embeddings if available or word/character TF-IDF cosine otherwise, reciprocal rank fusion with intent hints; optional cross-encoder reranker. Cached in-process. |
| `src/agent.py`, `src/llm.py` | Deterministic fallback and optional Anthropic tool loop; no multi-agent framework or local generative model. |
| `src/guardrails.py`, `src/risk.py` | Regex/Luhn redaction, injection patterns, citation/promise checks; transparent risk scores mapping to P1–P4. |
| `src/tools.py` | Five Python tools with JSON input schemas; mock order access and cancellation. |
| `src/store.py` | SQLite connections, schema/bootstrap, ticket/feedback CRUD, operational aggregates, feedback-label export, destructive mock-order reset. |
| `src/data.py` | Download Bitext ZIP if raw CSV absent, normalize placeholders/whitespace, remove case-insensitive duplicates, stratified 70/15/15 split. |
| `src/evaluate.py` | End-to-end routing/guardrail/citation/latency evaluation; optional paid LLM judge. |
| `dashboard.py`, `.streamlit/config.toml` | Existing Streamlit intake, review queue and analytics; server-side HTTP via `requests`, light theme and Altair charts. Google Fonts CSS is an external dependency. |
| `requirements.txt`, `Makefile` | Python dependencies and install/data/train/retrieval/eval/API/UI/test/Docker commands. No Python lockfile. |

Runtime flow stays in FastAPI. `auto_resolved` is a database routing label: there is no email/helpdesk delivery integration. Escalation returns an acknowledgement and records routing; there is no specialist notification or SLA scheduler. Refunds are never issued. No order, knowledge-base, evaluation-report, authentication, reply-edit, deletion, or dedicated approval API exists.

### Data, models and evaluations

- `models/intent_clf.joblib`: only repository model artifact (~2.6 MB), a joblib dictionary containing `model`, `intent_to_category`, `threshold`. Loaded artifact has **27 intents** and threshold **0.87**. Only load trusted artifacts: joblib deserialization can execute code.
- `data/raw/bitext_support.csv`; `data/processed/{train,val,test}.csv`: **16,991 / 3,641 / 3,642** processed rows. The validation CSV is loaded by training, but threshold selection actually uses realistic **dev** tickets.
- `eval/realistic_tickets.csv`: **66** tickets, 33 dev + 33 test, including 12 out-of-scope. `eval/intent_to_kb.json`: gold section mappings for 27 intents, also used for retrieval routing.
- `kb/{account,addresses,contact,invoices,orders,payments,refunds,returns,shipping,subscription}.md`: **10 documents / 32 sections**, IDs such as `shipping#tracking`. No persisted vector index. Embedding caches live outside the repository; no transformer weights are bundled here.
- `data/supportpilot.db`: existing default persistent database. Tables: `tickets`, `feedback`, `orders`. Seven fictional orders seeded only when `orders` is empty: 10233, 10345, 10432, 10561, 10877, 10992, 11001. Dates are relative to initialization, not refreshed daily.
- `reports/classifier_report.json`: Bitext accuracy 0.998902; realistic held-out in-scope accuracy 0.666667, threshold-only in-scope coverage 0.296296, accepted-intent accuracy 1.0 on this small split. `out_of_scope_escalated` here means confidence abstention, not actual pipeline escalation.
- `reports/classifier_per_intent.txt`: per-intent precision, recall, F1 and support.
- `reports/retrieval_eval.csv`: recall@3/MRR for BM25, dense, hybrid, hybrid+intent on 54 realistic in-scope and 540 sampled Bitext tickets. Saved realistic recall@3: **0.611111 / 0.981481 / 0.851852 / 0.888889**. The CSV does not record encoder/version provenance.
- `reports/e2e_fallback.csv`: per-ticket text, true/predicted intent, status, out-of-scope flag, correctness, latency, tokens, guardrail/reply/grounding flags. `reports/e2e_fallback.json`: 66 tickets; auto precision 1.0, in-scope auto coverage 0.185185, grounded-citation rate 0.686275, guardrail pass 0.949153, saved p95 **153.15 ms**. No LLM evaluation artifacts are present. `.gitkeep` files are placeholders.

README values for retrieval, coverage and latency differ from saved reports. Do not copy them into the UI. Classifier threshold coverage is not end-to-end auto-resolution coverage; correct intent and valid citation IDs do not establish answer correctness. End-to-end/retrieval summaries include realistic dev data, so they are not independent held-out production estimates.

## Verified API contracts

Verified from source, generated OpenAPI and `TestClient` against a temporary SQLite database. All successful application requests return **200**, including ticket creation. No endpoint declares a response model; OpenAPI success schemas are `{}`. The shapes below are observed/source-derived contracts, not generated response types.

| Method / path | Input | Success response |
| --- | --- | --- |
| `GET /health` | None | `{status: "ok", llm: boolean}`; `llm` tests only whether a key is nonempty. |
| `POST /tickets` | `TicketIn` | Created ticket object below; **no `created` timestamp** in this response. |
| `GET /tickets` | Optional `status`: `auto_resolved`, `needs_review`, `escalated`, `resolved`; integer `limit=100` | Bare array of stored ticket objects, newest ID first. No total/cursor/search/date filter. No limit bounds: `-1` returns all matching rows; `0` returns none. |
| `GET /tickets/{tid}` | Integer path parameter | Stored ticket object including `created`; missing ID → 404. |
| `POST /tickets/{tid}/feedback` | `FeedbackIn` | `{ok: true}`; missing ID → 404; nonempty unknown corrected intent → 422. |
| `GET /metrics` | None | Operational metrics object below, across the whole database. |
| `GET /intents` | None | Sorted array of the 27 classifier intent strings. |

Framework routes also exist: `GET/HEAD /openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc`.

Request schemas:

```ts
type TicketIn = {
  text: string;           // required, 3..5000 characters; whitespace is not stripped
  use_llm?: boolean | null; // default null: choose based on key presence
};
type FeedbackIn = {
  rating?: number | null; // integer 1..5
  approved?: boolean | null;
  corrected_intent?: string | null;
  comment?: string | null; // max 2000 characters
};
```

All feedback fields default to null; `{}` is accepted and creates a feedback row. Unknown body fields are ignored by default Pydantic configuration. An empty corrected-intent string bypasses the truthiness-based intent check. Validation is not configured as strict.

Observed response shape:

```ts
type Status = "auto_resolved" | "needs_review" | "escalated" | "resolved";
type Action = {
  tool: string;
  input: Record<string, unknown>;
  output: unknown; // tool-dependent, including error branches
};
type TicketCreated = {
  id: number;
  text: string; // redacted input, not original input
  pii: string[]; // detected categories, not original PII values
  intent: string;
  category: string;
  confidence: number;
  priority: "P1" | "P2" | "P3" | "P4";
  risk_reasons: string[];
  status: Status;
  route_reasons: string[];
  reply: string;
  citations: string[]; // IDs only; no section bodies or URLs
  actions: Action[];
  guardrail_issues: string[];
  agent: "fallback" | "llm" | "none";
  latency_ms: number;
  tokens_in: number;
  tokens_out: number;
};
type TicketStored = TicketCreated & { created: string }; // UTC ISO timestamp
type Metrics = {
  tickets: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  top_intents: Record<string, number>; // all counts, not top-N or frequency-sorted
  auto_resolve_rate: number; // fraction 0..1 of current status == auto_resolved
  latency_ms_p50: number | null;
  latency_ms_p95: number | null;
  tokens_in: number;
  tokens_out: number;
  avg_rating: number | null;
  feedback_count: number;
};
```

SQLite columns are nullable and reads have no response validation: legacy/manual rows can violate these observed types. Empty DB metrics have zero counts/rate/tokens, empty maps and null latency/rating. Latency uses sorted-index selection, unlike evaluation's interpolated NumPy percentiles. Repeated feedback affects rating/count aggregates; approval changes current-status metrics.

Storage schema: `tickets` stores the ticket fields above, with the six array fields (`pii`, `risk_reasons`, `route_reasons`, `citations`, `actions`, `guardrail_issues`) serialized as JSON TEXT; confidence/latency are REAL and ID/token counts INTEGER. `feedback` stores `id`, `ticket_id`, `created`, `rating`, `corrected_intent`, integer/null `approved`, `comment`. The `orders` fields are listed below. Only primary keys are constrained; no enum, NOT NULL or feedback foreign-key enforcement exists.

Errors: missing tickets return `{"detail":"ticket not found"}`; unknown corrected intent returns `{"detail":"unknown intent"}`. Invalid bodies/query/path values normally return 422 with `detail` validation entries (`loc`, `msg`, `type`, optionally `input`/`ctx`). Unhandled model/provider/storage failures return 500, potentially plain text. No unified error envelope exists.

### Tool contracts (internal, not HTTP endpoints)

| Tool | Published JSON input | Python result |
| --- | --- | --- |
| `search_kb` | Required `query: string` | Array of `{id,title,text,score}`. Python additionally accepts `intents=None`, `k=3`; these are not exposed in the tool schema. |
| `lookup_order` | Required `order_id: string` | `{id,status,items,total,ordered_at,delivered_at,final_sale,tracking,refund_status}` or `{error}`. Nullable delivery/tracking/refund fields; `final_sale` is an integer flag. |
| `check_refund_eligibility` | Required `order_id: string` | `{eligible:boolean,reason:string,needs_human_approval?:true}`. Approval flag is only included on the within-window delivered branch; no refund mutation. |
| `cancel_order` | Required `order_id: string` | `{cancelled:true,order_id}` or `{cancelled:false,reason}`. Only exact status `Processing` can change to `Cancelled`. |
| `escalate_to_human` | Required `reason: string`; optional `priority` enum P1–P4, Python default P3 | `{escalated:true,reason,priority}`; no notification is sent and returned priority does not update pipeline priority. |

Both agents return `{reply,citations,actions,escalated,retrieved_ids,tokens_in,tokens_out,agent}`. Classifier additionally returns internal `confident` and `top3: {intent,p}[]`; risk adds internal `risk_score`/`critical`; these are not ticket response fields.

## Fallback behavior and guardrails

With no `ANTHROPIC_API_KEY`, omitted/null `use_llm` selects `FallbackAgent`; explicit false always selects it. It extracts the first five-digit order ID matching `1\d{4}`, looks it up, may cancel based on predicted `cancel_order` intent, or checks refund eligibility for refund-related intents. It joins order facts with the first two sentences of the highest-ranked KB section and cites that section. Tokens are zero. It assumes at least one retrieved hit. Shared routing can still produce review/escalation.

This is free local inference, not local text generation. Base requirements support BM25 + TF-IDF without model downloads. Installed `sentence-transformers` attempts BGE loading; failures fall back to TF-IDF. The current environment has cached `BAAI/bge-small-en-v1.5`; offline verification loaded it, reranker off. First-time optional model use can require network access. Explicit `use_llm:true` without a key returned **500**; invalid keys/provider failures also have no exception fallback. No key was supplied or needed for this audit.

Input protections redact email, US-style phone, SSN and Luhn-valid card patterns. Injection patterns, critical risk score ≥5, or predicted `contact_human_agent` hard-escalate without running an agent. Risk adds legal/security/safety/chargeback/press, negative sentiment, repeats, urgency, shouting and high-risk intents. Output checks require ≥20-character replies, at least one citation from retrieved IDs, ≤1500 characters, and reject regex matches for refund promises, guarantees, legal advice, compensation and discount codes. Agent escalations skip these output checks. Low confidence, unsafe intents, high priority or output issues produce review; 18 allowlisted intents including cancellation can auto-resolve when confident, P3/P4 and checks pass.

Protections are heuristic: they do not prove semantic grounding, broad PII removal, explicit cancellation consent, or order ownership. The LLM system prompt's 120-word limit is not the output check's character limit. Tools execute before output checks and final routing. LLM tool inputs are passed straight to Python functions without local schema validation; exceptions and exhausted step budgets are not robustly handled (`AGENT_MAX_STEPS=0` leaves `resp` undefined).

## Risks and blockers

| Priority | Finding and implication | Smallest planned response |
| --- | --- | --- |
| P0 | `approved:true` resolves **any** existing status, including escalated/auto-resolved, without identity, state check, guardrail recheck or audit actor. Repeated approvals create more rows; false does not reject/reopen. | Enforce needs-review approval atomically in storage; reject stale/invalid transitions with 409; preserve feedback-only submissions and add regression coverage. Keep public access blocked until authentication/authorization is supplied. |
| P0 | Cancellation mutates orders during drafting, even for low-confidence or subsequently reviewed output. Fallback relies on intent classification, not explicit consent; LLM restriction is prompt-only. No ownership verification. | Keep demo orders explicit. Before real-order integration, require authenticated ownership and enforced consent; stage mutating actions until authorized execution. Do not claim the review button authorizes already-executed actions. |
| P0 | No authentication, tenant isolation, rate limits or TLS in app/Compose; published ports bind all interfaces by default. CORS is not access control. | Default local demo bindings to loopback in deployment work; no public deployment until existing hosting identity/TLS controls are defined. Do not add a new auth microservice in one day. |
| P1 | Dashboard's feedback-only button is disabled with an inaccurate claim: omitting `approved` already saves feedback and preserves status. | Wire it to existing feedback endpoint without approval; approval safety must be enforced server-side, not just by disabled buttons. |
| P1 | SQLite has no migrations, foreign-key constraint for feedback, WAL setup, explicit lock handling, backups/restore, retention or actor audit. Cancellation read/update is not atomic and ticket-save failure does not undo it. Comments are not redacted. | Keep one API instance and named volume for demo; bound reads, make approval transitions transactional, document backup/restore and data retention. Defer real-order writes until transaction/idempotency design is complete. |
| P1 | No CORS middleware. Verified JSON preflight from localhost:3000 returns 405, no allow-origin header. | Prefer a same-origin Next.js rewrite to the existing API; if direct browser access is chosen, configure explicit allowed origins. Never use wildcard credentialed CORS. |
| P1 | Responses untyped; forced LLM causes 500; health reports key presence only; list limits unbounded; no pagination. | Add response models preserving create/read shapes, bound `limit`, explicitly handle unavailable LLM mode, document errors. Client search must say it searches loaded rows. |
| P1 | Evaluation `save=False` still executes tools, and `reset_orders()` deletes/reseeds all orders after every case. Training imports feedback from configured DB, allowing duplicate/conflicting labels and evaluation leakage. | Always use a disposable evaluation DB; never run eval against demo/live state. Deduplicate/review labels before later retraining. |
| P1 | Docker uses Python 3.11 vs local 3.13; unpinned dependencies plus copied joblib have compatibility risk. Build retrains and may download data; includes raw/processed/model files; no non-root user, healthcheck or readiness wait. | Reproducible dependency/artifact strategy, Docker smoke test, non-root access to mounted DB, health/readiness and build-context review. Avoid retraining as a deployment side effect. |
| P2 | README/steps are stale; claimed `.github/workflows/ci.yml` is absent. Reports have no model/data/version manifest. Dashboard converts missing latency to zero. | Correct docs, show missing data as unavailable, keep operational and offline metrics separate, record evaluation provenance later. |

No `frontend/`, Node manifest, frontend packages, authentication configuration, CI workflow or frontend Docker service exists. New frontend dependencies must be installed when implementation is authorized. Current model configuration strings are unverified provider identifiers; paid LLM support is outside the default validation path. No blocker prevents a local fallback-based frontend; public deployment and real-order automation remain blocked on the safeguards above.

## Docker and configuration inventory

`Dockerfile`: `python:3.11-slim`, `/app`, apt `libgomp1/libstdc++6/ca-certificates`, pip requirements, `COPY . .`, create `/data`, run data preparation + classifier training, expose 8000, start Uvicorn on `0.0.0.0:8000`. `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, `DB_PATH=/data/ticketpilot.db`; runs as root.

`docker-compose.yml`: API with `ticketpilot_data:/data`, `8000:8000`; dashboard builds same image, runs Streamlit on `0.0.0.0:8501`, `8501:8501`, `API_URL=http://api:8000`, startup-order `depends_on`, both restart unless stopped. Dashboard does not mount the API DB, which is appropriate because it uses HTTP. Named volume survives ordinary restarts/down, but `down -v` destroys it. Optional embedding caches are not mounted.

`.dockerignore`: excludes `.venv`, Git/GitHub metadata, bytecode/test cache, `*.db`, `.env`/`.env.*`, Streamlit secrets and reports. Does not exclude data CSVs/model; add `frontend/node_modules` and `.next` before introducing frontend builds. No other Docker configurations were found.

Explicit application env settings (not every path is overridable despite config docstring):

| Variable | Default / consumer |
| --- | --- |
| `DB_PATH` | `<repo>/data/supportpilot.db`; Docker overrides `/data/ticketpilot.db`. Read at import. |
| `AGENT_MAX_STEPS` | `6`, LLM rounds; no range validation. |
| `LLM_MODEL` / `JUDGE_MODEL` | `claude-sonnet-5-5` / `claude-haiku-5-5`, optional Anthropic paths only. |
| `ANTHROPIC_API_KEY` | Absent by default; availability check and Anthropic SDK. No dotenv loader. |
| `DENSE_MODEL` | `BAAI/bge-small-en-v1.5`, optional sentence transformer. |
| `RERANK_MODEL` / `USE_RERANKER` | `cross-encoder/ms-marco-MiniLM-L-6-v2` / disabled unless exactly `1`. |
| `API_URL` | `http://127.0.0.1:8000`, Streamlit only. |

`HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE` were used only as optional-library controls during verification; they are not TicketPilot settings. No credentials were read or created.

## One-day implementation checklist (future work, 8 hours)

Scope: a local operator workspace in `frontend/` using Next.js + TypeScript + Tailwind + shadcn/ui, retaining FastAPI, SQLite, ML/retrieval and Streamlit. No new backend service/framework, no model migration, no paid inference. Timebox assumes an existing artifact and working Python environment. Frontend implementation is **not** part of this audit.

- [ ] **0:00–0:45 — Baseline/contracts:** preserve the 11 tests; add response models without changing current create/read fields; define 409 approval errors, unavailable-LLM behavior and bounded list limits. Add focused tests for status-preserving feedback, invalid/repeated approvals, validation and missing-key selection.
- [ ] **0:45–2:00 — Minimal API safety:** atomic needs-review-only approval plus feedback insert; no implicit resolution for correction/rating. Handle forced unavailable LLM as a documented client error. Preserve cancellation's existing test and demo behavior; clearly document that real-order approval gating is deferred and blocks production.
- [ ] **2:00–2:45 — Frontend foundation:** initialize `frontend/` with requested stack and one Node lockfile; choose compatible supported versions at implementation time. Use shadcn Button/Card/Badge/Table/Tabs/Dialog/Select/Textarea/Alert and standard fetch; avoid adding global state/chart packages unless needed. Plan `app/`, `components/`, `lib/api.ts`, `lib/types.ts`. Use server-side **proposed** `TICKETPILOT_API_URL` for a same-origin rewrite to FastAPI; this variable does not exist today. Keep API logic in Python.
- [ ] **2:45–4:15 — Intake and ticket detail:** validated 3–5000-character form, submit `{text,use_llm:false}` by default; show actual status, intent/confidence, priority, route/risk reasons, reply, citations and tool results. Render text safely, no raw HTML. Handle submission/loading/422/network/500 states; no automatic POST retries. Do not label generated replies as delivered messages.
- [ ] **4:15–5:30 — Review queue:** existing status filter/list/detail endpoints, loaded-row search, rating/correction/comment feedback without `approved`, explicit approval only for needs-review tickets. Refresh ticket/metrics after mutations; handle 409/stale state; disable duplicate submission and escalated approval. No invented reject, edit-reply, server-search or pagination controls.
- [ ] **5:30–6:15 — Analytics:** only `/metrics` values, sorted intent counts, null shown as unavailable; health fallback badge. No synthetic trends, customer satisfaction claims, cost savings, historical latency charts or hardcoded evaluation scores. Citations remain IDs until a real KB-read contract is added; no fabricated links.
- [ ] **6:15–7:15 — Validation:** Python regression suite; frontend lint/typecheck/production build; intake→review→feedback→approval smoke test with disposable DB; check empty/error states, keyboard navigation and narrow screens. Prefer a small real-flow browser test if browser tooling is available, not snapshot tests mirroring markup.
- [ ] **7:15–8:00 — Local handoff:** accurate run/env instructions, same-origin proxy check, Docker API/Streamlit smoke check and volume restart check using disposable deployment state. Decide frontend hosting only after the production blockers are addressed. Keep Streamlit runnable.

If time slips, defer charts, Docker frontend packaging and visual polish. Do not cut approval regression tests or claim public-production readiness. Real-order authorization, durable outbound delivery, full identity/audit, migrations, label governance and report provenance are follow-up work, not a credible one-day promise.

## Validation evidence and commands

Completed during audit:

- `.venv/bin/python -m pytest -q`: **11 passed in 74.90s**, no test edits. Five system tests (safe auto-resolution, Processing-order cancellation, legal escalation, injection escalation, feedback/metrics); five guardrail/risk tests (PII/order IDs, invalid cards, injection, reply checks, priorities); one fake-client LLM tool-loop test (tool response, citation parsing, tokens). `tests/conftest.py` assigns a temporary DB and removes the API key. System tests skip without the classifier artifact; passing counts matter.
- Disposable-DB API probes verified all seven endpoint shapes, create/read timestamp difference, feedback-only preservation, approval bypass, negative limit, empty feedback, 404/422 cases, missing-key forced-LLM 500 and failed cross-origin preflight.
- End-to-end evaluation with sentence-transformers import deliberately unavailable proved the **base TF-IDF fallback** works with no key. Outputs and DB went to a temporary directory; 66 tickets, auto precision 1.0, in-scope coverage 0.185185, grounded-citation rate 0.686275, guardrail pass 0.949153, zero tokens. Measured p50/p95 **1.1/1.3 ms** in that run, not a deployment promise. Existing reports were untouched.
- Retrieval evaluation also completed with TF-IDF and temporary output: realistic recall@3 was 0.611111 BM25, 0.685185 TF-IDF, 0.648148 hybrid, 0.851852 hybrid+intent. This differs from the existing saved encoder run and confirms why backend provenance matters.
- `docker compose config --quiet` passed; daemon version **29.8.2** accessible. No image build, container startup or persistence restart was run. `.venv/bin/python -m pip check` reported no broken requirements.

From repository root, validate the existing installation:

```bash
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
docker compose config --quiet
```

Run API and dashboard in separate terminals; use an isolated demo DB if preserving existing state:

```bash
DB_PATH=/tmp/ticketpilot-manual-demo.db .venv/bin/uvicorn src.api:app --reload
.venv/bin/streamlit run dashboard.py
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/openapi.json
curl -fsS http://127.0.0.1:8000/intents
curl -fsS http://127.0.0.1:8000/metrics
curl -fsS -X POST http://127.0.0.1:8000/tickets \
  -H 'Content-Type: application/json' \
  -d '{"text":"Where is my order 10233?","use_llm":false}'
```

Reproduce evaluations without changing the existing DB or reports (writes only to a new temp directory; forces the base dependency path):

```bash
.venv/bin/python - <<'PY'
import os, sys, tempfile
from pathlib import Path
out = Path(tempfile.mkdtemp(prefix="ticketpilot-validation-"))
os.environ["DB_PATH"] = str(out / "evaluation.db")
os.environ.pop("ANTHROPIC_API_KEY", None)
sys.modules["sentence_transformers"] = None
from src import evaluate, retrieval
evaluate.REPORTS_DIR = retrieval.REPORTS_DIR = out
evaluate.main(False)
retrieval.evaluate()
print("Outputs:", out)
PY
```

For fresh setup only: create a virtualenv, install `requirements.txt`, then `python -m src.data` and `python -m src.classifier`. Those commands write datasets/model/reports and training can consume configured feedback. `make all` also retrains, overwrites reports and resets configured orders through evaluation; it is not a read-only health check. No paid `eval-llm` run is needed.

Container validation when ready: `docker compose up --build`, check API health and Streamlit, create a test ticket, restart API and confirm persistence, then `docker compose down` (without `-v`). This affects the configured named volume; use disposable state for testing. Build success/runtime behavior remain unverified in this audit.

After frontend implementation, intended checks from `frontend/`: `npm ci`, `npm run lint` (define the script if absent), `npx tsc --noEmit`, `npm run build`. These commands are prospective; no frontend currently exists.
