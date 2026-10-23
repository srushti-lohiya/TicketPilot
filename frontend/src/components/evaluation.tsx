"use client";
import { BookOpen, LockKeyhole, ShieldCheck, Target, Zap } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { EvaluationReports, Report } from "@/lib/evaluation-types";
import { dateTime, humanize, milliseconds, percent } from "@/lib/utils";
import { DistributionChart } from "./charts";
import { Kpi, Notice, PageHeading, Panel } from "./common";
import { ConfusionMatrix, PerIntentResults } from "./evaluation-diagnostics";
const rate = (value: number | null | undefined) =>
  value == null ? "Not measured" : percent(value);
const count = (value: number | null | undefined) =>
  value == null ? "Not measured" : value.toLocaleString();
const decimal = (value: number | null | undefined, digits = 4) =>
  value == null ? "Not measured" : value.toFixed(digits);
function Provenance({ report }: { report: Report<unknown> }) {
  return (
    <p className="break-all border-t px-6 py-3 text-[10px] leading-5 text-slate-400">
      Source: {report.source}
      {report.modified
        ? ` · Artifact modified ${dateTime(report.modified)} (not a verified run timestamp)`
        : " · Not measured"}
    </p>
  );
}
function Unavailable({ error }: { error: string | null }) {
  return (
    <div role="status" className="p-6">
      <p className="font-medium">Not measured</p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        {error ?? "No compatible recorded results are available."}
      </p>
    </div>
  );
}
function Measurements({ rows }: { rows: [string, string, string?][] }) {
  return (
    <dl className="grid grid-cols-2 gap-5 p-6 text-xs">
      {rows.map(([label, value, note]) => (
        <div key={label}>
          <dt className="text-muted-foreground">{label}</dt>
          <dd className="mt-2 font-semibold tabular-nums">{value}</dd>
          {note && (
            <p className="mt-1 text-[11px] leading-5 text-muted-foreground">
              {note}
            </p>
          )}
        </div>
      ))}
    </dl>
  );
}
export function Evaluation({ reports }: { reports: EvaluationReports }) {
  const c = reports.classifier.data;
  const e = reports.e2e.data;
  const n = e?.counts;
  const rows = reports.retrieval.data;
  const comparisons = [...new Set(rows?.map((r) => r.mode))].map((mode) => {
    const realistic = rows?.find(
      (r) => r.mode === mode && r.set === "realistic",
    )?.recall;
    const bitext = rows?.find(
      (r) => r.mode === mode && r.set === "bitext_sample",
    )?.recall;
    return {
      mode,
      realistic: realistic == null ? null : realistic * 100,
      bitext: bitext == null ? null : bitext * 100,
    };
  });
  const benchmarkBars = Object.fromEntries(
    [
      ["Bitext accuracy", c?.bitextAccuracy],
      ["Realistic in-scope", c?.realisticAccuracy],
    ].filter(
      (entry): entry is [string, number] => typeof entry[1] === "number",
    ),
  );
  const classifierBars = Object.fromEntries(
    [
      ["Majority baseline", c?.baselineAccuracy],
      ["TF-IDF + logistic", c?.bitextAccuracy],
    ].filter(
      (entry): entry is [string, number] => typeof entry[1] === "number",
    ),
  );
  return (
    <>
      <PageHeading
        eyebrow="Measure what matters"
        title="Evaluation lab"
        description="Real, saved offline results. Classifier performance, retrieval comparisons, and measured pipeline safety."
      >
        <span className="flex items-center gap-2 rounded-md border bg-white px-3 py-2 text-xs font-medium text-slate-500">
          <LockKeyhole className="size-3.5" />
          Snapshot v{reports.schemaVersion} · read-only
        </span>
      </PageHeading>
      <div className="mb-6">
        <Notice>
          Offline evaluation results · bundled from repository artifacts. These
          are independent of live operational metrics and API availability.
          Snapshot generated {dateTime(reports.generatedAt)}; this is not the
          evaluation run time. Viewing this page never trains models, runs
          evaluation, or changes orders.
        </Notice>
      </div>
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi
          label="Benchmark accuracy"
          value={rate(c?.bitextAccuracy)}
          note={`Bitext test · ${count(c?.bitextN)} samples`}
          icon={Target}
        />
        <Kpi
          label="Realistic in-scope accuracy"
          value={rate(c?.realisticAccuracy)}
          note={`${count(c?.realisticInScopeN)} in-scope · ${count(c?.realisticN)} held-out total`}
          icon={BookOpen}
        />
        <Kpi
          label="Benchmark macro F1"
          value={decimal(c?.bitextF1)}
          note="Equal weight per intent class"
          icon={Zap}
        />
        <Kpi
          label="Out-of-scope held from auto"
          value={rate(e?.oosNotAuto)}
          note={
            n
              ? `${n.oosHeld} / ${n.oos} out-of-scope pipeline tickets`
              : "Denominator: Not measured"
          }
          icon={ShieldCheck}
        />
      </div>
      <div className="mb-6 grid items-start gap-6 xl:grid-cols-2">
        <Panel
          title="Benchmark vs. realistic tickets"
          description="Different datasets and difficulty; accuracy does not transfer unchanged."
        >
          {c ? (
            <>
              {Object.keys(benchmarkBars).length ? (
                <DistributionChart percentage values={benchmarkBars} />
              ) : (
                <Unavailable error={null} />
              )}
              <div className="overflow-x-auto border-t">
                <table className="w-full text-left text-xs">
                  <caption className="sr-only">
                    Classifier dataset metrics
                  </caption>
                  <thead className="bg-slate-50 text-muted-foreground">
                    <tr>
                      {["Metric", "Bitext test", "Realistic test"].map((h) => (
                        <th
                          key={h}
                          scope="col"
                          className="px-6 py-3 font-medium"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      [
                        "Accuracy (in-scope)",
                        rate(c.bitextAccuracy),
                        rate(c.realisticAccuracy),
                      ],
                      ["Macro F1", decimal(c.bitextF1), decimal(c.realisticF1)],
                      ["Total samples", count(c.bitextN), count(c.realisticN)],
                      [
                        "In-scope samples",
                        count(c.bitextN),
                        count(c.realisticInScopeN),
                      ],
                    ].map(([label, a, b]) => (
                      <tr key={label} className="border-t">
                        <th scope="row" className="px-6 py-3 font-medium">
                          {label}
                        </th>
                        <td className="px-6 py-3 tabular-nums">{a}</td>
                        <td className="px-6 py-3 tabular-nums">{b}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="px-6 py-5 text-xs leading-6 text-muted-foreground">
                Bitext is template-generated and similar to the training
                distribution. Handwritten realistic tickets include paraphrases,
                typos, ambiguity, and unfamiliar requests. The held-out set has{" "}
                {count(c.realisticInScopeN)} in-scope and{" "}
                {count(c.realisticOosN)} out-of-scope tickets; the accuracy
                above excludes out-of-scope tickets. This small fictional test
                is a stress test, not a production estimate.
              </p>
            </>
          ) : (
            <Unavailable error={reports.classifier.error} />
          )}
          <Provenance report={reports.classifier} />
          <p className="px-6 pb-3 text-[10px] text-slate-400">
            Sample counts: reports/classifier_per_intent.txt and
            eval/realistic_tickets.csv
          </p>
        </Panel>
        <Panel
          title="Classifier comparison & calibration"
          description="Recorded majority baseline versus the trained TF-IDF + logistic regression classifier, on the same Bitext test set."
        >
          {c ? (
            <>
              {Object.keys(classifierBars).length ? (
                <DistributionChart percentage values={classifierBars} />
              ) : (
                <Unavailable error={null} />
              )}
              <Measurements
                rows={[
                  ["Majority baseline accuracy", rate(c.baselineAccuracy)],
                  ["Trained classifier accuracy", rate(c.bitextAccuracy)],
                  [
                    "Confidence threshold",
                    rate(c.threshold),
                    "Selected on realistic development tickets; evaluated on the held-out split",
                  ],
                  [
                    "Expected calibration error",
                    decimal(c.calibrationError),
                    "10 confidence bins on Bitext; lower is better",
                  ],
                  ["Noisy Bitext accuracy", rate(c.noisyAccuracy)],
                  ["Category accuracy", rate(c.categoryAccuracy)],
                  ["Threshold-only in-scope coverage", rate(c.coverage)],
                  ["Accepted-intent accuracy", rate(c.autoAccuracy)],
                ]}
              />
              <p className="px-6 pb-5 text-xs leading-6 text-muted-foreground">
                Threshold acceptance is a classifier metric, not pipeline
                auto-resolution. Pipeline policy, risk routing and guardrails
                further restrict automation. Baseline macro F1 and additional
                trained classifiers: Not measured.
              </p>
            </>
          ) : (
            <Unavailable error={reports.classifier.error} />
          )}
          <Provenance report={reports.classifier} />
        </Panel>
      </div>
      <div className="mb-6 grid items-start gap-6 xl:grid-cols-2">
        <Panel
          title="Pipeline safety & grounding"
          description={
            e
              ? `${e.agent ?? "Not measured"} agent · ${count(e.tickets)} recorded realistic tickets, including development data`
              : "Not measured"
          }
        >
          {e ? (
            <>
              <Measurements
                rows={[
                  [
                    "Auto-resolve precision",
                    rate(e.autoPrecision),
                    n
                      ? `${n.autoCorrect} / ${n.autoResolved} auto-resolved intents correct`
                      : "Denominator: Not measured",
                  ],
                  [
                    "In-scope auto coverage",
                    rate(e.autoCoverage),
                    n
                      ? `${n.autoResolved} auto-resolved / ${n.inScope} in-scope; see OOS safety separately`
                      : undefined,
                  ],
                  [
                    "Output guardrail pass",
                    rate(e.guardrailPass),
                    n
                      ? `${n.guardrailPassed} / ${n.drafted} non-escalated replies · ${n.guardrailFailed} failed`
                      : "Denominator: Not measured",
                  ],
                  [
                    "Grounded citation rate",
                    rate(e.groundedRate),
                    n
                      ? `${n.groundedPassed} / ${n.groundedEligible} in-scope, non-escalated replies`
                      : "Denominator: Not measured",
                  ],
                  [
                    "Out-of-scope held from auto",
                    rate(e.oosNotAuto),
                    n
                      ? `${n.oosHeld} / ${n.oos} out-of-scope tickets`
                      : undefined,
                  ],
                  [
                    "LLM judge scores",
                    "Not measured",
                    "No paid-model evaluation artifact is present",
                  ],
                ]}
              />
              <p className="px-6 pb-5 text-xs leading-6 text-muted-foreground">
                Grounding means overlap with a gold policy-section ID. It does
                not verify every claim or answer quality. Guardrail pass
                excludes escalated acknowledgements. Historical results were not
                rerun after public-demo API policy changes; they do not
                establish current HTTP authorization safety.
              </p>
            </>
          ) : (
            <Unavailable error={reports.e2e.error} />
          )}
          <Provenance report={reports.e2e} />
        </Panel>
        <Panel
          title="Routing & processing latency"
          description="Measured offline processing, not customer wait time or live queue performance."
        >
          {e ? (
            <>
              {Object.keys(e.routing).length ? (
                <DistributionChart percentage values={e.routing} />
              ) : (
                <Unavailable error={null} />
              )}
              <Measurements
                rows={[
                  [
                    "Needs review",
                    n
                      ? `${n.routing.needs_review ?? 0} tickets`
                      : "Not measured",
                  ],
                  [
                    "Escalated",
                    n ? `${n.routing.escalated ?? 0} tickets` : "Not measured",
                  ],
                  [
                    "Processing p50",
                    e.p50 == null ? "Not measured" : milliseconds(e.p50),
                  ],
                  [
                    "Processing p95",
                    e.p95 == null ? "Not measured" : milliseconds(e.p95),
                  ],
                  ["Average tokens / ticket", count(e.avgTokens)],
                  ["Hardware / warmup protocol", "Not measured"],
                ]}
              />
              <p className="px-6 pb-5 text-xs leading-6 text-muted-foreground">
                Routing percentages are rounded in the summary; exact counts
                come from recorded CSV rows. Latency includes this run’s
                initialization effects. Zero tokens describes the deterministic
                agent, not a paid-model cost estimate.
              </p>
            </>
          ) : (
            <Unavailable error={reports.e2e.error} />
          )}
          <Provenance report={reports.e2e} />
        </Panel>
      </div>
      <Panel
        title="Retrieval comparisons"
        description="Recorded configurations only · recall@3 and reciprocal rank within the first 10 results."
      >
        {rows?.length ? (
          <>
            <div
              className="h-72 px-4 pt-6 sm:px-6"
              role="img"
              aria-label="Grouped retrieval recall comparison. Exact values are in the table below."
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={comparisons}
                  barGap={6}
                  margin={{ left: -16, right: 0 }}
                >
                  <CartesianGrid vertical={false} stroke="#f1f5f9" />
                  <XAxis
                    dataKey="mode"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#64748b", fontSize: 10 }}
                  />
                  <YAxis
                    domain={[0, 100]}
                    unit="%"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                  />
                  <Tooltip
                    cursor={{ fill: "#f8fafc" }}
                    contentStyle={{
                      background: "#fff",
                      border: "1px solid #e2e8f0",
                      borderRadius: 8,
                    }}
                    formatter={(value) => `${Number(value).toFixed(1)}%`}
                  />
                  <Legend
                    iconType="circle"
                    wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
                  />
                  <Bar
                    isAnimationActive={false}
                    name="Realistic in-scope"
                    dataKey="realistic"
                    fill="#6366f1"
                    radius={[4, 4, 0, 0]}
                    maxBarSize={40}
                  />
                  <Bar
                    isAnimationActive={false}
                    name="Bitext sample"
                    dataKey="bitext"
                    fill="#c7d2fe"
                    radius={[4, 4, 0, 0]}
                    maxBarSize={40}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-5 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <caption className="sr-only">
                  Saved retrieval comparison results
                </caption>
                <thead className="border-y bg-slate-50 text-muted-foreground">
                  <tr>
                    {["Dataset", "Method", "Recall@3", "MRR@10", "Tickets"].map(
                      (h) => (
                        <th
                          key={h}
                          scope="col"
                          className="px-6 py-3 font-medium"
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr
                      key={`${r.set}-${r.mode}`}
                      className="border-b last:border-0"
                    >
                      <td className="px-6 py-3 text-muted-foreground">
                        {humanize(r.set)}
                      </td>
                      <th scope="row" className="px-6 py-3 font-medium">
                        {r.mode}
                      </th>
                      <td className="px-6 py-3 tabular-nums">
                        {rate(r.recall)}
                      </td>
                      <td className="px-6 py-3 tabular-nums">
                        {decimal(r.mrr, 3)}
                      </td>
                      <td className="px-6 py-3 tabular-nums">{count(r.n)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <Unavailable error={reports.retrieval.error} />
        )}
        <div className="border-t px-6 py-5 text-xs leading-6 text-muted-foreground">
          <p>
            BM25 is sparse retrieval; hybrid uses reciprocal-rank fusion.
            Hybrid+intent uses predicted top-three intent hints, never gold
            labels. “Dense” is the recorded mode name; encoder identity is Not
            measured in these artifacts and the implementation can fall back to
            word/character TF-IDF.
          </p>
          <p className="mt-2">
            Reranking comparison: Not measured. The CSV does not identify a
            reranker run or version, so no reranking bar or improvement is
            claimed.
          </p>
        </div>
        <Provenance report={reports.retrieval} />
      </Panel>
      <div className="mt-6 grid gap-6">
        <Panel
          title="Intent confusion matrix"
          description="Derived from actual recorded predictions; this is the pipeline’s realistic set, not the Bitext benchmark."
        >
          {reports.confusion.data ? (
            <ConfusionMatrix report={reports.confusion.data} />
          ) : (
            <Unavailable error={reports.confusion.error} />
          )}
          <Provenance report={reports.confusion} />
        </Panel>
        <Panel
          title="Per-intent benchmark results"
          description="Recorded precision, recall, F1 and support · rounded to three decimals by the original evaluator."
        >
          {reports.perIntent.data?.length ? (
            <PerIntentResults rows={reports.perIntent.data} />
          ) : (
            <Unavailable error={reports.perIntent.error} />
          )}
          <Provenance report={reports.perIntent} />
        </Panel>
        <Panel
          title="Reproducibility & measurement limits"
          description="Content hashes identify snapshot inputs; they do not establish historical run lineage."
        >
          <div className="space-y-4 p-6 text-xs leading-6 text-muted-foreground">
            <p>
              The classifier held-out set is small; pipeline and retrieval
              evaluations also include development data. No confidence
              intervals, production dataset validation, historical benchmark
              confusion matrix, or human helpfulness assessment was recorded.
            </p>
            <p>
              The original reports contain no verified model hash, retrieval
              encoder/reranker version, hardware specification, or run
              timestamp. The artifact hash below identifies the local model
              present during snapshot generation and does not prove that it
              produced the historical reports.
            </p>
            <details>
              <summary className="cursor-pointer font-medium text-slate-700">
                Snapshot sources & SHA-256 hashes
              </summary>
              <div className="mt-3 space-y-3">
                {reports.sources.map((s) => (
                  <div key={s.path}>
                    <p className="font-medium text-slate-700">{s.path}</p>
                    <p className="break-all font-mono text-[10px]">
                      {s.sha256 ?? "Not measured"}
                    </p>
                    {s.error && <p>{s.error}</p>}
                  </div>
                ))}
                <p className="font-medium text-slate-700">
                  Model artifact at snapshot generation
                </p>
                <p className="break-all font-mono text-[10px]">
                  {reports.modelArtifactSha256AtGeneration ?? "Not measured"}
                </p>
              </div>
            </details>
            <p>
              Refresh the snapshot from the repository root:{" "}
              <code className="break-all rounded bg-slate-50 px-1.5 py-1">
                .venv/bin/python -m src.evaluation_snapshot
              </code>
              . Verify freshness with <code>--check</code>. Generation reads
              saved reports; it never trains, runs inference, or calls an LLM.
            </p>
          </div>
        </Panel>
      </div>
    </>
  );
}
