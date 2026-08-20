# 客户开发 / 多渠道触达工具 — 设计规范（v1 草案）

**日期**：2026-07-02
**状态**：✅ 已确认（Allen 2026-07-02 批准："就按你推荐的来"），进入实现计划
**作者**：Claude (brainstorming 流程产出)

> §9 的 5 项决策已全部按推荐默认值锁定：
> 1. 产品定位 = **自用版 MVP 优先**
> 2. 技术栈 = **FastAPI + SQLite + React 看板**
> 3. MVP 渠道 = **Email + IG + WA**（FB/LinkedIn 后置）
> 4. 界面语言 = **中文**
> 5. 商用约束 = **Phase 1 纯自用**，商用多租户完全后置到 Phase 2

---

## 1. 背景与问题

深圳迈彩视觉（LED 显示屏 B2B）目前的客户开发全流程都靠 Claude Code + 一堆一次性脚本完成，痛点非常明确：

- **客户库**：79 个 `generate_led_leads_vN.py` 链式 Python 文件（~925 条），每加一批就加一个脚本文件。
- **触达脚本**：50 个 email sender + 72 个 IG DM + 38 个 WA send 脚本，各写各的、版本号无限增长。
- **状态**：散落在 `pipeline/{email,whatsapp,instagram,facebook}/*.json`，无看板、无统一视图。
- **发现/深挖**：全靠对话里手动 WebSearch + Jina 抓取 + 人工判断，零沉淀。

**结论**：同一件事重复了 200+ 次 → 强产品化信号。目标是把这套流程收敛成**一个有可视化界面的应用**，Allen 点几下就能完成"搜索候选 → 深挖验证 → 入库去重 → 多渠道触达 → 看进度/回复"，无需再开 Claude Code 写脚本。

---

## 2. 范围与阶段（🟡 待确认：产品定位）

**推荐：自用版 MVP 优先，架构预留商用扩展。**

| 阶段 | 内容 | 说明 |
|---|---|---|
| **Phase 1（本规范聚焦）** | 单用户本地 Web 应用 | 驱动 Allen 自己的 Chrome + Gmail；替代当前全部脚本；SQLite 本地库 |
| Phase 2（后续单独立项） | 多租户商用 SaaS | 云部署、注册登录、计费、每租户渠道凭证与浏览器隔离、合规。**工作量数倍，法律责任连带，单独立项** |

理由：Phase 1 直接消除当前痛点、复用已有 CDP+Gmail 基础、风险自担可控；商用需要解决的多租户/计费/合规是完全不同量级的工程，硬塞进 MVP 会拖垮交付。

---

## 3. 硬约束：渠道自动化红线（第一性原理，决定产品天花板）

| 渠道 | 合规性 | MVP 处理方式 |
|---|---|---|
| **Email**（SMTP/Gmail） | ✅ 合法（守 CAN-SPAM + 退订） | 全自动，主力渠道 |
| **Web 搜索 / 网页深挖** | ✅ 合法 | 全自动（WebSearch + Jina 抓取） |
| **WhatsApp 冷发** | ⚠️ 违反 WA 政策；个人号批量易封 | 半自动：驱动本机 Chrome 的 WA Web，强制限速 + 人工确认，仅拉美有手机号的 |
| **Instagram / Facebook DM** | ⚠️ 违反 ToS，检测即封 | 半自动：CDP 驱动本机真实登录 Chrome，限速 + warmup + 人工节奏（沿用现方案） |
| **LinkedIn 自动私信** | ⛔ 违反 ToS，风控最严 | MVP **不做自动化**；只做"打开对方主页 + 复制话术"的辅助 |

**关键认识**：现在能发 IG/FB/WA 是因为"本机真实登录 + 小量 + 手动节奏"。这套**自用勉强可行**；一旦"给别人商用"= 要为客户封号负责且规模化必被平台风控打击。因此 Phase 1 把浏览器类渠道定位成**"人在环中的半自动助手"**，不是无人值守的群发机。这是产品的诚实边界。

---

## 4. 架构（模块边界清晰，可独立测试）

```
┌─────────────────────────────────────────────────────────┐
│                    Dashboard (React SPA)                  │
│  客户库表格 · Pipeline看板 · 战役运行器 · 统计 · 渠道健康  │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTP/JSON (REST)
┌───────────────────────────┴─────────────────────────────┐
│                  Backend API (FastAPI, Python)            │
│                                                           │
│  ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌─────────┐ │
│  │ Discovery  │ │ Enrichment │ │  Lead    │ │Outreach │ │
│  │  Engine    │→│  / Verify  │→│  Store   │→│ Engine  │ │
│  │            │ │            │ │ (dedup)  │ │         │ │
│  └────────────┘ └────────────┘ └────┬─────┘ └────┬────┘ │
│                                      │            │      │
│                                 ┌────┴────┐  ┌────┴────┐ │
│                                 │ SQLite  │  │Channel  │ │
│                                 │   DB    │  │adapters │ │
│                                 └─────────┘  └────┬────┘ │
└───────────────────────────────────────────────────┼─────┘
                                                     │
                      ┌──────────────┬───────────────┼──────────────┐
                      │ SMTP/Gmail   │  CDP Proxy → 本机 Chrome      │
                      │ (email)      │  (IG / FB / WA Web)          │
                      └──────────────┴──────────────────────────────┘
```

### 模块职责（每个：做什么 / 怎么用 / 依赖什么）

