＃ 59 — 记住哪些号码不在 WhatsApp 上

## 每发一次，发现一次，扔掉一次

Allen 手动发 WhatsApp 时发现「好多号码都没有 WA 账号」。

系统其实**已经知道**。`playwright_engine._send_op` 里就有这段：

```python
# invalid/unregistered number surfaces a dialog instead of a chat
if page.get_by_text(re.compile("invalid|not.*valid|isn't on whatsapp|无效", re.I)) ...:
    raise RuntimeError("number not on WhatsApp")
```

但这个 RuntimeError 被 `channel_outreach` 当成一次普通失败接住，只写进 `errors` 列表，**发送
结束就没了**。所以同一个号码明天照样进队列、照样跑一趟浏览器、照样发现它不存在。

855 个有电话的客户里，`whatsapp_verified` 只有 7 个是 1，848 个是 0——而 0 既表示"查过，没有"，
也表示"从来没查过"。这个字段全代码库没有一处在写它，它是个死字段。

## R1 「没查过」和「查过、没有」必须分得开

新字段 `whatsapp_status`，取值和 `email_status` 一个路数：

| 值 | 含义 |
|---|---|
| `NULL` | 没查过 |
| `active` | 发出去了，说明号码在 WhatsApp 上 |
| `none` | 打开对话时 WhatsApp 明说这个号码不存在 |

分不开的代价是具体的：把"没查过"当成"没有"，会白白丢掉几百个能联系的客户；把"没有"当成
"没查过"，就是现在这样，每天重新发现一遍。

**只有 WhatsApp 自己说的才算 `none`。** 超时、页面没加载出来、浏览器崩了——这些是我们这边的
问题，不是关于这个号码的事实（[45 号 spec](45-spec-truthful-lead-facts.md)）。写不出出处的
结论不能装作知道。

## R2 记下来的事实要真的挡住下一次

`none` 的号码不再进社媒队列，也不再被 `eligible()` 选中。

这一条不是可选的：R1 的全部价值就在这里。只记录不拦截，等于把观察结果存进一个没人读的表。

## R3 发成功了也是一条事实

送达即证明这个号码在 WhatsApp 上。顺手记 `active`，下次就不用再验。

## 不做的事

- 不批量"预检"号码。挨个打开 wa.me 探测几百个号码，是一种很容易被判定为滥用的行为模式，
  代价是这个 WhatsApp 账号本身。**只在正常发送的过程中顺带记录**，不额外制造流量。
- 不因为号码不在 WhatsApp 上就把线索标成不可联系——邮件和 Instagram 还在
- 不清空 `whatsapp_verified` 这个旧字段（本 spec 不动它，它是别处的历史遗留）

## 验收

1. 一个 WhatsApp 明说不存在的号码，发送后 `whatsapp_status='none'`
2. 这个号码第二天不再出现在社媒队列里
3. 一次超时或浏览器错误，不会把号码标成 `none`
4. 发送成功的号码记 `active`
