import { readFileSync } from "node:fs";
import { test, expect } from "@playwright/test";

// The app is password-gated once backend/auth_password.txt exists (online mode).
// Log in first so the smoke run tests the app, not the login page.
test.beforeEach(async ({ page }) => {
  const status = await (await page.request.get("/api/auth/status")).json();
  if (!status.enabled) return;
  const password = readFileSync("../backend/auth_password.txt", "utf8").trim();
  const r = await page.request.post("/api/login", { data: { password } });
  expect(r.ok(), "smoke login failed — check backend/auth_password.txt").toBeTruthy();
});

test("shell loads with sidebar and leads table", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Maxcolor")).toBeVisible();
  await expect(page.locator(".nav-item", { hasText: "客户库" })).toBeVisible();
  // Dashboard is the daily-workbench default; open the customer library explicitly.
  await page.getByRole("button", { name: /客户库/ }).click();
  await expect(page.locator("table tbody tr").first()).toBeVisible();
  // full columns present
  await expect(page.getByRole("columnheader", { name: "电话 / WhatsApp" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "IG" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "FB" })).toBeVisible();
});

test("untouched filter option exists", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /客户库/ }).click();
  await expect(page.locator("select option[value='untouched']")).toHaveCount(1);
  await expect(page.locator("select option[value='phone']")).toHaveCount(1);
});

// SAFETY: only selects a row to reveal the action bar — never clicks 发送 (that would send real messages).
test("selecting a lead reveals outreach action bar", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /客户库/ }).click();
  await page.locator("table tbody tr").first().locator("input[type=checkbox]").check();
  await expect(page.getByText(/触达（已选/)).toBeVisible();
  await expect(page.getByRole("button", { name: "发送邮件" })).toBeVisible();
});

// SAFETY: opens the detail drawer and reads it — does not save edits or send anything.
test("clicking a lead row opens detail drawer with stage and notes", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /客户库/ }).click();
  await page.locator("table tbody tr").first().locator("td").nth(2).click();
  await expect(page.locator(".drawer")).toBeVisible();
  await expect(page.getByText("销售阶段")).toBeVisible();
  await expect(page.getByText("下一步行动", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "安排任务" })).toBeVisible();
  await expect(page.getByText("LED 项目 / 商机")).toBeVisible();
  await expect(page.getByText("跟进记录", { exact: true })).toBeVisible();
  await page.locator(".drawer-close").click();
  await expect(page.locator(".drawer")).toHaveCount(0);
});

test("dashboard shows stats", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /仪表盘/ }).click();
  await expect(page.getByText("客户总数").first()).toBeVisible();
  await expect(page.getByText(/国家分布/)).toBeVisible();
  await expect(page.getByText("今日销售任务")).toBeVisible();
});

// SAFETY: reads the task workbench and creation controls, but does not create or complete anything.
test("sales activity workbench exposes one next-action queue", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /销售任务/ }).click();
  await expect(page.getByText("安排下一步")).toBeVisible();
  await expect(page.getByPlaceholder("输入并选择客户公司")).toBeVisible();
  await expect(page.getByRole("button", { name: "创建任务" })).toBeVisible();
  await expect(page.getByRole("button", { name: /全部未完成/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "最近完成" })).toBeVisible();
});

// SAFETY: only checks the discovery page renders — never clicks 搜索深挖/导入 (would hit network / write DB).
test("discovery page has multi-query textarea, presets and country picker", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /客户开发/ }).click();
  await expect(page.getByRole("button", { name: /搜索深挖/ })).toBeVisible();
  await expect(page.locator("textarea")).toBeVisible();
  await expect(page.getByRole("button", { name: /＋LED signage company/ })).toBeVisible();
  await expect(page.getByPlaceholder("选择或输入国家")).toBeVisible();
});

// SAFETY: reads the screening controls only — never runs a search.
test("discovery has peer/country screening on by default", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /客户开发/ }).click();
  await expect(page.getByText(/排除同行\/供应商/)).toBeVisible();
  await expect(page.locator("input[type=checkbox]").first()).toBeChecked();
  // India/Pakistan pre-excluded, shown as active chips
  await expect(page.getByRole("button", { name: "✓ India" })).toBeVisible();
  await expect(page.getByRole("button", { name: "✓ Pakistan" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Nigeria" })).toBeVisible();
});

// SAFETY: opens the health panel and reads it — never clicks 体检/一键处理 (would write DB).
test("leads page has health check panel", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /客户库/ }).click();
  await page.getByRole("button", { name: /客户库体检/ }).click();
  await expect(page.getByRole("button", { name: /开始体检/ })).toBeVisible();
});

// SAFETY: opens the quick-add panel and reads it — never clicks 添加入库.
test("leads page has quick-add panel", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /客户库/ }).click();
  await page.getByRole("button", { name: /快速添加/ }).click();
  await expect(page.getByPlaceholder(/粘贴链接/)).toBeVisible();
  await expect(page.getByRole("button", { name: "添加入库" })).toBeVisible();
});

// SAFETY: only reveals the action bar and reads the button — never clicks it.
test("action bar prevents same-day all-channel blasting", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /客户库/ }).click();
  await page.locator("table tbody tr").first().locator("input[type=checkbox]").check();
  await expect(page.getByText(/同一客户每天最多一次批量触达/)).toBeVisible();
  await expect(page.getByRole("button", { name: /一键全渠道/ })).toHaveCount(0);
});

// SAFETY: only checks the channels page renders — never clicks 连接 (would launch a real browser).
test("channels page is present", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /渠道连接/ }).click();
  // topbar h2 and card h3 both say 渠道连接 — assert the card heading specifically
  await expect(page.locator(".card h3", { hasText: "渠道连接" })).toBeVisible();
});

// SAFETY: only checks the inbox page renders — never clicks 拉取邮件 (would hit real IMAP).
test("inbox page is present", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /收件箱/ }).click();
  await expect(page.locator(".card h3", { hasText: "收件箱" })).toBeVisible();
  await expect(page.getByRole("button", { name: /拉取邮件/ })).toBeVisible();
});

// SAFETY: opens the drawer and reads the do-not-contact toggle — never checks it.
test("lead drawer shows do-not-contact toggle", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /客户库/ }).click();
  await page.locator("table tbody tr").first().locator("td").nth(2).click();
  await expect(page.getByRole("checkbox", { name: /不再联系/ })).toBeVisible();
  await page.locator(".drawer-close").click();
});

// SAFETY: validates the pipeline shell without assuming the live DB already has a deal.
test("opportunity pipeline shows forecast and LED project context", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /商机管道/ }).click();
  await expect(page.getByText("加权预测", { exact: true })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "下一步" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "LED 规格" })).toBeVisible();
  await expect(page.getByText(/共 \d+ 个项目/)).toBeVisible();
});

test("theme toggle switches to light and persists attribute", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /浅色/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: /深色/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});
