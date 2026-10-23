"use client";
import { Clock3, MessageSquare, ShieldCheck, Star } from "lucide-react";
import { api } from "@/lib/api";
import { useResource } from "@/hooks/use-resource";
import { milliseconds } from "@/lib/utils";
import { ErrorState, Kpi, Loading, Notice, PageHeading, Panel } from "./common";
import { DistributionChart } from "./charts";
import { Button } from "./ui/button";
export function Analytics() {
  const r = useResource(api.metrics);
  if (!r.data)
    return r.error ? (
      <ErrorState message={r.error} retry={r.refresh} />
    ) : (
      <Loading />
    );
  const m = r.data;
  return (
    <>
      <p className="mb-4 text-xs text-muted-foreground">
        {r.data.offline_demo
          ? "Offline demo data · browser-local drafts"
          : "Live backend data"}
      </p>
      <PageHeading
        eyebrow="Workspace performance"
        title="Analytics"
        description="Recorded backend metrics when connected; browser-local draft counts when offline. No synthetic trends."
      >
        <Button variant="outline" onClick={r.refresh} disabled={r.loading}>
          Refresh metrics
        </Button>
      </PageHeading>
      {r.error && <ErrorState message={r.error} retry={r.refresh} />}
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi
          label="Median processing time"
          value={milliseconds(m.latency_ms_p50)}
          note="P50 · all recorded requests"
          icon={Clock3}
        />
        <Kpi
          label="P95 processing time"
          value={milliseconds(m.latency_ms_p95)}
          note="95th percentile · all requests"
          icon={Clock3}
        />
        <Kpi
          label="Needs review / escalated"
          value={`${m.by_status.needs_review ?? 0} / ${m.by_status.escalated ?? 0}`}
          note="Current pending workload"
          icon={ShieldCheck}
        />
        <Kpi
          label="Average reply rating"
          value={m.avg_rating == null ? "—" : `${m.avg_rating.toFixed(1)} / 5`}
          note={`${m.feedback_count} feedback submissions`}
          icon={Star}
        />
      </div>
      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <Panel
          title="Status distribution"
          description="Current ticket status, not historical transitions"
        >
          <DistributionChart values={m.by_status} />
        </Panel>
        <Panel
          title="Priority distribution"
          description="Rule-based risk and urgency classification"
        >
          <DistributionChart values={m.by_priority} />
        </Panel>
        <Panel
          title="Most common intents"
          description="Top eight by recorded ticket count"
        >
          <DistributionChart
            values={Object.fromEntries(
              Object.entries(m.top_intents)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 8),
            )}
          />
        </Panel>
        <Panel
          title="Processing & feedback"
          description="Totals across this workspace"
        >
          <div className="space-y-5 p-6">
            <MessageSquare className="size-5 text-indigo-500" />
            {[
              ["Input tokens", m.tokens_in.toLocaleString()],
              ["Output tokens", m.tokens_out.toLocaleString()],
              ["Feedback submissions", m.feedback_count.toLocaleString()],
              [
                "Human-resolved tickets",
                (m.by_status.resolved ?? 0).toLocaleString(),
              ],
            ].map(([k, v]) => (
              <div
                key={k}
                className="flex justify-between border-b pb-3 text-sm"
              >
                <span className="text-muted-foreground">{k}</span>
                <span className="font-medium tabular-nums">{v}</span>
              </div>
            ))}
            <p className="text-xs leading-6 text-muted-foreground">
              Local fallback requests report zero LLM tokens. Repeated feedback
              counts as additional submissions, not unique reviewed tickets.
            </p>
          </div>
        </Panel>
      </div>
      <Notice>
        The API has no historical series, queue-wait times, approval event
        counts, or per-agent latency breakdown. Processing latency is not
        customer response time. Offline benchmark results live in Evaluation
        Lab.
      </Notice>
    </>
  );
}
