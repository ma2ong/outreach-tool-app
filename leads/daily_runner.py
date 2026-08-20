"""
Daily Runner: 每日触达主流程
用法:
  python daily_runner.py plan            # 预览今日触达计划（不执行）
  python daily_runner.py warmup          # 执行 warm-up（账号间手动按Enter继续）
  python daily_runner.py warmup --auto   # 自动批量 warm-up，账号间自动等待5分钟，无需人工确认
  python daily_runner.py send            # 生成消息，逐条打开DM页面，人工粘贴确认
  python daily_runner.py send --force    # 跳过24小时等待（调试用）
  python daily_runner.py status          # 显示今日进度

DM发送说明：
  opencli 当前不支持直接发DM。
  send 命令会：1) 生成个性化消息 → 2) 通过QA检查 → 3) 自动打开对方IG主页
                4) 显示消息让你复制 → 5) 你手动点DM发送 → 6) 回车确认记录状态
"""
import sys, os, json, time, random
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
from datetime import datetime, date, timedelta

BASE = Path(__file__).parent
PIPELINE = BASE / "pipeline"
PLATFORMS = ["instagram", "facebook"]

# 目标国家过滤（空列表 = 不过滤，取所有国家）
TARGET_COUNTRIES = ["USA"]

DAILY_TARGETS = {
    "instagram": random.randint(5, 8),
    "facebook":  random.randint(3, 5),
}

DAILY_LIMITS = {"instagram": 8, "facebook": 5, "whatsapp": 5}

PRIORITY_COUNTRIES = [
    "Colombia", "Peru", "Chile", "Mexico", "Argentina", "USA", "Canada", "Brazil", "Korea"
]

PROFILE_URLS = {
    "instagram": "https://www.instagram.com/{username}/",
    "facebook":  "https://www.facebook.com/{username}/",
}


def load_json(path) -> list:
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_prospects(platform: str) -> list:
    return load_json(PIPELINE / platform / "prospects.json")


def save_prospects(platform: str, data: list):
    save_json(PIPELINE / platform / "prospects.json", data)


def load_daily_log(today: str = None) -> list:
    today = today or date.today().isoformat()
    return load_json(PIPELINE / f"daily_log_{today}.json")


def save_daily_log(log: list, today: str = None):
    today = today or date.today().isoformat()
    save_json(PIPELINE / f"daily_log_{today}.json", log)


def log_event(event: dict):
    today = date.today().isoformat()
    log = load_daily_log(today)
    event["time"] = datetime.utcnow().isoformat()
    log.append(event)
    save_daily_log(log, today)


def open_in_browser(url: str):
    """用系统默认浏览器打开URL"""
    import subprocess
    try:
        if sys.platform == "win32":
            subprocess.Popen(["cmd", "/c", "start", url], shell=False)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
        time.sleep(2)
    except Exception as e:
        print(f"  ! 打开浏览器失败: {e}")
        print(f"  > 请手动打开: {url}")


def select_queue(platform: str, n: int) -> list:
    blacklist = {e.get("username", "") for e in load_json(PIPELINE / "blacklist.json")}
    prospects = load_prospects(platform)
    eligible = [
        p for p in prospects
        if p.get("status") == "prospect"
        and p.get("username") not in blacklist
        and p.get("touch_count", 0) < 2
        and (not TARGET_COUNTRIES or p.get("country") in TARGET_COUNTRIES)
    ]

    def priority(p):
        try:
            return PRIORITY_COUNTRIES.index(p.get("country", ""))
        except ValueError:
            return 99

    eligible.sort(key=priority)
    return eligible[:n]


