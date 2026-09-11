# 128 — 没人调用的那张渠道表

[docs/70](70-spec-discovery-channels.md) 把渠道做成了声明，[docs/126](126-spec-two-browsers-many-channels.md)
又往里注册了 Google、Bing、Naver 博客三条浏览器渠道。2026-09-11 查了一遍调用方：

```
grep -rn "gather" backend/app --include=*.py   # 只有 discovery_sources.py 自己
```

**`gather()` 没有任何调用方。** 关键词搜索——界面上的「搜索深挖」和 Agent 夜里的自动开发——
两条路都走 `discovery.run_discovery`，而它的默认 `search_fn` 是 `search.search_domains`，
只有 DuckDuckGo 一家。渠道表从建起来那天到今天，只被 `status()` 读过，用来在报告里显示
「哪条渠道没配好」。

所以 docs/70 和 docs/126 都只完成了一半：渠道**声明**了，但没人按这张表去问。
Naver 网页搜索——2026-09-10 实测唯一一条能稳定产出韩国买家的免费渠道——写好了，
放在表里，一次也没被关键词搜索用过。

这份 spec 把表接上，并交代 Playwright 这条读法实测下来到底值多少钱。

## 2026-09-11 实测：Playwright 在每条渠道上的成绩

headless Chromium，同一台机器，英文 `LED display distributor` / 韩文 `LED 전광판 유통업체`：

| 渠道 | Playwright headless 结果 | 结论 |
|---|---|---|
| Naver 网页 | 10 家真实韩国公司（pst24.co.kr、ganpanlab.kr、kioskkorea.kr、rayled.net…） | jina 已经能读，**不加读法** |
| Naver 博客 | 链接里仍然只有 naver 自己和 3 个广告位 | 公司名在正文，**仍归 browser-use** |
| Google | `Our systems have detected unusual traffic` | 见 R2 |
| Bing | 10 条，但见下 | **不上**，见「不做的事」 |
| Instagram | 811 字节登录墙 | 需要采集账号，见 R4 |
| Facebook | `Not Found`（9 字节） | 需要采集账号，见 R4 |

### Google 挡的不是浏览器，是这台机器

docs/126 的对照表写着 Google 可以「✅ 兜底」——那一行是推的，不是测的。今天补测：

| 读法 | 结果 |
|---|---|
| `jina.fetch` | 704 字节 `This page maybe requiring CAPTCHA` |
| Playwright headless | `unusual traffic from your computer network` |
| **真实 Chrome 窗口**（`channel="chrome", headless=False`，跟 browser-use 同一种启动方式） | **同样是异常流量页**，`IP 地址：23.254.150.216` |

三种读法全军覆没，而且第三种就是 browser-use 用的那种。**拦截发生在出口 IP 上，
换浏览器不解决问题**，browser-use 那 85–121 秒会烧在同一堵墙上。

### Bing 会在答不上来的时候回答另一个问题

Bing 的结果链接 `href` 全是 `bing.com` 的跳转地址，真实域名写在 `cite` 行里，
换成读 `cite` 就能拿到 10 条——技术上通了。然后是这个：

| 查询 | Bing 返回的前 5 条 |
|---|---|
| `LED display distributor` | eagerled.com、alibaba、hola-led.com、ledvstar.com、unit-led.com |
| `LED screen reseller Mexico` | wikipedia《Light-emitting diode》、merriam-webster、britannica、tech-led.com、amazon |
| `LED 전광판 유통업체` | **与上一行一字不差** |

后两个查询——一个西语市场、一个韩文——拿到了完全相同的十条「LED 是什么」科普页。
换 fresh context 一样，重复两次一样。**它没有报错，没有返回空，它返回了另一个问题的答案**，
而 tech-led.com、hackatronic.com、engineerfix.com 这三条能通过 `is_company_site`，
会被当成客户候选导进来。

至于它答得上来的那次：eagerled、hola-led、ledvstar、unit-led、linsnled、ledful、idisplayled
——**七家中国 LED 厂，同行**。这正是 docs/126 给 DuckDuckGo 记下的那笔账。

**答对时给同行，答不上时给别的问题的答案。** 所以 Bing 不上。

## R1 关键词搜索走渠道表

`run_discovery` 的默认 `search_fn` 从「DuckDuckGo 一家」换成 `discovery_sources.gather`。

