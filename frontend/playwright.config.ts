import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  globalSetup: "./tests/global-setup.ts",
  // One retry, and only for the environment. Nineteen tests, each loading the app and
  // the eight API calls it makes on mount, exhaust Windows' ephemeral ports when the
  // suite is run repeatedly; the socket error then lands on whichever test happens to
  // be running, which is why the failure moved around. A genuinely broken test still
  // fails on the retry — this hides a flaky socket, not a flaky assertion.
  retries: 1,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:8000",
    storageState: "tests/.auth.json",
  },
});
