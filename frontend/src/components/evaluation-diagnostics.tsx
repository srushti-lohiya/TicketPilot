"use client";
import type { ConfusionReport, PerIntentRow } from "@/lib/evaluation-types";
import { humanize } from "@/lib/utils";
export function ConfusionMatrix({ report: r }: { report: ConfusionReport }) {
  const max = Math.max(1, ...r.matrix.flat());
  return (
    <div className="space-y-5 p-6 text-xs">
      <p className="leading-6 text-muted-foreground">
        {r.scope}. {r.correct} / {r.n} correct predictions. Out-of-scope rows
        are excluded because they are not a trained intent class. Rows are
        actual labels; columns are predicted labels. Counts are not normalized.
      </p>
      {r.topConfusions.length ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <caption className="pb-3 text-left font-medium">
              Most frequent recorded intent errors
            </caption>
            <thead className="border-y bg-slate-50 text-muted-foreground">
              <tr>
                {["Actual", "Predicted", "Count"].map((h) => (
                  <th key={h} scope="col" className="px-3 py-2 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {r.topConfusions.slice(0, 8).map((row) => (
                <tr key={`${row.actual}-${row.predicted}`} className="border-b">
                  <th scope="row" className="px-3 py-2 font-medium">
                    {humanize(row.actual)}
                  </th>
                  <td className="px-3 py-2">{humanize(row.predicted)}</td>
                  <td className="px-3 py-2 tabular-nums">{row.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>No incorrect intent predictions in the recorded in-scope rows.</p>
      )}
      <details>
        <summary className="cursor-pointer font-medium text-indigo-700">
          Full confusion matrix ({r.labels.length} × {r.labels.length})
        </summary>
        <p className="my-3 leading-6 text-muted-foreground">
          Column numbers map to the numbered row labels. Indigo cells are
          correct predictions; amber cells are errors. Scroll horizontally to
          inspect all intents.
        </p>
        <div
          className="max-h-[620px] overflow-auto rounded-lg border"
          tabIndex={0}
          aria-label="Scrollable intent confusion matrix"
        >
          <table className="w-max border-collapse text-center text-[10px]">
            <caption className="sr-only">
              Recorded realistic intent confusion counts
            </caption>
            <thead className="sticky top-0 z-10 bg-slate-50">
              <tr>
                <th className="min-w-48 px-3 py-2 text-left" scope="col">
                  Actual ↓ / predicted →
                </th>
                {r.labels.map((label, i) => (
                  <th
                    key={label}
                    scope="col"
                    className="min-w-7 px-1 py-2"
                    title={`Predicted: ${humanize(label)}`}
                  >
                    {i + 1}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {r.matrix.map((row, i) => (
                <tr key={r.labels[i]}>
                  <th
                    scope="row"
                    className="whitespace-nowrap border-t bg-white px-3 py-2 text-left font-medium"
                  >
                    {i + 1}. {humanize(r.labels[i])}
                  </th>
                  {row.map((n, j) => (
                    <td
                      key={r.labels[j]}
                      className="border border-white p-1 tabular-nums"
                      title={`${r.labels[i]} → ${r.labels[j]}: ${n}`}
                      style={{
                        backgroundColor: n
                          ? i === j
                            ? `rgba(99,102,241,${0.12 + (0.55 * n) / max})`
                            : `rgba(245,158,11,${0.18 + (0.5 * n) / max})`
                          : "#f8fafc",
                        color: n ? "#1e293b" : "#94a3b8",
                      }}
                    >
                      {n}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <p className="leading-6 text-muted-foreground">
        Bitext benchmark confusion counts: Not measured in the saved artifacts.
        Per-intent summary scores cannot reconstruct a full confusion matrix.
      </p>
    </div>
  );
}
export function PerIntentResults({ rows }: { rows: PerIntentRow[] }) {
  return (
    <details className="p-6 text-xs">
      <summary className="cursor-pointer font-medium text-indigo-700">
        Inspect {rows.length} intent classes
      </summary>
      <div className="mt-4 max-h-[520px] overflow-auto rounded-lg border">
        <table className="w-full text-left">
          <caption className="sr-only">
            Per-intent Bitext benchmark metrics
          </caption>
          <thead className="sticky top-0 bg-slate-50 text-muted-foreground">
            <tr>
              {["Intent", "Precision", "Recall", "F1", "Support"].map((h) => (
                <th key={h} scope="col" className="px-4 py-3 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.intent} className="border-t">
                <th
                  scope="row"
                  className="whitespace-nowrap px-4 py-3 font-medium"
                >
                  {humanize(r.intent)}
                </th>
                {[r.precision, r.recall, r.f1].map((v, i) => (
                  <td key={i} className="px-4 py-3 tabular-nums">
                    {v.toFixed(3)}
                  </td>
                ))}
                <td className="px-4 py-3 tabular-nums">{r.support}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
