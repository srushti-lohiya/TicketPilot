export interface Report<T> {
  data: T | null;
  source: string;
  modified: string | null;
  error: string | null;
}
export interface ClassifierReport {
  bitextAccuracy: number | null;
  bitextF1: number | null;
  baselineAccuracy: number | null;
  bitextN: number | null;
  noisyAccuracy: number | null;
  categoryAccuracy: number | null;
  calibrationError: number | null;
  realisticAccuracy: number | null;
  realisticN: number | null;
  realisticInScopeN: number | null;
  realisticOosN: number | null;
  realisticF1: number | null;
  threshold: number | null;
  autoAccuracy: number | null;
  coverage: number | null;
}
export interface PipelineCounts {
  inScope: number;
  oos: number;
  drafted: number;
  guardrailPassed: number;
  guardrailFailed: number;
  groundedEligible: number;
  groundedPassed: number;
  autoResolved: number;
  autoCorrect: number;
  oosHeld: number;
  routing: Record<string, number>;
}
export interface E2EReport {
  agent: string | null;
  tickets: number | null;
  routing: Record<string, number>;
  autoPrecision: number | null;
  autoCoverage: number | null;
  guardrailPass: number | null;
  groundedRate: number | null;
  oosNotAuto: number | null;
  p50: number | null;
  p95: number | null;
  avgTokens: number | null;
  counts: PipelineCounts | null;
}
export interface RetrievalRow {
  set: string;
  mode: string;
  recall: number | null;
  mrr: number | null;
  n: number | null;
}
export interface PerIntentRow {
  intent: string;
  precision: number;
  recall: number;
  f1: number;
  support: number;
}
export interface ConfusionReport {
  labels: string[];
  matrix: number[][];
  n: number;
  correct: number;
  scope: string;
  topConfusions: { actual: string; predicted: string; count: number }[];
}
export interface EvaluationReports {
  schemaVersion: number;
  generatedAt: string;
  modelArtifactSha256AtGeneration: string | null;
  sources: {
    path: string;
    sha256: string | null;
    modified: string | null;
    error: string | null;
  }[];
  classifier: Report<ClassifierReport>;
  e2e: Report<E2EReport>;
  retrieval: Report<RetrievalRow[]>;
  perIntent: Report<PerIntentRow[]>;
  confusion: Report<ConfusionReport>;
}
