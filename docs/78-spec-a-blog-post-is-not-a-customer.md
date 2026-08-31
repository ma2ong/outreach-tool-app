＃ 78 — 一篇博客不是一个客户

## 先数一遍，再决定收紧什么

Allen 要「ICP 收紧」。收紧之前先看客户库里到底混进了什么——因为收错了地方，
代价是把真客户挡在门外，而那种损失是看不见的。

1318 家客户里，37 家是 ICP 读不出类型（`target_fit='discovered'`）就入库的。逐条看：

| 是什么 | 例子 |
|---|---|
| **不是公司** | `contact-us님의블로그 : 네이버 블로그`（blog.naver.com）、`URL Source: https://m.blog.naver.c…`、`ledplus.tistory.com`、`idplan.tistory.com` |
| **不是买家** | `ensun.io`（公司检索引擎）、`trademo.com`（贸易数据平台）、`f6s.com`（创业公司目录） |
| **反爬页读出来的** | `Checking your browser`（f6s.com）、`Robot Challenge Screen`（thesupersignguy.com，还给了 85 分） |
| **真客户，只是没分出类** | `avidex.com`、`avdg.com`、`avendor.com`（都是真的 AV 集成商）、`ledfactory.cl`、`mediarent.cl` |

**最后一行是这份 spec 最重要的一行。** 直觉答案是「ICP 读不出来就不入库」——37 家里
有一半会因此被扔掉，而它们是真的 AV 集成商，只是官网首页没写「system integration」
这个词。分类器读不出来是分类器的问题，不是这家公司的问题。

所以收紧的不是分数，是**「这到底是不是一家公司」**。

## R1 名字不像公司名的，不入库

三种，都出现在库里：

- 以 `URL Source:`、`http://`、`https://` 开头的
- 反爬页和错误页的标题：`Robot Challenge Screen`、`Checking your browser`、
  `Just a moment`、`Attention Required`、`Access denied`、`Enable JavaScript`、
  `Page not found`、`Security Check`
- 博客平台的标题格式：`…님의블로그`、`: 네이버 블로그`、`- Tistory`

这些不给覆盖开关。一个名字叫 `Robot Challenge Screen` 的客户，**没有任何情况下**
是 Allen 想写信的对象；而且这三类的共同点是：读到的页面根本不是这家公司的页面，
所以从这一页读出的简介、开场白、ICP 分数**全都是假的**。85 分那条就是这么来的。

## R2 内容平台和数据平台不是客户官网

现有的 `_DIRECTORY_HOSTS` 挡的是采购平台（alibaba、made-in-china）。同一类里还缺两种：

- **博客/内容平台**：`blog.naver.com`、`m.blog.naver.com`、`*.tistory.com`、
  `brunch.co.kr`、`medium.com`、`*.blogspot.com`、`wordpress.com`、`cafe.naver.com`
- **公司检索/贸易数据**：`ensun.io`、`trademo.com`、`f6s.com`、`crunchbase.com`、
  `owler.com`、`similarweb.com`

一篇讲 LED 的博客里当然全是 LED 关键词，所以它必然是高分。**分数越高越说明
问题不在分数上。**

## R3 开发页默认只勾「有话可说」的

`DiscoveryPanel` 现在的默认勾选是：

```ts
.filter((c) => !c.excluded && !c.duplicate_of && (c.email || c.phone || c.instagram))
```

只要页面上扒到一个电话就自动打勾。库里那几篇 naver 博客就是这么被一起勾进来的——
Allen 点的是「导入选中」，他没有一条条挑。

改成还要有 `hook` 或 `brief`：**没有一句能引用的话，就没有一封能写的信。**

不改成「ICP 必须有类型」——那正是 R1 开头那张表最后一行的教训：那会连 avidex
一起扔掉。**手动仍然可以勾任何一条**，收紧的是默认，不是权限。

## R4 已经混进去的清掉

`f6s.com`、`ensun.io`、`trademo.com`、`cloudworkpro.com`、`blog.naver.com`、
`m.blog.naver.com`、两个 tistory —— 删。
`thesupersignguy.com` 是真域名、只是名字读成了反爬页标题 —— 改名，不删。

## 不做的事

- **不提高 `minimum_fit` 门槛。** 自动导入路径（`qualify_for_auto_import`）已经要求
  ICP 有类型且有 hook/brief，它没漏；漏的是手动路径。往已经够严的那条路上再加一道，
  只会让开发更少，不会让开发更准。
- **不给分数重新标定。** 30 天 352 次触达只有 2 个回复，没有任何样本量能校准这个分数。
  在拿到回复之前，动分数就是换一组同样没有依据的数字。

## 验收

1. 名字是 `Robot Challenge Screen` / `URL Source: https://…` / `…님의블로그` 的候选，
   `import_candidates` 一律不建行，并在 skipped 里说明原因
2. `blog.naver.com`、`x.tistory.com`、`ensun.io` 被 screening 标为排除，理由可读
3. 开发页默认勾选里不再出现没有 hook 也没有 brief 的候选；手动勾仍可导入
4. 真的 AV 集成商（ICP unknown 但有 brief）照旧能进
5. 库里那 8 条清掉，`thesupersignguy.com` 改回域名名
