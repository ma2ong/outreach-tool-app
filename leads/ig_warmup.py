"""
Instagram + Facebook warmup via CDP.
For each prospect with IG/FB handle: Follow their account + like most recent post.
Runs through Chrome's existing login session (no credentials needed).

Usage: python ig_warmup.py [--country Korea] [--limit 20]
"""
import json, ast, re, sys, time, random, urllib.parse, subprocess, argparse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
WARMUP_LOG = BASE / "pipeline/warmup_log.json"


def cdp(path, body=None, timeout=20):
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


def open_tab(url):
    r = cdp(f"/new?url={url}")
    return r.get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def eval_js(tid, js, timeout=12):
    r = cdp(f"/eval?target={tid}", js, timeout=timeout)
    return r.get("value", "")


def load_all_leads():
    v4_src = open(BASE / "generate_led_leads_v4.py", encoding="utf-8").read()
    leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", v4_src, re.M | re.S).group(1))
    for vname in [f"v{i}" for i in range(5, 23)]:
        path = BASE / f"generate_led_leads_{vname}.py"
        if not path.exists():
            continue
        src = open(path, encoding="utf-8").read()
        m = re.search(r"^new_entries = (\[.+?^\])", src, re.M | re.S)
        if m:
            leads.extend(ast.literal_eval(m.group(1)))
    return leads


def load_warmup_log():
    if WARMUP_LOG.exists():
        with open(WARMUP_LOG, encoding="utf-8") as f:
            return json.load(f)
    return {"ig_followed": [], "fb_liked": []}


