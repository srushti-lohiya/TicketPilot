"use client";
import { useState } from "react";
import {
  ArrowUpRight,
  Loader2,
  Send,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Ticket } from "@/lib/types";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Label } from "./ui/label";
import { Notice, PageHeading, Panel } from "./common";
import { Decision } from "./ticket-detail";
export function NewTicket() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<Ticket>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(undefined);
    setResult(undefined);
    try {
      setResult(await api.create(text.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to create ticket.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeading
        eyebrow="Ticket intake"
        title="A better answer starts here."
        description="Submit a customer request. Get a policy-grounded draft and a transparent routing decision."
      />
      <div className="grid gap-6 xl:grid-cols-2">
        <Panel
          title="Customer request"
          description="The backend will classify, retrieve, and draft. Use fictional requests only."
        >
          <form className="space-y-5 p-6" onSubmit={submit}>
            <div>
              <Label htmlFor="customer-message" className="mb-3">
                Customer message
              </Label>
              <Textarea
                id="customer-message"
                placeholder="e.g. Where is my order 10233? It has been 10 days."
                rows={9}
                minLength={3}
                maxLength={5000}
                required
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={busy}
                className="min-h-56 resize-y bg-white leading-7"
                aria-describedby="message-help"
              />
              <p
                id="message-help"
                className="mt-2 text-right text-xs text-muted-foreground"
              >
                {text.length.toLocaleString()} / 5,000 characters
              </p>
            </div>
            <div className="flex items-center gap-3 rounded-lg bg-slate-50 p-4">
              <ShieldCheck className="size-5 text-indigo-500" />
              <div>
                <p className="text-xs font-medium">
                  Deterministic backend agent
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  No paid model or API key needed.
                </p>
              </div>
            </div>
            <Button
              className="w-full"
              disabled={busy || text.trim().length < 3}
              type="submit"
            >
              {busy ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Send className="size-4" />
              )}
              {busy ? "Processing request…" : "Process ticket"}
            </Button>
            {error && (
              <div
                role="alert"
                className="rounded-lg border border-rose-100 bg-rose-50 p-4 text-sm text-rose-700"
              >
                {error} Check the inbox before resubmitting if the request timed
                out.
              </div>
            )}
            <p className="text-xs leading-6 text-muted-foreground">
              Backend processing redacts PII. Offline drafts stay in this
              browser; avoid personal information. Public demo intake cannot
              change orders.
            </p>
          </form>
        </Panel>
        <Panel
          title="Decision & suggested answer"
          description="Evidence and routing appear after processing."
          className="flex flex-col"
        >
          {busy ? (
            <div
              role="status"
              className="flex min-h-96 flex-1 flex-col items-center justify-center gap-4 p-6 text-center"
            >
              <Loader2 className="size-7 animate-spin text-indigo-500" />
              <p className="font-medium">Working through your request</p>
              <p className="text-xs text-muted-foreground">
                Classifying intent, retrieving policy, and checking risk…
              </p>
            </div>
          ) : result ? (
            <div className="space-y-5 p-6">
              <Decision ticket={result} />
              <Button variant="outline" asChild className="w-full">
                <Link href={`/tickets/${result.id}`}>
                  Open full ticket & trace
                  <ArrowUpRight className="size-4" />
                </Link>
              </Button>
            </div>
          ) : (
            <div className="flex min-h-96 flex-1 flex-col items-center justify-center px-8 text-center">
              <span className="mb-5 rounded-2xl bg-indigo-50 p-4">
                <Sparkles className="size-7 text-indigo-500" />
              </span>
              <h2 className="font-semibold">Clarity, with every answer.</h2>
              <p className="mt-3 max-w-xs text-sm leading-6 text-muted-foreground">
                Your ticket’s intent, confidence, risk, and suggested reply will
                appear here.
              </p>
              <div className="mt-6 w-full max-w-xs">
                <Notice>
                  Generated answers are drafts. No customer message is sent.
                </Notice>
              </div>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
