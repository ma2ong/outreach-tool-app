# 106 — 他们在落款里写全了，书上还是空的

## 一张截图

Allen 09-04 转来一封回信（`inbox_messages.id=4805`，lead 1180）：

```
Sincerely,

Roman Gerashenko
CEO
Alternis LLC + Brands

m: 917-495-9116
e: roman@alternis.com
w: www.alternis.com
```

姓名、职位、公司、手机、邮箱、官网 —— 客户自己一行一行报了家门。
[86 号 R5](86-spec-the-product-can-change-itself.md) 写的 `reply_details` 从这封信里读到的是：

```python
{'phone': '+19174959116', 'website': 'www.alternis.com'}
```

名字没读到，职位没读到，邮箱没读到。

## 代价：这条规则上线以来，一个名字都没读出来过

把库里 10 封真人回信全部喂给今天的 `read()`：

| 读到 | 封数 |
|---|---|
| 电话 | 2 |
| 官网 | 2 |
| **姓名** | **0** |
| **职位** | **0** |
| **邮箱** | **0** |

姓名/职位那条正则要求名字和职位**在同一行、中间有分隔符**：

```python
r"([A-Z][A-Za-z.\-']+...)\s*[|｜/–—-]\s*((?:...)(?:Owner|Producer|Manager|...))"
```

两件事同时让它落空：

1. **Roman 这种落款根本没有分隔符** —— 姓名、职位、公司是三行。10 封里有 2 封是这个形状。
2. **86 号当初就是照着 AB Medina 那封写的，而那封信里的字符不是 `|`。**
   库里 `id=3893` 的原文是 `'AB Medina I Producer/Owner'` —— 一个大写字母 I。
   测试用例里写的是 `AB Medina | Producer/Owner`，所以测试一直是绿的，
   而它要读的那封真信，一次都没匹配上。

还有两处是「读到了也没进书」：

* `read()` 返回 `contact_title`，`apply()` 的写入清单是
  `("phone", "website", "contact_name")` —— **职位读出来就扔了**。
  书里 1318 家，1262 家 `title` 是空的。
* 官网写成 `www.alternis.com`。书里 977 个官网**没有一个**带 `www.`，
  也没有一个带 `http`。写进去的是一个和全书格式不一样的值。

社媒那条路上，`inbound.process_threads` 存完 `inbox_messages` 就结束了，
**从来没有调用过 `reply_details`** —— WhatsApp / Instagram / Facebook 的回信里
客户报的联系方式，一个字都没进过书。

## R1 落款是一块，不是一行

不再指望姓名和职位挤在一行里。改成先定位**落款块**，再在块里按行认：

落款块的锚点是这两样中任意一样：

* 一行落款语（`Sincerely` / `Regards` / `Best` / `Thanks` / `감사합니다` / `谢谢`），或
* 一行带标签的联系方式（`m:` / `e:` / `w:` / `C:` / `Tel:`）。

块里逐行判断，只认三种行：

| 行 | 判据 |
|---|---|
| 职位 | 整行拆成词（`/` `&` `,` 也算分隔）后**每个词**都在 `contact_names.TITLE_WORDS` 里 |
| 姓名 | 紧挨职位行上面那行，且过 `contact_names.is_sayable`（86 号不碰 `personalize`，这里也不碰） |
| 公司 | 紧挨职位行下面那行 —— **只用来定位，不写库**，理由见「没做的」 |

同一行里带分隔符的老写法继续认，并且把 ` I `（空格夹一个大写 I）加进分隔符 ——
不是为了好看，是因为库里那封真信就是这么写的。加它是安全的：分隔符右边必须命中职位词，
`John I Smith` 不会因此变成职位。

## R2 职位要落到书上

`title` 进入 `apply()` 的写入清单。这一列 96% 是空的，而落款里客户自己写着 `CEO`。

职位不是装饰：`contact_roles` 就是按 `title` 判断谁是决策人的，
[37 号](37-spec-decision-maker-radar.md)的整个雷达都建在这一列上。今天它读到的是 86 个联系人的职位，
其中一个都不是客户自己在回信里说的。

## R3 邮箱：只认他们自己的那个

回信正文里出现的地址，不是每一个都是「他的邮箱」。
`我们一直跟 tony@absen.com 买` 这种句子，认错一次就是把竞争对手的地址写进了发信目标。

所以一个地址要满足下面**任意一条**才算数：

* 它带着 `E:` / `e:` / `Email:` 这类标签 —— 标签本身就是他在报自己的地址；
* 它的域名和**发信人域名**相同；
* 它的域名和**书里这家公司的官网域名**相同。

外加一条永远的排除：**我们自己的域名**（`mailboxes` 里配置的收发邮箱 + 兜底发件人）。
86 号靠 `own_words()` 切掉引用来防这件事，但客户在自己那段话里写一句
`allen@maxcolorvisual.com` 是完全正常的，那不该被读成他的地址。

