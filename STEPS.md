# SupportPilot — step by step

Run each step, check the output, commit (`git add . && git commit -m "step N"`).

## Step 0 — Setup
```bash
unzip SupportPilot.zip && cd SupportPilot
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
`src/config.py` holds every setting.

## Step 1 — Data  (`src/data.py`)
```bash
python -m src.data
```
Downloads Bitext (~27K tickets, 27 intents), turns `{{Order Number}}` into `<order_number>`,
removes 2,598 duplicates **before** splitting, then makes train/val/test (17K / 3.6K / 3.6K).

## Step 2 — Intent classifier  (`src/classifier.py`)
```bash
python -m src.classifier
```
TF-IDF (words + character n-grams, so typos still work) → logistic regression.
You'll see two very different numbers — this is the main story of the project:
* Bitext test accuracy ≈ 0.999 (templated data, too easy)
* Realistic tickets (`eval/realistic_tickets.csv`) ≈ 0.67
Then it picks `auto_threshold` (≈0.87) using a cost function, and shows that above it
auto answers are 100% correct and every out-of-scope ticket is held back.
**Your task:** add 20+ more realistic tickets to the CSV (half `dev`, half `test`) and re-run.

## Step 3 — Knowledge base + hybrid RAG  (`kb/*.md`, `src/retrieval.py`)
```bash
python -m src.retrieval eval
python -m src.retrieval "my refund hasn't arrived"
```
Compares BM25, dense, hybrid (RRF) and hybrid + intent routing (≈0.85 recall@3).
Upgrade: `pip install sentence-transformers`, re-run, and add the new row to your README.
Then try `USE_RERANKER=1 python -m src.retrieval eval` (cross-encoder reranking).

## Step 4 — Guardrails  (`src/guardrails.py`)
PII redaction (email, phone, Luhn-checked cards, SSN), prompt-injection detection,
reply checks (must cite a retrieved section; no refunds/discounts/guarantees promised).

## Step 5 — Risk & priority  (`src/risk.py`)
Transparent rules → P1–P4 with reasons (legal, fraud, safety, anger, repeat contact, urgency).

## Step 6 — Tools + agent  (`src/store.py`, `src/tools.py`, `src/agent.py`)
Mock order DB (orders 10233, 10345, 10432, 10561, 10877, 10992, 11001).
`LLMAgent` runs a Claude tool-use loop; `FallbackAgent` does the same job with rules.
```bash
export ANTHROPIC_API_KEY=sk-ant-...      # optional
```

## Step 7 — Orchestrator  (`src/pipeline.py`)
```bash
python -c "from src import store; store.init_db(); from src.pipeline import handle_ticket; print(handle_ticket('pls cancel my order 10877'))"
```

## Step 8 — End-to-end evaluation  (`src/evaluate.py`)
```bash
python -m src.evaluate          # offline
python -m src.evaluate --llm    # Claude agent + LLM-as-judge
```
Put both result tables side by side in the README: that comparison shows what the LLM adds
(more auto-resolves, better drafts) and what it costs (latency, tokens).

## Step 9 — API  (`src/api.py`)
```bash
uvicorn src.api:app --reload      # http://127.0.0.1:8000/docs
curl -X POST localhost:8000/tickets -H "Content-Type: application/json" -d '{"text":"where is order 10233"}'
```
Endpoints: `POST /tickets`, `GET /tickets?status=`, `GET /tickets/{id}`,
`POST /tickets/{id}/feedback`, `GET /metrics`, `GET /intents`, `GET /health`.

## Step 10 — Dashboard  (`dashboard.py`)
```bash
streamlit run dashboard.py
```
Tabs: new ticket · review queue (approve, rate, correct the intent) · metrics.

## Step 11 — Feedback loop
Correct some intents in the review queue, then `python -m src.classifier` —
it prints `adding N human-corrected tickets from feedback`.

## Step 12 — Tests, Docker, CI
```bash
pytest -q                         # 11 passed (includes a fake-LLM test of the tool loop)
docker compose up --build         # API :8000, dashboard :8501, tickets kept in a volume
```
Push to GitHub: `.github/workflows/ci.yml` trains, evaluates and tests on every push and
uploads `reports/` as an artifact.

## Step 13 — Polish for recruiters
README with: demo GIF of the dashboard, the "99.9% vs 67%" finding, the threshold table,
the retrieval table, offline-vs-LLM end-to-end comparison, architecture, limitations.

## Next upgrades
* LLM zero-shot intent classifier for low-confidence tickets; compare on the realistic set
* Qdrant/pgvector service in docker-compose for the KB
* Langfuse/OpenTelemetry tracing of every agent step
* Fine-tune a small transformer (DistilBERT) on Bitext + feedback and compare
