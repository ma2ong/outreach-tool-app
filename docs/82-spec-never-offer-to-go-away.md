＃ 82 — 不许在信里主动提出离开

## Allen 的原话

> 以后的邮件或者社媒，wa 私信不能出现类似这样的话：**If ours won't mix with your stock
> I'll say so and leave it there.**……我们要引导他给我回复，要让对方感觉到兴趣才行。
> 什么如果我们的产品无法与你们现有的库存混用，我会直接告诉你，也就不再打扰了。
> 这样的话太烂了。不要再说如果觉得打扰到你就跟我说，我以后不联系你了之类的无关痛痒的
> 废话。**不允许你这么说。**

他还说了一句更重要的：**去看他自己发过的信。**

## 我去看了。3031 封，2022 到 2025，他自己写的

`backend/xiaoman_raw/sent.json` 里存着他小满账号发出的每一封。抽掉 agent 2026 年 8 月
之后写的，剩下 2956 封是他本人。挑收到过回复的那 26 封，和所有冷开场，看开头：

**韩语（他的主力市场）**

> 안녕하세요~ 심천 LED 전광판 업체 맥스컬러입니다. 저희 회사의 최신 **R3 시리즈** 실내/실외
> 렌탈형 **500×500 & 500×1000mm** LED 디스플레이 제품을 소개드립니다…
> 관심하신 제품 있으시면 연락주세요~

主题行：`전후면 유지보수 OK! R3 렌탈형 제품 만나보세요`、
`고해상도·방수·곡면 지원! 렌탈용 R3 LED 시리즈 제안드립니다`

**英语**

> Hi, I hope this email finds you well. I'm writing to you today to introduce our latest
> **P3.91 500x500** Rental M Series…
> Hello, friend~ I am Allen from Shenzhen Maxcolor. I am pleased to introduce our new
> **COB (Chip on Board)** models…

主题行：`Maxcolor Rental M Series`、`Exclusive Offer: Two New COB Models for Your Consideration`

**三个共同点，一条都不在现在的文案里：**

1. **一上来报出工厂和自己的名字**——「심천 LED 전광판 업체 맥스컬러입니다」/
   「This is Allen from Shenzhen Maxcolor」
2. **主角是一个具体产品**——R3 系列、P3.91 500×500、COB 新款，带箱体尺寸、带亮度、带维护方式
3. **结尾是邀请**——「관심하신 제품 있으시면 연락주세요~」

**一次都没有出现过的：** 道歉、说自己可能不合适、主动提出以后不再联系。
四年 26 个回复，没有一封是靠「不合适我就不打扰了」换来的。

## 现在 agent 写的是什么

```
We build LED panels in Shenzhen. What pitch and cabinet are you on now?
If ours won't mix with your stock I'll say so and leave it there.
```

主题行是 `{company} — which cabinet are you running?`——**一个关于对方的问题，
没有产品**。然后正文用一句「不合适我就不打扰了」收尾。

这是西方 SDR 那套「低压力、给对方台阶」的写法。它在这里失效的原因很直接：
**对方本来就没有压力**——一封来自陌生中国工厂的冷邮件，删掉的成本是零。
主动给一个不存在的压力递台阶，唯一的作用是**替对方把「不回」这个选项说出了口**。

## R1 禁止「退出语」，这是硬规则

以下形状的句子，任何渠道、任何语言、任何一封信里都不许出现：

| 形状 | 现在库里的实例 |
|---|---|
| 提出以后不再联系 | `I'll say so and leave it there` / `더 연락드리지 않겠습니다` |
| 声明这是最后一封 | `Last note.` / `마지막 메일입니다.` |
| 替对方把「没有需求」说成一个好答案 | `If panels aren't on your plan, that's a fine answer.` |
| 说自己会就此打住 | `Point me at whoever handles displays and I'll stop here.` |
| 贬低自己值不值得对方的时间 | `that tells me whether we're worth your time` |
| 怕占用对方收件箱 | `I don't want to fill up your inbox`（2026-08 那批里有） |

