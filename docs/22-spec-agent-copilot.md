# Spec 22 — 销售助手 Agent：提议、审批、逐步放手

> 状态：A 期 Implemented / B·C 期 Planned
> 日期：2026-08-19
> 范围：A 期（会说话）/ B 期（会自己动）/ C 期（会学），按序实施
> 代码：`backend/app/agent/`（llm / proposals / executors / classify / draft / memory / run）、
> `backend/app/api/agent.py`、`frontend/src/components/AgentPanel.tsx`

## 1. 要解决的问题

系统已经把 `客户 → 联系人 → 触达 → 回复 → 任务 → 商机 → 报价 → 订单` 全链路做完，
但每一环都要人去点。Allen 本人是这条链上唯一的调度器和唯一的写手：

1. **判断没人做。** 今天先跟谁、哪条商机该救、哪个 Campaign 该停，全靠脑子记。
2. **对话没人写。** 客户一回复工具就哑了——全库没有一处大模型调用，模板变量只够发第一封。
3. **记忆只有字段。** 有备注时间线，没有"这家客户的故事"，换个月份就想不起上次聊到哪。

## 2. 设计原则

- **Agent 提议，Allen 决策。** 现阶段任何对外产生后果的动作都不由 Agent 自己拍板。
  它的产物是**提议**，进审批队列；Allen 是唯一按下确认的人。
- **自主度是旋钮，不是开关。** 每类动作独立分三档 `off / propose / auto`，
  出厂全部 `propose`。某类动作连续跑准了，Allen 手动把那一格调到 `auto`，其余不受影响。
  放手是逐格进行的，且随时可以调回来。
- **Agent 不新开执行路径。** 提议获批后调用的是现有函数（`outreach` / `activities` /
  `sequences` / `opportunities`），因此单批 20、日限 40、同客户每日一次、无效邮箱跳过、
  `do_not_contact` 全渠道排除这些护栏**自动继承**，不需要在 Agent 层重写，也无法被绕开。
- **每句外发的话都要能追到来源。** 沿用 `brief.py` 的底线：客户官网原文、客户自己说过的话、
  产品库、已发报价——四个来源之外的事实一律不许出现。价格、交期、产能、认证、客户案例，
  模型不得自行生成。
- **决策必须留痕。** 每条提议都记下"为什么现在做这件事"和依据；Allen 的批准/驳回/修改
  同样入库。这份记录既是事后追责的凭据，也是 C 期唯一的训练数据来源。
- **不确定就问，不装懂。** 模型对意图判断没把握时输出 `unclear` 并说明缺什么，
  不允许猜一个凑数。

## 3. 审批脊柱（A/B/C 共用，先建）

### 3.1 `agent_proposals`

| 字段 | 说明 |
|---|---|
| `id` / `created_at` | |
| `kind` | `reply_draft` / `send_outreach` / `create_task` / `enroll_sequence` / `stop_sequence` / `discover_run` / `build_opportunity` / `mark_do_not_contact` |
| `lead_no` / `contact_id` / `opportunity_id` / `inbox_message_id` | 关联对象，按 kind 取用 |
| `title` | 一句人话：给谁、做什么 |
| `reasoning` | 为什么是现在、为什么是这个动作 |
| `evidence` | JSON 数组，每项 `{type, text, source}`；来源限官网 URL / 客户原话 / 库内字段 / 产品库 |
| `payload` | JSON，执行参数（草稿正文、任务标题与日期、序列 id 等） |
| `risk` | `low` / `medium` / `high` |
| `status` | `pending` / `approved` / `edited_approved` / `rejected` / `executed` / `failed` / `expired` |
| `decided_at` / `decided_by_note` | Allen 驳回的理由，或改动后的最终内容 |
| `executed_at` / `execution_result` | |
| `model` / `tokens` | 成本可查 |

`pending` 超过 7 天自动 `expired`——隔一周才发出去的回复已经没有意义，
让它烂在队列里比过期更糟。

### 3.2 自主度设置

`settings` 键 `agent_autonomy_<kind>`，值 `off | propose | auto`，默认 `propose`。

- `off`：这类动作压根不生成。
- `propose`：生成提议，等人批。
- `auto`：获批环节跳过，直接执行，但**照样写一条 `status='executed'` 的记录**，
  Allen 事后能看它干了什么。`auto` 只能手动开启，任何新增 kind 一律从 `propose` 起步。

### 3.3 审批界面

新增「Agent」页面，一屏解决：

- 顶部：今天有多少待批、Agent 上次运行时间与结果、本月模型花费；
- 提议流：按 `risk` 和时效排序，每条展开可见 `title / reasoning / evidence / payload`；
- 三个动作：**改后确认**、**直接确认**、**驳回**（驳回必须选一个理由，理由进 C 期）；
- 批量确认仅对 `risk='low'` 开放，中高风险逐条过。

回复草稿同时出现在收件箱页对应的那条回复下方，不用跳页。

## 4. A 期 · 会说话

