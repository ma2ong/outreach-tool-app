＃ 85 — 每个客户都要有开场白

## 为什么现在必须补

[docs/84 R3](84-spec-one-source-per-channel.md) 之后 Allen 定了一条：
**主题和正文都不能出现对方的公司名。** 这条是对的 —— 公司名放在主题开头是群发的标志。

但它有个副作用，数出来是这样：

| | 之前 | 之后 |
|---|---|---|
| 有邮箱的客户 | 1008 | 1008 |
| 首封被 `message_guard` 判「个性化不足」 | 88 | **382** |

因为 `_distinctive_terms` 把公司名算作个性化线索。公司名一去掉，**没有开场白的客户，
信里就再没有任何和它们有关的东西**。守卫拦得没错 —— 那确实是一封谁都能收的信。

Allen：

> 没开场白的都补齐，实在是补补齐不了的可以英文（除了韩国之外的其他国家）和韩文
> （只针对韩国客户）各做一个通用版的开场白

## R1：先用已有的材料补，不去重新抓站

385 家没有开场白，其中 **380 家有 `business`** —— 一句人写的业务描述：

```
LED display & digital signage solutions
LED multimedia panel sales & rental (Goiânia)
Outdoor LED screen (since 2004)
```

这已经够写开场白了，不需要再去抓一遍网站。`brief.build()` 要网页正文，那是发现阶段的路径；
补录走的是书里已经有的字段。

**词表只能落在 `personalize._HOOK_GLOSS_KO` 里面。** 那张表决定了一个英文开场白能不能
译成韩语；用一个表里没有的词，韩国客户的开场白就会整句消失。所以业务描述归类到
`rental` / `events` / `installation` / `signage` / `billboard` / `distribution` 这些
已经有韩文对照的类别，最多两个，和 [docs/78](78-spec-a-blog-post-is-not-a-customer.md)
的生成器同一个形状。

## R2：句式必须是能被认出来的那三种

`personalize.hook_ko` 靠正则认句式，认不出就返回空 —— 半句英文混在韩语信里比没有更糟。
所以补出来的开场白只能是：

```
Saw the {类别} work you do around {城市}.     ← 有城市
Saw the {类别} work on your site.             ← 有网站，没城市
Saw the {类别} work you do.                   ← 都没有
```

第三种是这次新增的，因为「没城市也没网站」在补录里是常态，而
`Saw ... on your site.` 是一句我们证明不了的话 —— 我们没抓过那个站
（[docs/45](45-spec-no-claim-without-a-source.md)）。

## R3：通用版开场白，用的是 Allen 自己的那句

补不出类别的，落到通用版。用词不是新写的，是他 v2 默认文案里那一句，
把公司名换成「贵司」：

| | |
|---|---|
| 英语（韩国以外） | `I came across your company while looking at LED and AV companies in your market.` |
| 韩语（只给韩国） | `귀사 관련 내용을 확인하다가 연락드렸습니다.` |

两句都**不对客户做任何声明** —— 说的全是我们自己做了什么。docs/45 不受影响。

韩语那句由 `hook_ko` 从英语那句映射出来，所以书里只存一条，韩国客户自动读到韩文。

## R4：通用版必须能通过守卫，但只有通用版可以

通用开场白没有任何专属线索，`message_guard` 的 `impersonal` 规则照样会拦。
而 Allen 已经决定这些信要发 —— [docs/80 R2](80-spec-no-hook-is-not-a-reason-not-to-write.md)
早就定过同样的事：**没有开场白不是不写的理由。**

所以守卫放行的条件写得很窄：**这家客户存的 `hook` 就是通用版那一条。**
不是「信里出现了这句话」—— 那样任何一封信都能靠加这句蒙混过去。
是「我们查过它、确实没材料、于是明确标了通用版」。

一个 hook 为空的客户，仍然被拦。这一点没有放宽。
