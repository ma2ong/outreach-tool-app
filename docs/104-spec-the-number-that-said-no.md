＃ 104 — 它早就告诉过我们了

## 一句中文，一年没人听懂

Allen 09-04 截了一张图：WhatsApp 网页版正中间弹着一个框。

```
电话号码+27 12 809 1494没有注册 WhatsApp。
                                    [确定]
```

而 `_send_op` 里认这句话的正则是：

```python
re.compile("invalid|not.*valid|isn't on whatsapp|无效", re.I)
```

**「没有注册」一个都不匹配。** 于是这个框被当成不存在，代码接着去等聊天输入框
（`footer div[contenteditable='true']`）—— 而这个框根本不会出现，因为弹窗后面没有聊天。
等满 45 秒，失败，什么都没学到。

`channel_outreach._NOT_ON_WHATSAPP` 是同一个毛病的第二处：

```python
re.compile(r"not on whatsapp|number not on|invalid|不存在|无效", re.I)
```

也没有「没有注册」。

## 代价：一条规则从上线到今天一次都没生效过

[59 号 spec](59-spec-remember-a-dead-number.md) 说：WhatsApp 告诉我们这个号码没有账号，
就记下来，不要每天重新发现一遍。库里的实情：

| `whatsapp_status` | 家数 |
|---|---|
| （空） | **1318** |
| `active` | 2 |
| `none` | **0** |

**一次都没记下来过。** 于是同一批死号码每天重新排进队列、每天重新弹一次同样的框、每天
浪费一次浏览器行程 —— 这就是 Allen 说的「总是这样显示」。不是偶发，是每天。

`_channel_for` 里那句 `whatsapp_status == "none"` 的跳过逻辑，因此也从来没跳过任何一家。

## R1 按它真正说的话认，不按我们猜它会说的话认

弹窗文案至少这几种写法（中文界面、英文界面）：

```
电话号码 +27 ... 没有注册 WhatsApp。
Phone number +27 ... is not on WhatsApp.
The phone number ... is not registered on WhatsApp.
```

判据要**同时**满足两件事：这句话里有 `WhatsApp`，并且带着一个否定标记
（`没有注册` / `未注册` / `is not on` / `isn't on` / `not registered` / `无效` / `不存在`）。

两个条件缺一不可，因为 `page.get_by_text` 搜的是**整页**，而 `?text=` 已经把我们自己的
正文预填进了输入框 —— 只按「invalid」这类词去搜，一句碰巧写着 "not valid" 的开场白就会
被读成「这个号码不存在」，然后 59 号会把一个好号码永久标死。

`WhatsApp` 这个词是安全的判据，因为**我们发出去的四类文案里一次都没出现过这个词**（实测
0 处）。它只会出现在平台自己的话里。

## R2 认出来之后要把框关掉

点掉那个「确定」。

不关也能跑 —— 下一条会 `page.goto` 一个新地址，导航会清掉弹窗。但留着它意味着这个浏览器
窗口停在一个报错状态上，而这个窗口是 `headless=False`、就摆在 Allen 桌面上的。一个自动化
留在屏幕上的报错框，会被关掉，然后整个 context 就没了。

关框是一行，代价为零；不关的代价是别人替我们关。

## R3 认不出来的时候，等待要短

即使 R1 漏掉了某种新写法，也不该花 45 秒去等一个不会出现的输入框。

输入框等待从 45 秒降到 **20 秒**。一个正常的聊天页在网络正常时几秒就绪；45 秒只在
「它永远不会来」的情况下才会被用满，而那正是我们要快速失败的情况。

失败之后照旧顺延（[92 号 R4](92-spec-the-clock-that-decides-is-ours.md)），不重试。

## R4 记下来这件事，比这一条发不发出去重要

R1 认出之后抛出的错误必须能被 `_NOT_ON_WHATSAPP` 匹配上，`leads.whatsapp_status` 才会
写成 `none`，这个号码才不会明天再来一次。两条正则各自独立地漏掉了同一句话，所以这次让
引擎抛一个**固定的英文串** `number not on WhatsApp`，两边只对这一个词组负责，不再各自
猜平台的措辞。

## 验收

1. 页面上有「电话号码 +27 ... 没有注册 WhatsApp。」→ 判定为号码无效。
2. 英文写法 `Phone number ... is not on WhatsApp.` → 同样判定。
3. 我们自己的正文里出现 `not valid` 而页面上没有 WhatsApp 的弹窗 → **不**判定为无效。
4. 判定为无效后，页面上的「确定 / OK」被点掉。
5. 抛出的错误能被 `channel_outreach._NOT_ON_WHATSAPP` 匹配 → `whatsapp_status='none'`。
6. 标成 `none` 的公司不再进入社媒队列的 whatsapp 渠道。
7. 输入框最多等 20 秒。

## 没做的

* **不改电话号码的取法。** [62 号](62-spec-a-number-we-cannot-dial.md)、[83 号](83-spec-the-wa-label.md)
  管的是「哪个号码该拨」，这份管的是「拨过去之后它说了什么」。有些号码本来就没有
  WhatsApp，那不是取号取错了。
* **不因此把这些公司标成 do-not-contact。** 号码上没有 WhatsApp，不代表这家公司不能碰 ——
  邮件和其他社媒渠道照旧。59 号只关掉这一个渠道。
* **不改 `headless=False`。** 窗口该不该出现在 Allen 桌面上是另一件事，还没查清楚
  （09-04 尚在确认浏览器窗口是被谁关掉的）。这份规格只保证我们不再自己制造一个留在
  屏幕上的报错框。
