# TicketPilot: Vercel Hobby + Render Free

Prepared 2026-10-24. **No deployment, push, purchase, account connection, remote configuration change or live-service restart was performed.** Every server used for deployment testing was disposable and local. Obtain explicit owner approval before publishing code, creating/importing cloud projects, deploying, changing provider settings or running remote write smoke tests.

## Inspected starting state

The frontend is a Next.js App Router project inside `frontend/`; FastAPI is `src.api:app` at the repository root. The browser uses the same-origin `/api/backend/*` route, not a direct cross-origin API client. The Evaluation Lab bundles `frontend/src/data/evaluation.v1.json`, so Vercel needs neither Python nor access to `../reports` at runtime.

The previous Dockerfile installed the full development/dashboard stack, downloaded/prepared data, retrained the classifier during its build and bound a fixed port. The checkout had no root `.gitignore`. Local installed Python packages occupy about 1.4 GB, including approximately 583 MB of Torch files; frontend dependencies occupy about 598 MB. These are disk measurements, not RAM measurements, and must not be committed or uploaded as source.

The shipped classifier is **2,751,409 bytes** and serializes sklearn **1.9.1**. Serving pins match that artifact and the verified Python 3.13.4 runtime. No weights, evaluation reports, datasets, original tickets or original orders were changed. The existing local Docker API/dashboard were not restarted.

## Prepared hosting layout

```text
Browser → Vercel Next.js /api/backend/* → Render FastAPI
          static /evaluation             one Python worker
          bundled snapshot               isolated temporary SQLite
                                         existing classifier + BM25/TF-IDF/RRF
```

Only the frontend and the existing backend are used. There is no paid API, embedding download, external database, persistent disk, cron keepalive, new framework or additional microservice. The original full local requirements and optional embedding/LLM behavior remain available outside DEMO_MODE.

## Vercel configuration

| Setting | Value |
| --- | --- |
| Plan/account | Personal **Hobby**, no Pro trial or paid add-ons |
| Repository root directory | **`frontend`** |
| Framework | Next.js |
| Node | **22.x**, declared in `frontend/package.json` and `.nvmrc` |
| Install command | `npm ci` |
| Build command | `npm run build` |
| Output directory | Next.js default; do not set `out` or enable static export |
| Git auto deployments | Disabled by `frontend/vercel.json`; use an explicitly approved manual deployment |
| Server-only environment | `TICKETPILOT_API_URL=https://YOUR-API.onrender.com` |

