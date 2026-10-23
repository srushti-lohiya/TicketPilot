"""Step 0: all paths and settings in one place (override any of them with env vars)."""
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
KB_DIR = ROOT / "kb"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"
DEMO_MODE = os.getenv("DEMO_MODE", "0").lower() in {"1", "true", "yes"}
# Public serving never opens the local/private database, even if DB_PATH is accidentally inherited.
DB_PATH = (Path(tempfile.gettempdir()) / "ticketpilot-public-demo" / "tickets.db" if DEMO_MODE
           else Path(os.getenv("DB_PATH", ROOT / "data" / "supportpilot.db")))
DEMO_MAX_TICKETS = 200
DEMO_MAX_FEEDBACK = 400

DATASET_ZIP = ("https://codeload.github.com/bitext/"
               "customer-support-llm-chatbot-training-dataset/zip/refs/heads/main")
RAW_CSV = DATA_RAW / "bitext_support.csv"
RANDOM_STATE = 42

# Routing policy (the confidence threshold is learned in step 2 and saved with the classifier)
AGENT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "6"))

# LLM (optional). Without ANTHROPIC_API_KEY a deterministic fallback agent is used.
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "claude-haiku-5-5")

for d in (DATA_RAW, DATA_PROCESSED, MODELS_DIR, REPORTS_DIR, DB_PATH.parent):
    d.mkdir(parents=True, exist_ok=True)
