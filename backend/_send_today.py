import datetime as dt, json, sys
sys.path.insert(0, ".")
from app.db import connect
from app import sequence_send, settings
from app.api import send as send_api

ids = json.load(open("_batch_ids.json"))
conn = connect("outreach.db")
now = dt.datetime.now()
print(f"[{now:%H:%M:%S}] 开始发送 {len(ids)} 封英语序列跟进", flush=True)
res = sequence_send.send_due(
    conn, ids,
    sender=send_api.pick_sender(conn),
    image_default=send_api.DEFAULT_ATTACHMENT,
    email_delay=(16, 28),
    on_progress=lambda i, total: print(f"  {i}/{total}", flush=True),
)
note = (f"{now:%m-%d %H:%M} 手动补发（英语序列）：成功 {res['sent']}，失败 {res['failed']}"
        + (f"，额度外延后 {res['deferred']}" if res.get("deferred") else ""))
settings.set_value(conn, "autosend_last_result", note)
print("\n结果：", json.dumps(res, ensure_ascii=False))
for e in res.get("errors", [])[:5]:
    print("  错误：", e)
conn.close()
