"""
Apply WhatsApp Business contact names from pipeline/whatsapp/prospects.json.

This edits the actual WhatsApp Web/Business contact name where the web UI exposes
the add/edit contact form. It does not send messages.
"""
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websocket

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent
PIPELINE = BASE / "pipeline/whatsapp/prospects.json"
LOG = BASE / "wa_contact_note_apply_log.json"


def load_targets(limit=None, only_no=None, retry_failed=False):
    data = json.load(open(PIPELINE, encoding="utf-8"))
    rows = []
    for row in data:
        if row.get("status") != "messaged" or row.get("message_channel") != "whatsapp":
            continue
        if row.get("wa_contact_note_applied") is True:
            continue
        if row.get("wa_contact_note_apply_date") and not retry_failed and not only_no:
            continue
        if only_no and int(row.get("no", -1)) != only_no:
            continue
        note = row.get("contact_note") or row.get("whatsapp_contact_note")
        phone = row.get("phone") or row.get("username")
        if not note or not phone:
            continue
        rows.append({
            "no": row.get("no"),
            "company_en": row.get("company_en"),
            "phone": phone,
            "note": note,
        })
    return rows[:limit] if limit else rows


def update_pipeline_apply_status(no, result):
    data = json.load(open(PIPELINE, encoding="utf-8"))
    for row in data:
        if row.get("no") == no and row.get("status") == "messaged" and row.get("message_channel") == "whatsapp":
            row["wa_contact_note_apply_date"] = time.strftime("%Y-%m-%d")
            row["wa_contact_note_apply_result"] = "applied" if result.get("ok") else result.get("reason", "failed")
            row["wa_contact_note_applied"] = bool(result.get("ok"))
            break
    json.dump(data, open(PIPELINE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def digits(value):
    return "".join(ch for ch in str(value) if ch.isdigit())


class Cdp:
    def __init__(self):
        self.ws = None
        self.msg_id = 0
        self.connect()

    def connect(self):
        targets = json.load(urllib.request.urlopen("http://127.0.0.1:9222/json/list"))
        wa = next((t for t in targets if "web.whatsapp.com" in t.get("url", "") and t.get("type") == "page"), None)
        if not wa:
            raise RuntimeError("No WhatsApp Web page found on Chrome 9222")
        self.ws = websocket.create_connection(wa["webSocketDebuggerUrl"], timeout=15, suppress_origin=True)
        self.call("Runtime.enable")
        self.call("Page.enable")

    def reconnect(self, delay=5):
        try:
            self.ws.close()
        except Exception:
            pass
        time.sleep(delay)
        self.connect()

    def call(self, method, params=None):
        self.msg_id += 1
        self.ws.send(json.dumps({"id": self.msg_id, "method": method, "params": params or {}}, ensure_ascii=False))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.msg_id:
                return msg

    def eval(self, expression, timeout=0):
        if timeout:
            time.sleep(timeout)
        result = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        return result.get("result", {}).get("result", {}).get("value")

    def click_at(self, x, y):
        self.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        self.call("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x,
            "y": y,
            "button": "left",
            "clickCount": 1,
        })
        self.call("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x,
            "y": y,
            "button": "left",
            "clickCount": 1,
        })

    def close(self):
        self.ws.close()


def wait_until(cdp, predicate_expr, timeout=45, interval=1):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = cdp.eval(predicate_expr)
        if last:
            return last
        time.sleep(interval)
    return last


def js_string(value):
    return json.dumps(value, ensure_ascii=False)


def set_clipboard(text):
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $args[0]", text],
        check=True,
        capture_output=True,
        timeout=10,
    )


