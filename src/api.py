"""Step 9: REST API.  Run: uvicorn src.api:app --reload  ->  http://127.0.0.1:8000/docs"""
from contextlib import asynccontextmanager
from typing import Literal, Optional
import os
import secrets
import time
from collections import deque
from threading import Lock
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src import store
from src.config import DEMO_MODE, DEMO_MAX_TICKETS
from src.deployment import permitted_origins, DemoBodyLimit
from src.tools import order_writes_allowed
from src.pipeline import handle_ticket, classifier
from src.retrieval import get_retriever
from src.llm import llm_available


@asynccontextmanager
async def lifespan(app):
    app.state.ready = False
    store.init_db(); classifier(); get_retriever()     # load existing model, never train
    app.state.ready = True
    try:
        yield
    finally:
        app.state.ready = False

app = FastAPI(title="TicketPilot", version="1.0", lifespan=lifespan)
app.add_middleware(DemoBodyLimit, enabled=lambda: DEMO_MODE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=permitted_origins(os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")),
    allow_credentials=False, allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
_demo_processing = Lock()
_demo_requests = deque()



class TicketIn(BaseModel):
    text: str = Field(..., min_length=3, max_length=5000,
                      examples=["Where is my order 10233? It's been 10 days."])
    use_llm: Optional[bool] = None


class FeedbackIn(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    approved: Optional[bool] = None
    corrected_intent: Optional[str] = None
    comment: Optional[str] = Field(None, max_length=2000)


@app.get("/health")
def health():
    if not getattr(app.state, "ready", False):
        raise HTTPException(503, "Model and retrieval startup is not complete")
    with store.conn() as c:
        c.execute("SELECT id FROM tickets LIMIT 1").fetchone()
    return {"status": "ok", "llm": llm_available(), "mode": "public_demo",
            "order_writes": False, "approvals": False, "demo_mode": DEMO_MODE,
            "storage": "ephemeral" if DEMO_MODE else "local",
            "data_policy": "Fictional requests only; submissions are public" if DEMO_MODE else "Local mock workspace",
            "retrieval_backend": get_retriever().dense.kind, "model_loaded": True}


@app.post("/tickets")
def create_ticket(t: TicketIn):
    if t.use_llm:
        raise HTTPException(403, "Paid LLM processing is disabled in public demo mode")
    acquired = False
    if DEMO_MODE:
        acquired = _demo_processing.acquire(blocking=False)
        if not acquired:
            raise HTTPException(429, "Demo is processing another request; retry shortly", headers={"Retry-After": "5"})
    token = order_writes_allowed.set(False)
    try:
        if DEMO_MODE:
            now = time.monotonic()
            while _demo_requests and now - _demo_requests[0] >= 60:
                _demo_requests.popleft()
            if len(_demo_requests) >= 10:
                raise HTTPException(429, "Shared demo intake limit: 10 tickets per minute", headers={"Retry-After": "60"})
            with store.conn() as c:
                if c.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] >= DEMO_MAX_TICKETS:
                    raise HTTPException(429, "Ephemeral demo is full; try after the service resets")
            _demo_requests.append(now)
        return handle_ticket(t.text, use_llm=False)
    finally:
        order_writes_allowed.reset(token)
        if acquired:
            _demo_processing.release()


@app.get("/tickets")
def tickets(status: Optional[Literal["auto_resolved", "needs_review", "escalated", "resolved"]] = None, limit: int = Query(100, ge=1, le=200)):
    return store.list_tickets(status, limit)


@app.get("/tickets/{tid}")
def ticket(tid: int):
    t = store.get_ticket(tid)
    if not t:
        raise HTTPException(404, "ticket not found")
    return t


@app.post("/tickets/{tid}/feedback")
def feedback(tid: int, f: FeedbackIn, authorization: Optional[str] = Header(None)):
    if f.approved is not None or f.corrected_intent is not None:
        if DEMO_MODE:
            raise HTTPException(403, "Approvals and training-label corrections are disabled in public DEMO_MODE")
        expected = os.getenv("TICKETPILOT_REVIEWER_TOKEN", "")
        if not expected or not authorization or not secrets.compare_digest(authorization.encode("utf-8"), ("Bearer " + expected).encode("utf-8")):
            raise HTTPException(403, "Authenticated reviewer required for approvals and training-label corrections")
    if not store.get_ticket(tid):
        raise HTTPException(404, "ticket not found")
    if f.corrected_intent is not None and f.corrected_intent not in classifier().intent_to_category:
        raise HTTPException(422, "unknown intent")
    try:
        store.add_feedback(tid, f.rating, f.corrected_intent, int(f.approved) if f.approved is not None else None, f.comment)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"ok": True}


@app.get("/metrics")
def metrics():
    return store.metrics()


@app.get("/intents")
def intents():
    return sorted(classifier().intent_to_category)
