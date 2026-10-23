# First GitHub commit preparation

Audit date: 2026-10-24. Scope: TicketPilot only.

## Repository state

The initial inspection confirmed there was **no `.git` directory** and `git status` failed because the project was not initialized. Ran `git init --initial-branch=main` in this project. The current unborn branch is **main**. There are no commits, configured remotes, staged files or pushes. Global Git configuration and author identity were not changed. No project file, local database, training data or cache was deleted. No remote repository was created and no history was rewritten.

## Exact files approved by this audit

[COMMIT_FILES.txt](COMMIT_FILES.txt) lists every audited, non-ignored project path, including this report and the manifest itself. The manifest is an explicit first-commit inventory, not a wildcard recommendation to publish everything on disk. It includes:

- Frontend source, component library, tests, configuration, lockfile and safe environment example.
- Backend/pipeline source, serving requirements, local development requirements, tests and startup/audit scripts.
- Dockerfiles, Compose configuration, Render Blueprint, Vercel configuration and deployment documentation.
- All ten knowledge-base Markdown files, the intent-to-policy map and reviewed fictional evaluation fixtures.
- The real trained model, evaluation reports and bundled versioned snapshot required for deployment.
- Safe root/Streamlit configuration and empty data/model/report placeholders.

All listed files are ready for review and staging; this task intentionally leaves the index empty. No actual environment values, runtime database, training CSV, log, generated test result, virtual environment or dependency/build cache is included.

## Secret and customer-data review

Inventoried all project-owned files, including ignored local data. Classified third-party dependencies, build/test output, bytecode caches and Git metadata separately; their contents are not proposed for publication. Provider-key patterns covered AWS, OpenAI/Anthropic, GitHub, Google, Slack and Stripe formats, plus private-key headers, JWT-shaped tokens, credential URLs, secret-like assignments, email/SSN patterns and local identity paths. Findings were reported without printing credential or customer values.

**No live credentials or private customer records were identified in the commit candidates.** Matches in the candidate set were reviewed as intentional test fixtures: fixed test-only reviewer tokens, example addresses used to test PII redaction, a credential-bearing dummy URL used to test CORS rejection, and standard synthetic phone/card values. These test values grant no access to a real service. Both `.env.example` files contain safe defaults/placeholders only; no real `.env` file was found among project-owned source files.

The retained `eval/realistic_tickets.csv` has 66 fictional examples. All 66 text fields in `reports/e2e_fallback.csv` match that reviewed fixture corpus exactly. Synthetic order numbers and the example street-address sentence are evaluation fixtures, not exports of runtime customers. Snapshot/report data and model bytes were not changed to make this audit pass.

The local SQLite runtime database contains ticket, feedback and order records and is excluded regardless of their apparent contents. It was inspected read-only for table/row-count classification; no record values were published, exported or modified. Raw/processed training CSVs contain email-shaped strings and are excluded in their entirety. They remain on disk for local workflows.

## Ignore rules and verified exclusions

Improved root `.gitignore` for Python bytecode/tool caches, venvs, package/build output, Next.js output, `node_modules`, test/coverage results, OS/editor files, logs/profiles, environment files, credential stores/private-key formats, SQLite DBs/WAL/journals/backups and local raw/processed training data. Environment examples and required real model/report/snapshot assets remain eligible for normal Git.

`git check-ignore -v --no-index` verifies actual and representative sensitive/generated paths, including:

```text
.env
.env.local
frontend/.env.local
.streamlit/secrets.toml
.aws/credentials
.ssh/id_rsa
frontend/.npmrc
data/supportpilot.db
data/supportpilot.db-wal
backup/tickets.sqlite3.backup
data/raw/bitext_support.csv
data/processed/train.csv
.venv/pyvenv.cfg
frontend/node_modules/next/package.json
frontend/.next/BUILD_ID
frontend/tsconfig.tsbuildinfo
.pytest_cache/README.md
frontend/test-results/.last-run.json
logs/server.log
```

