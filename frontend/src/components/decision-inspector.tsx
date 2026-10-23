"use client";
import { BookOpen, Check, ShieldCheck } from "lucide-react";
import type { Ticket } from "@/lib/types";
import { humanize, percent } from "@/lib/utils";
import { Notice, Panel } from "./common";

export function EvidenceInspector({ ticket: t }: { ticket: Ticket }) {
  const m = t.decision_metadata?.version === 1 ? t.decision_metadata : null;
  const retrieval = m?.retrieval;
  const hits = retrieval?.hits ?? [];
  const ids = new Set(hits.map((h) => h.id));
  const extraCites = t.citations.filter((id) => !ids.has(id));
  return (
    <Panel
      title="Retrieval evidence"
      description="Evidence captured during processing; this panel never reruns retrieval."
    >
      <div className="space-y-4 p-6">
        {retrieval ? (
          <>
            <dl className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <dt className="text-muted-foreground">Retrieval method</dt>
                <dd className="mt-1 font-medium">
                  {humanize(retrieval.mode)} · intent hints
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Encoder</dt>
                <dd className="mt-1 break-all font-medium">
                  {retrieval.encoder ?? "Not recorded"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Reranker</dt>
                <dd className="mt-1 font-medium">
                  {retrieval.reranker ? "Enabled" : "Disabled"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Retrieved sections</dt>
                <dd className="mt-1 font-medium">{hits.length}</dd>
              </div>
            </dl>
            <p className="text-xs leading-6 text-muted-foreground">
              Rank and scores are from the initial retrieval.{" "}
              {retrieval.reranker
                ? "Scores are cross-encoder reranker outputs after hybrid candidate retrieval."
                : "Scores use reciprocal-rank fusion."}{" "}
              They are ranking values, not confidence probabilities. Scores from
              different methods are not directly comparable.
            </p>
            {hits.length ? (
              hits.map((hit) => (
                <article
                  key={`${hit.rank}-${hit.id}`}
                  className="rounded-lg border p-4"
                >
                  <div className="flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
                    <span>Rank {hit.rank}</span>
                    <span>· score {hit.score.toFixed(4)}</span>
                    <span
                      className={`ml-auto rounded px-2 py-1 font-medium ${t.citations.includes(hit.id) ? "bg-indigo-50 text-indigo-700" : "bg-slate-50 text-slate-500"}`}
                    >
                      {t.citations.includes(hit.id)
                        ? "Cited in response"
                        : "Retrieved · not cited"}
                    </span>
                  </div>
                  <h3 className="mt-3 flex items-start gap-2 text-xs font-semibold">
                    <BookOpen className="mt-0.5 size-3.5 shrink-0 text-indigo-500" />
                    {hit.title}
                  </h3>
                  <p className="mt-2 break-all font-mono text-[10px] text-slate-500">
                    {hit.id}
                  </p>
                  <details className="mt-3 text-xs">
                    <summary className="cursor-pointer font-medium text-indigo-700">
                      Read captured policy section
                    </summary>
                    <p className="mt-3 whitespace-pre-wrap leading-6 text-slate-600">
                      {hit.text}
                    </p>
                  </details>
                </article>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">
                No initial retrieval hits recorded.
              </p>
            )}
          </>
        ) : (
          <Notice>
            {t.id < 0
              ? "Offline draft: retrieval did not run."
              : "Not recorded for this ticket. Existing tickets retain their original citation IDs; historical ranks, scores and section text are not reconstructed from today’s knowledge base."}
          </Notice>
        )}
        {extraCites.length > 0 && (
          <div>
            <p className="section-label mb-2">Additional citation IDs</p>
            <div className="space-y-2">
              {extraCites.map((id) => (
                <p
                  key={id}
                  className="break-all rounded border p-3 font-mono text-xs"
                >
                  {id}
                </p>
              ))}
            </div>
            <p className="mt-3 text-xs leading-6 text-muted-foreground">
              Full evidence for these IDs is not captured in the initial
              retrieval metadata. A search tool result, if recorded, is
              available in the tool events below.
            </p>
          </div>
        )}
        <p className="text-xs leading-6 text-muted-foreground">
          A citation identifies a policy section. Its presence alone does not
          verify every claim in the final response.
        </p>
      </div>
    </Panel>
  );
}

export function ChecksInspector({ ticket: t }: { ticket: Ticket }) {
  const m = t.decision_metadata?.version === 1 ? t.decision_metadata : null;
  const output = m?.output_guardrails;
  return (
    <Panel
      title="Decision checks"
      description="Observable classifier outputs and rule results; no generated reasoning trace."
    >
      <div className="space-y-5 p-6 text-xs">
        {m ? (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-muted-foreground">Classifier threshold</p>
                <p className="mt-1 font-semibold">
                  {percent(m.classifier.threshold)}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Confidence gate</p>
                <p className="mt-1 font-semibold">
                  {m.classifier.confident ? "Accepted" : "Below threshold"}
                </p>
              </div>
            </div>
            <div>
              <p className="section-label mb-3">Top intent candidates</p>
              <ol className="space-y-3">
                {m.classifier.top3.map((p) => (
                  <li key={p.intent}>
                    <div className="mb-1 flex justify-between gap-3">
                      <span>{humanize(p.intent)}</span>
                      <span className="tabular-nums">{percent(p.p)}</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full bg-indigo-400"
                        style={{ width: `${p.p * 100}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ol>
            </div>
            <dl className="space-y-3 border-t pt-4">
              {Object.entries(m.input_checks).map(([name, value]) => (
                <div key={name} className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">{humanize(name)}</dt>
                  <dd className="text-right font-medium">{humanize(value)}</dd>
                </div>
              ))}
            </dl>
          </>
        ) : (
          <Notice>
            {t.id < 0
              ? "Offline draft: classifier and safety checks did not run."
              : "Classifier candidates, threshold, and individual input-check outcomes were not recorded for this older ticket. Persisted confidence, risk flags and routing remain visible."}
          </Notice>
        )}
        <div className="rounded-lg border p-4">
          <p className="flex items-center gap-2 font-semibold">
            <ShieldCheck className="size-4 text-indigo-500" />
            Output guardrails
          </p>
          <p className="mt-2 leading-6">
            {output
              ? output.status === "not_run"
                ? `Not run · ${output.reason}`
                : output.status === "passed"
                  ? "Passed · no output guardrail issues"
                  : "Failed · issues require review"
              : "Not recorded · an empty issue list does not establish which checks ran"}
          </p>
          {output?.issues.length ? (
            <ul className="mt-2 list-inside list-disc leading-6">
              {output.issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          ) : null}
        </div>
        <p className="flex items-start gap-2 leading-6 text-muted-foreground">
          <Check className="mt-1 size-3 shrink-0" />
          Confidence and threshold acceptance do not establish answer
          correctness or authorize tool actions. Routing also applies risk,
          intent policy and output checks.
        </p>
      </div>
    </Panel>
  );
}

export function ToolOutcome({ output }: { output: unknown }) {
  const r =
    output && typeof output === "object" && !Array.isArray(output)
      ? (output as Record<string, unknown>)
      : null;
  let label = "Result recorded";
  if (r?.error) label = `Tool error: ${String(r.error)}`;
  else if (r && "cancelled" in r)
    label = r.cancelled
      ? "Order cancellation succeeded"
      : `Order cancellation blocked: ${String(r.reason ?? "No reason recorded")}`;
  else if (r?.escalated)
    label = `Escalated: ${String(r.reason ?? "No reason recorded")}`;
  else if (r && "eligible" in r)
    label = `Refund eligibility: ${r.eligible ? "eligible" : "not eligible"} · ${String(r.reason ?? "No reason recorded")}`;
  else if (r?.status) label = `Recorded order status: ${String(r.status)}`;
  else if (Array.isArray(output))
    label = `${output.length} search results recorded`;
  return <p className="mt-2 text-xs leading-6 text-slate-600">{label}</p>;
}
