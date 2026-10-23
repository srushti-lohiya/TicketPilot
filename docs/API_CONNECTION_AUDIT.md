# API connection and authorization audit

Completed 2026-10-24 (local time).

## Diagnosis

At inspection, both `http://localhost:8000/health` and `http://localhost:3000/api/backend/health` returned HTTP 200 with `status:ok` and `llm:false`. FastAPI was running in the existing Docker API container; Next.js was running locally on port 3000. No frontend `.env.local` was present. The configured default upstream is `http://127.0.0.1:8000`.

The contradictory UI had an architectural cause: Shell and Overview independently called `/health` through separate `useResource` instances. Shell persists across navigation and its health request was never retried. An initial failure could remain in the header while Overview made a later successful check. Overview could also retain old successful data after a refresh failure because `useResource` did not clear its previous data. The exact historical request failure was not captured; a persistent outage was not reproducible during inspection. The separate-state/stale-data defect was confirmed in the source and reproduced with connection-state browser tests.

The browser uses the same-origin Next.js `/api/backend/*` proxy. Next.js contacts FastAPI server-side, so FastAPI CORS does not block this path. Direct browser requests to port 8000 have no configured CORS allowance and are not the intended client path.

“Fallback” originally meant the deterministic Python agent, which still requires FastAPI, the classifier and retrieval. The original client had no browser-local fallback dataset. Saved evaluation results are independent report files.

## Result

Header and System Mode consume one shared, validated health state, refreshed on mount, every 15 seconds and on reconnect. Backend request failures invalidate that state. Resources reload on connection changes, and errors clear old data. Dataset labels remain attached to the data: live responses, browser-local offline drafts, and static evaluation artifacts are distinct.

All six requested operational screens use existing verified backend endpoints. Overview uses metrics/tickets; Inbox/Review use ticket lists with status filters; intake posts tickets with `use_llm:false`; Detail fetches ticket/intents and posts feedback; Analytics fetches metrics. Failed list/metrics reads use explicitly labeled local drafts. Counts derive from drafts; unavailable latency/ratings/priority assessments are not invented. Missing live ticket details remain errors. Failed POSTs are never automatically retried or silently replaced with offline duplicates.

Offline intake saves an explicitly unclassified, unprocessed browser-local draft after a failed health preflight. It has a negative ID and supports local detail/reload/inbox/review/analytics flows. It never claims model inference, retrieval, PII scanning or order execution. Drafts require explicit resubmission after reconnect.

Public HTTP intake executes under a request-scoped read-only order policy. The guarded tool blocks cancellation for both agent paths. Denied cancellation routes to needs-review. Paid LLM HTTP requests are rejected. Internal evaluation tool behavior remains intact.

Approvals and training-label corrections require a caller bearer token matching server-only `TICKETPILOT_REVIEWER_TOKEN`; missing configuration fails closed. Public ratings/comments remain allowed. The proxy forwards caller credentials and never supplies privileged credentials itself. The public console disables approvals/corrections.

An authenticated reviewer still cannot approve escalated, already resolved, auto-resolved, P1/P2, risky, guardrail-failing, financial/account-changing or cancellation/refund-action tickets. Eligibility checks and feedback insertion/status update run in a single SQLite `BEGIN IMMEDIATE` transaction. Repeated approvals return 409 without another feedback insertion. Approval sends no message and executes no order action.

## Exact repository files changed

