"""Step 6a: tools the agent can call. Each has a JSON schema (for LLM tool use) and a Python function.
Safety: the agent can READ orders and CANCEL unshipped orders. Refunds are never issued by the agent;
it checks eligibility and the ticket goes to a human for approval."""
from datetime import date
from contextvars import ContextVar

# Internal evaluations retain their isolated mock-order behavior; HTTP intake is read-only.
order_writes_allowed = ContextVar("order_writes_allowed", default=True)
from src import store
from src.config import DEMO_MODE
from src.retrieval import get_retriever

REFUND_WINDOW_DAYS = 30


def search_kb(query: str, intents=None, k: int = 3):
    return get_retriever().search(query, k=k, intents=intents)


def lookup_order(order_id: str):
    o = store.get_order(order_id)
    return o or {"error": f"order {order_id} not found"}


def check_refund_eligibility(order_id: str):
    o = store.get_order(order_id)
    if not o:
        return {"eligible": False, "reason": "order not found"}
    if o["refund_status"]:
        return {"eligible": False, "reason": f"refund already processed ({o['refund_status']})"}
    if o["final_sale"]:
        return {"eligible": False, "reason": "final-sale item (gift cards and personalised items are not refundable)"}
    if not o["delivered_at"]:
        return {"eligible": True, "reason": "not delivered yet; cancel or refuse delivery instead"}
    days = (date.today() - date.fromisoformat(o["delivered_at"])).days
    if days > REFUND_WINDOW_DAYS:
        return {"eligible": False, "reason": f"delivered {days} days ago, outside the {REFUND_WINDOW_DAYS}-day window"}
    return {"eligible": True, "reason": f"delivered {days} days ago, within the {REFUND_WINDOW_DAYS}-day window",
            "needs_human_approval": True}


def cancel_order(order_id: str):
    if DEMO_MODE or not order_writes_allowed.get():
        return {"cancelled": False, "reason": "public demo is read-only; authenticated order authorization required"}
    o = store.get_order(order_id)
    if not o:
        return {"cancelled": False, "reason": "order not found"}
    if o["status"] != "Processing":
        return {"cancelled": False, "reason": f"status is {o['status']}; only Processing orders can be cancelled"}
    store.set_order_status(order_id, "Cancelled")
    return {"cancelled": True, "order_id": order_id}


def escalate_to_human(reason: str, priority: str = "P3"):
    return {"escalated": True, "reason": reason, "priority": priority}


FUNCTIONS = {"search_kb": search_kb, "lookup_order": lookup_order,
             "check_refund_eligibility": check_refund_eligibility,
             "cancel_order": cancel_order, "escalate_to_human": escalate_to_human}

SCHEMAS = [
    {"name": "search_kb", "description": "Search the store's help-center policies. Always call this before answering a policy question.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "lookup_order", "description": "Get status, items, dates, tracking and refund status of an order by its number.",
     "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "check_refund_eligibility", "description": "Check whether an order can be refunded under policy. Does NOT issue a refund.",
     "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "cancel_order", "description": "Cancel an order. Only works while status is Processing. Use only if the customer clearly asked to cancel.",
     "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "escalate_to_human", "description": "Hand the ticket to a human agent: out-of-scope, security, legal, angry customer, or anything you cannot resolve with policy.",
     "input_schema": {"type": "object", "properties": {"reason": {"type": "string"},
                                                        "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]}},
                      "required": ["reason"]}},
]
