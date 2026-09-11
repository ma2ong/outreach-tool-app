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

## R4 Facebook 不需要账号：公共主页是公开的

先写的这份 spec 把 Instagram 和 Facebook 归成一类——「都要登录，所以都先注册成未启用」。
2026-09-11 补测推翻了 Facebook 那一半：

| 读什么 | 未登录的真实浏览器 |
|---|---|
| `facebook.com/search/pages/?q=…` | `Not Found`（9 字节）——**死的只有 FB 自己的搜索** |
| `facebook.com/<主页>` | 700 字节：主页名、粉丝数、类目、城市、简介 |
| **`facebook.com/<主页>/about`** | **网站域名 + 邮箱 + 电话 + 地址** |

实测四家：GCL Electronics → `gcled-usa.com` / info@gcled-usa.com / +1 469-686-1719；
LED3 → `led3.us` / clare@led3.us；LED Distribution（波多黎各）→ `leddistributionpr.com` /
+1 787-246-8899；第四家主页受限，返回「This content isn't available right now」——
那是一个答案，不是一个空结果。jina 读同样这几个地址全部撞登录墙，
所以这条路必须是浏览器，但**不必是登录的浏览器**。

找主页那一步也不用 FB：`site:facebook.com <关键词>` 丢给 DuckDuckGo 就能列出主页地址，
而 DuckDuckGo 免费、无人值守、今天就在跑。

于是 Facebook 这条渠道：**不需要账号，没有封号风险，headless 不弹窗，因此可以进调度器**
（`unattended=True`）——这是唯一一条靠浏览器才能读、却仍然无人值守的渠道。

只有域名过界（docs/124 R1 不变）：About 页上的邮箱和电话不落库，联系方式仍旧由
`enrich_domain` 读公司自己的官网得到。多带的一样东西是主页 handle，
它让这家公司一进库就有了 FB 私信的地址。About 页上没有网站的主页，不产生候选。

## R5 Instagram：注册，然后说清楚怎么开通

Instagram 的搜索页未登录只有一面登录墙（811 字节），没有 Facebook 那样的公开 About 页，
所以它现在就进表、读法声明 `playwright`，而 `~/.outreach-tool/scrape/instagram` 里
没有登录态时，它报的是「未启用：需要先登录采集专用账号」并说明怎么登，
不是异常、不是重试、不是空结果（docs/126 R6）。

登录用的必须是一个**可以赔的小号**，不是发私信那个账号。理由在 docs/126 R4：
平台封的是账号不是目录，而采集的浏览特征比发信重得多；发信账号被封，
在谈的对话和联系人一起没。

交接方式：**密码不进这套系统**。渠道页的「登录采集账号」弹出一个开在
`~/.outreach-tool/scrape/instagram` 上的浏览器窗口，Allen 在窗口里自己登录，
关掉窗口时登录态落盘。服务器不收任何凭据，也没有任何接口接受凭据。

### 登录这一步不能由程序驱动的浏览器来做

2026-09-11 一路测下来，这条是硬的：

| 试的东西 | 结果 |
|---|---|
| Playwright 自带 Chromium | 登录被推进 Meta 验证码页，**验证码不渲染**，只剩一个 logo |
| Playwright + 真实 Chrome + 去掉 `--enable-automation` | `navigator.webdriver` 已经是 false、品牌已经是 Google Chrome，**照样空白** |
| reCAPTCHA 官方演示页（同一个窗口） | **正常渲染**，资源全 200，零失败请求 |
| Allen 自己的 Chrome 无痕窗口（同一台机器、同一个 IP） | **验证码正常，登得进去** |

浏览器不背锅，网络不背锅，IP 也不背锅——同一个 IP 上普通 Chrome 能登。
剩下的唯一变量是**这个浏览器被 CDP 接管着**，而那不是一个可以关掉的开关：
Playwright 就是靠它工作的。账号本身也排除了，是用了两三年的成熟号。

所以规矩是：**登录用一个普通的 Chrome 进程，不带任何自动化**——
`chrome.exe --user-data-dir=~/.outreach-tool/scrape/instagram`，一个进程参数而已，
没有 Playwright、没有 CDP、没有自动化标记。Allen 在里面像平时一样登录，关掉窗口，
登录态落在我们自己的采集目录里。之后采集再用 Playwright 打开这个目录——
**带着已经建立的会话去浏览，和从零登录不是同一件事**。

