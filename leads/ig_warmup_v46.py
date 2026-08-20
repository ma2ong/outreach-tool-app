"""IG Warmup v46 — like + follow 4 accounts before DM"""
import json, sys, time, random, datetime, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
IG_PIPELINE = BASE / "pipeline/instagram/prospects.json"
TODAY = datetime.date.today().isoformat()

TARGET_USERNAMES = [
    "xperienceent",
    "phoenixledscreens",
    "limelightsentertain",
    "mtisoundlighting",
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
    return cdp(f"/new?url={url}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def warmup(username: str) -> bool:
    print(f"  → 打开: https://www.instagram.com/{username}/", flush=True)
    tid = open_tab(f"https://www.instagram.com/{username}/")
    if not tid:
        print("  ✗ 无法创建 tab", flush=True)
        return False
    time.sleep(10)
    cdp(f"/activate?target={tid}")
    time.sleep(3)

    # Like first post
    like_r = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("[aria-label='赞'], [aria-label='Like']"));
  if (btns.length > 0) { btns[0].click(); return JSON.stringify({ok: true}); }
  return JSON.stringify({ok: false, reason: 'like button not found'});
})()
""")
    try:
        lr = json.loads(like_r) if like_r else {}
    except Exception:
        lr = {}
    print(f"  like: {lr}", flush=True)

    time.sleep(2)

    # Follow
    follow_r = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button], button"));
  var btn = btns.find(b => {
    var t = (b.innerText || "").trim();
    return t === "关注" || t === "Follow";
  });
  if (btn) { btn.click(); return JSON.stringify({ok: true}); }
  return JSON.stringify({ok: false, reason: 'follow button not found (may already follow)'});
})()
""")
    try:
        fr = json.loads(follow_r) if follow_r else {}
    except Exception:
        fr = {}
    print(f"  follow: {fr}", flush=True)

    close_tab(tid)

    # Mark warmup in pipeline
    igdata = json.load(open(IG_PIPELINE, encoding="utf-8"))
    for p in igdata:
        if p.get("username") == username or p.get("instagram") == username:
            p["warmup_done"] = True
            p["warmup_date"] = TODAY
            break
    with open(IG_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(igdata, f, ensure_ascii=False, indent=2)

    return True


def main():
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    prospects = {(p.get("username") or p.get("instagram", "")): p for p in data}

    print(f"=== IG Warmup v46 | {len(TARGET_USERNAMES)} accounts | {TODAY} ===\n", flush=True)

    done = 0
    for i, username in enumerate(TARGET_USERNAMES, 1):
        p = prospects.get(username, {})
        print(f"[{i}/{len(TARGET_USERNAMES)}] @{username} | {p.get('company_en', '')} | {p.get('city', '')}", flush=True)
        warmup(username)
        done += 1
        print(f"  ✓ warmup done\n", flush=True)
        if i < len(TARGET_USERNAMES):
            wait = random.randint(80, 130)
            print(f"  waiting {wait}s...\n", flush=True)
            time.sleep(wait)

    print(f"=== Done: {done}/{len(TARGET_USERNAMES)} accounts warmed up ===")
    print("Next: run ig_dm_v46.py")


if __name__ == "__main__":
    main()
