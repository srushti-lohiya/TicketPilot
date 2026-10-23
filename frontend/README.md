# TicketPilot frontend

Next.js console for the existing FastAPI, trained classifier, retrieval pipeline and SQLite database. HTTP intake uses no paid API. Use Node 22 (`nvm use` from this folder). For the prepared Vercel Hobby + Render Free setup, environment variables, measured resource limits and approval-gated deployment steps, see [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md).

## Run locally

From the repository root:

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/uvicorn src.api:app --reload --host 127.0.0.1 --port 8000
```

In another terminal run `cd frontend` and `npm run dev`, then open http://localhost:3000. If Docker owns port 8000, use the existing updated image with `docker compose up -d --no-build --no-deps api` instead of launching a second server. Python source changes require an image update. The normal Dockerfile retrains during build; use the source-only recipe in `../docs/API_CONNECTION_AUDIT.md` to retain existing models. The named database volume is retained. For a disposable database, start FastAPI with `DB_PATH=/tmp/ticketpilot-demo.db`.

The browser calls same-origin `/api/backend/*`. Next.js forwards allowlisted routes to server-only `TICKETPILOT_API_URL`, default `http://127.0.0.1:8000`. Set this in `frontend/.env.local` and restart Next.js after changes. Browser-to-FastAPI CORS is unnecessary for this path. The proxy forwards the caller's Authorization header and never injects server credentials. Health timeout is 5 seconds; other requests time out after 30 seconds. POSTs are never retried automatically.

## Connection and data provenance

Header and System Mode now read one shared health state, verified on mount, every 60 seconds while the tab is visible and on browser reconnect. Transport/server failures invalidate it. A successful health check validates the response before marking the connection healthy. Resources reload on connection changes and clear stale data on errors.

| Screen | Backend endpoints |
| --- | --- |
| Overview | `/metrics`, `/tickets`; shared `/health` |
| Inbox / Review | `/tickets`, including status filters |
| New Ticket | `POST /tickets`, always `use_llm:false` |
| Detail | `/tickets/{id}`, `/intents`, `POST /tickets/{id}/feedback` |
| Analytics | `/metrics` |

Live backend data uses the deterministic fallback **agent**, including the real classifier and retrieval. That agent still requires FastAPI. It is distinct from **Offline demo data**, which consists only of unprocessed drafts stored in this browser.

On transport/server read failures, lists and metrics explicitly show offline data. Counts are computed from local drafts; latency and ratings remain unavailable. No prefilled tickets or fabricated operational measurements are used. Missing live ticket details show an error rather than a fabricated record. Validation and permission errors never fall back.

If an intake health preflight fails, the message is saved as an explicitly unclassified, unprocessed local draft with a negative ID. Drafts can be opened, reloaded and viewed in offline Inbox/Review/Analytics. No classifier, retrieval or backend processing is claimed. Avoid personal information: localStorage drafts have no server PII redaction. Drafts are not automatically synced. If a POST fails after preflight, the user gets an error and is asked to check the inbox; no offline duplicate is created. Offline feedback/approval is rejected.

Evaluation Lab statically bundles the versioned `src/data/evaluation.v1.json` snapshot, generated from actual repository reports. It works without the API or a runtime reports mount. Source paths, modification dates, content hashes, sample sizes and measurement scopes remain visible. Missing metrics show **Not measured**. No evaluation numbers appear as operational metrics. From the repository root, regenerate with `.venv/bin/python -m src.evaluation_snapshot` and check freshness with `.venv/bin/python -m src.evaluation_snapshot --check`. To use a different report directory, pass `--reports-dir /path/to/reports` during generation. `TICKETPILOT_REPORTS_DIR` is no longer a runtime setting. Rebuild the frontend after updating the snapshot. Neither generation nor page viewing runs inference, evaluation, training or order tools.

The lab includes the saved majority baseline/classifier comparison, per-intent benchmark report, eight recorded retrieval comparisons, measured pipeline safety and latency, and a confusion matrix derived from recorded in-scope pipeline predictions. The matrix covers 54 realistic development + test tickets; it is not the held-out classifier's 27 in-scope cases or the 3,642-case Bitext benchmark. Encoder/reranker identity, realistic held-out macro F1 and original benchmark confusion counts are not present in the saved reports and are labeled accordingly.

New processed tickets capture versioned observable `decision_metadata`: top-three classifier candidates and threshold, initial retrieval section text/rank/score, runtime encoder/reranker state, input-check outputs, and actual output-guardrail execution state. The AI decision inspector displays these alongside the existing routing, risk flags, tool input/output events, final draft, review status and processing latency. Evidence is captured during processing; ticket GETs do not rerun inference or retrieval. A backward-compatible SQLite migration adds one nullable JSON column. Older tickets retain citation IDs and explicitly show **Not recorded** for unavailable historical evidence. Offline drafts remain unprocessed. This is decision metadata, not a generated reasoning or chain-of-thought trace. See `../docs/EVALUATION_AND_INSPECTOR.md` for source mappings, limitations and browser verification.

## Authorization

Public HTTP intake always uses the free deterministic agent and a request-scoped read-only order policy. Both agent tool paths reach the same guarded cancellation function. Blocked cancellations become needs-review and do not mutate orders. Internal isolated evaluation tools retain their existing mock-order behavior.

Public callers can save ratings/comments. Approvals (including `approved:false`) and corrected training intents require a bearer credential matching server-only `TICKETPILOT_REVIEWER_TOKEN`. Missing configuration fails closed. Configure this on FastAPI only. The public console disables privileged controls; reviewer calls may use FastAPI directly or the proxy with the caller's Authorization header. No privileged token is bundled into the frontend.

Approval checks and feedback writes share a SQLite `BEGIN IMMEDIATE` transaction. Only low-risk needs-review tickets without risk reasons or output guardrail issues are eligible. Escalated/resolved/auto-resolved, P1/P2, and financial/account-changing tickets are rejected with 409 even for reviewers. Approval records a resolution; it sends no message and executes no order action. No privileged order-execution endpoint is exposed.

## Verification

From the repository root:

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m pytest -q
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:3000/api/backend/health
cd frontend
npm run lint
npm run typecheck
npm run build
npm run test:e2e
```

Playwright starts disposable key-free FastAPI on 8011 and production Next.js on 3011. Build first and leave these ports free. Tests use existing model artifacts, free TF-IDF retrieval and temporary databases; they do not overwrite the normal database or evaluation reports. Build uses Webpack to avoid an existing restricted-environment Turbopack worker issue.

## Remaining limits

The reviewer token is a minimal demo credential, not multi-user identity, tenant isolation or an audit system. There is no authenticated order ownership/execution workflow, specialist-resolution endpoint, outbound delivery or rate limiting. Offline drafts require explicit resubmission after reconnect. Direct browser requests to port 8000 are not supported by CORS configuration; use the same-origin proxy.
