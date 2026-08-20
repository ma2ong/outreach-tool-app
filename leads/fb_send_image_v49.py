"""
FB Image Send v49 — sends Korea project image to @AmericanLedDisplays (no=110)
Opens existing Messenger thread and uploads the image via CDP /setFiles.
"""
import json, sys, time, datetime, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
FB_PIPELINE = BASE / "pipeline/facebook/prospects.json"
TODAY = datetime.date.today().isoformat()
IMAGE_PATH = r"C:\Users\Administrator\Desktop\korea-led-projects-poster-4k.jpg"

TARGETS = [
    {"no": 110, "facebook": "AmericanLedDisplays", "company_en": "American LED Display Solutions"},
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


def set_files(tid, selector, filepath, timeout=10):
    body = json.dumps({"selector": selector, "files": [filepath]})
    args = ["curl", "-s", "--max-time", str(timeout), "-X", "POST",
            f"{CDP}/setFiles?target={tid}", "-d", body]
    r = subprocess.run(args, capture_output=True, timeout=timeout + 5)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def open_tab(url):
    return cdp(f"/new?url={url}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def send_fb_image(fb_handle: str) -> bool:
    # Open existing messenger thread
    url = f"https://www.facebook.com/messages/t/{fb_handle}"
    print(f"  → Opening {url}", flush=True)
    tid = open_tab(url)
    if not tid:
        print("  ✗ Cannot create tab", flush=True)
        return False
    time.sleep(8)
    cdp(f"/activate?target={tid}")
    time.sleep(3)

    info = cdp(f"/info?target={tid}")
    print(f"  URL: {info.get('url','')[:70]}", flush=True)

    # Click the photo/attachment icon in FB Messenger
    photo_btn = eval_js(tid, r"""
(function() {
  var labels = ["Photo", "照片", "Attach a photo or video", "Add Photo or Video",
                "Photo/Video", "选择图片", "Image"];
  for (var l of labels) {
    var el = document.querySelector('[aria-label="' + l + '"]');
    if (el) { el.click(); return JSON.stringify({ok: true, label: l}); }
  }
  // Find camera/photo SVG icon buttons
  var svgs = Array.from(document.querySelectorAll('[aria-label]'));
  var sv = svgs.find(s => {
    var la = (s.getAttribute('aria-label') || '').toLowerCase();
    return la.includes('photo') || la.includes('image') || la.includes('attach') || la.includes('照片');
  });
  if (sv) { sv.click(); return JSON.stringify({ok: true, found: sv.getAttribute('aria-label')}); }
  return JSON.stringify({ok: false});
})()
""")
    try:
        pr = json.loads(photo_btn) if photo_btn else {}
    except Exception:
        pr = {}
    print(f"  photo btn: {pr}", flush=True)
    time.sleep(2)

    # Try setFiles on the file input
    fr = set_files(tid, "input[type=file]", IMAGE_PATH)
    print(f"  setFiles: {fr}", flush=True)

    if not (fr.get("ok") or fr.get("set")):
        # Check available file inputs
        fi_check = eval_js(tid, r"""
(function() {
  var inputs = Array.from(document.querySelectorAll('input[type=file]'));
  return JSON.stringify({count: inputs.length, accepts: inputs.map(i => i.accept || 'any')});
})()
""")
        print(f"  file inputs: {fi_check}", flush=True)
        # Try clicking photo area buttons and retry
        eval_js(tid, r"""
(function() {
  // Try the + or attachment expand button
  var btns = Array.from(document.querySelectorAll('[role=button]'));
  var expand = btns.find(b => {
    var la = (b.getAttribute('aria-label') || '').toLowerCase();
    return la.includes('more') || la.includes('attach') || la.includes('更多') || la === '+';
  });
  if (expand) expand.click();
})()
""")
        time.sleep(1)
        fr = set_files(tid, "input[type=file]", IMAGE_PATH)
        print(f"  setFiles retry: {fr}", flush=True)

    time.sleep(3)

    # Check for image preview
    preview = eval_js(tid, r"""
(function() {
  var imgs = document.querySelectorAll('img[src*="blob:"], img[src*="data:"]');
  var previews = document.querySelectorAll('[class*="preview"], [class*="thumb"]');
  return JSON.stringify({blobs: imgs.length, previews: previews.length});
})()
""")
    print(f"  preview: {preview}", flush=True)

    time.sleep(1)

    # Send
    send_result = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button], button"));
  var sb = btns.find(b => {
    var la = (b.getAttribute("aria-label") || b.innerText || "").toLowerCase().trim();
    return la === "send" || la === "发送" || la === "press enter to send";
  });
  if (sb) { sb.click(); return JSON.stringify({ok: true, method: 'button'}); }
  // Enter key on input area
  var inp = document.querySelector('[contenteditable=true], [role=textbox]');
  if (inp) {
    inp.dispatchEvent(new KeyboardEvent("keydown", {key:"Enter", keyCode:13, bubbles:true}));
    return JSON.stringify({ok: true, method: 'enter'});
  }
  return JSON.stringify({ok: false});
})()
""")
    try:
        sr = json.loads(send_result) if send_result else {}
    except Exception:
        sr = {}
    print(f"  send: {sr}", flush=True)

    time.sleep(3)
    close_tab(tid)
    return sr.get("ok", False)


def main():
    print(f"=== FB Image Send v49 | {len(TARGETS)} targets | {TODAY} ===\n", flush=True)
    print(f"Image: {IMAGE_PATH}\n", flush=True)
    sent = 0
    for t in TARGETS:
        print(f"@{t['facebook']} | {t['company_en']}", flush=True)
        ok = send_fb_image(t["facebook"])
        if ok:
            sent += 1
            print(f"  ✓ Image sent\n", flush=True)
        else:
            print(f"  ✗ Failed\n", flush=True)
    print(f"=== Done: {sent}/{len(TARGETS)} images sent ===")


if __name__ == "__main__":
    main()