这也解释了为什么发私信那个账号一直好好的：它当初也不是在自动化窗口里登的。

### 如果连普通窗口也登不进去：把 Allen 自己登好的那份资料接过来

实测下来还有一层：换成完全没有自动化的普通 Chrome 之后，验证码过了，
Instagram 却回「你输入的登录信息有误」。这句话在 Meta 那里既可能是字面意思，
也可能是婉拒，从外面分不出来。

所以留第二条路，**不要求在这台机器的新窗口里建立会话**：Allen 在自己的 Chrome 里
「添加个人资料」，在那份资料里像平时一样登录，然后系统把**那份资料整份复制**到
`~/.outreach-tool/scrape/<channel>`。

这条路成立是实测过的（2026-09-11）：一份复制过来的 Chrome 资料，
在**没有访问任何页面之前**就已经带着原资料的 `datr` / `mid` / `ig_did` / `csrftoken`，
浏览器自己能解密。前提是 `Local State` 一起复制——cookie 的加密密钥在那个文件里，
少了它复制过来的是一堆解不开的字节。

约束两条：复制时 Chrome 必须全部关闭（开着时 cookie 文件是锁的，复制出来是半份），
以及**选哪份资料由 Allen 决定**——系统分不出哪份是小号、哪份是他本人的，
而这正是 docs/126 R4 在乎的那件事。

登录窗口用的是**真实 Chrome**，并去掉 `--enable-automation`。实测 2026-09-11：
Playwright 自带的 Chromium 在页面里 `navigator.webdriver === true`、
品牌报 "Chromium"，Instagram 因此把登录挡进验证码页——而那个验证码**根本不渲染**，
屏幕上只剩一个 Meta logo。真实 Chrome 去掉自动化标记后 `navigator.webdriver === false`、
品牌报 "Google Chrome"。recaptcha 的资源本身是通的（实测 200），挡人的不是网络。

headless 的读法保持原样（Facebook 公共主页就是用自带 Chromium 测通的）：
**有人要看、要打字的窗口才需要这身衣服**。

「登录了没有」的判据是**平台的 session cookie**，不是目录里有没有东西：
Chromium 一启动就写 `Default/`，按目录判断会把每一个开过一次的 profile 都算成已登录。
状态分三种——已登录 / 等待登录（窗口开着，cookie 还没落盘）/ 未登录——
因为这三种对应三种不同的下一步。

选择器是**未经实测的**：没有采集账号就打不开那两个页面，而这套系统的规矩是
不写不能验证的东西。所以这两条渠道的读法逻辑用假页面做了单元测试，
真实选择器等 Allen 登录一个可以赔的账号之后按实测改。在那之前渠道是「未启用」，
一行未验证的选择器也执行不到。

### 登进去之后：会话在被驱动的浏览器里是有效的

这是这条链上最后一个未知数，2026-09-11 实测答了：Allen 在普通 Chrome 里登好、
系统用 Playwright 打开同一个 profile，**首页是他的信息流，导航和自己的主页链接都在，
没有登录表单**。所以那条界线很清楚——

> **建立会话必须在没有程序驱动的浏览器里；带着会话去浏览没有这个限制。**

Instagram 的读法由此确定，两步都是实测出来的：

| 想读什么 | 能用的路 | 不能用的路 |
|---|---|---|
| 搜账号 | 页面内调 `/api/v1/web/search/topsearch/`（带 `X-IG-App-ID`） | `/explore/search/keyword/?q=` 只渲染 607 字节，没有结果 |
| 拿官网 | 打开主页读 bio 外链，解开 `l.instagram.com/?u=` 那层跳板 | `/api/v1/users/web_profile_info/` 直接 **429**，五个账号全被限流 |

还有一条必须写下来，否则这条渠道看起来像坏的：**Instagram 搜的是账号名，不是描述。**
`led display distributor` 返回 **0 个账号**；`pantallas led` 返回五家真实的拉美 LED 公司
（LedLemon、Pantallas LED Scherm、Pantallas Led Peru、CGS Chile、Pantallas Led Venezuela）。
所以这条渠道要喂**短的、像名字的词**，长句子在这里天生无效——那是空结果，不是故障。

跑通的产出（同日实测）：`pantallas led` → pantallasledlemon.com、exctecled.com；
`led screen rental` → ledscreenrental.ae。和 Facebook 一样只有域名过界，
账号 handle 跟着进库，这家公司一入库就带着私信地址。
429 按 docs/128 R2 处理：报「被限流」，不报 0 家。

