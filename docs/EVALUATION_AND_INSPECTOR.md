# Evaluation Lab and AI decision inspector

Implemented and verified 2026-10-24. The existing light design, component library, sidebar, indigo charts and responsive layout are retained. No paid APIs, new frameworks, training or services were added.

## What was already working

The Evaluation Lab already read classifier, fallback-pipeline and retrieval summaries with source labels and charts. Ticket Detail already showed the stored intent/confidence, priority, routing reasons, risk flags, citation IDs, tool payloads, draft, status, latency and feedback controls. Those features were retained.

The missing functionality was a portable versioned snapshot; classifier baseline/sample/per-intent comparisons; an honest confusion matrix; field-level missing measurements; reproducible source hashes; and captured retrieval/check metadata for the inspector.

## Implemented

- `src/evaluation_snapshot.py` reads saved artifacts using only the Python standard library and generates `frontend/src/data/evaluation.v1.json`. It performs no inference, training, database access or evaluation. `--check` compares normalized content and input hashes, ignoring checkout-dependent modification times.
- `/evaluation` now statically bundles that snapshot. It works independently of FastAPI and runtime report mounts. Snapshot generation time, artifact modification times and unknown historical run time are distinguished.
- Classifier cards/charts/tables show the measured benchmark/realistic gap, majority baseline comparison, macro F1, sample sizes, calibration error, confidence threshold, threshold-only coverage and accepted-intent accuracy. The dataset explanation explicitly distinguishes templated Bitext from small handwritten held-out cases.
- The per-intent report exposes all 27 recorded precision/recall/F1/support rows.
- The full 27×27 confusion matrix and most-confused pairs are computed from the recorded pipeline CSV's 54 in-scope predictions, excluding out-of-scope rows. Axes, counts, scope and development/test inclusion are labeled. The matrix is not presented as a Bitext benchmark matrix or the held-out 27-case classifier result.
- Retrieval comparisons show only the eight recorded configurations, with recall@3, MRR within the first 10 returned results, dataset and sample counts. No unrecorded reranking bar or improvement is inferred.
- Pipeline safety/grounding, routing counts, escalation share, latency and tokens use saved summary measurements and recorded prediction denominators. Missing values are null and render **Not measured**; zero remains a valid measurement.
- New processed tickets persist versioned `decision_metadata`: classifier top-three candidates and threshold/gate outcome; initial retrieval IDs, text, titles, ranks and scores; runtime retrieval encoder/reranker state; input check outcomes; and actual output-check state/issues. No prompts, hidden reasoning or chain-of-thought are recorded.
- The inspector shows captured policy sections with cited/uncited labels, observable checks, human-readable tool outcomes, existing inputs/outputs, final draft/acknowledgement, status and processing latency. It distinguishes passed, failed and not-run guardrails. Scores are described as ranking values, with RRF versus reranker semantics handled separately.
- A backward-compatible SQLite migration adds one nullable JSON column. Older tickets retain their citation IDs and show **Not recorded** for unavailable historical evidence. Reads never rerun the model or retrieval to reconstruct old evidence. Offline drafts remain explicitly unprocessed.

## Actual metric sources

