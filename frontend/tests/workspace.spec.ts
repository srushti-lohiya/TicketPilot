import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";

test.describe.configure({ mode: "serial" });
test("navigation stays visible and has a persistent active state on desktop and mobile", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Support, under control." }),
  ).toBeVisible();
  for (const label of [
    "Overview",
    "Ticket Inbox",
    "New Ticket",
    "Review Queue",
    "Evaluation Lab",
    "Analytics",
  ])
    await expect(
      page
        .getByRole("navigation")
        .getByRole("link", { name: label, exact: true }),
    ).toBeVisible();
  await expect(
    page
      .getByRole("navigation")
      .getByRole("link", { name: "Overview", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await page.setViewportSize({ width: 390, height: 844 });
  for (const label of [
    "Overview",
    "Ticket Inbox",
    "New Ticket",
    "Review Queue",
    "Evaluation Lab",
    "Analytics",
  ])
    await expect(
      page
        .getByRole("navigation")
        .getByRole("link", { name: label, exact: true }),
    ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("real backend intake, feedback-only save, and public approval denial", async ({
  page,
  request,
}) => {
  await page.goto("/new");
  await page.getByLabel("Customer message").fill("Where is my order 10233?");
  const posted = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/backend/tickets") &&
      r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Process ticket", exact: true })
    .click();
  const response = await posted;
  expect(response.request().postDataJSON().use_llm).toBe(false);
  expect(response.ok()).toBe(true);
  const ticket = await response.json();
  expect(ticket.agent).toBe("fallback");
  expect(ticket.status).toBe("needs_review");
  await expect(
    page.getByText("Suggested customer reply", { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Open full ticket & trace" }).click();
  await expect(
    page.getByRole("heading", { name: "Human review", exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Reviewer comment")
    .fill("Reviewed the stored policy references.");
  await page
    .getByRole("button", { name: "Save feedback", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Feedback saved" }),
  ).toBeVisible();
  expect(
    (await (await request.get(`/api/backend/tickets/${ticket.id}`)).json())
      .status,
  ).toBe("needs_review");
  await expect(
    page.getByRole("button", { name: "Approve resolution", exact: true }),
  ).toBeDisabled();
  const denied = await request.post(
    `/api/backend/tickets/${ticket.id}/feedback`,
    { data: { approved: true } },
  );
  expect(denied.status()).toBe(403);
  expect(
    (await (await request.get(`/api/backend/tickets/${ticket.id}`)).json())
      .status,
  ).toBe("needs_review");
});

test("escalated requests cannot be approved, but can receive comments", async ({
  page,
  request,
}) => {
  const response = await request.post("/api/backend/tickets", {
    data: {
      text: "My lawyer will sue you about this unsafe product",
      use_llm: false,
    },
  });
  const ticket = await response.json();
  expect(ticket.status).toBe("escalated");
  await page.goto(`/tickets/${ticket.id}`);
  await expect(
    page.getByRole("heading", { name: "Human review", exact: true }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("button", { name: "Approve resolution", exact: true })
      .first(),
  ).toBeDisabled();
  await expect(page.getByLabel("Classification correction")).toBeDisabled();
  await page
    .getByLabel("Reviewer comment")
    .fill("Requires specialist handling");
  await page
    .getByRole("button", { name: "Save feedback", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Feedback saved" }),
  ).toBeVisible();
  expect(
    (await (await request.get(`/api/backend/tickets/${ticket.id}`)).json())
      .status,
  ).toBe("escalated");
  await page.goto("/review");
  await expect(page.getByRole("table")).toContainText(ticket.text);
});

test("evaluation shows actual report values, inbox search is local, and analytics loads", async ({
  page,
}) => {
  const source = JSON.parse(
    readFileSync(
      path.resolve(process.cwd(), "..", "reports/classifier_report.json"),
      "utf8",
    ),
  );
  await page.goto("/evaluation");
  await expect(
    page.getByRole("heading", { name: "Evaluation lab", exact: true }),
  ).toBeVisible();
  await expect(
    page
      .getByText("Source: reports/classifier_report.json", { exact: false })
      .first(),
  ).toBeVisible();
  const chart = page
    .getByRole("img")
    .filter({ has: page.locator("svg") })
    .first();
  await expect(chart).toHaveAttribute(
    "aria-label",
    new RegExp(
      (source.bitext_test.accuracy * 100).toFixed(1).replace(".", "\\."),
    ),
  );
  await expect(
    page.getByRole("table", { name: "Saved retrieval comparison results" }),
  ).toContainText("hybrid+intent");
  await page.goto("/tickets");
  await page.getByLabel("Search loaded tickets").fill("10233");
  await expect(page.getByRole("table")).toContainText("10233");
  await expect(page.getByRole("table")).not.toContainText("My lawyer");
  await page.goto("/analytics");
  await expect(
    page.getByRole("heading", { name: "Processing & feedback", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Feedback submissions", { exact: true }),
  ).toBeVisible();
});

test("API failures show an actionable error instead of invented metrics", async ({
  page,
}) => {
  await page.route("**/api/backend/metrics", (route) =>
    route.fulfill({
      status: 502,
      contentType: "application/json",
      body: JSON.stringify({
        detail: "FastAPI unavailable for connection test.",
      }),
    }),
  );
  await page.goto("/analytics");
  await expect(
    page.getByText("Offline demo data · browser-local drafts", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Median processing time", { exact: true }),
  ).toBeVisible();
});

test("all screens stay light and fit desktop and mobile without browser errors", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.emulateMedia({ colorScheme: "dark" });
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const [name, route] of [
      ["overview", "/"],
      ["inbox", "/tickets"],
      ["intake", "/new"],
      ["review", "/review"],
      ["evaluation", "/evaluation"],
      ["analytics", "/analytics"],
    ]) {
      await page.goto(route);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
        `${name} at ${width}px`,
      ).toBe(true);
      expect(
        await page.evaluate(
          () => getComputedStyle(document.body).backgroundColor,
        ),
      ).toBe("rgb(248, 250, 252)");
      await page.screenshot({
        path: test.info().outputPath(`${name}-${width}.png`),
        fullPage: true,
      });
    }
  }
  expect(errors).toEqual([]);
});

test("one health state drives header and system mode, then recovers", async ({
  page,
}) => {
  await page.route("**/api/backend/health", (route) =>
    route.fulfill({ status: 502, json: { detail: "offline" } }),
  );
  await page.goto("/");
  await expect(page.locator("header")).toContainText("Offline demo data");
  await expect(
    page.getByText("Offline demo data", { exact: true }).last(),
  ).toBeVisible();
  await page.unroute("**/api/backend/health");
  await page.evaluate(() => window.dispatchEvent(new Event("online")));
  await expect(page.locator("header")).toContainText("API connected");
  await expect(page.getByText("ok", { exact: true })).toBeVisible();
});

test("offline drafts persist locally across intake, detail, inbox, review and analytics", async ({
  page,
}) => {
  await page.route("**/api/backend/**", (route) =>
    route.fulfill({ status: 502, json: { detail: "offline" } }),
  );
  await page.goto("/new");
  await page
    .getByLabel("Customer message")
    .fill("Offline sample request for demo");
  await page
    .getByRole("button", { name: "Process ticket", exact: true })
    .click();
  await expect(
    page.getByText("Offline demo data · local draft", { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Open full ticket & trace" }).click();
  await expect(
    page.getByRole("button", { name: "Approve resolution", exact: true }),
  ).toBeDisabled();
  await page.reload();
  await expect(
    page.getByText("Offline sample request for demo", { exact: true }),
  ).toBeVisible();
  for (const route of ["/tickets", "/review"]) {
    await page.goto(route);
    await expect(page.getByRole("table")).toContainText(
      "Offline sample request for demo",
    );
  }
  await page.goto("/analytics");
  await expect(
    page.getByText("Offline demo data · browser-local drafts", { exact: true }),
  ).toBeVisible();
  await page.goto("/evaluation");
  await expect(
    page.getByRole("status").filter({ hasText: "Static evaluation results" }),
  ).toBeVisible();
});

test("public demo cannot cancel orders or correct training labels", async ({
  request,
}) => {
  const response = await request.post("/api/backend/tickets", {
    data: {
      text: "pls cancel my order 10877, bought the wrong size",
      use_llm: false,
    },
  });
  const ticket = await response.json();
  expect(ticket.status).toBe("needs_review");
  expect(
    ticket.actions.find((a: { tool: string }) => a.tool === "cancel_order")
      .output.cancelled,
  ).toBe(false);
  expect(
    (
      await request.post(`/api/backend/tickets/${ticket.id}/feedback`, {
        data: { corrected_intent: "complaint" },
      })
    ).status(),
  ).toBe(403);
});

test("failed POST stays an error without silently creating a duplicate local draft", async ({
  page,
}) => {
  await page.route("**/api/backend/tickets", (route) =>
    route.request().method() === "POST"
      ? route.fulfill({ status: 502, json: { detail: "uncertain submission" } })
      : route.continue(),
  );
  await page.goto("/new");
  await page.getByLabel("Customer message").fill("Where is my order 10233?");
  await page
    .getByRole("button", { name: "Process ticket", exact: true })
    .click();
  await expect(
    page.getByRole("alert").filter({ hasText: "uncertain submission" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => localStorage.getItem("ticketpilot-offline-v1")),
  ).toBeNull();
});
