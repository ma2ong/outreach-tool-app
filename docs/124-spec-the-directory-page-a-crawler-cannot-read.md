＃ 124 — 抓不动的那种名录页

## 四个真实名录页，现在的采集拿到 0 家公司

2026-09-10 实测，用现在的 `jina.fetch` + `harvest.harvest_domains` 打四个页面：

| 页面 | 结果 |
|---|---|
| ISE 2026 展商名录 | 反爬页，0 |
| InfoComm 展商名录 | 抓到 18 个域名，**没有一个是展商**——全是 CDN、社交、协会自己的域名 |
| Absen「去哪买」 | 抓到 4 个域名：cookie 服务、Google、Absen 自己的两个子域，**0 家经销商** |
| LEDs Magazine 供应商目录 | 反爬页，0 |

这不是「抓得少」，是**一家都没有**。展商名单在 `mapyourshow.com` 的 JS 应用里，经销商名单在
点了「Load More」才出现的卡片里，两者都不在 HTML 源码中。

同一天，用 browser-use 开真实 Chrome 读 Absen 的合作伙伴页，拿到 **66 家 AV 分销商**，
带国家：Avientek（阿联酋）、SYSCOM（墨西哥）、Midwich（英国）、PSCo（英国）、
TD Synnex（西班牙）、NMK（阿联酋）……这些正是买 LED 屏的公司。

[docs/70](70-spec-discovery-channels.md) 声明的四条渠道里有三条是 Naver，全球市场实际只有
DuckDuckGo 一条腿。竞品经销商页和展会展商名录是这个行业里质量最高的两个名单，
而它们恰好都属于「抓不动」的那一类。

## 这条和 docs/70「不引入 OpenCLI」不矛盾

docs/70 拒绝 OpenCLI / AutoCLI 的理由是：它们复用**你正在用的那个浏览器**的登录态，
你关掉 Chrome 它就断了。

browser-use 不一样：它自己拉起一个 Chrome，用自己的 `user_data_dir`，
**不读、不写、不碰** `~/.outreach-tool/browser` 里 WhatsApp / Instagram / Facebook 的登录态。
它是一个独立的读页面工具，不是「借用你的会话」。

## R1 它只交域名，公司名一个字都不要

实测输出里，browser-use 把 `syscom-cloned-21865-Avientek-Logo--768x134.png` 这个图片文件名
读成了公司名，把邮箱域名当成了官网域名，还有几家名字是它自己凑出来的。
它自带的 judge 也判了「questionable methodology」。

这正是 AGENTS.md 那条红线：**来源薄弱的数据是停下来的理由，不是猜测的理由。**

所以接口只收一样东西：**域名列表**。公司名、国家、邮箱、电话、ICP 判分，全部由现有的
`enrich_domain` 去读那家公司自己的官网得到——和关键词搜索来的候选走完全一样的路。

这样幻觉无处藏身：编造的域名在 enrich 阶段解析不到内容，编造的公司名根本没有入口进来。
`harvest_domains` 的签名本来就是这个形状（`fetch` 可注入，返回 `list[str]`），
所以这是换一个 `harvest_fn`，不是新开一条管线。

## R2 它跑在自己的虚拟环境里，用子进程调用

`pip install browser-use` 拉进来 100 个包，其中包括 openai 2.26（生产环境是 1.109）、
pydantic 2.13、httpx2、一套 google-api 客户端。**装进生产 Python 环境会重装 uvicorn 正在用的依赖。**

所以它住在 `~/.outreach-tool/bu-venv`，通过 `subprocess` 调用——和 `agent/llm.py` 调
Claude CLI 是同一个模式。三个好处：依赖不打架、它崩了不会带走服务、超时可以硬杀。

## R3 域名白名单是机械保证，不是提示词里的一句话

`BrowserProfile(allowed_domains=[...])` 只放行目标站点。实测有效：模型在 Absen 页面卡住时
自己想去 DuckDuckGo 和 Bing 找答案，两次都被 `blocked by security policy` 拦下。

白名单由调用方按目标 URL 的域名自动生成，**不接受任务提示词里出现的域名**。
一个只能访问目标站点的浏览器，最坏情况是抓不到东西，而不是跑去别的地方。

## R4 必须开真实 Chrome 窗口，所以这是 Allen 在场时按的按钮

headless 模式打 Absen 被 Cloudflare Turnstile 挡死：等了 6+8+10+10+10 秒、点了验证框、
重新导航两次，页面从头到尾没加载出来。换成 `channel="chrome"` + `headless=False`，同一个页面
一次通过。

代价是屏幕上会弹出一个浏览器窗口。所以：

- **不进任何调度器**——autosend、社媒队列、Agent 的 `discover_run` 都不调用它
- 只在 `/api/discover/page` 显式指定 `engine="browser"` 时运行
- 日报里也不提它，它没有「今天跑了几次」这回事

一个会在凌晨三点弹窗抢焦点的东西，不该由定时器决定什么时候弹。

## R5 没装 = 未启用，不是失败

沿用 [docs/70](70-spec-discovery-channels.md) R4：`bu-venv` 不存在、或者没有
`deepseek_key.txt`，返回的是「未启用」和一句话说明缺什么，不是异常、不是重试。
一个没装的工具和一个坏掉的工具，在界面上必须是两回事。

## R6 步数和超时是硬上限

实测一次运行 85–121 秒、12–14 步。上限：`max_steps=12`、单步 90 秒、整体 5 分钟。
超时就杀进程、返回已经拿到的东西。

实测那次因为步数用完，只收了两个分类中的一个（66 家里少了 VAE 那批）。
**收得不全是可接受的，收错是不可接受的**——这就是 R1 的理由。

## 不做的事

- 不替换关键词搜索。DuckDuckGo 那条路便宜、无人值守、每天都在跑，它没坏
- 不进 Agent 的自动开发路径（R4）
- 不碰任何发送路径。这个工具只读页面，不认识 `channel_outreach`
- 不做登录后才能看的名录。要登录就是要账号，要账号就是可以被封的账号
- 不做展会名录的专用适配器。先证明一个 URL 走通，再谈第二个

## 验收

1. `harvest_with_browser(url)` 返回域名列表，与 `harvest_domains` 同型，可直接喂给 `run_page_discovery`
2. 域名之外的字段一概不返回；公司名来自 enrich，不来自浏览器
3. 没装 bu-venv 时，`/api/discover/page?engine=browser` 报「未启用」并说明缺什么
4. 传给子进程的白名单只含目标 URL 的域名
5. 任何调度器代码路径都不会调用到它
6. 超时后不留下 Chrome 进程
