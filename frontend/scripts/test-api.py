"""Disposable, key-free FastAPI instance for real frontend integration tests."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.pop("ANTHROPIC_API_KEY", None)
# Exercise the free base-requirements path, without downloading embedding models.
sys.modules["sentence_transformers"] = None

import uvicorn

with tempfile.TemporaryDirectory(prefix="ticketpilot-browser-tests-") as folder:
    os.environ["DB_PATH"] = str(Path(folder) / "test.db")
    uvicorn.run("src.api:app", host="127.0.0.1", port=8011, log_level="warning")
