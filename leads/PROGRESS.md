# LED Display Leads — 采集进度记录

> 最后更新：2026-05-22

---

## 2026-05-21 USA 大批次推进（v29-v31）

### 当前数据库状态

| 版本 | 记录数 | 新增 | 文件 |
|------|--------|------|------|
| v30 | 573 | +6 USA | generate_led_leads_v30.py |
| v31 | 580 | +7 USA | generate_led_leads_v31.py |
| **当前** | **580** | — | LED_Display_Leads_v20.xlsx |

### 各国进度（v31）

| 国家 | 数量 | 目标 | 缺口 |
|------|------|------|------|
| Korea | 135 | 500 | -365 |
| USA | **102** | 500 | -398 |
| Brazil | 79 | 500 | -421 |
| Canada | 39 | 500 | -461 |
| Chile | 44 | 500 | -456 |
| Argentina | 45 | 500 | -455 |
| Colombia | 54 | 500 | -446 |
| Peru | 38 | 500 | -462 |
| Mexico | 44 | 500 | -456 |
| **合计** | **580** | 4500 | — |

### Instagram DM 发送（今日）

**v29 批次（6 账号）：**

| # | 账号 | 公司 | 状态 |
|---|------|------|------|
| 1 | @ariatechnologyrentals | Aria AV Rentals | ✅ SENT |
| 2 | @rentforeventus | Rent For Event | ✅ SENT |
| 3 | @led_rentals_la | LED Rentals LA | ✅ SENT |
| 4 | @rentexavrentals | Rentex AV Rentals | ✅ SENT |
| 5 | @bigbangmn | Big Bang Companies | ✅ SENT |
| 6 | @4wall | 4Wall Entertainment | ✗ FAILED (input len=0 after type) |

**v30 批次（4 账号）：**

| # | 账号 | 公司 | 状态 |
|---|------|------|------|
| 7 | @airbornevisuals | Airborne Visuals | ✅ SENT |
| 8 | @audiotekhouston | ATH Productions | ✗ FAILED (Message btn not found — private/restricted) |
| 9 | @geoeventla | GeoEvent | ✗ FAILED (input len=0 after type) |
| 10 | @led_video_walls | TLL Top LED Lumination | ✅ SENT |

**v31 批次（5 账号，运行中）：**

| # | 账号 | 公司 | 状态 |
|---|------|------|------|
| 11 | @event_technology_services | Event Smart Technology | ✗ FAILED (Message btn not found — restricted) |
| 12 | @ledrentalshouston | LED Rentals Houston | 待发... |
| 13 | @pacificcoastentertainment | Pacific Coast Entertainment | 待发... |
| 14 | @audiovideola | Audio Video LA | 待发... |
| 15 | @atlspecialfx | Atlanta Special FX | 待发... |

### 关键技术问题记录

**问题 1：Chrome 130+ document.execCommand("insertText") 废弃**
- 症状：type返回ok但input len=1
- 修复：CDP `Input.insertText` 通过 `/type` 端点（cdp-proxy.mjs 已更新）
- 所有 ig_dm_v29+ 均使用此方法

**问题 2：type ok 但 input len=0（部分账号）**
- 症状：@4wall、@geoeventla 出现
- 原因：React DM dialog 渲染时有短暂失焦，Input.insertText 命中错误元素
- 缓解：v31 将 pre-type sleep 从 0.5s 增加到 1.5s，加入重试逻辑

**问题 3：Message button not found（部分账号）**
- 账号：@audiotekhouston、@event_technology_services
- 原因：可能是商业账号开启了消息限制，或需先互关
- 策略：这类账号改走 Email 渠道

### Email 待发列表（等待 GMAIL_APP_PASSWORD）

| 批次 | 脚本 | 目标数 | 待发 |
|------|------|--------|------|
| v29 | email_sender_usa.py | 4 | Aria AV/LED Rentals LA/Rentex/Big Bang |
| v30 | email_sender_v30.py | 4 | Airborne/GeoEvent/Bounce/TrueBlue |
| v31 | email_sender_v31.py | 7 | Event Smart/LED Houston/PCE/Audio LA/LV Led Wall/ATL FX/All Pro AV |

---

## 2026-05-22 今日执行汇总

### 数据库状态

