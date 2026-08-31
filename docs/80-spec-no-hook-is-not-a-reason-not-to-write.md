＃ 80 — 没有开场白，不是不写的理由

Allen：

> 没有开场白的客户那就用通用的开场白，邮件、wa、ins、fb 的私信内容，
> 不要说没有开场白的客户进不了社媒私信队列。

## 现在是什么样

638 家客户没有 `hook`。这一条只卡住一个地方：

| | 没有 hook 时 |
|---|---|
| **邮件** | **照发**。`personalize.render` 把 `{hook}` 这个 token 直接去掉，那句话消失，信照样成立 |
| **WhatsApp / Instagram / Facebook** | **一条都不发**。`social_queue._candidates` 里写着 `AND COALESCE(l.hook,'') != ''` |

所以这不是一条贯穿全系统的规矩，是社媒队列自己加的一道，而且**它加错了地方**。

## 为什么当初那么写，以及为什么现在不成立

原来的注释是：「一条不提对方任何事的私信，比冷邮件还差——邮件至少还有个主题行。」
这句话本身没错，但它推出的结论错了：**「说不出对方的事」不等于「说不出话」。**

真正的问题在别处——现在这四条私信模板，有三条离开 hook 就读不通：

```
Hi, {hook} We manufacture the LED panels behind that kind of work — …
Hi, {hook} We supply the panels for exactly this — …
Hi, {hook} That's the sort of work our panels go into. …
```

`that kind of work`、`exactly this`、`the sort of work` 全部指向 hook 那一句。
hook 一空，这三句指向空气。**所以真正该做的不是放行，是另写一套能独立成立的话术。**
直接去掉那个 WHERE 条件而不换模板，发出去的就是一条读不通的信息。

## R1 去掉「必须有 hook」这道门

`social_queue._candidates` 不再按 hook 过滤。其余过滤条件（不联系名单、今天已发过、
邮件序列今天要碰的、冷却期）**一条都不动**。

## R2 没有 hook 时换一套不依赖它的模板，按客户类型选

用 [`copy_segments.segment_of`](../backend/app/copy_segments.py)——docs/76 已经建好的
那一套：Allen 自己打的标签优先，其次 `target_fit`，最后是对方自己写的业务描述，
都读不出来就落到 `general`。638 家里 618 家有 `business`，201 家有 Allen 的中文标签，
所以大部分能落到一个真实的段，而不是一律 general。

**这不违反 [docs/45](45-spec-truthful-lead-facts.md)**，理由要写清楚：通用话术里
**没有一句是在陈述对方的事实**，讲的全是我们自己是做什么的。段位只决定我们先说
自己的哪一面。哪怕段判错了，「我们做活动租赁用的 LED 屏」对我们仍然是真话——
错的代价是这句话没说到点上，不是说了假话。有 hook 的那条路才会引用对方，
所以严格出处那条规矩留在那条路上。

每段两个变体，按客户编号取——[docs/52 R6](52-spec-social-dm-daily-queue.md)：
平台读的是句式，不是名词，一批只有 handle 不同的私信会被当成同一条群发。

## R3 有 hook 的排在前面——这一条要真的写进排序里

原来的排序是：采购信号 → ICP 分 → 是否触达过 → 编号。**里面没有 hook**，
所以去掉门之后，有没有开场白纯看编号先后，那不是「排在后面」，是「随机」。

排序键插一档：采购信号 → ICP 分 → **有没有 hook** → 是否触达过 → 编号。

放在采购信号和 ICP 分**后面**是故意的：一家正在买的公司值这个名额，
哪怕我们只说得出自己是做什么的。一天 8–15 条名额，
「通用的可以发，但排最后」这句话的全部含义就是这一档。

## R3.1 个性化闸只管有 hook 的那一半

去掉 WHERE 之后还有第二道门，第一次跑才发现：`build_today` 里写着

```python
verdict = message_guard.check(body, lead, channel="email")  # judge as a first touch
```

`GUARDED_CHANNELS = ("email",)`——个性化检查本来就是**邮件的规矩**，社媒队列是
自己主动套上去的。套上去之后，通用私信必然被判 `impersonal`，因为最终文本里
确实没有任何一个能认出这家公司的词。

**有 hook 的那一半继续套**：那里它抓的是另一种失败——hook 应该渲染进去却没渲染，
于是「…behind that kind of work」指向空气。**没有 hook 的不套**，那正是这份 spec 说的情况。

**价格检查两边都跑**：它在渠道判断之前，任何渠道、任何情况都不放行一句自动报价。

## R4 邮件那边不动，但理由和我一开始想的不一样

我一开始以为「邮件本来就发得出去，`{hook}` 空了那句自动消失」就完了。查下去不是——
邮件也过同一道 `message_guard`，而且它**不看模板里有没有 hook，它看最终文本里有没有
一个能认出这家公司的词**（公司名、官网域名、城市、hook 的词）。

真正让邮件通过的是另一件事：**每一条序列步骤的主题行里都写着 `{company}`。**

```
{company} — which cabinet are you running?
{company} — 다음 시공 건 패널 문의
```

所以「NA Equipment — which cabinet are you running?」自带个性化，hook 空不空都过。
实测三家没有 hook 的客户走序列路径，全部 PASS。**冷邮件走的就是序列，所以邮件这边
一个字都不用改。**

**顺带记一个还没修的**：`templates` 表里那几条旧模板（首次触达/跟进2/跟进3）主题行
没有 `{company}`，走手动群发面板发给一家没有 hook 的客户会被挡下，提示还看不出原因。
那是 Allen 的文案，不替他改；等他要用那条路的时候再说。

## 不做的事

- **不给这 638 家编 hook。** 617 家手上只有「小满标签：工程商」这种内部标签，
  从它编不出一句能引用的官网原话（docs/45）。292 家有官网，那是复检该做的事，
  不是这份 spec 该做的事。
- **不放宽 WhatsApp/IG/FB 的额度。** 池子变大只是能挑的人变多，一天发几条不变。

## 验收

1. 一个没有 hook、有 Instagram 的客户，会出现在明天的队列里
2. 它的私信读得通，且不含 `that kind of work` 这类指向空气的说法
3. 同段位的两个客户，拿到的不是同一句
4. 有 hook 的客户，私信内容不变
5. 有 hook 的客户排在没有 hook 的前面（排序键里真的有这一档）
6. 通用私信里出现价格，照样被拦
