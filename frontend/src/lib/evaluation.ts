import snapshot from "@/data/evaluation.v1.json";
import type { EvaluationReports } from "./evaluation-types";

// Generated from repository reports. Bundled for portable, API-independent viewing.
// Regenerate: .venv/bin/python -m src.evaluation_snapshot
export async function loadEvaluation(): Promise<EvaluationReports> {
  return snapshot;
}
