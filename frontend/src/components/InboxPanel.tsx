import { useEffect, useState } from "react";
import { fetchInbox, markInboxHandled, markInboxRead, pollReplies, scanSocial } from "../api";
import { approveProposal, fetchAgentMeta, fetchProposals } from "../agentApi";
import type { AgentMeta, Proposal } from "../agentApi";
import type { InboxMessage } from "../types";

const CH_NAME: Record<string, string> = { whatsapp: "WhatsApp", instagram: "Instagram", email: "邮件" };
const KIND_LABEL: Record<string, string> = { reply: "回复", auto: "自动回复", attachment: "只发了图", unsubscribe: "退订" };
const KIND_COLOR: Record<string, string> = { reply: "badge-replied", auto: "badge-messaged", attachment: "badge-messaged", unsubscribe: "badge-messaged" };

function fmtTs(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(+d) ? iso : d.toLocaleString();
}

function DraftBox({ p, onDone }: { p: Proposal; onDone: () => void }) {
  const [body, setBody] = useState(String(p.payload?.body ?? ""));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const edited = body !== String(p.payload?.body ?? "");

  async function send(e: React.MouseEvent) {
    e.stopPropagation();
    setBusy(true); setErr("");
    try {
      await approveProposal(p.id, { ...p.payload, body });
      onDone();
    } catch (ex) {
      setErr(String(ex instanceof Error ? ex.message : ex));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" style={{ margin: "10px 0", borderColor: p.risk === "high" ? "var(--danger)" : undefined }}
      onClick={(e) => e.stopPropagation()}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <span className="stat-label">AI 草稿</span>
        {p.risk === "high" && <span className="warn-text" style={{ fontSize: 12 }}>需要你逐字看过</span>}
      </div>
      <div className="muted" style={{ fontSize: 12, margin: "4px 0 8px" }}>{p.reasoning}</div>
      <textarea className="input" rows={8} value={body} onChange={(e) => setBody(e.target.value)}
        style={{ width: "100%", fontFamily: "inherit" }} />
      {!!p.evidence?.length && (
        <div style={{ marginTop: 8 }}>
          {p.evidence.map((ev, i) => (
            <div key={i} className="muted" style={{ fontSize: 12 }}>· {ev.claim} —— {ev.source}</div>
          ))}
        </div>
      )}
      {err && <div className="error-text" style={{ marginTop: 8 }}>{err}</div>}
      <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <button className="btn btn-green btn-sm" disabled={busy} onClick={send}>
          {busy ? "发送中…" : edited ? "改后发送" : "确认发送"}
        </button>
        <span className="muted" style={{ fontSize: 12 }}>
          发给 {String(p.payload?.to ?? "")}
          {p.payload?.mailbox_email ? ` · 从 ${p.payload.mailbox_email} 发出` : ""}
          　不想发就去 Agent 页驳回
        </span>
      </div>
    </div>
  );
}

export function InboxPanel({ onOpenLead, onPendingChange }: {
  onOpenLead: (leadNo: number) => void;
  onPendingChange?: () => void;
}) {
  const [messages, setMessages] = useState<InboxMessage[]>([]);
  const [pendingOnly, setPendingOnly] = useState(false);
  const [open, setOpen] = useState<number | null>(null);
  const [polling, setPolling] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [drafts, setDrafts] = useState<Record<number, Proposal>>({});
  const [meta, setMeta] = useState<AgentMeta | null>(null);

  function reload() {
    fetchInbox(pendingOnly).then(setMessages).catch((e) => setErr(String(e)));
    // The draft belongs next to the reply it answers, so Allen never leaves this page
    // to deal with the thing this page exists for.
    fetchProposals({ status: "pending", kind: "reply_draft" })
      .then((ps) => setDrafts(Object.fromEntries(
        ps.filter((p) => p.inbox_message_id).map((p) => [p.inbox_message_id as number, p]))))
      .catch(() => setDrafts({}));
  }
  useEffect(reload, [pendingOnly]);
  useEffect(() => { fetchAgentMeta().then(setMeta).catch(() => setMeta(null)); }, []);

  async function poll() {
    setPolling(true); setMsg("正在拉取邮件…");
    try {
      const r = await pollReplies();
      setMsg(`拉取完成（回看 ${r.since_days} 天）：回复 ${r.replies} 封、退订 ${r.unsubscribes} 家（已停止一切触达）。`
        + `另有退信 ${r.bounces} 封（邮箱已自动标无效，不再发送）、投递延迟 ${r.delayed ?? 0} 封（地址仍有效），都不进收件箱`);
      reload(); onPendingChange?.();
    } catch (e) { setMsg("拉取失败（需配置 Gmail 授权码）：" + String(e)); }
    finally { setPolling(false); }
  }

  async function scan() {
    setScanning(true); setMsg("正在读取 WhatsApp / Instagram 会话列表…（只读列表，不会打开对话、不会清掉你手机上的未读）");
    try {
      const r = await scanSocial();
      const per = r.channels.map((c) => `${CH_NAME[c.channel] ?? c.channel} ${c.replies} 条`).join("、");
      const bad = r.errors.length ? `；失败：${r.errors.map((e) => `${CH_NAME[e.channel] ?? e.channel}(${e.error})`).join("、")}` : "";
      const off = r.skipped?.length ? `；未连接已跳过：${r.skipped.map((c) => CH_NAME[c] ?? c).join("、")}` : "";
      // 对不上客户的入站消息也要报出来 —— 悄悄丢掉就等于没修
      const un = r.unmatched?.length
        ? `；另有 ${r.unmatched.length} 条对方来信没能对上客户（${r.unmatched.slice(0, 5).join("、")}），请到 App 里自行查看`
        : "";
      setMsg(`扫描完成：共 ${r.threads} 个会话，识别到真人回复 ${r.replies} 条、自动回复 ${r.auto ?? 0} 条（自动回复不算已回复，跟进继续）（新入库 ${r.stored} 条）${per ? "——" + per : ""}${un}${off}${bad}`);
      reload(); onPendingChange?.();
    } catch (e) { setMsg("扫描失败：" + String(e)); }
    finally { setScanning(false); }
  }

  async function toggleOpen(m: InboxMessage) {
    setOpen(open === m.id ? null : m.id);
    if (!m.is_read) {
      try {
        await markInboxRead(m.id);
        setMessages((ms) => ms.map((x) => (x.id === m.id ? { ...x, is_read: 1 } : x)));
        onPendingChange?.();
      } catch { /* 已读标记失败不打断阅读 */ }
    }
  }

  async function handle(m: InboxMessage) {
    try {
      await markInboxHandled(m.id);
      setMessages((ms) => pendingOnly
        ? ms.filter((x) => x.id !== m.id)
        : ms.map((x) => (x.id === m.id ? { ...x, is_read: 1, handled_at: new Date().toISOString() } : x)));
      onPendingChange?.();
      setMsg(`${m.company_en} 的回复已标记处理完成`);
    } catch (e) { setErr(`更新处理状态失败：${String(e)}`); }
  }

  return (
    <div className="card">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <h3 style={{ margin: 0 }}>收件箱（{messages.length}）</h3>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <label className="muted" style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 4 }}>
            <input type="checkbox" checked={pendingOnly} onChange={(e) => setPendingOnly(e.target.checked)} />只看待处理
          </label>
          <button className="btn btn-sm" onClick={poll} disabled={polling}
            title="拉取邮件：客户回复入库、退信自动标无效邮箱、退订自动停发。回看天数按上次成功同步的间隔自动决定">
            {polling ? "拉取中…" : "↻ 拉取邮件"}
          </button>
          <button className="btn btn-sm" onClick={scan} disabled={scanning}
            title="读取 WhatsApp / Instagram 会话列表，找出客户回复。只读列表、不打开对话，不会清掉手机上的未读。需要先在「渠道」页连接登录">
            {scanning ? "扫描中…" : "↻ 扫社媒回复"}
          </button>
        </div>
      </div>
      <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
        客户回了什么直接在这里看，不用去翻 Gmail 和手机。打开消息只代表已读；回复客户、建商机或安排下一步后，点「完成处理」才会从首页待办消失。邮件每 15 分钟自动同步、
        WhatsApp / Instagram 每天自动扫一次（仅在已连接时）。退信和投递延迟不进这里：退信自动把邮箱标为无效，退订自动停止一切触达。
        <br />Instagram 的来信多数落在 App 的「一般」和「消息请求」标签里，主收件箱看不到 —— 在这里看到 Instagram 消息却在手机上找不到，去那两个标签翻。
      </div>
      {err && <div className="error-text" style={{ marginTop: 8 }}>加载失败：{err}</div>}
      {msg && <div className="muted" style={{ marginTop: 8 }}>{msg}</div>}
      {messages.length === 0 ? (
        <div className="muted" style={{ marginTop: 12 }}>还没有消息。点「拉取邮件」同步邮件回复，点「扫社媒回复」读 WhatsApp / Instagram。</div>
      ) : (
        <div style={{ marginTop: 10 }}>
          {messages.map((m) => (
            <div key={m.id} className="note-item" style={{ cursor: "pointer", opacity: m.is_read && open !== m.id ? 0.75 : 1 }}
              onClick={() => toggleOpen(m)}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <span className={`badge ${KIND_COLOR[m.kind] ?? ""}`}><i />{KIND_LABEL[m.kind] ?? m.kind}</span>
                <strong style={{ fontWeight: m.is_read ? 500 : 700 }}>{m.company_en}</strong>
                {m.contact_name && <span className="muted">联系人：{m.contact_name}</span>}
                {m.kind === "reply" && !m.handled_at && <span className="warn-text" style={{ fontSize: 12 }}>待处理</span>}
                {m.intent && meta && <span className="tag">{meta.intents[m.intent] ?? m.intent}</span>}
                {drafts[m.id] && <span className="tag" style={{ color: "var(--green)", borderColor: "var(--green)" }}>已起草</span>}
                {m.kind === "reply" && m.handled_at && <span className="muted" style={{ fontSize: 12 }}>已处理</span>}
                {m.country && <span className="muted">{m.country}</span>}
                {m.channel !== "email" && <span className="muted" style={{ fontSize: 12 }}>{CH_NAME[m.channel] ?? m.channel}</span>}
                <span className="muted" style={{ fontSize: 12 }}>{m.subject || "(无主题)"}</span>
                <span className="muted" style={{ marginLeft: "auto", fontSize: 12 }}>{fmtTs(m.received_at)}</span>
              </div>
              {open === m.id && (
                <div style={{ marginTop: 8 }}>
                  <div className="muted" style={{ fontSize: 12 }}>
                    发件人：{m.from_addr}{m.contact_name ? ` · 已匹配 ${m.contact_name}` : ""}
                  </div>
                  <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", fontSize: 13, margin: "6px 0" }}>{m.body || "(无正文)"}</pre>
                  <button className="btn btn-sm" style={{ marginRight: 8 }} onClick={(e) => { e.stopPropagation(); onOpenLead(m.lead_no); }}>
                    打开客户详情 →
                  </button>
                  {m.kind === "reply" && !m.handled_at && (
                    <button className="btn btn-green btn-sm" style={{ marginRight: 8 }}
                      onClick={(e) => { e.stopPropagation(); handle(m); }}
                      title="确认你已经回复客户、建了商机或安排了明确下一步">
                      ✓ 已回复客户 / 已安排下一步
                    </button>
                  )}
                  {drafts[m.id] && (
                    <DraftBox p={drafts[m.id]} onDone={() => { reload(); onPendingChange?.(); }} />
                  )}
                  {m.channel === "email" && m.kind === "reply" && m.from_addr && (
                    <a className="btn btn-sm" target="_blank" rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      href={`https://mail.google.com/mail/u/0/#search/${encodeURIComponent("from:" + m.from_addr)}`}
                      title="在 Gmail 里打开和这个客户的往来邮件，直接回复">
                      ↩ 去 Gmail 回复
                    </a>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
