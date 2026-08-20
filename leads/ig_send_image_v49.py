"""
IG Image Send v49 — sends Korea project image to v49 IG accounts
that received text-only DMs. Opens existing DM thread, uploads image via CDP.
Targets: soflostudio, allproaudiovisual, vegaseventgroup (+ tsvusa/mediaquestpgh/mastersoundpro if needed)
"""
import json, sys, time, random, datetime, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
IG_PIPELINE = BASE / "pipeline/instagram/prospects.json"
TODAY = datetime.date.today().isoformat()
IMAGE_PATH = r"C:\Users\Administrator\Desktop\korea-led-projects-poster-4k.jpg"

# Accounts that received text-only DMs — send image follow-up
TARGET_USERNAMES = [
    "soflostudio",
    "allproaudiovisual",
    "vegaseventgroup",
    "tsvusa",
    "mediaquestpgh",
    "mastersoundpro",
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
    import json as _json
    body = _json.dumps({"selector": selector, "files": [filepath]})
    args = ["curl", "-s", "--max-time", str(timeout), "-X", "POST",
            f"{CDP}/setFiles?target={tid}", "-d", body]
    r = subprocess.run(args, capture_output=True, timeout=timeout + 5)
    try:
        return _json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def open_tab(url):
    return cdp(f"/new?url={url}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def send_image_dm(username: str) -> bool:
    print(f"  → Opening https://www.instagram.com/{username}/", flush=True)
    tid = open_tab("https://www.instagram.com/")
    if not tid:
        print("  ✗ Cannot create tab", flush=True)
        return False
    time.sleep(3)

    cdp(f"/navigate?target={tid}&url=https://www.instagram.com/{username}/", timeout=35)
    cdp(f"/activate?target={tid}")
    time.sleep(10)

    # Click "Message" button to open existing DM thread
    msg_btn = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button], button"));
  var btn = btns.find(b => {
    var t = (b.innerText || "").trim();
    return t === "发消息" || t === "消息" || t === "Message";
  });
  if (btn) { btn.click(); return JSON.stringify({ok: true}); }
  return JSON.stringify({ok: false});
})()
""")
    try:
        mr = json.loads(msg_btn) if msg_btn else {}
    except Exception:
        mr = {}
    print(f"  msg btn: {mr}", flush=True)
    if not mr.get("ok"):
        close_tab(tid)
        return False

    time.sleep(10)
    cdp(f"/activate?target={tid}")
    time.sleep(3)

    # Look for the photo/image upload icon in DM thread
    # Try to find and click the photo icon / file input trigger
    photo_btn = eval_js(tid, r"""
(function() {
  // Try aria-label variations for photo button
  var labels = ["添加照片", "Add Photo", "Photo", "照片", "图片", "Image"];
  for (var l of labels) {
    var el = document.querySelector('[aria-label="' + l + '"]');
    if (el) { el.click(); return JSON.stringify({ok: true, label: l}); }
  }
  // Try SVG icons commonly used for photo upload in IG DM
  var svgs = Array.from(document.querySelectorAll('svg[aria-label]'));
  var sv = svgs.find(s => {
    var la = s.getAttribute('aria-label') || '';
    return la.includes('照片') || la.includes('Photo') || la.includes('Image') || la.includes('图');
  });
  if (sv) {
    var el = sv;
    for (var i = 0; i < 8; i++) {
      if (el.tagName === 'BUTTON' || el.getAttribute('role') === 'button') { el.click(); return JSON.stringify({ok: true, tag: el.tagName}); }
      if (!el.parentElement) break;
      el = el.parentElement;
    }
    sv.click();
    return JSON.stringify({ok: true, method: 'svg direct'});
  }
  return JSON.stringify({ok: false});
})()
""")
    try:
        pr = json.loads(photo_btn) if photo_btn else {}
    except Exception:
        pr = {}
    print(f"  photo btn: {pr}", flush=True)

    time.sleep(2)

    # Try to find file input and set the image
    file_result = set_files(tid, "input[type=file]", IMAGE_PATH)
    print(f"  setFiles: {file_result}", flush=True)

    if not file_result.get("ok") and not file_result.get("set"):
        # Try alternative: look for hidden file input after clicking photo icon
        file_result2 = eval_js(tid, r"""
(function() {
  var inputs = document.querySelectorAll('input[type=file]');
  return JSON.stringify({count: inputs.length, accepts: Array.from(inputs).map(i => i.accept)});
})()
""")
        print(f"  file inputs: {file_result2}", flush=True)

        # Try clicking the photo button and then setFiles
        time.sleep(1)
        file_result = set_files(tid, "input[type=file][accept*='image'], input[type=file]", IMAGE_PATH)
        print(f"  setFiles retry: {file_result}", flush=True)

    time.sleep(3)

    # Check if image preview appeared
    preview_check = eval_js(tid, r"""
(function() {
  // Look for image preview in DM compose area
  var imgs = document.querySelectorAll('img[src*="blob:"], img[src*="data:"]');
  var canvas = document.querySelectorAll('canvas');
  return JSON.stringify({imgs: imgs.length, canvas: canvas.length});
})()
""")
    print(f"  preview: {preview_check}", flush=True)

    time.sleep(2)

    # Send via Enter or send button
    send_result = eval_js(tid, r"""
(function() {
  // Try send button
  var btns = Array.from(document.querySelectorAll("[role=button],button"));
  var sendBtn = btns.find(b => {
    var label = b.getAttribute("aria-label") || "";
    return label === "发送" || label === "Send";
  });
  if (sendBtn) { sendBtn.click(); return JSON.stringify({ok: true, method: 'button'}); }
  // Try Enter on contenteditable
  var inp = document.querySelector('[contenteditable=true]');
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
    # Only send to accounts that are already messaged
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    messaged = {(p.get("username") or p.get("instagram", "")): p
                for p in data if p.get("status") == "messaged"}

    queue = [u for u in TARGET_USERNAMES if u in messaged]
    print(f"=== IG Image Send v49 | {len(queue)} accounts | {TODAY} ===\n", flush=True)
    print(f"Image: {IMAGE_PATH}\n", flush=True)

    sent = 0
    for i, username in enumerate(queue, 1):
        p = messaged[username]
        print(f"[{i}/{len(queue)}] @{username} | {p.get('company_en', '')} | {p.get('city', '')}", flush=True)
        ok = send_image_dm(username)
        if ok:
            sent += 1
            print(f"  ✓ Image sent\n", flush=True)
        else:
            print(f"  ✗ Failed\n", flush=True)
        if i < len(queue):
            wait = random.randint(90, 150)
            print(f"  waiting {wait}s...\n", flush=True)
            time.sleep(wait)

    print(f"=== Done: {sent}/{len(queue)} images sent ===")


if __name__ == "__main__":
    main()