**不给例外开关。** 这条和价格那条同级：`message_guard` 在发送前判定最终文本，
命中就拦下，理由写清楚。放在那里而不是只放在种子文案里，是因为文案是数据库里的行，
从界面上改得动——规则要长在发送路径上。

## R2 每封信必须给对方一个能回的具体东西

「引导他给我回复」不是加一句「期待您的回复」。是给一个**具体到可以回一行字**的东西：
一个系列名、一个箱体尺寸、一个 pitch 区间、一张当天能拿到的规格书。

这正是他自己那些信在做的事。所以开场重写成他的顺序：

> 报出工厂和人 → 摆出一个具体产品和它的参数 → 用一个当天兑现的承诺邀请回复

主题行也从「关于对方的问题」改成「一个产品加它最硬的那个参数」——
和 `전후면 유지보수 OK! R3 렌탈형` 是同一个写法。

## R3 第三封不是告别信，是把最有用的东西给出去

原来的第三封整封都是退出语。改成：把我们做的全部范围摆一遍，
留一个「随时来，当天给规格书和报价」的口子。

**不写价格。** 产品库里有价格区间，但 `message_guard` 的第一条就是自动化的冷邮件
不能代替 Allen 定价——那条不动。

## R4 说「我们是制造商」，不强调「我们自己造」

Allen：

> `we build the panels ourselves.` 这句话表达方式也不好，可以说我们是 LED 显示屏的制造商
> 或者工厂，**但不要强调我们自己制造的**。

「ourselves / 直接 / 자체 공장에서」这类强调在信里是**替一个没人提出的质疑辩护**——
对方还没怀疑我们是不是贸易商，我们先急着否认了。他自己的信从来只是平铺直叙地报身份：
`I am Allen from Shenzhen Maxcolor` / `심천 LED 전광판 업체 맥스컬러입니다`。

改成：`Shenzhen Maxcolor Visual, an LED display manufacturer in Shenzhen` /
`심천 LED 디스플레이 제조업체 맥스컬러`。是事实，不是辩解。

## R5 收尾是提供，不是指派

Allen：

> `Tell me the pitch and cabinet size you work with and I'll send the spec sheet…`
> 这部分内容很不好，说不出来的感觉，总感觉怪怪的，**有点命令对方的感觉**。

他说的是对的，而且能说清楚为什么：`Tell me X and I'll send Y` 是一笔**交易**——
它在对方还没同意做生意之前，先给对方派了一个活。收件人和我们素不相识，
凭什么先干活。

他自己的收尾从来是**报告我这边随时可以**，动作留给对方自己决定：

> 관심하신 제품 있으시면 연락주세요~ ／ Please check and let me know

所以句式从祈使句改成条件句 + 我方意愿：

| 改前 | 改后 |
|---|---|
| Tell me the pitch and size and I'll send the sheet the same day. | If any of this is close to what you use, I'd be glad to send the spec sheet. Just let me know which pitch, whenever it's convenient. |
| 크기만 알려주시면 당일에 사양서 보내드리겠습니다. | 검토하시는 사양과 비슷하다면 사양서 기꺼이 보내드리겠습니다. 편하실 때 말씀만 주세요. |

**「当天」的承诺也一并去掉了。** 它本来是想显得利落，实际读起来是在给这件事加时钟——
对方并没有在赶时间。R2 要的是「给一个具体、能回的东西」，那个东西是**规格书**，
不是交付它的速度。

## R6 「没问题」「没关系」也不许说

我第一版把这条锚在「不需要也没关系」那个语境上，放过了 `Shipping to Brazil? No problem
at all, we do it weekly.` ——理由是它说的是能力不是退让。Allen 的判断是「这两句也很垃圾
不能放」，他是对的。

**「没问题」在回答一个没人提出的抱怨。** 对方还没说这件事难办，我们先表态说不难办，
等于承认它本来该难办。从能力出发的说法更短：

> ~~Shipping to Brazil? No problem at all, we do it weekly.~~
> **We ship to Brazil weekly.**

## R7 主题里不许出现公司名——我们的和对方的都不许

Allen：

