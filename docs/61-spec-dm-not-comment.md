＃ 61 — 私信就是私信，绝不能发成公开评论

## 发生了什么

Allen 的开发信出现在了一个 Facebook 主页帖子的**评论区**，署他的实名，公开可见：

> Allen Ma — Hi, Saw the rental work you do around Los Angeles. We're an LED display
> manufacturer and work with rental and AV companies directly…

它本该是一条私信。

原因在这一行：

```python
box = page.locator("div[contenteditable='true'][role='textbox'], ...").first
```

Facebook 主页上，帖子下面的**评论框**也是 `contenteditable` 的 `role=textbox`，而且在 DOM 里
排在聊天窗之前。`.first` 抓到的是评论框，`Enter` 于是把冷开发信发成了公开评论。

## R1 没确认在私信框里，就不准打字

这不是选择器调优的问题，是顺序问题：**先确认，再输入**。

输入之前必须确认光标所在的框位于一个私信容器里（Facebook 的聊天 dock、Instagram 的会话
窗）。确认不了就**中止这次发送并报错**，不要退而求其次找一个"看起来像输入框"的东西。

发错渠道的两个方向不对等：

- 中止的代价：这条线索今天没发出去，明天再发
- 发错的代价：一条公开的、署实名的推销评论挂在潜在客户的主页上，删不删得掉由对方决定

**所以宁可不发。**

## R2 图片没点发送，就是没发出去

Instagram 那边：附件选好之后，代码等 4 秒就 `return True`。

```python
page.locator("input[type='file']").last.set_input_files(image)
page.wait_for_timeout(4000)
return True
```

但 Instagram 附上图片后是**放进输入框等你点发送**，不是立即发出。所以文字发出去了，图片一直
挂在那儿，而系统记的是"已发送"。

WhatsApp 那条路径（`_wa_attach_image`）本来就是对的——附件之后明确地点发送按钮。Instagram
照做。

### R2.1 发没发出去，要看得见的东西说了算

等待若干秒不是确认。附件从输入框里消失（或者出现在会话记录里）才是发出去了。等不到，就报
错，不要记成成功——一条"已发送但其实没发"的记录，比失败更难查。

## 不做的事

- 不改文字发送的时序（文字这一半一直是对的）
- 不在评论区做任何事，包括点赞、回复——这个系统只走私信

## 验收

1. 一个能私信的 Facebook 主页：消息进私信，评论区没有任何新增
2. 一个关闭了私信的主页：报错中止，评论区没有任何新增
3. Instagram 带图发送：图片出现在会话里，不是挂在输入框
4. 图片确认不了发出，这次发送记为失败
