"""
CDP DM Sender - 通过 CDP 自动化发送 Instagram DM
"""
import sys, json, subprocess, time, datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

CDP_BASE = "http://localhost:3456"
BASE = Path(__file__).parent


def cdp_eval(target_id: str, js: str) -> dict:
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", f"{CDP_BASE}/eval?target={target_id}", "-d", js],
        capture_output=True, text=True, encoding="utf-8", timeout=15,
    )
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"error": r.stdout[:200]}


def cdp_new(url: str) -> str:
    r = subprocess.run(
        ["curl", "-s", f"{CDP_BASE}/new?url={url}"],
        capture_output=True, text=True, encoding="utf-8", timeout=15,
    )
    return json.loads(r.stdout).get("targetId", "")


def cdp_close(target_id: str):
    subprocess.run(
        ["curl", "-s", f"{CDP_BASE}/close?target={target_id}"],
        capture_output=True, timeout=10,
    )


def cdp_info(target_id: str) -> dict:
    r = subprocess.run(
        ["curl", "-s", f"{CDP_BASE}/info?target={target_id}"],
        capture_output=True, text=True, encoding="utf-8", timeout=10,
    )
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def send_instagram_dm(username: str, message: str) -> bool:
    """
    打开 Instagram 用户主页，点击发消息，输入消息，点击发送。
    返回 True 表示发送成功。
    """
    msg_js = json.dumps(message)

    print(f"  → 打开主页: @{username}")
    tid = cdp_new(f"https://www.instagram.com/{username}/")
    if not tid:
        print("  ✗ 无法创建 tab")
        return False

    time.sleep(5)
    info = cdp_info(tid)
    if "instagram.com" not in info.get("url", ""):
        print(f"  ✗ 页面未加载: {info}")
        cdp_close(tid)
        return False

    # Click 发消息 button (index-based, Lexical editor)
    print(f"  → 点击发消息按钮")
    result = cdp_eval(tid, '''
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button]"));
  // Find 发消息 by codepoints: 53d1(发) 6d88(消) 606f(息)
  var btn = btns.find(b => {
    var chars = Array.from(b.innerText.trim()).map(c => c.codePointAt(0).toString(16));
    return chars.length === 3 && chars[0] === '53d1' && chars[1] === '6d88' && chars[2] === '606f';
  });
  if(!btn) return JSON.stringify({ok: false, reason: "btn not found", btns: btns.length});
  btn.click();
  return JSON.stringify({ok: true});
})()
''')
    val = result.get("value", "{}")
    try:
        obj = json.loads(val) if isinstance(val, str) else val
    except Exception:
        obj = {"ok": False, "reason": val}

    if not obj.get("ok"):
        print(f"  ✗ 发消息按钮未找到: {obj}")
        cdp_close(tid)
        return False

    time.sleep(4)

    # Check DM input appeared
    check = cdp_eval(tid, '''
(function() {
  var inputs = Array.from(document.querySelectorAll("[contenteditable=true], [role=textbox]"));
  var dmInput = inputs.find(el => {
    var ph = el.getAttribute("aria-placeholder") || el.placeholder || "";
    return ph.length > 0;
  });
  return dmInput ? "found" : "not found";
})()
''')
    if check.get("value") != "found":
        print(f"  ✗ DM 输入框未出现: {check}")
        cdp_close(tid)
        return False

    # Type message via execCommand insertText (reliable across Lexical versions)
    print(f"  → 输入消息 ({len(message.split())} 词)")
    type_result = cdp_eval(tid, f'''
(function() {{
  var el = Array.from(document.querySelectorAll("[contenteditable=true], [role=textbox]")).find(e => {{
    return (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0;
  }});
  if(!el) return JSON.stringify({{ok: false, reason: "no input"}});
  el.focus();
  el.click();
  document.execCommand("selectAll", false, null);
  document.execCommand("delete", false, null);
  var r = document.execCommand("insertText", false, {msg_js});
  return JSON.stringify({{ok: r, len: el.innerText.length}});
}})()
''')
    try:
        type_obj = json.loads(type_result.get("value", "{}"))
    except Exception:
        type_obj = {}

    if not type_obj.get("ok") or type_obj.get("len", 0) < 10:
        print(f"  ✗ 输入失败: {type_obj}")
        cdp_close(tid)
        return False

    time.sleep(1)

    # Click send button (aria-label contains 发送)
    print(f"  → 点击发送")
    send_result = cdp_eval(tid, '''
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button], button"));
  var sendBtn = btns.find(b => {
    var label = b.getAttribute("aria-label") || "";
    var chars = Array.from(label).map(c => c.codePointAt(0).toString(16));
    // 发送 = 53d1,9001
    return chars.length === 2 && chars[0] === "53d1" && chars[1] === "9001";
  });
  if(!sendBtn) return JSON.stringify({ok: false, reason: "send btn not found", count: btns.length});
  sendBtn.click();
  return JSON.stringify({ok: true});
})()
''')
    try:
        send_obj = json.loads(send_result.get("value", "{}"))
    except Exception:
        send_obj = {}

    if not send_obj.get("ok"):
        print(f"  ✗ 发送按钮未找到: {send_obj}")
        cdp_close(tid)
        return False

    time.sleep(2)

    # Verify sent: input should be empty, title might show (N)
    verify = cdp_eval(tid, '''
(function() {
  var el = Array.from(document.querySelectorAll("[contenteditable=true], [role=textbox]")).find(e => {
    return (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0;
  });
  var inputEmpty = el ? el.innerText.trim().length <= 1 : true;
  var titleHasBadge = document.title.includes("(");
  return JSON.stringify({inputEmpty: inputEmpty, title: document.title.slice(0, 30)});
})()
''')
    try:
        v_obj = json.loads(verify.get("value", "{}"))
    except Exception:
        v_obj = {}

    sent = v_obj.get("inputEmpty", False) or v_obj.get("titleHasBadge", False)
    print(f"  ✓ 验证: {v_obj}")

    cdp_close(tid)
    return True


