"""
IG Warmup v50 — v50 USA batch (1 account with Instagram)
Zasco Productions (@zascoproduction) - Chicopee, MA
"""
import json, sys, time, random, datetime, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
IG_PIPELINE = BASE / "pipeline/instagram/prospects.json"
TODAY = datetime.date.today().isoformat()

TARGET_USERNAMES = [
    "zascoproduction",
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
    return cdp(f"/eval?target={tid}", js, timeout=timeout).get("value", "")


def open_tab(url):
    return cdp(f"/new?url={url}").get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def load_pipeline():
    with open(IG_PIPELINE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pipeline(data):
    with open(IG_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def mark_warmup_done(username):
    data = load_pipeline()
    for p in data:
        if p.get("instagram") == username:
            p["warmup_done"] = True
            p["warmup_date"] = TODAY
            break
    else:
        data.append({"instagram": username, "warmup_done": True, "warmup_date": TODAY,
                     "status": "prospect", "touch_count": 0})
    save_pipeline(data)


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
        print(f"  ✗ 页面未加载", flush=True)
        close_tab(tid)
        return False

    like_result = eval_js(tid, r"""
(function() {
  var posts = document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]');
  if (!posts || posts.length === 0) return JSON.stringify({ok: false, reason: "no posts found"});
  posts[0].click();
  return JSON.stringify({ok: true});
})()
""", timeout=10)
    try:
        lr = json.loads(like_result) if like_result else {}
    except Exception:
        lr = {}
    print(f"  like result: {lr}", flush=True)
    time.sleep(3)

    follow_result = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("button"));
  var btn = btns.find(b => b.innerText.trim() === "关注" || b.innerText.trim() === "Follow");
  if (btn) { btn.click(); return JSON.stringify({ok: true, text: btn.innerText.trim()}); }
  return JSON.stringify({ok: false, btns: btns.map(b => b.innerText.trim()).filter(t => t).slice(0, 10)});
})()
""", timeout=10)
    try:
        fr = json.loads(follow_result) if follow_result else {}
    except Exception:
        fr = {}
    print(f"  follow result: {fr}", flush=True)

    close_tab(tid)
    mark_warmup_done(username)
    return True


def main():
    print(f"=== IG Warmup v50 | {len(TARGET_USERNAMES)} accounts | {TODAY} ===", flush=True)
    for i, username in enumerate(TARGET_USERNAMES, 1):
        print(f"\n[{i}/{len(TARGET_USERNAMES)}] @{username}", flush=True)
        warmup_account(username)
        if i < len(TARGET_USERNAMES):
            wait = random.randint(120, 240)
            print(f"  waiting {wait}s...", flush=True)
            time.sleep(wait)
    print(f"\n=== Done. Run ig_dm_v50.py after 24h ===", flush=True)


if __name__ == "__main__":
    main()