| File | Change |
| --- | --- |
| `src/api.py` | Public capabilities, free/read-only HTTP processing, reviewer authentication, validation and conflict responses |
| `src/tools.py` | Request-scoped cancellation restriction |
| `src/pipeline.py` | Route blocked cancellations to review |
| `src/store.py` | Atomic approval eligibility and feedback transaction |
| `tests/test_system.py` | Update public cancellation/feedback expectations for required restrictions |
| `tests/test_api_permissions.py` (new) | Authentication, missing configuration, approval eligibility, repeat approvals, paid model restrictions |
| `frontend/src/lib/api.ts` | Validate health, propagate failures, safe offline reads/intake, reject offline mutations |
| `frontend/src/lib/connection.ts` (new) | Shared health state and subscription hook |
| `frontend/src/lib/offline.ts` (new) | Browser-local unprocessed drafts and derived counts |
| `frontend/src/lib/types.ts` | Offline metric provenance flag |
| `frontend/src/hooks/use-resource.ts` | Reload on connection changes and clear stale data on errors |
| `frontend/src/components/shell.tsx` | Shared health polling, reconnect handling and mode labels |
| `frontend/src/components/overview.tsx` | Shared System Mode state and dataset provenance |
| `frontend/src/components/inbox.tsx` | Offline list/review provenance and permission copy |
| `frontend/src/components/new-ticket.tsx` | Explain deterministic processing and public/offline limits |
| `frontend/src/components/ticket-detail.tsx` | Disable public privileged controls and distinguish unprocessed local drafts |
| `frontend/src/components/common.tsx` | Show offline priority as unassessed |
| `frontend/src/components/analytics.tsx` | Distinguish live metrics and local draft counts |
| `frontend/src/app/api/backend/[...path]/route.ts` | Forward caller authorization and bound timeouts |
| `frontend/src/app/tickets/[id]/page.tsx` | Support negative local draft IDs |
| `frontend/tests/workspace.spec.ts` | Real backend flows, public restrictions, outage/recovery, offline persistence and uncertain POST behavior |
| `frontend/README.md` | Current setup, endpoint contracts, provenance, authorization, verification and limits |
| `docs/API_CONNECTION_AUDIT.md` (new) | This audit and exact change/test/deployment record |

This checkout has no `.git` metadata, so the inventory records the files intentionally edited during this task rather than a Git diff. No model, training data, retrieval implementation or evaluation report was edited or regenerated. No other repository was modified.

## Final verification results

| Check | Result |
| --- | --- |
| Backend pytest | **23 passed** |
| Frontend lint | **Passed** |
| Frontend typecheck | **Passed** |
| Frontend production build | **Passed** |
| Playwright E2E | **10 passed** |
| Live FastAPI and Next.js proxy | Health, list, existing detail, intents and metrics passed |
| Live permission checks | Unauthenticated approval/correction and paid LLM requests returned 403 through both entrypoints |
| Live-data preservation | Verification added no tickets; persistent volume retained |
| Deployed model preservation | Identical SHA-256 before/after: `7f20bb507d3c8e430a4adc55b7f5bdeb5c3558ec216352a4e667a4b3348fd98e` |

E2E servers and backend tests use temporary databases. Browser tests run real local model/retrieval processing without paid keys, plus intercepted failures for connection/fallback cases. Initial sandbox port restrictions were resolved by authorized execution outside the sandbox. Missing Playwright Chromium was installed. One test selector was narrowed to exclude Next.js's route announcer; the final full run passed.

## Running local API update

The API container originally held the old source. Its normal Dockerfile retrains the classifier during a full build. To preserve the running trained model and installed dependencies, the update used a source-only layer over the previous local image:

```dockerfile
FROM ticketpilot-api:before-api-fix-20261024
COPY src/api.py src/tools.py src/store.py src/pipeline.py /app/src/
```

The previous API image is retained as `ticketpilot-api:before-api-fix-20261024`. The source-only image is tagged `ticketpilot-api:latest`. Only the API was recreated using `docker compose up -d --no-build --no-deps api`; the existing database volume and dashboard container were retained. The temporary build recipe is `/tmp/ticketpilot-api-source.Dockerfile`.

For future source-only updates, retain the existing trained image and use this recipe instead of the normal full Docker build if retraining is undesired. The normal Dockerfile was not changed by this task.

## Local verification commands

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

FastAPI should report `status:ok`, `mode:public_demo`, `order_writes:false`, `approvals:false`. The last field describes the public console, not an authenticated reviewer's capability. Browser tests require free ports 8011 and 3011. For a non-Docker backend, use the uvicorn command in the frontend README. Do not start a second API on an occupied port.

## Remaining limits

No verification blockers remain. Reviewer authorization uses a shared server-side token, not individual user accounts, tenant boundaries or an audit system. No authenticated order-execution/ownership, specialist-resolution or outbound-delivery workflow was added. There is no rate limiting. Offline drafts stay in browser localStorage without server PII scanning and require manual resubmission. Public ticket reads and low-impact ratings/comments remain available in this demo. These are deployment/product limits, not bypasses of the enforced public approval and order-write restrictions.
