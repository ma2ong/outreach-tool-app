import { useEffect, useState } from "react";
import { fetchJob } from "../api";
import {
  buildSocialQueue, dropSocialQueueItem, editSocialQueueItem, fetchSocialAutonomy,
  fetchSocialQueue, sendSocialQueue, setSocialMode,
  type QueueBuildResult, type SocialAutonomy, type SocialMode, type SocialQueueItem,
} from "../socialQueueApi";

const CH_NAME: Record<string, string> = {
  whatsapp: "WhatsApp", instagram: "Instagram", facebook: "Facebook",
};

export function SocialQueuePanel() {
  const [items, setItems] = useState<SocialQueueItem[]>([]);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [held, setHeld] = useState<QueueBuildResult["holds"]>([]);
  const [job, setJob] = useState<{ id: string; done: number; total: number } | null>(null);
  const [autonomy, setAutonomy] = useState<SocialAutonomy | null>(null);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [confirmText, setConfirmText] = useState("");

  function reload() {
    fetchSocialQueue()
      .then((q) => {
        const ready = q.items.filter((i) => i.status === "ready");
        setItems(q.items);
        setPicked(new Set(ready.map((i) => i.id)));
      })
      .catch((e) => setMsg(String(e)));
  }
  function reloadAutonomy() {
    fetchSocialAutonomy().then(setAutonomy).catch((e) => setMsg(String(e)));
  }
  useEffect(() => { reload(); reloadAutonomy(); }, []);

  async function changeMode(channel: string, mode: SocialMode) {
    // 升到 auto 要照抄渠道名：这不是"确定吗"能承担的决定。
    if (mode === "auto") { setConfirming(channel); setConfirmText(""); return; }
    try { await setSocialMode(channel, mode); reloadAutonomy(); }
    catch (e) { setMsg(String(e)); }
  }

  async function confirmAuto(channel: string) {
    try {
      await setSocialMode(channel, "auto", confirmText.trim());
      setConfirming(null); setConfirmText(""); reloadAutonomy();
      setMsg(`${CH_NAME[channel]} 已切到全自动：每天在随机时刻自己发，随时可以关。`);
    } catch (e) { setMsg(String(e)); }
  }

  // 发送在后台逐条跑（每条间隔 1–5 分钟），所以这里轮询进度而不是干等。
  useEffect(() => {
    if (!job) return;
    const timer = setInterval(async () => {
      try {
        const j = await fetchJob(job.id);
        setJob({ id: job.id, done: j.done, total: j.total });
        if (j.status !== "running") {
          clearInterval(timer);
          setJob(null);
          setBusy(false);
          const r: any = j.result ?? {};
          setMsg(j.status === "error"
            ? `发送出错：${r.error ?? "未知原因"}`
            : `已发出 ${r.sent ?? 0} 条，失败 ${r.failed ?? 0}${r.deferred ? `，超出今日渠道上限延后 ${r.deferred}` : ""}`);
          reload();
        }
      } catch { /* 下一轮再试 */ }
    }, 3000);
    return () => clearInterval(timer);
  }, [job]);

  async function build() {
    setBusy(true); setMsg("");
    try {
      const r = await buildSocialQueue();
      setHeld(r.holds ?? []);
      setMsg(`今天备好 ${r.queued} 条（${Object.entries(r.per_channel)
        .filter(([, n]) => n > 0).map(([c, n]) => `${CH_NAME[c]} ${n}`).join(" · ")}）`
        + (r.held ? `，另有 ${r.held} 家没进队列` : ""));
      reload();
    } catch (e) { setMsg("生成失败：" + String(e)); }
    finally { setBusy(false); }
  }

  async function saveEdit(id: number) {
    if (!draft.trim()) { setMsg("正文不能为空"); return; }
    try {
      await editSocialQueueItem(id, draft.trim());
      setEditing(null); setDraft(""); reload();
    } catch (e) { setMsg("保存失败：" + String(e)); }
  }

  async function drop(id: number) {
    try { await dropSocialQueueItem(id); reload(); }
    catch (e) { setMsg("删除失败：" + String(e)); }
  }

  async function send() {
    const ids = items.filter((i) => i.status === "ready" && picked.has(i.id)).map((i) => i.id);
    if (!ids.length) { setMsg("先勾选要发的条目"); return; }
    setBusy(true); setMsg("");
    try {
      const r = await sendSocialQueue(ids);
      setJob({ id: r.job_id, done: 0, total: r.will_send });
      setMsg(`开始发送 ${r.will_send} 条，每条间隔 1–5 分钟，浏览器会自动操作，别关窗口…`);
    } catch (e) { setMsg("发送失败：" + String(e)); setBusy(false); }
  }

  const ready = items.filter((i) => i.status === "ready");
  const sent = items.filter((i) => i.status === "sent");

  return (
    <div className="card">
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
        <h3 style={{ margin: 0, fontSize: 15 }}>今日社媒私信</h3>
        <span className="muted">Agent 备好，你确认后再发</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          <button className="btn btn-sm" onClick={build} disabled={busy}>
            {busy && !job ? "生成中…" : ready.length ? "重新生成" : "生成今日队列"}
          </button>
          <button className="btn btn-sm btn-primary" onClick={send} disabled={busy || !ready.length}>
            {job ? `发送中 ${job.done}/${job.total}` : `发出所选 ${picked.size} 条`}
          </button>
        </div>
      </div>

      <div className="muted" style={{ marginBottom: 10 }}>
        每天每个渠道 8–15 条（周末减半），一家公司一天只出现在一个渠道，正文逐条不同。
        发送时每条间隔 1–5 分钟，走的是「渠道连接」里已登录的账号。
      </div>

      {autonomy && (
        <div style={{ marginBottom: 12, padding: 10, border: "1px solid var(--line)", borderRadius: 6 }}>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
            <b style={{ fontSize: 13 }}>谁按发送</b>
            {Object.keys(CH_NAME).map((ch) => (
              <span key={ch} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                {CH_NAME[ch]}
                <select className="input" style={{ width: 92, padding: "2px 4px" }}
                  value={autonomy.modes[ch] ?? "manual"}
                  onChange={(e) => changeMode(ch, e.target.value as SocialMode)}>
                  <option value="off">不发</option>
                  <option value="manual">我来发</option>
                  <option value="auto">全自动</option>
                </select>
              </span>
            ))}
            <span className="muted">今天自动发送时刻 {autonomy.send_at}（每天不同）</span>
          </div>
          {/* 不写出来的话，「全自动」会被读成"所有人都自动发"，而韩国那批不是。docs/63 */}
          {Object.values(autonomy.modes).some((m) => m === "auto") && (
            <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
              韩国客户不走全自动：他们多数是做了几年的老客户，自动开场白读起来像群发。
              他们照常出现在下面的列表里，等你按发送。
            </div>
          )}
          {confirming && (
            <div style={{ marginTop: 8 }}>
              <div style={{ marginBottom: 4 }}>
                切到全自动后，{CH_NAME[confirming]} 会在每天随机时刻自己发出上面这些私信。
                <b>这个账号一旦被封是拿不回来的</b>
                {confirming === "whatsapp" && "，而这个号绑着你的微信和全部客户联系方式"}。
                确认的话，照抄一遍渠道名：
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <input className="input" autoFocus style={{ width: 160 }} value={confirmText}
                  placeholder={confirming}
                  onChange={(e) => setConfirmText(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") confirmAuto(confirming); }} />
                <button className="btn btn-sm btn-primary" onClick={() => confirmAuto(confirming)}>
                  打开全自动
                </button>
                <button className="btn btn-sm" onClick={() => { setConfirming(null); reloadAutonomy(); }}>
                  算了
                </button>
              </div>
            </div>
          )}
          {autonomy.last_run && (
            <div className="muted" style={{ marginTop: 6 }}>
              今天自动发过：{Object.entries(autonomy.last_run.channels)
                .map(([c, n]) => `${CH_NAME[c]} ${n} 条`).join(" · ")}
              {autonomy.last_run.failed ? `，失败 ${autonomy.last_run.failed}` : ""}
            </div>
          )}
        </div>
      )}

      {msg && <div style={{ marginBottom: 10 }}>{msg}</div>}

      {ready.length === 0 && sent.length === 0 ? (
        <div className="muted">今天还没有队列。点「生成今日队列」，Agent 会挑客户、定渠道、写好每一条。</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th style={{ width: 30 }}></th>
              <th style={{ width: 150 }}>客户</th>
              <th style={{ width: 90 }}>渠道</th>
              <th>要发的话</th>
              <th style={{ width: 120 }}></th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.id} style={it.status === "sent" ? { opacity: 0.5 } : undefined}>
                <td>
                  {it.status === "ready" && (
                    <input type="checkbox" checked={picked.has(it.id)}
                      onChange={() => setPicked((old) => {
                        const next = new Set(old);
                        next.has(it.id) ? next.delete(it.id) : next.add(it.id);
                        return next;
                      })} />
                  )}
                </td>
                <td>
                  {it.company_en}
                  <div className="ts">{it.country ?? ""}{it.website ? ` · ${it.website}` : ""}</div>
                </td>
                <td>
                  <span className="badge badge-messaged"><i />{CH_NAME[it.channel]}</span>
                  <div className="ts">{it.target}</div>
                </td>
                <td>
                  {editing === it.id ? (
                    <textarea className="input" autoFocus rows={3} style={{ width: "100%" }}
                      value={draft} onChange={(e) => setDraft(e.target.value)} />
                  ) : (
                    <>
                      {it.body}
                      {it.edited === 1 && <span className="ts"> · 我改过</span>}
                    </>
                  )}
                </td>
                <td>
                  {it.status === "sent" ? <span className="muted">已发出</span> : editing === it.id ? (
                    <>
                      <button className="btn btn-sm btn-primary" style={{ marginRight: 6 }}
                        onClick={() => saveEdit(it.id)}>保存</button>
                      <button className="btn btn-sm" onClick={() => setEditing(null)}>取消</button>
                    </>
                  ) : (
                    <>
                      <button className="btn btn-sm" style={{ marginRight: 6 }}
                        onClick={() => { setEditing(it.id); setDraft(it.body); }}>改</button>
                      <button className="btn btn-sm" onClick={() => drop(it.id)}>不发</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {held.length > 0 && (
        <>
          <div className="section-title">没进队列的（补好再发）</div>
          {held.slice(0, 8).map((h) => (
            <div key={h.lead_no} className="muted">· {h.company}：{h.detail}</div>
          ))}
        </>
      )}
    </div>
  );
}
