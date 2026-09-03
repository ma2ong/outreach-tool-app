＃ 94 — 写着他们做过什么的那一页，从来没被读到

## Allen 的话

> 客户 blog、官网的项目页/案例页现在都没读（只读了联系页和首页）。
> 这些不涉及账号风险，可以放开跑。接着做。
>
> 另外加一个限制六年前的帖子不算「最近动态」》》》只看近两年的帖子即可。

## 案例页读不到有两个原因，都在代码里写着

`enrich_domain` 跟链接的那一步：

```python
if not _pitches(joined):          # 首页上提过点距，就再也不跟任何内容链接
    urls = _content_links(joined, domain, seen)
```

而就算跟了，`_CONTENT_LINK_WORDS` 里案例类的权重是最低的一档：

```
"product": 3, "products": 3, "catalog": 3,
"about": 2, "company": 2, "profile": 2,
"portfolio": 1, "project": 1, "projects": 1     ← 只有 2 个名额，永远抢不到
```

**两条叠起来的结果是：一家在首页写了 P2.5 的公司，它的案例页永远不会被打开。**
而案例页恰恰是唯一会写「我们给里斯本那个体育馆做了主屏」的地方 ——
`brief` 和 `hook` 都是从这些页面的文本里建出来的，所以读不到案例页，
就只能拿「LED display & digital signage solutions」这种句子去开场。

blog 更直接：`_CONTENT_LINK_WORDS` 和 `_SIGNAL_LINK_WORDS` 两张表里都没有 `blog`。

## R1：案例页自己一轮，自己的预算

案例不跟产品页抢那 2 个名额，像 `_SIGNAL_LINK_WORDS` 一样独立成一档、独立计数。
理由和当初把 signal 拆出来的理由是同一个，写在代码注释里：
「product evidence must not suppress radar」—— 产品证据也不该压掉案例证据，
它们回答的是两个不同的问题。

词表要覆盖这门生意里案例页的实际叫法，包括西语、葡语、韩语、中文 ——
库里 1311 家客户分布在这些市场上，只写英文等于只对英文站生效。

## R2：找到点距不等于拿到了可引用的一句话

`if not _pitches(joined)` 这个条件对产品页是对的：知道他们卖 P2.5 之后，
再读一页产品页没有新东西。**对案例页它是错的** —— 点距是规格，
案例是「他们上个月做了什么」，后者才是开场白的材料。

所以案例那一轮不看 `_pitches`，无条件跑。

## R3：blog 归 signal 那一档

blog 上写的是「最近在忙什么」，和 news / press 是同一类，进 `_SIGNAL_LINK_WORDS`。
不新开一档 —— 一个网站的 blog 和 news 常常是同一个栏目的两个叫法。

## R4：只看近两年

`social_watch.STALE_AFTER_DAYS` 从 540 天改成 **730 天**。

Allen 的原话是「太久远的不用看了」，两年是他给的线。一条 2023 年的帖子仍然说明
这家公司活着、在做这门生意；2019 年的不说明任何还成立的事。

这个数字同时管两处：社媒主页，和 blog 上带日期的文章。

## R5：国家仍然只从联系页和首页推断

这条是既有规则，写在这里是因为 R1/R2 正好会破坏它：

> Country is an identity fact. Infer it only from the bounded contact/home pass,
> before following product, project, news or signal pages. Those later pages often
> mention customer markets and case-study countries that are not the company's own.

案例页是这个陷阱最深的地方 —— 一家韩国公司的案例页上全是迪拜、新加坡、伦敦。
**`country` 的推断必须留在案例那一轮之前**，一行都不能挪。

## 放开的是什么，没放开的是什么

**放开：官网。** 抓官网不碰任何登录态，不触发任何平台的风控，
代价只是每家公司多几次 `r.jina.ai` 请求和几秒钟。这一轮从每家最多 7 页
提到最多 12 页。

**没放开：社媒。** `social_watch.DAILY_LIMIT = 20` 一动不动。
那条线是 docs/71 定的，理由和抓取速度无关：Instagram 封号不会回来，
而那个 WhatsApp 号上有微信和全部客户联系方式。官网和社媒在这件事上不是一回事，
不能因为「都是读公开内容」就套同一个额度。

## 验收

1. 一家首页就写了 P2.5 的公司，它的案例页仍然被读到（R2）。
2. 案例页和产品页各有各的名额：跟了 2 个产品页不会让案例页一个都跟不到。
3. `blog` 链接会被跟到。
4. 案例页里出现的国家**不改变** `country` 的判定（R5）。
5. 一条 2023 年的社媒帖子算「最近动态」，2022 年之前的不算（R4，730 天）。
6. 社媒每日额度仍然是 20，不因为这份规格改变。

## 没做的

* **全站爬。** `_rank_links` 只从已经抓到的页面上取同域链接，跟一层，有上限。
  这不是爬虫，也不该变成爬虫 —— 一个把客户官网抓穿的工具，
  第一次被对方运维注意到就是最后一次。
* **让模型总结案例页。** `brief.py` 那条规矩不变：引用他们自己写的句子，不改写。
