"use client";
import { useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  BookOpen,
  Check,
  Code2,
  Loader2,
  ShieldCheck,
  Terminal,
} from "lucide-react";
import { api } from "@/lib/api";
import { useResource } from "@/hooks/use-resource";
import type { StoredTicket, Ticket } from "@/lib/types";
import { dateTime, humanize, milliseconds, percent } from "@/lib/utils";
import {
  ErrorState,
  Loading,
  Notice,
  PageHeading,
  Panel,
  PriorityBadge,
  StatusBadge,
} from "./common";
import { Button } from "./ui/button";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import {
  ChecksInspector,
  EvidenceInspector,
  ToolOutcome,
} from "./decision-inspector";
export function Decision({ ticket: t }: { ticket: Ticket }) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <StatusBadge status={t.status} />
        {t.id < 0 ? (
          <span className="text-xs">Risk not assessed</span>
        ) : (
          <PriorityBadge priority={t.priority} />
        )}
        <span className="ml-auto text-xs text-muted-foreground">
          {t.id < 0 ? "Offline demo data · local draft" : `#${t.id}`}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-4 border-y py-4">
        <div>
          <p className="section-label">Detected intent</p>
          <p className="mt-2 text-sm font-medium">{humanize(t.intent)}</p>
        </div>
        <div>
          <p className="section-label">Confidence</p>
          <p className="mt-2 text-sm font-medium">
            {t.id < 0 ? "Not assessed" : percent(t.confidence)}
          </p>
        </div>
      </div>
      <div>
        <p className="section-label mb-3">Suggested customer reply</p>
        <div className="whitespace-pre-wrap rounded-lg border border-indigo-100 bg-indigo-50/40 p-4 text-sm leading-7 text-slate-700">
          {t.reply || "No reply returned."}
        </div>
      </div>
      <div>
        <p className="section-label mb-2">Policy references</p>
        {t.citations.length ? (
          <div className="flex flex-wrap gap-2">
            {t.citations.map((c) => (
              <span
                key={c}
                className="inline-flex items-center gap-2 rounded-md border bg-white px-2 py-1.5 text-xs text-slate-600"
              >
                <BookOpen className="size-3 text-indigo-500" />
                {c}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            No policy references returned.
          </p>
        )}
      </div>
      {t.route_reasons.length > 0 && (
        <div>
          <p className="section-label mb-2">Routing reasons</p>
          <ul className="list-inside list-disc space-y-1 text-xs leading-6 text-slate-600">
            {t.route_reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}
      <div>
        <p className="section-label mb-2">Risk signals</p>
        <p className="text-xs leading-6 text-slate-600">
          {t.risk_reasons.length
            ? t.risk_reasons.join(" · ")
            : "No rule-based risk signals detected."}
        </p>
      </div>
      {t.guardrail_issues.length > 0 && (
        <div
          role="note"
          className="rounded-lg bg-amber-50 p-4 text-xs leading-6 text-amber-800"
        >
          <strong>Output guardrail issues</strong>
          <ul className="list-inside list-disc">
            {t.guardrail_issues.map((i) => (
              <li key={i}>{i}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
function ReviewForm({
  ticket,
  refresh,
}: {
  ticket: StoredTicket;
  refresh: () => void;
}) {
  const intents = useResource(api.intents);
  const [corrected, setCorrected] = useState("");
  const [rating, setRating] = useState("");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const canApprove = false;
  async function save(approve: boolean) {
    if (busy) return;
    setBusy(true);
    setMessage("");
    setError("");
    try {
      if (approve) {
        const latest = await api.ticket(ticket.id);
        if (
          latest.status !== "needs_review" ||
          latest.guardrail_issues.length
        ) {
          refresh();
          throw new Error(
            "This ticket is no longer eligible for approval. Refresh and review its current state.",
          );
        }
      }
      await api.feedback(ticket.id, {
        ...(corrected ? { corrected_intent: corrected } : {}),
        ...(rating ? { rating: Number(rating) } : {}),
        ...(comment.trim() ? { comment: comment.trim() } : {}),
        ...(approve ? { approved: true } : {}),
      });
      setMessage(
        approve
          ? "Resolution approved. No customer message was sent."
          : "Feedback saved. Ticket status preserved.",
      );
      setCorrected("");
      setRating("");
      setComment("");
      dialog.current?.close();
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save feedback.");
      dialog.current?.close();
    } finally {
      setBusy(false);
    }
  }
  return (
    <Panel
      title="Human review"
      description="Feedback and resolution are separate actions."
    >
      <form
        className="space-y-4 p-6"
        onSubmit={(e) => {
          e.preventDefault();
          void save(false);
        }}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="corrected-intent" className="mb-2">
              Classification correction
            </Label>
            <select
              id="corrected-intent"
              className="field"
              value={corrected}
              onChange={(e) => setCorrected(e.target.value)}
              disabled={true}
            >
              <option value="">Keep original intent</option>
              {intents.data?.map((i) => (
                <option key={i} value={i}>
                  {humanize(i)}
                </option>
              ))}
            </select>
            {intents.error && (
              <p className="mt-2 text-xs text-amber-700">
                Intent list unavailable.{" "}
                <button
                  type="button"
                  className="underline"
                  onClick={intents.refresh}
                >
                  Retry
                </button>
              </p>
            )}
          </div>
          <div>
            <Label htmlFor="rating" className="mb-2">
              Reply quality
            </Label>
            <select
              id="rating"
              className="field"
              value={rating}
              onChange={(e) => setRating(e.target.value)}
              disabled={busy}
            >
              <option value="">No rating</option>
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n} / 5
                </option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <Label htmlFor="review-comment" className="mb-2">
            Reviewer comment{" "}
            <span className="text-muted-foreground">(optional)</span>
          </Label>
          <Textarea
            id="review-comment"
            rows={3}
            maxLength={2000}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            disabled={busy}
            placeholder="Add context for the team. Avoid personal information."
          />
        </div>
        <div className="flex flex-wrap gap-3">
          <Button
            type="submit"
            variant="outline"
            disabled={busy || (!corrected && !rating && !comment.trim())}
          >
            {busy ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Check className="size-4" />
            )}
            Save feedback
          </Button>
          <Button
            type="button"
            disabled={busy || !canApprove}
            onClick={() => dialog.current?.showModal()}
          >
            <ShieldCheck className="size-4" />
            Approve resolution
          </Button>
        </div>
        {!canApprove && (
          <p className="text-xs leading-6 text-muted-foreground">
            {ticket.status === "escalated"
              ? "Escalated tickets require specialist handling. No specialist-resolution endpoint is available."
              : ticket.guardrail_issues.length
                ? "Approval disabled: the draft has output guardrail issues. Reply editing is not supported by the API."
                : "Public demo approval is disabled. An authenticated reviewer may approve eligible low-risk drafts through the API."}
          </p>
        )}
        {message && (
          <p role="status" className="text-sm text-emerald-700">
            {message}
          </p>
        )}
        {error && (
          <p role="alert" className="text-sm text-rose-700">
            {error} Check the ticket before retrying a timed-out submission.
          </p>
        )}
        <p className="text-xs leading-5 text-muted-foreground">
          Public demo approvals and training-label corrections require an
          authenticated reviewer through the API. Server-side checks reject
          high-risk or ineligible approvals.
        </p>
      </form>
      <dialog
        ref={dialog}
        aria-labelledby="approval-title"
        className="fixed inset-0 m-auto w-[calc(100%-32px)] max-w-md rounded-xl border bg-white p-6 shadow-xl backdrop:bg-slate-900/30"
      >
        <h3 id="approval-title" className="text-lg font-semibold">
          Approve this resolution?
        </h3>
        <p className="my-4 text-sm leading-6 text-muted-foreground">
          This records feedback and changes ticket #{ticket.id} to resolved. It
          does not send the reply or execute new tools.
        </p>
        <div className="flex justify-end gap-3">
          <Button
            variant="outline"
            disabled={busy}
            onClick={() => dialog.current?.close()}
          >
            Cancel
          </Button>
          <Button disabled={busy} onClick={() => void save(true)}>
            {busy && <Loader2 className="size-4 animate-spin" />}Approve
            resolution
          </Button>
        </div>
      </dialog>
    </Panel>
  );
}
export function TicketDetail({ id }: { id: number }) {
  const resource = useResource(() => api.ticket(id));
  if (!resource.data)
    return resource.error ? (
      <ErrorState message={resource.error} retry={resource.refresh} />
    ) : (
      <Loading />
    );
  const t = resource.data;
  return (
    <>
      <p className="mb-4 text-xs text-muted-foreground">
        {resource.data.id < 0
          ? "Offline demo data · browser-local drafts"
          : "Live backend data"}
      </p>
      <Link
        href="/tickets"
        className="mb-5 inline-flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-primary"
      >
        <ArrowLeft className="size-3.5" />
        Back to inbox
      </Link>
      <PageHeading
        eyebrow="Ticket workspace"
        title={`Ticket TP-${String(t.id).padStart(4, "0")}`}
        description={`Created ${dateTime(t.created)} · ${humanize(t.category)}`}
      >
        <StatusBadge status={t.status} />
      </PageHeading>
      {resource.error && (
        <ErrorState message={resource.error} retry={resource.refresh} />
      )}
      <div className="grid items-start gap-6 xl:grid-cols-[1.15fr_1fr]">
        <div className="space-y-6">
          <Panel
            title="Customer message"
            description={
              t.id < 0
                ? "Browser-local draft · not processed or redacted"
                : "Stored text after pattern-based PII redaction"
            }
          >
            <div className="p-6">
              <p className="whitespace-pre-wrap text-sm leading-7">{t.text}</p>
              <div className="mt-4 border-t pt-3 text-xs text-muted-foreground">
                {t.id < 0
                  ? "Not scanned for PII offline."
                  : t.pii.length
                    ? `Redacted categories: ${t.pii.join(", ")}`
                    : "No supported PII patterns detected."}
              </div>
            </div>
          </Panel>
          <Panel
            title="AI decision"
            description="Final generated draft or escalation acknowledgement, with recorded routing metadata"
          >
            <div className="p-6">
              <Decision ticket={t} />
            </div>
          </Panel>
          <Notice>
            Only observable decision metadata is shown. A resolved or
            auto-resolved status does not send a customer message.
          </Notice>
          <ReviewForm ticket={t} refresh={resource.refresh} />
        </div>
        <div className="space-y-6">
          <ChecksInspector ticket={t} />
          <EvidenceInspector ticket={t} />
          <Panel
            title="Tool execution timeline"
            description="Recorded order of execution; individual timestamps unavailable."
          >
            <div className="p-6">
              {t.actions.length ? (
                <ol className="space-y-5">
                  {t.actions.map((a, i) => (
                    <li key={i} className="relative border-l pl-6 pb-1">
                      <span className="absolute -left-2.5 top-0 flex size-5 items-center justify-center rounded-full border bg-white text-[10px] text-indigo-600">
                        {i + 1}
                      </span>
                      <p className="flex items-center gap-2 text-xs font-semibold">
                        <Terminal className="size-3.5 text-slate-400" />
                        {a.tool}
                      </p>
                      <ToolOutcome output={a.output} />
                      <details className="mt-2 text-xs">
                        <summary className="cursor-pointer text-muted-foreground">
                          View input & result
                        </summary>
                        <pre className="mt-2 max-h-72 overflow-auto rounded-md bg-slate-50 p-3 text-[11px] leading-5">
                          {JSON.stringify(
                            { input: a.input, output: a.output },
                            null,
                            2,
                          )}
                        </pre>
                      </details>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No tools executed.
                </p>
              )}
            </div>
          </Panel>
          <Panel
            title="Technical trace"
            description="Persisted execution metadata"
          >
            <dl className="space-y-3 p-6 text-xs">
              {[
                ["Agent", t.agent],
                [
                  "Processing time",
                  t.id < 0 ? "Not processed" : milliseconds(t.latency_ms),
                ],
                ["Input / output tokens", `${t.tokens_in} / ${t.tokens_out}`],
                [
                  "Output checks",
                  t.decision_metadata?.version === 1
                    ? humanize(t.decision_metadata.output_guardrails.status)
                    : "Not recorded",
                ],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">{k}</dt>
                  <dd className="text-right font-medium">{v}</dd>
                </div>
              ))}
            </dl>
            <details className="border-t p-6 text-xs">
              <summary className="flex cursor-pointer items-center gap-2 text-muted-foreground">
                <Code2 className="size-4" />
                {t.id < 0 ? "Local draft record" : "Full API response"}
              </summary>
              <pre className="mt-4 max-h-96 overflow-auto rounded-md bg-slate-50 p-3 text-[11px] leading-5">
                {JSON.stringify(t, null, 2)}
              </pre>
            </details>
          </Panel>
        </div>
      </div>
    </>
  );
}