1. **Discovery Engine** — 输入关键词+市场+垂直细分，输出原始候选公司（域名/名称/来源URL）。依赖：WebSearch、Jina。做什么：跑关键词库、去噪。
2. **Enrichment / Verify** — 输入候选域名，输出验证后的联系信息。依赖：Jina 抓联系页 grep 邮箱、DNS/MX 校验、规则分类器（是否 LED 买家 / 是否制造商 / 国别判断）。**这是把当前"人工判断"沉淀成规则的地方。**
3. **Lead Store** — SQLite，唯一真相源。负责入库、**去重**（域名/IG/名称）、字段模板、标签。**替代 79 个 Python 文件链。**
4. **Outreach Engine** — 战役概念：选一批 leads + 选渠道 + 选模板 → 按渠道限速发送 → 写状态 → 检测回复。依赖：Channel adapters。
5. **Channel Adapters** — 统一接口 `send(lead, message, attachment) -> result`，各渠道一个实现：`EmailAdapter`(SMTP)、`IgAdapter`(CDP)、`WaAdapter`(CDP)、`FbAdapter`(CDP)。**复用现有 `email_sender_v58.py` / `ig_dm_vN_safe.py` / `wa_send_vN.py` 的核心逻辑。**
6. **Dashboard** — 可视化：客户库表格（筛选/搜索）、Pipeline 看板（prospect→queued→messaged→replied）、战役运行器（选人选渠道发）、统计（各国/各渠道触达数）、渠道健康（CDP 是否连上、Gmail 是否就绪、今日发送额度）。

---

## 5. 技术栈（🟡 待确认）

| 层 | 选型 | 理由 |
|---|---|---|
| 后端 | **Python + FastAPI** | 复用全部已有 Python 触达/抓取逻辑，零重写 |
| 数据库 | **SQLite** | 单用户本地零配置；一个文件；替代 79 文件链 |
| 前端 | **React + Vite + 轻量 UI 库** | "可视化看板"需要真正的交互界面 |
| 浏览器渠道 | **复用现有 CDP Proxy** (`~/.claude/skills/web-access/scripts/cdp-proxy.mjs`) 驱动本机 Chrome | IG/FB/WA 沿用已验证方案（含 Chrome 130+ `Input.insertText` 修复） |
| Email | **smtplib + Gmail App Password** | 沿用现方案，密码在 `~/.gmail_app_password` |
| 打包/启动 | 一条命令启动（`uvicorn` + 静态前端），本地浏览器打开 | Allen 非程序员，必须"双击即用" |

---

## 6. 数据模型（SQLite 初稿）

```
leads(id, company_en, company_local, country, region, city,
      website, email, phone, whatsapp_verified, instagram, facebook, linkedin,
      business_desc, target_fit, source_urls(json), created_at, updated_at)

campaigns(id, name, channel, template_id, status, created_at)

outreach(id, lead_id, campaign_id, channel, status,       -- prospect/queued/messaged/replied/excluded
         message_body, attachment, sent_at, reply_at, exclude_reason)

templates(id, name, channel, subject, body, attachment_path)
```

**迁移**：写一次性脚本把 79 文件链 + 4 个 pipeline JSON 导入 SQLite（~925 leads + 已发状态），保证历史触达不丢、不重发。

---

## 7. 分解为子项目 + 建议建造顺序

MVP 本身仍需拆，按"能独立验证、逐步可用"排序：

| # | 子项目 | 交付即可验证 | 依赖 |
|---|---|---|---|
| **S1** | Lead Store + 迁移脚本（SQLite + 导入 79 文件+pipeline） | 能查询/去重全部历史 leads | 无 |
| **S2** | Backend API 骨架 + 客户库只读看板（表格/筛选/统计） | 浏览器里看到全部客户和触达状态 | S1 |
| **S3** | Outreach Engine + EmailAdapter + 战役运行器 | 从界面选一批客户发邮件、状态自动更新 | S1,S2 |
| **S4** | Discovery + Enrichment 引擎（界面里输入关键词→出候选→一键验证入库） | 界面完成"搜索+深挖+入库"闭环 | S1,S2 |
| **S5** | CDP 渠道适配（IG/WA/FB 半自动发送 + 渠道健康面板） | 界面驱动本机 Chrome 发 IG/WA，含限速 | S3 |

每个子项目走独立的 spec→plan→实现 循环。**先做 S1+S2**（最快让 Allen 看到"我的客户库变成看板了"）。

---

## 8. MVP 完成定义（Phase 1 Done）

Allen 打开本地网页，能够：
1. 看到全部 925+ 历史客户 + 各渠道触达状态（看板）。
2. 输入关键词/市场/垂直细分，跑发现+深挖，验证后的新客户一键入库（自动去重）。
3. 选一批客户 + 选模板，一键发邮件；IG/WA 半自动发送（限速+人工确认）。
4. 看到统计与渠道健康，全程不碰命令行、不写脚本。

---

## 9. 待确认决策清单（🟡）

1. **产品定位**：自用版 MVP 优先？（推荐）还是别的？（§2）
2. **技术栈**：FastAPI + SQLite + React 可接受？还是想要更简单的（如无独立前端、服务端渲染）？（§5）
3. **MVP 渠道范围**：Email + IG + WA 三个够不够？FB/LinkedIn 是否 Phase 1 就要？（§3）
4. **界面语言**：中文界面？中英混合？
5. **是否现在就要**把商用多租户的架构约束写进 Phase 1（会增加工作量），还是 Phase 1 纯自用、商用完全后置？

---

## 10. 明确不做（YAGNI / Out of scope for Phase 1）

- 多租户、注册登录、计费系统 → Phase 2
- LinkedIn 自动私信 → 违反 ToS，只做辅助
- 无人值守大规模群发 → 违反平台风控，不做
- 移动 App → 本地 Web 足够
- AI 自动写个性化话术（可作为后续增强，非 MVP 必需）
