"""
FB image resend for verified USA LED targets whose text DM was sent without the case image.
Sends image only; does not send duplicate text.
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
PIPELINE = BASE / "pipeline/facebook/prospects.json"
TODAY = datetime.date.today().isoformat()
IMAGE_PATH = r"C:\Users\Administrator\Desktop\Recent-led-projects-poster-4k.jpg"


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
    body = json.dumps({"selector": 'input[type="file"]', "files": [IMAGE_PATH]})
    return cdp(f"/setFiles?target={tid}", body=body, timeout=timeout)


def open_tab(url):
    return cdp(f"/new?url={url}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def load_pipeline():
    return json.load(open(PIPELINE, encoding="utf-8"))


def save_pipeline(data):
    json.dump(data, open(PIPELINE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def targets():
    rows = []
    for row in load_pipeline():
        if row.get("country") != "USA":
            continue
        if row.get("status") != "messaged":
            continue
        if row.get("target_fit") != "verified_led_display":
            continue
        if row.get("do_not_contact"):
            continue
        if row.get("image_sent") is True:
            continue
        username = row.get("username") or row.get("facebook")
        if username:
            rows.append({
                "no": row.get("no"),
                "company_en": row.get("company_en", ""),
                "facebook": username,
            })
    return rows


def mark_image(target, ok, reason=""):
    data = load_pipeline()
    for row in data:
        if row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["facebook"].lower():
            row["image_sent"] = ok
            row["attachment"] = IMAGE_PATH
            if ok:
                row["image_sent_date"] = TODAY
                row.pop("image_last_attempt_result", None)
            else:
                row["image_last_attempt_date"] = TODAY
                row["image_last_attempt_result"] = reason
            break
    save_pipeline(data)


def click_match(tid, labels):
    labels_json = json.dumps([x.lower() for x in labels])
    return eval_js(tid, f"""
(function(){{
  const labels={labels_json};
  const buttons=Array.from(document.querySelectorAll("a,button,[role=button]"));
  const b=buttons.find(x=>{{
    const t=(x.innerText||x.getAttribute("aria-label")||"").trim().toLowerCase();
    return labels.includes(t) || labels.some(label => t.includes(label));
  }});
  if(b){{b.click(); return JSON.stringify({{ok:true,text:(b.innerText||b.getAttribute("aria-label")||"").trim()}});}}
  return JSON.stringify({{ok:false}});
}})()
""")


def send_image(target):
    tid = open_tab(f"https://www.facebook.com/{target['facebook']}")
    if not tid:
        return False, "open_tab_failed"
    try:
        time.sleep(8)
        print(f"  url: {cdp(f'/info?target={tid}').get('url','')[:100]}", flush=True)
        msg_click = click_match(tid, ["Message", "Send message", "发消息", "消息"])
        print(f"  message button: {msg_click}", flush=True)
        try:
            if not json.loads(msg_click or "{}").get("ok"):
                return False, "message_button_not_found"
        except Exception:
            return False, "message_button_not_found"
        time.sleep(8)
        eval_js(tid, r"""
(function(){
  const buttons=Array.from(document.querySelectorAll("[aria-label],[role=button],button"));
  const b=buttons.find(x=>{
    const a=(x.getAttribute("aria-label")||"").toLowerCase();
    return a.includes("photo")||a.includes("image")||a.includes("attach");
  });
  if(b)b.click();
})()
""")
        time.sleep(2)
        upload = set_files(tid)
        print(f"  setFiles: {upload}", flush=True)
        if not upload.get("success"):
            return False, "setFiles_failed"
        time.sleep(4)
        sent = click_match(tid, ["Send", "发送", "Press Enter to send"])
        try:
            ok = bool(json.loads(sent or "{}").get("ok"))
        except Exception:
            ok = False
        return ok, "sent" if ok else "send_button_not_found"
    finally:
        close_tab(tid)


def main():
    todo = targets()
    print(f"=== FB image resend | {len(todo)} targets | {TODAY} ===", flush=True)
    sent = 0
    for target in todo:
        print(f"\nfb:{target['facebook']} | no:{target['no']} | {target['company_en']}", flush=True)
        ok, reason = send_image(target)
        mark_image(target, ok, reason)
        if ok:
            sent += 1
            print("  IMAGE SENT", flush=True)
        else:
            print(f"  FAILED: {reason}", flush=True)
        time.sleep(6)
    print(f"\n=== Done: {sent}/{len(todo)} images sent ===", flush=True)


if __name__ == "__main__":
    main()
