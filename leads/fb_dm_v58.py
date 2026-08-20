"""
FB DM v58 - verified USA LED targets with official Facebook pages.
Follows/likes first, attempts image attachment, then sends casual DM text.
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

TARGETS = [
    {
        "no": 776,
        "facebook": "104590035815139",
        "company_en": "EAV Pro",
        "city": "Delaware / Miami event work",
        "message": (
            "Hi! I'm from Shenzhen, China. I saw your LED video wall and installation work. "
            "Sharing a recent Korea LED installation reference. For event and install projects, what panel size or pixel pitch do clients request most often?"
        ),
    },
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


def type_text(tid, text, timeout=30):
    args = ["curl", "-s", "--max-time", str(timeout), "-X", "POST",
            f"{CDP}/type?target={tid}", "--data-binary", text.encode("utf-8")]
    r = subprocess.run(args, capture_output=True, timeout=timeout + 5)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


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


def already_sent(target):
    return any(
        (row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["facebook"].lower())
        and row.get("status") == "messaged"
        for row in load_pipeline()
    )


def mark_result(target, text_sent, image_sent, followed, reason=""):
    data = load_pipeline()
    payload = {
        "no": target["no"],
        "country": "USA",
        "platform": "facebook",
        "username": target["facebook"],
        "facebook": target["facebook"],
        "company_en": target["company_en"],
        "city": target["city"],
        "target_fit": "verified_led_display",
        "do_not_contact": False,
        "followed": followed,
        "image_sent": image_sent,
        "attachment": IMAGE_PATH,
    }
    if text_sent:
        payload.update({
            "status": "messaged",
            "touch_count": 1,
            "message_sent_date": TODAY,
            "message_channel": "facebook",
            "message_text": target["message"],
        })
        if image_sent:
            payload["image_sent_date"] = TODAY
    else:
        payload.update({"status": "prospect", "last_attempt_date": TODAY, "last_attempt_result": reason})
    for row in data:
        if row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["facebook"].lower():
            row.update(payload)
            break
    else:
        data.append(payload)
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


def send_image(tid):
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
        return False
    time.sleep(4)
    sent = click_match(tid, ["Send", "发送", "Press Enter to send"])
    try:
        return bool(json.loads(sent or "{}").get("ok"))
    except Exception:
        return False


def send_text(tid, message):
    eval_js(tid, r"""
(function(){
  const boxes=Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  const box=boxes.find(e=>e.offsetParent!==null)||boxes[boxes.length-1];
  if(box){box.focus();box.click();}
})()
""")
    time.sleep(0.5)
    type_text(tid, message)
    time.sleep(1)
    typed = eval_js(tid, r"""
(function(){
  const boxes=Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  const box=boxes.find(e=>e.offsetParent!==null)||boxes[boxes.length-1];
  return box ? String(box.innerText.trim().length) : "0";
})()
""")
    print(f"  input len: {typed}", flush=True)
    if int(typed or "0") < 10:
        return False
    sent = click_match(tid, ["Send", "发送", "Press Enter to send"])
    try:
        return bool(json.loads(sent or "{}").get("ok"))
    except Exception:
        return False


def send_fb(target):
    tid = open_tab(f"https://www.facebook.com/{target['facebook']}")
    if not tid:
        return False, False, False, "open_tab_failed"
    try:
        time.sleep(8)
        print(f"  url: {cdp(f'/info?target={tid}').get('url','')[:100]}", flush=True)
        followed = False
        try:
            followed = bool(json.loads(click_match(tid, ["Follow", "Like", "关注", "赞"]) or "{}").get("ok"))
        except Exception:
            followed = False
        print(f"  followed/liked: {followed}", flush=True)
        time.sleep(2)
        msg_click = click_match(tid, ["Message", "Send message", "发消息", "消息"])
        print(f"  message button: {msg_click}", flush=True)
        try:
            if not json.loads(msg_click or "{}").get("ok"):
                return followed, False, False, "message_button_not_found"
        except Exception:
            return followed, False, False, "message_button_not_found"
        time.sleep(8)
        image_sent = send_image(tid)
        time.sleep(3)
        text_sent = send_text(tid, target["message"])
        return followed, image_sent, text_sent, "sent" if text_sent else "text_not_sent"
    finally:
        close_tab(tid)


def main():
    print(f"=== FB DM v58 | {len(TARGETS)} targets | {TODAY} ===", flush=True)
    sent = 0
    for target in TARGETS:
        print(f"\nfb:{target['facebook']} | no:{target['no']} | {target['company_en']}", flush=True)
        if already_sent(target):
            print("  SKIP: already sent", flush=True)
            continue
        followed, image_sent, text_sent, reason = send_fb(target)
        mark_result(target, text_sent, image_sent, followed, reason)
        if text_sent:
            sent += 1
            print(f"  SENT | followed={followed} | image={image_sent}", flush=True)
        else:
            print(f"  FAILED | followed={followed} | image={image_sent} | reason={reason}", flush=True)
    print(f"\n=== Done: {sent}/{len(TARGETS)} FB DMs sent ===", flush=True)


if __name__ == "__main__":
    main()
