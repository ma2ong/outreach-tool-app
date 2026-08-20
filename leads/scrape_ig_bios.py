"""
Scrape Instagram bios for Korean prospects via CDP proxy.
Extracts email, phone, website from bio text.
Updates prospects.json with found contact info.
"""
import json, re, time, sys, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}")
PHONE_RE = re.compile(r"(?:\+82|0)[\s\-]?\d{1,4}[\s\-]?\d{3,4}[\s\-]?\d{4}")

JUNK = {"wixpress", "sentry", "example", "naver.com", "kakao.com"}


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


def open_tab(url):
    r = cdp(f"/new?url={url}")
    return r.get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def eval_js(tid, js, timeout=10):
    r = cdp(f"/eval?target={tid}", js, timeout=timeout)
    return r.get("value", "")


def get_ig_bio(username):
    url = f"https://www.instagram.com/{username}/"
    tid = open_tab(url)
    if not tid:
        return {}

    time.sleep(5)  # wait for IG to load

    # Extract bio, website, email, phone from page
    js = """
    (function() {
      var result = {};
      // Bio text
      var bioEl = document.querySelector('span._ap3a') ||
                  document.querySelector('h1 ~ div span') ||
                  document.querySelector('section main header section div span');
      if (bioEl) result.bio = bioEl.innerText;

      // Try meta description as fallback
      var meta = document.querySelector('meta[name="description"]');
      if (meta) result.meta = meta.getAttribute('content');

      // Website link
      var links = Array.from(document.querySelectorAll('a[href]'));
      var extLinks = links.filter(a => a.href && !a.href.includes('instagram.com') &&
                                       !a.href.includes('facebook.com') &&
                                       a.closest('header'));
      if (extLinks.length) result.website = extLinks[0].href;

      // All text in header section
      var header = document.querySelector('header');
      if (header) result.headerText = header.innerText;

      return JSON.stringify(result);
    })()
    """
    data_str = eval_js(tid, js)
    close_tab(tid)

    try:
        data = json.loads(data_str) if data_str else {}
    except Exception:
        data = {}

    # Combine all text sources for email/phone extraction
    all_text = " ".join(filter(None, [
        data.get("bio", ""),
        data.get("meta", ""),
        data.get("headerText", ""),
    ]))

    result = {}
    # Extract email
    for m in EMAIL_RE.finditer(all_text):
        addr = m.group(0).lower().rstrip(".")
        if not any(j in addr for j in JUNK):
            result["email"] = addr
            break
    # Extract phone (Korean format)
    for m in PHONE_RE.finditer(all_text):
        result["phone_ig"] = m.group(0).strip()
        break
    # Website
    if data.get("website"):
        result["website_ig"] = data["website"]

    result["bio"] = data.get("bio", "") or data.get("meta", "")[:200]
    return result


def main():
    with open(PROSPECTS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # Targets: Korea prospects with Instagram but no email
    targets = [
        p for p in data
        if p.get("country") == "Korea"
        and p.get("status") == "prospect"
        and p.get("instagram", "").strip()
        and not (p.get("email", "").strip() and
                 not any(j in p.get("email", "") for j in JUNK))
    ]

    print(f"Scraping {len(targets)} Instagram profiles...\n", flush=True)
    found = 0

    for i, p in enumerate(targets, 1):
        ig = p["instagram"].strip()
        print(f"[{i}/{len(targets)}] no:{p['no']} {p['company_en']}  @{ig}", flush=True)

        info = get_ig_bio(ig)
        bio = info.get("bio", "")
        print(f"  bio: {bio[:80]}" if bio else "  bio: (empty)", flush=True)

        changed = False
        if info.get("email"):
            p["email"] = info["email"]
            print(f"  → email: {info['email']}", flush=True)
            changed = True
        if info.get("website_ig") and not p.get("website"):
            p["website"] = info["website_ig"]
            print(f"  → website: {info['website_ig']}", flush=True)
            changed = True
        if info.get("phone_ig"):
            print(f"  → phone (IG): {info['phone_ig']}", flush=True)

        if changed:
            found += 1

        time.sleep(2)
        print(flush=True)

    with open(PROSPECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Done. Found new info for {found}/{len(targets)} accounts.", flush=True)


if __name__ == "__main__":
    main()
