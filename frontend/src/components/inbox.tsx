"use client";
import { useState } from "react";
import { ListFilter, RefreshCw, Search } from "lucide-react";
import { api } from "@/lib/api";
import type { Status } from "@/lib/types";
import { useResource } from "@/hooks/use-resource";
import {
  Empty,
  ErrorState,
  Loading,
  Notice,
  PageHeading,
  Panel,
  TicketTable,
} from "./common";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
export function InboxView({ review = false }: { review?: boolean }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Status | "all">("all");
  const [priority, setPriority] = useState("all");
  const resource = useResource(async () => {
    if (!review) return api.tickets();
    const groups = await Promise.all([
      api.tickets("needs_review"),
      api.tickets("escalated"),
    ]);
    return Object.assign(
      groups
        .flat()
        .sort((a, b) => a.priority.localeCompare(b.priority) || b.id - a.id),
      {
        offline_demo: groups.some((group) => "offline_demo" in group),
      },
    );
  });
  const rows = resource.data?.filter(
    (t) =>
      (filter === "all" || t.status === filter) &&
      (priority === "all" || t.priority === priority) &&
      `${t.text} ${t.intent} ${t.id}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  return (
    <>
      <p className="mb-4 text-xs text-muted-foreground">
        {resource.data &&
        (("offline_demo" in resource.data && resource.data.offline_demo) ||
          resource.data.some((t) => t.id < 0))
          ? "Offline demo data · browser-local drafts"
          : resource.data
            ? "Live backend data"
            : "Loading backend data…"}
      </p>
      <PageHeading
        eyebrow={review ? "Human oversight" : "All customer requests"}
        title={review ? "Review queue" : "Ticket inbox"}
        description={
          review
            ? "Review drafts, correct classifications, and handle escalated requests with care."
            : "Every request, its decision, and the evidence behind it. All in one place."
        }
      >
        <Button
          variant="outline"
          disabled={resource.loading}
          onClick={resource.refresh}
        >
          <RefreshCw className="size-4" />
          Refresh
        </Button>
      </PageHeading>
      {review && (
        <div className="mb-6">
          <Notice>
            Open a ticket to save ratings and comments. Public demo approvals
            and training-label corrections are disabled; the API requires an
            authenticated reviewer. Escalated and high-risk requests require
            specialist handling.
          </Notice>
        </div>
      )}
      <Panel
        title={review ? "Requests needing attention" : "All tickets"}
        description={
          review
            ? "Needs review and escalated · priority first"
            : "Newest first · up to 200 loaded tickets"
        }
        action={
          <span className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-500">
            {rows?.length ?? "—"} tickets
          </span>
        }
      >
        <div className="flex flex-wrap gap-3 border-b p-4">
          <div className="relative min-w-48 flex-1">
            <Search className="absolute top-3 left-3 size-4 text-slate-400" />
            <Input
              aria-label="Search loaded tickets"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search message, intent, or ticket ID…"
              className="bg-white pl-9"
            />
          </div>
          <div className="flex items-center gap-2">
            <ListFilter className="size-4 text-slate-400" />
            <label className="sr-only" htmlFor="status-filter">
              Status
            </label>
            <select
              id="status-filter"
              className="field w-auto"
              value={filter}
              onChange={(e) => setFilter(e.target.value as Status | "all")}
            >
              <option value="all">All statuses</option>
              <option value="needs_review">Needs review</option>
              <option value="escalated">Escalated</option>
              {!review && (
                <>
                  <option value="auto_resolved">Auto-resolved</option>
                  <option value="resolved">Resolved</option>
                </>
              )}
            </select>
            <label className="sr-only" htmlFor="priority-filter">
              Priority
            </label>
            <select
              id="priority-filter"
              className="field w-auto"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            >
              <option value="all">All priorities</option>
              {["P1", "P2", "P3", "P4"].map((p) => (
                <option key={p}>{p}</option>
              ))}
            </select>
          </div>
        </div>
        {resource.error ? (
          <ErrorState message={resource.error} retry={resource.refresh} />
        ) : resource.loading ? (
          <Loading />
        ) : rows?.length === 0 &&
          (query || filter !== "all" || priority !== "all") ? (
          <Empty
            title="No matching tickets"
            description="Try another search term or clear your status and priority filters."
          />
        ) : (
          <TicketTable tickets={rows ?? []} />
        )}
        <div className="border-t px-6 py-3 text-xs text-muted-foreground">
          Search and filters apply to loaded rows only.{" "}
          {review
            ? "Up to 200 tickets per status."
            : "The API does not return a total count or pagination cursor."}
        </div>
      </Panel>
    </>
  );
}
