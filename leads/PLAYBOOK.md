# LED Leads — DM 发送 Playbook

> 记录 Playwright MCP 浏览器自动化执行过程中积累的操作规范、已知坑、优化方法。
> 最后更新：2026-05-23

---

## 零 (新增)、一次性全渠道执行原则（2026-05-21 起强制执行）

**每次采集新客户后，必须在同一 session 内完成所有触达动作，不拆分到下一天。**

| 步骤 | 动作 | 工具/脚本 |
|------|------|----------|
| 1 | 搜索候选公司 | WebSearch + Jina |
| 2 | dedup 检查 | python dedup 脚本 |
| 3 | 写 vN+1 采集脚本，生成 Excel | `generate_led_leads_vN+1.py` |
| 4 | 加入各 pipeline | WA: prospects.json; IG: pipeline/instagram/prospects.json; Email: pipeline/email/prospects.json |
| 5 | Instagram warmup（like + follow） | CDP / opencli |
| 6 | Instagram DM 发送 | `cdp_send_dm.py` 或 CDP 手动 |
| 7 | Facebook DM 发送（有 Messenger 的） | CDP |
| 8 | WhatsApp 发送（仅拉美/有手机号） | `wa_send_vN.py` |
| 9 | Email 发送（美国/韩国优先） | `email_sender_korea.py` 或邮件脚本 |
| 10 | 更新 SKILL.md 数据统计 | git commit + push |

**例外**：WA 每日上限 30 条。超过当日配额的 WA 发送，推到次日执行。其他渠道不受此限制。

**美国/加拿大特别规则**：不发 WhatsApp（固话），优先级：Email > IG DM > FB DM。

---

## 零、渠道适用范围（必读）

| 国家/地区 | WhatsApp | 邮件 | Instagram DM | Facebook DM |
|-----------|----------|------|-------------|-------------|
| 巴西 | ✅ 首选（手机普及率极高） | ✅ | ✅ | ✅ |
| 哥伦比亚 | ✅ 首选 | ✅ | ✅ | ✅ |
| 秘鲁 | ✅ 首选 | ✅ | ✅ | ✅ |
| 阿根廷 | ✅ 首选 | ✅ | ✅ | ✅ |
| 智利 | ✅ 首选 | ✅ | ✅ | ✅ |
| 墨西哥 | ✅ 可用 | ✅ | ✅ | ✅ |
| **美国 / 加拿大** | ⚠️ 主动搜索 | ✅ **首选** | ✅ | ✅ |
| 韩国 | ❌ 用 KakaoTalk | ✅ | ✅ | ✅ |

**美国 WhatsApp 搜索规则（2026-05-22 修正）**：
- **禁止默认假设"美国没有 WhatsApp"**。部分老板/业主有手机 WA，尤其是小公司、家族企业、拉丁裔业主。
- 每家公司必须主动搜索：① 官网联系页 ② IG bio ③ Facebook 主页 ④ Google "[company] WhatsApp" ⑤ Jina 抓官网
- **只有穷尽以上途径仍未找到手机号或 WA 链接，才记录为 `whatsapp_confirmed: false`**。
- 历史实测 9 个固话未注册 WA，仅代表那 9 个号码，不代表美国全部无 WA。
- 四渠道并行触达：WhatsApp（如找到）+ IG DM + Email + FB DM

---

## 零、目标客户定义与过滤规则

### 0.1 我们的目标客户（必须符合其中之一）

| 类型 | 说明 | 典型关键词 |
|------|------|-----------|
| LED 显示屏经销商/分销商 | 采购整屏转售 | distributor, reseller, wholesale |
| LED 显示屏租赁商 | 活动/舞台租屏 | rental, locação, alquiler, events |
| LED 显示屏集成商 | 系统集成安装 | integrator, installation, sistema |
| LED 显示屏零售商 | 面向终端用户销售 | sales, venda, venta |
| 广告/OOH 媒体公司 | 自持广告位使用 LED 屏 | outdoor advertising, billboard, OOH |

