import { useEffect, useRef, useState } from "react";
import { fetchSequences, createSequence, fetchDue, sendDue, pollReplies, fetchJob, loadSeeds, fetchQuota } from "../api";
import type { Sequence, DueItem, SendJob } from "../types";

const CH_LABEL: Record<string, string> = { email: "Email", whatsapp: "WhatsApp", instagram: "Instagram", facebook: "Facebook" };

type Step = { day_offset: number; subject: string; body: string };
const BLANK_STEPS: Step[] = [
  { day_offset: 0, subject: "", body: "" },
  { day_offset: 3, subject: "", body: "" },
];

export function SequencesPanel({ onChanged }: { onChanged?: () => void }) {
  const [seqs, setSeqs] = useState<Sequence[]>([]);
  const [due, setDue] = useState<DueItem[]>([]);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [job, setJob] = useState<SendJob | null>(null);
  const [sending, setSending] = useState(false);
  const [msg, setMsg] = useState("");

  // builder state
  const [name, setName] = useState("");
  const [channel, setChannel] = useState("email");
  const [steps, setSteps] = useState<Step[]>(BLANK_STEPS);

  const [quota, setQuota] = useState<Record<string, { sent_today: number; cap: number; batch?: number }>>({});

  // 默认只勾选今天真能发出去的量：全选 266 条再点发，后端会截断，界面却让人以为都发了。
  function pickWithinQuota(items: DueItem[], q: typeof quota): Set<number> {
    const left: Record<string, number> = {};
    const picked = new Set<number>();
    for (const d of items) {
      if (left[d.channel] === undefined) {
        const qc = q[d.channel];
        const remainingToday = qc ? Math.max(0, qc.cap - qc.sent_today) : 0;
        left[d.channel] = Math.min(remainingToday, qc?.batch ?? 20);
      }
      if (left[d.channel] > 0) { picked.add(d.enrollment_id); left[d.channel] -= 1; }
    }
    return picked;
  }

  const pollRef = useRef<number | null>(null);
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  function reload() {
    fetchSequences().then(setSeqs).catch((e) => setMsg(String(e)));
    Promise.all([fetchDue(), fetchQuota()])
      .then(([d, q]) => { setDue(d); setQuota(q); setPicked(pickWithinQuota(d, q)); })
      .catch((e) => setMsg(`跟进队列或额度加载失败：${String(e)}`));
  }
  useEffect(reload, []);

  const isEmail = channel === "email";
  const togglePick = (id: number) => setPicked((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });

  async function save() {
    if (!name.trim()) { setMsg("请填序列名称"); return; }
    const clean = steps.filter((s) => s.body.trim());
    if (!clean.length) { setMsg("至少要有一步且填正文"); return; }
    try {
      await createSequence({
        name: name.trim(), channel,
        steps: clean.map((s) => ({ day_offset: Number(s.day_offset) || 0, subject: isEmail ? s.subject : null, body: s.body })),
      });
      setName(""); setSteps(BLANK_STEPS); setMsg(`已创建序列「${name.trim()}」`);
      reload();
    } catch (e) { setMsg("创建失败：" + String(e)); }
  }

  async function send() {
    if (picked.size === 0) { setMsg("请先勾选要发送的跟进"); return; }
    setSending(true); setMsg(""); setJob(null);
    try {
      const start = await sendDue([...picked]);
      setMsg(`本批将发送 ${start.will_send} 条跟进…`);
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = window.setInterval(async () => {
        const j = await fetchJob(start.job_id);
        setJob(j);
        if (j.status !== "running") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null; setSending(false); reload(); onChanged?.();
        }
      }, 1500);
    } catch (e) { setMsg("发送失败：" + String(e)); setSending(false); }
  }

  async function seed() {
    try {
      const r = await loadSeeds();
      setMsg(r.templates === 0 && r.sequence_ids.length === 0
        ? "现成话术已经载入过了"
        : `已载入 ${r.templates} 条话术模板${r.sequence_ids.length ? ` + ${r.sequence_ids.length} 个 3 步冷邮件跟进序列（英/西/葡，第 0/3/8 天）` : ""}。序列在下方，模板在触达面板的下拉里选。`);
      reload(); onChanged?.();
    } catch (e) { setMsg("载入失败：" + String(e)); }
  }

  async function poll() {
    try { const r = await pollReplies(); setMsg(`已拉取邮件：回复 ${r.replies} 封、退信 ${r.bounces} 封（邮箱已标无效）、退订 ${r.unsubscribes} 家（已停发）。回复正文在"收件箱"页查看。`); reload(); onChanged?.(); }
    catch (e) { setMsg("拉取回复失败（需配置 Gmail 授权码）：" + String(e)); }
  }

  return (
    <>
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
          <h3 style={{ margin: 0 }}>今日待发跟进（{due.length}）</h3>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-sm" onClick={seed}
              title="一键载入现成话术：英/西/葡三语首次触达邮件 + 跟进邮件 + WA/IG DM 模板，外加一个 3 步冷邮件跟进序列（第 0/3/8 天）。已存在的不会重复添加。">
              ✨ 载入现成话术
            </button>
            <button className="btn btn-sm" onClick={poll} title="从 Gmail 收件箱拉取回复，自动停掉已回复客户的后续跟进">↻ 拉取邮件回复</button>
            <button className="btn btn-green btn-sm" onClick={send} disabled={sending || due.length === 0}>
              {sending ? "发送中…" : `发送已选（${picked.size}）`}
            </button>
          </div>
        </div>
        {due.length === 0 && <div className="muted" style={{ marginTop: 8 }}>今天没有到期的跟进。把客户加入序列后，到期的那一步会出现在这里。</div>}
        {due.length > picked.size && (
          <div className="warn-text" style={{ marginTop: 8, fontSize: 13 }}>
            队列里有 {due.length} 条，今天只勾了 {picked.size} 条——防封上限（邮件单次 {quota.email?.batch ?? 30} 封、
            WA/IG 单次 20 条），剩下的明天继续，不会丢。硬发更多会被判垃圾/限号，得不偿失。
            {quota.email && ` 今日邮件已发 ${quota.email.sent_today}/${quota.email.cap}。`}
          </div>
        )}
        {due.length > 0 && (
          <table className="lead-table" style={{ marginTop: 10 }}>
            <thead><tr><th style={{ width: 32 }}></th><th>客户</th><th>序列</th><th>第几步</th><th>话术预览</th></tr></thead>
            <tbody>
              {due.map((d) => (
                <tr key={d.enrollment_id}>
                  <td><input type="checkbox" checked={picked.has(d.enrollment_id)} onChange={() => togglePick(d.enrollment_id)} /></td>
                  <td>{d.company_en}</td>
                  <td>{d.sequence_name} <span className="muted">· {CH_LABEL[d.channel] ?? d.channel}</span></td>
                  <td>第 {d.step_order + 1} 步</td>
                  <td className="muted" style={{ maxWidth: 360, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{d.body}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {job && <div className="muted" style={{ marginTop: 8 }}>进度 {job.done}/{job.total}
          {job.status === "done" && job.result && "sent" in job.result &&
            ` — 成功 ${job.result.sent}，失败 ${job.result.failed}${job.result.deferred ? `，延后 ${job.result.deferred}（日上限）` : ""}`}
          {job.status === "error" && job.result && "error" in job.result && ` — 错误：${job.result.error}`}
        </div>}
        {msg && <div className="muted" style={{ marginTop: 8 }}>{msg}</div>}
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3>新建跟进序列</h3>
        <div className="muted" style={{ fontSize: 12, marginBottom: 10 }}>
          冷触达发一次基本没人回，回复几乎都在第 2–4 次跟进。设定几步话术和间隔天数，到期后系统会把这一步放进上面的待发队列，仍由你手动确认发送（守住防封）。正文里可用变量：{"{name}"}=公司名、{"{contact}"}=联系人（缺失时自动写 there）、{"{country}"}、{"{city}"}。
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
          <input className="input" placeholder="序列名称，如「冷触达 3 步」" value={name} onChange={(e) => setName(e.target.value)} style={{ minWidth: 220 }} />
          <select className="input" value={channel} onChange={(e) => setChannel(e.target.value)}>
            <option value="email">Email</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="instagram">Instagram</option>
          </select>
        </div>
        {steps.map((s, i) => (
          <div key={i} className="card" style={{ padding: 10, marginBottom: 8, background: "var(--surface-2)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
              <b style={{ fontSize: 13 }}>第 {i + 1} 步</b>
              <label className="muted" style={{ fontSize: 12 }}>入组后第
                <input className="input" type="number" min={0} value={s.day_offset}
                  onChange={(e) => setSteps((st) => st.map((x, j) => j === i ? { ...x, day_offset: Number(e.target.value) } : x))}
                  style={{ width: 60, margin: "0 4px" }} /> 天发送</label>
              {steps.length > 1 && <button className="btn btn-sm" onClick={() => setSteps((st) => st.filter((_, j) => j !== i))}>删除此步</button>}
            </div>
            {isEmail && <input className="input" placeholder="邮件主题（可用 {name}）" value={s.subject} style={{ width: "100%", marginBottom: 6 }}
              onChange={(e) => setSteps((st) => st.map((x, j) => j === i ? { ...x, subject: e.target.value } : x))} />}
            <textarea className="input" placeholder="这一步的话术正文" value={s.body} style={{ height: 80 }}
              onChange={(e) => setSteps((st) => st.map((x, j) => j === i ? { ...x, body: e.target.value } : x))} />
          </div>
        ))}
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-sm" onClick={() => setSteps((st) => [...st, { day_offset: (st[st.length - 1]?.day_offset ?? 0) + 4, subject: "", body: "" }])}>+ 加一步</button>
          <button className="btn btn-primary" onClick={save}>创建序列</button>
        </div>
      </div>

      <div className="card">
        <h3>已有序列</h3>
        {seqs.length === 0 && <div className="muted">还没有序列。</div>}
        {seqs.map((s) => (
          <div key={s.id} style={{ borderTop: "1px solid var(--border)", padding: "10px 0" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <b>{s.name} <span className="muted">· {CH_LABEL[s.channel] ?? s.channel}</span></b>
              <span className="muted">进行中 {s.enrolled} 家 · {s.steps.length} 步</span>
            </div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
              {s.steps.map((st) => `第${st.step_order + 1}步(第${st.day_offset}天)`).join(" → ")}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
