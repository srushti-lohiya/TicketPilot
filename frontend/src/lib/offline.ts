import type { Metrics, StoredTicket } from "./types";
const key = "ticketpilot-offline-v1";
export function offlineTickets(): StoredTicket[] {
  try {
    return JSON.parse(localStorage.getItem(key) || "[]");
  } catch {
    return [];
  }
}
export function offlineCreate(text: string): StoredTicket {
  // Offline intake is a local draft, never simulated model inference.
  const t: StoredTicket = {
    id: -Date.now(),
    created: new Date().toISOString(),
    text,
    pii: [],
    intent: "unclassified",
    category: "Offline draft",
    confidence: 0,
    priority: "P3",
    risk_reasons: ["Not assessed offline"],
    status: "needs_review",
    route_reasons: [
      "Offline demo data: no classifier, retrieval, or backend processing ran",
    ],
    reply:
      "Saved locally for demonstration. Reconnect and submit to the backend for a policy-grounded answer.",
    citations: [],
    actions: [],
    guardrail_issues: ["Unprocessed offline draft"],
    agent: "none",
    latency_ms: 0,
    tokens_in: 0,
    tokens_out: 0,
  };
  localStorage.setItem(key, JSON.stringify([t, ...offlineTickets()]));
  return t;
}
export function offlineMetrics(): Metrics {
  const tickets = offlineTickets();
  return {
    offline_demo: true,
    tickets: tickets.length,
    by_status: { needs_review: tickets.length },
    by_priority: {},
    top_intents: {},
    auto_resolve_rate: 0,
    latency_ms_p50: null,
    latency_ms_p95: null,
    tokens_in: 0,
    tokens_out: 0,
    avg_rating: null,
    feedback_count: 0,
  };
}