**产品必须是 LED 显示屏（LED display / LED screen / video wall / painel de LED / pantalla LED）**，不是灯具、灯条、灯泡。

---

### 0.2 必须排除的非目标类型

以下类型**一律不采集、不发送**，发现后标记 `status: "excluded"` + `exclude_reason`：

| 排除类型 | 中文 | 识别关键词 |
|---------|------|-----------|
| LED 灯具/照明 | 装饰灯、建筑照明、工程照明 | iluminação, lighting fixtures, luminárias, lâmpadas, luminaire, architectural lighting |
| LED 灯条/灯带 | 灯带供应商 | LED strip, tira LED, fita LED, LED tape, LED tube |
| DJ / 娱乐音响 | DJ 公司兼做灯光 | DJ, som e iluminação, audio, sound system, música |
| 舞台灯光（非显示屏） | 只做舞台灯效，不做视频显示 | stage lighting, moving head, beam light, wash light, 舞台灯 |
| **Lighting 公司**（新增） | 公司名含 Lighting、以灯光为主业 | "Lighting" in company name, event lighting, architectural lighting company — **不开发，哪怕有部分 LED video wall** |
| LED 灯泡/零件 | 灯泡、电子元件供应商 | LED bulb, bombilla LED, lampada LED, LED chip, LED module retail |
| 霓虹/招牌字 | 只做平面招牌 | neon sign, letra LED（独立招牌字，非显示屏） |
| 中国品牌海外子公司 | 国内厂商开的海外分公司，自己就是供应商 | 公司注册地/母公司在中国，美国/加拿大为销售前台 |

**边界情况**：同时做灯光 + LED 显示屏的公司（如舞台 AV 公司），**保留**，因为他们购买 LED 显示屏面板。

---

### 0.3 号码质量验证规则（WhatsApp 发送前）

采集到号码后，发送前需确认：

1. **巴西手机号识别**：本地号码 9 位且以 9 开头（区号+9XXXX-XXXX）。固话前缀 `3xxx`、`2xxx`、`4xxx` 不是手机，WhatsApp 无效，跳过。
2. **哥伦比亚手机号**：以 `3` 开头的 10 位数字（`3XX XXX XXXX`）。`601` 开头是波哥大固话，跳过。
3. **智利手机号**：`+56 9` 开头的 8 位数字。`+56 2` 开头是固话。
4. **秘鲁手机号**：`9` 开头的 9 位数字（`9XX XXX XXX`）。
5. **发送后如对方自动回复内容涉及 DJ / 灯光 / 美容 / 餐饮等无关业务** → 立即标记 `excluded`，`exclude_reason: "wrong_contact - 号码实际归属非目标行业"`。

---

## 一、整体流程

```
账号入库 → warmup（like 帖子）→ DM 发送 → pipeline 记录
```

- **Instagram**：warmup + send 可同日完成，like 1-2 篇帖子即可
- **Facebook**：依赖页面开启 Messenger；warmup 可 like 帖子，但部分页面无法私信
- **等待策略**：每个账号页面加载后至少等 2 秒再操作，Facebook 等 3 秒

---

## 二、Instagram 操作规范

### 2.1 进入账号 + Like 帖子（warmup）

```js
// 导航到主页，等待 2 秒
// 点击第一篇帖子
const posts = document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]');
posts[0].click();

// Like（SVG 节点没有直接 button 父级，需向上遍历找 role="button" 的 div）
const svg = document.querySelector('svg[aria-label="赞"]');
let el = svg;
for (let i = 0; i < 10; i++) {
  el = el.parentElement;
  if (el.tagName === 'BUTTON' || el.getAttribute('role') === 'button') {
    el.click(); break;
  }
}

// 验证是否 like 成功（aria-label 变为"取消赞"）
document.querySelector('svg[aria-label="取消赞"]') ? 'liked' : 'not-liked'
```

**坑**：`svg.closest('button')` 返回 null，因为点赞按钮是 `div[role="button"]` 包裹 SVG，不是 `<button>`。必须手动向上遍历 10 层。

