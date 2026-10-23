"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  ChevronRight,
  CircleHelp,
  FlaskConical,
  Inbox,
  LayoutDashboard,
  Plus,
  ShieldCheck,
  Ticket,
  Workflow,
} from "lucide-react";
import { api } from "@/lib/api";
import { useEffect } from "react";
import { useConnection } from "@/lib/connection";
import { cn } from "@/lib/utils";
const navigation = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Ticket Inbox", href: "/tickets", icon: Inbox },
  { name: "New Ticket", href: "/new", icon: Plus },
  { name: "Review Queue", href: "/review", icon: ShieldCheck },
  { name: "Evaluation Lab", href: "/evaluation", icon: FlaskConical },
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
];
export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const active = navigation.find((n) =>
    n.href === "/" ? path === "/" : path.startsWith(n.href),
  );
  const connection = useConnection();
  useEffect(() => {
    const check = () => {
      if (document.visibilityState !== "hidden")
        void api.health().catch(() => {});
    };
    check();
    const interval = setInterval(check, 60000);
    window.addEventListener("online", check);
    document.addEventListener("visibilitychange", check);
    return () => {
      clearInterval(interval);
      window.removeEventListener("online", check);
      document.removeEventListener("visibilitychange", check);
    };
  }, []);
  return (
    <div className="min-h-screen">
      <a
        href="#main-content"
        className="sr-only z-50 bg-white p-4 focus:not-sr-only focus:fixed"
      >
        Skip to content
      </a>
      <aside className="border-b bg-white md:fixed md:inset-y-0 md:left-0 md:z-30 md:flex md:w-60 md:flex-col md:border-r md:border-b-0">
        <Link href="/" className="flex h-[72px] items-center gap-3 px-6">
          <span className="flex size-9 items-center justify-center rounded-xl bg-indigo-600 text-white">
            <Ticket className="size-5" />
          </span>
          <span className="text-xl font-semibold tracking-tight">
            TicketPilot<span className="text-indigo-500">.</span>
          </span>
        </Link>
        <div className="px-4 pb-4 md:mt-5">
          <p className="section-label mb-3 hidden px-3 md:block">Workspace</p>
          <nav
            aria-label="Main navigation"
            className="grid grid-cols-2 gap-1 sm:grid-cols-3 md:grid-cols-1"
          >
            {navigation.map((n) => {
              const selected = active?.href === n.href;
              return (
                <Link
                  key={n.href}
                  href={n.href}
                  aria-current={selected ? "page" : undefined}
                  className={cn(
                    "flex min-h-10 items-center gap-3 rounded-lg px-3 py-2 text-xs font-medium transition-colors sm:text-sm",
                    selected
                      ? "bg-indigo-50 text-indigo-700"
                      : "text-slate-500 hover:bg-slate-50 hover:text-slate-900",
                  )}
                >
                  <n.icon className="size-[18px] shrink-0" />
                  {n.name}
                  {selected && (
                    <span className="ml-auto hidden size-1.5 rounded-full bg-indigo-600 md:block" />
                  )}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="mt-auto hidden space-y-4 p-4 md:block">
          <div className="rounded-xl border bg-slate-50 p-4">
            <Workflow className="mb-3 size-5 text-indigo-500" />
            <p className="text-xs font-semibold">Human oversight, built in</p>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">
              Policy-grounded answers.
              <br />
              Your team stays in control.
            </p>
          </div>
          <div className="flex items-center gap-2 px-2 text-xs text-muted-foreground">
            <CircleHelp className="size-4" />
            <span>Portfolio demo workspace</span>
            <ArrowUpRight className="ml-auto size-3" />
          </div>
        </div>
      </aside>
      <div className="md:ml-60">
        <header className="flex h-16 items-center justify-between border-b bg-white px-6 lg:px-8">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Workspace</span>
            <ChevronRight className="size-3" />
            <span className="font-medium text-slate-700">
              {active?.name ?? "Ticket detail"}
              {path.startsWith("/tickets/") ? " / Detail" : ""}
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="hidden items-center gap-2 text-xs text-muted-foreground sm:flex">
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  connection.status === "offline"
                    ? "bg-amber-500"
                    : connection.status === "online"
                      ? "bg-emerald-500"
                      : "bg-slate-300",
                )}
              />
              {connection.status === "offline"
                ? "Offline demo data"
                : connection.status === "online"
                  ? "API connected"
                  : "Connecting"}
            </span>
            <span className="rounded-md border bg-slate-50 px-2 py-1 text-[10px] font-medium text-slate-500">
              DEMO
            </span>
            <span
              className="flex size-8 items-center justify-center rounded-full bg-indigo-50 text-xs font-semibold text-indigo-700"
              aria-label="Support operations workspace"
            >
              TP
            </span>
          </div>
        </header>
        <main
          id="main-content"
          className="mx-auto max-w-[1440px] px-4 py-8 sm:px-6 lg:px-8"
        >
          <p
            role="status"
            className="mb-4 rounded-lg border bg-white p-3 text-xs"
          >
            {path === "/evaluation"
              ? "Static evaluation results · saved report artifacts · "
              : ""}
            {connection.status === "offline"
              ? "Offline demo data · browser-local drafts only; backend data unavailable. Drafts are not synced automatically."
              : connection.status === "online"
                ? "API connected · deterministic local agent · mock orders · public demo is read-only for order changes."
                : "Checking backend connection…"}
          </p>
          {connection.health?.demo_mode && (
            <p className="mb-4 rounded-lg border border-amber-100 bg-amber-50 p-3 text-xs leading-6 text-amber-900">
              Public demo · fictional requests only. Tickets are shared with all
              visitors. Ephemeral storage resets when the free backend restarts
              or sleeps. No real orders are changed and no customer messages are
              sent.
            </p>
          )}
          {connection.status === "offline" && (
            <p className="mb-4 text-xs leading-6 text-muted-foreground">
              Free hosting may need about a minute to wake up. Offline drafts
              stay in this browser; resubmit explicitly after reconnecting.
              <button
                type="button"
                className="ml-2 font-medium text-indigo-700 underline"
                onClick={() => {
                  void api.health().catch(() => {});
                }}
              >
                Retry backend connection
              </button>
            </p>
          )}
          {children}
          <footer className="mt-8 flex flex-wrap justify-between gap-2 border-t pt-4 text-[11px] text-slate-400">
            <span>TicketPilot · Support operations</span>
            <span className="flex items-center gap-1.5">
              <Activity className="size-3" />
              Mock orders · Local fallback submissions
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