社媒没有发信人域名，所以社媒回复里只有前两条中的第一条和第三条能成立 —— 这是对的，
一条 WhatsApp 预览里裸着的地址本来就不该直接进书。

## R4 写进联系人，否则会被同步冲掉

今天 `apply()` 直接 `UPDATE leads SET phone=...`。而 `contacts._sync_lead()` 会把
**主联系人**的 name / title / email / phone / linkedin **无条件**刷回 `leads` ——
包括刷成 NULL。也就是说：从回信里补进 `leads.phone` 的号码，
在任何人下一次编辑这家公司的联系人时会被静静抹掉。

所以补全的落点改成：

1. 有「写这封信的人」（`replies.py` 已经知道 `contact_id`）→ 填他；
2. 否则有主联系人 → 填主联系人；
3. 一个联系人都没有 → 照旧直接填 `leads`。

填的是联系人表里**空着的列**，走 `contacts.update()`，主联系人的同步由它自己完成。
`website` 不在联系人表上，它照旧直接写 `leads`。

回填走同一条路：`inbox_messages.contact_id` 早就记着这封信是谁写的，
读回来当 `contact_id` 用。实测差别是真的 —— Blipbillboards 的落款是
`mwatson@blipbillboards.com` 写的，不带这一条，`Senior Account Executive`
会被写到 `customersupport@` 那一行上。

## R5 社媒回复走同一条路

`inbound.process_threads` 存下一条 `kind='reply'` 之后，调 `reply_details.apply()`。

WhatsApp 的预览里出现完整落款的概率不高（只有 500 字预览），但成本是四行代码，
而 Allen 问的就是「ins、wa、fb 有回复的话」。少读一条路等于这条路永远读不到。

## R6 只填空，永不覆盖（86 号 R5 原样保留）

新加的三个字段（职位、邮箱、公司）和老的三个一样：空着就填，有值就跳过。
理由没变 —— 库里的值有它的来处，落款只能证明「还存在另一个值」，
不能证明「原来那个是错的」。

`phone` 那条「一列垃圾不算值」的例外照旧，不扩大到别的列。

官网顺手去掉 `www.` 前缀，理由在上面：全书 977 个官网都是裸域名。

## 验收

1. Roman 那封信 → 读出 `contact_name='Roman Gerashenko'`、`title='CEO'`、
   `email='roman@alternis.com'`、`phone='+19174959116'`、`website='alternis.com'`。
2. AB Medina 那封信的**真实原文**（`AB Medina I Producer/Owner`）→ 读出姓名和职位。
3. 正文里写着 `allen@maxcolorvisual.com` → **不**被读成客户的邮箱。
4. 正文里写着 `我们跟 tony@absen.com 买`（域名既不是发信人的也不是官网的、也没标签）
   → **不**入库。
5. 书里已有电话/官网/姓名 → 一个都不改，返回 `{}`。
6. 这家公司有主联系人 → 补全写在 `contacts` 上，`leads` 由同步得到相同的值；
   之后再 `contacts.update()` 一次，补进去的值**还在**。
7. 回信来自一个非主联系人 → 补的是那个人的行，不是主联系人的行。
8. Instagram / WhatsApp 的一条回信预览里带标签的联系方式 → 同样入库。
9. 引用区里我们自己的落款 → 依旧一个字都不读（86 号 R5 的老测试保持绿）。

## 回填

`python -m app.reply_details`（预览）/ `--apply`（写入）把库里已存的回信重新读一遍。
10 封信里有 2 封带完整落款，它们的姓名和职位今天还是空的。

## 没做的

* **不写公司名。** Allen 问到了，实测答案是：`leads.company_en` 是 `NOT NULL`，
  全库 1318 家没有一家是空的，这一列结构上就不可能「缺」。
  落款里的公司名只用来定位块。
  落款上的公司名和书里不一样是另一个问题（是「书里这个名字对不对」，不是「书里少了什么」），
  那要人来判断，不在这份规格里。
* **不改自动回复的判定。** `id=2357` 那封 `I am traveling 8/28 and will respond Monday 8/31`
  今天被记成了真人回信 —— 那是 `is_auto_reply` 的漏，另开一份。
* **不因为读到了新邮箱就去发信。** 写进书是写进书，发不发由发信那条路照旧决定
  （日限额、do-not-contact、退信抑制一条不动）。新写进去的地址 `email_status` 留空，
  由既有的校验路径去判定。
* **不动 `personalize.looks_like_a_person`。** 98 号说过它是共用的闸，这份规格只用它，不改它。
* **不修 `_sync_lead` 本身。** 回信来自一个**非主**联系人时，补全同时落在他的联系人行和公司行上；
  公司行那一份将来仍可能被主联系人的同步刷掉（[17 号](17-spec-company-multi-contact.md)让主联系人
  无条件覆盖公司那五列，包括覆盖成空）。联系人行那一份不会丢。
  把「主联系人不该覆盖成空」改对是 17 号的账，改它要动所有联系人编辑路径，不在这份里。
