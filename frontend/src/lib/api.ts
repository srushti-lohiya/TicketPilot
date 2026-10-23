import { setConnection } from "./connection";
import { offlineCreate, offlineMetrics, offlineTickets } from "./offline";
import type {
  Feedback,
  Health,
  Metrics,
  Status,
  StoredTicket,
  Ticket,
} from "./types";
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/backend${path}`, {
      ...init,
      cache: "no-store",
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch (e) {
    if (e instanceof Error && e.name === "AbortError") throw e;
    setConnection(null);
    throw new ApiError(
      "Cannot reach the workspace server. Check your connection and try again.",
      0,
    );
  }
  const body = await response.text();
  let data: unknown;
  try {
    data = JSON.parse(body);
  } catch {
    data = undefined;
  }
  if (!response.ok) {
    if (response.status >= 500) setConnection(null);
    const detail =
      data && typeof data === "object" && "detail" in data ? data.detail : null;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map(
                (d) =>
                  `${d.loc?.join(".") ?? "Request"}: ${d.msg ?? "Invalid value"}`,
              )
              .join("; ")
          : `Request failed (${response.status}). The API may be unavailable.`;
    throw new ApiError(message, response.status);
  }
  if (data === undefined)
    throw new ApiError(
      "The API returned an unexpected response.",
      response.status,
    );
  return data as T;
}
async function fallback<T>(
  live: () => Promise<T>,
  offline: () => T,
): Promise<T> {
  try {
    return await live();
  } catch (e) {
    if (e instanceof ApiError && (e.status === 0 || e.status >= 500))
      return offline();
    throw e;
  }
}
export const api = {
  health: async () => {
    try {
      const health = await request<Health>("/health");
      if (health.status !== "ok" || typeof health.llm !== "boolean")
        throw new ApiError("Invalid health response", 502);
      setConnection(health);
      return health;
    } catch (e) {
      setConnection(null);
      throw e;
    }
  },
  metrics: () => fallback(() => request<Metrics>("/metrics"), offlineMetrics),
  intents: () => request<string[]>("/intents"),
  tickets: (status?: Status, signal?: AbortSignal) =>
    fallback(
      () =>
        request<StoredTicket[]>(
          `/tickets?limit=200${status ? `&status=${status}` : ""}`,
          { signal },
        ),
      () =>
        Object.assign(
          offlineTickets().filter((t) => !status || t.status === status),
          { offline_demo: true },
        ),
    ),
  ticket: (id: number) =>
    id < 0
      ? Promise.resolve(offlineTickets().find((t) => t.id === id)).then((t) => {
          if (!t)
            throw new ApiError("Offline draft not found in this browser", 404);
          return t;
        })
      : request<StoredTicket>(`/tickets/${id}`),
  create: async (text: string) => {
    if (text.length < 3 || text.length > 5000)
      throw new ApiError("Message must contain 3–5000 characters", 422);
    try {
      await api.health();
    } catch {
      return offlineCreate(text);
    }
    return request<Ticket>("/tickets", {
      method: "POST",
      body: JSON.stringify({ text, use_llm: false }),
    });
  },
  feedback: (id: number, data: Feedback) => {
    if (id < 0)
      return Promise.reject(
        new ApiError(
          "Offline drafts cannot receive backend feedback or approvals",
          403,
        ),
      );
    return request<{ ok: boolean }>(`/tickets/${id}/feedback`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
};
