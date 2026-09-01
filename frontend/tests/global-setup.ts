// Log in once for the whole run instead of once per test.
//
// The suite kept failing at a different test each run with net::ERR_NO_BUFFER_SPACE —
// Windows running out of ephemeral ports, not an app fault. Every test was opening its
// own connections for GET /api/auth/status and POST /api/login on top of the page load
// and the eight API calls the app makes on mount, and TIME_WAIT holds each socket for
// minutes afterwards. Signing in once and handing every test the cookie removes two
// round-trips per test.
import { chromium, type FullConfig } from "@playwright/test";
import { readFileSync } from "node:fs";

export const STORAGE_STATE = "tests/.auth.json";

export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0]?.use?.baseURL ?? "http://127.0.0.1:8000";
  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL });
  const status = await (await context.request.get("/api/auth/status")).json();
  if (status.enabled) {
    const password = readFileSync("../backend/auth_password.txt", "utf8").trim();
    const r = await context.request.post("/api/login", { data: { password } });
    if (!r.ok()) throw new Error("smoke login failed — check backend/auth_password.txt");
  }
  await context.storageState({ path: STORAGE_STATE });
  await browser.close();
}