### 4.1 触发与范围

`replies.py` 落库一条 `kind='reply'` 的真人回复后入队处理。

- **邮件**：有完整正文 → 分类 + 起草。
- **WhatsApp / Instagram**：`inbound.py` 只抓得到会话列表的一行预览，没有全文
  （刻意不点开对话，避免清掉手机上的未读）→ **只分类、只提醒，不起草**。
  预览不足以支撑一封负责任的回复，凭半句话编出的回复正是本 spec 要防的东西。

现有的确定性判断（退信、退订、自动回复识别）优先级高于模型分类，模型不得覆盖。

### 4.2 意图分类

`inquiry` 泛询盘 / `spec` 要参数 / `quote` 要正式报价 / `sample` 要样品 /
`negotiation` 已有报价后砍价 / `referral` 转介绍 / `reject` 明确拒绝 / `unclear` 判断不了。

分类名不得语义重叠。实测中 "send price for 200sqm P2.5" 曾在 `quote` 和 `price` 之间
摇摆，因此砍价档改名 `negotiation` 并以"是否已发过报价"作为与 `quote` 的判据。

用 Haiku 跑（量大、便宜）。分类结果写回 `inbox_messages`，同时决定后续动作：
`reject` → 提议置 `do_not_contact`；`quote`/`sample` → 提议建商机 + 建任务；其余 → 提议草稿。

### 4.3 草稿生成

上下文包（喂给 Opus）：

- 这家公司的 `brief` / `hook` / 国家 / 城市 / ICP 分级；
- 我方发过的全部消息（含模板渲染后的实际文本）；
- 客户的全部历史回复；
- 商机字段（尺寸、像素间距、室内外、用途、数量、贸易条款）；
- 已发报价与产品库标准五档 P0.7–P10。

硬约束写进 system prompt：

- 语言跟随客户来信，但只输出英语或韩语（沿用现有对外语言约定，西语/葡语客户用英语）；
- 产品型号统一写 `P0.7–P10 indoor and outdoor LED panels`；
- 价格、交期、MOQ、产能、认证、客户案例**只能引用上下文里出现过的值**，
  没有就写"确认后回复"，不许估、不许约等于；
- 不用 email 署名格式（社媒场景），不提公司名，只说 from Shenzhen China；
- 每个事实点在 `evidence` 里标注来源，界面上可展开核对。

产物落 `agent_proposals`（`kind='reply_draft'`, `risk='medium'`）。

### 4.4 客户记忆

新增 `lead_memory` 表：`lead_no` 唯一，一段 ≤200 字的 running summary
（他们是谁 / 要什么 / 卡在哪 / 下一步说什么 / 有什么忌讳）+ `updated_at` + `source_count`。
每次新回复或成交状态变化后重写。它是所有后续 prompt 的第一段上下文，
也是 Allen 打开客户抽屉时第一眼看到的东西。

### 4.5 A 期验收

1. 一条真实询盘邮件进来，5 分钟内收件箱出现带意图标签的草稿，依据可展开核对；
2. 草稿里出现的任何价格/交期都能在上下文里找到出处，找不到就是缺陷；
3. 「改后确认」发出去的内容与界面所见完全一致，且走的是现有发送路径（限速、日额度生效）；
4. WA/IG 回复只出现意图标签和提醒，不出现草稿；
5. `agent_autonomy_reply_draft=off` 时全链路静默，系统行为与今天完全一致。

## 5. B 期 · 会自己动

`backend/app/agent/loop.py`：每天早上（09:00 窗口内）跑一次，读世界状态 → 出「今日计划」。

**世界状态**（全部来自现有查询，不新增采集）：未处理回复数、逾期与今日任务、
停滞商机、各渠道剩余额度、未触达且 A/B 级的客户数、近 7 天回复率、就绪中心告警。

**输出**：一组 `agent_proposals`，构成当天的行动计划。首页新增「今日计划」卡，
Allen 一屏批完就是一天的工作。

**工具白名单**：模型不接触数据库，只能调受限工具集
（`draft_reply` / `create_task` / `enroll_sequence` / `stop_sequence` / `discover_leads` /
`build_opportunity` / `propose_send`），每个工具都是现有函数的薄封装。

**日报**：当天收工时推一条飞书消息——发了什么、收到几个回复、Agent 处理了几条、
还有几条等你定、新建了什么商机。

## 6. C 期 · 会学

唯一的训练信号是 Allen 的决定：**驳回理由**和**改稿前后的 diff** 比任何评分都准。

- 累积到一定量后，把「被改过的草稿对」作为 few-shot 注入草稿 prompt；
- 按 Campaign / 国家 / 话术统计真实回复率，自动提议停掉跑不动的序列；
- 用成交与丢单结果回头校准 ICP 分项权重（只提议调整，不自动改分）。

## 7. 明确不做