### 2.2 打开 DM 对话框（正确做法：从对方主页点发消息）

**必须从目标账号的主页点击"发消息"按钮，不要去自己的聊天记录里搜索用户名。**

原因：Instagram 的新消息搜索框（compose dialog）通过 CDP 无法触发 React onChange 搜索事件，只会显示历史聊天记录，搜不出新的联系人。

```python
# CDP 发送流程（ig_dm_vN.py）
# Step 1: 打开主页（先初始化 React app）
tid = cdp('/new?url=https://www.instagram.com/', timeout=35)['targetId']
time.sleep(3)

# Step 2: 导航到目标账号主页
cdp(f'/navigate?target={tid}&url=https://www.instagram.com/{username}/', timeout=35)

# Step 3: 激活 tab（前台渲染，避免 React 组件不渲染）
cdp(f'/activate?target={tid}')
time.sleep(12)

# Step 4: 检查主页是否正常（404 账号直接 excluded）
page_err = eval_js(tid, "document.body.innerText.includes('无法访问此页面')")
if page_err == "true": return False  # 账号已删除/改名

# Step 5: 点击主页上的"发消息"按钮
msg_result = eval_js(tid, '''
(function(){
  var all = Array.from(document.querySelectorAll("[role=button], button"));
  var btn = all.find(b => {
    var t = (b.innerText || "").trim();
    return t === "发消息" || t === "Message";
  });
  if (btn) { btn.click(); return JSON.stringify({ok: true}); }
  return JSON.stringify({ok: false});
})()
''')
# 点击成功后 DM 输入框会直接出现，不需要额外的"聊天"确认步骤
```

**坑**：`/new?url=instagram.com/username/` 直接打开对方主页，React 内容不渲染（背景 tab 限速）。
→ 解决：必须先打开 IG 主页，再用 `/navigate` 跳转，再用 `/activate` 置前台。

**坑**：部分账号没有"发消息"按钮（私人账号限制 DM、或对方尚未关注我们）。
→ 解决：检测 available 按钮列表，如无 `发消息` 则标 `excluded`，原因 `no_message_button`。

**坑**：v35 前的旧方法（新消息收件箱→搜索框输入用户名）不再有效，CDP 的 rawKeyDown 无法触发 Instagram 搜索 API。

```js
// 找"发消息"按钮的 JS（DOM 中是 DIV[role=button]，不是 <button>）
const all = Array.from(document.querySelectorAll('[role="button"], button'));
const btn = all.find(b => (b.innerText || '').trim() === '发消息');
btn && btn.click();
```

### 2.3 输入消息 + 发送

```js
// browser_type 用 fill（比模拟按键可靠）
await page.locator('div[contenteditable="true"]').fill('消息内容');
await page.keyboard.press('Enter');

// 验证发送成功：输入框清空
const el = document.querySelector('[contenteditable="true"]');
el.innerText.trim() === '' // → 'sent'
```

**坑**：有时 DM 弹窗打开后会跳转到 `/direct/t/xxxxx` 页面，或保持在主页以 overlay 形式显示。两种情况都可以用 `div[contenteditable="true"]` 找到输入框。

---

## 三、Facebook 操作规范

### 3.1 判断页面是否支持 Messenger

加载完成后检查按钮列表：
- 有 **"发消息"** → 可以直接 DM
- 只有 **"关注" + "立即拨打"** → 该页面未开启 Messenger，跳过

```js
const btns = Array.from(document.querySelectorAll('[role="button"], button'));
const hasMsg = btns.some(b => b.textContent.trim() === '发消息');
```

**已知无 Messenger 的账号类型**：
- 纯展示型企业主页（只留电话/地址）
- 未认证的小型本地商家
- 个人型业务账号（偶发）

### 3.2 打开聊天窗口

```js
const btns = Array.from(document.querySelectorAll('[role="button"], button'));
btns.find(b => b.textContent.trim() === '发消息').click();
// 等 2 秒让聊天浮层加载
```

### 3.3 写入消息（关键：aria-label 选择器）