Set the upstream variable separately for the intended Production and Preview environments. It is an **origin only**: HTTPS, no credentials, path, `/api`, `/api/backend`, query or fragment. Do not use `NEXT_PUBLIC_` for it. Do not put reviewer tokens, LLM keys, databases or model files in Vercel environment variables. Root-directory settings are documented by [Vercel](https://vercel.com/docs/project-configuration/general-settings); Node version overrides are documented [here](https://vercel.com/docs/functions/runtimes/node-js/node-js-versions).

The proxy allowlists existing endpoints, forwards the caller's Authorization header and preserves upstream statuses. It never injects a privileged credential. There is **no Next.js rewrite** to configure. Missing/invalid upstream configuration fails with 503 on Vercel rather than trying Vercel's localhost. Redirects are not followed with credentials. POST bodies are limited to 32 KiB. Upstream health timeout is 5 seconds, other calls 30 seconds, and the Node route declares a 45-second function duration. This is within both current Hobby and legacy non-Fluid duration ceilings; see [Vercel duration settings](https://vercel.com/docs/functions/configuring-functions/duration).

The browser continues to request `/api/backend/health`, `/tickets`, etc. Render CORS does not block this server-to-server hop. Static evaluation remains visible during backend sleep/outages; offline drafts remain explicitly unprocessed and browser-local. POSTs are never automatically retried or silently converted into duplicate local drafts after an uncertain submission. Health polling runs once per minute while the tab is visible and checks again on reconnect/focus; no external keepalive service is configured.

## Render configuration

Use a **native Python Web Service**, not the full local Docker image. Root Directory is blank/repository root. `render.yaml` defines one `plan: free` web service and disables automatic deployment with `autoDeployTrigger: "off"`. The Blueprint is preparation only; applying it creates a remote service and requires approval. Current Blueprint fields are described in [Render's reference](https://render.com/docs/blueprint-spec).

**Build command**

```sh
pip install --no-cache-dir -r requirements-render.txt && python scripts/check_runtime.py
```

**Start command**

```sh
sh scripts/start_render.sh
```

The start script sets numerical thread counts to one, then executes:

```sh
python -m uvicorn src.api:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --limit-concurrency 8 --timeout-keep-alive 5
```

Render supplies `PORT`; do not hardcode a cloud port. Health Check Path is **`/health`**. Startup loads the existing trusted joblib and constructs a 32-section retrieval index. It never downloads training data, retrains the classifier or runs the evaluation scripts. The build checker fails if the required artifact is missing, incompatible or cannot produce a prediction/retrieval result. Health reports ready only after model/index/database initialization and verifies database access.

| Environment variable | Render value |
| --- | --- |
| `PYTHON_VERSION` | `3.13.4` (also declared in root `.python-version`) |
| `DEMO_MODE` | `1` |
| `RETRIEVAL_BACKEND` | `tfidf` |
| `CORS_ORIGINS` | Exact production frontend origin, e.g. `https://YOUR-PROJECT.vercel.app`; comma-separated explicit preview origins may be added after approval |
| `HF_HUB_OFFLINE` | `1` |
| `TRANSFORMERS_OFFLINE` | `1` |
| `OPENBLAS_NUM_THREADS` | `1` |
| `OMP_NUM_THREADS` | `1` |
| `MKL_NUM_THREADS` | `1` |
| `PYTHONDONTWRITEBYTECODE` | `1` |
| `PYTHONUNBUFFERED` | `1` |
| `PORT` | Provider-supplied; do not override |
| `DB_PATH` | **Unset**; ignored in DEMO_MODE even if inherited |
| `ANTHROPIC_API_KEY`, `TICKETPILOT_REVIEWER_TOKEN` | **Unset**; no secrets are needed for the public demo |

Explicit Python pinning avoids Render's changing default; see [Render Python versions](https://render.com/docs/python-version). No `DENSE_MODEL` or reranker download is required. DEMO_MODE forces TF-IDF and disables reranking even if heavyweight optional packages or flags are present. The trained classifier is unchanged; historical retrieval benchmarks remain historical and do not claim to measure this hosted fallback.

## Public demo policy and storage

DEMO_MODE always uses `<system temp>/ticketpilot-public-demo/tickets.db`. It never opens the existing local database or honors an inherited `DB_PATH`. Render's isolated filesystem starts without any bundled local database. Existing fictional Nimbus order fixtures are seeded; operational tickets begin empty. No fabricated operational counts or latency are seeded. Visitor submissions are real pipeline runs on explicitly requested fictional examples.

The UI labels the demo as public/shared, requests fictional data only, and states that storage is ephemeral. It is not a private helpdesk: other visitors can see submissions. Do not enter real personal information, order data or credentials, including in feedback comments. Existing PII-pattern redaction is limited and is not an anonymity guarantee.

Public order mutations are forbidden at both the HTTP boundary and the cancellation tool. Paid LLM calls are disabled. Approvals, `approved:false` and corrected training labels return 403 in DEMO_MODE, **even with a matching reviewer token**. Ratings/comments remain available. Existing authenticated reviewer behavior outside DEMO_MODE is preserved.

For the Free instance, intake is serialized, limited globally to 10 tickets/minute and capped at 200 tickets; feedback is capped at 400 rows. List limits are bounded to 200 and request bodies to 32 KiB. Capacity is not reclaimed by deleting existing tickets; new writes return an explicit limit error when full. Render's normal filesystem reset starts a fresh demo. These controls are basic shared-demo resource limits, not tenant authentication or a full abuse-prevention system.

CORS accepts only exact configured origins. Wildcards, URL credentials and paths are rejected. Browser preflight allows GET/POST and Content-Type/Authorization, without cookies. Each preview URL must be explicitly listed if direct browser-to-Render calls are intended. The same-origin Vercel proxy works independently of that allowlist. **CORS is not authorization**; non-browser callers are still subject to server-side demo restrictions.

## Measured compatibility

| Check | Observed result |
| --- | --- |
| Existing model | 2.62 MiB; loads under pinned sklearn 1.9.1; no training |
| Clean frontend install | Node **22.23.4**, isolated `npm ci`: **485 packages installed successfully** |
| Frontend API server trace | **1.65 MiB**, no model, local DB or `.env` included |
| Linux x86-64 wheels | All pinned serving dependencies downloaded successfully as binary wheels for Python 3.13 |
| Clean serving venv | Install succeeded; `pip check` passed; about 216 MB installed on macOS |
| Linux serving dependencies | About **304 MiB** installed, plus about **3 MiB** application/model files |
| Linux test image | `linux/arm64`, **607,351,577 bytes** uncompressed; native Render does not use this image |
| Cold process at 512 MiB / 0.1 CPU, no swap/network | **20.796 s**, **123.22 MiB peak process RSS**, one real ticket **99.4 ms** |
| Heavy imports in that process | None of Torch, transformers, sentence-transformers, pandas or Anthropic |
| Backend HTTP smoke at those resource limits | **7 policy/processing checks passed**, no OOM |
| Full frontend + minimal-backend local smoke | **12 checks passed** against production Next.js build |

These are engineering measurements on a local constrained Linux container, not promised Render response times or saved portfolio evaluation metrics. The profile includes model/index initialization and one ticket; it is not an ASGI load test or peak traffic measurement. A separate HTTP smoke passed within the same container limit. Actual Render hosts, x86-64 architecture, shared CPU, memory accounting and cold-start infrastructure can differ; verify provider logs after an approved deployment. The minimal runtime reuses existing TF-IDF retrieval and lazily imports pandas only inside the original training/evaluation entrypoints. No local AI feature or trained artifact was removed.

`Dockerfile.render` is an optional reproducible lightweight validation image. The root Dockerfile retains the fuller local dashboard/optional-LLM requirements, copies the existing model, no longer trains during build, and uses the dynamic-port start script. Do not confuse the full local image with the native minimal Render build. No running local image/container was replaced.

## Expected free-tier limits and zero-cost rules

Render's Free web service currently provides **512 MB RAM / 0.1 CPU**. It sleeps after **15 minutes** without inbound traffic; waking usually takes about a minute. SQLite changes are lost on sleep, restart and redeployment; Free services do not support persistent disks. The workspace has **750 free instance hours/month**. Without a payment method, excess bandwidth/build usage causes suspension/build restrictions instead of paid overages. See [compute plans](https://render.com/docs/compute-plans) and [Free service limitations](https://render.com/docs/free).

Vercel Hobby is for **personal/non-commercial** use and has included-usage limits; the portfolio must stay within those limits. See [Hobby policy and limits](https://vercel.com/docs/plans/hobby). Use the included `vercel.app` and `onrender.com` domains. Do not buy a domain, add a persistent disk/database, enable paid integrations, add payment methods, start a Pro trial or upgrade plans. This configuration requires no credit card or paid credential. If a provider requests a card/payment verification during account setup, stop and treat that as an account-level blocker rather than adding one.

Cold starts can produce a temporary API-unavailable indicator and offline local drafts. The UI offers Retry backend connection and explains wake-up delay. The static Evaluation Lab is always independent of backend availability. No uptime or production reliability guarantee is made.

## Step-by-step deployment, only after owner approval

1. **Review the first-commit audit first.** Git is now initialized on `main`; the index and history remain empty. See [FIRST_COMMIT_AUDIT.md](FIRST_COMMIT_AUDIT.md) and the exact [COMMIT_FILES.txt](COMMIT_FILES.txt) manifest. Run `python scripts/audit_release.py --candidate` before staging. Review all pending changes and do not touch another project.
2. Run `python scripts/audit_release.py --working-tree`, snapshot freshness and all validation commands below. Ensure the trusted model, knowledge base, intent map, frontend lockfile and static snapshot will be tracked. Local `.db` files, `.env` secrets, training data, `.venv`, `node_modules`, `.next`, downloaded model caches and test output must not be tracked. Run `python scripts/audit_release.py --tracked` after staging the reviewed release and review history for secrets/private data. `.gitignore` does not remove files already tracked or present in old commits. Stop if either audit is blocked.
3. Only after push approval, publish the reviewed TicketPilot repository/branch to the intended personal Git account. No push was performed here. Do not regenerate/train the model or rerun evaluation just to publish.
4. Only after service/deployment approval, create a Render **Web Service → Python → Free**, repository root blank, using the build/start commands and environment table above. Alternatively apply the reviewed `render.yaml` Blueprint; select only its Free API service. Do not create a database/disk or pay for anything. Automatic deploys remain off.
5. For CORS before the Vercel domain is assigned, use the two exact localhost origins from `.env.example`; the frontend proxy does not depend on CORS. After the final Vercel URL is assigned, update `CORS_ORIGINS` to that exact HTTPS origin with approval. Do not use `*.vercel.app` or `*`.
6. Let the Render build/start complete. Inspect logs for the model checksum, sklearn 1.9.1 and `tfidf(word+char)`, then open `https://YOUR-API.onrender.com/health`. Wait through an initial cold start. Expect `status:ok`, `model_loaded:true`, `demo_mode:true`, `storage:ephemeral`, `llm:false`, `order_writes:false`, `approvals:false`. Stop if any capability/storage value is wrong.
7. Only after frontend deployment approval, create/import the Vercel project under personal Hobby, set **Root Directory = frontend**, select Node 22.x, and set server-only `TICKETPILOT_API_URL` to the Render HTTPS origin. Keep the default Next.js output. `frontend/vercel.json` disables Git-triggered automatic deployments; use an approved manual deployment/redeploy. Do not bypass that setting merely to make a push publish automatically. If using the CLI manually, run it from `frontend/`, never repository root.
8. After an approved frontend deployment, visit `/evaluation` first: it should show the bundled versioned snapshot without needing the API. Visit `/api/backend/health` and compare its demo/storage capabilities with Render's health response. Complete the approved exact-origin CORS update once the stable frontend domain is known.
9. Run the read-only remote smoke command below. To test ticket creation/privileged denial remotely, obtain explicit approval for those demo writes, then add `--allow-remote-writes`. The runner still refuses to write if the backend does not advertise DEMO_MODE plus ephemeral storage.
10. In the browser, verify Overview/Inbox/Analytics show actual demo records, submit a fictional request, inspect its captured evidence, and confirm approval remains disabled. Check the ephemeral/shared-data banner, mobile layout, cold-start Retry flow and static Evaluation Lab. Review free-usage dashboards; do not configure periodic external keepalives.

## Verification commands

Local checks, from repository root (use Node 22 and the existing local development venv):

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m pytest -q
.venv/bin/python -m src.evaluation_snapshot --check
.venv/bin/python scripts/audit_release.py --working-tree
cd frontend
npm run lint
npm run typecheck
npm run build
npm run test:e2e
cd ..
.venv/bin/python scripts/deployment_smoke.py --local
```

The local smoke runner starts disposable servers on temporary ports with an isolated demo database, fake test-only reviewer credential and explicitly permitted local origin. It stops them afterward. It does not contact Render/Vercel or use the normal database. Run it with the clean serving venv's Python to verify no hidden development dependency is required. Browser tests use their existing disposable ports 8011/3011.

Fresh native serving environment (writes only to a new temporary venv):

```sh
python3.13 -m venv /tmp/ticketpilot-serving-check
/tmp/ticketpilot-serving-check/bin/python -m pip install --no-cache-dir -r requirements-render.txt
DEMO_MODE=1 RETRIEVAL_BACKEND=tfidf /tmp/ticketpilot-serving-check/bin/python scripts/check_runtime.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/ticketpilot-serving-check/bin/python scripts/profile_runtime.py
/tmp/ticketpilot-serving-check/bin/python scripts/deployment_smoke.py --local
```

Optional local resource check (creates a separate temporary test image/container, not a deployment):

```sh
docker build -f Dockerfile.render -t ticketpilot-render-check .
docker run --rm --memory=512m --memory-swap=512m --cpus=0.1 --network=none ticketpilot-render-check python scripts/profile_runtime.py
docker run --rm --memory=512m --memory-swap=512m --cpus=0.1 --network=none ticketpilot-render-check python scripts/deployment_smoke.py --local --backend-only
```

After approved cloud deployment, read-only endpoint/configuration checks:

```sh
python scripts/deployment_smoke.py --backend-url https://YOUR-API.onrender.com --frontend-url https://YOUR-PROJECT.vercel.app
```

After separate approval for fictional demo writes, use the same command with `--allow-remote-writes`. The full smoke checks readiness, model/retrieval mode, ephemeral policy, explicit CORS allow/deny, proxy connectivity/allowlist, static snapshot loading, missing/insecure Vercel upstream rejection (local mode), body-size limits, real ticket processing/persisted evidence, approval/correction denial even with a supplied token, paid LLM denial and blocked cancellation. POSTs are not retried automatically.

## Final results and remaining blockers

| Required validation | Final observed result |
| --- | --- |
| `pytest -q` via existing venv | **63 passed** (45 existing + 18 deployment tests) |
| `npm run lint` | **Passed**, Node 22 |
| `npm run typecheck` | **Passed**, Node 22 |
| `npm run build` | **Passed**, static evaluation page retained |
| `npm run test:e2e` | **14 passed** |
| Full local deployment smoke, clean serving environment | **12 checks passed** |
| Constrained Linux backend HTTP smoke | **7 checks passed** at 512 MiB / 0.1 CPU |
| Snapshot freshness / model & original report hashes | **Unchanged / passed** |
| Serving dependency consistency | **`pip check` passed** |
| Candidate source/credential scan | **Passed**; no matched credential patterns |
| Git audit status | **Candidate audit passes; main initialized, index intentionally empty. Run `--tracked` after reviewed staging.** |

Deployment tests additionally cover exact-origin validation, readiness before warmup, demo/private-DB isolation, real and direct-tool cancellation denial, supplied reviewer credentials, paid SDK disablement, limits, body-size rejection, and remote-smoke read-only guards. All remote smoke POSTs require explicit write approval; default remote probes use GET/OPTIONS only.

The clean frontend install emitted an ESLint 9.39.5 version-support deprecation notice. Lint passes; a separate major-version maintenance change was intentionally not mixed into deployment preparation. No vulnerability-free claim is made from these tests.

Git metadata is now initialized and the candidate audit passes. Publication still requires reviewed staging/commit, an audit of that staged set, assigned cloud URLs/exact CORS origin, verified provider account eligibility and explicit deployment/push approval. No remote performance/health result can be claimed before an approved deployment.

Shared anonymous storage, basic global limits and limited PII redaction are suitable only for fictional portfolio examples. A visitor can fill the shared quota; no user identity, tenant isolation, persistent data, guaranteed uptime or production abuse protection is provided. There is no privileged order-execution workflow or outbound customer messaging. Pinned runtime/dependency versions need maintenance and revalidation with the preserved model.

## Exact files changed for deployment preparation

| Area | Files |
| --- | --- |
| Root configuration | `.gitignore` (new), `.dockerignore`, `.env.example` (new), `.python-version` (new), `render.yaml` (new), `requirements-render.txt` (new) |
| Docker | `Dockerfile`, `Dockerfile.render` (new) |
| Backend | `src/config.py`, `src/api.py`, `src/deployment.py` (new), `src/classifier.py`, `src/retrieval.py`, `src/llm.py`, `src/tools.py`, `src/store.py` |
| Validation/start scripts | `scripts/check_runtime.py`, `scripts/start_render.sh`, `scripts/profile_runtime.py`, `scripts/deployment_smoke.py`, `scripts/audit_release.py` (all new) |
| Tests | `tests/test_deployment.py` (new) |
| Frontend configuration | `frontend/package.json`, `frontend/package-lock.json`, `frontend/vercel.json` (new), `frontend/.nvmrc` (new), `frontend/.env.example` |
| Frontend behavior | `frontend/src/app/api/backend/[...path]/route.ts`, `frontend/src/lib/types.ts`, `frontend/src/components/shell.tsx`, `frontend/src/components/new-ticket.tsx` |
| Documentation | `README.md`, `frontend/README.md`, `docs/DEPLOYMENT.md` (new) |

This records the 34 files changed during deployment preparation, when Git metadata was absent. Git was subsequently initialized during first-commit preparation; see FIRST_COMMIT_AUDIT.md for the current candidate inventory. No model, original report, snapshot, original ticket/order data, PayLens file or unrelated repository was modified.
