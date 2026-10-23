import { loadEvaluation } from "@/lib/evaluation";
import { Evaluation } from "@/components/evaluation";
export const runtime = "nodejs";
export default async function Page() {
  return <Evaluation reports={await loadEvaluation()} />;
}
