"""SQLite storage: tickets, feedback, and a mock orders table used by the agent's tools."""
import json, sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from src.config import DB_PATH, DEMO_MODE, DEMO_MAX_FEEDBACK

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT, text TEXT, pii TEXT,
  intent TEXT, category TEXT, confidence REAL, priority TEXT, risk_reasons TEXT,
  status TEXT, route_reasons TEXT, reply TEXT, citations TEXT, actions TEXT,
  guardrail_issues TEXT, agent TEXT, latency_ms REAL, tokens_in INTEGER, tokens_out INTEGER, decision_metadata TEXT);
CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER, created TEXT,
  rating INTEGER, corrected_intent TEXT, approved INTEGER, comment TEXT);
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY, status TEXT, items TEXT, total REAL, ordered_at TEXT,
  delivered_at TEXT, final_sale INTEGER, tracking TEXT, refund_status TEXT);
"""
JSON_COLS = {"pii", "risk_reasons", "route_reasons", "citations", "actions", "guardrail_issues", "decision_metadata"}


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c; c.commit()
    finally:
        c.close()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db():
    with conn() as c:
        c.executescript(SCHEMA)
        # Additive migration: existing tickets keep null metadata rather than reconstructed evidence.
        columns = {r["name"] for r in c.execute("PRAGMA table_info(tickets)")}
        if "decision_metadata" not in columns:
            c.execute("ALTER TABLE tickets ADD COLUMN decision_metadata TEXT")
        if c.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0:
            d = lambda days: (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
            c.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)", [
                ("10233", "Shipped", "Desk lamp", 39.0, d(10), None, 0, "1Z999AA10233", None),
                ("10345", "Delivered", "Wireless headphones", 129.0, d(20), d(15), 0, "1Z999AA10345", "Issued " + d(5)),
                ("10432", "Processing", "Blender", 89.0, d(2), None, 0, None, None),
                ("10561", "Packed", "Rain jacket (blue, M)", 110.0, d(1), None, 0, None, None),
                ("10877", "Processing", "Running shoes", 95.0, d(0), None, 0, None, None),
                ("10992", "Delivered", "Office chair", 249.0, d(40), d(35), 0, "1Z999AA10992", None),
                ("11001", "Delivered", "Gift card", 50.0, d(6), d(5), 1, None, None),
            ])


def save_ticket(t: dict) -> int:
    row = {k: (json.dumps(v) if k in JSON_COLS else v) for k, v in t.items()}
    row["created"] = now()
    cols = ",".join(row)
    with conn() as c:
        cur = c.execute(f"INSERT INTO tickets ({cols}) VALUES ({','.join('?' * len(row))})", list(row.values()))
        return cur.lastrowid


def _decode(r):
    d = dict(r)
    for k in JSON_COLS & d.keys():
        d[k] = json.loads(d[k]) if d[k] else (None if k == "decision_metadata" else [])
    return d


def get_ticket(tid):
    with conn() as c:
        r = c.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
    return _decode(r) if r else None


def list_tickets(status=None, limit=200):
    q, args = "SELECT * FROM tickets", []
    if status:
        q += " WHERE status=?"; args.append(status)
    with conn() as c:
        return [_decode(r) for r in c.execute(q + " ORDER BY id DESC LIMIT ?", args + [limit])]


def add_feedback(tid, rating=None, corrected_intent=None, approved=None, comment=None):
    with conn() as c:
        c.execute("BEGIN IMMEDIATE")
        if DEMO_MODE and c.execute("SELECT COUNT(*) FROM feedback").fetchone()[0] >= DEMO_MAX_FEEDBACK:
            raise ValueError("Ephemeral demo feedback limit reached; try after the service resets")
        if approved:
            row = c.execute("SELECT status, priority, guardrail_issues, risk_reasons, intent, actions FROM tickets WHERE id=?", (tid,)).fetchone()
            if (not row or row["status"] != "needs_review" or row["priority"] in ("P1", "P2")
                    or any(a.get("tool") in {"cancel_order", "refund_issued"} for a in json.loads(row["actions"] or "[]"))
                    or row["intent"] in {"cancel_order", "get_refund", "delete_account", "change_order", "payment_issue"}
                    or json.loads(row["guardrail_issues"] or "[]") or json.loads(row["risk_reasons"] or "[]")):
                raise ValueError("Only low-risk needs-review tickets without guardrail issues can be approved")
        c.execute("INSERT INTO feedback (ticket_id, created, rating, corrected_intent, approved, comment) "
                  "VALUES (?,?,?,?,?,?)", (tid, now(), rating, corrected_intent, approved, comment))
        if approved:
            c.execute("UPDATE tickets SET status='resolved' WHERE id=?", (tid,))


def get_order(order_id):
    with conn() as c:
        r = c.execute("SELECT * FROM orders WHERE id=?", (str(order_id),)).fetchone()
    return dict(r) if r else None


def set_order_status(order_id, status):
    with conn() as c:
        c.execute("UPDATE orders SET status=? WHERE id=?", (status, str(order_id)))


def metrics():
    with conn() as c:
        rows = [dict(r) for r in c.execute("SELECT status, priority, intent, latency_ms, tokens_in, tokens_out, agent FROM tickets")]
        fb = [dict(r) for r in c.execute("SELECT rating, approved FROM feedback")]
    n = len(rows)
    by = lambda k: {v: sum(1 for r in rows if r[k] == v) for v in sorted({r[k] for r in rows if r[k]})}
    lat = sorted(r["latency_ms"] for r in rows if r["latency_ms"] is not None)
    pct = lambda p: lat[min(len(lat) - 1, int(p * len(lat)))] if lat else None
    ratings = [f["rating"] for f in fb if f["rating"]]
    return {"tickets": n, "by_status": by("status"), "by_priority": by("priority"), "top_intents": by("intent"),
            "auto_resolve_rate": (sum(r["status"] == "auto_resolved" for r in rows) / n) if n else 0,
            "latency_ms_p50": pct(0.5), "latency_ms_p95": pct(0.95),
            "tokens_in": sum(r["tokens_in"] or 0 for r in rows), "tokens_out": sum(r["tokens_out"] or 0 for r in rows),
            "avg_rating": (sum(ratings) / len(ratings)) if ratings else None, "feedback_count": len(fb)}


def reset_orders():
    """Restore the mock orders table (evaluation runs may cancel orders)."""
    with conn() as c:
        c.execute("DELETE FROM orders")
    init_db()


def export_feedback_labels():
    """Human-corrected intents -> extra training rows for the classifier (feedback loop)."""
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT t.text AS text, f.corrected_intent AS intent FROM feedback f "
            "JOIN tickets t ON t.id = f.ticket_id WHERE f.corrected_intent IS NOT NULL")]
