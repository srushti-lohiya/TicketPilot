"""Measure a cold demo startup + one real ticket in an isolated temporary DB (no network)."""
import json
import os
import resource
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

with tempfile.TemporaryDirectory(prefix='ticketpilot-profile-') as folder:
    os.environ.update(DEMO_MODE='1', RETRIEVAL_BACKEND='tfidf', TMPDIR=folder,
                      HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    tempfile.tempdir = None
    started = time.perf_counter()
    from src import store
    from src.pipeline import classifier, handle_ticket
    from src.retrieval import get_retriever
    store.init_db(); classifier(); get_retriever()
    startup = time.perf_counter() - started
    ticket = handle_ticket('Where is my order 10233?', use_llm=False)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mb = peak / (1024 * 1024 if sys.platform == 'darwin' else 1024)
    forbidden = [name for name in ('torch', 'transformers', 'sentence_transformers', 'pandas', 'anthropic') if name in sys.modules]
    assert not forbidden, forbidden
    result = {'platform': sys.platform, 'python': sys.version.split()[0],
              'cold_startup_seconds': round(startup, 3), 'peak_rss_mib': round(peak_mb, 2),
              'ticket_latency_ms': ticket['latency_ms'], 'retrieval': get_retriever().dense.kind,
              'heavy_imports': forbidden}
    print(json.dumps(result, indent=2))
    if peak_mb >= 450:
        raise SystemExit('Insufficient memory headroom for a 512 MB free service')
