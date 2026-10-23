import { NextRequest, NextResponse } from "next/server";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 45; // Fits Hobby, including projects without Fluid Compute.
async function proxy(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const endpoint = "/" + path.join("/");
  const allowed =
    req.method === "GET"
      ? /^\/(health|metrics|intents|tickets(?:\/\d+)?)$/
      : /^\/tickets(?:\/\d+\/feedback)?$/;
  if (!allowed.test(endpoint))
    return NextResponse.json(
      { detail: "Endpoint not available." },
      { status: 404 },
    );
  const configured = process.env.TICKETPILOT_API_URL;
  if (process.env.VERCEL && !configured) {
    return NextResponse.json(
      {
        detail:
          "Set server-only TICKETPILOT_API_URL to your Render HTTPS origin.",
      },
      { status: 503 },
    );
  }
  let base: string;
  try {
    const upstream = new URL(configured || "http://127.0.0.1:8000");
    if (
      !["http:", "https:"].includes(upstream.protocol) ||
      upstream.username ||
      upstream.password ||
      upstream.pathname !== "/" ||
      upstream.search ||
      upstream.hash ||
      (process.env.VERCEL && upstream.protocol !== "https:")
    )
      throw new Error("Invalid upstream origin");
    base = upstream.origin;
  } catch {
    return NextResponse.json(
      {
        detail:
          "TICKETPILOT_API_URL must be an origin without credentials, path or query; Vercel requires HTTPS.",
      },
      { status: 503 },
    );
  }
  try {
    const body = req.method === "POST" ? await req.text() : undefined;
    if (body && new TextEncoder().encode(body).byteLength > 32768) {
      return NextResponse.json(
        { detail: "Public demo request exceeds 32 KiB." },
        { status: 413 },
      );
    }
    const response = await fetch(`${base}${endpoint}${req.nextUrl.search}`, {
      method: req.method,
      redirect: "manual",
      headers: {
        "Content-Type": "application/json",
        ...(req.headers.get("authorization")
          ? { Authorization: req.headers.get("authorization")! }
          : {}),
      },
      ...(body !== undefined ? { body } : {}),
      cache: "no-store",
      signal: AbortSignal.timeout(endpoint === "/health" ? 5_000 : 30_000),
    });
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("Content-Type") || "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "FastAPI is unavailable or timed out. A free backend may be waking up; wait about a minute and retry. Check TICKETPILOT_API_URL if this persists.",
      },
      { status: 502 },
    );
  }
}
export const GET = proxy;
export const POST = proxy;