def generate_warmup_comment(business: str) -> str:
    business_lower = (business or "").lower()
    if any(w in business_lower for w in ["rental", "aluguel", "locação", "alquiler", "arriendo", "renta", "임대", "렌탈"]):
        options = [
            "Clean rental setup — what panel pitch are you running for indoor events?",
            "Nice event deployment. Are those quick-lock cabinets? Curious about your stacking height.",
            "Solid LED wall build. How's the pixel pitch working out for close viewing distances?",
        ]
    elif any(w in business_lower for w in ["outdoor", "billboard", "ooh", "옥외", "telão", "pantalla gigante"]):
        options = [
            "Great outdoor install — what's the brightness rating on those panels?",
            "Nice fixed outdoor setup. How's the IP rating holding up in your climate?",
            "Impressive billboard work. Are those SMD or GOB surface treatment panels?",
        ]
    elif any(w in business_lower for w in ["church", "stadium", "교회", "경기장", "fine pitch", "fine-pitch"]):
        options = [
            "Sharp fine pitch install — what's the viewing distance from the back row?",
            "Great resolution on that screen. Fine pitch LED or COB technology?",
            "Clean integration. How's the refresh rate for camera recording in that venue?",
        ]
    else:
        options = [
            "Nice LED work — what pixel pitch is that?",
            "Clean install. Indoor or outdoor rated panels?",
            "Great LED project. How long has that been running?",
        ]
    return random.choice(options)


def run_warmup_instagram(username: str, business: str) -> bool:
    comment = generate_warmup_comment(business)

    # 点赞最近3条帖子
    for idx in range(1, 4):
        cmd = f'opencli instagram like "{username}" --index {idx}'
        print(f"    > {cmd}")
        ret = os.system(cmd)
        if ret != 0:
            print(f"    ! 点赞 #{idx} 失败（可能帖子不足{idx}条）")
        wait = random.randint(120, 300)
        print(f"    > 等待 {wait}s...")
        time.sleep(wait)

    # 评论最新帖子
    safe_comment = comment.replace('"', "'")
    cmd = f'opencli instagram comment "{username}" "{safe_comment}" --index 1'
    print(f"    > 评论: {comment}")
    ret = os.system(cmd)
    if ret != 0:
        print(f"    ! 评论失败")
        return False

    time.sleep(random.randint(60, 120))

    # 关注
    cmd = f'opencli instagram follow "{username}"'
    print(f"    > 关注")
    os.system(cmd)

    return True


def run_warmup_facebook(username: str, business: str) -> bool:
    # Facebook: 发好友请求
    cmd = f'opencli facebook add-friend "{username}"'
    print(f"    > 好友请求: {cmd}")
    ret = os.system(cmd)
    return ret == 0


def cmd_plan():
    print(f"\n{'='*60}")
    print(f"今日触达计划 {date.today().isoformat()}")
    print(f"{'='*60}")
    total = 0
    for platform in PLATFORMS:
        n = DAILY_TARGETS[platform]
        queue = select_queue(platform, n)
        print(f"\n{platform.upper()} (目标{n}条):")
        for i, p in enumerate(queue, 1):
            warmup_done = p.get("warmup_done", False)
            status = "✓ warmup已完成" if warmup_done else "待warmup"
            warmup_date = p.get("warmup_date", "")
            date_str = f" [{warmup_date}]" if warmup_date else ""
            print(f"  {i}. @{p['username']} | {p.get('company_en','')} | {p.get('country','')} | {status}{date_str}")
        total += len(queue)
    print(f"\n合计今日触达目标: {total} 人")
    print("\n执行步骤:")
    print("  Step 1: python daily_runner.py warmup   → 自动点赞+评论+关注")
    print("  Step 2: 等待 24 小时")
    print("  Step 3: python daily_runner.py send     → 生成消息，逐条人工发DM")


