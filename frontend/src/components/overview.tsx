"use client";
import Link from "next/link";
import {
  ArrowRight,
  Clock3,
  Inbox,
  Plus,
  RefreshCw,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { Button } from "./ui/button";
import { DistributionChart } from "./charts";
import {
  ErrorState,
  Kpi,
  Loading,
  Notice,
  PageHeading,
  Panel,
  TicketTable,
} from "./common";
import { useResource } from "@/hooks/use-resource";
import { api } from "@/lib/api";
import { useConnection } from "@/lib/connection";
import { milliseconds, percent } from "@/lib/utils";
export function Overview() {
  const connection = useConnection();
  const resource = useResource(async () => {
    const [metrics, tickets] = await Promise.all([
      api.metrics(),
      api.tickets(),
    ]);
    return { metrics, tickets };
  });
  if (!resource.data)
    return resource.error ? (
      <ErrorState message={resource.error} retry={resource.refresh} />
    ) : (
      <Loading />
    );
  const { metrics: m, tickets } = resource.data;
  return (
    <>
      <p className="mb-4 text-xs text-muted-foreground">
        {resource.data.metrics.offline_demo
          ? "Offline demo data · browser-local drafts"
          : "Live backend data"}
      </p>
      <PageHeading
        eyebrow="Operations at a glance"
        title="Support, under control."
        description="A clear view of your inbox, automation, and the requests that need your team."
      >
        <Button asChild>
          <Link href="/new">
            <Plus className="size-4" />
            New ticket
          </Link>
        </Button>
      </PageHeading>
      {resource.error && (
        <div className="mb-6">
          <ErrorState message={resource.error} retry={resource.refresh} />
        </div>
      )}
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi
          label="Total tickets"
          value={m.tickets.toLocaleString()}
          note="All requests in this workspace"
          icon={Inbox}
        />
        <Kpi
          label="Auto-resolution rate"
          value={percent(m.auto_resolve_rate)}
          note="Current auto-resolved status"
          icon={Zap}
        />
        <Kpi
          label="Awaiting review"
          value={m.by_status.needs_review ?? 0}
          note={`${m.by_status.escalated ?? 0} additional escalated tickets`}
          icon={ShieldCheck}
        />
        <Kpi
          label="P95 processing time"
          value={milliseconds(m.latency_ms_p95)}
          note="Across recorded ticket processing"
          icon={Clock3}
        />
      </div>
      <div className="mb-6 grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <Panel
          title="Ticket status"
          description="Current distribution across the workspace"
        >
          <DistributionChart values={m.by_status} />
        </Panel>
        <Panel
          title="System mode"
          description="Connected services and automation policy"
        >
          <div className="space-y-5 p-6">
            <div className="flex items-center gap-3">
              <span className="rounded-lg bg-indigo-50 p-3 text-indigo-600">
                <Zap className="size-5" />
              </span>
              <div>
                <p className="font-semibold">
                  {connection.status === "online"
                    ? "Deterministic backend agent"
                    : "Backend agent unavailable"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Default for every request from this console
                </p>
              </div>
              <span className="ml-auto rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-semibold text-emerald-700">
                {connection.status === "online" ? "READY" : "OFFLINE"}
              </span>
            </div>
            <div className="space-y-3 border-t pt-4 text-xs">
              <div className="flex justify-between gap-2">
                <span className="text-muted-foreground">
                  FastAPI connection
                </span>
                <span className="flex items-center gap-1.5 font-medium">
                  {connection.status === "online"
                    ? "ok"
                    : connection.status === "offline"
                      ? "Offline demo data"
                      : "Checking…"}
                </span>
              </div>
              <div className="flex justify-between gap-2">
                <span className="text-muted-foreground">
                  LLM key configured on API
                </span>
                <span>
                  {!connection.health
                    ? "Unavailable"
                    : connection.health.llm
                      ? "Yes · unused by this console"
                      : "No · not required"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Order environment</span>
                <span>Mock orders only</span>
              </div>
            </div>
            <Notice>
              Replies are generated drafts. A resolution status does not send a
              message to a customer.
            </Notice>
          </div>
        </Panel>
      </div>
      <Panel
        title="Recent tickets"
        description="The latest requests and their routing decisions"
        action={
          <Button asChild variant="ghost" size="sm">
            <Link href="/tickets">
              View inbox
              <ArrowRight className="size-3.5" />
            </Link>
          </Button>
        }
      >
        <TicketTable tickets={tickets.slice(0, 5)} />
      </Panel>
      <div className="mt-4 flex justify-end">
        <Button
          variant="ghost"
          size="sm"
          disabled={resource.loading}
          onClick={resource.refresh}
        >
          <RefreshCw className="size-3.5" />
          Refresh workspace
        </Button>
      </div>
    </>
  );
}
