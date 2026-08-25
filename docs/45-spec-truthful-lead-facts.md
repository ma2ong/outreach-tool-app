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

规则：GET 请求保持只读。归属迁移属于启动流程和 Worker，不属于页面刷新。

这条规则由 PR #11（`ab3d5ed` / `c30396a`）实现，与本 spec 的其余修复并行发生。
本 spec 只补一条回归测试：Worker 持有写锁时，任务列表和统计接口仍必须返回 200。

### R5 公司名不是页面标题

`extract_company_name()` 只拒绝完全等于 "Contact" 的标题，于是
"Contact PixelFLEX" 整条进了客户库——八条记录如此。

规则：标题里的 "Contact" / "Contact Us" 前缀和页面标签段落一律不作为公司名的一部分；
`Contact Us | Impact LED` 取后半段。代价是真名以 Contact 开头的公司会被截断，
在一个 LED/AV 客户库里这笔交换是划算的。

### R6 序列的语言就是发送条件

`enroll_leads` 只挡重复入组和已回复的客户，不看序列写的是什么语言。入组要点两次
（选客户、点序列），而选择在第一次点击后不会清空——2026-08-13 同一批 50 家巴西、
智利、哥伦比亚客户先进了英语序列，紧接着又进了韩语序列，并在那里排了十二天队。

规则：韩语序列只接受韩国客户。反向不限制——英语是这行的工作语言，韩国客户读英文
开发信是正常的。语言判定读序列自己的正文，不读序列名。

被语言规则拒绝的客户要单独报出来，不能混进"已在其中或已回复"的数字里：那会让人
以为是重复入组而再点一次，而不是去换一个序列。前端入组后清空选择。

## 验证

- `tests/test_screening.py`：Eidim 页脚文本判为 USA；`+1` 不判国家；`.ca` 判
  Canada；中国工厂的美国地址仍判 China。
- `tests/test_enrich.py`：`tel:877.773.4346` 输出本地格式，不是 `+8777734346`；
  `enrich_domain` 返回 `country`。
- `tests/test_discovery.py`：搜韩国市场时，检出 USA 的候选被 `qualify_for_auto_import`
  拒绝，理由是目标市场不符。
- `tests/test_replies.py`：Eidim 那封自动回复不停跟进、不建任务、不建联系人，
  但在收件箱里可见。
- `tests/test_activities_api.py`：Worker 持有写锁时 `GET /api/activities` 返回 200。
- `tests/test_enrich.py`：`# Contact PixelFLEX` 读作 `PixelFLEX`，`# Contact Us` 仍是 None。
- `tests/test_fix_invented_country_codes.py`：只改能确证的号码，`+82 2 510-2000` 不动。
- `tests/test_sequences.py`：巴西客户进不了韩语序列，韩国客户进得了；韩国客户仍可进英语序列。