| Source artifact | Measurements displayed | Scope / denominator |
| --- | --- | --- |
| `reports/classifier_report.json` | Bitext accuracy **99.8902%**, macro F1 **0.998904**, majority baseline accuracy **4.1186%**, category/noisy-text accuracy, ECE **0.012935** | Bitext benchmark test; sample count comes from the per-intent report |
| `reports/classifier_report.json` | Realistic in-scope accuracy **66.6667%**, threshold **0.87**, threshold-only in-scope coverage **29.6296%**, accepted-intent accuracy **100%** | Held-out realistic classifier split: **33 total**, including **27 in-scope / 6 out-of-scope** |
| `reports/classifier_per_intent.txt` | Per-intent precision, recall, F1, support; benchmark **3,642** samples | 27 intent classes; precision/recall/F1 were rounded to three decimals by the original evaluator; supports must match aggregate report support |
| `eval/realistic_tickets.csv` | In-scope/out-of-scope classifier test sample counts | Derived only when test-split size matches the classifier report's recorded total |
| `reports/retrieval_eval.csv` | Recall@3 and MRR@10 for **BM25, dense, hybrid, hybrid+intent** | Four methods on **54** realistic in-scope queries and four on a **540**-query Bitext sample |
| `reports/e2e_fallback.json` | Auto precision **100%**, in-scope auto coverage **18.5185%**, output guardrail pass **94.9153%**, grounded citation rate **68.6275%**, OOS held from auto **100%** | Historical deterministic pipeline evaluation: **66** total tickets, development + test included |
| `reports/e2e_fallback.json` | Processing p50 **13.95 ms**, p95 **153.15 ms**, mean tokens **0**; rounded routing shares | Offline run, not current operational latency or customer wait time |
| `reports/e2e_fallback.csv` | Confusion counts; exact routing **49 review / 10 auto-resolved / 7 escalated**; safety denominators | **37/54** in-scope intents correct; auto precision **10/10**; guardrail pass **56/59** non-escalated replies; grounding **35/51** in-scope non-escalated replies; OOS held **12/12** |

All six source files have SHA-256 entries in the snapshot. The model artifact hash recorded during generation identifies the model present at generation time; it is explicitly **not** claimed as the historical model-run identity.

The saved retrieval mode `dense` does not identify its encoder. The implementation supports a sentence-transformer encoder and a word/character TF-IDF fallback. The snapshot does not infer which produced the historical CSV. Similarly, no separately identified reranking result exists. The evaluation code bounds reciprocal-rank calculation to the first 10 results; the original CSV column is named `mrr`.

## Remaining measurement limits

- Realistic held-out macro F1, majority-baseline macro F1, additional trained classifier comparisons and the original Bitext confusion counts are **Not measured** in the artifacts. Rounded per-intent summaries cannot reconstruct a confusion matrix.
- Retrieval encoder/reranker identity, original model/data version manifest, verified evaluation run timestamp, hardware/warmup protocol, human helpfulness scores, paid-model judge scores, production validation and confidence intervals were not recorded.
- The realistic dataset is small and fictional. Pipeline/retrieval results include development examples. Results are historical and were not rerun after public-demo authorization policy changes; they do not establish current HTTP authorization behavior.
- Guardrail pass excludes escalated acknowledgements. Citation overlap is a proxy for grounding, not proof of every answer claim. OOS “held from auto” includes review drafts as well as escalation.
- Historical tickets lack the new retrieval/check capture. New metadata includes initial retrieval; additional LLM search evidence, if present, stays in recorded tool results. Per-tool timestamps and durations were not recorded and are not fabricated.
- The snapshot must be explicitly regenerated and the frontend rebuilt after report changes. The old `TICKETPILOT_REPORTS_DIR` runtime setting is replaced by the generator's `--reports-dir` option.

## Final test results

| Check | Final result |
| --- | --- |
| Backend pytest | **45 passed** (23 existing + 22 new) |
| Frontend lint | **Passed** |
| Frontend typecheck | **Passed** |
| Frontend production build | **Passed**, including statically prerendered `/evaluation` |
| Existing + new Playwright E2E | **14 passed** (10 existing + 4 new) |
| Snapshot freshness | **Matches source artifacts** |
| Desktop/mobile review | Screenshots inspected; no overflow or browser errors in E2E |
| Live localhost verification | Evaluation page returns 200; sample ticket 5 has three captured sections, persisted candidates/checks and denied public approval |

Parser tests cover missing/corrupt independent reports, absent/invalid/non-finite/boolean rates, real zeroes, missing CSV metrics, duplicate retrieval configurations, mismatched sample counts, incomplete per-intent support, inconsistent prediction flags, confusion counts, denominators and snapshot content equality. Inspector tests cover metadata persistence, no retrieval on ticket reads, explicit skipped/failed checks, PII redaction and idempotent migration preserving legacy records. Browser tests cover snapshot rendering without API access, real values/missing metrics, matrix totals, section expansion, tool outcomes, legacy records, blocked cancellation, escalation and responsive layouts.

