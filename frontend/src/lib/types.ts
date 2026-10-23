export type Status =
  "auto_resolved" | "needs_review" | "escalated" | "resolved";
export type Priority = "P1" | "P2" | "P3" | "P4";
export interface Action {
  tool: string;
  input: Record<string, unknown>;
  output: unknown;
}
export interface DecisionMetadata {
  version: number;
  classifier: {
    top3: { intent: string; p: number }[];
    threshold: number;
    confident: boolean;
  };
  retrieval: {
    mode: string;
    intent_hints: string[];
    encoder: string | null;
    reranker: boolean;
    hits: {
      rank: number;
      id: string;
      title: string;
      text: string;
      score: number;
    }[];
  };
  input_checks: { pii_redaction: string; injection: string; risk: string };
  output_guardrails: {
    status: "not_run" | "passed" | "failed";
    reason: string | null;
    issues: string[];
  };
}
export interface Ticket {
  decision_metadata?: DecisionMetadata | null;
  id: number;
  text: string;
  pii: string[];
  intent: string;
  category: string;
  confidence: number;
  priority: Priority;
  risk_reasons: string[];
  status: Status;
  route_reasons: string[];
  reply: string;
  citations: string[];
  actions: Action[];
  guardrail_issues: string[];
  agent: "fallback" | "llm" | "none";
  latency_ms: number;
  tokens_in: number;
  tokens_out: number;
}
export type StoredTicket = Ticket & { created: string };
export interface Feedback {
  rating?: number | null;
  approved?: boolean | null;
  corrected_intent?: string | null;
  comment?: string | null;
}
export interface Metrics {
  offline_demo?: boolean;
  tickets: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  top_intents: Record<string, number>;
  auto_resolve_rate: number;
  latency_ms_p50: number | null;
  latency_ms_p95: number | null;
  tokens_in: number;
  tokens_out: number;
  avg_rating: number | null;
  feedback_count: number;
}
export interface Health {
  demo_mode?: boolean;
  storage?: "ephemeral" | "local";
  retrieval_backend?: string;
  model_loaded?: boolean;
  status: string;
  llm: boolean;
}