def apply_one(cdp, target):
    phone_digits = digits(target["phone"])
    note = target["note"]
    cdp.call("Page.navigate", {"url": f"https://web.whatsapp.com/send?phone={phone_digits}"})
    cdp.reconnect(delay=6)
    loaded = wait_until(
        cdp,
        """(() => {
          const t=document.body.innerText;
          if (
            t.includes('\\u8f93\\u5165\\u6d88\\u606f') ||
            t.includes('\\u53d1\\u9001\\u7684\\u6d88\\u606f') ||
            t.includes('\\u7535\\u8bdd\\u53f7\\u7801\\u901a\\u8fc7\\u7f51\\u5740\\u5206\\u4eab') ||
            t.includes('Phone number shared')
          ) return t.slice(0,1200);
          return (t.includes('输入消息') || t.includes('发送的消息') || t.includes('电话号码通过网址分享') || t.includes('Phone number shared')) ? t.slice(0,1200) : '';
        })()""",
        timeout=60,
    )
    if not loaded:
        return {"ok": False, "reason": "chat_not_loaded"}

    # Open contact/profile details by clicking the header title for this chat.
    click_header = cdp.eval(f"""(() => {{
      const wanted={js_string(phone_digits)};
      const norm=s=>(s||'').replace(/\\D/g,'');
      const els=Array.from(document.querySelectorAll('[role=button],button,[aria-label]'));
      const hit=els.find(e=>norm(e.innerText).endsWith(wanted.slice(-10)) || norm(e.innerText).includes(wanted.slice(-10)));
      if(hit) {{ hit.click(); return {{ok:true, text:(hit.innerText||hit.getAttribute('aria-label')||'').slice(0,120)}}; }}
      const title=els.find(e=>(e.getAttribute('title')||'').includes('\\u4e2a\\u4eba\\u4e3b\\u9875\\u8be6\\u60c5'));
      if(title) {{ title.click(); return {{ok:true, text:'profile-title'}}; }}
      return {{ok:false, body:document.body.innerText.slice(0,1000)}};
    }})()""")
    if not click_header or not click_header.get("ok"):
        return {"ok": False, "reason": "header_click_failed", "detail": click_header}
    time.sleep(2)

    already_visible = cdp.eval(f"""(() => document.body.innerText.includes({js_string(note)}))()""")
    if already_visible:
        return {"ok": True, "reason": "already_visible"}

    # If unsaved, click Add. If already saved, try Edit.
    mode = cdp.eval("""(() => {
      const items=Array.from(document.querySelectorAll('button,[role=button],[aria-label]')).map((e,i)=>{
        const r=e.getBoundingClientRect();
        return {i, text:((e.innerText||'')+' '+(e.getAttribute('aria-label')||'')).trim(), rect:[r.left,r.top,r.width,r.height]};
      });
      const add=items.find(x=>x.text.includes('\\u6dfb\\u52a0') && x.rect[0] > 900);
      if(add) return {mode:'add', x:add.rect[0]+add.rect[2]/2, y:add.rect[1]+add.rect[3]/2};
      const edit=items.find(x=>x.text.includes('\\u7f16\\u8f91') && x.rect[0] > 900);
      if(edit) return {mode:'edit', x:edit.rect[0]+edit.rect[2]/2, y:edit.rect[1]+edit.rect[3]/2};
      return {mode:'no_add_or_edit'};
    })()""")
    if not mode or mode.get("mode") == "no_add_or_edit":
        return {"ok": False, "reason": "no_add_or_edit"}
    cdp.click_at(mode["x"], mode["y"])
    mode = mode["mode"]
    time.sleep(2)

    form_ready = wait_until(
        cdp,
        """(() => Array.from(document.querySelectorAll('[role="textbox"],[contenteditable="true"]')).some(e=>(e.getAttribute('aria-label')||'')==='\\u540d\\u5b57'))()""",
        timeout=15,
        interval=0.5,
    )
    if not form_ready:
        return {"ok": False, "reason": "contact_form_not_open", "mode": mode}

    existing_name = cdp.eval("""(() => {
      const first=Array.from(document.querySelectorAll('[role="textbox"],[contenteditable="true"]')).find(e=>(e.getAttribute('aria-label')||'')==='\\u540d\\u5b57');
      return first ? first.innerText.trim() : '';
    })()""")
    # Fill first name with the full note through CDP keyboard/input events.
    # WhatsApp's contact form is React-backed and direct CDP text insertion turns
    # Chinese into ?? on this machine. Clipboard paste preserves Unicode.
    focus = cdp.eval(f"""(() => {{
      const first=Array.from(document.querySelectorAll('[role="textbox"],[contenteditable="true"]')).find(e=>(e.getAttribute('aria-label')||'')==='\\u540d\\u5b57');
      if(!first) return {{ok:false}};
      first.focus();
      first.click();
      const range=document.createRange();
      range.selectNodeContents(first);
      const sel=window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      return {{ok:true, before:first.innerText}};
    }})()""")
    if not focus or not focus.get("ok"):
        return {"ok": False, "reason": "first_name_focus_failed"}
    set_clipboard(note)
    cdp.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Control", "code": "ControlLeft", "windowsVirtualKeyCode": 17, "modifiers": 2})
    cdp.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "v", "code": "KeyV", "windowsVirtualKeyCode": 86, "modifiers": 2})
    cdp.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "v", "code": "KeyV", "windowsVirtualKeyCode": 86, "modifiers": 2})
    cdp.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Control", "code": "ControlLeft", "windowsVirtualKeyCode": 17})
    time.sleep(0.5)

    check = cdp.eval("""(() => {
      const first=Array.from(document.querySelectorAll('[role="textbox"],[contenteditable="true"]')).find(e=>(e.getAttribute('aria-label')||'')==='\\u540d\\u5b57');
      const save=document.querySelector('[aria-label="\\u4fdd\\u5b58\\u8054\\u7cfb\\u4eba"]') ||
        Array.from(document.querySelectorAll('button,[role=button]')).find(e=>(e.innerText||'').includes('\\u4fdd\\u5b58'));
      return {first:first&&first.innerText, save:!!save};
    })()""")
    if not check or check.get("first") != note:
        return {"ok": False, "reason": "name_not_set", "check": check}

    saved = cdp.eval("""(() => {
      const save=document.querySelector('[aria-label="\\u4fdd\\u5b58\\u8054\\u7cfb\\u4eba"]') ||
        Array.from(document.querySelectorAll('button,[role=button]')).find(e=>(e.innerText||'').includes('\\u4fdd\\u5b58'));
      if(!save) return false;
      save.click();
      return true;
    })()""")
    if not saved:
        return {"ok": False, "reason": "save_button_missing"}
    time.sleep(4)

    visible = cdp.eval(f"""(() => document.body.innerText.includes({js_string(note)}))()""")
    return {"ok": bool(visible), "reason": None if visible else "saved_but_not_visible_yet", "mode": mode}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--no", type=int)
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()

    targets = load_targets(limit=args.limit, only_no=args.no, retry_failed=args.retry_failed)
    cdp = Cdp()
    log = []
    try:
        for idx, target in enumerate(targets, 1):
            print(f"[{idx}/{len(targets)}] no:{target['no']} {target['phone']} -> {target['note']}", flush=True)
            try:
                result = apply_one(cdp, target)
            except Exception as exc:
                result = {"ok": False, "reason": type(exc).__name__, "detail": str(exc)}
            print(" ", result, flush=True)
            log.append({**target, **result, "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
            json.dump(log, open(LOG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            update_pipeline_apply_status(target["no"], result)
    finally:
        cdp.close()


if __name__ == "__main__":
    main()