| 版本 | 记录数 | 新增 | 文件 |
|------|--------|------|------|
| v32 | **587** | +7 USA | generate_led_leads_v32.py |

**USA 总量：109 条**（今日新增：Imagine Media Group/Soflo Studio/Kings Rentals/Stellar XP/R90 Lighting/Studio46 Media/Lumina Event Lighting）

### 今日触达汇总

| 渠道 | 数量 | 明细 |
|------|------|------|
| WA | 1 | Visual LED Oficial (Colombia +57 310 873 1503) ✅ |
| IG DM v32 | 2 | @4wall ✅ / @geoeventla ✅（v29/v30 重试成功）|
| IG DM v33 | 4/5 | LatAm: proyectoresypantallasmede✅/altema✅/publicidad_del_aguila✅/visualledoficial✅/@mcsydesign❌(无Message按钮) |
| IG DM v34 | 2/3 | USA: @kingsrental✅/@stellarxp✅(重试)/@r90.lighting❌(len=0,有邮件) |
| IG Warmup v32 | 4/5 | 拉美5账号（@mcsydesign lazy load，手动标done）|
| IG Warmup v33 | 3/3 | USA: @kingsrental/@stellarxp/@r90.lighting |
| Email v32 | 7/7 | 全部成功（附韩国案例图）|
| **今日合计触达** | **≥20** | — |

### 邮件更新（2026-05-22）

昨日（2026-05-21）已发完 15 封（email_sender_usa/v30/v31），今日发出 7 封（v32）。

**新邮件模板**（2026-05-21 起统一使用）：
- 主题：`Recent LED Display Projects — Shenzhen Maxcolor Visual`
- 正文：分享韩国案例 + 邀请联系
- 附件：`korea-led-projects-poster-4k.jpg`

### IG DM 所有已发状态（截至 2026-05-22）

- v29 批次：6账号（5/6 成功，@4wall→v32重试成功）
- v30 批次：4账号（2/4 成功，@geoeventla→v32重试成功）
- v31 批次：5账号（4/5 成功，@event_technology_services 受限→改Email）
- v32 批次：2账号（2/2 成功 — USA 重试）
- v33 批次：5账号（4/5 SENT，@mcsydesign 无 Message 按钮）
- v34 批次：3账号（2/3 SENT，@r90.lighting len=0 失败，已有邮件覆盖）

### v33 批次（2026-05-22 下午）

新增 9 条 USA leads（nos 588-596），总量 596，USA=118：

| no | 公司 | 城市 | Email | IG |
|----|------|------|-------|-----|
| 588 | Special FX Rentals | PA/Las Vegas | ✅ | @specialfxrentals |
| 589 | AB AV Rentals | Houston TX | ✅ | @abavrentals |
| 590 | Atlanta Pro AV | Atlanta GA | ✅ | @atl_proav |
| 591 | Technical Elements | Woodstock GA | ✅ | — |
| 592 | Rayne Events | Washington DC | ✅ | @rayne_events |
| 593 | Promosa | Kent WA | ✅ | @promosamgmt |
| 594 | Colorado Live Events | Centennial CO | — | @coloradoliveevents |
| 595 | Centric Events | Phoenix AZ | — | @centricevents |
| 596 | Las Vegas LED Rentals | Las Vegas NV | — | @vegasledrentals |

- Email v33: 6/6 ✅（无邮件的3条走IG DM）
- IG Warmup v35: 7/8（@rayne_events lazy load→手动标done）
- IG DM v35: 8/8 ✅ 全部成功

### Lighting 公司排除规则（新增）

公司名含 "Lighting" 或以灯光为主业的公司一律不开发（与 LED 显示屏行业不相关）：
- no:585 R90 Lighting → excluded
- no:587 Lumina Event Lighting → excluded

### 待处理

- IG DM v35 完成后 git push
- 继续搜索 USA 新 leads（目标 500，当前 118）
- @r90.lighting IG pipeline 已标 excluded（有邮件覆盖）

---

> 以下为历史记录（2026-05-14 及之前）

---

---

## 2026-05-14 DM 发送记录

### 今日发送（Instagram 2 条 + Facebook 7 条，共 9 条，成功 8 条）

**Instagram（已 warmup 账号）：**

