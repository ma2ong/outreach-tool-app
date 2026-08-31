// 一家客户的往来记录：发了什么、什么时候发的，邮件和 IG/FB/WA 排在同一条时间线上。
// 数据来自 docs/56 已有的 timeline 接口，这里只是把它放到客户页面上——以前要看
// 「上次给这家发了什么」得离开客户页去对话页找人，那是把一件事拆成了两个地方。
import { useEffect, useState } from "react";
import { fetchConversation, type ConversationEvent } from "../conversationApi";
import type { Lead } from "../types";

const CH: Record<string, string> = {
  email: "邮件", whatsapp: "WhatsApp", instagram: "Instagram", facebook: "Facebook",
};
const KIND_LABEL: Record<string, string> = { auto: "自动回复", bounce: "退信", unsubscribe: "退订" };
const STATE_TEXT: Record<string, string> = { replied: "已回复", messaged: "已触达" };

function fmt(iso: string | null | undefined): string {
  if (!iso) return "时间不明";
  const d = new Date(iso);
  return isNaN(+d) ? iso : d.toLocaleString();
}

function Row({ e }: { e: ConversationEvent }) {
  const [open, setOpen] = useState(false);
  if (e.kind === "activity") {
    return <div className="ts" style={{ padding: "5px 0", opacity: 0.7 }}>◉ {fmt(e.at)} · {e.title}</div>;
  }
  const mine = e.kind === "sent";
  const body = e.body ?? "";
  // 长信折起来：时间线是拿来扫的，一屏塞两封完整邮件就扫不动了。
  const long = body.length > 160;
  const meta = [
    CH[e.channel || "email"] || e.channel,
    e.campaign,
    e.message_kind && e.message_kind !== "reply" ? KIND_LABEL[e.message_kind] || e.message_kind : null,
  ].filter(Boolean).join(" · ");
  return (
    <div className="note-item" style={{
      marginBottom: 7, opacity: e.quiet ? 0.7 : 1,
      borderLeft: `3px solid var(--${mine ? "primary" : "success"}, #888)`, paddingLeft: 9,
    }}>
      <div className="ts" style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 3 }}>
        <b style={{ fontWeight: 600 }}>{mine ? "→ 我们发出" : `← ${e.from || "客户"}`}</b>
        <span>{meta}</span>
        <span style={{ marginLeft: "auto" }}>{fmt(e.at)}</span>
      </div>
      {e.subject && <div style={{ fontWeight: 600, marginBottom: 3 }}>{e.subject}</div>}
      {e.body_missing ? (
        // 信确实发出去了，但正文没留存。不拿模板重渲染顶上 —— docs/56 R1.1
        <div className="ts" style={{ fontStyle: "italic" }}>正文未留存（发这封信的时候，系统还没有保存正文）</div>
      ) : (
        <div style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>
          {long && !open ? body.slice(0, 160) + "…" : body}
          {long && <button className="btn btn-sm" style={{ marginLeft: 6 }}
            onClick={() => setOpen((v) => !v)}>{open ? "收起" : "全文"}</button>}
        </div>
      )}
    </div>
  );
}

export function CorrespondencePanel({ leadNo, outreach }: {
  leadNo: number; outreach: Lead["outreach"];
}) {
  const [events, setEvents] = useState<ConversationEvent[] | null>(null);
  const [err, setErr] = useState("");
  const [showQuiet, setShowQuiet] = useState(false);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    setEvents(null); setErr("");
    fetchConversation(leadNo)
      // 最新的在上面：客户页面上要回答的问题是「上次说到哪了」，不是「一开始说了什么」。
      .then((c) => setEvents([...c.events].reverse()))
      .catch((e) => setErr(String(e)));
  }, [leadNo]);

  const visible = (events ?? []).filter((e) => showQuiet || !e.quiet);
  const shown = showAll ? visible : visible.slice(0, 8);
  const quietCount = (events ?? []).filter((e) => e.quiet).length;

  return (
    <>
      <div className="section-title" style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span>往来记录</span>
        <span style={{ marginLeft: "auto", display: "flex", gap: 5, flexWrap: "wrap" }}>
          {outreach.length === 0
            ? <span className="muted" style={{ fontSize: 12, fontWeight: 400 }}>尚未触达</span>
            : outreach.map((o) => (
              <span key={o.channel} className={`badge badge-${o.status === "replied" ? "replied" : o.status === "messaged" ? "messaged" : "untouched"}`}>
                <i />{CH[o.channel] ?? o.channel}：{STATE_TEXT[o.status] ?? o.status}
                {o.message_sent_date ? ` (${o.message_sent_date})` : ""}
              </span>
            ))}
        </span>
      </div>
      {err && <div className="error-text" style={{ marginBottom: 8 }}>往来记录读不出来：{err}</div>}
      {events === null && !err && <div className="muted">正在读往来记录…</div>}
      {events !== null && visible.length === 0 &&
        <div className="muted">还没有任何往来记录。</div>}
      {shown.map((e) => <Row key={`${e.kind}-${e.id}`} e={e} />)}
      <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
        {visible.length > shown.length &&
          <button className="btn btn-sm" onClick={() => setShowAll(true)}>
            展开全部 {visible.length} 条
          </button>}
        {quietCount > 0 &&
          <button className="btn btn-sm" onClick={() => setShowQuiet((v) => !v)}>
            {showQuiet ? "收起" : `显示`} 自动回复 / 退信 / 任务（{quietCount}）
          </button>}
      </div>
    </>
  );
}
