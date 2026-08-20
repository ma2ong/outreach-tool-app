"""
WA Image Send — SoFlo Studio (Fort Lauderdale FL, +1 954-446-5619)
Opens WA chat, attaches Korea project image via CDP /setFiles, sends.
"""
import subprocess, json, sys, time, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

TODAY = datetime.date.today().isoformat()
CDP = "http://localhost:3456"
CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
IMAGE_PATH = r"C:\Users\Administrator\Desktop\korea-led-projects-poster-4k.jpg"
PHONE = "19544465619"


def cdp(path, body=None, timeout=10):
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


def get_wa_tids():
    data = cdp("/targets")
    if isinstance(data, list):
        return {t["targetId"] for t in data if "web.whatsapp.com" in t.get("url", "")}
    return set()


def main():
    print(f"=== WA Image Send — SoFlo Studio | {TODAY} ===", flush=True)
    print(f"Phone: +{PHONE}", flush=True)
    print(f"Image: {IMAGE_PATH}\n", flush=True)

    # Find existing WA tab or open new one
    wa_send_url = f"https://web.whatsapp.com/send?phone={PHONE}"
    tabs = get_wa_tids()
    if tabs:
        tid = list(tabs)[0]
        print(f"  → Using existing WA tab {tid[:8]}, navigating to chat...", flush=True)
        cdp(f"/navigate?target={tid}&url={wa_send_url}", timeout=35)
    else:
        print(f"  → Opening WA chat...", flush=True)
        subprocess.Popen([CHROME, wa_send_url])
        deadline = time.time() + 40
        tid = None
        while time.time() < deadline:
            wa_tabs = get_wa_tids()
            if wa_tabs:
                tid = list(wa_tabs)[0]
                break
            time.sleep(0.5)
        if not tid:
            print("  ✗ WA tab not found", flush=True)
            return

    print(f"  WA tab: {tid[:8]}", flush=True)
    time.sleep(10)  # wait for chat to load

    url_check = cdp(f"/info?target={tid}").get("url", "")
    print(f"  URL: {url_check[:70]}", flush=True)

    # Check if phone is on WA (look for chat input)
    inp_check = eval_js(tid, r"""
(function() {
  var inp = document.querySelector('[data-tab="10"], [contenteditable][title], [contenteditable][data-lexical-editor]');
  var err = document.querySelector('[data-animate-modal-popup]');
  return JSON.stringify({inp: !!inp, err: !!err, url: window.location.href.slice(0, 60)});
})()
""")
    print(f"  chat check: {inp_check}", flush=True)

    # Click attachment (paperclip) icon
    clip_btn = eval_js(tid, r"""
(function() {
  var selectors = [
    '[data-icon="attach-menu-plus"]',
    '[data-icon="clip"]',
    '[aria-label="Attach"]',
    '[title="Attach"]',
    'span[data-icon="attach-menu-plus"]',
    'span[data-icon="plus"]'
  ];
  for (var s of selectors) {
    var el = document.querySelector(s);
    if (el) {
      var p = el;
      for (var i = 0; i < 8; i++) {
        if (p.tagName === 'BUTTON' || p.getAttribute('role') === 'button') { p.click(); return JSON.stringify({ok: true, sel: s}); }
        if (!p.parentElement) break;
        p = p.parentElement;
      }
      el.click();
      return JSON.stringify({ok: true, sel: s, method: 'direct'});
    }
  }
  return JSON.stringify({ok: false});
})()
""")
    try:
        cr = json.loads(clip_btn) if clip_btn else {}
    except Exception:
        cr = {}
    print(f"  clip btn: {cr}", flush=True)
    time.sleep(1)

    # Click "Photos & Videos" option that appears after clip
    photo_opt = eval_js(tid, r"""
(function() {
  var labels = ["Photos & Videos", "Photo & Video", "Photos", "Gallery"];
  for (var l of labels) {
    var el = document.querySelector('[aria-label="' + l + '"]');
    if (el) { el.click(); return JSON.stringify({ok: true, label: l}); }
  }
  // Find by data-icon
  var photoIcon = document.querySelector('[data-icon="photo-media-filled"]') ||
                  document.querySelector('[data-icon="image"]');
  if (photoIcon) {
    var p = photoIcon;
    for (var i = 0; i < 8; i++) {
      if (p.tagName === 'LI' || p.tagName === 'BUTTON' || p.getAttribute('role') === 'button') {
        p.click(); return JSON.stringify({ok: true, method: 'icon'});
      }
      if (!p.parentElement) break;
      p = p.parentElement;
    }
    photoIcon.click();
    return JSON.stringify({ok: true, method: 'icon direct'});
  }
  return JSON.stringify({ok: false});
})()
""")
    try:
        por = json.loads(photo_opt) if photo_opt else {}
    except Exception:
        por = {}
    print(f"  photo option: {por}", flush=True)
    time.sleep(1)

    # setFiles on the file input
    fr = set_files(tid, "input[type=file]", IMAGE_PATH)
    print(f"  setFiles: {fr}", flush=True)

    if not (fr.get("ok") or fr.get("success") or fr.get("set")):
        # Check available inputs
        fi = eval_js(tid, r"""
(function() {
  var inputs = Array.from(document.querySelectorAll('input[type=file]'));
  return JSON.stringify({count: inputs.length, accepts: inputs.map(i => i.accept || 'any')});
})()
""")
        print(f"  file inputs: {fi}", flush=True)
        fr = set_files(tid, "input[type=file][accept*='image'], input[type=file]", IMAGE_PATH)
        print(f"  setFiles retry: {fr}", flush=True)

    time.sleep(3)

    # Check preview
    preview = eval_js(tid, r"""
(function() {
  var imgs = document.querySelectorAll('img[src*="blob:"], img[src*="data:"]');
  var canvas = document.querySelectorAll('canvas');
  return JSON.stringify({imgs: imgs.length, canvas: canvas.length});
})()
""")
    print(f"  preview: {preview}", flush=True)

    time.sleep(1)

    # Send via send button or Enter
    send_result = eval_js(tid, r"""
(function() {
  var sendBtn = document.querySelector('[data-icon="send"]') ||
                document.querySelector('span[data-icon="wds-ic-send-filled"]') ||
                document.querySelector('[aria-label="Send"]');
  if (sendBtn) {
    var el = sendBtn;
    for (var i = 0; i < 8; i++) {
      if (el.tagName === 'BUTTON' || el.getAttribute('role') === 'button') {
        el.click(); return JSON.stringify({ok: true, method: 'button'});
      }
      if (!el.parentElement) break;
      el = el.parentElement;
    }
    sendBtn.click();
    return JSON.stringify({ok: true, method: 'icon direct'});
  }
  // Enter key
  var inp = document.querySelector('[contenteditable=true]');
  if (inp) {
    inp.dispatchEvent(new KeyboardEvent("keydown", {key:"Enter", keyCode:13, bubbles:true}));
    return JSON.stringify({ok: true, method: 'enter'});
  }
  return JSON.stringify({ok: false, reason: 'no send button'});
})()
""")
    try:
        sr = json.loads(send_result) if send_result else {}
    except Exception:
        sr = {}
    print(f"  send: {sr}", flush=True)

    time.sleep(2)
    if sr.get("ok"):
        print(f"\n  ✓ Image sent to SoFlo Studio via WhatsApp!")
    else:
        print(f"\n  ✗ Send failed")


if __name__ == "__main__":
    main()
