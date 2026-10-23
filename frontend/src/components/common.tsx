"use client";
import Link from "next/link";
import {
  AlertCircle,
  ArrowUpRight,
  Inbox,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn, dateTime, humanize } from "@/lib/utils";
import type { Priority, Status, StoredTicket } from "@/lib/types";

export function PageHeading({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="section-label mb-2">{eyebrow}</p>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-[28px]">
          {title}
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          {description}
        </p>
      </div>
      {children}
    </div>
  );
}
export function StatusBadge({ status }: { status: Status }) {
  const colors: Record<Status, string> = {
    auto_resolved: "bg-emerald-50 text-emerald-700",
    resolved: "bg-slate-100 text-slate-600",
    needs_review: "bg-amber-50 text-amber-800",
    escalated: "bg-rose-50 text-rose-700",
  };
  return (
    <Badge
      variant="secondary"
      className={cn(
        "gap-1.5 whitespace-nowrap rounded-md border-0 px-2 py-1 font-medium",
        colors[status],
      )}
    >
      <span className="size-1.5 rounded-full bg-current" />
      {humanize(status)}
    </Badge>
  );
}
export function PriorityBadge({ priority }: { priority: Priority }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs font-medium",
        priority === "P1"
          ? "text-rose-700"
          : priority === "P2"
            ? "text-amber-700"
            : "text-slate-500",
      )}
    >
      <span aria-hidden="true">
        {priority === "P1" ? "▰" : priority === "P2" ? "▮" : "▥"}
      </span>
      {priority}
    </span>
  );
}
export function Loading() {
  return (
    <div
      role="status"
      className="panel flex min-h-48 items-center justify-center gap-3 p-8 text-muted-foreground"
    >
      <Loader2 className="size-4 animate-spin" />
      Loading workspace data…
    </div>
  );
}
export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div role="alert" className="panel flex flex-wrap items-center gap-4 p-6">
      <AlertCircle className="size-5 shrink-0 text-amber-600" />
      <div className="flex-1">
        <p className="font-medium">Unable to load data</p>
        <p className="mt-1 text-sm text-muted-foreground">{message}</p>
      </div>
      {retry && (
        <Button variant="outline" onClick={retry}>
          <RefreshCw className="size-4" />
          Try again
        </Button>
      )}
    </div>
  );
}
export function Empty({
  title = "No tickets yet",
  description = "Process your first customer request to start building your workspace.",
  action = false,
}: {
  title?: string;
  description?: string;
  action?: boolean;
}) {
  return (
    <div className="flex min-h-56 flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-4 rounded-xl bg-slate-50 p-3">
        <Inbox className="size-6 text-slate-400" />
      </div>
      <h3 className="font-semibold">{title}</h3>
      <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
        {description}
      </p>
      {action && (
        <Button asChild className="mt-6">
          <Link href="/new">
            Create a ticket
            <ArrowUpRight className="size-4" />
          </Link>
        </Button>
      )}
    </div>
  );
}
export function Panel({
  title,
  description,
  children,
  action,
  className,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("panel min-w-0 overflow-hidden", className)}>
      <div className="flex items-center justify-between gap-4 border-b px-6 py-5">
        <div>
          <h2 className="font-semibold">{title}</h2>
          {description && (
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {description}
            </p>
          )}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Kpi({
  label,
  value,
  note,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  note: string;
  icon: React.ElementType;
}) {
  return (
    <div className="panel px-6 py-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">{label}</p>
        <Icon className="size-4 text-slate-400" />
      </div>
      <p className="mt-3 text-[28px] font-semibold tracking-tight tabular-nums">
        {value}
      </p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{note}</p>
    </div>
  );
}
export function TicketTable({ tickets }: { tickets: StoredTicket[] }) {
  return tickets.length === 0 ? (
    <Empty action />
  ) : (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">
          Customer tickets. Open a request to view its decision and trace.
        </caption>
        <thead className="bg-slate-50/70 text-xs text-muted-foreground">
          <tr>
            {[
              "Ticket / customer request",
              "Priority",
              "Status",
              "Intent",
              "Created",
            ].map((label) => (
              <th
                key={label}
                className="whitespace-nowrap px-6 py-3 font-medium"
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tickets.map((t) => (
            <tr
              key={t.id}
              className="border-t transition-colors hover:bg-slate-50/70"
            >
              <td className="min-w-64 max-w-96 px-6 py-4">
                <Link href={`/tickets/${t.id}`} className="group block">
                  <span className="mb-1 block text-xs font-medium text-muted-foreground">
                    TP-{String(t.id).padStart(4, "0")}
                  </span>
                  <span className="line-clamp-1 font-medium group-hover:text-primary">
                    {t.text}
                  </span>
                </Link>
              </td>
              <td className="px-6 py-4">
                {t.id < 0 ? (
                  <span className="text-xs text-muted-foreground">
                    Not assessed
                  </span>
                ) : (
                  <PriorityBadge priority={t.priority} />
                )}
              </td>
              <td className="px-6 py-4">
                <StatusBadge status={t.status} />
              </td>
              <td className="max-w-48 px-6 py-4 text-xs text-muted-foreground">
                {humanize(t.intent)}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-xs text-muted-foreground">
                {dateTime(t.created)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-indigo-100 bg-indigo-50/50 p-4 text-xs leading-6 text-slate-600">
      <AlertCircle className="mt-1 size-4 shrink-0 text-indigo-500" />
      <div>{children}</div>
    </div>
  );
}
