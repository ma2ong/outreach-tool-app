"""
IG Warmup v35 - USA v33 batch (8 accounts)
specialfxrentals, abavrentals, atl_proav, rayne_events,
promosamgmt, coloradoliveevents, centricevents, vegasledrentals
"""
import json, sys, time, random, datetime, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
IG_PIPELINE = BASE / "pipeline/instagram/prospects.json"
TODAY = datetime.date.today().isoformat()

TARGET_USERNAMES = [
    "specialfxrentals",
    "abavrentals",
    "atl_proav",
    "rayne_events",
    "promosamgmt",
    "coloradoliveevents",
    "centricevents",
    "vegasledrentals",
]


def cdp(path, body=None, timeout=15):
    args = ["curl", "-s", "--max-time", str(timeout)]
    if body is not None:
        args += ["-X", "POST", f"{CDP}{path}", "-d", body]
    else:
        args += [f"{CDP}{path}"]
    r = subprocess.run(args, capture_output=True, timeout=timeout + 5)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def eval_js(tid, js, timeout=12):
    r = cdp(f"/eval?target={tid}", js, timeout=timeout)
    return r.get("value", "")


def open_tab(url):
    r = cdp(f"/new?url={url}")
    return r.get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def warmup_account(username: str) -> bool:
    url = f"https://www.instagram.com/{username}/"
    print(f"  → 打开: {url}", flush=True)
    tid = open_tab(url)
    if not tid:
        print("  ✗ 无法创建 tab", flush=True)
        return False

    time.sleep(6)

    info = cdp(f"/info?target={tid}")
    if "instagram.com" not in info.get("url", ""):
        print(f"  ✗ 页面未加载: {info.get('url', '')}", flush=True)
        close_tab(tid)
        return False

    like_result = eval_js(tid, r"""
(function() {
  var posts = document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]');
  if (!posts || posts.length === 0) return JSON.stringify({ok: false, reason: "no posts found"});
  posts[0].click();
  return JSON.stringify({ok: true, action: "opened first post"});
})()
""", timeout=10)
    try:
        lr = json.loads(like_result) if like_result else {}
    except Exception:
        lr = {}

    if not lr.get("ok"):
        print(f"  ✗ 打开帖子失败: {lr}", flush=True)
        close_tab(tid)
        return False

    time.sleep(4)

    like_click = eval_js(tid, r"""
(function() {
  var svg = document.querySelector('svg[aria-label="赞"]') ||
            document.querySelector('svg[aria-label="Like"]');
  if (!svg) return JSON.stringify({ok: false, reason: "like button not found"});
  var el = svg;
  for (var i = 0; i < 10; i++) {
    if (el.tagName === 'BUTTON' || el.getAttribute('role') === 'button') {
      el.click();
      return JSON.stringify({ok: true});
    }
    if (!el.parentElement) break;
    el = el.parentElement;
  }
  svg.click();
  return JSON.stringify({ok: true, method: "svg direct"});
})()
""")
    try:
        lc = json.loads(like_click) if like_click else {}
    except Exception:
        lc = {}
    print(f"  like: {lc}", flush=True)

    time.sleep(2)

    cdp(f"/navigate?target={tid}&url={url}")
    time.sleep(4)

    follow_result = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll('[role="button"], button'));
  var followBtn = btns.find(b => {
    var t = b.innerText.trim();
    return t === "关注" || t === "Follow";
  });
  if (!followBtn) return JSON.stringify({ok: false, reason: "follow button not found (may already follow)"});
  followBtn.click();
  return JSON.stringify({ok: true});
})()
""")
    try:
        fr = json.loads(follow_result) if follow_result else {}
    except Exception:
        fr = {}
    print(f"  follow: {fr}", flush=True)

    close_tab(tid)
    return True


def mark_warmup_done(username: str):
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    for p in data:
        if p.get("username") == username:
            p["warmup_done"] = True
            p["warmup_date"] = TODAY
            break
    with open(IG_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    prospects = {p["username"]: p for p in data}

    queue = [u for u in TARGET_USERNAMES
             if u in prospects
             and not prospects[u].get("warmup_done")]

    print(f"=== IG Warmup v35 | {len(queue)} USA v33 accounts | {TODAY} ===\n", flush=True)

    done = 0
    for i, username in enumerate(queue, 1):
        p = prospects[username]
        print(f"[{i}/{len(queue)}] @{username} | {p.get('company_en', '')} | {p.get('city', '')}", flush=True)
        ok = warmup_account(username)
        if ok:
            mark_warmup_done(username)
            done += 1
            print(f"  ✓ warmup done\n", flush=True)
        else:
            print(f"  ✗ warmup failed\n", flush=True)

        if i < len(queue):
            wait = random.randint(90, 150)
            print(f"  waiting {wait}s before next...\n", flush=True)
            time.sleep(wait)

    print(f"=== Done: {done}/{len(queue)} warmed up ===")


if __name__ == "__main__":
    main()
