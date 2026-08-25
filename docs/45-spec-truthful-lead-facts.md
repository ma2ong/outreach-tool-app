# 45 — 客户资料只写"知道的事"，不写"搜索时假设的事"

## 触发这份 spec 的真实事故

Eidim（eidim.com）是加州 Fullerton 的 AV 系统集成商，页脚写着
`1015 S Placentia Ave, Fullerton, CA 92831` 和 `877.773.4346`。系统里它是：

- 国家：**South Korea**
- 电话：**+8777734346**
- 收到过一封**韩语**开发信（`한국 LED 디스플레이 납품 사례`）
- 它的自动回复（`hello+noreply@eidim.com`，正文写着 "Please DO NOT reply to this
  email"）被当成**真人回复**：lead 标记为已回复、跟进序列停掉、生成待处理任务、
  发件地址被收成联系人
- 打开客户详情时右下角报 `任务加载失败：Error: activities 500`

四条独立缺陷，同一个根子：**系统把"不知道"写成了"知道"**。

## 规则

### R1 国家是查出来的，不是搜出来的

`discovery.import_candidates(conn, candidates, default_country)` 用
`candidate["country"] or default_country` 落库，而 `default_country` 是搜索任务的
目标市场。这本身可以接受——前提是检测真的会先跑。事实上检测从未成功过：

- `enrich_domain()` 不看网页里的地址，只产出邮箱/电话/社媒；
- `screening.detect_country()` 只认国际区号和 ccTLD，而北美客户是 `.com` +
  本地格式电话。

于是全部 966 条 lead 的国家实际等于"当初搜的哪个市场"。

规则：

1. `enrich_domain()` 从抓到的页面文本判定国家，写进候选的 `country`。
2. `screening.detect_country()` 的优先级是
   **国际区号 → 页面地址 → ccTLD → 邮箱 ccTLD**。
   区号排第一不能动：`+86` 是识别同行工厂最强的信号，一个中国工厂的美国办事处
   地址不能把它洗白成美国客户。
3. `+1` 不再判定国家。`1` 区号覆盖美加两国，写死其一就是猜；美国客户由
   `CA 92831` 这样的"州 + ZIP"判出，加拿大客户由 `.ca` 或 `ON M5V 3L9` 判出。
   `USA/Canada` 这个既不是国家也不能参与目标市场比对的值就此消失。
4. 目标市场校验（`qualify_for_auto_import`）因此第一次真正生效：搜韩国市场时
   检出为 USA 的候选**不导入**，也就不会收到韩语开发信。

### R2 本地格式电话不是国际号码

`extract_phones()` 把 `tel:877.773.4346` 归一成 `+8777734346`——凭空造了个国家码。
`screening` 专门写过防线（`(866) 738-3580` 不能读成 `+86` 中国），这一步把防线绕开了。

规则：只有原文自带 `+` 或 `00`，或来自 wa.me / WhatsApp API 链接（WhatsApp 号码
必然是国际格式），才输出 `+` 前缀；其余保持原样的本地写法。

### R3 自动回复不是回复

邮件通道没有自动回复识别，社交通道有（`inbound.is_auto_reply`）。一封自动回执
被当成真人回复的代价，`inbound.py` 里已经写明：跟进序列被永久停掉，而实际上根本
没有人读过这封信。

规则：一封邮件满足任一条件即判为自动回复——

- `Auto-Submitted` 头不是 `no`，或 `Precedence: auto_reply/bulk/junk`，
  或带 `X-Autoreply` / `X-Auto-Response-Suppress`（RFC 3834，最可靠）；
- 发件地址是不可投递地址（`noreply@` / `no-reply@` / `donotreply@`，含
  `hello+noreply@` 这类子地址写法）；
- 正文/主题命中 `inbound.is_auto_reply` 的措辞模式。

判为自动回复时：`kind='auto'` 存进收件箱**照常可见**，但

- 不 `mark_replied`（跟进序列继续）
- 不建待处理任务
- 不把发件地址收成联系人

不可投递地址在任何自动路径上都不得成为联系人，即使那封信被判成了真人回复。

### R4 读接口不做写迁移

`GET /api/activities` 每次都调 `task_ownership.backfill()`，它内部对
`agent_proposals` 全表逐行 `UPDATE`。嵌入式 Sales Worker 正在写库时，读请求就
`database is locked` → 500 → 整个任务列表和客户详情的任务区打不开。

规则：

1. `_legacy_provenance()` 先查出确实需要修的行，没有就不开写事务——稳定状态下
   backfill 是纯读操作。
2. backfill 遇到 `database is locked` 时安静跳过并返回 `skipped`，读请求照常返回
   数据。归属修复晚一次没有代价，任务列表打不开有。

## 验证

- `tests/test_screening.py`：Eidim 页脚文本判为 USA；`+1` 不判国家；`.ca` 判
  Canada；中国工厂的美国地址仍判 China。
- `tests/test_enrich.py`：`tel:877.773.4346` 输出本地格式，不是 `+8777734346`；
  `enrich_domain` 返回 `country`。
- `tests/test_discovery.py`：搜韩国市场时，检出 USA 的候选被 `qualify_for_auto_import`
  拒绝，理由是目标市场不符。
- `tests/test_replies.py`：Eidim 那封自动回复不停跟进、不建任务、不建联系人，
  但在收件箱里可见。
- `tests/test_activities_api.py`：库被别的连接锁住时 `GET /api/activities` 返回 200。
