"""Thin Anthropic client wrapper. Everything works without a key (deterministic fallbacks)."""
import os
from functools import lru_cache
from src.config import DEMO_MODE


def llm_available() -> bool:
    return not DEMO_MODE and bool(os.getenv("ANTHROPIC_API_KEY"))


@lru_cache
def client():
    if DEMO_MODE:
        raise RuntimeError("Paid LLM clients are disabled in DEMO_MODE")
    import anthropic
    return anthropic.Anthropic()   # reads ANTHROPIC_API_KEY