## R7 一条渠道要不要人守着，按「它会不会开窗口」判，不按「它用哪个引擎」判

docs/126 R5 把「要登录态的 playwright」和「browser-use」一起判成必须有人守着，
理由是它们会在凌晨三点弹窗抢焦点。2026-09-11 实测把这条规则拆成了两半：

| 渠道 | 原来为什么要人守着 | 实测 | 现在 |
|---|---|---|---|
| Instagram | 假设 headless 过不了平台的机器人检查 | headless 读到**同样的账号、同样的 bio 外链**，27 秒一轮 | 无人值守 |
| Naver 博客 | browser-use 一定开窗口 | 正文根本不在浏览器后面：jina 12 秒拿到 85,749 字，一次 DeepSeek 调用 1.6 秒抽出公司名 | 无人值守 |

Naver 博客这条值得单独说：docs/126 把它交给 browser-use 是**对的读法，错的理由**。
当时的判断是「公司名写在正文里、没有链接，所以要模型读」——前半句对，后半句多了一步。
要模型读的是**文本**，而文本 jina 早就免费拿到了。85–121 秒一个弹窗，换成 1.6 秒一次
API 调用，产出一样：`아바비젼` → avavision.co.kr（另外三个名字没通过 docs/126 R2 的
确认关，如期丢弃）。browser-use 的读法保留为第二声明，留给 fetch 打不开的页面。

于是规则改写成它本来想说的那句话：

> **无人值守与否，看这条渠道的默认读法会不会在屏幕上开窗口。**
> browser-use 一定会开，所以它永远不能是无人值守渠道的第一读法；
> headless 的 playwright 永远不会开。

Instagram 还多两条闸，因为它背后是一个会被封的账号：
**每轮最多 8 个主页**（`gather` 默认要 20，夜里每条关键词走 20 个主页是小号消失的方式），
以及**长句截成前三个词**——实测 `LED video wall installer contact` 一个账号都搜不到，
截成 `led video wall` 搜到四个、产出 churchleds.com 和 distinctled.com。
面板的默认关键词全是长句，所以这个截断不是优化，是这条渠道在无人值守时能不能产出的前提。

## R8 一条渠道是一串读法，按顺序试，不是只有一种

docs/126 R1 把三种读法按成本排了队，但每条渠道最后只用了其中一种。一种读法有三种
停止工作的方式——抛异常、被挡、以及**选择器底下的东西被换掉了所以返回空**——
而这三种都不等于「这个市场没有客户」。

docs/124 R4 早就手工处理过这件事：名录页抓到 0 家，界面才冒出「用浏览器读这一页」的按钮。
那里面唯一需要人的是**决定**，而这个决定每次都一样。所以它现在是自动的：

> 按声明顺序往下试，**抛异常或返回空都换下一个**，第一个拿到东西的读法算数。

两条边界：

- **点名了读法就是点名了**。请求写了 `http` 却悄悄给了一个 Chrome 窗口，
  那不是对这个问题的回答（R6 不变）
- **无人值守时，会开窗口的读法根本不进这条链**。兜底正是定时器在凌晨三点打开 Chrome
  的那条路径，所以 `gather` 不点名渠道时（＝定时器在跑）直接把 `browser` 从链上摘掉。
  Allen 自己点的时候可以一路退到浏览器

2026-09-11 按这条规则补的两条腿，都是测过才加的：

| 渠道 | 原来 | 现在 | 为什么 |
|---|---|---|---|
| Naver 网页 | jina 一条腿 | jina → headless 浏览器 | jina 是**别人在运营的服务**，它挂了这条最能产出韩国买家的免费渠道就死了。实测 headless 读同一页拿到 14 家真实韩国公司 |
| Instagram | 选择器一条腿 | 选择器 → browser-use | 搜索接口和主页结构是 Meta 的，他们改的那天选择器返回 0。模型读页面不在乎 DOM 长什么样 |
| DuckDuckGo | jina 一条腿 | **不动** | 实测 `html.duckduckgo.com` 给 headless 浏览器 205 字节、0 条结果。**不能用的读法不是兜底** |
| Facebook | 选择器一条腿 | **不动** | 它读的是可见文本的正则，不是选择器；这种读法本来就不怕改版，加一条没测过的兜底是凭空的工作 |

