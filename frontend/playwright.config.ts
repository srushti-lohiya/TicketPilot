import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: process.env.TEST_BASE_URL || "http://127.0.0.1:3011",
    headless: true,
    trace: "retain-on-failure",
  },
  reporter: "list",
  webServer: [
    {
      command: "../.venv/bin/python scripts/test-api.py",
      url: "http://127.0.0.1:8011/health",
      timeout: 90_000,
      reuseExistingServer: false,
    },
    {
      command: "npm run start -- --hostname 127.0.0.1 --port 3011",
      url: "http://127.0.0.1:3011/new",
      timeout: 60_000,
      reuseExistingServer: false,
      env: { TICKETPILOT_API_URL: "http://127.0.0.1:8011" },
    },
  ],
});
