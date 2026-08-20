"""
Probe Instagram image upload/send controls for a known verified thread.
Does not update pipeline. Use for selector debugging.
"""
import json
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
IMAGE_PATH = r"C:\Users\Administrator\Desktop\Recent-led-projects-poster-4k.jpg"
USERNAME = "showproductionmiami"


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


def set_files(tid):
    body = json.dumps({"selector": 'input[type="file"][multiple]', "files": [IMAGE_PATH]})
    return cdp(f"/setFiles?target={tid}", body=body, timeout=20)


def main():
    tid = cdp(f"/new?url=https://www.instagram.com/{USERNAME}/", timeout=35).get("targetId")
    print("tid", tid)
    time.sleep(10)
    print("info", cdp(f"/info?target={tid}"))
    print("click msg", eval_js(tid, r"""
(function(){
  const buttons=Array.from(document.querySelectorAll("[role=button],button,a"));
  const b=buttons.find(x=>{
    const t=(x.innerText||x.getAttribute("aria-label")||"").trim();
    return t==="Message" || t==="发消息" || t==="消息";
  });
  if(b){b.click(); return JSON.stringify({ok:true,text:(b.innerText||b.getAttribute("aria-label")||"").trim()});}
  return JSON.stringify({ok:false});
})()
"""))
    time.sleep(8)
    print("inputs before", eval_js(tid, r"""
(function(){
  return JSON.stringify(Array.from(document.querySelectorAll('input[type=file]')).map((i,idx)=>({idx,accept:i.accept,multiple:i.multiple,display:getComputedStyle(i).display,html:i.outerHTML.slice(0,200)})));
})()
"""))
    print("setFiles", set_files(tid))
    time.sleep(5)
    print("state after upload", eval_js(tid, r"""
(function(){
  const buttons=Array.from(document.querySelectorAll("[role=button],button"));
  const btns=buttons.map((b,idx)=>({
    idx,
    text:(b.innerText||'').trim(),
    aria:b.getAttribute('aria-label')||'',
    title:b.getAttribute('title')||'',
    disabled:b.getAttribute('aria-disabled')||b.disabled||false,
    html:b.outerHTML.slice(0,160)
  })).filter(x=>x.text||x.aria||x.title).slice(-80);
  const imgs=Array.from(document.querySelectorAll('img')).map((img,idx)=>({idx,src:(img.src||'').slice(0,80),alt:img.alt||'',w:img.naturalWidth,h:img.naturalHeight})).slice(-20);
  const files=Array.from(document.querySelectorAll('input[type=file]')).map((i,idx)=>({idx,files:i.files?i.files.length:null,accept:i.accept}));
  return JSON.stringify({url:location.href,buttons:btns,imgs,files,body:document.body.innerText.slice(-1000)});
})()
""", timeout=20))
    # Leave tab open for manual inspection if needed.


if __name__ == "__main__":
    main()