def cmd_warmup(auto: bool = False):
    print(f"\n{'='*60}")
    print(f"执行 Warm-up {date.today().isoformat()}{' [自动模式]' if auto else ''}")
    print(f"{'='*60}")
    if auto:
        print("自动模式：账号间自动等待5分钟，无需人工确认。可随时 Ctrl+C 中断。\n")

    for platform in PLATFORMS:
        n = DAILY_TARGETS[platform]
        prospects = load_prospects(platform)
        blacklist = {e.get("username", "") for e in load_json(PIPELINE / "blacklist.json")}
        eligible = [
            p for p in prospects
            if p.get("status") == "prospect"
            and not p.get("warmup_done")
            and p.get("username") not in blacklist
            and p.get("touch_count", 0) < 2
            and (not TARGET_COUNTRIES or p.get("country") in TARGET_COUNTRIES)
        ]
        queue = eligible[:n]
        idx_map = {p["username"]: i for i, p in enumerate(prospects)}

        print(f"\n{platform.upper()} ({len(queue)} 个账号):")
        for j, p in enumerate(queue):
            username = p["username"]
            print(f"\n  [{j+1}/{len(queue)}] @{username} | {p.get('company_en')} | {p.get('country')}")

            if platform == "instagram":
                success = run_warmup_instagram(username, p.get("business", ""))
            else:
                success = run_warmup_facebook(username, p.get("business", ""))

            if success:
                i = idx_map.get(username)
                if i is not None:
                    prospects[i]["warmup_done"] = True
                    prospects[i]["warmup_date"] = date.today().isoformat()
                    save_prospects(platform, prospects)

                log_event({
                    "platform": platform,
                    "action": "warmup_done",
                    "username": username,
                    "company": p.get("company_en"),
                    "country": p.get("country"),
                })
                print(f"    ✓ Warm-up 完成")
            else:
                print(f"    ! Warm-up 失败，跳过")

            # 账号间间隔
            if j < len(queue) - 1:
                if auto:
                    wait_sec = 300  # 自动模式固定等待5分钟
                    print(f"\n  自动等待 {wait_sec//60} 分钟后处理下一个账号...")
                    time.sleep(wait_sec)
                else:
                    wait_min = random.randint(20, 50)
                    print(f"\n  建议等待 {wait_min} 分钟后处理下一个账号")
                    print(f"  准备好后按 Enter 继续，输入 q 退出...")
                    try:
                        ans = input("  > ").strip().lower()
                    except EOFError:
                        print(f"  （非交互模式，已保存进度，下次运行继续）")
                        return
                    if ans == "q":
                        print("  已暂停，下次运行 warmup 会继续未完成的账号")
                        return

    print(f"\nWarm-up 全部完成。明天执行: python daily_runner.py send")