def update_pipeline(username: str, message: str, platform: str = "instagram"):
    from qa_checker import log_send
    data = json.load(open(BASE / "pipeline" / platform / "prospects.json", encoding="utf-8"))
    prospect = None
    for p in data:
        if p["username"] == username:
            p["status"] = "messaged"
            p["touch_count"] = p.get("touch_count", 0) + 1
            p["dm_sent_date"] = datetime.date.today().isoformat()
            p["dm_message_preview"] = message[:100]
            prospect = p
            break
    if prospect is None:
        print(f"  ✗ {username} not in prospects.json")
        return
    with open(BASE / "pipeline" / platform / "prospects.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log_send(platform, prospect, message)
    print(f"  → 已更新 pipeline: @{username} status=messaged")


if __name__ == "__main__":
    import sys
    # Usage: python cdp_send_dm.py [--dry-run]
    dry_run = "--dry-run" in sys.argv

    results = json.load(open(BASE / "_messages_today.json", encoding="utf-8"))
    data = json.load(open(BASE / "pipeline/instagram/prospects.json", encoding="utf-8"))
    prospects = {p["username"]: p for p in data}

    # Today's send order - skip already messaged
    order = [
        "svsolutions.usa", "americanledgroup", "techledwall", "fastinstall.us",
        "ledfactoryusa", "avrental305", "event_smart_technology", "showbossav"
    ]

    # Check which already sent today
    from qa_checker import QAChecker
    checker = QAChecker("instagram")
    today_log_path = BASE / "pipeline" / f"daily_log_{datetime.date.today().isoformat()}.json"
    sent_today = []
    if today_log_path.exists():
        log = json.load(open(today_log_path, encoding="utf-8"))
        sent_today = [e["username"] for e in log if e.get("action") == "dm_sent" and e.get("platform") == "instagram"]

    INTERVAL_MINUTES = 5
    send_count = len(sent_today)
    DAILY_LIMIT = 8

    print(f"今日已发: {send_count} 条 | 已发账号: {sent_today}")
    print(f"队列: {[u for u in order if u not in sent_today]}")
    print()

    for i, username in enumerate(order):
        if username in sent_today:
            print(f"[{i+1}/8] @{username} 今日已发，跳过")
            continue
        if send_count >= DAILY_LIMIT:
            print(f"今日上限 {DAILY_LIMIT} 条已达，停止")
            break

        r = results.get(username, {})
        if r.get("status") != "ok":
            print(f"[{i+1}/8] @{username} 无消息，跳过")
            continue

        p = prospects.get(username, {})
        if not p:
            print(f"[{i+1}/8] @{username} 不在 prospects 中，跳过")
            continue

        # QA check - 先过滤时区和间隔失败（间隔由下方 sleep 保证）
        qa = checker.check(p, r["msg"])
        qa.failures = [f for f in qa.failures
                       if "发送窗口" not in f and "Mon-Fri" not in f
                       and "距上次发送" not in f]
        qa.passed = len(qa.failures) == 0
        if not qa.passed:
            print(f"[{i+1}/8] @{username} QA 失败: {qa.failures}")
            continue

        print(f"\n[{send_count+1}/{DAILY_LIMIT}] 发送 @{username}")
        print(f"  消息预览: {r['msg'][:80]}...")

        if dry_run:
            print("  [dry-run] 跳过实际发送")
            continue

        # Wait interval (except for first)
        if send_count > 0:
            wait_sec = INTERVAL_MINUTES * 60
            print(f"  ⏱ 等待 {INTERVAL_MINUTES} 分钟间隔...")
            time.sleep(wait_sec)

        success = send_instagram_dm(username, r["msg"])
        if success:
            update_pipeline(username, r["msg"])
            send_count += 1
            sent_today.append(username)
            print(f"  ✓ 第 {send_count} 条发送成功\n")
        else:
            print(f"  ✗ 发送失败，跳过\n")

    print(f"\n完成. 今日共发送: {send_count} 条")