A separate negative check confirms the trained model, snapshot, reports, environment examples, knowledge base, Dockerfiles, Render/Vercel files and source/test files are **not ignored**. `git status --ignored` shows generated/private local data as ignored while the manifest's files remain untracked. No file was force-added to bypass ignores.

## Model and GitHub size limits

- `models/intent_clf.joblib`: **2,751,409 bytes (2.624 MiB)**, unchanged SHA-256 `8864285d5b3130ec92f21fcaf5b174e6a06e7b20416bfa86165464c567ab8ee0`.
- `frontend/src/data/evaluation.v1.json`: **21,932 bytes**, preserved with its recorded artifact hashes.
- The classifier is the largest commit candidate. No candidate exceeds 50 MiB or GitHub's regular Git 100 MiB limit. Git LFS is unnecessary; the actual joblib stays available to Render instead of becoming an unresolved LFS pointer.

GitHub documents its size limits in [About large files](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github). Git attributes for the model have no configured clean/filter or text conversion. The committed artifact can therefore remain the original binary. The size check covers every actual Git candidate, not merely the model directory.

## Verification and remaining limits

- Actual `git status`, `git ls-files --cached --others --exclude-standard`, `git check-ignore`, branch and remote checks completed.
- `scripts/audit_release.py --candidate` audits the actual Git publish set before staging, enforces required assets, blocks sensitive/generated paths, checks provider-shaped secrets and GitHub size thresholds. `--tracked` remains available for the eventual staged set.
- Snapshot freshness and the original model/evaluation input hashes pass. Release-policy tests verify sensitive paths stay out and serving/deployment assets stay in.

| Final check | Result |
| --- | --- |
| Exact manifest | **132 files**, matches actual non-ignored Git candidate paths |
| File sizes | Every candidate below **50 MiB**; largest is the **2,751,409-byte** model |
| Ignore checks | **19** actual/representative sensitive/generated paths excluded |
| Required-asset checks | **12** serving/deployment paths explicitly verified eligible |
| Candidate credential/path audit | **Passed** for all 132 candidates |
| Snapshot freshness and original artifact hashes | **Passed / unchanged** |
| Backend and audit-policy tests | **101 passed** (63 existing + 38 release-policy checks) |
| Branch / commits / remotes / staged files | **main / 0 / 0 / 0** |

First-commit preparation changed only `.gitignore`, `scripts/audit_release.py`, `docs/DEPLOYMENT.md`, and the new `tests/test_release_audit.py`, `docs/FIRST_COMMIT_AUDIT.md`, `docs/COMMIT_FILES.txt`, plus local `.git` metadata. The deployment guide now points to the initialized repository/current audit instead of claiming Git metadata is still absent.

Pattern scanning cannot prove the absence of every possible credential format or private detail. Review the manifest/diff again before the first commit, and audit newly created files before adding them. Third-party dependency/build caches were classified and excluded, not certified as source. Ignored databases and training data still exist locally and should be protected in machine backups. No existing Git history needs cleaning because this is an empty repository.

Before committing, review the public author name/email you want attached to the commit; this task did not infer or configure personal identity. GitHub repository creation, remote configuration, commits and pushes remain separate user actions. The existing restrictions on remote deployment/publishing remain in force.

## Safe local follow-up commands

```sh
git status --short --untracked-files=all
.venv/bin/python scripts/audit_release.py --candidate
.venv/bin/python -m src.evaluation_snapshot --check
```

After reviewing the exact manifest, optional local staging (not executed by this task):

```sh
git --literal-pathspecs add --pathspec-from-file=docs/COMMIT_FILES.txt
.venv/bin/python scripts/audit_release.py --tracked
git diff --cached --stat
```

`--literal-pathspecs` preserves bracketed Next.js paths such as `[id]` exactly. No commit or push command was run or is included in this preparation step.