def cmd_send(force: bool = False):
    """半自动DM：生成消息 → QA → 打开IG主页 → 人工复制粘贴 → 确认记录"""
    from message_crafter import craft_message
    from qa_checker import QAChecker, log_send

    yesterday = (date.today() - timedelta(days=1)).isoformat()

    print(f"\n{'='*60}")
    print(f"发送 DM {date.today().isoformat()}")
    print(f"{'='*60}")
    print("流程：系统生成消息 → 自动打开对方主页 → 你复制消息手动发DM → 回车确认")
    print("提示：连接加了--force可跳过24h等待（调试用）\n")

    total_sent = 0

    for platform in PLATFORMS:
        checker = QAChecker(platform)
        n = DAILY_TARGETS[platform]
        prospects = load_prospects(platform)
        idx_map = {p["username"]: i for i, p in enumerate(prospects)}

        # 筛选：warmup完成 + 24h已过 + 目标国家
        ready = []
        for p in prospects:
            if p.get("status") != "prospect":
                continue
            if not p.get("warmup_done"):
                continue
            if not force and p.get("warmup_date", "") > yesterday:
                continue
            if p.get("touch_count", 0) >= 2:
                continue
            if TARGET_COUNTRIES and p.get("country") not in TARGET_COUNTRIES:
                continue
            ready.append(p)

        def priority(p):
            try:
                return PRIORITY_COUNTRIES.index(p.get("country", ""))
            except ValueError:
                return 99
        ready.sort(key=priority)
        queue = ready[:n]

        if not queue:
            print(f"{platform.upper()}: 无待发账号（warmup未完成或未过24h）")
            continue

        print(f"\n{'─'*50}")
        print(f"{platform.upper()} — {len(queue)} 条待发（日限 {DAILY_LIMITS[platform]}）")
        print(f"{'─'*50}")

        sent_count = 0
        for j, p in enumerate(queue):
            username = p["username"]
            company = p.get("company_en", username)
            country = p.get("country", "")

            print(f"\n[{j+1}/{len(queue)}] @{username} | {company} | {country}")

            # 生成消息
            print("  生成消息中...", end=" ", flush=True)
            try:
                message = craft_message(p, platform)
                print(f"✓ ({len(message.split())} 词)")
            except Exception as e:
                print(f"✗ 失败: {e}")
                continue

            # QA 检查
            qa = checker.check(p, message)
            if force:
                # --force 模式跳过时区检查，其余硬规则保留
                qa.failures = [f for f in qa.failures if "发送窗口" not in f and "Mon-Fri" not in f and "Tue-Thu" not in f]
                qa.passed = len(qa.failures) == 0
            if not qa.passed:
                print("  QA 拦截:")
                for f in qa.failures:
                    print(f"    ✗ {f}")
                print("  → 跳过此条")
                continue

            print("  QA 通过 ✓" + (" [--force 跳过时区检查]" if force else ""))

            # 显示消息
            print(f"\n  {'─'*40}")
            print(f"  消息内容（共 {len(message.split())} 词）:")
            print(f"  {'─'*40}")
            print(f"\n  {message}\n")
            print(f"  {'─'*40}")

            # 打开对方主页
            profile_url = PROFILE_URLS[platform].format(username=username)
            print(f"\n  正在打开: {profile_url}")
            open_in_browser(profile_url)

            # 等待人工操作
            print(f"\n  操作步骤:")
            print(f"  1. 复制上方消息")
            print(f"  2. 在浏览器中点击「发消息」/ Message")
            print(f"  3. 粘贴并发送")
            print(f"\n  完成后按 Enter 记录 ✓  |  输入 skip 跳过  |  输入 block 拉黑")
            try:
                action = input("  > ").strip().lower()
            except EOFError:
                print("  （非交互模式，自动跳过）")
                continue

            if action == "block":
                # 加入黑名单
                blacklist = load_json(PIPELINE / "blacklist.json")
                blacklist.append({"username": username, "platform": platform, "date": date.today().isoformat()})
                save_json(PIPELINE / "blacklist.json", blacklist)
                print(f"  已将 @{username} 加入 blacklist")
                continue
            elif action == "skip":
                print(f"  跳过 @{username}")
                continue

            # 记录为已发送
            i = idx_map.get(username)
            if i is not None:
                prospects[i]["status"] = "messaged"
                prospects[i]["touch_count"] = prospects[i].get("touch_count", 0) + 1
                prospects[i]["message_sent_date"] = date.today().isoformat()
                prospects[i]["message_text"] = message
                save_prospects(platform, prospects)

            log_send(platform, p, message)
            log_event({
                "platform": platform,
                "action": "dm_sent",
                "username": username,
                "company": company,
                "country": country,
                "message": message,
            })

            sent_count += 1
            total_sent += 1
            print(f"  ✓ 已记录")

            # 显示剩余限额
            remaining = DAILY_LIMITS[platform] - sent_count
            print(f"  今日 {platform} 剩余: {remaining} 条")

            # 账号间间隔提醒（不强制sleep，人工节奏更自然）
            if j < len(queue) - 1:
                wait = random.randint(20, 50)
                print(f"\n  建议等待 {wait} 分钟后处理下一条（按 Enter 继续）")
                try:
                    input("  > ")
                except EOFError:
                    pass

        print(f"\n{platform.upper()} 今日发送: {sent_count} 条")

    print(f"\n{'='*60}")
    print(f"今日合计发送: {total_sent} 条")
    print(f"完成！明天记得检查回复: python daily_runner.py status")


def cmd_status():
    today = date.today().isoformat()
    log = load_daily_log(today)

    print(f"\n{'='*60}")
    print(f"今日状态 {today}")
    print(f"{'='*60}")

    for platform in PLATFORMS + ["whatsapp"]:
        sends = [e for e in log if e.get("platform") == platform and e.get("action") == "dm_sent"]
        warmups = [e for e in log if e.get("platform") == platform and e.get("action") == "warmup_done"]
        limit = DAILY_LIMITS.get(platform, 5)
        print(f"\n{platform.upper()}: 预热 {len(warmups)} | 发送 {len(sends)}/{limit}")
        for s in sends:
            print(f"  ✓ @{s.get('username')} ({s.get('country')})")

    # 总pipeline进度
    print(f"\n{'─'*40}")
    print("Pipeline 总进度:")
    for platform in PLATFORMS:
        prospects = load_prospects(platform)
        by_status = {}
        for p in prospects:
            s = p.get("status", "prospect")
            by_status[s] = by_status.get(s, 0) + 1
        print(f"  {platform}: " + " | ".join(f"{k}={v}" for k, v in by_status.items()))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "plan":
        cmd_plan()
    elif args[0] == "warmup":
        cmd_warmup(auto="--auto" in args)
    elif args[0] == "send":
        cmd_send(force="--force" in args)
    elif args[0] == "status":
        cmd_status()
    else:
        print(__doc__)
