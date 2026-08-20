"""
FB DM v57 - verified USA LED targets with official Facebook links.
Exact page only; attempts follow/like before DM.
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
FB_PIPELINE = BASE / "pipeline/facebook/prospects.json"
TODAY = datetime.date.today().isoformat()
IMAGE_PATH = r"C:\Users\Administrator\Desktop\Recent-led-projects-poster-4k.jpg"

TARGETS = [
    {"no": 772, "facebook": "losangelesled", "company_en": "Los Angeles LED Rental", "city": "Los Angeles, CA",
     "message": "Hi! I'm from Shenzhen, China. I saw your LED screen and LED video wall rental work in Los Angeles. Sharing a recent Korea LED installation reference. For rental jobs, do clients ask more for indoor fine-pitch or outdoor high-brightness panels?"},
    {"no": 773, "facebook": "unitylogics", "company_en": "Unity Logics", "city": "Los Angeles, CA",
     "message": "Hi! I'm from Shenzhen, China. I saw your LED screen rental and custom LED video wall work in Los Angeles. Sharing a recent Korea LED installation reference. What LED wall size is requested most often by your event clients?"},
    {"no": 774, "facebook": "showproductionmiami", "company_en": "Show Production Miami", "city": "Miami, FL",
     "message": "Hi! I'm from Shenzhen, China. I saw your LED screen rental work in Miami. Sharing a recent Korea LED installation reference. For event LED screens, do clients ask more for indoor fine-pitch or outdoor high-brightness panels?"},
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


def set_files(tid, files, timeout=20):
    body = json.dumps({"selector": 'input[type="file"]', "files": files})
    return cdp(f"/setFiles?target={tid}", body=body, timeout=timeout)


def open_tab(url):
    return cdp(f"/new?url={url}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def load_pipeline():
    with open(FB_PIPELINE, encoding="utf-8") as f:
        return json.load(f)


def save_pipeline(data):
    with open(FB_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def already_sent(target):
    return any(
        (row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["facebook"].lower())
        and row.get("status") == "messaged"
        for row in load_pipeline()
    )


def mark_result(target, status, reason="", image_sent=False, followed=False):
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
    }
    if status == "messaged":
        payload.update({
            "status": "messaged",
            "touch_count": 1,
            "message_sent_date": TODAY,
            "message_channel": "facebook",
            "message_text": target["message"],
            "image_sent": image_sent,
            "attachment": IMAGE_PATH,
        })
    else:
        payload.update({"status": "prospect", "last_attempt_date": TODAY, "last_attempt_result": reason})
    for row in data:
        if row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["facebook"].lower():
            row.update(payload)
            break
    else:
        data.append(payload)
    save_pipeline(data)


def try_follow_or_like(tid):
    result = eval_js(tid, r"""
(function(){
  const buttons=Array.from(document.querySelectorAll("a,button,[role=button]"));
  const b=buttons.find(x=>{
    const t=(x.innerText||x.getAttribute("aria-label")||"").trim().toLowerCase();
    return t==="follow" || t==="like" || t==="关注" || t==="赞";
  });
  if(b){b.click(); return JSON.stringify({ok:true,text:(b.innerText||b.getAttribute("aria-label")||"").trim()});}
  return JSON.stringify({ok:false});
})()
""")
    try:
        return bool(json.loads(result or "{}").get("ok"))
    except Exception:
        return False


def try_send_image(tid):
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
    upload = set_files(tid, [IMAGE_PATH])
    print(f"  setFiles: {upload}", flush=True)
    time.sleep(3)
    sent = eval_js(tid, r"""
(function(){
  const buttons=Array.from(document.querySelectorAll("[role=button],button"));
  const b=buttons.find(x=>{
    const t=(x.getAttribute("aria-label")||x.innerText||"").trim().toLowerCase();
    return t==="send" || t==="发送" || t==="press enter to send";
  });
  if(b){b.click(); return JSON.stringify({ok:true});}
  return JSON.stringify({ok:false});
})()
""")
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
        print(f"  url: {cdp(f'/info?target={tid}').get('url','')[:80]}", flush=True)
        followed = try_follow_or_like(tid)
        print(f"  followed/liked: {followed}", flush=True)
        time.sleep(2)
        msg_click = eval_js(tid, r"""
(function(){
  const buttons=Array.from(document.querySelectorAll("a,button,[role=button]"));
  const b=buttons.find(x=>{
    const t=(x.innerText||x.getAttribute("aria-label")||"").trim().toLowerCase();
    return t==="message" || t==="send message" || t.includes("发消息") || t.includes("消息");
  });
  if(b){b.click(); return JSON.stringify({ok:true,text:(b.innerText||b.getAttribute("aria-label")||"").trim()});}
  return JSON.stringify({ok:false});
})()
""")
        try:
            mr = json.loads(msg_click or "{}")
        except Exception:
            mr = {}
        print(f"  message button: {mr}", flush=True)
        if not mr.get("ok"):
            return followed, False, False, "message_button_not_found"
        time.sleep(8)
        image_sent = try_send_image(tid)
        eval_js(tid, r"""
(function(){
  const boxes=Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  const box=boxes.find(e=>e.offsetParent!==null)||boxes[boxes.length-1];
  if(box){box.focus();box.click();}
})()
""")
        time.sleep(0.5)
        type_text(tid, target["message"])
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
            return followed, image_sent, False, "input_len_0"
        sent = eval_js(tid, r"""
(function(){
  const buttons=Array.from(document.querySelectorAll("[role=button],button"));
  const b=buttons.find(x=>{
    const t=(x.getAttribute("aria-label")||x.innerText||"").trim().toLowerCase();
    return t==="send" || t==="发送" || t==="press enter to send";
  });
  if(b){b.click(); return JSON.stringify({ok:true});}
  const boxes=Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  const box=boxes.find(e=>e.offsetParent!==null)||boxes[boxes.length-1];
  if(box){box.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",code:"Enter",keyCode:13,which:13,bubbles:true})); return JSON.stringify({ok:true,method:"enter"});}
  return JSON.stringify({ok:false});
})()
""")
        try:
            ok = bool(json.loads(sent or "{}").get("ok"))
        except Exception:
            ok = False
        return followed, image_sent, ok, "sent" if ok else "send_button_failed"
    finally:
        close_tab(tid)


def main():
    print(f"=== FB DM v57 | {len(TARGETS)} targets | {TODAY} ===", flush=True)
    sent = 0
    for target in TARGETS:
        print(f"\nfb:{target['facebook']} | no:{target['no']} | {target['company_en']}", flush=True)
        if already_sent(target):
            print("  SKIP: already sent", flush=True)
            continue
        followed, image_sent, text_sent, reason = send_fb(target)
        if text_sent:
            mark_result(target, "messaged", image_sent=image_sent, followed=followed)
            sent += 1
            print(f"  SENT | followed={followed} | image={image_sent}", flush=True)
        else:
            mark_result(target, "prospect", reason=reason, image_sent=image_sent, followed=followed)
            print(f"  FAILED | followed={followed} | image={image_sent} | reason={reason}", flush=True)
        time.sleep(7)
    print(f"\n=== Done: {sent}/{len(TARGETS)} FB DMs sent ===", flush=True)


if __name__ == "__main__":
    main()