| # | 账号 | 公司 | 状态 |
|---|------|------|------|
| 1 | @ledtechmiami | LED Tech Miami | ✅ 已发 |
| 2 | @ledmiamirentalsigns | LED Miami Rental Signs | ✅ 已发 |

**Facebook（warmup_done=true 账号）：**

| # | 账号 | 公司 | 国家 | 状态 |
|---|------|------|------|------|
| 3 | brightlinkav | Brightlink AV | USA | ✅ 已发 |
| 4 | AmericanLedDisplays | American LED Display Solutions | USA | ❌ 跳过（页面受限/不可访问） |
| 5 | publimasterSJ | PubliMaster Colombia | Colombia | ✅ 已发 |
| 6 | DigitalSignageColombia | Digital Signage Colombia | Colombia | ✅ 已发 |
| 7 | MachineTronics | MachineTronics | Colombia | ✅ 已发 |
| 8 | magoarlekin | Visionled Colombia | Colombia | ✅ 已发 |
| 9 | Alquilerpantallasledcolombia | Alquiler Pantallas LED Colombia | Colombia | ✅ 已发 |

**执行方式：** Playwright MCP 浏览器自动化（直接操控已登录 Instagram/Facebook 账号）

**日志：** `pipeline/daily_log_2026-05-14.json`（9 条记录）

---

## 2026-05-14 DM 发送记录 — Batch 3

### Instagram + Facebook 第三批（共 11 个账号，成功 8 条）

**Instagram（warmup+send 同日）：**

| # | 账号 | 公司 | 国家 | 状态 |
|---|------|------|------|------|
| 1 | @abklightingoficial | ABK Lighting | Mexico | ✅ 已发 |
| 2 | @led_vk3133 | LED VK | Korea | ✅ 已发 |
| 3 | @led_master_colombia | LED Master Colombia | Colombia | ✅ 已发 |
| 4 | @exodoled | Exodo LED | Argentina | ✅ 已发 |
| 5 | @illusionuniverse | Illusion Universe | Canada | ❌ 跳过（账号无帖子，DM 无法打开） |
| 6 | @fixledchile | Fix LED Chile | Chile | ❌ 跳过（点击发消息后 DM 浮层未出现） |
| 7 | @alquiler_de_pantallas_led_peru | Alquiler Pantallas LED Peru | Peru | ✅ 已发 |

**Facebook：**

| # | 账号 | 公司 | 国家 | 状态 |
|---|------|------|------|------|
| 8 | exctecled | EXCTECLED Peru | Peru | ❌ 跳过（页面受限/不可访问） |
| 9 | gtledpainel | GT Painel de Led | Brazil | ✅ 已发 |
| 10 | azkareventos | Azkar Eventos | Colombia | ✅ 已发 |
| 11 | Agsled | AgsLed | Chile | ✅ 已发 |

**日志：** `pipeline/daily_log_2026-05-14.json`（32 条记录）

---

## 2026-05-14 DM 发送记录 — Batch 2

### Instagram + Facebook 第二批（共 12 个账号，成功 9 条）

**Instagram（warmup+send 同日）：**

| # | 账号 | 公司 | 国家 | 状态 |
|---|------|------|------|------|
| 1 | @rdl_led | RDL LED | USA | ❌ 跳过（账号不存在） |
| 2 | @avt.ca | AVT Canada | Canada | ✅ 已发 |
| 3 | @fenixevolution_led | Fénix-Evolution LED | Mexico | ✅ 已发 |
| 4 | @pantallas_led_de_colombia | Pantallas LED de Colombia | Colombia | ✅ 已发 |
| 5 | @ledwave | LedWave | Brazil | ✅ 已发 |
| 6 | @dinalight.led | Dinalight | Argentina | ✅ 已发 |
| 7 | @cgschile.pantallasled.hd | CGS Chile | Chile | ✅ 已发 |
| 8 | @pantallasledperu | EXCTECLED Peru | Peru | ✅ 已发 |

**Facebook：**

| # | 账号 | 公司 | 国家 | 状态 |
|---|------|------|------|------|
| 9 | ledwavesaopaulo | LedWave | Brazil | ❌ 跳过（页面无 Messenger） |
| 10 | produccionesfenixevolution | Fénix-Evolution LED | Mexico | ❌ 跳过（页面无 Messenger） |
| 11 | grupounoled | Grupo UNO LED | Argentina | ✅ 已发 |
| 12 | CGSincChile | CGS Chile | Chile | ✅ 已发 |

