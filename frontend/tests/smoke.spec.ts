import { test, expect } from "@playwright/test";

// The app is password-gated once backend/auth_password.txt exists (online mode). The
// login happens once in global-setup and every test starts from that cookie — doing it
// per test cost two extra connections each, and the run was running Windows out of
// ephemeral ports.

test("shell loads with sidebar and leads table", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("MCVISUAL")).toBeVisible();
  await expect(page.locator(".nav-item", { hasText: "客户库" })).toBeVisible();
  // Dashboard is the daily-workbench default; open the customer library explicitly.
  await page.getByRole("button", { name: /客户库/ }).click();
  await expect(page.locator("table tbody tr").first()).toBeVisible();
  // full columns present
  await expect(page.getByRole("columnheader", { name: "电话 / WhatsApp" })).toBeVisible();
  // IG 和 FB 合成了一列「社媒」，官网跟在它后面
  await expect(page.getByRole("columnheader", { name: "社媒" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "官网" })).toBeVisible();
});

test("untouched filter option exists", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /客户库/ }).click();
  await expect(page.locator("select option[value='untouched']")).toHaveCount(1);
  await expect(page.locator("select option[value='phone']")).toHaveCount(1);
});

// SAFETY: only selects a row to reveal the action bar — never clicks 发送 (that would send real messages).
test("selecting a lead offers actions, and composing is opt-in", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /客户库/ }).click();
  await page.locator("table tbody tr").first().locator("input[type=checkbox]").check();
  // 客户库是管理客户的地方：勾选给出一条操作栏，不是一整张发信表单
  await expect(page.getByText(/已选 1 家/)).toBeVisible();
  await expect(page.getByRole("button", { name: /删除/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "取消选择" })).toBeVisible();
  await expect(page.getByRole("button", { name: "发送邮件" })).toHaveCount(0);
  // 点了触达才展开
  await page.getByRole("button", { name: /触达/ }).click();
  await expect(page.getByRole("button", { name: "发送邮件" })).toBeVisible();
});

// SAFETY: ticks a row and opens the confirm step, but never clicks 确认删除.
test("bulk delete asks before it destroys anything", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /客户库/ }).click();
  await page.locator("table tbody tr").first().locator("input[type=checkbox]").check();
  await page.getByRole("button", { name: /🗑 删除/ }).click();
  await expect(page.getByText(/不可恢复/)).toBeVisible();
  await expect(page.getByRole("button", { name: "确认删除" })).toBeVisible();
  await page.getByRole("button", { name: "取消", exact: true }).click();
  await expect(page.getByRole("button", { name: "确认删除" })).toHaveCount(0);
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
  // 公司信息和联系人在开场白正下方：打开一家客户，先要看的是这家是谁、官网在哪、找谁谈
  await expect(page.getByText("公司信息")).toBeVisible();
  await expect(page.getByRole("link", { name: /打开/ }).first()).toBeVisible();
  await expect(page.getByText(/联系人（\d+）/)).toBeVisible();
  await expect(page.getByRole("button", { name: "＋ 新建联系人" })).toBeVisible();
  await expect(page.getByText("往来记录")).toBeVisible();
  // 评分卡按 Allen 的判断删掉了；采购信号那种带出处的证据留着
  await expect(page.getByText(/不是成交概率/)).toHaveCount(0);
  await expect(page.getByText("LED 项目 / 商机")).toBeVisible();
  await expect(page.getByText("跟进记录", { exact: true })).toBeVisible();
  await page.locator(".drawer-close").click();
  await expect(page.locator(".drawer")).toHaveCount(0);
});

test("dashboard shows today's work and the stock analysis on one page", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /仪表盘/ }).click();
  // 单页：今天要做的和库存统计都在同一屏滚动里，不分标签（Allen 试过分页后的判断）
  await expect(page.getByText("客户总数").first()).toBeVisible();
  await expect(page.getByText(/国家分布/)).toBeVisible();
  await expect(page.getByText(/触达漏斗/)).toBeVisible();
  await expect(page.getByText("生成订单")).toBeVisible();
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
  await page.getByRole("button", { name: /触达/ }).click();
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

// SAFETY: opens a blank quotation form and reads controls, but never saves real sales data.
test("formal quotation and order workbench is ready for LED projects", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /报价订单/ }).click();
  await expect(page.locator(".card h3", { hasText: "正式报价" })).toBeVisible();
  await expect(page.locator(".card h3", { hasText: "订单履约与收款" })).toBeVisible();
  await expect(page.locator(".card h3", { hasText: "快速产品报价卡" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "报价号 / 项目" })).toBeVisible();
  await page.getByRole("button", { name: "＋ 新建正式报价" }).click();
  await expect(page.getByPlaceholder("输入并选择客户")).toBeVisible();
  await expect(page.getByPlaceholder("例如：Church P2.5 LED wall")).toBeVisible();
  await expect(page.getByRole("button", { name: "创建报价草稿" })).toBeVisible();
  await expect(page.getByText(/金额由系统根据尺寸、数量和单价重新计算/)).toBeVisible();
  await page.getByRole("button", { name: "关闭" }).click();
  await expect(page.getByPlaceholder("输入并选择客户")).toHaveCount(0);
});

// SAFETY: reads ranking and signal workbench only; never creates tasks, deals or signals.
test("sales intelligence radar explains priority and protects signal actions", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /销售雷达/ }).click();
  await expect(page.locator(".card h3", { hasText: "客户优先级（可解释评分）" })).toBeVisible();
  await expect(page.locator(".card h3", { hasText: "LED 采购信号" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "五项分数" })).toBeVisible();
  await expect(page.getByText(/没有来源和证据就不能保存/)).toBeVisible();
  await page.getByRole("button", { name: /录入采购信号/ }).click();
  await expect(page.getByPlaceholder("来源 URL（必填）")).toBeVisible();
  await expect(page.getByPlaceholder(/证据原文/)).toBeVisible();
  await expect(page.getByRole("button", { name: "保存信号" })).toBeVisible();
});

test("theme toggle switches to light and persists attribute", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /浅色/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: /深色/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});
