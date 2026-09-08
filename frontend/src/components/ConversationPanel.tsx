// 客户对话：左边是等我们回的人，右边是和这个人的全部往来。docs/56
import { useEffect, useRef, useState } from "react";
import {
  fetchConversation, fetchConversations, sendReply,
  type Conversation, type ConversationEvent, type ConversationRow,
} from "../conversationApi";

const CH: Record<string, string> = {
  email: "邮件", whatsapp: "WhatsApp", instagram: "Instagram", facebook: "Facebook",
};
const STATE_LABEL: Record<string, string> = {
  waiting_us: "等我们回", waiting_customer: "等客户", human_takeover: "你已接手", closed: "已结束",
};
const KIND_LABEL: Record<string, string> = { auto: "自动回复", bounce: "退信", unsubscribe: "退订" };

function fmt(iso: string | null | undefined): string {
  if (!iso) return "时间不明";
  const d = new Date(iso);
  return isNaN(+d) ? iso : d.toLocaleString();
}

function Event({ e }: { e: ConversationEvent }) {
  const mine = e.kind === "sent";
  if (e.kind === "activity") {
    return (
      <div className="ts" style={{ padding: "6px 0", opacity: 0.7 }}>
        ◉ {fmt(e.at)} · {e.title}
      </div>
    );
  }
  const meta = [
    mine ? "我们发出" : e.from || "客户",
    CH[e.channel || "email"] || e.channel,
    fmt(e.at),
    e.campaign,
    e.message_kind && e.message_kind !== "reply" ? KIND_LABEL[e.message_kind] || e.message_kind : null,
  ].filter(Boolean).join(" · ");
  return (
    <div style={{ display: "flex", justifyContent: mine ? "flex-end" : "flex-start", margin: "10px 0" }}>
      <div className="card" style={{ maxWidth: "78%", opacity: e.quiet ? 0.65 : 1 }}>
        <div className="ts" style={{ marginBottom: 4 }}>{meta}</div>
        {e.subject && <div style={{ fontWeight: 600, marginBottom: 4 }}>{e.subject}</div>}
        {e.body_missing ? (
          // 信确实发出去了，但正文没留存。不拿模板重渲染顶上 —— docs/56 R1.1
          <div className="ts" style={{ fontStyle: "italic" }}>
            正文未留存（发这封信的时候，系统还没有保存正文）
          </div>
        ) : (
          <div style={{ whiteSpace: "pre-wrap" }}>{e.body}</div>
        )}
      </div>
    </div>
  );
}

function ReplyBox({ no, onSent }: { no: number; onSent: () => void }) {
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [blocked, setBlocked] = useState<{ reason: string; detail: string } | null>(null);
  const [err, setErr] = useState("");

  async function go(override: boolean) {
    if (!body.trim()) return;
    setBusy(true); setErr(""); setBlocked(null);
    try {
      const r = await sendReply(no, body, undefined, override);
      if ("blocked" in r) { setBlocked({ reason: r.reason, detail: r.detail }); return; }
      setBody(""); onSent();
    } catch (ex) {
      setErr(String(ex instanceof Error ? ex.message : ex));
    } finally { setBusy(false); }
  }

  return (
    <div className="card" style={{ marginTop: 12, flexShrink: 0 }}>
      <textarea value={body} onChange={(e) => { setBody(e.target.value); setBlocked(null); }}
        rows={4} placeholder="写回复…发出去走的是和 Agent 一样的邮箱、一样的检查"
        style={{ width: "100%", resize: "vertical" }} />
      {blocked && (
        <div className="card" style={{ borderColor: "var(--danger)", margin: "8px 0" }}>
          <div style={{ fontWeight: 600 }}>拦下了：{blocked.reason}</div>
          <div className="ts">{blocked.detail}</div>
          <button className="btn" disabled={busy} onClick={() => go(true)} style={{ marginTop: 8 }}>
            我知道，还是发出去
          </button>
        </div>
      )}
      {err && <div className="ts" style={{ color: "var(--danger)" }}>{err}</div>}
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
        <button className="btn btn-primary" disabled={busy || !body.trim()} onClick={() => go(false)}>
          {busy ? "发送中…" : "发送"}
        </button>
      </div>
    </div>
  );
}