Facebook 聊天输入框用 `aria-label` 标识对话对象，格式为 `发消息给{PageName}`：

```js
// 用 aria-label 精准定位（防止多个聊天窗口同时打开时误操作）
await page.locator('div[contenteditable][aria-label*="部分名称"]').fill('消息内容');
await page.keyboard.press('Enter');

// 验证
document.querySelector('div[contenteditable][aria-label*="部分名称"]').innerText.trim() === ''
```

**坑**：aria-label 有时全大写（`"DIGITAL SIGNAGE COLOMBIA"`），有时带尾部空格（`"Alquiler Pantallas Led  "`）。永远用 `aria-label*=` 模糊匹配，不要用精确等号。

**坑**：多个聊天窗口同时打开时，`div[contenteditable="true"]` 会匹配到错误窗口。必须用 aria-label 区分。

**坑**：`execCommand('insertText', false, text)` 在复杂 React 输入框中只插入 1 个字符。不要用，直接用 `locator.fill()`。

### 3.4 当页面没有"发消息"时的备选方案

1. **通过 Instagram 发**（大多数 Facebook LED 商家同时有 Instagram）
2. **WhatsApp**（如有电话号码，用 `wa.me/` 链接）
3. **Messenger 新消息搜索**：可用，但找到的结果可能是个人账号而非主页，谨慎使用

---

## 四、已知账号问题

| 账号 | 平台 | 问题 | 处理 |
|------|------|------|------|
| @rdl_led | Instagram | 账号不存在（404） | 从 pipeline 移除或标记 skipped |
| AmericanLedDisplays | Facebook | 页面受限，内容无法显示 | 标记 skipped，查找备用渠道 |
| ledwavesaopaulo | Facebook | 页面无 Messenger 按钮 | 改走 Instagram @ledwave |
| produccionesfenixevolution | Facebook | 页面无 Messenger 按钮 | 改走 Instagram @fenixevolution_led |

---

## 五、效率优化

### 5.1 warmup + send 同日执行
不需要等 24 小时。Like 1 篇帖子后立刻发 DM，实测有效。节省整个等待周期。

### 5.2 消息生成
- 批量预生成所有消息存到 `_ig_messages_MMDD_batchN.json` / `_fb_messages_MMDD_batchN.json`
- 不要在浏览器操作过程中实时调用 Claude 生成，避免阻塞

### 5.3 Facebook 页面加载
Facebook 比 Instagram 慢，必须等 3 秒（Instagram 等 2 秒）。部分按钮需要 `role="button"` 和 `button` 两类都查。

### 5.4 每日发送量建议
- **Instagram**：每日 6-10 个，超过容易触发限制
- **Facebook**：每日 4-6 个
- **WhatsApp**：每日最多 **30 条**（超过触发账号受限，2026-05-15 教训）
- 同一账号不要连续发超过 3 个同类型消息（语速过快会被检测）

### 5.5 验证发送成功的标准
唯一可靠标准：**发送后输入框 `innerText.trim() === ''`**。不要依赖消息气泡是否出现（加载慢时可能误判）。

---

## 六、pipeline 文件更新规范

发送完一批后必须立即更新：

1. `pipeline/instagram/prospects.json` 或 `pipeline/facebook/prospects.json`
   - `status` → `"messaged"` 或 `"skipped"`
   - `warmup_done` → `true`
   - `warmup_date`, `message_sent_date`, `message_text`, `touch_count`

2. `pipeline/daily_log_YYYY-MM-DD.json`
   - 每条记录包含 `time`, `platform`, `action`, `username`, `company`, `country`, `message`
   - skipped 记录包含 `reason`

3. `PROGRESS.md`
   - 追加当日发送表格

---

## 七、消息写作规范（来自 message_crafter.py）

- 长度：Instagram 40-60 词，Facebook 50-80 词
- 永远不出现对方公司名，用 "your team / your setup / your operation"
- 以真实行业问题结尾（不是 CTA）
- 引用至少 1 个账号的具体业务特征
- 禁止：「I hope this message finds you well」「factory direct」「best price」「dear sir」
