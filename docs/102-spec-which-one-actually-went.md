＃ 102 — 到底哪一条发出去了

> 写的时候编号是 100，与 Codex 同一小时提交的 100 号（空开场白不是扣信的理由）相撞 ——
> 它比这份先合进 `main`，按 `AGENTS.md` 的规矩后合并的一方改名。那条「Claude 取偶数、
> Codex 取奇数」的规则是 11:45 才写进去的，Codex 12:03 那次提交多半还没拉到。

## 一条没发的信，被记成发过了

09-04 11:54（深圳），[99 号](99-spec-the-box-that-would-not-name-itself.md) 上线后第一轮
自动发送。记录说：

```
{"channels": {"whatsapp": 1}, "failed": 1, "attempted": 2,
 "error": "Page.goto: Target page, context or browser has been closed"}
```

库里的实情正好相反：

| | |
|---|---|
| 队列行 18267（Atlanta Pro AV / whatsapp） | 状态 `sent`，`send_log` 0 条，`outreach` 0 条 |
| `send_log` 里真正发出去的 | #1409，**instagram**，03:56:29 |
| #1409 的队列行 | 状态还是 `ready` |

**成功记在了失败那条身上。** WhatsApp 那条从没发出去，却被标成已发；Instagram 那条发出去了，
队列里还写着待发；`social_last_send_at_whatsapp` 盖了一个没发生过的戳；仪表盘告诉 Allen
「whatsapp 发了 1 条」。

## 为什么：把「成了几条」当成了「成的是哪几条」

`social_autonomy.run_due` 和 `api/social_queue._run_send` 都写着同一行：

```python
sent_ids = [item["id"] for item in items[:result["sent"]]]
```

而 `channel_outreach.send_prepared` 是逐条发的，每条各自成败，**成功的不保证排在前面**。
这一轮 WhatsApp 排第一且失败、Instagram 第二且成功，`items[:1]` 就取到了失败的那一条。

日限额还会让第三种结果混进来：`deferred` 的条目既不在成功里也不在失败里，`items[:sent]`
在那种情况下同样对不上。

一个计数不能回答一个身份问题。这是 [92 号 R5](92-spec-the-clock-that-decides-is-ours.md)
那件事的另一面：那次是「失败了没人知道」，这次是「成功了记错人」，两者都让屏幕上的字
和真实发生的事对不上。

## R1 发送器要报出「哪几条成了」，调用方不许从数量推断

`send_prepared` 返回 `sent_ids`（真正调用成功、并且已经写进 `send_log` 的那些 `id`）。
`run_due` 和 `_run_send` 用它来更新队列状态、盖时间戳、统计每个渠道的条数。

不是补一个排序假设（「让失败的排到后面去」），而是取消这个假设。顺序是发送器的自由，
身份必须由发送器自己说。

### R1.1 队列行被错标成 `sent` 的代价，不能靠重建来兜底

`build_today` 每轮会删掉当天 `edited=0` 的行再重排，所以被错标的 Atlanta Pro AV 明天会
回到队列 —— 这不是理由。`edited=1` 的行（Allen 亲手改过文案的那些）**不会被删**，一条
被错标成 `sent` 的改过的信，就是永久丢失。

## R2 上下文死没死，第一次导航说了算，不是 `new_page()` 说了算

`_page()` 的注释写着「真正用一下这个 context 才是唯一诚实的测试」，但它只在**没有缓存
页面**的时候才走到 `ctx.new_page()`。有缓存页面时它直接 `return live[0]` ——
`page.is_closed()` 是 False，而那个页面所属的 context 已经死了。**缓存那条路上一次
测试都没做过。**

于是下一行 `page.goto(...)` 抛出 `Target page, context or browser has been closed`，
而这正是那段注释当初想根治的错误原文。

改法沿着它自己的道理再走一步：**第一次真实导航就是那个测试**。`_send_op` 的
`goto` 失败在「context 已关闭」这类错误上时，丢掉缓存的 context、重开一次、只重试一次。

重试安全，因为 `goto` 发生在**打任何字之前**：这一步失败意味着什么都没发出去。打字之后
的任何失败一律不重试 —— 那才是会发出两条一样的信的地方。

## R3 一轮里的每一个错误都要留下，不只是第一个

09-03 夜里三个渠道各失败一次，记录里只有一句 `errors[0]`，是社媒取框那个错误。
**WhatsApp 自己的错误从来没有出现在任何地方**，所以它必须被单独问一次才查得到。

记录改成按渠道保留各自的第一个错误：

```json
{"attempted": 3, "failed": 3, "channels": {},
 "errors": {"whatsapp": "Page.goto: ...closed",
            "instagram": "could not confirm this customer's private message box...",
            "facebook": "no Message button on this page..."}}
```

一个渠道一条就够了 —— 同一轮同一个渠道最多发一条（92 号），所以不会更多。

## 验收

1. 两条待发，第一条失败、第二条成功 → 只有第二条的队列行变成 `sent`。
2. 同上 → `social_last_send_at_*` 只盖在真正发成的那个渠道上。
3. 同上 → `last_run.channels` 说的是第二条那个渠道，不是第一条的。
4. 一条被日限额 `deferred` → 它既不算成功也不算失败，队列行保持 `ready`。
5. `goto` 抛出「context has been closed」→ 丢掉缓存 context，重开，重试一次成功。
6. `goto` 第二次仍然失败 → 抛出去，不再重试。
7. 打字之后的失败 → **不重试**（否则会发出第二条一样的信）。
8. 三个渠道各失败一次 → 记录里三条错误都在，按渠道分开。

## 没做的

* **不改「一轮每渠道最多一条」。** 92 号的节流不动。
* **不给失败的条目自动重排。** 92 号 R4 已经说了：错过的时刻顺延，队列第二天照常重建。
  在这里加一层重试队列，是把一个已经有答案的问题再答一遍。
* **不动 `send_prepared` 的发送顺序。** 顺序是它的自由；这份规格改的是调用方不许猜。