export function ConversationPanel({ onOpenLead }: { onOpenLead?: (no: number) => void }) {
  const [rows, setRows] = useState<ConversationRow[]>([]);
  const [waitingOnly, setWaitingOnly] = useState(false);
  const [picked, setPicked] = useState<number | null>(null);
  const [conv, setConv] = useState<Conversation | null>(null);
  const [showQuiet, setShowQuiet] = useState(false);
  const [err, setErr] = useState("");
  const timeline = useRef<HTMLDivElement>(null);

  async function loadList() {
    try { setRows(await fetchConversations(waitingOnly)); }
    catch (ex) { setErr(String(ex instanceof Error ? ex.message : ex)); }
  }
  async function loadConv(no: number) {
    try { setConv(await fetchConversation(no)); }
    catch (ex) { setErr(String(ex instanceof Error ? ex.message : ex)); }
  }

  useEffect(() => { loadList(); }, [waitingOnly]);
  useEffect(() => { if (picked != null) loadConv(picked); }, [picked]);
  // 换一个客户，右边从最新的一条开始看 —— 时间线是旧在上、新在下，而要处理的是最后
  // 那一条。不重置的话，这个 div 会留着上一个客户的滚动位置。
  useEffect(() => {
    const el = timeline.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [conv]);

  const events = conv ? conv.events.filter((e) => showQuiet || !e.quiet) : [];
  const hidden = conv ? conv.events.length - events.length : 0;

  return (
    // 两栏各自滚动，页面本身不滚。之前整页是一个滚动条，客户列表一长，点到下面的客户
    // 时右边的对话已经在屏幕上方几千像素处，每选一个人都要先往上拉一次。
    <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16,
                  flex: 1, minHeight: 360 }}>
      <div style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8, flexShrink: 0 }}>
          <button className={waitingOnly ? "btn btn-primary" : "btn"}
            onClick={() => setWaitingOnly((v) => !v)}>只看等我们回的</button>
          <button className="btn" onClick={loadList}>刷新</button>
        </div>
        <div style={{ flex: 1, minHeight: 0, overflowY: "auto", paddingRight: 6 }}>
        {err && <div className="ts" style={{ color: "var(--danger)" }}>{err}</div>}
        {rows.length === 0 && <div className="ts">还没有任何往来记录。</div>}
        {rows.map((r) => (
          <div key={r.no} className="card"
            style={{ cursor: "pointer", marginBottom: 6, borderColor: picked === r.no ? "var(--accent)" : undefined }}
            onClick={() => setPicked(r.no)}>
            <div style={{ fontWeight: 600 }}>
              {r.company_en || "#" + r.no}
              {r.unread > 0 && <span className="badge badge-replied" style={{ marginLeft: 6 }}>{r.unread} 未读</span>}
            </div>
            <div className="ts">
              {r.country || "国家未知"} · 发 {r.sent_count} 收 {r.reply_count}
              {r.state ? " · " + (STATE_LABEL[r.state] || r.state) : ""}
            </div>
            <div className="ts">{fmt(r.last_at)}</div>
          </div>
        ))}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
        {!conv && <div className="ts">左边选一个客户，看和他的全部往来。</div>}
        {conv && (
          <>
            <div className="card" style={{ marginBottom: 10, flexShrink: 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 16 }}>
                    {conv.lead.company_en || "#" + conv.lead.no}
                    {conv.lead.company_local && conv.lead.company_local !== conv.lead.company_en
                      && <span className="ts" style={{ marginLeft: 8 }}>{conv.lead.company_local}</span>}
                  </div>
                  <div className="ts">
                    {[conv.lead.contact_name, conv.lead.title, conv.lead.email, conv.lead.country]
                      .filter(Boolean).join(" · ")}
                  </div>
                  {conv.lead.tags && <div className="ts">标签：{conv.lead.tags}</div>}
                </div>
                <div style={{ textAlign: "right" }}>
                  {conv.state && <span className="badge">{STATE_LABEL[conv.state.state] || conv.state.state}</span>}
                  {onOpenLead && <button className="btn" style={{ marginLeft: 8 }}
                    onClick={() => onOpenLead(conv.lead.no)}>打开客户档案</button>}
                </div>
              </div>
              {conv.missing_bodies > 0 && (
                <div className="ts" style={{ marginTop: 8 }}>
                  这个客户有 {conv.missing_bodies} 封已发邮件没留存正文 —— 那时系统只记了发出的是哪一步。
                </div>
              )}
            </div>

            <div ref={timeline}
              style={{ flex: 1, minHeight: 0, overflowY: "auto", paddingRight: 6 }}>
              {events.map((e) => <Event key={e.kind + "-" + e.id} e={e} />)}
            </div>
            {hidden > 0 && (
              <button className="btn" style={{ marginTop: 8, flexShrink: 0 }} onClick={() => setShowQuiet(true)}>
                还有 {hidden} 条系统消息（退信、自动回复、Agent 动作）
              </button>
            )}
            {showQuiet && (
              <button className="btn" style={{ marginTop: 8, flexShrink: 0 }} onClick={() => setShowQuiet(false)}>
                收起系统消息
              </button>
            )}

            {conv.lead.do_not_contact
              ? <div className="ts" style={{ marginTop: 12, flexShrink: 0 }}>这个客户标了不再联系，不能在这里回信。</div>
              : <ReplyBox no={conv.lead.no} onSent={() => { loadConv(conv.lead.no); loadList(); }} />}
          </>
        )}
      </div>
    </div>
  );
}