def save_warmup_log(log):
    WARMUP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(WARMUP_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def ig_warmup(username: str, keep_open: bool = False) -> str:
    """Follow + like top post on Instagram. Returns 'followed'/'already'/'failed'."""
    # Strip any URL prefix if present
    username = re.sub(r'^https?://(www\.)?instagram\.com/?', '', username).strip("/")
    url = f"https://www.instagram.com/{username}/"
    tid = open_tab(url)
    if not tid:
        return "failed"

    time.sleep(5)

    # Check if Follow button exists (handles both EN and ZH UI)
    result = eval_js(tid, """
    (function() {
        var btns = Array.from(document.querySelectorAll('button'));
        // Click Follow (EN) or 关注 (ZH)
        var followBtn = btns.find(b => {
            var t = b.innerText.trim();
            return t === 'Follow' || t === 'Follow Back' || t === '关注' || t === '回关';
        });
        if (followBtn) {
            followBtn.click();
            return 'clicked_follow';
        }
        // Already following
        var followingBtn = btns.find(b => {
            var t = b.innerText.trim();
            return t === 'Following' || t === 'Message' || t === '已关注' || t === '互相关注' || t === '发消息';
        });
        if (followingBtn) return 'already_following';
        // Login wall
        if (document.querySelector('[data-testid="login-username"]') ||
            document.querySelector('input[name="username"]')) return 'login_wall';
        return 'no_button';
    })()
    """, timeout=10)

    time.sleep(2)

    # Like the most recent post
    like_result = eval_js(tid, """
    (function() {
        // Find first post link
        var links = Array.from(document.querySelectorAll('a[href*="/p/"]'));
        if (links.length > 0) {
            return links[0].href;
        }
        return null;
    })()
    """, timeout=8)

    liked = False
    if like_result and "/p/" in str(like_result):
        if not keep_open:
            close_tab(tid)
        time.sleep(1)
        tid2 = open_tab(like_result)
        if tid2:
            time.sleep(4)
            like_click = eval_js(tid2, """
            (function() {
                // Find like button (EN or ZH aria-label)
                var likeBtn = document.querySelector('[aria-label="Like"]') ||
                              document.querySelector('[aria-label="赞"]') ||
                              document.querySelector('svg[aria-label="Like"]') ||
                              document.querySelector('svg[aria-label="赞"]');
                if (likeBtn) {
                    (likeBtn.closest('button') || likeBtn).click();
                    return 'liked';
                }
                return 'no_like_btn';
            })()
            """, timeout=8)
            liked = like_click == "liked"
            if not keep_open:
                close_tab(tid2)
        elif not keep_open:
            close_tab(tid)
    elif not keep_open:
        close_tab(tid)

    if result == "clicked_follow":
        return "followed" + ("+liked" if liked else "")
    elif result == "already_following":
        return "already" + ("+liked" if liked else "")
    else:
        return f"no_btn({result})"


def fb_warmup(page_handle: str) -> str:
    """Like/Follow Facebook page. Returns status string."""
    url = f"https://www.facebook.com/{page_handle}"
    tid = open_tab(url)
    if not tid:
        return "failed"

    time.sleep(5)

    result = eval_js(tid, """
    (function() {
        var btns = Array.from(document.querySelectorAll('[role="button"]'));
        var likeBtn = btns.find(b => {
            var t = b.innerText.trim();
            return t === 'Like' || t === 'Follow' || t === 'Like Page' ||
                   t === '赞' || t === '喜欢' || t === '关注';
        });
        if (likeBtn) {
            likeBtn.click();
            return 'clicked_' + likeBtn.innerText.trim();
        }
        var liked = btns.find(b => {
            var t = b.innerText.trim();
            return t === 'Liked' || t === 'Following' || t === '已赞' || t === '取消关注';
        });
        if (liked) return 'already';
        return 'not_found';
    })()
    """, timeout=10)

    close_tab(tid)
    return result or "failed"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", default="", help="Filter by country (empty=all)")
    parser.add_argument("--limit", type=int, default=20, help="Max accounts to warm up this run")
    parser.add_argument("--platform", default="ig", choices=["ig", "fb", "both"], help="Which platform")
    parser.add_argument("--keep-open", action="store_true", help="Keep browser tabs open after warmup")
    args = parser.parse_args()

    leads = load_all_leads()
    log = load_warmup_log()

    done_ig = set(log.get("ig_followed", []))
    done_fb = set(log.get("fb_liked", []))

    # Build target list
    ig_targets = []
    fb_targets = []

    for l in leads:
        country = l.get("country", "")
        if args.country and country != args.country:
            continue
        ig = l.get("instagram", "").strip()
        fb = l.get("facebook", "").strip()
        if ig and ig not in done_ig:
            ig_targets.append(l)
        if fb and fb not in done_fb:
            fb_targets.append(l)

    print(f"IG targets: {len(ig_targets)} | FB targets: {len(fb_targets)}")
    print(f"Limit per platform: {args.limit}")
    print()

    count = 0

    if args.platform in ("ig", "both"):
        for l in ig_targets[:args.limit]:
            ig = l["instagram"].strip()
            print(f"[IG] no:{l['no']} {l['country']} {l['company_en']}  @{ig}", flush=True)
            result = ig_warmup(ig, keep_open=args.keep_open)
            print(f"  → {result}", flush=True)
            done_ig.add(ig)
            log["ig_followed"] = list(done_ig)
            save_warmup_log(log)
            count += 1
            wait = random.randint(20, 40)
            print(f"  waiting {wait}s...", flush=True)
            time.sleep(wait)

    if args.platform in ("fb", "both"):
        for l in fb_targets[:args.limit]:
            fb = l["facebook"].strip()
            print(f"[FB] no:{l['no']} {l['country']} {l['company_en']}  fb/{fb}", flush=True)
            result = fb_warmup(fb)
            print(f"  → {result}", flush=True)
            done_fb.add(fb)
            log["fb_liked"] = list(done_fb)
            save_warmup_log(log)
            count += 1
            wait = random.randint(15, 30)
            print(f"  waiting {wait}s...", flush=True)
            time.sleep(wait)

    print(f"\nDone. {count} accounts warmed up.")
    print(f"Total IG done: {len(done_ig)} | FB done: {len(done_fb)}")


if __name__ == "__main__":
    main()
