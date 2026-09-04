＃ 98 — 叫一个人的名字，不需要有他的联系方式

> 编号说明：这份先写成 96，再改 97，最后落到 98 —— 同一个上午 Codex 连续占了 96 和 97。
> 两个工作树各自取号，谁先合进 `main` 谁得到那个号，后到的改名。编号就是身份，代码注释
> 里的 `docs/96` 必须只指一份东西。

## Allen 的一条（09-04）

> 不要让我来点击或者确认什么。不需要界面。你只需要知道除了韩国的公司之外，其他国家的
> 公司有名字的话就写名字称呼，没名字或者不确定的情况下直接 Hi，韩国的称呼我已经让
> 另一个窗口修改了。

## 246 个名字，被一道为别的事设的闸挡住

`decision_maker_radar` 扫了 **545 次**，产出 **270 个候选人**。其中 24 个晋级成了联系人，
**246 个停在 `new`**，一个都没用过。

停住的机制在 `promote_candidate` 里，一行：

```python
if not (candidate.get("email") or candidate.get("linkedin")):
    raise DecisionMakerValidation("自动晋级需要公开公司邮箱或个人 LinkedIn")
```

这条规则本身是对的 —— "晋级"的含义是"这个人可能会收到我们的信"，而没有渠道就发不了信。
246 个里只有 3 个有 LinkedIn，所以 243 个永远过不去。

但**叫一个人的名字，不需要有他的联系方式**。这 88 家公司的信照样在发，发往
`info@`，开头是一句 "Hi,"。缺的从来不是收件人，是称呼。

一道为「能不能发给他」设的闸，挡住了「能不能叫他」这件完全不同的事。

## 抓回来的名字有多脏，量过

`personalize.looks_like_a_person`（[95 号 spec](95-spec-two-mailboxes-one-letter.md) R3）
挡掉 72 个，剩 174 个过闸。但 174 不等于 174 个真人。同一家公司 Data Projections
的九个候选长这样：

```
Data Projections   President    ← 公司自己的名字
Read More          President    ← 网页上的「阅读更多」按钮
Read More          CTO          ← 同上
Jim Scalise        President
Kris Begnaud       President
Matt Zaleski       President    ← 和下一行是同一个人
Matthew Zaleski    President
Megan Stasio       President
Travis Corgey      President    ← 九个人的职位全是 President，正则把职位配错了
```

**这九个全部通过了闸门。** 而且闸门比想象的更宽 —— 实测（不是假设）：

```
looks_like_a_person("Operations Manager")  → True
looks_like_a_person("Read More")           → True
looks_like_a_person("Outside Sales")       → False
looks_like_a_person("Contact")             → False
```

它挡的是自己那张黑名单上的词，不挡「职位词组」，也不挡公司名和网页控件文字。

## R1 韩国不在这份规格里

韩国 295 家公司的称呼由 [96 号 spec](96-spec-a-korean-letter-says-the-title.md) 处理
（Allen 09-04：「韩国的称呼我已经让另一个窗口修改了」）—— 那份的结论是韩语商务信里
陌生人按职级称呼，不按名字，所以这份规格里的名字对韩国公司毫无用处。这里对 `country` 落在
[63 号 spec](63-spec-korea-stays-semi-automatic.md) 那张韩国表里的公司**不做任何事**，
连读都不读，免得两边同时写同一列。

## R2 一家公司只有一个可信候选时，才用那个名字

这是「不确定的情况下直接 Hi」的落点，也是这份规格里唯一需要判断的地方。

Data Projections 有六个真人名字，我们**不知道该叫哪一个**。那就是不确定，用 "Hi,"。
UTG Digital Media 只有 Alan Wehbe 一个，那就是确定，用 "Hi Alan Wehbe,"。

不按可信度排序取第一名。九个候选的可信度全是 81 —— 分数在这里没有区分力，拿它排序
只是把一个抛硬币写成一个算法。

按这条，75 家里 **39 家一个候选**，36 家有多个，后者全部继续用 "Hi,"。

## R3 三道过滤，都是确定性的

顺序在 R2 之前：先滤掉不算数的，再数还剩几个。

1. `looks_like_a_person` —— 95 号 R3 那道闸，原样复用，不改它（那个文件另一份工作在动）。
2. **不能是公司自己的名字。** `Data Projections` 对 Data Projections 不是人名。归一化后
   比对 `company_en`，也比对去掉 `Inc/Ltd/LLC/GmbH` 之类后缀的形式。
3. **不能整个由职位词组成。** `Operations Manager`、`Executive Producer` 两段都是职位词。
   一个职位词不算 —— 有人姓 Marshall，`Tom Sales` 更可能是个人而不是部门。
4. **不能是网页控件文字。** `Read More`、`Learn More`、`View Profile`、`Our Team`、
   `Contact Us`、`Read Bio` 这类。列一张小表，不做模式推断 —— 推断出来的规则会在某个
   姓 `More` 的人身上出错，而这张表不会。

残留的假阳性还会有。95 号 R3 已经把这件事写在明处，这里不重复承诺。

## R4 证据必须来自客户自有官网