不传渠道名时，`gather` 只跑 `unattended=True` 的渠道（docs/126 R5 的守卫原样生效），
也就是 DuckDuckGo + Naver 网页 + 配了密钥的 Naver API。Agent 夜里那条路因此天然
够不到任何会弹窗的读法，**这条保证来自 gather 本身，不是调用方的自觉**。

要跑浏览器渠道，必须由界面显式点名——那是 Allen 按按钮，不是定时器。

每条候选带着**发现它的那条渠道**进库：`_enrich_candidates` 以前给一次搜索里的所有候选
盖同一个 `"搜索"` 标签，现在渠道自己写的 `source` 优先。哪条渠道产出买家、哪条产出同行，
只有留痕了才能在三个月后回答。

## R2 被挡住要说被挡住，不能返回 0 家

Google 今天在这台机器上返回的是一面墙。三种读法都返回「0 家公司」，而 0 家的含义是
「这个关键词在 Google 上没有客户」——完全不是事实。

任何按结果页读的渠道，识别到搜索引擎的反自动化页面（`unusual traffic` / `异常流量` /
`CAPTCHA` / `not a robot`）时，报**失败并带上原因**，不返回空结果。

一条没配好的渠道、一条被挡住的渠道、一条真的没搜到东西的渠道，在界面上必须是三回事
（docs/70 R4 说的是前两件，这条补第三件）。

## R3 Playwright 是第三种读法，有自己的采集身份

`playwright_engine.py` 用 `~/.outreach-tool/browser/<channel>`，里面是 WhatsApp /
Instagram / Facebook 的**发送登录态**。采集不许碰它，它有自己的
`~/.outreach-tool/scrape/<channel>`（docs/126 R4）。

采集跑在独立子进程里，用的是服务器同一个解释器但不共享 `PlaywrightEngine` 那个工作线程：
发送那条路上的浏览器出任何问题，都不该是采集引起的，反过来也一样。

理由 docs/126 R4 已经写过，这里只补一句实现层面的：**两套 profile 目录不同还不够，
进程也要不同**——同一个 profile 目录被两个 Chromium 同时打开就是 `exitCode=21`，
`playwright_engine._kill_stale_browser` 那段注释记的就是这个坑。

## R4 Instagram / Facebook：注册，然后说清楚怎么开通

两条渠道现在就进表，读法声明 `playwright`。`~/.outreach-tool/scrape/<channel>` 里
没有登录态时，它报的是「未启用：需要先登录采集专用账号」并说明怎么登，
不是异常、不是重试、不是空结果（docs/126 R6）。

选择器是**未经实测的**：没有采集账号就打不开那两个页面，而这套系统的规矩是
不写不能验证的东西。所以这两条渠道的读法逻辑用假页面做了单元测试，
真实选择器等 Allen 登录一个可以赔的账号之后按实测改。在那之前渠道是「未启用」，
一行未验证的选择器也执行不到。

## R5 读法由渠道声明，API 按声明校验

`/api/discover` 和 `/api/discover/page` 收到一条渠道没有声明的读法时报 400，
而不是默默降级成默认读法。docs/126 验收第 1 条，这份 spec 把它实现了。

## 不做的事

- **不上 Bing**。理由在上面的实测表里：答对时给同行，答不上时悄悄给别的问题的答案
- **不给 Naver 网页加 Playwright 读法**。jina 免费、无人值守、今天就在产出韩国买家，
  加一条更贵的读法读同一页，是给没坏的东西换零件
- 不因为 Google 今天被挡就把它从表里删掉。IP 会变，换网络就可能通；它现在的正确行为
  是报「被 Google 判定为异常流量」，不是消失
- 不给 Instagram / Facebook 写此刻验证不了的真实选择器（R4）
- 不让任何 `browser`/带登录态的 `playwright` 读法进调度器（docs/126 R5 不变）

## 验收

1. `gather` 有调用方：`/api/discover` 的关键词搜索经由它，不指定渠道时只跑
   `unattended=True` 的渠道
2. 候选行带着发现它的渠道名进导入面板，不再全部盖成「搜索」
3. 结果页出现反自动化拦截时，该渠道报失败并带原因，不返回空结果
4. 采集用的 profile 目录在 `~/.outreach-tool/scrape/` 下，且任何采集代码路径都不会打开
   `~/.outreach-tool/browser/` 下的目录
5. Instagram / Facebook 在没有采集登录态时报「未启用」并说明怎么登
6. 指定一条渠道没有声明的读法，API 报 400