**日志：** `pipeline/daily_log_2026-05-14.json`（21 条记录）

---

## 2026-05-13 Instagram DM 发送记录

### 今日发送（Instagram，共 18 条）

**第一批（warmup 完成账号，发送时间 ~10:00）：**

| # | 账号 | 公司 | 状态 |
|---|------|------|------|
| 1 | @techledwall | TechLed | ✅ 已发 |
| 2 | @fastinstall.us | FastInstall | ✅ 已发 |
| 3 | @ledfactoryusa | LED Factory USA | ✅ 已发 |
| 4 | @avrental305 | AV Rental 305 | ✅ 已发 |
| 5 | @event_smart_technology | Event Smart Technology | ✅ 已发 |
| 6 | @showbossav | Show Boss AV | ✅ 已发 |

**第二批（新账号 batch2，发送时间 ~10:09–10:22）：**

| # | 账号 | 公司 | 状态 |
|---|------|------|------|
| 7 | @publimastersj | PubliMaster Colombia | ✅ 已发 |
| 8 | @digitalsignagecolombia | Digital Signage Colombia | ✅ 已发 |
| 9 | @inoutsoluciones | InOut Soluciones | ✅ 已发 |
| 10 | @ciber_colombia_ | CIBER CORP Colombia | ✅ 已发 |
| 11 | @pantallasledencolombia | Pantallas Colombia | ✅ 已发 |
| 12 | @pantallasledbogota | Pantallas LED Bogota | ✅ 已发 |
| 13 | @ledproductionsmiami | LED Productions Miami | ✅ 已发 |
| 14 | @ledproductionsorlando | LED Productions Orlando | ✅ 已发 |
| 15 | @ledmiamirentalsigns | LED Miami Rental Signs | ❌ 跳过（DM搜索找不到，可能未互关） |
| 16 | @ledmiamisigns | LED Miami Signs | ✅ 已发 |
| 17 | @screenled.us | Screen LED US | ✅ 已发 |
| 18 | @americanledscreens | American LED Screens | ✅ 已发 |
| 19 | @losangelesledscreens | Los Angeles LED Screens | ✅ 已发 |

**规则说明：**
- 所有消息不出现对方公司名，用"your team / your setup / your operation"替代
- 消息文案由 `message_crafter.py` 通过 `claude -p` 生成，40–60 词，以真实行业问题结尾
- 日志记录文件：`pipeline/daily_log_2026-05-13.json`（19 条记录）

---

## 当前状态

| 文件 | 记录数 | 状态 |
|------|--------|------|
| `LED_Display_Leads_v18.xlsx` | **489** | ✅ 当前最新版本 |
| `generate_led_leads_v18.py` | — | 生成脚本（v18） |
| `LED_Display_Leads_v17.xlsx` | 474 | 历史版本 |
| `generate_led_leads_v17.py` | — | 生成脚本（v17） |
| `LED_Display_Leads_v16.xlsx` | 436 | 历史版本 |
| `generate_led_leads_v16.py` | — | 生成脚本（v16） |
| `LED_Display_Leads_v15.xlsx` | 426 | 历史版本 |
| `LED_Display_Leads_v14.xlsx` | 420 | 历史版本 |
| `generate_led_leads_v14.py` | — | 生成脚本（v14） |
| `LED_Display_Leads_v13.xlsx` | 413 | 历史版本 |
| `LED_Display_Leads_v12.xlsx` | 403 | 历史版本 |
| `LED_Display_Leads_v11.xlsx` | 396 | 历史版本 |
| `LED_Display_Leads_v10.xlsx` | 389 | 历史版本 |
| `LED_Display_Leads_v9.xlsx` | 379 | 历史版本 |
| `LED_Display_Leads_v8.xlsx` | 372 | 历史版本 |
| `generate_led_leads_v4.py` | 209 | 历史版本（链式基础） |

---

## 各国进度