复用 `decision_maker_radar._company_owned`。第三方名录上的名字不进称呼 —— 那是
[89 号 spec](89-spec-an-address-nobody-ever-saw.md) 的同一条道理换个对象。

## R5 写进去，并且留下痕迹，好让 Allen 的修改是最终的

用上的名字：写进 `leads.contact_name`（邮件和社媒私信的称呼都从这一列来，两条路都不用改），
同时按现有路径建一条 `contacts` 行（`source='agent.public-site'`，**没有邮箱**，所以
95 号 R1 的抄送不会把它当成第二个收件人），并把候选标成 `promoted`。

留痕不是为了好看，是为了**不覆盖 Allen**。他把一个名字删掉或改掉之后，候选已经是
`promoted`，下一轮不会再看它，也就不会把他的修改改回去。一个会覆盖用户修改的自动化，
比一个从不动手的自动化更糟。

已经有称呼的公司一律不碰。

## R6 每轮都跑，不是一次性回填

雷达每天都在产出新候选，所以这一步进运行循环，和 `auto_prune_sequences` 一样的位置。
一次性脚本会把今天这 39 家填上，然后明天的新候选又开始堆积。

## R7 确定性过滤到此为止，最后一道由模型判断

R1–R4 全部实现之后，拿真实库跑了一次。29 家会被填上称呼，信会这样开头：

```
Hi Recent Comments,        ← WordPress 侧边栏
Hi Our Story,   Hi Our Vision,   Hi Our Business,   Hi Our Equipment,
Hi What We Do,             Hi From Humble Beginnings,
Hi Warranty Overview,      Hi Preliminary Site Plans,
Hi Alan GoodellProject Manager,   ← 抓取时粘连
Hi Meet Josh,              ← 页面上写的是「Meet Josh」
```

**29 个里只有约 12 个是真人名字。** 按 95 号自己的话，这种信从第一行就结束了。而 95 号
也已经记着「收紧正则试了两轮，两头都不准」—— 确定性规则在这份数据上就是到头了。

所以最后一道闸交给模型，用 `llm` 里本来就有的 `classify` 任务（DeepSeek 主、Haiku 备）。
93 号两小时前刚立下的规矩在这里原样适用：

* **模型只判断，不写。** 它返回的字符串如果不是我们发过去的那一个，丢掉；进入信里的
  永远是官网上读到的原字符串。`Meet Josh` 判成人名也只会原样用，**不会被修剪成
  `Josh`** —— 修剪是编造的近亲。
* **模型不可用 = 一个名字都不用。** 这是「不确定的情况下直接 Hi」最彻底的一种情况。
* **一天一批一次调用**，不是一个名字一次；而且每个销售日只跑一轮（`run_if_due`），
  否则同样三十几个名字会在一天八十五个周期里被反复问。

加上这道闸之后，同一份真实数据：

| | |
|---|---|
| 填上称呼 | **19 家**（全部是像样的人名） |
| 多个候选，不确定 | 19 家 → 继续 `Hi,` |
| 模型否决 | 15 家 → 继续 `Hi,` |
| 韩国跳过 | 20 家 |

被否决的候选**保持 `new`**，不标成 `dismissed`：雷达还在改进，明天重爬同一个页面可能
读得更干净。每天一次的闸保证这不会变成每天三十次调用。

## 验收

1. 非韩国公司、`contact_name` 为空、恰好一个可信候选 → `contact_name` 被填上。
2. 同一家公司两个及以上可信候选 → `contact_name` 保持为空。
3. 候选名字等于公司名（含去后缀比对）→ 不算可信候选。
4. 候选名字是 `Read More` 这类控件文字 → 不算可信候选。
4b. 候选名字整个由职位词组成（`Operations Manager`）→ 不算可信候选。
5. 韩国公司即使只有一个候选 → 一个字都不改。
6. 已经有 `contact_name` 的公司 → 不覆盖。
7. 用过的候选变成 `promoted`；Allen 事后清空 `contact_name`，再跑一轮不会重新填。
8. 建出来的 `contacts` 行没有邮箱，因此不会成为 95 号 R1 的抄送人。
9. 模型不可用 → 一个称呼都不填。
10. 模型返回了一个我们没发过去的字符串 → 丢弃，不进称呼。
11. 一天跑第二轮 → 不再调用模型。
12. `country` 为空但名字是韩文（`이승근` / `대표`）→ 当作韩国公司跳过。

## 没做的

* **不做确认界面。** Allen 明确否了（09-04）：不要点击，不要确认。上一版方案是一屏
  一家公司让他按键，75 家十分钟 —— 他要的是零操作。
* **不猜邮箱。** 名字有了不等于地址有了。[89 号 spec](89-spec-an-address-nobody-ever-saw.md)
  不动，这里只写称呼那一列。
* **不改 `personalize.py`。** 渲染逻辑（`looks_like_a_person` 那道闸、`Hi ,` 的标点回收）
  一个字不动，而且那个文件此刻有另一份工作在改。这份规格只负责把名字送到它面前。
* **不动 `promote_candidate` 的邮箱要求。** 那条规则守的是「谁会收到信」，是对的。这里
  走的是另一条路，不是把那条闸放松。
