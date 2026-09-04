＃ 99 — 认框的方式，不是登录失效

## 六天的沉默，闸门是对的

08-28 到 09-03，社媒一条私信都没发出去。[92 号 spec](92-spec-the-clock-that-decides-is-ours.md)
修好了「消息轮不到发送」和「失败没人知道」，R5 那条记录在 09-04 00:52 吐出了真正的原因：

```
试了 3 条，全失败
could not confirm this customer's private message box — refusing to type,
because the box on this page would post a public comment.
saw: ['(无标签)','(无标签)','(无标签)','(无标签)','(无标签)','(无标签)']
```

不是登录失效，不是超时。是 `_dm_composer` 主动拒绝：它在页面上找不到能确认身份的私信框，
怕打进去变成公开评论。**这道闸做了正确的事** —— [61 号 spec](61-spec-never-guess-the-box.md)
建它就是为了这个，一条冷开发私信发成公开评论，比不发糟得多。

要改的是它认框的方式。09-04 用真实已登录 profile 只读探了两个渠道，下面全部是探回来的原文。

## Facebook：标签是对的，比对方式是错的

页面上三个框：

```
[1] aria-label="以 Allen Ma 的身份评论"      ← 评论框
[2] aria-label="以 Allen Ma 的身份评论"      ← 评论框
[3] aria-label="发消息给Rentex Audio Visual & Computer Rentals"   ← 私信框
```

私信框认得清清楚楚。挡住它的是 `_addresses()`：

```python
return cls._slug(target) in cls._slug(label)
```

`target` 是 handle `rentexrentals`，标签归一化后是 `rentexaudiovisualcomputerrentals`。
**handle 是缩写，标签里是公司全称，子串比对永远不成立。** 这不是偶发，这是常态 ——
Facebook 主页的 handle 和显示名本来就是两个东西。

## Instagram：标签在另一个属性上，而且不含公司名

```
[1] role="textbox" contenteditable="true"
    aria-placeholder="发消息..."      ← 只有这一个属性写着它是什么
    data-lexical-editor="true"
```

`_dm_composer` 读的是 `aria-label` 和 `placeholder`，两个都没有，于是标签为空 ——
日志里那六个 `(无标签)` 就是这么来的。

而且即使读到了，它写的是 `发消息...`，**一个字都不提对着谁**。往上翻十二层祖先，最好的
一句是 `Instagram 用户 Instagram 查看主页 发消息...`；页面上没有任何 `role="dialog"`。
Instagram 已经不再提供 61 号 R1 依赖的那条线索。

## R1 标签要从三个属性读，不是两个

`aria-label`、`placeholder`、**`aria-placeholder`**。

一个属性名。它同时修好两件事：Instagram 的私信框终于有标签了，而 Facebook 的评论框
（`aria-placeholder="以 Allen Ma 的身份评论"`）也终于会被认出来是评论框 —— 在此之前
那两个框在闸门眼里同样是「无标签」，也就是说这道闸对两个方向都是瞎的。

## R2 身份不再靠「标签里有没有这个 handle」

61 号 R1 要守的是：**不要打进属于另一家公司的聊天窗**。这一条不变，变的是怎么确认。

按顺序：

1. **标签点名了目标就用它。** 比对放宽成两头都算：handle 是标签的子串（旧行为），
   **或者**标签是「发消息给X」而 X 与我们要写的公司同名。第二种要求发送方把公司名传进来。
2. **否则，如果整页只有一个私信框，就是它。** 我们刚刚 `page.goto` 打开了这家公司自己的
   主页 —— 那是一次真实导航，此前的聊天窗都已随页面销毁 —— 然后点了这个页面上的
   「发消息」。此刻页面上唯一的那个私信框，只能是刚打开的这一个。
3. **两个及以上、又没有一个点名目标 → 拒绝。** 61 号那个「Jaws Audio 和 PRI Productions
   两个窗同时开着」的场景原样保留，这是唯一还需要拒绝的情况。

第 2 条是这份规格的实质。它把「标签里要有名字」这个**代理指标**，换成了「这是我们刚打开的
那一个」这个**真实事实**。代理指标会随平台改版失效，而且已经失效了两次；导航这件事不会。

## R3 评论框永远不是候选，这条不放宽

`_is_comment_box` 原样保留，而且因为 R1 现在读得到 `aria-placeholder`，它比以前更严。
一个自称是评论的框，无论页面上还剩几个框、无论多想把今天的队列发出去，都不进候选。

这是 61 号唯一不可交易的一条：发错公司是尴尬，发成公开评论是把冷开发信钉在别人主页上。

## R4 拒绝时要说清楚看到了什么

现有的错误已经把 `saw:` 列出来了，这次它救了六天的时间。保留，并且把标签的三个来源都
写进去 —— 一个 `(无标签)` 告诉不了任何人属性名换了。

## 验收

1. `aria-placeholder="发消息..."` 的框被认成私信框。
2. `aria-placeholder="以 Allen Ma 的身份评论"` 的框被认成评论框，且永不入选。
3. 页面上只有一个私信框、标签不含 handle（Instagram 的实况）→ 选中它。
4. 页面上一个私信框、标签是 `发消息给Rentex Audio Visual & Computer Rentals`、
   handle 是 `rentexrentals`（Facebook 的实况）→ 选中它。
5. 两个私信框、都不点名目标 → 拒绝，错误里带上两个标签。
6. 两个私信框、其中一个点名目标 → 选中点名的那个。
7. 一个私信框 + 两个评论框（Facebook 实况）→ 选中私信框。
8. 只有评论框 → 拒绝。

## 没做的

* **不放宽评论框那条。** R3。
* **不改 WhatsApp 的取框方式。** 它走 `footer div[contenteditable='true']`，不经过这个函数，
  而且它昨晚的失败原因还没单独查过 —— 那是另一件事，不在这份规格里假装一起修好了。
* **不加重试。** 拒绝一次的代价是这条消息顺延（92 号 R4），不是丢失。反复重试一个认不出
  的页面，只会把一个静默失败变成一个吵闹的静默失败。