The first expanded E2E run exposed a selector matching both classifier provenance footers; its assertion was scoped. The final complete suite passes against the final build.

## Running local services and preservation

The existing API Docker image was updated with a source-only layer containing `src/store.py` and `src/pipeline.py`. It retains its installed dependencies and trained model; no full Docker build or retraining was used. The previous image is tagged `ticketpilot-api:before-evaluation-20261024`. The source-only recipe is `/tmp/ticketpilot-evaluation-api.Dockerfile`. Only the API service was recreated with `docker compose up -d --no-build --no-deps api`; the dashboard was left alone.

A SQLite backup was saved in the existing volume at `/data/ticketpilot-before-evaluation-20261024.db` before migration. All **four original tickets** and all order records were compared with the backup and are unchanged. One sample ticket was intentionally added for browser verification: **ticket 5**. The original five evaluation artifacts and local model were checksum-verified unchanged; deployed model SHA-256 is also unchanged:

```text
Local model:    8864285d5b3130ec92f21fcaf5b174e6a06e7b20416bfa86165464c567ab8ee0
Deployed model: 7f20bb507d3c8e430a4adc55b7f5bdeb5c3558ec216352a4e667a4b3348fd98e
```

These identify the pre-existing local/container artifacts respectively, not verified historical evaluation provenance. Retrieval implementation, evaluation scripts that execute inference, trained weights and existing approval restrictions were preserved. No PayLens or unrelated project was accessed or modified. No verification blockers remain.

## Browser verification

1. Open **http://localhost:3000/evaluation**. Check benchmark vs realistic metrics, the majority baseline, eight retrieval rows, safety denominators, routing and offline latency.
2. Expand **Full confusion matrix (27 × 27)** and **Inspect 27 intent classes**. Expand source hashes to inspect artifact provenance. Realistic held-out macro F1 and reranking should explicitly say **Not measured**.
3. Open **http://localhost:3000/tickets/5**. Inspect **Decision checks**, the captured retrieval sections, cited/uncited labels, order lookup outcome, routing/review status and latency. Expand a policy section to read exactly what was captured.
4. Open **http://localhost:3000/new**, submit a free deterministic request and open its full ticket. Older tickets such as `/tickets/1` should show **Not recorded** for historical evidence instead of reconstructed scores/text.
5. The Evaluation Lab remains available when the API is unreachable because its snapshot is bundled independently. Browser tests exercise that state without stopping the user's running service.

## Reproduce checks

From the repository root:

```sh
.venv/bin/python -m src.evaluation_snapshot --check
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m pytest -q
cd frontend
npm run lint
npm run typecheck
npm run build
npm run test:e2e
```

To intentionally refresh the snapshot from current saved reports:

```sh
.venv/bin/python -m src.evaluation_snapshot
# Optional: --reports-dir /path/to/reports --output /path/to/snapshot.json
```

Run generation from the repository root, then rebuild the frontend. Test servers use free ports 8011/3011, existing model artifacts and temporary databases. Do not run the existing training/evaluation commands against the normal DB just to refresh the snapshot; they are not necessary.

## Files changed in this task

- `src/evaluation_snapshot.py` (new)
- `src/pipeline.py`
- `src/store.py`
- `tests/test_evaluation_snapshot.py` (new)
- `tests/test_decision_metadata.py` (new)
- `frontend/src/data/evaluation.v1.json` (new)
- `frontend/src/lib/evaluation.ts`
- `frontend/src/lib/evaluation-types.ts`
- `frontend/src/lib/types.ts`
- `frontend/src/components/evaluation.tsx`
- `frontend/src/components/evaluation-diagnostics.tsx` (new)
- `frontend/src/components/decision-inspector.tsx` (new)
- `frontend/src/components/ticket-detail.tsx`
- `frontend/src/app/evaluation/page.tsx`
- `frontend/tests/evaluation-inspector.spec.ts` (new)
- `frontend/tests/workspace.spec.ts`
- `frontend/.env.example`
- `frontend/README.md`
- `docs/EVALUATION_AND_INSPECTOR.md` (new)

The checkout has no `.git` metadata, so this is the intentional file inventory rather than a Git diff.
