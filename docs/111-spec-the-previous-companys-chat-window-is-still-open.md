＃ 111 — 上一家公司的聊天窗还开着

## 09-08 发生的事

| 本地时间 | 记录里发给 | 正文写的是 | 实际落在 |
|---|---|---|---|
| 10:02 | #972 PixelFLEX（`PixelFlexUSA`） | Hi Steve Paladino… | PixelFLEX ✓ |
| 11:33 | #1337 EKM Exports（`EKMexports`） | Hi El Sundew, You export roughly 3 million cartons of produce annually… | **PixelFLEX 的聊天窗** |

Allen 看到的是「PixelFLEX 怎么被发了两次」。不是两次：第二条是写给另一家公司的信，
落在了 PixelFLEX 的对话框里。一家真的 LED 客户，收到了一封谈农产品出口的开发信。

`send_log` 两条都记着「已发送」，收件人写的是各自的 handle。**记录是错的，而且它不知道自己错了。**

## 为什么闸门没拦住

[docs/61](61-spec-dm-not-comment.md) 和 [docs/99](99-spec-the-box-that-would-not-name-itself.md)
早就立过规矩：写进哪个输入框必须确定是这一家的，拿不准就拒发。`_dm_composer` 现在的顺序是：

1. 标签里写着这一家名字的框 —— 有且只有一个，就是它；
2. 有两个及以上聊天框 —— 拒发（docs/61 的原案）；
3. **只有一个聊天框 —— 就是它**。

第 3 条依赖一句写在它自己 docstring 里的假设：

> a real navigation destroys every dock that was open before.

**这句话对 Facebook 不成立。** FB 的聊天浮层挂在 Messenger 外壳上，`page.goto` 到另一家
公司的主页之后，它照样开着——[docs/110 R4](110-spec-the-dm-is-already-standing-on-their-page.md)
昨天刚为另一件事写下同一个事实（浮层会把我们自己发的话混进主页文字里），却没有回头看这里。

于是 11:33 那一轮：导航到 `facebook.com/EKMexports`，EKM 的聊天窗没打开（或还没渲染出来），
PixelFLEX 的浮层还在——页面上「只有一个聊天框」，第 3 条把它交了出去。
标签写着「发消息给PixelFlex LED」，跟 `EKMexports` 对不上，但第 3 条根本不看标签。

## R1 点「发消息」之前，先把已经开着的框标记成「上一家的」

导航之后、点击「发消息」之前，给页面上每一个可见输入框打一个 `data-mc-stale="1"`。

这一步不需要认识任何公司名字：**这一刻页面上开着的框，没有一个是我们要的**——
我们还没点那个按钮。身份不再靠标签推断，靠「它是不是我们这一次点出来的」。

## R2 只在新出现的框里选

`_dm_composer` 从此只在没被标记的框里挑，规则不变（认名字优先、两个以上拒发、
评论框永远不算）。

**一个新框都没出现时**：说明「发消息」没点开新窗口，通常是这一家的窗口本来就开着。
只有当某个旧框的标签明确写着这一家的名字，才用它；否则拒发，并把看到的标签写进错误里。

这条会误伤一种情况：同一家公司当天第二次发，而 FB 的标签写的是公司全称、我们手里是
handle（`rentexrentals` vs "Rentex Audio Visual & Computer Rentals"，docs/99 R2 那个），
对不上就拒发了。**这个代价是对的**：拒发一次，少发一条；发错一次，一家真客户收到
写给另一家的信，而且我们的记录还说发对了。

## R3 读主页只读主内容区，不读整个 body

[docs/110](110-spec-the-dm-is-already-standing-on-their-page.md) 让私信发完顺手读一遍主页。
浮层既然会留在页面上，`inner_text("body")` 读到的就不只是这家公司的主页，还有上一家
公司的整段对话。

所以读 `main` / `div[role="main"]`——主页内容在里面，浮层不在。读不到或内容太短时才退回 body。
R4 那条「删掉我们自己刚发的话」继续有效，它挡的是同一个浮层的另一半。

## R4 已经发生的那一条，两边都要说实话

EKM 的记录说「facebook 已发送」，PixelFLEX 的记录说「已发送一条」。两条都不准确。
给两家各写一条备注写明当天发生了什么，不改发送记录本身——发送记录是当时系统相信的事，
备注是后来查清的事，两者都留着才看得出这个错误是怎么被发现的。
