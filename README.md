# Maxcolor 客户开发系统 (outreach-tool)

把 LED B2B 销售工作流（搜索候选 → 深挖验证 → 入库去重 → 多渠道触达 → 商机成交）
产品化成一个单用户本地网页应用。SaaS 级界面：日工作台 + 客户/商机/触达完整漏斗 + 深浅双主题。

## 功能一览
| 页面 | 能力 |
|---|---|
| 仪表盘 | 今日工作台 + 统计卡 + 渠道额度 + 触达漏斗 + "该跟进了"卡 + **商机金额/加权预测/逾期停滞** + **回复率分析（各 Campaign/国家回复率）** + 国家分布 |
| 客户库 | 全列表格（含**客户类型分级列**、邮箱有效性徽章）+ 详情抽屉（阶段/标签/跟进日期/备注时间线/**不再联系开关**）+ 筛选/排序/分页/导出 Excel + **一键验证邮箱（MX）/一键 ICP 分级** + **快速添加**（粘贴 IG/FB/LinkedIn/官网链接一键入库，官网自动深挖+分级+查重）+ 勾选后触达操作条（模板按客户国家推荐语言、可换附件、可命名 Campaign、**🚀 一键全渠道 Email+WA+IG 三路同发**） |
| 商机管道 | 一个客户可建多个 LED 项目；记录金额/概率/预计成交日/下一步/用途/室内户外/尺寸/数量/像素间距/目的地/贸易条款/竞争对手/丢单原因；自动计算**加权预测**、识别下一步逾期和阶段停滞，关键字段不完整时阻止虚假推进 |
| 收件箱 | 客户**回复正文直接在工具里看**（未读徽章、点开跳客户详情）。邮件每 15 分钟自动拉取（失败每分钟重试，回看天数按断线时长自动放宽）；**WhatsApp / Instagram 每天自动扫一次会话列表**（只读列表、不打开对话，因此不会清掉手机上的未读；仅在渠道已连接时执行，也可手动点「扫社媒回复」）。**永久退信自动把死邮箱标 invalid**（投递延迟只展示不处理）；**退订关键词自动置"不再联系"**（全渠道停发）；**自动回复单独标记、不算已回复**，跟进序列照常继续 |
| 跟进序列 | 建多步跟进序列（第 N 天发什么话术）→ 客户库勾选入组 → 每日"今日待发跟进"队列手动确认发送 → 回复自动检测（邮件走 IMAP，WA/IG 读会话列表）并停掉已回复客户的后续跟进 |
| 客户开发 | **多行关键词搜索（一行一条、预设话术词、目标国家可选自动拼入、结果按域名合并去重）** / **名录·竞品经销商页 URL 批量挖**（展会参展商名录、竞品 where-to-buy 页）→ 深挖官网提取联系方式 + 自动 ICP 分级 → 去重 → 勾选导入（**跳过原因透明可见**）。**自动筛掉同行**：+86 电话/.cn 域名的中国·港台 LED 厂、alibaba/tradekey/kompass 等 B2B 目录站，外加可自选排除的市场（印度/巴基斯坦等，默认排印巴）——被筛掉的不做深挖、不自动勾选、默认隐藏并标明原因 |
| 产品报价 | 产品库（一键载入 P0.7–P10 标准五档）→ 勾选生成品牌英文报价卡 PNG → 复制路径作为发送附件 |
| 渠道连接 | WhatsApp 扫码 / Instagram 弹窗登录（持久化浏览器）+ **发件邮箱轮换配置**（多箱轮发、各守日限，保送达率） |

发送防护：单批硬上限 20 条、每渠道日上限 40、强制随机限速、WA/IG 自动附带案例图、已回复客户自动排除、无效邮箱（MX 验证失败/退信）自动跳过、"不再联系"客户全渠道排除。

话术个性化变量：`{name}`=公司名、`{contact}`=联系人（缺失自动写 there）、`{country}`、`{city}`；模板里出现未知 `{xxx}` 原样保留，不会导致发送失败。

数据安全：每次启动自动把 outreach.db 备份到 `backend/backups/`（每天一份，保留最近 14 份）。

## 双击即用（免命令行）
1. **第一次**：双击 `setup.bat`（装依赖 + 导入历史客户 + 构建界面，约几分钟）。
2. **以后每次**：双击 `start.bat` —— 自动启动服务并打开浏览器看板。
   工作时保留弹出的 "outreach-tool-server" 窗口；关掉它即停止工具。

## 开机自启 + 固定网址（推荐）
双击 `install_autostart.bat`，之后：
- 开机登录 20 秒后服务自动在后台运行，**没有黑窗口，不用再点 start.bat**；桌面留一个「客户开发系统」快捷方式。
- 配过隧道的话，40 秒后公网地址 `https://crm.mcvisualled.com` 也自动上线，手机和外网同一个网址，永不变化。
- 崩溃自动重试 3 次；日志在 `backend/logs/server-日期.log`。
- 取消：双击 `uninstall_autostart.bat`（不影响手动 start.bat）。

**电脑关机或睡眠 = 网站下线。** 隧道入口在本机，这是数据不出本地的代价。

首次配置固定网址（换电脑时重做）：
1. `bin\cloudflared.exe tunnel login` → 浏览器授权 `mcvisualled.com`（国内网络常拉取证书失败，按提示把浏览器下载的 `cert.pem` 手动放到 `%USERPROFILE%\.cloudflared\`）
2. `bin\cloudflared.exe tunnel create maxcolor-crm`
3. `bin\cloudflared.exe tunnel route dns maxcolor-crm crm.mcvisualled.com`
4. 写 `%USERPROFILE%\.cloudflared\config.yml`：隧道 ID + 凭证路径 + `ingress` 指向 `http://127.0.0.1:8000`
5. 重新双击 `install_autostart.bat`

上公网前必须在 `backend/auth_password.txt` 写一行密码，否则客户库对外敞开（`start_online.bat` 会直接拒绝启动）。

## 命令行方式（可选）
一次性准备：
1. `cd backend && python -m pip install -r requirements.txt`
2. `cd backend && python -m app.migrate`
3. `cd frontend && npm install && npm run build`

启动：
```
cd backend && python -m uvicorn app.main:app --port 8000
```
浏览器打开 http://127.0.0.1:8000

## 开发模式（热更新）
- 后端：`cd backend && python -m uvicorn app.main:app --reload --port 8000`
- 前端：`cd frontend && npm run dev`（自动代理 /api 到 8000）

## 测试
- 后端：`cd backend && python -m pytest`（全量回归）
- 前端冒烟：启动后端后 `cd frontend && npx playwright test`（15 用例，只读+勾选，绝不触发真实发送；有密码时自动登录）

## 架构
- `backend/app/db.py` — SQLite schema + 连接 · `repository.py` — 全部 SQL（含 untouched/has 筛选）
- `backend/app/enrich.py` — 官网抓取（邮箱/电话/wa.me/IG/FB/LinkedIn）· `discovery.py` — 搜索深挖管道
- `backend/app/outreach.py` / `channel_outreach.py` — Email / WA·IG 发送编排（限速+批量上限+日额度）
- `backend/app/playwright_engine.py` — 每渠道持久化有头浏览器
- `backend/app/api/` — REST：leads / stats / send / discover / channels
- `frontend/src/theme.css` — 双主题 design tokens；`App.tsx` — AppShell + 页面切换；`components/` — Dashboard / LeadsTable / OutreachPanel / DiscoveryPanel / ConnectionPanel

## 已知边界
- 官网没留的联系方式抓不到（深挖只提取公开信息）。
- WA/IG 自动私信违反平台 ToS，有封号风险；限速+批量上限只能降低、不能消除。
- 多租户/登录/计费 = Phase 2，未开始。

## 上线（公网访问）
本系统必须跑在你自己的电脑上（WA/IG 发送依赖本机已登录的持久化浏览器，搬到云服务器会话全丢且封号风险高），
"上线" = 把本机服务安全地暴露到公网。

1. 设访问密码：在 `backend/auth_password.txt` 写一行密码（该文件已 gitignore，绝不进仓库）。
   有密码文件 → 全部 `/api` 需登录；没有 → 本地免密模式（双击 start.bat 的用法不变）。
2. 双击 `start_online.bat`：自动装 cloudflared → 起服务 → 建隧道，
   窗口里出现的 `https://xxxx.trycloudflare.com` 就是公网网址，手机/同事浏览器打开输密码即可用。
3. 关掉隧道窗口 = 下线；本地 http://127.0.0.1:8000 不受影响。

免费隧道每次重启网址会变。想要固定网址需要一个自己的域名（Cloudflare 免费托管 + named tunnel）。
安全：密码 HMAC 会话 Cookie（HttpOnly）、连错 5 次锁 1 分钟、页面本身无数据（数据全在需登录的 /api 下）。