| 国家 | 当前数量 | 目标 | 缺口 |
|------|----------|------|------|
| Korea | 135 | 500 | -365 |
| USA | 74 | 500 | -426 |
| Brazil | 74 | 500 | -426 |
| Canada | 39 | 500 | -461 |
| Chile | 41 | 500 | -459 |
| Argentina | 34 | 500 | -466 |
| Colombia | 33 | 500 | -467 |
| Peru | 26 | 500 | -474 |
| Mexico | 33 | 500 | -467 |
| **合计** | **489** | **4500** | — |

> 注：如果目标是"各区域合计500"而不是"每国500"，韩国+美洲目前分别约 75 和 225，仍有较大缺口。

---

## Excel 结构（v5）

**Sheet 1 — LED Leads - All Markets**
- 16 列：No. / Region / Country / City / Company (English) / Company (Local Language) / Contact Person / Title / Email / Phone / WhatsApp / Kakao / Website / Main Business / Facebook / Instagram / LinkedIn / Notes/Action
- 按国家色彩区分行背景
- 冻结首行

**Sheet 2 — Summary**：各国公司数量汇总

**Sheet 3 — 开发建议**：9个市场的 B2B 开发策略

---

## 数据来源（已用过）

| 来源 | 说明 |
|------|------|
| eagerled.com | 各国 LED 供应商聚合列表，有效 |
| bibiled.com | 各国 top 10 LED 公司，有效 |
| hidipl.com | 韩国合作伙伴列表，给出 12 家 |
| szjy-led.com | 韩国页面有效，其他国家 404 |
| kompass.com | 403 Forbidden，跳过 |
| nseledcloud.com / linsnled.com | CAPTCHA 拦截，跳过 |
| ledscreenfactory.com | 国家页面全部 404 |

---

## 下次扩充建议

### 优先目标
1. **韩国** — 缺口最大，可深挖方向：
   - Naver 搜索：`LED 전광판 업체`, `실내 LED 업체`
   - 韩国中小企业数据库：bizno.net、kompass.co.kr（直接搜索绕过403）
   - 建筑/舞台/体育场馆垂直方向单独挖掘

2. **巴西** — 可继续挖的方向：
   - 各州市场：Rio Grande do Sul / Minas Gerais / Pernambuco
   - Google 搜索：`painel de led fornecedores brasil`
   - Mercado Livre 上的 LED 供应商账号

3. **美国** — 可继续挖的方向：
   - signage垂直：signsofthetimes.com、signweb.com 目录
   - 体育场馆LED：专门搜索 stadium scoreboard suppliers
   - 教堂/教育市场：church LED display suppliers USA

4. **哥伦比亚/墨西哥** — 数量最少，可大量补充
   - Google Maps 搜索：`pantallas LED` + 城市名
   - LinkedIn Sales Navigator（如有）

### 可试的新数据源
- `globaled.com` — 全球 LED 供应商目录
- `ledcolumbus.com` — 美国中西部
- `alibaba.com` B2B 买家方向（找分销商/系统集成商）
- 韩国 Yellow Pages：`114.co.kr` 搜索 LED 업체

---

## 技术说明

脚本链式设计（v4→v5→v6→v7）：
- 每版脚本用 `ast.literal_eval` + `re.search` 读取上一版的数据列表，追加 `new_entries`
- v4: 读取 `leads` 列表；v5/v6/v7: 读取上版的 `new_entries`
- v7 读取链：v4.leads + v5.new_entries + v6.new_entries + v7.new_entries = 358 条
- 下次扩充：创建 `generate_led_leads_v8.py`，读取 v7 的 `new_entries` 再追加

**注意**：`re.search` 匹配 `^new_entries = ([...])`，依赖列表从行首开始，结束行 `]` 在行首。若修改上版格式需重新验证。

---

## 数据来源补充（v6-v7 新增）

| 来源 | 说明 |
|------|------|
| Instagram / opencli search | 韩국/미국 LED 업체 계정 발굴 |
| Naver Blog / Google Search | 韩国전광판업체, 各地区业者 |
| Google Maps | 各城市"전광판 업체" 搜索 |
| bibiled.com Korea/Mexico top lists | 聚合列表，有效 |
| 直接 WebFetch (Jina) | 公司官网联系信息提取 |

---

## 联系信息质量统计（v7 估算）

- 有 Email：约 210 条（59%）
- 有 Phone/WA/Kakao：约 230 条（64%）
- 有联系人姓名：约 35 条（10%）
- 有完整网站：约 260 条（73%）
