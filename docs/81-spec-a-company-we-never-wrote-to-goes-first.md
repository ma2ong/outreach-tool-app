＃ 81 — 一家从没写过的公司，排在已经不理我们的前面

## 从「今日邮件计划只有两封」查出来的

那个问题本身不是 bug：当天 60 封额度早上就发完了。但顺着查下去，发现补量的路只有一条，
而且是**次好的那一条**。

`autosend._top_up`（[docs/73 R3](73-spec-recontact-cooldown.md)）在到期跟进不够额度时补人，
候选来自 `recontact.reapproachable`：

```sql
WHERE o.channel = ? AND o.status = 'messaged'
  AND o.message_sent_date <= date('now', '-14 days')
```

`o.status = 'messaged'` 是一道硬条件：**必须已经写过。** 所以能被补进来的，
只有那些「已经收到过我们的信、并且没有回」的公司。

数出来的结果：

| | 家数 |
|---|---|
| 邮箱可用、从没进过任何序列 | 598 |
| 其中已经群发过、只是没进序列（`_top_up` 捞得到） | 507 |
| **其中一封邮件都没写过（没有任何路径捞得到）** | **94** |

两个池子**零重叠**：一个是「从没写过」，一个是「写过、冷了」。

这 94 家不是垃圾数据——NUMMAX、Genoptic Smart Displays、Xtreme LED Screens
都是真的北美 LED 公司，前十家全部带着从官网读出来的开场白。它们只是从来没有过一条入口。
其中 #169 RAON VISUAL 今天早上的销售计划里还专门点名过「99 天逾期跟进」——
计划想联系它，而没有任何代码路径能把它排进去。

「没写过」按**渠道**算：一家在 Instagram 上私信过、但从没发过邮件的公司，
在邮件这边仍然算没写过。渠道之间不互相抵消。

## 为什么会漏

三条入口，各自管一段，中间正好空出一块：

| 入口 | 管谁 |
|---|---|
| `executors._enroll_imported` | 开发时**新导入**的客户 |
| `autosend._top_up` → `reapproachable` | **写过、冷了 14 天**的客户 |
| —— | **早就在库里、但一封都没写过的** ← 没人管 |

这块是历史留下的：小满导入（[docs/54](54-spec-import-existing-customers.md)）和
`_enroll_imported` 上线之前的那些开发批次，进库的时候还没有自动入序列这回事。
不是设计成这样，是没人回头看过。

## R1 补量先补没写过的

`_top_up` 的候选改成两段拼接，**没写过的在前**：

```python
candidates = outreach.never_touched(conn, "email") + recontact.reapproachable(conn, "email")
```

顺序不是随便定的。**一家从没听说过我们的公司，比一家已经看过一封信并且没回的公司更值钱。**
现在的代码把唯一的入口留给了后者，这是反的。

其余不动：`can_be_addressed` 照过、`_sequence_for` 照选段（[docs/76](76-spec-copy-by-customer-type.md)）、
`gap` 照封顶。补的只是候选从哪儿来，不是一天发多少。

## R2 没写过的那一段，有开场白的排前面

和 [docs/80 R3](80-spec-no-hook-is-not-a-reason-not-to-write.md) 同一条规矩：
说得出对方事情的排前面，说不出的排后面，但都发。

## R3 不重复 `reapproachable` 的排除项

`never_touched` 和它排除同样的东西：`do_not_contact`、`stage` 是 `won`/`lost`、
邮箱为空或 `invalid`。**已成交的客户绝不进冷邮件序列**——那正是
[docs/54](54-spec-import-existing-customers.md) 存在的理由。

## 这不会让今天多发信

`_top_up(gap)` 只补到当天额度，一封都不会多。变的是**同样 60 封写给谁**：
先写 94 家没写过的，写完了才回到已经不理我们的那批。94 家两天就走完，
之后一切照旧。

## 验收

1. 一家邮箱可用、从没写过、没进序列的公司，会被 `_top_up` 补进序列
2. 同时有「没写过」和「冷了 14 天」的候选时，没写过的先进
3. `stage='won'` 的客户不会被补进来
4. 一天发出的总数不变，仍然封顶在当天额度
5. 有开场白的排在没有开场白的前面
