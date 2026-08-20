"""
IG image resend for verified USA LED targets whose text DM was sent without the case image.

Uses the correct DM file input selector: input[type="file"][multiple].
Does not use search or direct/new; opens exact official profiles only.
"""
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
PIPELINE = BASE / "pipeline/instagram/prospects.json"
TODAY = datetime.date.today().isoformat()
IMAGE_PATH = r"C:\Users\Administrator\Desktop\Recent-led-projects-poster-4k.jpg"

TARGETS = [
    # v56 text-sent IG targets missing image
    {"no": 759, "username": "edenusa.la", "company_en": "Eden USA"},
    {"no": 760, "username": "euroledwall", "company_en": "EuroLedwall USA"},
    {"no": 761, "username": "fidelisatx", "company_en": "Fidelis Sound & Lighting"},
    {"no": 762, "username": "1avamerica", "company_en": "AV America Florida"},
    {"no": 763, "username": "digitalartvideo", "company_en": "Digital Art Video"},
    {"no": 764, "username": "oneworldrental", "company_en": "One World Rental USA"},
    # v57 text-sent IG targets missing image
    {"no": 772, "username": "losangelesled", "company_en": "Los Angeles LED Rental"},
    {"no": 774, "username": "showproductionmiami", "company_en": "Show Production Miami"},
]


def cdp(path, body=None, timeout=15):
    args = ["curl", "-s", "--max-time", str(timeout)]
    if body is None:
        args.append(f"{CDP}{path}")
    else:
        args += ["-X", "POST", f"{CDP}{path}", "-d", body]
    r = subprocess.run(args, capture_output=True, timeout=timeout + 5)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def eval_js(tid, js, timeout=12):
    return cdp(f"/eval?target={tid}", js, timeout=timeout).get("value", "")


def set_files(tid, timeout=20):
    body = json.dumps({"selector": 'input[type="file"][multiple]', "files": [IMAGE_PATH]})
    return cdp(f"/setFiles?target={tid}", body=body, timeout=timeout)


def open_tab(url):
    return cdp(f"/new?url={url}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def load_pipeline():
    return json.load(open(PIPELINE, encoding="utf-8"))


def save_pipeline(data):
    json.dump(data, open(PIPELINE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def mark_image(target, ok, reason=""):
    data = load_pipeline()
    for row in data:
        if row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["username"].lower():
            if ok:
                row["image_sent"] = True
                row["image_sent_date"] = TODAY
                row["attachment"] = IMAGE_PATH
                row.pop("image_last_attempt_result", None)
            else:
                row["image_sent"] = False
                row["image_last_attempt_date"] = TODAY
                row["image_last_attempt_result"] = reason
            break
    save_pipeline(data)


def image_already_sent(target):
    for row in load_pipeline():
        if row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["username"].lower():
            return row.get("image_sent") is True
    return False


def open_dm(tid, username):
    click = eval_js(tid, r"""
(function(){
  const buttons=Array.from(document.querySelectorAll("[role=button],button,a"));
  const b=buttons.find(x=>{
    const t=(x.innerText||x.getAttribute("aria-label")||"").trim();
    return t==="Message" || t==="发消息" || t==="消息";
  });
  if(b){b.click(); return JSON.stringify({ok:true,text:(b.innerText||b.getAttribute("aria-label")||"").trim()});}
  return JSON.stringify({ok:false});
})()
""")
    print(f"  message button: {click}", flush=True)
    try:
        return bool(json.loads(click or "{}").get("ok"))
    except Exception:
        return False


def click_image_send(tid):
    result = eval_js(tid, r"""
(function(){
  const buttons=Array.from(document.querySelectorAll("[role=button],button,[aria-label]"));
  const send=buttons.find(x=>{
    const a=(x.getAttribute("aria-label")||"").trim();
    const t=(x.innerText||"").trim();
    return a==="发送" || a==="Send" || t==="发送" || t==="Send";
  });
  if(send){send.click(); return JSON.stringify({ok:true, label:send.getAttribute("aria-label")||send.innerText||""});}
  return JSON.stringify({ok:false, buttons:buttons.map((x,i)=>({i,aria:x.getAttribute("aria-label")||"",text:(x.innerText||"").trim()})).filter(x=>x.aria||x.text).slice(-30)});
})()
""", timeout=20)
    print(f"  send click: {result}", flush=True)
    try:
        return bool(json.loads(result or "{}").get("ok"))
    except Exception:
        return False


def send_image(target):
    tid = open_tab(f"https://www.instagram.com/{target['username']}/")
    if not tid:
        return False, "open_tab_failed"
    try:
        time.sleep(10)
        url = cdp(f"/info?target={tid}").get("url", "")
        print(f"  url: {url[:80]}", flush=True)
        if f"/{target['username'].lower()}" not in url.lower():
            return False, "profile_url_mismatch"
        if not open_dm(tid, target["username"]):
            return False, "message_button_not_found"
        time.sleep(8)
        inputs = eval_js(tid, r"""
(function(){
  return JSON.stringify(Array.from(document.querySelectorAll('input[type=file]')).map((i,idx)=>({idx,accept:i.accept,multiple:i.multiple})));
})()
""")
        print(f"  file inputs: {inputs}", flush=True)
        upload = set_files(tid)
        print(f"  setFiles multiple: {upload}", flush=True)
        if not upload.get("success"):
            return False, "setFiles_failed"
        time.sleep(5)
        preview = eval_js(tid, r"""
(function(){
  const remove = Array.from(document.querySelectorAll('[aria-label]')).some(x => (x.getAttribute('aria-label')||'').includes('移除附件') || (x.getAttribute('aria-label')||'').toLowerCase().includes('remove attachment'));
  const blobs = document.querySelectorAll('img[src^="blob:"]').length;
  return JSON.stringify({remove, blobs, url:location.href});
})()
""")
        print(f"  preview: {preview}", flush=True)
        ok = click_image_send(tid)
        time.sleep(4)
        return ok, "sent" if ok else "send_button_not_found"
    finally:
        close_tab(tid)


def main():
    print(f"=== IG image resend | {len(TARGETS)} targets | {TODAY} ===", flush=True)
    sent = 0
    for target in TARGETS:
        print(f"\n@{target['username']} | no:{target['no']} | {target['company_en']}", flush=True)
        if image_already_sent(target):
            print("  SKIP: image already marked sent", flush=True)
            continue
        ok, reason = send_image(target)
        mark_image(target, ok, reason)
        if ok:
            sent += 1
            print("  IMAGE SENT", flush=True)
        else:
            print(f"  FAILED: {reason}", flush=True)
        time.sleep(7)
    print(f"\n=== Done: {sent}/{len(TARGETS)} images sent ===", flush=True)


if __name__ == "__main__":
    main()