Instagram 的 browser-use 读法用的是**采集身份那份 profile**（`~/.outreach-tool/scrape/`），
不是 browser-use 自己那份匿名 profile，也永远不是发送身份（docs/126 R4 不变），
并且白名单只放行 `*.instagram.com`。

## R9 Google：前门被墙拦了八次，那就走 Google 自己留的那扇门

2026-09-11 把前门试穿了：

| 读法 | 结果 |
|---|---|
| jina | 704 字节 `This page maybe requiring CAPTCHA` |
| headless Chromium | 异常流量页 |
| 有头的真实 Chrome | 异常流量页 |
| 真实 Chrome + 去掉 `--enable-automation`、`navigator.webdriver=false` | 异常流量页 |
| 先用**完全没被驱动**的普通 Chrome 打开一次 google 预热过的 profile | **一次通过（5641 字节真实结果页）**，随后两次又被墙 |
| 预热时让普通 Chrome 自己搜一次，再驱动 | 两次都被墙 |

八次里一次侥幸。冷 profile 确实是诱因之一，但预热不是解药——**这台机器的地址在
Google 的公开搜索页上是被限的**，多试只会把限得更紧。

Google 自己留了另一扇门：Programmable Search Engine 的 JSON API，**每天 100 次免费**，
没有反爬页，不需要浏览器。所以这条渠道的读法顺序变成 `http → playwright → browser`：
配了 key 就走 API，没配就沿着 docs/128 R8 的链掉进浏览器，行为和今天一模一样。

**2026-09-11 当天试到底了，没通**：拿到 key 之后一路排除——换项目（两个）、
换 key（三把）、新建一个干净项目、API 确认已启用、key 限制只放行 Custom Search、
等了十分钟重试十几次——Google 始终回同一句
`This project does not have the access to Custom Search JSON API.`。
这个账号的控制台顶部一直挂着「您的免费试用需要支付预付款」，而那条横幅是跨项目的：
**免费额度不发给这个状态的账号**，换项目解决不了。

所以这条读法留在表里但当前不通，报错文案把两种可能都说清楚（没启用 / 账号结算状态），
不再单说其中一种——被实测证伪的提示比没有提示更糟。渠道本身沿 R8 的链掉进浏览器，
行为和加这条读法之前一样。其余六条渠道不受影响。

两个值要 Allen 自己去拿（都免费，五分钟）：一个搜索引擎 ID（cx，建的时候打开
「搜索整个网络」），一个 API key。两行写进 `backend/google_cse.txt`。没配的时候
渠道报的不是「坏了」，是**这两步怎么做**——docs/70 R4 的规矩在这里的样子。

## R6 读法由渠道声明，API 按声明校验

`/api/discover` 和 `/api/discover/page` 收到一条渠道没有声明的读法时报 400，
而不是默默降级成默认读法。docs/126 验收第 1 条，这份 spec 把它实现了。

## 不做的事

- **不上 Bing**。理由在上面的实测表里：答对时给同行，答不上时悄悄给别的问题的答案
- **不给 Naver 网页加 Playwright 读法**。jina 免费、无人值守、今天就在产出韩国买家，
  加一条更贵的读法读同一页，是给没坏的东西换零件
- 不因为 Google 今天被挡就把它从表里删掉。IP 会变，换网络就可能通；它现在的正确行为
  是报「被 Google 判定为异常流量」，不是消失
- 不给 Instagram 写此刻验证不了的真实选择器（R5）
- 不用登录态读 Facebook 公共主页：未登录就能读的东西，没有理由拿一个能被封的身份去读（R4）
- 不让任何 `browser`/带登录态的 `playwright` 读法进调度器（docs/126 R5 不变）

## 验收

1. `gather` 有调用方：`/api/discover` 的关键词搜索经由它，不指定渠道时只跑
   `unattended=True` 的渠道
2. 候选行带着发现它的渠道名进导入面板，不再全部盖成「搜索」
3. 结果页出现反自动化拦截时，该渠道报失败并带原因，不返回空结果
4. 采集用的 profile 目录在 `~/.outreach-tool/scrape/` 下，且任何采集代码路径都不会打开
   `~/.outreach-tool/browser/` 下的目录
5. Facebook 不需要登录态就能产出候选，且只有域名过界；Instagram 在没有采集登录态时
   报「未启用」，并且渠道页上真的有那个登录按钮——提示语指向的下一步必须存在
6. 采集登录态的判据是 session cookie；一个只是被打开过的 profile 目录不算已登录
7. 指定一条渠道没有声明的读法，API 报 400