> 邮件主题永远不要出现公司名，除非很出名的上市公司，不然别人一看你的名字就不会看了。
> **直接从名字就能够判断出这个邮件值不值得看。**

两个名字都要去掉，理由正好相反：

- **我们的名字**（Maxcolor）对方不认识。主题还没说任何事情，就先自报了一个陌生供应商。
- **对方的名字**放在主题开头，是群发的标志。没有人会把客户自己的公司名打进主题行，
  只有机器会。

剩下的部分必须靠内容本身换来打开——这正是他自己的主题在做的事：
`전후면 유지보수 OK! R3 렌탈형 제품 만나보세요`、`Exclusive Offer: Two New COB Models`。

`{company}` 挪到正文的收尾句里。个性化闸照样过，但它不再是对方看到的第一样东西。

## R8 品牌名只出现一次，在签名里

> 不要老是强调自己是 Maxcolor，如果能不提的话也可以不提。

正文里报一次身份就够，而且不用报品牌：`I'm Allen, handling export sales for an LED
display manufacturer in Shenzhen.` 品牌名在签名档里，它本来就在那儿。

## R9 `{fit}` 整个删掉

> built for crews that reload every week, and sized to mix with stock you already own

这是形容词堆砌，而且它上面那段已经用数字把同一件事说完了。

## R10 中性版和固定安装（英语）只发一封

> 冷邮件英文中性版第 2、3 封整个都很垃圾，直接删去，永不复用。固装版第二三封也删去。

删掉之后要把理由写下来，因为它能推广：**这两个分段恰恰是最没话说的两个。**
中性版存在的前提就是我们不知道对方做什么；固定安装的项目跟着工程日历走，不是周历。
给这两类写第二封第三封，只能把同一个提议换个说法再说一遍——那就是骚扰的定义。

保留三封的分段，是因为后续那封真的带着开场白没有的东西：租赁客户的箱体存量、
户外项目的视距。

**顺带修的**：那两条序列改名成「冷邮件单封」。一条只发一封的序列叫「3 步跟进」，
是今天每个 bug 都有的那种静默错位。77 个卡在已删除的第 2 封上的入组标记为完成——
它们永远不会再收到任何东西，挂着 active 只会让每个计数都是错的。

## R11 开场白不许和分段互相矛盾

Allen：

> 都固定安装版了还说 `Saw the rental and touring work you do around Tampa.`？
> 为啥还出现 rental 租赁这个词？**是不是明显有错的。**

是。开场白是从对方官网读来的，分段优先看 Allen 手打的标签——两者可以不一致。
库里**有 23 家正是这样**：他手打了「工程商」，而官网写的是 rental。

谁都没错，所以谁都不推翻：**开场白直接不写。** 信照样成立，就跟一家本来就没有开场白的
公司收到的一样（docs/80）。

## 事实出处（docs/45）

| 写进文案的 | 出处 |
|---|---|
| P0.7-P1.8 / P2-P3 / P2.6-P3.9 / P3.9-P4.8 / P4-P10，及各自亮度 | `products` 表，`agent_approved=1` |
| 室内 600-800 nits | Allen 更正：室内一般 600~800，最高可到 1000，一般说 600~800 就够。`products` 和 `quote.py` 都已改 |
| R3 系列、500×500 与 500×1000mm 箱体、前后维护 | 他 2025-06 自己发的韩语邮件，同一批发了七封 |
| 深圳自有工厂 | 他每一封信里的自我介绍 |

R3 那几个数字是从他自己的信里抄的，不是我编的。**如果箱体尺寸已经变了，改这里。**

## 验收

1. 六个分段 × 两种语言的开场白里，一句退出语都搜不到
2. 第三封里没有「最后一封」「没需求也没关系」
3. 每个开场白里有：工厂自称、一个具体产品参数、一个具体可交付的东西（规格书）
3.1 自称是「制造商」，不是「我们自己造」；收尾是条件句不是祈使句
4. `message_guard` 拦下任何含退出语的最终文本，且理由说得出是哪一句
5. 价格仍然一分钱都不许出现
6. 社媒私信（含 docs/80 的通用话术）同样过这道检查