- 不自动加好友、不自动开启新的 WA/IG 会话（ToS 风险，现有规矩不变）；
- 不自动发正式报价、不自动承诺交期与价格；
- 不自动修改客户主数据（只能提议）；
- 不为了让模型看到全文而去点开社媒对话（会清掉手机未读，且提高封号风险）。

## 8. 模型接入与成本

**不需要 ANTHROPIC_API_KEY。** 本机已安装并登录 Claude Code CLI
（`~/.claude/.credentials.json`），后端以子进程方式调用
`claude -p ... --output-format json --strict-mcp-config`，复用现有订阅登录态。
已实测：Python 子进程、`stdin=DEVNULL`、无终端环境下正常返回，
因此开机自启的后台服务里可用。

`agent/llm.py` 抽象三个后端，上层分类与草稿逻辑不感知后端差异：

| 后端 | 取值 | 凭据 | 说明 |
|---|---|---|---|
| Claude Code CLI | `cli` | `~/.claude/.credentials.json` | 零额外花费，消耗订阅额度 |
| DeepSeek | `deepseek` | `backend/deepseek_key.txt`（gitignore） | OpenAI 兼容接口，`base_url=https://api.deepseek.com`，模型 `deepseek-chat`；国内直连稳定，便宜一个数量级 |
| Anthropic API | `api` | `backend/agent_key.txt`（gitignore） | 需要高并发或稳定延迟时再切 |

**按任务分派后端**，而不是全局二选一。`settings` 两个键：

- `agent_llm_backend_classify`，默认 `deepseek` — 意图分类与客户记忆摘要。量最大、
  最吃额度，但任务最简单（八选一），弱模型足够。走 DeepSeek 可以让 Agent 几乎不消耗
  Allen 本人的 Claude Code 额度。
- `agent_llm_backend_draft`，默认 `cli` — 回复草稿与 B 期今日计划。量小、订阅内免费，
  且是唯一直面客户的输出。第 2 节「每句外发的话都要能追到来源」是一条**否定性约束**
  （没有就写待确认，不许估），对指令服从度要求最高，韩语输出同理，因此不下放给弱模型。

任一后端不可用时，只有依赖它的那类任务静默，另一类照常工作。

**送云端的数据。** 走任何云 API 都意味着数据出本机，这与隧道跑在本地的初衷相悖，
Claude 与 DeepSeek 同理，差别只在条款（Anthropic API 默认不用 API 数据训练；
DeepSeek 需自行确认当前条款）。因此：分类请求**只送脱敏后的回复正文**——
去掉公司名、邮箱、电话、URL，分类准确率不受影响；草稿请求需要完整上下文，
只走 `cli` 后端。

**CLI 后端的已知代价，实现时必须处理：**

1. **额度与本人共用。** 设每日调用上限（`agent_daily_call_limit`），超限停当天并在
   Agent 页面显示原因，避免 Agent 把 Allen 自己的 Claude Code 额度吃光。
2. **登录会过期。** 就绪中心新增一项检查：CLI 是否仍可用。过期时明确报
   "Agent 需要重新登录 Claude Code"，不允许静默失效。
3. **每次约 3 秒且并发不可控。** 全部走后台任务，页面不做同步等待。
4. **每次调用约 12k token 固定开销**（全局 `CLAUDE.md` + 基础系统提示）。
   1 小时内命中缓存，因此**分类必须批处理**——攒一批一次跑完，不允许来一条跑一次。

CLI 后端下草稿与计划走 Opus。所有后端都不可用时 Agent 整体静默，系统退回今天的行为。


## 9. A 期实现记录（2026-08-19）

已实现并实测：

- 审批脊柱 `agent_proposals` + `lead_memory`，自主度旋钮出厂全 `propose`，
  `auto` 仍写执行记录，指纹去重，`pending` 满 7 天自动 `expired`。
- 执行器只接 A 期四类（reply_draft / create_task / build_opportunity /
  mark_do_not_contact），B 期四类未接执行器时**显式失败**而不是静默通过。
- 回复走出去的地址：新增 `inbox_messages.mailbox_email`，回信从客户当初写信的那个
  邮箱发出，取不到才回落轮换。
- 分类脱敏后再出网（邮箱/电话/URL/公司名替换为占位符）。
- 草稿护栏：`draft.check_claims` 扫价格/交期/MOQ/质保数字，上下文里查不到就把提议
  升到 `high` 并在理由里加 ⚠。
- 就绪中心新增两项：Agent 模型接入（登录过期会明说）、Agent 待审批数。
- 测试 541 项全绿（新增 40 项）。

**实测（DeepSeek 分类 + Claude CLI 起草）**：三封回复分别判为
quote / reject / spec（含韩语），把握 85–95；一封索要 P4 报价和交期的邮件，
草稿明确拒绝给出未经确认的价格与交期，改为承诺确认后回复，并反问固装还是租赁——
四条 evidence 全部可追溯到官网笔记、客户原话或产品范围。

**已知边界**：外发正文没有留档（`send_log` 只记 campaign 标签），
所以草稿上下文里"我们发过什么"只有标签和日期，没有原文。
