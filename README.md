# MCVISUAL 客户开发系统 (outreach-tool)

把 LED B2B 销售工作流（搜索候选 → 深挖验证 → 入库去重 → 多渠道触达 → 商机成交）
产品化成一个单用户本地网页应用。SaaS 级界面：日工作台 + 客户/商机/触达完整漏斗 + 深浅双主题。

## 功能一览
| 页面 | 能力 |
|---|---|
| Agent | **AI 助手：提议 → 你审批**。新回复自动分类意图（询盘/要参数/要报价/要样品/砍价/转介绍/拒绝）。**报价永远由你来做**：客户一要价或谈价，Agent 只建一条高优先级报价任务并把客户说的尺寸/点间距/交期整理进去，绝不起草回复（这条在代码里兜底，配置也改不开）；能起草的只有询盘/要参数/要样品这类简单回复。回复自动起草（邮件用完整正文；WhatsApp/Instagram 按需打开对话读全文后起草，聊天口吻、无主题无落款），草稿直接出现在收件箱对应那条回复下面，可改后一键发。**任何对外动作都不自动执行**：自主度按动作类型分 `关闭/提议/自动` 三档，出厂全在「提议」；调到「自动」也照样留执行记录，随时可调回来。驳回必须选理由。草稿里出现上下文查不到的价格/交期/起订量会被标红成高风险。分类默认走 DeepSeek（便宜、不吃 Claude 额度），起草默认走本机 Claude Code 订阅（不需要 API key）。**今日计划**：每天早上读一遍管道（未处理回复/逾期任务/停滞商机/未触达池/剩余额度/回复率），产出当天该做什么——同样是提议，一屏批完就是一天的活；模型只选「给谁、为什么现在」，文案来自你自己的模板。**日报**：每天 18:00 后推飞书（webhook 写 `backend/lark_webhook.txt`） |
| 仪表盘 | 今日工作台 + **销售任务（今日/逾期）** + 统计卡 + 渠道额度 + 触达漏斗 + "该跟进了"卡 + **商机金额/加权预测/逾期停滞** + **回复率分析（各 Campaign/国家回复率）** + 国家分布 |
| 销售任务 | 所有下一步行动的唯一工作台：逾期/今天/未来/未排日期分组，支持电话、Email、WhatsApp、会议、报价等任务；客户真人回复自动建高优先级任务，商机下一步自动同步，完成后客户跟进字段同步更新 |
| 客户库 | 全列表格（含**客户类型分级列**、邮箱有效性徽章）+ 详情抽屉（**客户简介与开场白**/**邮箱来源标注**/**一键复检官网**/阶段/标签/**下一步任务**/**多联系人与采购角色**/备注时间线/**不再联系开关**）+ 筛选/排序/分页/导出 Excel + **一键验证邮箱（MX）/一键 ICP 分级** + **快速添加**（粘贴 IG/FB/LinkedIn/官网链接一键入库，官网自动深挖+分级+查重）+ 勾选后触达操作条（模板按客户国家推荐语言、可换附件、可命名 Campaign；主要联系人是默认收件人，同一客户每天最多一次批量触达） |
| 商机管道 | 一个客户可建多个 LED 项目；记录金额/概率/预计成交日/下一步/用途/室内户外/尺寸/数量/像素间距/目的地/贸易条款/竞争对手/丢单原因；自动计算**加权预测**、识别下一步逾期和阶段停滞，关键字段不完整时阻止虚假推进 |
| 收件箱 | 客户**回复正文直接在工具里看**，并尽量归属到具体联系人；“已读”和“已处理”分开，只有确认已回复客户/已安排下一步后才清除首页待办，避免询盘看过后遗忘。邮件每 15 分钟自动拉取（失败每分钟重试，回看天数按断线时长自动放宽）；**WhatsApp / Instagram 每天自动扫一次会话列表**（只读列表、不打开对话，因此不会清掉手机上的未读；仅在渠道已连接时执行，也可手动点「扫社媒回复」）。**永久退信自动把死邮箱标 invalid 且不占收件箱**（投递延迟只展示不处理）；**退订关键词自动置"不再联系"**（全渠道停发）；**自动回复单独标记、不算已回复**，跟进序列照常继续 |
| 跟进序列 | 建多步跟进序列（第 N 天发什么话术）→ 客户库勾选入组 → 每日"今日待发跟进"队列手动确认发送 → 回复自动检测（邮件走 IMAP，WA/IG 读会话列表）并停掉已回复客户的后续跟进 |
| 客户开发 | **多行关键词搜索（一行一条、预设话术词、目标国家可选自动拼入、结果按域名合并去重）** / **名录·竞品经销商页 URL 批量挖**（展会参展商名录、竞品 where-to-buy 页）→ 深挖官网提取联系方式 + 自动 ICP 分级 → 去重 → 勾选导入（**跳过原因透明可见**）。**自动筛掉同行**：+86 电话/.cn 域名的中国·港台 LED 厂、alibaba/tradekey/kompass 等 B2B 目录站，外加可自选排除的市场（印度/巴基斯坦等，默认排印巴）——被筛掉的不做深挖、不自动勾选、默认隐藏并标明原因 |
| 产品报价 | 产品库（一键载入 P0.7–P10 标准五档）→ 勾选生成品牌英文报价卡 PNG → 复制路径作为发送附件 |
| 渠道连接 | WhatsApp 扫码 / Instagram 弹窗登录（持久化浏览器）+ **发件邮箱轮换配置**（多箱轮发、各守日限，保送达率） |

发送防护：单批硬上限 20 条、每渠道日上限 40、**同一客户每天最多一次批量触达（跨渠道）**、强制随机限速、WA/IG 自动附带案例图、已回复客户自动排除、无效邮箱（MX 验证失败/退信）自动跳过、"不再联系"客户全渠道排除。

话术个性化变量：`{name}`=公司名、`{contact}`=联系人（缺失自动写 there）、`{country}`、`{city}`、`{hook}`=按这家官网写的开场白；模板里出现未知 `{xxx}` 原样保留，不会导致发送失败。

**客户简介与开场白**：深挖官网时按页面上实际出现的内容生成——引用命中的业务关键词原词（带引号，一眼看出是人家自己写的），加上页面印的像素间距。不接大模型改写——编一句「贵司在拉美市场领先」客户自己知道不是真的。
非英文关键词配英文释义而不是丢掉，所以韩语、西语、葡语站同样有简介和开场白：简介写 `mentions "전광판" (LED signage)`，开场白写 `Saw the LED signage work on your site.`
简介给自己看（不重复公司名、分级、城市这些抽屉里已有的），开场白给客户看（客户没见过我们的分级，所以照样用）。有像素间距时优先用规格：`Saw P1–P10 panels listed on your site.`。`{hook}` 为空时消息里这句自动消失，不留空档。

**存量回填**：`cd backend && python -m app.backfill_brief --limit 40`，分批可续跑，再跑一次自动接着上次的位置（`--all` 一次跑完，会很久）。

**官网复检**：触达过的客户按契合度排下次复检（90 分档 30 天 / 70 分档 90 天 / 其余 180 天，连续没变化则退避，上限一年），每天后台自动读 20 家官网。补上以前没有的联系方式，官网上和库里冲突的值只写进备注不覆盖；**查了没变化就什么都不产生**，不建任务不写备注。详情抽屉可随时点「复检官网」立刻跑一次。详见 `docs/19-spec-brief-provenance-recheck.md`。

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
- 前端冒烟：启动后端后 `cd frontend && npx playwright test`（只读+勾选，绝不触发真实发送；有密码时自动登录）

## 架构
- `backend/app/db.py` — SQLite schema + 连接 · `repository.py` — 全部 SQL（含 untouched/has 筛选）
- `backend/app/enrich.py` — 官网抓取（邮箱/电话/wa.me/IG/FB/LinkedIn）· `discovery.py` — 搜索深挖管道
- `backend/app/brief.py` — 只用官网上出现过的内容拼客户简介和开场白（含非英文关键词的英文释义表）
- `backend/app/recheck.py` — 官网复检节奏与差异处理 · `backfill_brief.py` — 存量客户分批回填简介
- `backend/app/outreach.py` / `channel_outreach.py` — Email / WA·IG 发送编排（限速+批量上限+日额度）
- `backend/app/playwright_engine.py` — 每渠道持久化有头浏览器
- `backend/app/activities.py` — 销售任务、回复/商机自动建单、旧字段兼容迁移
- `backend/app/contacts.py` — 公司多联系人、主要收件人同步、回复归属与采购角色
- `backend/app/agent/` — 销售助手：`llm.py` 三后端按任务分派 · `proposals.py` 审批脊柱与自主度旋钮 ·
  `executors.py` 获批后调既有模块（护栏自动继承）· `classify.py` 脱敏批量分类 ·
  `draft.py` 起草与未溯源数字告警 · `social.py` 按需读社媒对话 · `memory.py` 客户 running summary ·
  `world.py` 世界状态 · `plan.py` 今日计划与动作校验 · `report.py` 飞书日报 · `run.py` 每轮流水线
- `backend/app/api/` — REST：leads / activities / opportunities / stats / send / discover / channels / agent
- `frontend/src/theme.css` — 双主题 design tokens；`App.tsx` — AppShell + 页面切换；`components/` — Dashboard / LeadsTable / OutreachPanel / DiscoveryPanel / ConnectionPanel

## 已知边界
- Agent 只提议不自作主张：A 期任何对外动作都要你点确认（自主度默认全在「提议」档）。
- 社媒起草会打开那条对话读全文，因此**会清掉手机上那条未读**（只对值得回的消息开，
  同一条只读一次）。读不到（登录过期/没号码/页面改版）就退回成提醒，绝不拿预览起草。
- Agent 需要模型后端：分类默认 DeepSeek（`backend/deepseek_key.txt`），
  起草默认本机 Claude Code 登录态。两者都不可用时 Agent 静默，系统行为与没有它时一致。
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
